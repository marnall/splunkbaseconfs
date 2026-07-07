import json
import time
import traceback
import urlparse
from threading import Lock

import py42.util
from c42fedextractor.common import SecurityEventExtractorHandlers
from c42fedextractor.event_detail import SecurityEventDetailExtractor
from py42.sdk.util.queued_logger import QueuedLogger

_EVENT_TYPES = ["DEVICE_APPEARED",
                "DEVICE_DISAPPEARED",
                "DEVICE_FILE_ACTIVITY",
                "PERSONAL_CLOUD_FILE_ACTIVITY",
                "RESTORE_JOB",
                "RESTORE_FILE",
                "FILE_OPENED",
                "RULE_MATCH"]


def _process_security_events(e):
    # MUST RETURN A LIST OF EVENTS
    if "timestamp" in e:
        if len("{}".format(e["timestamp"])) > 10:
            e["timestamp"] = int("{}".format(e["timestamp"])[0:10])
    return [e]


def get_plan_id_from_cursor(cursor):
    return cursor.split(":")[0]


def get_cursor_entry_for_plan(cursor_entries, plan_id):
    for entry in cursor_entries:
        if entry["plan_id"] == plan_id:
            return entry
    return None


class SplunkSecurityEventFetcherHandlers(SecurityEventExtractorHandlers):
    def __init__(self, logger, utils, event_response_handler, logging_class):
        self._logger = logger
        self._utils = utils
        self._processed_users_log = QueuedLogger(logging_class().get_logger("Code42ForSplunk", "processed_users"))
        self._total_events = 0
        self._event_response_handler = event_response_handler
        self._event_count_lock = Lock()

    def get_processed_event_count(self):
        return self._total_events

    def kv_store_user_get(self, user_uid):
        try:
            search_query = {"$or": [{"_key": user_uid}]}
            internal_uuid_checkpoint = [x for x in self._utils.get_kvstore_data("mi_code42_users",
                                                                                json.dumps(search_query))]
            self._logger.debug(
                "action=kv_store_user_get userUid={} response={}".format(user_uid,
                                                                         json.dumps(internal_uuid_checkpoint)))
            if len(internal_uuid_checkpoint) >= 1:
                return internal_uuid_checkpoint[0]
            return {}
        except Exception as e:
            trace = traceback.format_exc()
            self._logger.error("Error occurred while getting user from kvstore: " + trace)

    def kv_store_user_set(self, user=None):
        try:
            self._logger.debug("action=starting timer={} user={}".format(time.time(), json.dumps(user)))
            kv_object = {"user_uuid": user.get("userId"), "last_stored": time.time(),
                         "active": user.get("active"), "last_login": user.get("lastLoginDate", "null"),
                         "user_email": user.get("email", "N/A"), "_key": user.get("userUid")}
            self._logger.debug("action=setting_object timer={} kv_object={}".format(time.time(), kv_object))
            self._utils.update_kvstore_data("mi_code42_users", user.get("_key", ""), kv_object)
            self._logger.debug("action=ending timer={}".format(time.time()))
        except Exception as e:
            trace = traceback.format_exc()
            self._logger.error("Error occurred while adding user to kvstore:" + trace)

    def process_response(self, response, user):
        if response.content:
            ret_events = []
            host_address = urlparse.urljoin(response.request.url, "/")
            security_events = py42.util.get_obj_from_response(response, "securityDetectionEvents")
            if len(security_events) > 0:
                [ret_events.extend(_process_security_events(x)) for x in security_events]
                self._event_count_lock.acquire()
                self._total_events += len(ret_events)
                self._event_count_lock.release()
                message = "received new events for user. username={} num_events={} storage_node={}"
                self._processed_users_log.info(message.format(user.get("username"), len(ret_events), host_address))
                self._event_response_handler("code42:security", ret_events)

    def should_process_user(self, user):
        try:
            is_active = user.get("active")
            stored_info = self.kv_store_user_get(user.get("userUid"))
            if "_key" in stored_info:
                user["_key"] = stored_info["_key"]
            self.kv_store_user_set(user=user)
            self._logger.debug("action=should_process_user stored_information={}".format(json.dumps(stored_info)))
            message = "action=checking_active is_active={} stored_active={} not_is_active={}"
            self._logger.debug(message.format(is_active, stored_info.get("active"), not is_active))
            if is_active == stored_info.get("active") and not is_active:
                self._logger.debug("action=returning value=False")
                return False
            else:
                self._logger.debug("action=returning value=True")
                return True
        except Exception as e:
            trace = traceback.format_exc()
            self._logger.error("Error occurred while checking if user should be processed: " + trace)
            return False

    def handle_security_event_error(self, ex):
        self._logger.error("Error occurred while fetching security events: {0}".format(ex))

    def _get_current_cursor_entries(self, user):
        try:
            user_id = user.get("userId")
            search_query = {"user_uuid": user_id}
            cursor_entries = self._utils.get_kvstore_data("mi_code42_cursor", json.dumps(search_query))
            if cursor_entries is None:
                cursor_entries = []
            self._logger.debug("action=got_cursor user_id={0}, cursor_entries={1}".format(user_id, cursor_entries))
            return cursor_entries
        except Exception as e:
            trace = traceback.format_exc()
            self._logger.error("Error occurred while attempting to fetch cursor: " + trace)

    def get_starting_cursor_positions(self, user):
        message = "user is being checked for new events. username={0}, userId={1}"
        self._processed_users_log.info(message.format(user.get("username"), user.get("userId")))
        return [entry["cursor"] for entry in self._get_current_cursor_entries(user)]

    def record_cursor_position(self, user, cursor):
        try:
            plan_id = get_plan_id_from_cursor(cursor)
            user_id = user.get("userId")
            self._logger.debug("action=set_cursor_kvstore plan={} user={} cursor={}".format(plan_id, user_id, cursor))
            if plan_id is None or user_id is None or cursor is None or cursor == "":
                error = "action=set_cursor_kvstore Unable to save cursor. " + \
                        "One or more of plan_id, user_id, and cursor are None. plan_id={} user_id={} cursor={}"
                self._logger.error(error.format(plan_id, user_id, cursor))
                return None
            key = ""
            existing_cursor_entries = self._get_current_cursor_entries(user)
            existing_cursor_entry = get_cursor_entry_for_plan(existing_cursor_entries, plan_id)
            if existing_cursor_entry:
                key = existing_cursor_entry.get("_key", "")

            if key == "":
                resp = self._utils.set_kvstore_data("mi_code42_cursor",
                                                    {"_key": key, "plan_id": plan_id, "user_uuid": user_id,
                                                     "cursor": cursor, "last_updated": time.time()})
                self._logger.debug(
                    "action=set_cursor_kvstore plan={} user={} cursor={} resp={}".format(plan_id, user_id,
                                                                                         cursor, resp))
            else:
                resp = self._utils.update_kvstore_data("mi_code42_cursor", key,
                                                       {"plan_id": plan_id, "user_uuid": user_id, "cursor": cursor,
                                                        "last_updated": time.time()})
                self._logger.debug(
                    "action=update_cursor_kvstore  plan={} user={} cursor={} resp={} key={}".format(plan_id, user_id,
                                                                                                    cursor,
                                                                                                    resp, key))
        except Exception as e:
            trace = traceback.format_exc()
            self._logger.error("Error occurred while attempting to write cursor to kvstore: " + trace)


class Code42BatchDataProcessor(SecurityEventDetailExtractor):

    def __init__(self, sdk_client, min_timestamp, custom_handlers, event_response_handler,
                 include_users=True, include_security_events=True):
        super(Code42BatchDataProcessor, self).__init__(sdk_client, handlers=custom_handlers)
        self._include_users = include_users
        self._include_security_events = include_security_events
        self._event_response_handler = event_response_handler
        self._user_count_lock = Lock()
        self._total_users = 0
        self._min_timestamp = min_timestamp

    def get_stats(self):
        return {"user_count": self._total_users, "event_count": self._handlers.get_processed_event_count()}

    def start(self):
        self._sdk.users.for_each_user(then=self.get_user_locations, return_each_page=True)
        self._sdk.wait()

    def get_user_locations(self, user_list):
        if self._include_users:
            self._user_count_lock.acquire()
            self._total_users += len(user_list)
            self._user_count_lock.release()
            self._event_response_handler("code42:user", user_list)

        if self._include_security_events:
            for user in user_list:
                super(Code42BatchDataProcessor, self).get_user_security_events(user,
                                                                               self._min_timestamp,
                                                                               event_types=",".join(_EVENT_TYPES))

