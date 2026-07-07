#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_maintenance.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import datetime
import json
import os
import sys
import time

import requests

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.maintenance", "trackme_rest_api_maintenance.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_audit_event, trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerMaintenance_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerMaintenance_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_maintenance(self, request_info, **kwargs):
        response = {
            "resource_group_name": "maintenance",
            "resource_group_desc": "The maintenance mode feature provides a built-in workflow to temporarily silence all alerts from TrackMe for a given period of time, which can be scheduled in advance.",
        }

        return {"payload": response, "status": 200}

    # Check the global maintenance mode
    def get_check_global_maintenance_status(self, request_info, **kwargs):
        # declare
        update_comment = "API update"
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        if describe:
            response = {
                "describe": "This endpoint checks and returns the maintenance status. It requires a GET call with no data.",
                "resource_desc": "Check and return the maintenance mode status",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/maintenance/check_global_maintenance_status"',
            }

            return {"payload": response, "status": 200}

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = "kv_trackme_maintenance_mode"
        collection = service.kvstore[collection_name]

        # get records
        try:
            records = collection.data.query()
            key = records[0].get("_key")
        except Exception as e:
            key = None

        # if we have no records yet, the maintenance mode is not setup yet, therefore it is disabled
        if not key:
            # Set the response record
            response = {
                "tenants_scope": "*",
                "maintenance": False,
                "maintenance_mode": "disabled",
                "maintenance_message": "The global maintenance mode is currently disabled, all alerts from TrackMe are permitted",
                "maintenance_comment": update_comment,
                "epoch_updated": round(time.time(), 0),
                "time_updated": time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(time.time())
                ),
                "src_user": "nobody",
            }

            # insert a new record
            try:
                collection.data.insert(json.dumps(response))
            except Exception as e:
                logger.error(
                    f'failed to insert the maintenance record with exception="{str(e)}"'
                )

            # Render
            return {"payload": response, "status": 200}

        # if we have records, then investigate
        else:
            tenants_scope = records[0].get("tenants_scope", "*")
            maintenance = records[0].get("maintenance")
            maintenance_mode = records[0].get("maintenance_mode")
            knowledge_record_id = records[0].get("knowledge_record_id", None)

            # maintenance mode is enabled or scheduled, verify its expiration
            if maintenance or maintenance_mode == "scheduled":
                # get count down
                maintenance_countdown = round(
                    int(records[0].get("maintenance_mode_end")) - time.time(), 0
                )

                # set bool
                if not maintenance_countdown >= 0:
                    maintenance_mode_has_expired = True
                else:
                    maintenance_mode_has_expired = False

                # if count down has expired
                if maintenance_mode_has_expired:
                    logger.info(
                        f'global maintenance mode was enabled and has now expired, count_down="{maintenance_countdown}"'
                    )
                    response = {
                        "tenants_scope": tenants_scope,
                        "maintenance": False,
                        "maintenance_mode": "disabled",
                        "maintenance_message": "The global maintenance mode has expired and was automatically disabled, all alerts from TrackMe are now permitted",
                        "maintenance_mode_start": records[0].get(
                            "maintenance_mode_start"
                        ),
                        "maintenance_mode_end": records[0].get("maintenance_mode_end"),
                        "maintenance_comment": records[0].get("maintenance_comment"),
                        "epoch_updated": round(time.time(), 0),
                        "epoch_started": records[0].get("time_started"),
                        "time_updated": time.strftime(
                            "%Y-%m-%d %H:%M", time.localtime(time.time())
                        ),
                        "time_started": time.strftime(
                            "%Y-%m-%d %H:%M",
                            time.localtime(int(records[0].get("epoch_started"))),
                        ),
                        "src_user": records[0].get("src_user"),
                        "knowledge_record_id": knowledge_record_id,
                    }

                    # update record
                    try:
                        collection.data.update(str(key), json.dumps(response))
                    except Exception as e:
                        logger.error(
                            f'failed to updated the maintenance record with exception="{str(e)}"'
                        )

                    # Maintenance Knowledge DataBase
                    if knowledge_record_id:
                        data = {
                            "action": "stop_period",
                            "record_id": knowledge_record_id,
                            "update_comment": update_comment,
                        }

                        header = {
                            "Authorization": "Splunk %s" % request_info.session_key,
                            "Content-Type": "application/json",
                        }

                        try:
                            with requests.post(
                                f"{request_info.server_rest_uri}/services/trackme/v2/maintenance_kdb/admin/maintenance_kdb_manage_record",
                                data=json.dumps(data),
                                headers=header,
                                verify=False,
                                timeout=600,
                            ) as response:
                                response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
                                response_json = response.json()

                                # Process successful response
                                logger.info(
                                    f'Success stopping the period of the knowledge record, data="{json.dumps(response_json, indent=2)}"'
                                )

                                # Update the maintenance record with the new record_id
                                maintenance_record = collection.data.query_by_id(key)
                                # remove the knowledge_record_id from maintenance record
                                del maintenance_record["knowledge_record_id"]
                                # update
                                collection.data.update(
                                    key, json.dumps(maintenance_record)
                                )
                                logger.info(
                                    f'Success stopping the period of the maintenance record, data="{json.dumps(collection.data.query_by_id(key), indent=2)}"'
                                )

                        except requests.HTTPError as http_err:
                            # Handle HTTP errors
                            error_message = f'Failed to stop the knowledge record period, status_code={http_err.response.status_code}, response_text="{http_err.response.text}"'
                            logger.error(error_message)
                            return {
                                "payload": {"response": error_message},
                                "status": 500,
                            }
                        except Exception as e:
                            # Handle other exceptions
                            error_message = f'Failed to stop the knowledge record period, exception="{str(e)}"'
                            logger.error(error_message)
                            return {
                                "payload": {"response": error_message},
                                "status": 500,
                            }

                    # Render
                    return {"payload": response, "status": 200}

                # and not expired yet
                else:
                    # is this a scheduled maintenance?

                    if int(records[0].get("maintenance_mode_start")) > time.time():
                        logger.info(
                            f'global maintenance mode is scheduled, but not active yet, count_down="{maintenance_countdown}"'
                        )
                        response = {
                            "tenants_scope": tenants_scope,
                            "maintenance": False,
                            "maintenance_mode": "scheduled",
                            "maintenance_message": "The global maintenance mode is currently scheduled, alerts from TrackMe are currently permitted until it is activated",
                            "maintenance_mode_start": records[0].get(
                                "maintenance_mode_start"
                            ),
                            "maintenance_mode_end": records[0].get(
                                "maintenance_mode_end"
                            ),
                            "maintenance_countdown": round(
                                time.time()
                                - int(records[0].get("maintenance_mode_start"))
                            ),
                            "maintenance_comment": records[0].get(
                                "maintenance_comment"
                            ),
                            "epoch_updated": round(time.time(), 0),
                            "epoch_started": records[0].get("epoch_started"),
                            "time_updated": time.strftime(
                                "%Y-%m-%d %H:%M", time.localtime(time.time())
                            ),
                            "time_started": time.strftime(
                                "%Y-%m-%d %H:%M",
                                time.localtime(int(records[0].get("epoch_started"))),
                            ),
                            "src_user": records[0].get("src_user"),
                            "knowledge_record_id": knowledge_record_id,
                        }

                    else:
                        logger.info(
                            f'global maintenance mode is enabled and has not expired yet, count_down="{maintenance_countdown}"'
                        )
                        response = {
                            "tenants_scope": tenants_scope,
                            "maintenance": True,
                            "maintenance_mode": "enabled",
                            "maintenance_message": "The global maintenance mode is currently enabled, alerts from TrackMe are not permitted",
                            "maintenance_mode_start": records[0].get(
                                "maintenance_mode_start"
                            ),
                            "maintenance_mode_end": records[0].get(
                                "maintenance_mode_end"
                            ),
                            "maintenance_countdown": maintenance_countdown,
                            "maintenance_comment": records[0].get(
                                "maintenance_comment"
                            ),
                            "epoch_updated": round(time.time(), 0),
                            "epoch_started": records[0].get("epoch_started"),
                            "time_updated": time.strftime(
                                "%Y-%m-%d %H:%M", time.localtime(time.time())
                            ),
                            "time_started": time.strftime(
                                "%Y-%m-%d %H:%M",
                                time.localtime(int(records[0].get("epoch_started"))),
                            ),
                            "src_user": records[0].get("src_user"),
                            "knowledge_record_id": knowledge_record_id,
                        }

                    # update record
                    try:
                        collection.data.update(str(key), json.dumps(response))
                    except Exception as e:
                        logger.error(
                            f'failed to updated the maintenance record with exception="{str(e)}"'
                        )

                    # Render
                    return {"payload": response, "status": 200}

            # whatever - only enabled would be considered in the maintenance logic
            else:
                response = {
                    "tenants_scope": tenants_scope,
                    "maintenance": False,
                    "maintenance_mode": "disabled",
                    "maintenance_comment": update_comment,
                    "maintenance_message": "The maintenance is currently disabled, all alerts from TrackMe are permitted",
                }

                if not records[0].get("maintenance_mode") == "disabled":
                    # update record
                    try:
                        collection.data.update(str(key), json.dumps(response))
                    except Exception as e:
                        logger.error(
                            f'failed to updated the maintenance record with exception="{str(e)}"'
                        )

                # Render
                return {"payload": response, "status": 200}

    # Enable the maintenance mode
    def post_global_maintenance_enable(self, request_info, **kwargs):
        # Declare
        tenants_scope = ["*"]
        maintenance_mode_start = None
        maintenance_mode_end = None
        maintenance_duration = None
        add_knowledge_record = None
        time_format = None
        update_comment = None

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
                    resp_dict = json.loads(str(request_info.raw_args["payload"]))
                except Exception as e:
                    resp_dict = []

                # Get tenants_scope, optional
                try:
                    tenants_scope = resp_dict["tenants_scope"]
                    if tenants_scope == "*" or tenants_scope == "":
                        tenants_scope = ["*"]
                except Exception as e:
                    tenants_scope = ["*"]

                # if not already a list, convert to list from comma separated string
                if not isinstance(tenants_scope, list):
                    tenants_scope = tenants_scope.split(",")

                # if tenants_scope has more than entry, ensure to remove * if present
                # also, tenants_scope cannot be empty, if empty add *
                if len(tenants_scope) > 1:
                    try:
                        tenants_scope.remove("*")
                    except Exception as e:
                        pass
                if len(tenants_scope) == 0:
                    tenants_scope = ["*"]

                # Get start and end maintenance, both are optionals

                # maintenance_mode_start
                try:
                    maintenance_mode_start = resp_dict["maintenance_mode_start"]
                except Exception as e:
                    maintenance_mode_start = 0

                # maintenance_mode_end
                try:
                    maintenance_mode_end = resp_dict["maintenance_mode_end"]
                    logger.info(f'Received maintenance_mode_end from request: "{maintenance_mode_end}" (type: {type(maintenance_mode_end).__name__})')
                except Exception as e:
                    maintenance_mode_end = 0
                    logger.warning(f'Failed to get maintenance_mode_end from request, defaulting to 0, exception="{str(e)}"')

                # maintenance_duration
                try:
                    maintenance_duration = int(resp_dict["maintenance_duration"])
                except Exception as e:
                    maintenance_duration = 0

                # time_format: optional and defaults to epochtime, alternative is date string in the format YYYY-MM-DDTHH:MM
                try:
                    time_format = resp_dict["time_format"]
                    if time_format not in ("epochtime", "datestring"):
                        return {
                            "payload": {
                                "response": 'Invalid option for time_format="{}", valid options are: epochtime | datestring'
                            },
                            "status": 500,
                        }
                except Exception as e:
                    time_format = "epochtime"

                # Add a knowledge record
                try:
                    add_knowledge_record = resp_dict["add_knowledge_record"]
                    # Handle both boolean and string values
                    if isinstance(add_knowledge_record, bool):
                        # Already a boolean, use as-is
                        pass
                    elif isinstance(add_knowledge_record, str):
                        # String value, convert to boolean
                        if add_knowledge_record.lower() in ("true", "1", "yes"):
                            add_knowledge_record = True
                        else:
                            add_knowledge_record = False
                    else:
                        # Default to True for other types
                        add_knowledge_record = True
                except Exception as e:
                    add_knowledge_record = True

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

        else:
            # body is not required in this endpoint
            describe = False

        if describe:
            response = {
                "describe": "This endpoint enables the maintenance mode, it requires a POST call with the following information:",
                "resource_desc": "Enable global TrackMe maintenance mode",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/maintenance/global_maintenance_enable\" body=\"{'maintenance_duration': '3600', 'update_comment': 'Enabling a TrackMe global maintenance for 1 hour of duration from now.'}\"",
                "options": [
                    {
                        "tenants_scope": "OPTIONAL: the tenants scope for the maintenance expressed as a comma separated list of values, defaults to * for all tenants",
                        "maintenance_duration": "(integer) OPTIONAL: the duration of the maintenance window in seconds, if unspecified and maintenance_mode_end is not specified either, defaults to now plus 24 hours",
                        "maintenance_mode_end": "OPTIONAL: the date time in epochtime format for the end of the maintenance window, it is overridden by maintenance_duration if specified, defaults to now plus 24 hours if not specified and maintenance_duration is not specified",
                        "maintenance_mode_start": "OPTIONAL: the date time in epochtime format for the start of the maintennce window, defaults to now if not specified",
                        "time_format": "OPTIONAL: the time format when submitting start and end maintenance values, defaults to epochtime and can alternatively be set to datestring which expects YYYY-MM-DDTHH:MM as the input format",
                        "add_knowledge_record": "OPTIONAL: a boolean value to indicate if a knowledge record should be added to the knowledge database, defaults to true",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Calculates start and end
        time_updated = round(time.time())

        # Get service early to check for existing record before processing start time
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # get current user
        username = request_info.user

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Set the collection
        collection_name = "kv_trackme_maintenance_mode"
        collection = service.kvstore[collection_name]

        # Get the current record early to check if we need to preserve start time
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only
        existing_start_time = None
        try:
            records = collection.data.query()
            key = records[0].get("_key")
            # Get existing start time to preserve it when extending
            existing_start_time = records[0].get("maintenance_mode_start")
        except Exception as e:
            key = None

        # Check if we need to preserve existing start time BEFORE applying defaults
        # This must happen before the default logic that converts 0 to current time
        should_preserve_start = False
        try:
            start_time_int = int(maintenance_mode_start) if maintenance_mode_start is not None else 0
            if start_time_int <= 0 and existing_start_time:
                should_preserve_start = True
                maintenance_mode_start = str(existing_start_time)
        except:
            pass

        if time_format == "datestring":
            # convert maintenance start
            # Skip datestring conversion if we're preserving an existing start time (it's already an epoch timestamp)
            if not should_preserve_start:
                try:
                    maintenance_mode_start_dt = datetime.datetime.strptime(
                        str(maintenance_mode_start), "%Y-%m-%dT%H:%M"
                    )
                    # Make the datetime timezone-aware as UTC
                    maintenance_mode_start_dt = maintenance_mode_start_dt.replace(
                        tzinfo=datetime.timezone.utc
                    )
                    maintenance_mode_start = int(
                        round(float(maintenance_mode_start_dt.timestamp()))
                    )
                except Exception as e:
                    return {
                        "payload": {
                            "response": f'Exception while trying to convert the input datestring, exception="{str(e)}"'
                        },
                        "status": 500,
                    }
            else:
                # When preserving, maintenance_mode_start is already an epoch timestamp string, convert to int
                try:
                    maintenance_mode_start = int(maintenance_mode_start)
                except:
                    pass

            # convert maintenance end
            try:
                maintenance_mode_end_dt = datetime.datetime.strptime(
                    str(maintenance_mode_end), "%Y-%m-%dT%H:%M"
                )
                # Make the datetime timezone-aware as UTC
                maintenance_mode_end_dt = maintenance_mode_end_dt.replace(
                    tzinfo=datetime.timezone.utc
                )
                maintenance_mode_end = int(
                    round(float(maintenance_mode_end_dt.timestamp()))
                )
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Exception while trying to convert the input datestring, exception="{str(e)}"'
                    },
                    "status": 500,
                }

        else:
            # if maintenance start is not specified and we're not preserving existing, starts at now
            if not should_preserve_start and ((maintenance_mode_start is None) or (maintenance_mode_start <= 0)):
                maintenance_mode_start = str(round(time_updated))

            # if maintenance end is not specified, and maintenance duration is not specified either, defaults to now + 24 hours
            if (maintenance_mode_end is None) or (maintenance_mode_end <= 0):
                maintenance_mode_end = str(round(time.time() + 86400))

        # if maintenance duration is specified, it overrides the maintenance end whenever it is specified or not
        if (maintenance_duration is not None) and (maintenance_duration > 0):
            maintenance_mode_end = str(round(time.time() + maintenance_duration))

        # control: the start of the maintenance cannot be in the past (allow 5 min margin)
        # Exception: if we're preserving an existing start time from an existing record, allow it
        if not should_preserve_start:
            try:
                if int(maintenance_mode_start) - time.time() < -300:
                    return {
                        "payload": {
                            "response": f"The maintenance start cannot be in the past, it is in past of {round(int(maintenance_mode_start) - time.time())} seconds"
                        },
                        "status": 500,
                    }
            except:
                pass

        # set count down
        maintenance_countdown = round(int(maintenance_mode_end) - time.time(), 0)

        # set maintenance_mode_start and maintenance_mode_end to int
        try:
            maintenance_mode_start = int(round(float(maintenance_mode_start), 0))
        except:
            pass
        try:
            maintenance_mode_end_before = maintenance_mode_end
            maintenance_mode_end = int(round(float(maintenance_mode_end), 0))
            if maintenance_mode_end_before != maintenance_mode_end:
                logger.info(f'Converted maintenance_mode_end from "{maintenance_mode_end_before}" to "{maintenance_mode_end}"')
        except Exception as e:
            logger.warning(f'Failed to convert maintenance_mode_end to int, exception="{str(e)}"')
            pass

        # is this a scheduled maintenance?
        if int(maintenance_mode_start) > time.time():
            logger.info(
                f'global maintenance mode is scheduled, but not active yet, count_down="{maintenance_countdown}"'
            )
            maintenance_mode_response = {
                "tenants_scope": tenants_scope,
                "maintenance": False,
                "maintenance_mode": "scheduled",
                "maintenance_message": "The global maintenance mode is currently scheduled, alerts from TrackMe are currently permitted until it is activated",
                "maintenance_mode_start": maintenance_mode_start,
                "maintenance_mode_end": maintenance_mode_end,
                "maintenance_countdown": maintenance_countdown,
                "maintenance_comment": update_comment,
                "epoch_updated": round(time.time(), 0),
                "time_updated": time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(time.time())
                ),
                "epoch_started": round(time.time(), 0),
                "time_started": time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(time.time())
                ),
                "src_user": username,
            }

        else:
            # Set response
            maintenance_mode_response = {
                "tenants_scope": tenants_scope,
                "maintenance": True,
                "maintenance_mode": "enabled",
                "maintenance_message": "The global maintenance mode is currently enabled, alerts from TrackMe are not permitted",
                "maintenance_mode_start": maintenance_mode_start,
                "maintenance_mode_end": maintenance_mode_end,
                "maintenance_countdown": maintenance_countdown,
                "maintenance_comment": update_comment,
                "epoch_updated": round(time.time(), 0),
                "time_updated": time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(time.time())
                ),
                "epoch_started": round(time.time(), 0),
                "time_started": time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(time.time())
                ),
                "src_user": username,
            }

        # Get existing knowledge_record_id before updating (if extending)
        existing_knowledge_record_id = None
        if key:
            try:
                existing_record = collection.data.query_by_id(key)
                existing_knowledge_record_id = existing_record.get("knowledge_record_id")
                # Handle empty string or None
                if existing_knowledge_record_id == "" or existing_knowledge_record_id is None:
                    existing_knowledge_record_id = None
                # Preserve knowledge_record_id in the response when updating
                if existing_knowledge_record_id:
                    maintenance_mode_response["knowledge_record_id"] = existing_knowledge_record_id
                logger.info(
                    f'Found existing maintenance record, key="{key}", knowledge_record_id="{existing_knowledge_record_id}", add_knowledge_record="{add_knowledge_record}" (type: {type(add_knowledge_record).__name__})'
                )
            except Exception as e:
                logger.warning(f'Failed to get existing record, key="{key}", exception="{str(e)}"')
                pass

        if key:
            # Update the record
            collection.data.update(str(key), json.dumps(maintenance_mode_response))
        else:
            # Insert the record
            kv_response = collection.data.insert(json.dumps(maintenance_mode_response))
            key = kv_response.get("_key")

        # Update existing knowledge record if extending (not creating new one)
        logger.info(
            f'Checking knowledge record update conditions: key="{key}", existing_knowledge_record_id="{existing_knowledge_record_id}", add_knowledge_record="{add_knowledge_record}" (type: {type(add_knowledge_record).__name__}), not add_knowledge_record="{not add_knowledge_record}"'
        )
        if key and existing_knowledge_record_id and not add_knowledge_record:
            # We're extending an existing maintenance period, update the knowledge record's end time
            logger.info(
                f'Attempting to update knowledge record for extended maintenance period, record_id="{existing_knowledge_record_id}", new_end_time="{maintenance_mode_end}"'
            )
            try:
                kdb_collection_name = "kv_trackme_maintenance_kdb"
                kdb_collection = service.kvstore[kdb_collection_name]
                
                # Get the existing knowledge record
                kdb_record = kdb_collection.data.query_by_id(existing_knowledge_record_id)
                if kdb_record:
                    # Store old end time for logging
                    old_end_time = kdb_record.get("time_end")
                    logger.info(
                        f'Retrieved knowledge record before update: record_id="{existing_knowledge_record_id}", current_time_end="{old_end_time}", target_time_end="{maintenance_mode_end}"'
                    )
                    
                    # Update the end time to the new extended end time
                    # Ensure we're using the integer value
                    new_end_time = int(maintenance_mode_end)
                    kdb_record["time_end"] = new_end_time
                    kdb_record["mtime"] = round(time.time(), 0)
                    if update_comment:
                        kdb_record["add_info"] = update_comment
                    
                    # Log the record we're about to update
                    logger.info(
                        f'Updating knowledge record with: time_end="{new_end_time}", mtime="{kdb_record["mtime"]}", add_info="{kdb_record.get("add_info", "")}"'
                    )
                    
                    # Update the knowledge record - ensure we're updating with the correct key format
                    update_result = kdb_collection.data.update(str(existing_knowledge_record_id), json.dumps(kdb_record))
                    logger.info(f'KVStore update result: {update_result}')
                    
                    # Verify the update was persisted by querying the record again
                    try:
                        updated_record = kdb_collection.data.query_by_id(existing_knowledge_record_id)
                        verified_end_time = updated_record.get("time_end") if updated_record else None
                        logger.info(
                            f'Success updating knowledge record end time for extended maintenance period, record_id="{existing_knowledge_record_id}", old_end_time="{old_end_time}", new_end_time="{maintenance_mode_end}", verified_end_time="{verified_end_time}"'
                        )
                        if verified_end_time != int(maintenance_mode_end):
                            logger.error(
                                f'VERIFICATION FAILED: Knowledge record update did not persist correctly! Expected end_time="{maintenance_mode_end}", but verified_end_time="{verified_end_time}"'
                            )
                    except Exception as verify_error:
                        logger.warning(
                            f'Could not verify knowledge record update, record_id="{existing_knowledge_record_id}", exception="{str(verify_error)}"'
                        )
                        logger.info(
                            f'Success updating knowledge record end time for extended maintenance period, record_id="{existing_knowledge_record_id}", old_end_time="{old_end_time}", new_end_time="{maintenance_mode_end}"'
                        )
                    
                    # Record audit change
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        "all",
                        request_info.user,
                        "success",
                        "extend maintenance period - update knowledge record",
                        "all",
                        "all",
                        str(json.dumps(kdb_record, indent=1)),
                        f'The knowledge record end time was updated for extended maintenance period by user="{username}"',
                        str(update_comment),
                    )
                else:
                    logger.warning(
                        f'Knowledge record not found for record_id="{existing_knowledge_record_id}", cannot update end time'
                    )
            except Exception as e:
                # Log error but don't fail the extend operation
                import traceback
                error_message = f'Failed to update knowledge record end time, record_id="{existing_knowledge_record_id}", exception="{str(e)}", traceback="{traceback.format_exc()}"'
                logger.error(error_message)
        else:
            # Log why knowledge record update was skipped
            reasons = []
            if not key:
                reasons.append("no key (new record)")
            if not existing_knowledge_record_id:
                reasons.append("no existing knowledge_record_id")
            if add_knowledge_record:
                reasons.append(f"add_knowledge_record is {add_knowledge_record}")
            logger.info(
                f'Skipping knowledge record update: {", ".join(reasons) if reasons else "unknown reason"}'
            )

        # record an audit change
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            "all",
            request_info.user,
            "success",
            "enable maintenance mode",
            "all",
            "all",
            str(json.dumps(collection.data.query_by_id(key), indent=1)),
            f'The maintenance mode was enabled successfully by user="{username}"',
            str(update_comment),
        )

        # log
        logger.info(
            f'TrackMe maintenance mode was enabled, record="{json.dumps(maintenance_mode_response, indent=2)}"'
        )

        # add knowledge record
        if add_knowledge_record:
            # set data
            """
            "tenants_scope": "OPTIONAL: the tenants scope for the maintenance expressed as a comma separated list of values, defaults to * for all tenants",
            "time_start": "MANDATORY: the start time of the maintenance, it can be specified in epochtime or datestring format",
            "time_end": "MANDATORY: the end time of the maintenance, it can be specified in epochtime or datestring format",
            "no_days_validity": "OPTIONAL: the number of days of validity of the maintenance record, if set to 0, the maintenance record is valid forever",
            "reason": "MANDATORY: the reason for the maintenance",
            "type": "MANDATORY: the type of the maintenance, it can be either planned or unplanned",
            "add_info": "OPTIONAL: additional information about the maintenance",
            "no_days_validity": "OPTIONAL: the number of days of validity of the maintenance record, if set to 0, the maintenance record is valid forever",
            "time_format": "OPTIONAL: the time format when submitting start and end maintenance values, defaults to epochtime and can alternatively be set to datestring which expects YYYY-MM-DDTHH:MM as the input format",
            "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
            """

            data = {
                "tenants_scope": ",".join(tenants_scope),
                "time_start": maintenance_mode_start,
                "time_end": maintenance_mode_end,
                "no_days_validity": 0,
                "reason": "TrackMe global maintenance",
                "type": "planned",
                "add_info": update_comment,
                "update_comment": update_comment,
            }

            header = {
                "Authorization": "Splunk %s" % request_info.session_key,
                "Content-Type": "application/json",
            }

            try:
                with requests.post(
                    f"{request_info.server_rest_uri}/services/trackme/v2/maintenance_kdb/admin/maintenance_kdb_add_record",
                    data=json.dumps(data),
                    headers=header,
                    verify=False,
                    timeout=600,
                ) as response:
                    response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
                    response_json = response.json()

                    # Process successful response
                    record_id = response_json.get("record_id")
                    logger.info(
                        f'Success creating the knowledge record, data="{json.dumps(response_json, indent=2)}"'
                    )

                    # Update the maintenance record with the new record_id
                    maintenance_record = collection.data.query_by_id(key)
                    maintenance_record["knowledge_record_id"] = record_id
                    maintenance_mode_response["knowledge_record_id"] = record_id
                    collection.data.update(key, json.dumps(maintenance_record))
                    logger.info(
                        f'Success updating the maintenance record, data="{json.dumps(collection.data.query_by_id(key), indent=2)}"'
                    )

            except requests.HTTPError as http_err:
                # Handle HTTP errors
                error_message = f'Failed to create the knowledge record, status_code={http_err.response.status_code}, response_text="{http_err.response.text}"'
                logger.error(error_message)
                return {
                    "payload": {"response": error_message},
                    "status": 500,
                }
            except Exception as e:
                # Handle other exceptions
                error_message = (
                    f'Failed to create the knowledge record, exception="{str(e)}"'
                )
                logger.error(error_message)
                return {
                    "payload": {"response": error_message},
                    "status": 500,
                }

        # render resoonse
        return {"payload": maintenance_mode_response, "status": 200}

    # Disable the maintenance mode
    def post_maintenance_disable(self, request_info, **kwargs):
        # Declare
        update_comment = None
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
                    resp_dict = json.loads(str(request_info.raw_args["payload"]))
                except Exception as e:
                    resp_dict = []

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

        else:
            # body is not required in this endpoint
            describe = False

        if describe:
            response = {
                "describe": "This endpoint disables the maintenance mode, it requires a POST call with the following information:",
                "resource_desc": "Disable global TrackMe maintenance mode",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/maintenance/maintenance_disable\" body=\"{'update_comment': 'All operations done, disabling global TrackMe maintenance mode.'}\"",
                "options": [
                    {
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # get current user
        username = request_info.user

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Set the collection
        collection_name = "kv_trackme_maintenance_mode"
        collection = service.kvstore[collection_name]

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        try:
            kvrecord = collection.data.query()[0]
            key = kvrecord.get("_key")

        except Exception as e:
            key = None

        # Set the response record
        response_maintenance_mode = {
            "tenants_scope": "*",  # disable maintenance for all tenants
            "maintenance": False,
            "maintenance_mode": "disabled",
            "maintenance_message": "The global maintenance mode is currently disabled, all alerts from TrackMe are permitted",
            "maintenance_comment": update_comment,
            "epoch_updated": round(time.time(), 0),
            "time_updated": time.strftime(
                "%Y-%m-%d %H:%M", time.localtime(time.time())
            ),
            "src_user": username,
        }

        # Process
        if key:
            # check the current status
            maintenance = kvrecord.get("maintenance")
            maintenance_mode = kvrecord.get("maintenance_mode")
            # maintenance knowledge database, check if we have a knowledge_record_id, if we do, call the endpoint with the stop_period
            knowledge_record_id = kvrecord.get("knowledge_record_id", None)

            # if maintenance is currently enabled, an update is required
            if maintenance or maintenance_mode == "scheduled":
                # Update the record
                collection.data.update(str(key), json.dumps(response_maintenance_mode))

                # record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    "all",
                    request_info.user,
                    "success",
                    "disable maintenance mode",
                    "all",
                    "all",
                    str(json.dumps(collection.data.query_by_id(key), indent=1)),
                    f'The maintenance mode was disabled successfully by user="{username}"',
                    str(update_comment),
                )

                # log
                logger.info(
                    f'TrackMe maintenance mode was disabled, record="{json.dumps(response_maintenance_mode, indent=2)}"'
                )

                # Maintenance Knowledge DataBase
                if knowledge_record_id:
                    data = {
                        "action": "stop_period",
                        "record_id": knowledge_record_id,
                        "update_comment": update_comment,
                    }

                    header = {
                        "Authorization": "Splunk %s" % request_info.session_key,
                        "Content-Type": "application/json",
                    }

                    try:
                        with requests.post(
                            f"{request_info.server_rest_uri}/services/trackme/v2/maintenance_kdb/admin/maintenance_kdb_manage_record",
                            data=json.dumps(data),
                            headers=header,
                            verify=False,
                            timeout=600,
                        ) as response:
                            response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
                            response_json = response.json()

                            # Process successful response
                            logger.info(
                                f'Success stopping the period of the knowledge record, data="{json.dumps(response_json, indent=2)}"'
                            )

                    except requests.HTTPError as http_err:
                        # Handle HTTP errors
                        error_message = f'Failed to stop the knowledge record period, status_code={http_err.response.status_code}, response_text="{http_err.response.text}"'
                        logger.error(error_message)
                        return {
                            "payload": {"response": error_message},
                            "status": 500,
                        }
                    except Exception as e:
                        # Handle other exceptions
                        error_message = f'Failed to stop the knowledge record period, exception="{str(e)}"'
                        logger.error(error_message)
                        return {
                            "payload": {"response": error_message},
                            "status": 500,
                        }

            else:
                # we haven't done any change, override the response
                response = {
                    "tenants_scope": "*",
                    "maintenance": False,
                    "maintenance_mode": kvrecord.get("maintenance_mode"),
                    "maintenance_message": kvrecord.get("maintenance_message"),
                    "maintenance_comment": kvrecord.get("maintenance_comment"),
                    "epoch_updated": kvrecord.get("epoch_updated"),
                    "time_updated": kvrecord.get("time_updated"),
                    "src_user": kvrecord.get("src_user"),
                }

                # log
                logger.info(
                    f'TrackMe maintenance mode disablement was requested, however it is already disabled, record="{json.dumps(response, indent=2)}"'
                )

        else:
            # Insert the record
            collection.data.insert(json.dumps(response))

            # record an audit change
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                request_info.user,
                "success",
                "disable maintenance mode",
                "all",
                "all",
                str(json.dumps(collection.data.query_by_id(key), indent=1)),
                f'The maintenance mode was disabled successfully by user="{username}"',
                str(update_comment),
            )

            # log
            logger.info(
                f'TrackMe maintenance mode was disabled, record="{json.dumps(response, indent=2)}"'
            )

        # render response
        return {
            "payload": collection.data.query()[0],
            "status": 200,
        }
