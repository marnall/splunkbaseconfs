#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_allowlist.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os, sys
import json
import re
import time
import threading

splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_blocklist_power", "trackme_rest_api_splk_blocklist_power.log"
)


import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    extract_keys_list,
    trackme_audit_event,
    trackme_getloglevel,
    trackme_parse_describe_flag,
    trackme_register_tenant_component_summary,
)

# import trackme libs utils
from trackme_libs_utils import update_wildcard

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkBlocklistWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkBlocklistWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_blocklist(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_blocklist/write",
            "resource_group_desc": "these endpoints provide capabilities to manage blocklists for feeds tracking. (splk-dsm/dhm/mhm, power operations)",
        }

        return {"payload": response, "status": 200}

    def register_component_summary_async(
        self, session_key, splunkd_uri, tenant_id, component
    ):
        try:
            summary_register_response = trackme_register_tenant_component_summary(
                session_key,
                splunkd_uri,
                tenant_id,
                component,
            )
            logger.debug(
                f'function="trackme_register_tenant_component_summary", response="{json.dumps(summary_register_response, indent=2)}"'
            )
        except Exception as e:
            logger.error(
                f'failed to register the component summary with exception="{str(e)}"'
            )

    # Add new allowlist index if does not exist yet
    def post_blocklist_add(self, request_info, **kwargs):

        # Declare
        action = "block"
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": "tenant_id is required, please provide a valid tenant_id",
                        "status": 500,
                    }
                try:
                    component = resp_dict["component"]
                    if component not in ("dsm", "dhm", "mhm", "flx", "wlk", "fqm"):
                        return {
                            "payload": f'Invalid component="{component}"',
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "component is required, please provide a valid component",
                        "status": 500,
                    }

                try:
                    object_category = resp_dict["object_category"]
                except Exception as e:
                    return {
                        "payload": "object_category is required, please provide a valid object_category",
                        "status": 500,
                    }

                try:
                    object_value = resp_dict["object"]

                    # if the object_value contains wildcards, replace these with .* to interpret this as a regex automatically
                    object_value = update_wildcard(object_value)

                except Exception as e:
                    return {
                        "payload": "object is required, please provide a valid object",
                        "status": 500,
                    }

                # optional: a comment for this blocklist
                try:
                    comment_value = resp_dict["comment"]
                    if len(comment_value) == 0:
                        comment_value = None
                except Exception as e:
                    comment_value = None

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": (
                    "This endpoint adds a new blocklist record. Blocklists exclude "
                    "matching entities from a TrackMe tenant's monitoring on the next "
                    "tracker cycle. Each record is keyed by (object_category, object): "
                    "object_category names WHICH FIELD on the entity to compare, and "
                    "object holds the literal or regex pattern to match. Picking the "
                    "wrong object_category creates a valid record that matches NOTHING "
                    "— the operator sees a row in the blocklist but no entities get "
                    "blocked. The category must match how the operator referenced the "
                    "entities (see the object_category options below)."
                ),
                "resource_desc": "Add a new blocklist record",
                "resource_spl_example": (
                    "| trackme mode=post url=\"/services/trackme/v2/splk_blocklist/write/blocklist_add\" "
                    "body=\"{'tenant_id': 'mytenant', 'component': 'dsm', "
                    "'object_category': 'object', 'object': '^os(?!:@all$)', "
                    "'comment': 'Block os* entities except os:@all'}\""
                ),
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": (
                            "REQUIRED. The component, valid options are: "
                            "dsm | dhm | mhm | flx | wlk | fqm"
                        ),
                        "object_category": (
                            "REQUIRED. Which field on the entity record to "
                            "match the ``object`` value against. The downstream "
                            "blocklist evaluator (``apply_blocklist`` in "
                            "``trackme_libs_decisionmaker.py``) checks ``if "
                            "object_category in record`` — so ANY field name "
                            "present on the entity record is technically valid, "
                            "including ``metric_category`` (DSM), ``group``, "
                            "``app`` (WLK), and any tenant-custom field.  The "
                            "four common values below cover ~95% of operator "
                            "intent; the rest are reserved for advanced "
                            "filtering by domain-specific fields.\n"
                            "\n"
                            "Common values and their semantics:\n"
                            "  - ``object`` — match the entity's full identifier "
                            "as displayed in the entity list (e.g. "
                            "``main:syslog`` for DSM, ``host1.example.com`` "
                            "for DHM, the saved-search name for WLK). THIS IS "
                            "THE MOST COMMON CASE; use it whenever the "
                            "operator names the entities they want to block "
                            "by the identifier visible in the UI.\n"
                            "  - ``sourcetype`` — match the entity's Splunk "
                            "sourcetype field. Use ONLY when the operator "
                            "says things like 'block all entities of "
                            "sourcetype X' or 'sourcetype=X'. Does NOT apply "
                            "to DSM entities named ``<index>:<sourcetype>`` — "
                            "those are matched as ``object`` (e.g. blocking "
                            "``main:syslog`` requires object_category=object, "
                            "not sourcetype=syslog).\n"
                            "  - ``index`` — match the entity's Splunk index "
                            "field. Use ONLY when the operator says 'block "
                            "everything in index X' or 'index=X'.\n"
                            "  - ``alias`` — match the entity's alias field "
                            "(the operator-defined display name). Use ONLY "
                            "when the operator says 'block entities with "
                            "alias X' or explicitly references aliases.\n"
                            "\n"
                            "Advanced values (use only when the operator "
                            "names the field explicitly): ``metric_category`` "
                            "(comma-list of categories on DSM entities), "
                            "``group`` (entity group assignment), ``app`` (WLK "
                            "Splunk app), plus any tenant-custom field present "
                            "on the entity record. If unsure whether a custom "
                            "category matches anything, call the "
                            "``blocklist_simulate`` endpoint first to dry-run.\n"
                            "\n"
                            "Disambiguation rule for AI consumers: when the "
                            "operator references entities by the same string "
                            "they see in the entity list (e.g. ``os:@all``, "
                            "``os:bandwidth``, ``main:syslog``), the answer "
                            "is ALWAYS ``object_category=object``. Only fall "
                            "back to ``sourcetype`` / ``index`` / ``alias`` "
                            "when the operator uses those exact words. NEVER "
                            "default to ``sourcetype`` when uncertain — "
                            "that's the failure mode the AI Concierge "
                            "previously hit (the record got created against "
                            "the wrong field and matched nothing). When in "
                            "doubt, ask the operator."
                        ),
                        "object": (
                            "REQUIRED. The literal value or regex pattern to "
                            "match against the field named by ``object_category``. "
                            "Wildcards (``*``) are auto-converted to regex "
                            "(``.*``); explicit regex metacharacters "
                            "(``^`` / ``$`` / ``(?!...)`` / character classes) "
                            "are stored as-is and the record is marked "
                            "``is_rex=true``. Examples:\n"
                            "  - ``main:syslog`` — literal match against one "
                            "entity\n"
                            "  - ``os:*`` — wildcard, auto-converted, matches "
                            "any object starting with ``os:``\n"
                            "  - ``^os(?!:@all$)`` — explicit regex with "
                            "negative lookahead, matches ``os:*`` except "
                            "``os:@all``"
                        ),
                        "comment": (
                            "OPTIONAL: a comment for this blocklist, stored and "
                            "displayed alongside the record in the blocklist UI"
                        ),
                        "update_comment": (
                            "OPTIONAL: a comment for the audit record. If unset, "
                            "defaults to ``API update``. When called by an AI "
                            "agent, the Concierge stamps this with the "
                            "``[AI Agent]`` prefix automatically at consent time."
                        ),
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Define the KV query
        query_string = {
            "$and": [
                {
                    "object_category": object_category,
                    "object": object_value,
                    "action": action,
                }
            ]
        }

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            # Data collection
            collection_name = f"kv_trackme_{component}_allowlist_tenant_{tenant_id}"
            collection = service.kvstore[collection_name]

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                kvrecord = collection.data.query(query=json.dumps(query_string))[0]
                key = kvrecord.get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                # This record exists already
                logger.error(
                    f'conflict, this object exists already, record="{json.dumps(kvrecord, indent=0)}"'
                )

                return {
                    "payload": {
                        "action": "failure",
                        "response": "conflict, this object exists already",
                        "record": kvrecord,
                    },
                    "status": 500,
                }

            else:
                # This record does not exist yet
                try:
                    # Define if the pattern is a regex and store this information in the collection
                    r = re.match("[\\\\|\\?|\\$|\\^|\\[|\\]|\\{|\\}|\\+]", object_value)
                    r2 = re.findall("\\.[\\*|\\+]", object_value)

                    if r or r2:
                        is_rex = "true"
                    else:
                        is_rex = "false"

                    # define the blocklist_record
                    blocklist_record = {
                        "object_category": object_category,
                        "object": object_value,
                        "action": action,
                        "is_rex": is_rex,
                        "mtime": time.time(),
                    }
                    if comment_value:
                        blocklist_record["comment"] = comment_value

                    # Insert the record
                    collection.data.insert(json.dumps(blocklist_record))

                    # Get record
                    kvrecord = collection.data.query(query=json.dumps(query_string))[0]

                    # Audit
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "add allowlist index",
                        str(object_value),
                        str(component),
                        json.dumps(kvrecord, indent=0),
                        "The object was successfulled added to allow list",
                        str(update_comment),
                    )

                    # Log and return response
                    logger.info(
                        f'action="success", record="{json.dumps(kvrecord, indent=0)}"'
                    )

                    # call trackme_register_tenant_component_summary
                    thread = threading.Thread(
                        target=self.register_component_summary_async,
                        args=(
                            request_info.session_key,
                            request_info.server_rest_uri,
                            tenant_id,
                            component,
                        ),
                    )
                    thread.start()

                    return {
                        "payload": {
                            "action": "success",
                            "response": "the new record was successfully added",
                            "record": kvrecord,
                        },
                        "status": 200,
                    }

                except Exception as e:
                    response = {
                        "action": "failure",
                        "response": f'An exception was encountered, exception="{str(e)}"',
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'An exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Delete records from the collection
    def post_blocklist_del(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": "tenant_id is required, please provide a valid tenant_id",
                        "status": 500,
                    }
                try:
                    component = resp_dict["component"]
                except Exception as e:
                    return {
                        "payload": "component is required, please provide a valid component",
                        "status": 500,
                    }

                try:
                    if component not in ("dsm", "dhm", "mhm", "flx", "wlk", "fqm"):
                        return {
                            "payload": f'Invalid component="{component}"',
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "component is required, please provide a valid component",
                        "status": 500,
                    }

                try:
                    keys_list = extract_keys_list(resp_dict)
                    # Handle as a CSV list of keys if not a list already
                    if not isinstance(keys_list, list):
                        keys_list = [x.strip() for x in keys_list.split(",") if x.strip()]
                    else:
                        # Filter out empty strings from existing list
                        keys_list = [x.strip() if isinstance(x, str) else x for x in keys_list if (x.strip() if isinstance(x, str) else bool(x))]
                except Exception as e:
                    return {
                        "payload": "keys_list is required, please provide a valid keys_list",
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes an existing blocklist, it requires a POST call with the following information:",
                "resource_desc": "Delete an existing blocklist record",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_blocklist/write/blocklist_del\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'keys_list': '<redacted_list_of_csv_keyids>'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm | flx | wlk | fqm",
                        "keys_list": "List of record keys separated by a comma of the records to be deleted from the collection",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # Data collection
        collection_name = f"kv_trackme_{component}_allowlist_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop
        for item in keys_list:
            # Define the KV query
            query_string = {
                "_key": item,
            }

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
            try:
                kvrecord = collection.data.query(query=json.dumps(query_string))[0]
                key = kvrecord.get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                # Remove and audit
                try:
                    # Remove the record
                    collection.data.delete(json.dumps({"_key": key}))

                    # increment counter
                    processed_count += 1
                    succcess_count += 1

                    # audit record
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "delete allowlist index",
                        str(item),
                        str(component),
                        str(kvrecord),
                        "The index was deleted from allow list successfully",
                        str(update_comment),
                    )

                    result = {
                        "action": "delete",
                        "result": "success",
                        "record": kvrecord,
                    }

                    records.append(result)

                    logger.info(json.dumps(result, indent=0))

                except Exception as e:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # audit record
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "delete allowlist index",
                        str(item),
                        str(component),
                        str(kvrecord),
                        str(e),
                        str(update_comment),
                    )

                    result = {
                        "action": "delete",
                        "result": "failure",
                        "record": kvrecord,
                        "exception": e,
                    }

                    # append to records
                    records.append(result)

                    # log
                    logger.error(json.dumps(result, indent=0))

            else:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                # audit record
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "failure",
                    "delete allowlist index",
                    str(item),
                    str(component),
                    str(kvrecord),
                    "HTTP 404 NOT FOUND",
                    str(update_comment),
                )

                result = {
                    "action": "delete",
                    "result": "failure",
                    "record": item,
                    "exception": "HTTP 404 NOT FOUND",
                }

                # append to records
                records.append(result)

                # log
                logger.error(json.dumps(result, indent=0))

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                component,
            ),
        )
        thread.start()

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "records": records,
        }

        if processed_count > 0 and processed_count == succcess_count:
            return {"payload": req_summary, "status": 200}

        else:
            return {"payload": req_summary, "status": 500}

    # Update records
    def post_blocklist_update(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception as e:
                    return {
                        "payload": "tenant_id is required, please provide a valid tenant_id",
                        "status": 500,
                    }

                try:
                    component = resp_dict["component"]
                    if component not in ("dsm", "dhm", "mhm", "flx", "wlk", "fqm"):
                        return {
                            "payload": f'Invalid component="{component}"',
                            "status": 500,
                        }
                except Exception as e:
                    return {
                        "payload": "component is required, please provide a valid component",
                        "status": 500,
                    }

                try:
                    records_list = resp_dict["records_list"]
                    # Handle as an object list if needed
                    if not isinstance(records_list, list):
                        records_list = json.loads(records_list)
                except Exception as e:
                    return {
                        "payload": "records_list is required, please provide a valid records_list",
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates one or more entries in the per-component blocklist (kv_trackme_<component>_allowlist_tenant_<tenant_id>). Used to programmatically toggle the action (block/allow) on existing blocklist records identified by their KV _key.",
                "resource_desc": "Update one or more entries in the per-component blocklist",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_blocklist/write/blocklist_update" body="'
                + "{'tenant_id': 'mytenant', 'component': 'dsm', 'records_list': '[{\\\"object_category\\\":\\\"index\\\",\\\"object\\\":\\\"test2\\\",\\\"action\\\":\\\"block\\\",\\\"_key\\\":\\\"61fe64224aa485576f72b0a0\\\"}]'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "REQUIRED. The component owning the blocklist (one of: dsm, dhm, mhm, flx, fqm, wlk)",
                        "records_list": "REQUIRED. JSON array of blocklist records to update. Each record must include the existing _key plus the fields to overwrite (object, object_category, action, etc.)",
                        "update_comment": "OPTIONAL. Comment recorded in the audit log for this change. Defaults to 'API update' when omitted",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # Data collection
        collection_name = f"kv_trackme_{component}_allowlist_tenant_{tenant_id}"
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # debug
        logger.debug(f'records_list="{json.dumps(records_list, indent=0)}"')

        # loop
        for item in records_list:
            # debug
            logger.debug(f'item="{item}"')

            # Define the KV query
            query_string = {
                "_key": item.get("_key"),
            }

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
            try:
                kvrecord = collection.data.query(query=json.dumps(query_string))[0]
                key = kvrecord.get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:

                # get object_value
                object_value = item.get("object")

                # if object_value contains a wildcard which is not prefixed with a dot, replace this with .* to interpret this as a regex automatically
                object_value = update_wildcard(object_value)

                # Update and audit
                try:
                    # Define if the pattern is a regex and store this information in the collection
                    r = re.match("[\\\\|\\?|\\$|\\^|\\[|\\]|\\{|\\}|\\+]", object_value)
                    r2 = re.findall("\\.[\\*|\\+]", object_value)

                    if r or r2:
                        is_rex = "true"
                    else:
                        is_rex = "false"

                    # Update the record
                    collection.data.update(
                        str(key),
                        json.dumps(
                            {
                                "object_category": item.get("object_category"),
                                "object": object_value,
                                "action": item.get("action"),
                                "is_rex": is_rex,
                                "comment": item.get("comment", ""),
                                "mtime": time.time(),
                            }
                        ),
                    )

                    # increment counter
                    processed_count += 1
                    succcess_count += 1

                    # audit record
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "update allowlist index",
                        str(item),
                        str(component),
                        json.dumps(item, indent=1),
                        "The index was deleted from allow list successfully",
                        str(update_comment),
                    )

                    result = {
                        "action": "update",
                        "result": "success",
                        "record": kvrecord,
                    }

                    records.append(result)

                    logger.info(json.dumps(result, indent=0))

                except Exception as e:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # audit record
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "delete allowlist index",
                        str(item),
                        str(component),
                        str(kvrecord),
                        str(e),
                        str(update_comment),
                    )

                    result = {
                        "action": "update",
                        "result": "failure",
                        "record": kvrecord,
                        "exception": e,
                    }

                    # append to records
                    records.append(result)

                    # log
                    logger.error(json.dumps(result, indent=0))

            else:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                # audit record
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "failure",
                    "delete allowlist index",
                    str(item),
                    str(component),
                    str(kvrecord),
                    "HTTP 404 NOT FOUND",
                    str(update_comment),
                )

                result = {
                    "action": "update",
                    "result": "failure",
                    "record": item,
                    "exception": "HTTP 404 NOT FOUND",
                }

                # append to records
                records.append(result)

                # log
                logger.error(json.dumps(result, indent=0))

        # call trackme_register_tenant_component_summary
        thread = threading.Thread(
            target=self.register_component_summary_async,
            args=(
                request_info.session_key,
                request_info.server_rest_uri,
                tenant_id,
                component,
            ),
        )
        thread.start()

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "records": records,
        }

        if processed_count > 0 and processed_count == succcess_count:
            return {"payload": req_summary, "status": 200}

        else:
            return {"payload": req_summary, "status": 500}
