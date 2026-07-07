#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import base64
import json
import os
import os.path as op
import re
import sys
import traceback
from datetime import datetime, timedelta
import requests
import signal
import snow_consts as sc
import snow_oauth_helper as soauth
import snow_checkpoint
from snow_utility import (
    get_sslconfig,
    build_proxy_info,
    add_ucc_error_logger,
    log_events_ingested,
    create_log_object,
)

from solnlib.modular_input import event_writer
from solnlib import log, utils

COMMON_LOGGER = create_log_object("splunk_ta_snow_main")

global_input_name = None
global_table_name = None
global_timefield = None
global_jobs = None
event_ingested = False
checkpoint_updated = False


class Snow(object):
    _SUPPORTED_DISPLAY_VALUES = ["false", "true", "all"]

    def __init__(self, config, logger=COMMON_LOGGER):
        """
        @config: dict like, should have url, username, checkpoint_dir,
                 since_when, proxy_url, proxy_username, proxy_password
        """

        host = config["url"]
        self.auth_type = config["auth_type"]
        self.logger = logger
        if isinstance(host, str):
            prefix = re.search("^https?://", host)
            if not prefix:
                host = "https://{0}".format(host)

            if not host.endswith("/"):
                host = "{0}/".format(host)
        else:
            self.logger.critical(
                "Please check your splunk_ta_snow_account.conf, the 'url' "
                "value is missing. Please add valid 'url' in "
                "splunk_ta_snow_account.conf and restart your instance. Exiting TA."
            )
            sys.exit(1)
        if self.auth_type == "basic" and (
            not config["username"] or not config["password"]
        ):
            self.logger.critical(
                "Please check your splunk_ta_snow_account.conf, the 'username' and/or "
                "'password' value are missing. Please recreate the input as this "
                "input is malformed. Exiting TA."
            )
            sys.exit(1)

        elif self.auth_type == "oauth" and (
            not config["access_token"]
            or not config["refresh_token"]
            or not config["client_id"]
            or not config["client_secret"]
        ):
            self.logger.critical(
                "Please check your splunk_ta_snow_account.conf, one or more of the required parameters: 'client_id',"
                " 'client_secret', 'access_token', 'refresh_token' are missing. Please recreate the input as this "
                "input is malformed. Exiting TA."
            )
            sys.exit(1)
        elif self.auth_type == "oauth_client_credentials" and (
            not config["access_token"]
            or not config["client_id_oauth_credentials"]
            or not config["client_secret_oauth_credentials"]
        ):
            self.logger.critical(
                "Please check your splunk_ta_snow_account.conf, one or more of the required parameters: 'client_id',"
                " 'client_secret', 'access_token' are missing. Please recreate the input as this "
                "input is malformed. Exiting TA."
            )
            sys.exit(1)

        self.host = host
        self.account = config["account"]

        # For auth_type="basic", username and password will be required for data collection
        if self.auth_type == "basic":
            self.username = config["username"]
            self.password = config["password"]
        # For auth_type="outh", access_token and refresh_token will be required for data collection
        elif self.auth_type == "oauth":
            self.oauth_access_token = config["access_token"]
            self.oauth_refresh_token = config["refresh_token"]
        else:
            self.oauth_access_token = config["access_token"]

        if config["since_when"] == "now":
            now = datetime.utcnow() - timedelta(7)
            self.since_when = datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
        else:
            self.since_when = config["since_when"]
        self.id_field = config.get("id_field") or "sys_id"
        self.filter_data = config.get("filter_data", "")
        self.include_list = (config.get("include") or "").replace(" ", "")
        self.config = config
        self.context = {}
        self._display_value = self._get_display_value(config)

        # Kv-store checkpoint handler for the input
        self.checkpoint_handler = snow_checkpoint.CheckpointHandler(
            collection_name=sc.CHECKPOINT_COLLECTION_NAME,
            session_key=self.config["session_key"],
            logger=self.logger,
            input_name=self.config["name"],
            table=self.config["table"],
            timefield=(self.config.get("timefield") or "sys_updated_on"),
        )

    def exit_gracefully(self, signum, frame):
        global global_input_name
        global global_timefield
        global global_jobs
        global event_ingested
        global checkpoint_updated
        global global_table_name
        self.logger.info(
            "Execution about to get stopped for input '{}' due to SIGTERM.".format(
                global_input_name
            )
        )
        try:
            if event_ingested and not checkpoint_updated:
                self.logger.info(
                    "Updating the checkpoint before exiting gracefully for the input: {}".format(
                        global_input_name
                    )
                )
                _ = self._write_checkpoint(
                    global_input_name, global_table_name, global_timefield, global_jobs
                )
                self.logger.info(
                    "Updated the checkpoint successfully before exiting for the input: {}".format(
                        global_input_name
                    )
                )
        except Exception as exc:
            msg = f"Unable to save checkpoint before SIGTERM termination. Error: {exc}"
            add_ucc_error_logger(
                logger=self.logger,
                logger_type=sc.GENERAL_EXCEPTION,
                exception=exc,
                msg_before=msg,
            )

        sys.exit(0)

    def _get_display_value(self, config):
        dv = config.get("display_value", "")
        if utils.is_false(dv):
            return "false"
        if utils.is_true(dv):
            return "true"
        if dv and dv in self._SUPPORTED_DISPLAY_VALUES:
            return dv
        return sc.DEFAULT_DISPLAY_VALUE

    @staticmethod
    def _rebuild_json_node(json_obj):
        # For latest api, field is returned as dict which contains
        # value and display_value.
        node = {}
        for k, v in json_obj.items():
            if not isinstance(v, dict):
                node[k] = v
            else:
                node[k] = v.get("value", "")
                node["dv_%s" % k] = v.get("display_value", "")
        return node

    def _flat_json_records(self, records):
        self.logger.debug("Start to rebuild json content.")
        if self._display_value != "all":
            # For old api, field and display value which starts with 'dv_'
            # are returned together. We don't need to do anything.
            return records
        results = []
        for item in records:
            results.append(self._rebuild_json_node(item))
        self.logger.debug("Rebuild json content end.")
        return results

    def _validate_time_field_in_records(self, records, timefield) -> False:
        self.logger.debug(
            f"Validating if timefield: {timefield} is present in fetched events."
        )
        for obj in records:
            try:
                obj[timefield]
                return True
            except KeyError:
                continue
        return False

    def collect_data(
        self,
        table,
        timefield,
        input_name,
        host,
        excludes,
        delay,
        count=sc.DEFAULT_RECORD_LIMIT,
    ):
        # Creating an object of the ClassicEventWriter to write events
        ew = event_writer.ClassicEventWriter()

        global global_input_name
        global global_timefield
        global global_jobs
        global checkpoint_updated
        global global_table_name
        global event_ingested
        global_timefield = timefield
        global_input_name = input_name
        global_table_name = table
        assert (  # nosemgrep: gitlab.bandit.B101 - additional check for table and timefield
            table and timefield
        )
        if not count:
            count = sc.DEFAULT_RECORD_LIMIT
        # setting the upper limit for the time range (FROM - TO) to collect data.
        now = datetime.utcnow() - timedelta(seconds=int(delay))
        now = datetime.strftime(now, "%Y-%m-%d+%H:%M:%S")
        end_datetime = utils.datetime_to_seconds(
            datetime.strptime(now, "%Y-%m-%d+%H:%M:%S")
        )
        checkpoint_name = ".".join((input_name, table, timefield))

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

        # for windows machine
        if os.name == "nt":
            signal.signal(signal.SIGBREAK, self.exit_gracefully)  # pylint:disable=E1101

        total_events = 0
        while True:
            _write_checkpoint_status = 0

            (
                last_timestamp,
                last_record_id,
            ) = self._read_last_collection_time_and_offset(input_name, table, timefield)
            # setting the query for time range and ordering of events in the servicenow table
            # e.g. sys_updated_on=2023-11-20+12:47:15^sys_id>SYS_ID^NQsys_updated_on>2023-11-20+12:47:15^sys_updated_on<2023-11-24+00:00:00^ORDERBYsys_updated_on,sys_id
            # if value for sys_id(last_record_id) is not present, the query will not have sys_id>SYS_ID part to avoid comparing to empty value, sys_id is used as an example here due to it being default id_field
            if last_record_id:
                params = "{0}={1}^{2}>{3}^NQ{0}>{1}^{0}<{4}^ORDERBY{0},{2}".format(
                    timefield, last_timestamp, self.id_field, last_record_id, now
                )
            else:
                params = "{0}={1}^NQ{0}>{1}^{0}<{3}^ORDERBY{0},{2}".format(
                    timefield, last_timestamp, self.id_field, now
                )
            _, content = self._do_collect(table, params, limit=count)
            if not content:
                return
            try:
                jobjs = self._json_to_objects(content, self.logger)
            except Exception as e:
                msg = (
                    "Failure occurred while getting records for the input: {3} "
                    "from the table: {1} of the servicenow host: {0}. "
                    "The reason for failure= {2}. Contact Splunk administrator "
                    "for further information.".format(
                        self.host, table, str(e), input_name
                    )
                )
                add_ucc_error_logger(
                    logger=self.logger,
                    logger_type=sc.GENERAL_EXCEPTION,
                    exception=e,
                    msg_before=msg,
                )
                return
            records = jobjs.get("result")

            if jobjs.get("error"):
                self.logger.error(
                    "Failure occurred while getting records for the input: {3} "
                    "from the table: {1} of the servicenow host: {0}. "
                    "The reason for failure= {2}. Contact Splunk administrator "
                    "for further information.".format(
                        self.host, table, str(jobjs["error"]), input_name
                    )
                )
                return

            if not records:
                # no records are returned by the API call.
                self.context[checkpoint_name]["last_collection_time"] = now.replace(
                    "+", " "
                )
                self.context[checkpoint_name]["last_record_id"] = ""
                _write_checkpoint_status = self._write_checkpoint(
                    input_name, table, timefield, records
                )
                if not _write_checkpoint_status:
                    return None
                self.logger.info(
                    "Data collection completed for input {0}. Got a total of {1} records from {2}{3}.".format(
                        input_name, total_events, self.host, table
                    )
                )
                return
            jobjs = self._flat_json_records(records)
            # Setting checkpoint_updated = False just before ingesting the events
            # for better handling of the SIGTERM.
            checkpoint_updated = False
            self._write_events_to_event_writer(
                jobjs,
                table,
                timefield,
                input_name,
                host,
                excludes,
                ew,
                end_datetime,
                delay,
            )
            total_events += len(jobjs)

            if self.context[checkpoint_name].get("last_time_records") and jobjs:
                # setting offset using older version of checkpoint if any exist.
                # this is used to minimize data duplication during upgrade.
                (
                    self.context[checkpoint_name]["last_time_records"],
                    jobjs,
                ) = self._remove_collected_records(
                    self.context[checkpoint_name]["last_time_records"], jobjs
                )
            global_jobs = jobjs
            _write_checkpoint_status = self._write_checkpoint(
                input_name, table, timefield, jobjs
            )

            if not _write_checkpoint_status:
                return None
            else:
                checkpoint_updated = True
                # Setting event_ingested = False just after updating the checkpoint
                # for better handling of the SIGTERM.
                event_ingested = False

            self.logger.info(
                "Data collection is in progress for input {0}. Got {1} records for the table: {3} from {2}.".format(
                    input_name, len(jobjs), self.host, table
                )
            )

    def _write_events_to_event_writer(
        self,
        jobjs,
        table,
        timefield,
        input_name,
        host,
        excludes,
        ew,
        end_datetime,
        delay,
    ):
        """
        This method writes events to the eventwriter.
        :param jobjs: the json objects or events to be ingested into splunk.
        :param table: the servicenow table from which data is to be collected.
        :param timefield: the field used to checkpoint the modular input.
        :param input_name: the name of the input configured.
        :param host: the host to be assigned to the collected events.
        :param excludes: param to format events.
        :param ew: Object of the event writer from solnlib's ClassicEventWriter.
        :param end_datetime: Latest timestamp up to which data is being collected
        """
        global event_ingested

        self.logger.info(
            "Proceeding to add events to Event Writer for input '{}'".format(input_name)
        )
        checkpoint_name = ".".join((input_name, table, timefield))
        successfully_written_events_count = 0
        prev_timestamp = None
        if jobjs:
            for obj in jobjs:
                try:
                    try:
                        timestamp = datetime.strptime(
                            obj[timefield], "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        timestamp = datetime.utcnow() - timedelta(seconds=int(delay))
                    except KeyError as e:
                        if not prev_timestamp:
                            if not self._validate_time_field_in_records(
                                jobjs, timefield
                            ):
                                msg = "'{}' field is missing in the data collected for '{}' input. Please ensure the provided timefield is correct and present in the table records in ServiceNow.".format(
                                    timefield, input_name
                                )
                                add_ucc_error_logger(
                                    logger=self.logger,
                                    logger_type=sc.GENERAL_EXCEPTION,
                                    exception=e,
                                    msg_before=msg,
                                )
                                sys.exit(0)
                            prev_timestamp = datetime.utcnow() - timedelta(
                                seconds=int(delay)
                            )
                            self.logger.warn(
                                "Timefield: {} not found in the event. Defaulting to current UTC time({}).".format(
                                    timefield, prev_timestamp
                                )
                            )
                        else:
                            self.logger.warn(
                                "Timefield: {} not found in the event. Defaulting to timestamp of previous event({}).".format(
                                    timefield, prev_timestamp
                                )
                            )
                        timestamp = prev_timestamp
                    tag_vals = ",".join(
                        (
                            '{0}="{1}"'.format(k, str(v).replace('"', ""))
                            for k, v in obj.items()
                            if k not in excludes
                        )
                    )
                    _time = utils.datetime_to_seconds(timestamp)
                    if ((timefield in obj) and _time < end_datetime) or not (
                        timefield in obj
                    ):
                        event = ew.create_event(
                            stanza=f"snow://{input_name}",
                            time=_time,
                            source=self.host,
                            sourcetype=f"snow:{table}",
                            host=host,
                            index=self.config.get("index", "default"),
                            data=f'endpoint="{self.host}",{tag_vals}',
                        )
                        ew.write_events([event])
                        event_ingested = True
                        successfully_written_events_count += 1
                        prev_timestamp = timestamp
                        if timefield in obj:
                            self.context[checkpoint_name]["last_collection_time"] = obj[
                                timefield
                            ]
                            self.context[checkpoint_name]["last_record_id"] = obj[
                                self.id_field
                            ]
                    else:
                        self.logger.debug(
                            "Received record({}) with {}={}. Skipping the ingestion.".format(
                                obj[self.id_field], timefield, obj[timefield]
                            )
                        )
                except Exception as e:
                    msg = "Some exception occurred while writing event to event writer for the input '{}'. However, successfully wrote '{}' events. The reason for failure = {}".format(
                        input_name,
                        successfully_written_events_count,
                        traceback.format_exc(),
                    )
                    log_events_ingested(
                        logger=self.logger,
                        modular_input_name=f"snow://{table}",
                        sourcetype=f"snow:{table}",
                        n_events=successfully_written_events_count,
                        index=self.config.get("index", "default"),
                        account=self.config["account"],
                        host=host,
                        license_usage_source=self.host,
                    )
                    add_ucc_error_logger(
                        logger=self.logger,
                        logger_type=sc.CONNECTION_ERROR,
                        exception=e,
                        msg_before=msg,
                    )
                    return
        self.logger.info(
            "Successfully written '{}' events to Event Writer for the input '{}'".format(
                successfully_written_events_count, input_name
            )
        )
        log_events_ingested(
            logger=self.logger,
            modular_input_name=f"snow://{table}",
            sourcetype=f"snow:{table}",
            n_events=successfully_written_events_count,
            index=self.config.get("index", "default"),
            account=self.config["account"],
            host=host,
            license_usage_source=self.host,
        )
        return

    def _do_collect(self, table, params, limit):
        rest_uri = self._get_uri(table, params, limit)
        proxy_info = build_proxy_info(self.config)
        session_key = self.config["session_key"]
        sslconfig = get_sslconfig(self.config, session_key, self.logger)
        response, content = None, None
        try:
            for retry in range(3):
                if retry > 0:
                    self.logger.info("Retry count: {}/3".format(retry + 1))
                self.logger.info("Initiating request to {}".format(rest_uri))
                headers = {}
                if self.auth_type == "basic":
                    credentials = base64.urlsafe_b64encode(
                        (
                            "%s:%s" % (self.config["username"], self.config["password"])
                        ).encode("UTF-8")
                    ).decode("ascii")

                    headers = {
                        "Accept-Encoding": "gzip",
                        "Accept": "application/json",
                        "Authorization": "Basic %s" % credentials,
                    }
                else:
                    headers = {
                        "Accept-Encoding": "gzip",
                        "Accept": "application/json",
                        "Authorization": "Bearer %s" % self.oauth_access_token,
                    }
                # semgrep ignore reason: we have custom handling for unsuccessful HTTP status codes
                response = requests.request(  # nosemgrep: python.requests.best-practice.use-raise-for-status.use-raise-for-status  # noqa: E501
                    "GET",
                    rest_uri,
                    headers=headers,
                    proxies=proxy_info,
                    timeout=120,
                    verify=sslconfig,
                )

                content = response.content
                if response.status_code not in (200, 201):
                    self.logger.error(
                        "Failure occurred while connecting to {0}. The reason for failure={1}.".format(
                            rest_uri, response.reason
                        )
                    )

                    # If HTTP status = 401, there is a possibility that access token is expired
                    if response.status_code == 401 and self.auth_type in [
                        "oauth",
                        "oauth_client_credentials",
                    ]:
                        self.logger.error(
                            "Failure potentially caused by expired access token. Regenerating access token."
                        )

                        snow_oauth = soauth.SnowOAuth(
                            self.config,
                            "splunk_ta_snow_main_{}".format(global_input_name),
                        )
                        update_status, _ = snow_oauth.regenerate_oauth_access_tokens()

                        if update_status:
                            token_details = snow_oauth.get_account_oauth_tokens(
                                session_key, self.account
                            )

                            # Reloading the class variables with the new tokens generated
                            self.oauth_access_token = token_details["access_token"]
                            self.config["access_token"] = token_details["access_token"]

                            if self.auth_type == "oauth":
                                self.oauth_refresh_token = token_details[
                                    "refresh_token"
                                ]
                                self.config["refresh_token"] = token_details[
                                    "refresh_token"
                                ]
                            continue
                        else:
                            self.logger.error(
                                "Unable to generate a new access token. Failure potentially caused by "
                                "the expired refresh token. To fix the issue, reconfigure the account."
                            )
                            break
                    # Error is not related to access token expiration. Hence breaking the loop
                    else:
                        break
                # Response obtained successfully. Hence breaking the loop
                else:
                    break

        except Exception as e:
            msg = "Failure occurred while connecting to {0}. The reason for failure={1}.".format(
                rest_uri, traceback.format_exc()
            )
            add_ucc_error_logger(
                logger=self.logger,
                logger_type=sc.CONNECTION_ERROR,
                exception=e,
                msg_before=msg,
            )

        self.logger.info("Ending request to {}".format(rest_uri))
        return response, content

    @staticmethod
    def _json_to_objects(json_str, logger=COMMON_LOGGER):
        json_str = json_str.decode()
        json_object = {}
        try:
            json_object = json.loads(json_str)
        except ValueError as e:
            msg = "Obtained an invalid json string while parsing. Got value of type {}. Traceback : {}".format(
                type(json_str), traceback.format_exc()
            )
            add_ucc_error_logger(
                logger=logger,
                logger_type=sc.GENERAL_EXCEPTION,
                exception=e,
                msg_before=msg,
            )
            raise ValueError("Received an invalid JSON string while parsing.")
        except Exception as e:
            msg = "Error occured while parsing json string. Got value of type {} . The reason for failure= {}".format(
                type(json_str), traceback.format_exc()
            )
            add_ucc_error_logger(
                logger=logger,
                logger_type=sc.GENERAL_EXCEPTION,
                exception=e,
                msg_before=msg,
            )

        return json_object

    def _remove_collected_records(self, last_time_records, jobjs):
        """
        This method removes records already collected in the last run before the upgrade
        from addon version 6.0.1 or earlier.
        :param last_time_records: list of values id_field of lastest timestamp records collected in last before upgrade.  # noqa: E501
        :param jobjs: the json objects or events to be ingested into splunk
        :return last_time_records: list of values id_field of lastest timestamp records collected in last before upgrade.
        :return jobjs: the json objects or events to be ingested into splunk
        """

        records_to_be_removed = []

        for obj in jobjs:
            if obj[self.id_field] in last_time_records:
                records_to_be_removed.append(obj[self.id_field])

        if records_to_be_removed:
            self.logger.debug(
                "Duplicate records found : {}".format(records_to_be_removed)
            )
            jobjs = [
                jobj
                for jobj in jobjs
                if jobj[self.id_field] not in records_to_be_removed
            ]
            last_time_records = [
                last_time_record
                for last_time_record in last_time_records
                if last_time_record not in records_to_be_removed
            ]
            self.logger.debug("Removed duplicate records.")
        return last_time_records, jobjs

    def _get_uri(self, table, params, limit):
        endpoint = (
            "api/now/table/{}?sysparm_display_value={}" "&sysparm_limit={}"
        ).format(table, self._display_value, limit)

        if self.include_list:
            combine_list = self.id_field.replace(" ", "").split(",")
            combine_list.extend(
                (self.config.get("timefield") or "sys_updated_on")
                .replace(" ", "")
                .split(",")
            )

            # when the process reboots, include_list is str, and otherwise a list
            self.include_list = (
                self.include_list.split(",")
                if isinstance(self.include_list, str)
                else self.include_list
            )
            self.include_list = [
                item for item in self.include_list if item not in combine_list
            ]
            self.include_list.extend(combine_list)

            endpoint = "".join(
                (endpoint, "&sysparm_fields=", ",".join(self.include_list))
            )

        if params:
            if self.filter_data:
                queries = params.split("^NQ")
                params = (
                    "&sysparm_exclude_reference_link=true"
                    "&sysparm_query={0}^{1}^NQ{0}^{2}"
                ).format(self.filter_data, queries[0], queries[1])

            else:
                params = (
                    "&sysparm_exclude_reference_link=true" "&sysparm_query={}"
                ).format(params)
        if params is None:
            if self.filter_data:
                params = (
                    "&sysparm_exclude_reference_link=true" "&sysparm_query={}"
                ).format(self.filter_data)

            else:
                params = ""
        rest_uri = "".join((self.host, endpoint, params))
        return rest_uri

    def _read_last_collection_time_and_offset(self, input_name, table, timefield):
        checkpoint_name = ".".join((input_name, table, timefield))
        if not self.context.get(checkpoint_name, None):
            self.logger.debug(
                "Checkpoint {} not in cache, reloading from kv-store checkpoint.".format(
                    checkpoint_name
                )
            )
            ckpt = self._read_last_checkpoint(checkpoint_name)
            self.logger.debug("Got checkpoint value as {}".format(json.dumps(ckpt)))
            if not ckpt:
                self.context[checkpoint_name] = {
                    "last_collection_time": self.since_when,
                    "last_record_id": "",
                }

        return self.context[checkpoint_name]["last_collection_time"].replace(
            " ", "+"
        ), self.context[checkpoint_name].get("last_record_id", "")

    def _read_last_checkpoint(self, input_name):
        try:
            ckpt = self.checkpoint_handler.get_kv_checkpoint()
            if ckpt:
                assert (  # nosemgrep: gitlab.bandit.B101 - additional check for checkpoint existence
                    ckpt["version"] == 1
                )
                self.context[input_name] = ckpt
            return ckpt
        except Exception as e:
            msg = "Error while reading last checkpoint for input {}. {}".format(
                input_name, traceback.format_exc()
            )
            add_ucc_error_logger(
                logger=self.logger,
                logger_type=sc.GENERAL_EXCEPTION,
                exception=e,
                msg_before=msg,
            )

            raise

    def _write_checkpoint(self, input_name, table, timefield, jobjs):
        checkpoint_name = ".".join((input_name, table, timefield))
        self.logger.debug(
            "Proceeding to write checkpoint for input: {}".format(input_name)
        )

        try:
            ckpt = {
                "version": 1,
                "last_collection_time": self.context[checkpoint_name][
                    "last_collection_time"
                ],
                "last_record_id": self.context[checkpoint_name]["last_record_id"],
            }
            if self.context[checkpoint_name].get("last_time_records"):
                ckpt["last_time_records"] = self.context[checkpoint_name][
                    "last_time_records"
                ]

            self.checkpoint_handler.update_kv_checkpoint(ckpt)
            self.context[checkpoint_name] = ckpt
            self.logger.debug(
                "Checkpoint written successfully for input: {}".format(input_name)
            )
            return 1

        except Exception as e:
            msg = "Error while writing checkpoint for input {}. {}".format(
                input_name, traceback.format_exc()
            )
            add_ucc_error_logger(
                logger=self.logger,
                logger_type=sc.GENERAL_EXCEPTION,
                exception=e,
                msg_before=msg,
            )

    def is_alive(self):
        return 1
