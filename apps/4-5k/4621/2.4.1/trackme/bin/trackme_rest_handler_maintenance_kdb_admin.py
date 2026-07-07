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

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.maintenance_kdb_admin", "trackme_rest_api_maintenance_kdb_admin.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_audit_event, trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerMaintenanceKdbAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerMaintenanceKdbAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_maintenance_kdb(self, request_info, **kwargs):
        response = {
            "resource_group_name": "maintenance_kdb/admmin",
            "resource_group_desc": "The maintenance knowledge database can be used to influence the SLA calculations by adding and maintaining knowledge of planned operations or outages, these endpoints cover admin operations only",
        }

        return {"payload": response, "status": 200}

    # Add a new maintenance knowledge record in the database
    def post_maintenance_kdb_add_record(self, request_info, **kwargs):
        # Declare

        tenants_scope = [
            "*"
        ]  # the scope of tenants, defaults to all tenants with *, expected as a comma separated list of tenant names to be turned into a list
        time_format = (
            None  # time format, defaults to epochtime, alternative is datestring
        )
        is_disabled = False  # if true, the maintenance record is disabled
        no_days_validity = 0  # number of days of validity, if set to 0, the maintenance record is valid forever
        time_expiration = None  # time of expiration of the maintenance record in epochtime, calculated automatically depending on no_days_validity
        reason = None  # reason for the maintenance
        type = None  # planned, unplanned
        add_info = None  # additional information
        src_user = request_info.user  # user who created the maintenance record
        time_start = None  # start time of the maintenance in epochtime
        time_end = None  # end time of the maintenance in epochtime
        ctime = round(time.time(), 0)  # creation time of the maintenance record
        mtime = round(
            time.time(), 0
        )  # last modification time of the maintenance record

        update_comment = None  # comment for the update, used for audit purposes
        describe = False  # describe the endpoint

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

                # tenants_scope
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

                # time_start
                time_start = resp_dict.get("time_start", None)
                if time_start is None:
                    return {
                        "payload": {
                            "response": "The time_start is a mandatory field, please specify it in the payload"
                        },
                        "status": 500,
                    }

                # time_end
                time_end = resp_dict.get("time_end", None)
                if time_end is None:
                    return {
                        "payload": {
                            "response": "The time_end is a mandatory field, please specify it in the payload"
                        },
                        "status": 500,
                    }

                # no_days_validity
                no_days_validity = resp_dict.get("no_days_validity", 0)
                # if not an integer, raise an exception
                if not isinstance(no_days_validity, int):
                    return {
                        "payload": {
                            "response": "The value for no_days_validity must be an integer, please correct your input"
                        },
                        "status": 500,
                    }

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

                # reason
                reason = resp_dict.get("reason", None)
                if reason is None:
                    return {
                        "payload": {
                            "response": "The reason is a mandatory field, please specify it in the payload"
                        },
                        "status": 500,
                    }

                # type
                type = resp_dict.get("type", None)
                if type is None:
                    return {
                        "payload": {
                            "response": "The type is a mandatory field, please specify it in the payload"
                        },
                        "status": 500,
                    }
                if type not in ("planned", "unplanned"):
                    return {
                        "payload": {
                            "response": "The type must be either planned or unplanned, please correct your input"
                        },
                        "status": 500,
                    }

                # add_info is optional
                add_info = resp_dict.get("add_info", "no additional information")

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
                "describe": "This endpoint adds a new maintenance record in the maintenance knowledge database, it requires a POST call with the following information:",
                "resource_desc": "Add a new maintenance knowledge record in the database",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/maintenance_kdb/admin/maintenance_kdb_add_record\" body=\"{'time_start': '2023-01-01T00:00', 'time_end': '2023-01-01T01:00', 'no_days_validity': 0, 'time_format': 'datestring', 'reason': 'planned maintenance', 'type': 'planned', 'add_info': 'additional information', 'update_comment': 'API update'}\"",
                "options": [
                    {
                        "tenants_scope": "OPTIONAL: the scope of tenants, defaults to all tenants with *, expected as a comma separated list of tenant identifiers",
                        "time_start": "MANDATORY: the start time of the maintenance, it can be specified in epochtime or datestring format",
                        "time_end": "MANDATORY: the end time of the maintenance, it can be specified in epochtime or datestring format",
                        "no_days_validity": "OPTIONAL: the number of days of validity of the maintenance record, if set to 0, the maintenance record is valid forever",
                        "reason": "MANDATORY: the reason for the maintenance",
                        "type": "MANDATORY: the type of the maintenance, it can be either planned or unplanned",
                        "add_info": "OPTIONAL: additional information about the maintenance",
                        "no_days_validity": "OPTIONAL: the number of days of validity of the maintenance record, if set to 0, the maintenance record is valid forever",
                        "time_format": "OPTIONAL: the time format when submitting start and end maintenance values, defaults to epochtime and can alternatively be set to datestring which expects YYYY-MM-DDTHH:MM as the input format",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        if time_format == "datestring":
            # convert maintenance start
            try:
                time_start_dt = datetime.datetime.strptime(
                    str(time_start), "%Y-%m-%dT%H:%M"
                )
                time_start = int(round(float(time_start_dt.timestamp())))
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Exception while trying to convert the input datestring, exception="{str(e)}"'
                    },
                    "status": 500,
                }

            # convert maintenance end
            try:
                time_end_dt = datetime.datetime.strptime(
                    str(time_end), "%Y-%m-%dT%H:%M"
                )
                time_end = int(round(float(time_end_dt.timestamp())))
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Exception while trying to convert the input datestring, exception="{str(e)}"'
                    },
                    "status": 500,
                }

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

        collection_name = "kv_trackme_maintenance_kdb"
        collection = service.kvstore[collection_name]

        # define time_expiration
        if no_days_validity == 0:
            time_expiration = 0
        else:
            time_expiration = int(round(time.time() + no_days_validity * 86400))

        # insert the new record, the KVstore key can be generated automatically and does not need to be specified
        new_record = {
            "tenants_scope": tenants_scope,
            "is_disabled": is_disabled,
            "no_days_validity": no_days_validity,
            "reason": reason,
            "type": type,
            "add_info": add_info,
            "src_user": src_user,
            "time_start": time_start,
            "time_end": time_end,
            "time_expiration": time_expiration,
            "ctime": ctime,
            "mtime": mtime,
        }

        try:
            # Insert the record
            kv_response = collection.data.insert(json.dumps(new_record))

            # record an audit change
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                request_info.user,
                "success",
                "add a new maintenance knowledge record in the database",
                "all",
                "all",
                new_record,
                f'The new maintenance knowledge record was added successfully by user="{src_user}"',
                str(update_comment),
            )

            # log
            logger.info(
                f'TrackMe new maintenance knowledge record added successfully to the database, record="{json.dumps(new_record, indent=2)}"'
            )

            # render response
            return {
                "payload": {
                    "response": f"TrackMe new maintenance knowledge record added successfully to the database, record_id={kv_response['_key']}",
                    "record": new_record,
                    "record_id": kv_response["_key"],
                },
                "status": 200,
            }

        except Exception as e:
            error_msg = f'An exception was encountered while attempting to add the new maintenance knowledge record, exception="{str(e)}", new_record="{json.dumps(new_record, indent=2)}"'
            logger.error(error_msg)
            return {
                "payload": {"response": error_msg},
                "status": 500,
            }

    # Manage an existing maintenance knowledge record in the database, allows to disable or enable a maintenance record, delete the record or update the time_end value
    def post_maintenance_kdb_manage_record(self, request_info, **kwargs):
        # Declare
        describe = False
        src_user = request_info.user

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

                # Get the record_id
                try:
                    record_id = resp_dict.get("record_id", None)
                    if record_id:
                        if not isinstance(record_id, list):
                            record_id = record_id.split(",")
                    else:
                        return {
                            "payload": {
                                "response": "The record_id is a mandatory field, please specify it in the payload"
                            },
                            "status": 500,
                        }

                except Exception as e:
                    return {
                        "payload": {
                            "response": f"The record_id is a mandatory field, please specify it in the payload, exception={str(e)}"
                        },
                        "status": 500,
                    }

                # Get the action
                try:
                    action = resp_dict["action"]
                    if action not in ("disable", "enable", "delete", "stop_period"):
                        error_msg = f'Invalid action="{action}" specified, valid options are: disable | enable | delete | stop_period'
                        logger.error(error_msg)
                        return {
                            "payload": {"response": error_msg},
                            "status": 500,
                        }

                except Exception as e:
                    return {
                        "payload": {
                            "response": "The action is a mandatory field, please specify it in the payload"
                        },
                        "status": 500,
                    }

                # Get the update_comment
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

        else:
            # body is not required in this endpoint
            describe = False

        if describe:
            response = {
                "describe": "This endpoint allows to manage an existing maintenance knowledge record in the database, it requires a POST call with the following information:",
                "resource_desc": "Manage an existing maintenance knowledge record in the database",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/maintenance_kdb/admin/maintenance_kdb_manage_record\" body=\"{'record_id': '1234567890', 'action': 'disable', 'update_comment': 'API update'}\"",
                "options": [
                    {
                        "record_id": "MANDATORY: the record id of the maintenance record to manage, to specify more than a single record, use a comma separated list of record ids",
                        "action": "MANDATORY: the action to perform, valid options are: disable | enable | delete | stop_period",
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

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )

        logger.setLevel(loglevel)

        collection_name = "kv_trackme_maintenance_kdb"
        collection = service.kvstore[collection_name]

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records = []

        # loop through the record ids
        for key in record_id:
            try:
                kvrecord = collection.data.query_by_id(key)
            except Exception as e:
                # increment counter
                processed_count += 1
                succcess_count += 0
                failures_count += 1

                # append for summary
                result = {
                    "record_id": key,
                    "action": "update",
                    "result": "failure",
                    "message": f'An exception was encountered while attempting to retrieve the maintenance record, exception="{str(e)}"',
                }
                records.append(result)
                break

            if action == "disable":
                # Update the record
                try:
                    kvrecord["is_disabled"] = True
                    kvrecord["mtime"] = round(time.time(), 0)
                    collection.data.update(str(key), json.dumps(kvrecord))

                except Exception as e:
                    error_msg = f'An exception was encountered while attempting to update the maintenance record, exception="{str(e)}"'
                    logger.error(error_msg)
                    return {
                        "payload": {"response": error_msg},
                        "status": 500,
                    }

                # record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    "all",
                    request_info.user,
                    "success",
                    "disable a maintenance knowledge record in the database",
                    "all",
                    "all",
                    kvrecord,
                    f'The maintenance knowledge record with record_id="{key}" was disabled successfully by user="{src_user}"',
                    str(update_comment),
                )

                # log
                logger.info(
                    f'TrackMe maintenance knowledge record with record_id="{key}" disabled successfully, record="{json.dumps(kvrecord, indent=2)}"'
                )

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # append for summary
                result = {
                    "record_id": key,
                    "action": "update",
                    "result": "success",
                    "message": f"The maintenance record was successfully disabled",
                }
                records.append(result)

            elif action == "enable":
                # Update the record
                try:
                    kvrecord["is_disabled"] = True
                    kvrecord["mtime"] = round(time.time(), 0)
                    collection.data.update(str(key), json.dumps(kvrecord))

                except Exception as e:
                    error_msg = f'An exception was encountered while attempting to update the maintenance record, exception="{str(e)}"'

                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # append for summary
                    result = {
                        "record_id": key,
                        "action": "update",
                        "result": "failure",
                        "message": error_msg,
                    }
                    records.append(result)

                # record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    "all",
                    request_info.user,
                    "success",
                    "enable a maintenance knowledge record in the database",
                    "all",
                    "all",
                    kvrecord,
                    f'The maintenance knowledge record with record_id="{key}" was enabled successfully by user="{src_user}"',
                    str(update_comment),
                )

                # log
                logger.info(
                    f'TrackMe maintenance knowledge record with record_id="{key}" enabled successfully, record="{json.dumps(kvrecord, indent=2)}"'
                )

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # append for summary
                result = {
                    "record_id": key,
                    "action": "update",
                    "result": "success",
                    "message": f"The maintenance record was successfully enabled",
                }
                records.append(result)

            elif action == "stop_period":
                # Update the record
                try:
                    kvrecord["time_end"] = round(time.time(), 0)
                    kvrecord["mtime"] = round(time.time(), 0)
                    collection.data.update(str(key), json.dumps(kvrecord))

                except Exception as e:
                    error_msg = f'An exception was encountered while attempting to update the maintenance record, exception="{str(e)}"'

                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # append for summary
                    result = {
                        "record_id": key,
                        "action": "update",
                        "result": "failure",
                        "message": error_msg,
                    }
                    records.append(result)

                # record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    "all",
                    request_info.user,
                    "success",
                    "stop the period of a maintenance knowledge record in the database",
                    "all",
                    "all",
                    kvrecord,
                    f'The maintenance knowledge record period with record_id="{key}" was stopped successfully by user="{src_user}"',
                    str(update_comment),
                )

                # log
                logger.info(
                    f'TrackMe maintenance knowledge record period with record_id="{key}" was stopped successfully, record="{json.dumps(kvrecord, indent=2)}"'
                )

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # append for summary
                result = {
                    "record_id": key,
                    "action": "update",
                    "result": "success",
                    "message": f"The maintenance record end period was successfully stopped",
                }
                records.append(result)

            elif action == "delete":
                # Delete the record
                try:
                    collection.data.delete(json.dumps({"_key": key}))
                except Exception as e:
                    error_msg = f'An exception was encountered while attempting to delete the maintenance record, exception="{str(e)}"'

                    # increment counter
                    processed_count += 1
                    succcess_count += 0
                    failures_count += 1

                    # append for summary
                    result = {
                        "record_id": key,
                        "action": "update",
                        "result": "failure",
                        "message": error_msg,
                    }
                    records.append(result)

                # record an audit change
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    "all",
                    request_info.user,
                    "success",
                    "delete a maintenance knowledge record in the database",
                    "all",
                    "all",
                    kvrecord,
                    f'The maintenance knowledge record with record_id="{key}" was deleted successfully by user="{src_user}"',
                    str(update_comment),
                )

                # log
                logger.info(
                    f'TrackMe maintenance knowledge record with record_id="{key}" deleted successfully, record="{json.dumps(kvrecord, indent=2)}"'
                )

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # append for summary
                result = {
                    "record_id": key,
                    "action": "delete",
                    "result": "success",
                    "message": f"The maintenance record was successfully deleted",
                }
                records.append(result)

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

    # Check and verify if a maintenance knowledge record is expired, if so, disable it
    def post_maintenance_kdb_check_expired(self, request_info, **kwargs):
        # Declare
        describe = False
        src_user = request_info.user

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

                # Get the update_comment
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

        else:
            # body is not required in this endpoint
            describe = False

        if describe:
            response = {
                "describe": "This endpoint allows to check and verify if a maintenance knowledge record is expired, if so, disable it, it requires a POST call with no options:",
                "resource_desc": "Check and verify if a maintenance knowledge record is expired, if so, disable it",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/maintenance_kdb/admin/maintenance_kdb_check_expired"',
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

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )

        logger.setLevel(loglevel)

        collection_name = "kv_trackme_maintenance_kdb"
        collection = service.kvstore[collection_name]

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records = []

        # Get records
        try:
            records = collection.data.query()
        except Exception as e:
            error_msg = f'An exception was encountered while attempting to retrieve maintenance knowledge database records, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {"response": error_msg},
                "status": 500,
            }

        # loop through the records, check if the time_expiration is set (different from 0) and if it is now in the past, if so, disable the record
        for record in records:
            if record["time_expiration"] != 0:
                if record["time_expiration"] < round(time.time(), 0):
                    # Update the record
                    try:
                        record["is_disabled"] = True
                        record["mtime"] = round(time.time(), 0)
                        collection.data.update(str(record["_key"]), json.dumps(record))

                    except Exception as e:
                        error_msg = f'An exception was encountered while attempting to update the maintenance record, exception="{str(e)}"'

                        # increment counter
                        processed_count += 1
                        succcess_count += 0
                        failures_count += 1

                        # append for summary
                        result = {
                            "record_id": record["_key"],
                            "action": "update",
                            "result": "failure",
                            "message": error_msg,
                        }
                        records.append(result)

                    # record an audit change
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        "all",
                        request_info.user,
                        "success",
                        "disable a maintenance knowledge record in the database due to expiration",
                        "all",
                        "all",
                        record,
                        f'The maintenance knowledge record with record_id="{record["_key"]}" was disabled successfully as it now expired',
                        str(update_comment),
                    )

                    # log
                    logger.info(
                        f'TrackMe maintenance knowledge record with record_id="{record["_key"]}" disabled successfully as it is now expired, record="{json.dumps(record, indent=2)}"'
                    )

                    # increment counter
                    processed_count += 1
                    succcess_count += 1
                    failures_count += 0

                    # append for summary
                    result = {
                        "record_id": record["_key"],
                        "action": "update",
                        "result": "success",
                        "message": f"The maintenance record was successfully disabled as it is now expired",
                    }
                    records.append(result)

        # render HTTP status and summary

        req_summary = {
            "context": "Maintenance knowledge database expiration check for records",
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "records": records,
            "no_records": len(records),
        }

        if processed_count == 0:
            req_summary["status"] = "success"
            return {
                "payload": {
                    "context": "Maintenance knowledge database expiration check for records",
                    "result": f"No maintenance records in the maintenance knowldege database were found to be expired",
                    "no_records": len(records),
                },
                "status": 200,
            }

        elif processed_count > 0 and processed_count == succcess_count:
            req_summary["status"] = "success"
            req_summary["result"] = (
                f"All maintenance records in the maintenance knowldege database were checked and found to be expired, they were disabled successfully"
            )
            return {"payload": req_summary, "status": 200}

        else:
            req_summary["status"] = "failure"
            req_summary["result"] = (
                f"Some maintenance records in the maintenance knowldege database were checked and found to be expired, however some of them could not be disabled"
            )
            return {"payload": req_summary, "status": 500}

    # Bulk edit (to be used from the inline Tabulator)
    def post_maintenance_kdb_bulk_edit(self, request_info, **kwargs):
        # perf counter
        start_time = time.time()

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                json_data = resp_dict["json_data"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs a bulk edit, it requires a POST call with the following information:",
                "resource_desc": "Perform a bulk edit to one or more entities",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_dsm/admin/maintenance_kdb_bulk_edit" mode="post" body="<redacted json>"',
                "options": [
                    {
                        "json_data": "The JSON array object",
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

        # counters
        failures_count = 0

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.session_key,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Data collection
        collection_name = "kv_trackme_maintenance_kdb"
        collection = service.kvstore[collection_name]

        # get all records
        get_collection_start = time.time()
        collection_records = []
        collection_records_keys = set()

        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    if item.get("_key") not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item.get("_key"))
                skip_tracker += len(process_collection_records)
            else:
                end = True

        # turn it into a dict for fast operations
        collection_dict = {record["_key"]: record for record in collection_records}

        # len collection_records
        collection_records_len = len(collection_records)

        logger.info(
            f'context="perf", get collection records, no_records="{collection_records_len}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        # final records
        entities_list = []
        final_records = []

        # error counters and exceptions
        failures_count = 0
        exceptions_list = []

        # loop and proceed
        for json_record in json_data:
            keys_to_check = [
                "is_disabled",
                "reason",
                "add_info",
                "type",
            ]

            key = json_record["_key"]

            try:
                if key in collection_dict:
                    current_record = collection_dict[key]

                    is_different = False
                    for key in keys_to_check:
                        new_value = json_record.get(key)
                        if current_record.get(key) != new_value:
                            is_different = True
                            current_record[key] = new_value

                    if is_different:
                        current_record["mtime"] = time.time()

                        # Add for batch update
                        final_records.append(current_record)

                        # Add for reporting
                        entities_list.append(current_record.get("_key"))
                else:
                    raise KeyError(f"Resource not found for key {key}")

            except Exception as e:
                # increment counter
                failures_count += 1
                exceptions_list.append(
                    f'failed to update the entity, key="{key}", exception="{str(e)}"'
                )

        # batch update/insert
        batch_update_collection_start = time.time()

        # process by chunk
        chunks = [final_records[i : i + 500] for i in range(0, len(final_records), 500)]
        for chunk in chunks:
            try:
                collection.data.batch_save(*chunk)
            except Exception as e:
                logger.error(f'KVstore batch failed with exception="{str(e)}"')
                failures_count += 1
                exceptions_list.append(str(e))

        # calculate len(final_records) once
        final_records_len = len(final_records)

        # perf counter for the batch operation
        logger.info(
            f'context="perf", batch KVstore update terminated, no_records="{final_records_len}", run_time="{round((time.time() - batch_update_collection_start), 3)}"'
        )

        # Record an audit change
        for record in final_records:
            status = "success" if failures_count == 0 else "failure"
            message = (
                "Entity was updated successfully"
                if failures_count == 0
                else "Entity bulk update has failed"
            )
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                request_info.user,
                status,
                "inline bulk edit",
                record.get("_key"),
                "all",
                (
                    json.dumps(record, indent=1)
                    if failures_count == 0
                    else exceptions_list
                ),
                message,
                str(update_comment),
            )

        if failures_count == 0:
            req_summary = {
                "process_count": final_records_len,
                "failures_count": failures_count,
                "entities_list": entities_list,
            }
            logger.info(
                f'entity bulk edit was successful, no_modified_records="{final_records_len}", no_records="{collection_records_len}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}", results="{json.dumps(req_summary, indent=1)}"'
            )
            return {"payload": req_summary, "status": 200}

        else:
            req_summary = {
                "process_count": final_records_len,
                "failures_count": failures_count,
                "entities_list": entities_list,
                "exceptions": exceptions_list,
            }
            logger.error(
                f'entity bulk edit has failed, no_modified_records="{final_records_len}", no_records="{collection_records_len}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}", results="{json.dumps(req_summary, indent=1)}"'
            )
            return {"payload": req_summary, "status": 500}
