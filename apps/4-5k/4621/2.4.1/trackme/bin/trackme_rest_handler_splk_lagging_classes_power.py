#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_lagging_classes.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import json
import os
import sys
import time
import re

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_lagging_classes_power",
    "trackme_rest_api_splk_lagging_classes_power.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import extract_keys_list, get_kv_collection, trackme_audit_event, trackme_getloglevel, trackme_parse_describe_flag
from trackme_libs_decisionmaker import match_lagging_class_pattern
from trackme_libs_utils import validate_variable_delay_slots

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkLaggingClassesWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkLaggingClassesWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_lagging_classes(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_lagging_classes",
            "resource_group_desc": "Endpoints related to the management of lagging classes for splk-feeds components (power operations)",
        }

        return {"payload": response, "status": 200}

    # Add new lagging class
    def post_lagging_classes_add(self, request_info, **kwargs):

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
                        "payload": "Error: tenant_id is required",
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                    if component not in ("dsm", "dhm"):
                        return {
                            "payload": "Error: component is required and must be dsm or dhm",
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": "Error: component is required",
                        "status": 400,
                    }

                try:
                    name = resp_dict["name"]
                except Exception as e:
                    return {
                        "payload": "Error: name is required",
                        "status": 400,
                    }

                try:
                    level = resp_dict["level"]
                    if level not in ("sourcetype", "index", "priority"):
                        return {
                            "payload": "Error: level must be sourcetype, index or priority",
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": "Error: level is required",
                        "status": 400,
                    }

                try:
                    match_mode = resp_dict["match_mode"]
                    if match_mode not in ("exact", "wildcard", "regex"):
                        return {
                            "payload": "Error: match_mode must be exact, wildcard or regex",
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": "Error: match_mode is required",
                        "status": 400,
                    }

                # validate regex if match_mode is regex
                if match_mode == "regex":
                    try:
                        re.compile(name)
                    except re.error as e:
                        return {
                            "payload": f'Error: name is not a valid regex pattern, error="{str(e)}"',
                            "status": 400,
                        }

                # delay_mode: optional, defaults to "static"
                delay_mode = resp_dict.get("delay_mode", "static")
                if delay_mode not in ("static", "variable"):
                    return {
                        "payload": "Error: delay_mode must be static or variable",
                        "status": 400,
                    }

                # value_delay: required when delay_mode is static
                if delay_mode == "static":
                    try:
                        value_delay = int(resp_dict["value_delay"])
                    except Exception as e:
                        return {
                            "payload": "Error: value_delay is required when delay_mode is static and must be an integer",
                            "status": 400,
                        }
                    variable_delay_default = ""
                    variable_delay_slots = ""
                    slots_config = {}
                else:
                    # variable delay mode
                    value_delay = ""
                    try:
                        variable_delay_default = resp_dict["variable_delay_default"]
                        int(variable_delay_default)
                    except Exception as e:
                        return {
                            "payload": "Error: variable_delay_default is required when delay_mode is variable and must be an integer",
                            "status": 400,
                        }

                    try:
                        variable_delay_slots = resp_dict["variable_delay_slots"]
                        # parse and validate slots
                        if isinstance(variable_delay_slots, str):
                            slots_config = json.loads(variable_delay_slots)
                        else:
                            slots_config = variable_delay_slots
                        slot_errors = validate_variable_delay_slots(slots_config)
                        if slot_errors:
                            return {
                                "payload": f'Error: variable_delay_slots validation failed: {", ".join(slot_errors)}',
                                "status": 400,
                            }
                    except json.JSONDecodeError:
                        return {
                            "payload": "Error: variable_delay_slots is not valid JSON",
                            "status": 400,
                        }
                    except Exception as e:
                        return {
                            "payload": "Error: variable_delay_slots is required when delay_mode is variable",
                            "status": 400,
                        }

                # value_lag: OPTIONAL (can be empty)
                value_lag = resp_dict.get("value_lag", "")
                if value_lag is not None and str(value_lag).strip():
                    try:
                        int(value_lag)
                    except (ValueError, TypeError):
                        return {
                            "payload": "Error: value_lag must be an integer when provided",
                            "status": 400,
                        }

                # optional: a comment for this entry
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
                "describe": "This endpoint creates a new lagging class policy, it requires a POST call with the following data:",
                "resource_desc": "Create a new lagging class policy",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_lagging_classes/write/lagging_classes_add" body=\'{"tenant_id":"mytenant","component":"dsm","name":"linux_secure","level":"sourcetype","match_mode":"exact","value_delay":"3600","delay_mode":"static","value_lag":"900"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component: dsm or dhm",
                        "name": "The pattern to match against (exact value, wildcard with *, or regex)",
                        "level": "Which level the lagging class is based on, valid options are: sourcetype / index / priority",
                        "match_mode": "The matching mode: exact / wildcard / regex",
                        "value_delay": "CONDITIONAL: the delay threshold in seconds (required when delay_mode is static)",
                        "delay_mode": "OPTIONAL: static (default) or variable",
                        "variable_delay_default": "CONDITIONAL: default delay fallback in seconds (required when delay_mode is variable)",
                        "variable_delay_slots": "CONDITIONAL: JSON slot definitions (required when delay_mode is variable)",
                        "value_lag": "OPTIONAL: the latency threshold in seconds, leave empty to not override entity latency",
                        "comment": "OPTIONAL: a comment for this lagging class",
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

        # Define the KV query for conflict check
        query_string = {
            "$and": [
                {
                    "name": name,
                    "level": level,
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
            # Data collection - component-specific
            collection_name = f"kv_trackme_{component}_lagging_classes_tenant_{tenant_id}"
            collection = service.kvstore[collection_name]

            # Check for existing record with same name+level
            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")
            except Exception as e:
                key = None

            # Render result
            if key:
                # conflict, the same entity exists already
                logger.error(
                    f'tenant_id="{tenant_id}", component="{component}", conflict the same lagging class exists already, name="{name}", level="{level}"'
                )
                return {
                    "payload": f'tenant_id="{tenant_id}", component="{component}", conflict the same lagging class exists already, name="{name}", level="{level}"',
                    "status": 500,
                }

            else:
                # This record does not exist yet
                now = time.time()

                try:
                    record_class = {
                        "name": name,
                        "level": level,
                        "match_mode": match_mode,
                        "value_delay": str(value_delay),
                        "delay_mode": delay_mode,
                        "variable_delay_default": str(variable_delay_default),
                        "variable_delay_slots": json.dumps(slots_config) if delay_mode == "variable" else "",
                        "value_lag": str(value_lag) if value_lag is not None and str(value_lag).strip() else "",
                        "ctime": now,
                        "mtime": now,
                    }

                    if comment_value:
                        record_class["comment"] = comment_value

                    # Insert the record
                    collection.data.insert(json.dumps(record_class))

                    # Get record back
                    record = json.dumps(
                        collection.data.query(query=json.dumps(query_string)), indent=1
                    )

                    # Audit
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "create lagging class",
                            str(name),
                            str(component),
                            str(record),
                            "The lagging class was created successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                except Exception as e:
                    response = {
                        "action": "failure",
                        "response": f'an exception was encountered, exception="{str(e)}"',
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

                logger.info("success for record=" + str(record))
                return {"payload": str(record), "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Add new metrics lagging class policy
    def post_lagging_classes_metrics_add(self, request_info, **kwargs):

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
                        "payload": "Error: tenant_id is required",
                        "status": 400,
                    }

                try:
                    metric_category = resp_dict["metric_category"]
                except Exception as e:
                    return {
                        "payload": "Error: metric_category is required",
                        "status": 400,
                    }

                try:
                    metric_max_lag_allowed = int(resp_dict["metric_max_lag_allowed"])
                except Exception as e:
                    return {
                        "payload": "Error: metric_max_lag_allowed is required and must be an integer",
                        "status": 400,
                    }

                # optional: a comment for this entry
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
                "describe": "This endpoint creates a new tag policy, it requires a POST call with the following data:",
                "resource_desc": "Create a new lagging class policy",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_lagging_classes/write/lagging_classes_metrics_add\" body=\"{'tenant_id':'mytenant','metric_category':'spl','metric_max_lag_allowed':'900'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "metric_category": "name of the metric category",
                        "metric_max_lag_allowed": "the lagging value in seconds, an integer is expected",
                        "comment": "OPTIONAL: a comment for this blocklist, the comment will be stored and displayed when accessing records",
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

        try:
            # Data collection
            collection_name = "kv_trackme_mhm_lagging_classes_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            # Define the KV query
            query_string = {
                "metric_category": metric_category,
            }

            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                # conflict, the same entity exists already
                logger.error(
                    f'tenant_id="{tenant_id}", conflict the same object exists already, metric_category="{metric_category}"'
                )
                return {
                    "payload": f'tenant_id="{tenant_id}", conflict the same object exists already, metric_category="{metric_category}"',
                    "status": 500,
                }

            else:
                # This record does not exist yet
                new_kvrecord = {
                    "metric_category": metric_category,
                    "metric_max_lag_allowed": metric_max_lag_allowed,
                    "mtime": time.time(),
                }

                if comment_value:
                    new_kvrecord["comment"] = comment_value

                # Perform and audit
                try:
                    # Insert the record
                    collection.data.insert(json.dumps(new_kvrecord))

                    # Audit
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "create metric sla policy",
                            str(metric_category),
                            "metric_sla_policy",
                            new_kvrecord,
                            "The metric SLA policy was created successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                except Exception as e:
                    response = {
                        "action": "failure",
                        "response": f'an exception was encountered, exception="{str(e)}"',
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

                response = {
                    "action": "success",
                    "response": "lagging class added successfully",
                    "record": new_kvrecord,
                }
                return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Delete records from the collection
    def post_lagging_classes_del(self, request_info, **kwargs):

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
                        "payload": "Error: tenant_id is required",
                        "status": 400,
                    }

                try:
                    lagging_class_type = resp_dict["lagging_class_type"]
                    if lagging_class_type not in ("events", "metrics"):
                        return {
                            "payload": f'tenant_id="{tenant_id}", invalid option lagging_class_type="{lagging_class_type}", valid options are: events / metrics',
                            "status": 400,
                        }

                except Exception as e:
                    return {
                        "payload": "Error: lagging_class_type is required",
                        "status": 400,
                    }

                # component is required for events type
                if lagging_class_type == "events":
                    try:
                        component = resp_dict["component"]
                        if component not in ("dsm", "dhm"):
                            return {
                                "payload": f'Invalid component="{component}", valid options are: dsm / dhm',
                                "status": 400,
                            }
                    except Exception as e:
                        return {
                            "payload": "Error: component is required for events lagging classes",
                            "status": 400,
                        }
                else:
                    component = "mhm"

                try:
                    keys_list = extract_keys_list(resp_dict)
                    # Handle as a CSV list of keys, if not already a list
                    if not isinstance(keys_list, list):
                        keys_list = [x.strip() for x in keys_list.split(",") if x.strip()]
                    else:
                        # Filter out empty strings from existing list
                        keys_list = [x.strip() if isinstance(x, str) else x for x in keys_list if (x.strip() if isinstance(x, str) else bool(x))]
                    # if is empty, return an error
                    if not keys_list or len(keys_list) == 0:
                        return {
                            "payload": "Error: keys_list is required",
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": "Error: keys_list is required",
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes lagging classes, it requires a POST call with the following information:",
                "resource_desc": "Delete one or more lagging classes",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_lagging_classes/write/lagging_classes_del" body=\'{"tenant_id":"mytenant","lagging_class_type":"events","component":"dsm","keys_list":"63716c098336d473a8152f30"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "lagging_class_type": "The type of lagging classes, valid options are: events | metrics",
                        "component": "CONDITIONAL: the component (dsm / dhm), required when lagging_class_type is events",
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

        # Data collection - component-specific for events
        if lagging_class_type == "events":
            collection_name = f"kv_trackme_{component}_lagging_classes_tenant_{tenant_id}"
        elif lagging_class_type == "metrics":
            collection_name = "kv_trackme_mhm_lagging_classes_tenant_" + str(tenant_id)
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
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                # This record exists already

                # Store the record for audit purposes
                record = str(json.dumps(collection.data.query_by_id(key), indent=1))

                # Remove and audit
                try:
                    # Remove the record
                    collection.data.delete(json.dumps({"_key": key}))

                    # increment counter
                    processed_count += 1
                    succcess_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "delete lagging class",
                            str(item),
                            str(component),
                            str(record),
                            "The lagging class was deleted successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "delete",
                        "result": "success",
                        "record": record,
                    }

                    records.append(result)

                    logger.info(json.dumps(result, indent=0))

                except Exception as e:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "failure",
                            "delete lagging class",
                            str(item),
                            str(component),
                            str(record),
                            str(e),
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "delete",
                        "result": "failure",
                        "record": record,
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
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "delete lagging class",
                        str(item),
                        str(component),
                        str(record),
                        "HTTP 404 NOT FOUND",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
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
    def post_lagging_classes_update(self, request_info, **kwargs):

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
                        "payload": "Error: tenant_id is required",
                        "status": 400,
                    }

                try:
                    lagging_class_type = resp_dict["lagging_class_type"]
                    if lagging_class_type not in ("events", "metrics"):
                        return {
                            "payload": f'tenant_id="{tenant_id}", invalid option lagging_class_type="{lagging_class_type}", valid options are: events / metrics',
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": "Error: lagging_class_type is required",
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                    if lagging_class_type == "events" and component not in ("dsm", "dhm"):
                        return {
                            "payload": f'Invalid component="{component}", valid options for events are: dsm / dhm',
                            "status": 400,
                        }
                    elif lagging_class_type == "metrics" and component not in ("mhm",):
                        return {
                            "payload": f'Invalid component="{component}", valid option for metrics is: mhm',
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": "Error: component is required",
                        "status": 400,
                    }

                try:
                    records_list = resp_dict["records_list"]
                    records_list = json.loads(records_list)
                except Exception as e:
                    return {
                        "payload": "Error: records_list is required",
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates records, it requires a POST call with the following information:",
                "resource_desc": "Update one or more lagging classes",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_lagging_classes/write/lagging_classes_update" body=\'{"tenant_id":"mytenant","lagging_class_type":"events","component":"dsm","records_list":"[...]"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "lagging_class_type": "The type of lagging classes, valid options are: events | metrics",
                        "component": "The component: dsm / dhm (for events) or mhm (for metrics)",
                        "records_list": "JSON records to be updated",
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

        # Data collection - component-specific for events
        if lagging_class_type == "events":
            collection_name = f"kv_trackme_{component}_lagging_classes_tenant_{tenant_id}"
        elif lagging_class_type == "metrics":
            collection_name = "kv_trackme_mhm_lagging_classes_tenant_" + str(tenant_id)
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop
        for item in records_list:

            # Define the KV query
            query_string = {
                "_key": item.get("_key"),
            }

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                # This record exists already

                # Validate item fields for events type (mirror add endpoint validation)
                if lagging_class_type == "events":
                    validation_error = None

                    # validate level
                    item_level = item.get("level", "")
                    if item_level not in ("sourcetype", "index", "priority"):
                        validation_error = f'Invalid level="{item_level}", valid options are: sourcetype / index / priority'

                    # validate match_mode
                    item_match_mode = item.get("match_mode", "exact")
                    if item_match_mode not in ("exact", "wildcard", "regex"):
                        validation_error = f'Invalid match_mode="{item_match_mode}", valid options are: exact / wildcard / regex'

                    # validate regex pattern if match_mode is regex
                    if not validation_error and item_match_mode == "regex":
                        try:
                            re.compile(item.get("name", ""))
                        except re.error as e:
                            validation_error = f'name is not a valid regex pattern, error="{str(e)}"'

                    # validate delay_mode
                    item_delay_mode = item.get("delay_mode", "static")
                    if not validation_error and item_delay_mode not in ("static", "variable"):
                        validation_error = f'Invalid delay_mode="{item_delay_mode}", valid options are: static / variable'

                    # validate value_delay when static (required, matching add endpoint)
                    if not validation_error and item_delay_mode == "static":
                        if "value_delay" not in item:
                            validation_error = "value_delay is required when delay_mode is static"
                        else:
                            try:
                                int(item["value_delay"])
                            except (ValueError, TypeError):
                                validation_error = "value_delay must be an integer when delay_mode is static"

                    # validate variable delay fields when variable (required, matching add endpoint)
                    if not validation_error and item_delay_mode == "variable":
                        if "variable_delay_default" not in item:
                            validation_error = "variable_delay_default is required when delay_mode is variable"
                        else:
                            try:
                                int(item["variable_delay_default"])
                            except (ValueError, TypeError):
                                validation_error = "variable_delay_default must be an integer when delay_mode is variable"

                        if not validation_error:
                            if "variable_delay_slots" not in item:
                                validation_error = "variable_delay_slots is required when delay_mode is variable"
                            else:
                                try:
                                    vd_slots = item["variable_delay_slots"]
                                    if isinstance(vd_slots, str):
                                        slots_config = json.loads(vd_slots)
                                    else:
                                        slots_config = vd_slots
                                    slot_errors = validate_variable_delay_slots(slots_config)
                                    if slot_errors:
                                        validation_error = f'variable_delay_slots validation failed: {", ".join(slot_errors)}'
                                except json.JSONDecodeError:
                                    validation_error = "variable_delay_slots is not valid JSON"

                    # validate value_lag when provided
                    if not validation_error:
                        item_value_lag = item.get("value_lag", "")
                        if item_value_lag and str(item_value_lag).strip():
                            try:
                                int(item_value_lag)
                            except (ValueError, TypeError):
                                validation_error = "value_lag must be an integer when provided"

                    if validation_error:
                        processed_count += 1
                        failures_count += 1
                        records.append(
                            {
                                "_key": item.get("_key"),
                                "result": "failure",
                                "reason": validation_error,
                            }
                        )
                        continue

                # Store the record for audit purposes
                record = str(json.dumps(collection.data.query_by_id(key), indent=1))

                # Update and audit
                try:
                    # Update the record

                    if lagging_class_type == "events":
                        # normalize variable_delay_slots to JSON string (consistent with add endpoint)
                        raw_slots = item.get("variable_delay_slots", "")
                        if isinstance(raw_slots, dict):
                            normalized_slots = json.dumps(raw_slots)
                        elif isinstance(raw_slots, str):
                            normalized_slots = raw_slots
                        else:
                            normalized_slots = ""

                        update_data = {
                            "name": item.get("name"),
                            "level": item.get("level"),
                            "match_mode": item.get("match_mode", "exact"),
                            "value_delay": str(item["value_delay"]) if item_delay_mode == "static" else str(item.get("value_delay", "")),
                            "delay_mode": item.get("delay_mode", "static"),
                            "variable_delay_default": str(item["variable_delay_default"]) if item_delay_mode == "variable" else str(item.get("variable_delay_default", "")),
                            "variable_delay_slots": normalized_slots,
                            "value_lag": str(item.get("value_lag")) if item.get("value_lag") is not None and str(item.get("value_lag")).strip() else "",
                            "comment": item.get("comment", ""),
                            "mtime": time.time(),
                        }
                        # preserve ctime from existing record
                        existing = json.loads(record) if isinstance(record, str) else record
                        if isinstance(existing, dict):
                            update_data["ctime"] = existing.get("ctime", time.time())
                        elif isinstance(existing, list) and len(existing) > 0:
                            update_data["ctime"] = existing[0].get("ctime", time.time())
                        collection.data.update(
                            str(key),
                            json.dumps(update_data),
                        )
                    elif lagging_class_type == "metrics":
                        collection.data.update(
                            str(key),
                            json.dumps(
                                {
                                    "metric_category": item.get("metric_category"),
                                    "metric_max_lag_allowed": item.get(
                                        "metric_max_lag_allowed"
                                    ),
                                    "comment": item.get("comment", ""),
                                    "mtime": time.time(),
                                }
                            ),
                        )

                    # increment counter
                    processed_count += 1
                    succcess_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "update lagging classes",
                            str(item),
                            str(component),
                            json.dumps(item, indent=1),
                            "The lagging class was updated successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "update",
                        "result": "success",
                        "record": record,
                    }

                    records.append(result)

                    logger.info(json.dumps(result, indent=0))

                except Exception as e:
                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # audit record
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "failure",
                            "update lagging classes",
                            str(item),
                            str(component),
                            str(record),
                            str(e),
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    result = {
                        "action": "update",
                        "result": "failure",
                        "record": record,
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
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "update lagging classes",
                        str(item),
                        str(component),
                        str(record),
                        "HTTP 404 NOT FOUND",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
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

    # Simulate a lagging class to preview which entities would match
    def post_lagging_classes_simulate(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        component = None
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
                        "payload": {
                            "response": "The tenant_id is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                    if component not in ("dsm", "dhm"):
                        return {
                            "payload": {
                                "action": "failure",
                                "response": f"invalid component {component}, valid options are: dsm / dhm",
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The component is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    name = resp_dict["name"]
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The argument name is required (the pattern to test)",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    match_mode = resp_dict["match_mode"]
                    if match_mode not in ("exact", "wildcard", "regex"):
                        return {
                            "payload": {
                                "response": "match_mode must be exact, wildcard or regex",
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The argument match_mode is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

                try:
                    level = resp_dict["level"]
                    if level not in ("index", "sourcetype", "priority"):
                        return {
                            "payload": {
                                "response": "level must be index, sourcetype or priority",
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": {
                            "response": "The argument level is required",
                            "status": 400,
                        },
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint simulates a lagging class matching, it requires a POST call with the following information:",
                "resource_desc": "Simulates a lagging class to preview which entities would match",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_lagging_classes/write/lagging_classes_simulate" body=\'{"tenant_id": "mytenant", "component": "dsm", "name": "linux*", "match_mode": "wildcard", "level": "sourcetype"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "(required) The component: dsm / dhm",
                        "name": "(required) The pattern to test (exact value, wildcard, or regex)",
                        "match_mode": "(required) The matching mode: exact / wildcard / regex",
                        "level": "(required) The level to match against: index / sourcetype / priority",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Validate regex if match_mode is regex
        if match_mode == "regex":
            try:
                re.compile(name)
            except re.error:
                req_summary = {
                    "entities_matched_count": 0,
                    "result_summary": "The name pattern is not a valid regular expression, review this expression and try again.",
                    "name": name,
                    "match_mode": match_mode,
                    "pattern_is_valid": "false",
                }
                return {"payload": req_summary, "status": 200}

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

        # start
        main_start = time.time()

        #
        # KV entities
        #

        # entities KV collection
        data_collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
        data_collection = service.kvstore[data_collection_name]

        # get all records (full collection load for efficiency)
        data_records, data_collection_keys, data_collection_dict = get_kv_collection(
            data_collection, data_collection_name
        )

        #
        # Match entities against the pattern
        #

        entities_matched = []

        if len(data_records) > 0:

            for entity_record in data_records:

                # Skip entities that override lagging classes (consistent with resolve_lagging_class_threshold)
                if entity_record.get("data_override_lagging_class") == "true":
                    continue

                entity_object = entity_record.get("object", "")

                # Extract the value for the specified level
                if level == "index":
                    entity_value_raw = entity_record.get("data_index", "")
                elif level == "sourcetype":
                    entity_value_raw = entity_record.get("data_sourcetype", "")
                elif level == "priority":
                    entity_value_raw = entity_record.get("priority", "")
                else:
                    continue

                if not entity_value_raw:
                    continue

                # Handle multi-value fields (comma-separated, common in DHM)
                if isinstance(entity_value_raw, str) and "," in entity_value_raw:
                    entity_values = [v.strip() for v in entity_value_raw.split(",") if v.strip()]
                else:
                    entity_values = [str(entity_value_raw).strip()]

                # Check if ANY value matches the pattern
                matched = False
                for ev in entity_values:
                    if match_lagging_class_pattern(ev, name, match_mode):
                        matched = True
                        break

                if matched and entity_object not in entities_matched:
                    entities_matched.append(entity_object)

        # get run_time
        run_time = round((time.time() - main_start), 3)

        # create a result summary
        if len(entities_matched) > 0:
            result_summary = f"The pattern has matched {len(entities_matched)} entities."
        else:
            result_summary = "The pattern has not matched any entities, verify your inputs and try again."

        # request summary
        req_summary = {
            "kvstore_collection_entities_count": len(data_records),
            "entities_matched_count": len(entities_matched),
            "entities_matched": entities_matched,
            "result_summary": result_summary,
            "pattern_is_valid": "true",
        }

        logger.info(
            f'lagging class simulation operation has terminated, tenant_id="{tenant_id}", component="{component}", name="{name}", match_mode="{match_mode}", level="{level}", matched={len(entities_matched)}, run_time="{run_time}"'
        )
        return {"payload": req_summary, "status": 200}
