#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import queue
import thread_pool

from solnlib.modular_input import event_writer

import import_declare_test
import json
import threading
import time
import traceback
from datetime import datetime, timedelta
from json import loads

from checkpoint import Checkpointer
from box_client import BoxAPIError, BoxClient
from solnlib import utils, log

_LOGGER = log.Logs().get_logger("ta_box")


def _json_loads(content):
    if not content:
        return None

    try:
        return loads(content)
    except Exception:
        _LOGGER.error("Failed to parse json. Reason=%s", traceback.format_exc())
        return None


def get_entity_location(entity_sequence):
    entity_location = [entity["name"] for entity in entity_sequence if entity["name"]]
    entity_location = "/".join(entity_location)
    entity_location = str(entity_location).replace('"', '\\"')
    return entity_location


def flatten_json_dict_type(prefix, obj):
    template = '%s_{}="{}"' % prefix if prefix else '{}="{}"'
    results = []
    for k, v in obj.items():  # py2/3():
        if k == "path_collection":
            if "entries" in v:
                res = 'location="{}"'.format(get_entity_location(v["entries"]))
        elif isinstance(v, dict):
            if prefix:
                k = "{}_{}".format(prefix, k)
            res = flatten_json_dict_type(k, v)
            if res:
                res = ",".join(res)
        elif isinstance(v, list):
            # FIXME
            res = template.format(k, v)
        else:
            if v:
                v = str(v).replace('"', '\\"')
            res = template.format(k, v if v is not None else "")
        results.append(res)
    return results


def _flatten_box_json_object(json_obj):
    results = []
    if "entries" in json_obj:
        for obj in json_obj["entries"]:
            res = flatten_json_dict_type(None, obj)
            if res:
                results.append(",".join(res))
    else:
        if isinstance(json_obj, dict):
            res = flatten_json_dict_type(None, json_obj)
            if res:
                results.append(",".join(res))
        else:
            # semgrep ignore reason: assertion error if json_obj is not a dict
            assert False  # nosemgrep: gitlab.bandit.B101
    return results


class _JObject:
    def __init__(self, obj, account_id, url, endpoint, name, input_name):
        self.obj = obj
        self.url = url
        self.endpoint = endpoint
        self.account_id = account_id
        self.name = name
        self.input_name = input_name

    def to_events(self, idx, host, ew):
        results = _flatten_box_json_object(self.obj)
        sourcetype = "box:" + self.endpoint
        source = "{0}::{1}".format(self.url, self.input_name)

        events = []
        for res in results:
            data = "{0},account_id={1}".format(res, self.account_id)
            event = ew.create_event(
                source=source,
                sourcetype=sourcetype,
                host=host,
                index=idx,
                data=data,
            )
            events.append(event)
        return events


class BoxBase:
    _UNKNOWN = 1

    def __init__(self, config, client=None):
        """
        @config: dict like, should have url, refresh_token, access_token,
                 checkpoint_dir, proxy_url, proxy_username, proxy_password
        """
        self.checkpoint_updated = False
        self.events_ingested = 0
        self.old_checkpoint = None
        self.updated_checkpoint = None

        self.config = config
        self._lock = threading.Lock()
        self._stopped = False
        self.client = client or BoxClient(self.config, logger=_LOGGER)

    def run(self):
        _ew = event_writer.ClassicEventWriter()
        while 1:
            events = []
            done, results = self.collect_data()
            if results is not None and len(results) > 0:
                self.events_ingested = 0
                idx = self.config.get("index", "main")
                host = self.config["host"]

                for obj in results:
                    _events = obj.to_events(idx, host, _ew)
                    events.extend(_events)

                _ew.write_events(events)
                self.events_ingested += len(events)
            if done:
                break

    def collect_data(self):
        if self._lock.locked():
            _LOGGER.info(
                "Last request for endpoint=%s has not been done yet",
                self.config["rest_endpoint"],
            )
            return True, None

        ret = self._check_if_job_is_due()
        if not ret:
            return True, None

        with self._lock:
            done, objs = self._do_collect()
            return done, objs

    def _do_collect(self):
        """
        @return: (done, objs)
        """

        uri = self._get_uri()  # pylint: disable=assignment-from-no-return
        if not uri:
            return True, None

        results = []
        err, content = self._send_request(uri, results, self.config["rest_endpoint"])
        if err:
            return True, None

        end_invocation = self._save_ckpts(content)

        if not results or end_invocation:
            return True, results

        return False, results

    def _do_expiration_check(self):
        return True

    def _check_if_job_is_due(self):
        """
        @return: True if the job is due else return False
        """

        if not self._do_expiration_check():
            return True

        ckpt = self._get_state()
        if ckpt is not None and ckpt["ckpts"] is None:
            last_timestamp = ckpt.get("start_timestamp", ckpt["timestamp"])
            delta = last_timestamp + self.config["interval"] - time.time()
            if int(delta) > 0:
                _LOGGER.info(
                    "There are %f seconds for the job=%s to be due for input=%s",
                    delta,
                    self.config["rest_endpoint"],
                    self.config["input_name"],
                )
                return False
        return True

    def _get_uri(self, ckpt=None, option=None):
        pass

    def _save_ckpts(self, content):
        pass

    def _send_request(
        self, uri, results, sourcetype, verify_entries=True, index_result=True
    ):
        try:
            status, json_response = self.client.make_request(uri)
        except BoxAPIError as ex:
            if ex.status == 415:
                fileid = ""
                try:
                    fileid = (uri.rsplit("/", 1)[-1]).rsplit("?", 1)[0]
                except Exception:
                    fileid = ""
                _LOGGER.warning(
                    "Box API error returned: %s File id %s skipped. Consider adjusting your API field parameters.",
                    ex.message,
                    fileid,
                )
            else:
                _LOGGER.error(
                    "Failed to connect url=%s, input_name=%s, "
                    "endpoint=%s, message=%s, status=%s, code=%s,"
                    " context_info=%s",
                    uri,
                    self.config.get("name", ""),
                    sourcetype,
                    ex.message,
                    ex.status,
                    ex.code,
                    ex.context_info,
                )
            return ex.status or self._UNKNOWN, None

        if status not in (200, 201):
            return status, None

        if not index_result:
            return None, json_response

        if not verify_entries or (json_response and json_response["entries"]):
            results.append(
                _JObject(
                    json_response,
                    self.config["account_id"],
                    self.config["url"],
                    sourcetype,
                    self.config["account"],
                    self.config["input_name"],
                )
            )
        return None, json_response

    def _save_state(self, ckpts, start_time=None):
        collection_name = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
            self.config["rest_endpoint"]
        )
        checkpointer_object = Checkpointer(
            self.config["session_key"],
            self.config["input_name"],
            collection_name,
            _LOGGER,
        )
        old_ckpt = checkpointer_object.get_kv_checkpoint_value()
        _LOGGER.debug(
            "Successfully received the KV store checkpoint for the input: {}".format(
                self.config["input_name"]
            )
        )

        ckpt = {
            "version": 2,
            "ckpts": ckpts,
            "timestamp": time.time(),
        }
        if start_time is not None:
            ckpt["start_timestamp"] = start_time
        elif old_ckpt is not None:
            ckpt["start_timestamp"] = old_ckpt.get(
                "start_timestamp", old_ckpt.get("timestamp", ckpt["timestamp"])
            )
        else:
            ckpt["start_timestamp"] = ckpt["timestamp"]
        _LOGGER.debug(
            "Saving Checkpoint for the input {}".format(
                self.config["input_name"],
            )
        )
        checkpointer_object.update_kv_checkpoint(ckpt)
        self.checkpoint_updated = True
        self.updated_checkpoint = ckpt
        _LOGGER.debug(
            "Saved the new state of the checkpoint for the input: {} with value {}".format(
                self.config["input_name"], json.dumps(ckpt)
            )
        )

    def _remove_state(self):
        collection_name = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
            self.config["rest_endpoint"]
        )
        checkpointer_object = Checkpointer(
            self.config["session_key"],
            self.config["input_name"],
            collection_name,
            _LOGGER,
        )
        use_state_store = True
        checkpointer_object.delete_file_checkpoint(
            use_state_store, self.config["checkpoint_dir"]
        )
        checkpointer_object.delete_kv_checkpoint()

        _LOGGER.debug(
            "Successfully removed the state of checkpoint for input: {}".format(
                self.config["input_name"]
            )
        )

    def _get_state(self):
        collection_name = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
            self.config["rest_endpoint"]
        )
        checkpointer_object = Checkpointer(
            self.config["session_key"],
            self.config["input_name"],
            collection_name,
            _LOGGER,
        )
        ckpt = checkpointer_object.get_kv_checkpoint_value()
        _LOGGER.debug(
            "Successfully received the kv store checkpoint for input: {}".format(
                self.config["input_name"]
            )
        )

        if ckpt:
            # semgrep ignore reason: assertion error for checkpoint version less than one
            assert ckpt["version"] >= 1  # nosemgrep: gitlab.bandit.B101
            _LOGGER.debug(
                "Found an existing checkpoint for the input {}.".format(
                    self.config["input_name"]
                )
            )
            self.old_checkpoint = ckpt.copy()
            return ckpt
        _LOGGER.debug(
            "No existing checkpoint found for the input {}. The add-on will collect all the data "
            "from the Box using stream position 0".format(self.config["input_name"])
        )
        return None

    @staticmethod
    def is_alive():
        return 1

    def revert_checkpoint(self):
        try:
            collection_name = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
                self.config["rest_endpoint"]
            )
            checkpointer_object = Checkpointer(
                self.config["session_key"],
                self.config["input_name"],
                collection_name,
                _LOGGER,
            )

            if self.checkpoint_updated:
                if not self.events_ingested:
                    # Case where checkpoint is updated but no events were ingested
                    if not self.old_checkpoint:
                        checkpointer_object.delete_kv_checkpoint()
                    else:
                        checkpointer_object.update_kv_checkpoint(self.old_checkpoint)

            _LOGGER.info("Successfully updated the checkpoint before exiting.")
        except Exception as exc:
            _LOGGER.error(
                "Unable to save checkpoint before SIGTERM termination. Error: %s", exc
            )


class BoxFile(BoxBase):
    def __init__(self, uri, src_type, verify_entries, config, client=None):
        super(BoxFile, self).__init__(config, client)
        self._uri = uri
        self._source_type = src_type
        self._verify_entries = verify_entries

    def _do_expiration_check(self):
        return False

    def _do_collect(self):
        results = []
        self._send_request(self._uri, results, self._source_type, self._verify_entries)
        return True, results


class BoxEvent(BoxBase):
    time_fmt = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, config, client=None):
        if int(config["record_count"]) > 500:
            config["record_count"] = 500
        super(BoxEvent, self).__init__(config, client)
        self._last_created_before = None
        self._last_created_after = None

    def _do_expiration_check(self):
        return False

    def _get_ckpts(self):
        ckpt = self._get_state()
        if ckpt is None:
            after = datetime.strptime(self.config["created_after"], self.time_fmt)

            before = after + timedelta(hours=24)
            # Taking minimum of before and current time to make sure value of before is less than equal to current time
            before = datetime.strftime(min(before, datetime.utcnow()), self.time_fmt)

            return {
                "created_after": self.config["created_after"],
                "created_before": before,
                "stream_position": 0,
            }
        else:
            before = datetime.utcnow()
            after = before - timedelta(seconds=self.config["interval"])
            before = datetime.strftime(before, self.time_fmt)
            after = datetime.strftime(after, self.time_fmt)
            if ckpt["version"] == 1:
                _LOGGER.debug(
                    "Using the existing checkpoint for input {}: created_after={} and created_before={}".format(
                        self.config["input_name"],
                        ckpt["ckpts"]["created_after"],
                        ckpt["ckpts"]["created_before"],
                    )
                )
                return {
                    "created_after": after,
                    "created_before": before,
                    "stream_position": ckpt["ckpts"],
                }

            if ckpt["ckpts"]["created_before"] == "now":
                now = datetime.strftime(datetime.utcnow(), self.time_fmt)
                ckpt["ckpts"]["created_before"] = now
            _LOGGER.debug(
                "Using the existing checkpoint for input {}: created_after={} and created_before={}".format(
                    self.config["input_name"],
                    ckpt["ckpts"]["created_after"],
                    ckpt["ckpts"]["created_before"],
                )
            )
            return ckpt["ckpts"]

    def _save_ckpts(self, result):
        ckpts = self._get_ckpts()
        now = datetime.utcnow()
        created_after = datetime.strptime(ckpts["created_after"], self.time_fmt)
        created_before = datetime.strptime(self._last_created_before, self.time_fmt)
        aday = timedelta(hours=24)
        thresh_win = timedelta(hours=22)
        entries = result.get("entries", [])
        result_count = len(entries)
        max_count = self.config["record_count"]
        end_invocation = False

        _LOGGER.info("Got %d enterprise event records", result_count)

        def set_created_before(ck, before):
            before = before + aday
            if before >= now:
                ck["created_before"] = "now"
                if (
                    datetime.strptime(self._last_created_before, self.time_fmt)
                    - datetime.strptime(self._last_created_after, self.time_fmt)
                ) < timedelta(hours=24):
                    return True
            else:
                next_before = datetime.strftime(before, self.time_fmt)
                ck["created_before"] = next_before

        # Update stream pos
        ckpts["stream_position"] = result["next_stream_position"]

        if result_count == max_count:
            _LOGGER.info(
                "Continue collecting events for [%s, %s] window",
                ckpts["created_after"],
                self._last_created_before,
            )
        elif 0 < int(result_count) < int(max_count):
            ckpts["created_after"] = self._last_created_before
            end_invocation = set_created_before(ckpts, created_before)
        elif result_count == 0:
            if (
                created_after + thresh_win <= created_before
                and created_after + aday > now
            ):
                # Exception case, no events in thresh_win, rewind to pos to 0
                ckpts["stream_position"] = "0"
                _LOGGER.warn("Rewind pos to 0 to recover stream position")
            elif created_after + aday < now:
                # No history data in this win, progress created_after
                ckpts["created_after"] = self._last_created_before
                end_invocation = set_created_before(ckpts, created_before)
            else:
                # Now has no data, don't progress created_after unless there
                # are no events in more than thresh win
                end_invocation = set_created_before(ckpts, created_before)

        self._save_state(ckpts)
        return end_invocation

    def _get_uri(self, ckpt=None, option=None):
        ckpts = self._get_ckpts()
        self._last_created_after = ckpts["created_after"]
        self._last_created_before = ckpts["created_before"]
        if ckpts["created_after"] == ckpts["created_before"]:
            return None
        else:
            _LOGGER.debug(
                "Old created_after={} and created_before="
                "{}.".format(ckpts["created_after"], ckpts["created_before"])
            )

            ckpts["created_before"] = self.delay_calculator_modified(
                ckpts["created_before"]
            )
            ckpts["created_after"] = self.delay_calculator_modified(
                ckpts["created_after"]
            )

            _LOGGER.debug(
                "Updated created_after={} and created_before="
                "{}.".format(ckpts["created_after"], ckpts["created_before"])
            )
            params = (
                "?stream_type=admin_logs&limit={}&stream_position={}"
                "&created_after={}-00:00&created_before={}-00:00"
            ).format(
                self.config["record_count"],
                ckpts["stream_position"],
                ckpts["created_after"],
                ckpts["created_before"],
            )
            url = "".join((self.config["restapi_base"], "/events", params))
            return url

    def delay_calculator_modified(self, time_stmp):
        """
        Gets the 'event_delay' from config and deducts it from `time_stmp` provided. Used only for Box Events endpoint.
        :param time_stmp:
            Timestamp of the format `"%Y-%m-%dT%H:%M:%S"`
        :type time_stmp:
            `str`
        :rtype:
            `str` of the format `"%Y-%m-%dT%H:%M:%S"`
        """
        try:
            delayed_timestamp = datetime.strptime(time_stmp, self.time_fmt)
        except Exception:
            _LOGGER.error(
                "Failed to convert timestamp:{}. \nTraceback: {}".format(
                    time_stmp, traceback.format_exc()
                )
            )
            return time_stmp
        else:
            delay = self.config.get("event_delay")
            self.config["event_delay"] = int(delay) if delay else 0

            delayed_timestamp = delayed_timestamp - timedelta(
                seconds=self.config.get("event_delay")
            )
            delayed_timestamp = datetime.strftime(delayed_timestamp, self.time_fmt)
            return delayed_timestamp


class BoxUserGroupBase(BoxBase):
    def __init__(self, config, client=None):
        super(BoxUserGroupBase, self).__init__(config, client)

    def _get_ckpts(self):
        """
        @return: offset
        """

        ckpt = self._get_state()
        if ckpt is None or ckpt["ckpts"] is None:
            return 0
        else:
            return ckpt["ckpts"]

    def _save_ckpts(self, result):
        if not result or not result["entries"]:
            _LOGGER.info(
                "All %s records have been collected for input %s",
                self.config["rest_endpoint"],
                self.config["input_name"],
            )
            self._save_state(None)
            return

        if result["total_count"] > result["offset"] + len(result["entries"]):
            offset = result["offset"] + len(result["entries"])
        else:
            offset = result["total_count"]
        self._save_state(offset)


class BoxUser(BoxUserGroupBase):
    def _get_uri(self, ckpt=None, option=None):
        offset = self._get_ckpts()
        params = "?limit={}&offset={}&fields={}".format(
            self.config["record_count"], offset, self.config["user_fields"]
        )
        return "".join((self.config["restapi_base"], "/users", params))


class BoxGroup(BoxUserGroupBase):
    def _get_uri(self, ckpt=None, option=None):
        offset = self._get_ckpts()
        params = "?limit={}&offset={}".format(self.config["record_count"], offset)
        return "".join((self.config["restapi_base"], "/groups", params))


class BoxFolder(BoxBase):
    count_threshold = 10000
    time_threshold = 10 * 60

    def __init__(self, config, client=None):
        super(BoxFolder, self).__init__(config, client)

        self._file_count = 0
        self._folder_count = 0
        self._file_total_count = 0
        self._folder_total_count = 0
        self._task_count = 0
        self._collaboration_count = 0

    def _get_uri(self, ckpt=None, option=None):
        if ckpt["type"] == "folder":
            if option is None:
                params = "/folders/{}/items?limit={}&offset={}&fields={}"
                params = params.format(
                    ckpt["id"],
                    self.config["record_count"],
                    int(ckpt.get("offset", 0)),
                    self.config["folder_fields"],
                )
            elif option == "collaborations":
                params = "/folders/{}/collaborations?fields={}".format(
                    ckpt["id"], self.config["collaboration_fields"]
                )
            else:
                assert 0  # nosemgrep: gitlab.bandit.B101
        else:
            if option is None:
                params = "/files/{}?fields={}".format(
                    ckpt["id"], self.config["file_fields"]
                )
            elif option == "tasks":
                params = "/files/{}/tasks?fields={}".format(
                    ckpt["id"], self.config["task_fields"]
                )
            elif option == "versions":
                params = "/files/{}/versions".format(ckpt["id"])
            elif option == "comments":
                params = "/files/{}/comments?fields={}".format(
                    ckpt["id"], self.config["comment_fields"]
                )
            else:
                assert 0  # nosemgrep: gitlab.bandit.B101
        uri = "".join((self.config["restapi_base"], params))
        return uri

    def _get_ckpts(self):
        ckpt = self._get_state()
        is_start = False
        if not ckpt or ckpt["ckpts"] is None:
            ckpts = [{"type": "folder", "id": 0, "offset": 0}]
            _LOGGER.info("Start from root")
            is_start = True
        else:
            ckpts = ckpt["ckpts"]
            _LOGGER.info(
                "Pickup execution of input {} from {}".format(
                    self.config.get("name"), ckpts[-1]
                )
            )
        return ckpts, is_start

    def _handle_file(self, uri, ckpts, results):
        file_results = []
        err, _ = self._send_request(uri, file_results, "file", False)

        if utils.is_true(self.config["collect_file"]):
            self._file_count += 1
            if not err and file_results:
                results.extend(file_results)

        if err in (403, 404):
            ckpts.pop(-1)
            return

        # Collect tasks/comments for this file
        if utils.is_true(self.config["collect_task"]):
            tasks = (("tasks", "fileTask"), ("comments", "fileComment"))
            for endpoint, src_type in tasks:
                uri = self._get_uri(ckpts[-1], endpoint)
                if not self._run_job_async(uri, src_type, True, endpoint):
                    self._send_request(uri, results, src_type)
        ckpts.pop(-1)
        return

    def _handle_folder_result(self, res, results, new_entries):
        folders = []
        for entry in res["entries"]:
            obj = {"type": entry["type"], "id": entry["id"]}
            if entry["type"] == "folder":
                obj["has_collaborations"] = entry.get("has_collaborations")
                if utils.is_true(self.config["collect_folder"]):
                    folders.append(entry)
            new_entries.append(obj)

        if folders:
            results.append(
                _JObject(
                    {"entries": folders},
                    self.config["account_id"],
                    self.config["url"],
                    "folder",
                    self.config["account"],
                    self.config["input_name"],
                )
            )

    def _handle_folder(self, uri, ckpts, results, new_entries):
        err, res = self._send_request(uri, results, "folder", False, False)

        if err:
            if err in (self._UNKNOWN, 401):
                return False

            ckpts.pop(-1)
            return True

        self._handle_folder_result(res, results, new_entries)
        total, offset = res["total_count"], res["offset"]
        if res["entries"] and total > offset + len(res["entries"]):
            ckpts[-1]["offset"] = offset + res["limit"]
            del res
            return False
        else:
            if utils.is_true(self.config["collect_folder"]):
                self._folder_count += 1
            if utils.is_true(self.config["collect_collaboration"]) and ckpts[-1].get(
                "has_collaborations"
            ):
                uri = self._get_uri(ckpts[-1], "collaborations")
                self._send_request(uri, results, "folderCollaboration")
            ckpts.pop(-1)
            ckpts.extend(new_entries)
            del new_entries[:]
            return True

    def _run_job_async(self, uri, src_type, verify_entries, endpoint="files"):
        if not self.config["use_thread_pool"]:
            return False

        new_config = {}
        new_config.update(self.config)
        new_config["name"] = new_config["name"].replace("folders", endpoint)
        task = BoxFile(uri, src_type, verify_entries, new_config, self.client)
        try:
            thread_pool.task_queue.put(task)
        except queue.Full as e:
            _LOGGER.error(
                "Error while running job asynchronously: {0}. Stack trace: {1}".format(
                    e, traceback.format_exc()
                )
            )
            return False
        except Exception as e:
            _LOGGER.error(
                "Error while running job asynchronously: {0}. Stack trace: {1}".format(
                    e, traceback.format_exc()
                )
            )
            return False
        return True

    def _reach_threshold(self, start_time, ckpts):
        if (
            self._folder_count + self._file_count >= self.count_threshold
            or time.time() - start_time >= self.time_threshold
        ):
            return True
        return False

    def _do_collect(self):
        ckpts, is_start = self._get_ckpts()
        update_time = False
        # update start timestamp if collecting from root
        if is_start:
            update_time = True
        results, new_entries, start_time = [], [], time.time()

        self._file_count, self._folder_count = 0, 0
        while ckpts:
            uri = self._get_uri(ckpts[-1])
            if ckpts[-1]["type"] == "folder":
                self._handle_folder(uri, ckpts, results, new_entries)
            else:
                self._handle_file(uri, ckpts, results)
            if self._reach_threshold(start_time, ckpts):
                _LOGGER.debug("Reached threshold, breaking")
                break

        self._file_total_count += self._file_count
        self._folder_total_count += self._folder_count
        _LOGGER.info(
            "Collect %d folders, %d files in %f seconds. For now, "
            "%d folders, %d files have been collected.",
            self._folder_count,
            self._file_count,
            time.time() - start_time,
            self._folder_total_count,
            self._file_total_count,
        )

        if ckpts:
            # We are in the middle of collecting, reach thresholds
            if update_time:
                self._save_state(ckpts, start_time)
            else:
                self._save_state(ckpts)
            return False, results
        else:
            _LOGGER.info(
                "All directories and files have been collected for input: {}.".format(
                    self.config["input_name"]
                )
            )
            if update_time:
                self._save_state(None, start_time)
            else:
                self._save_state(None)
            return True, results
