#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_data_sampling.py"
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

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_data_sampling_power",
    "trackme_rest_api_splk_data_sampling_power.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_audit_event, trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDataSamplingWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDataSamplingWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_data_sampling(self, request_info, **kwargs):
        response = {
            "resource_group_name": "data_sampling/write",
            "resource_group_desc": "Endpoints for the data sampling events recognition engine (power operations)",
        }

        return {"payload": response, "status": 200}

    # Add new model
    def post_data_sampling_models_add(self, request_info, **kwargs):
        r"""
        | trackme mode=post url=\"/services/trackme/v2/splk_data_sampling/write/data_sampling_models_add\" body=\"{'tenant_id':'mytenant', 'model_name':'Netscreen', 'model_type':'inclusive', 'model_regex':':\sNetScreen\sdevice_id=', 'sourcetype_scope': 'netscreen:firewall'}\"
        """

        # Declare
        tenant_id = None
        model_name = None
        model_regex = None
        model_type = None

        query_string = None

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                model_name = resp_dict["model_name"]
                model_regex = resp_dict["model_regex"]
                model_type = resp_dict["model_type"]

                # Update comment is optional and used for audit changes
                try:
                    update_comment = resp_dict["update_comment"]
                except Exception as e:
                    update_comment = "API update"

                # sourcetype_scope is optional, if unset it will be defined to * (any)
                try:
                    sourcetype_scope = resp_dict["sourcetype_scope"]
                except Exception as e:
                    sourcetype_scope = "*"

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new data sampling custom model, it requires a POST call with the following data:",
                "resource_desc": "Add new Data Sampling custom model",
                "resource_spl_example": r"| trackme mode=post url=\"/services/trackme/v2/splk_data_sampling/write/data_sampling_models_add\" body=\"{'tenant_id':'mytenant', 'model_name':'Netscreen', 'model_type':'inclusive', 'model_regex':':\\\sNetScreen\\\sdevice_id=', 'sourcetype_scope': 'netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "model_name": "REQUIRED. Name of the custom model",
                        "model_regex": "REQUIRED. The regular expression to be used by the custom model. Special characters should be escaped",
                        "model_type": "REQUIRED. The type of match for this model — one of: \"inclusive\" (rule must match) or \"exclusive\" (rule must not match)",
                        "sourcetype_scope": "OPTIONAL. Value of the sourcetype to match (defaults to \"*\"). Can be a comma-separated list of sourcetypes — wildcards and spaces should not be used",
                        "update_comment": "OPTIONAL. Comment recorded in the audit log for this change. Defaults to 'API update' when omitted",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Define the KV query
        query_string = {
            "model_name": model_name,
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
            collection_name = (
                "kv_trackme_dsm_data_sampling_custom_models_tenant_" + str(tenant_id)
            )
            collection = service.kvstore[collection_name]

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                kvrecord = collection.data.query(query=json.dumps(query_string))[0]
                key = kvrecord.get("_key")

            except Exception as e:
                key = None

            # Render result
            if key and model_type in ("inclusive", "exclusive"):
                # This record exists already
                model_id = kvrecord.get("model_id")

                # Update the record
                newrecord = {
                    "model_name": model_name,
                    "model_regex": model_regex,
                    "model_type": model_type,
                    "model_id": model_id,
                    "sourcetype_scope": sourcetype_scope,
                    "mtime": time.time(),
                }
                collection.data.update(str(key), json.dumps(newrecord))

                # audit event
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "add data parsing custom rule",
                    str(model_name),
                    "splk-dsm",
                    str(json.dumps(kvrecord, indent=1)),
                    "Data sampling custom parsing rule was updated successfully",
                    str(update_comment),
                )

                # render response
                return {"payload": kvrecord, "status": 200}

            elif model_type in ("inclusive", "exclusive"):
                # This record does not exist yet

                import hashlib

                model_id = hashlib.sha256(model_name.encode("utf-8")).hexdigest()

                # Insert the record
                newrecord = {
                    "model_name": model_name,
                    "model_regex": model_regex,
                    "model_type": model_type,
                    "model_id": model_id,
                    "sourcetype_scope": sourcetype_scope,
                    "mtime": time.time(),
                }
                collection.data.insert(json.dumps(newrecord))

                # audit event
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    tenant_id,
                    request_info.user,
                    "success",
                    "add data parsing custom rule",
                    str(model_name),
                    "splk-dsm",
                    str(json.dumps(newrecord, indent=1)),
                    "Data sampling custom parsing rule was added successfully",
                    str(update_comment),
                )

                # render response
                return {"payload": newrecord, "status": 200}

            else:
                logger.error("bad request")
                return {"payload": "bad request", "status": 404}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Delete records from the collection
    def post_data_sampling_models_del(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/splk_data_sampling/write/data_sampling_models_del\" body=\"{'tenant_id':'mytenant', 'models_list':'Netscreen'\"}
        """

        # Declare
        tenant_id = None
        models_list = None
        query_string = None

        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                models_list = resp_dict["models_list"]
                # if not a list already, convert to a list from comma separated string
                if not isinstance(models_list, list):
                    models_list = models_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes data sampling models, it requires a POST call with the following information:",
                "resource_desc": "Delete Data Sampling custom model",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_data_sampling/write/data_sampling_models_del\" body=\"{'tenant_id':'mytenant', 'models_list':'Netscreen'\"}",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "models_list": "List of record keys separated by a comma of the records to be deleted from the collection",
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
        collection_name = "kv_trackme_dsm_data_sampling_custom_models_tenant_" + str(
            tenant_id
        )
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # loop
        for item in models_list:
            # Try to find the record by _key first (for backward compatibility)
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
                kvrecord = None

            # If not found by _key, try model_id (for new UI calls)
            if not key:
                query_string = {
                    "model_id": item,
                }
                try:
                    kvrecord = collection.data.query(query=json.dumps(query_string))[0]
                    key = kvrecord.get("_key")
                except Exception as e:
                    key = None
                    kvrecord = None

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
                        "delete data sampling model",
                        str(item),
                        "all",
                        str(kvrecord),
                        "The lagging class was deleted successfully",
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
                        "delete data sampling model",
                        str(item),
                        "all",
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
                    "delete data sampling model",
                    str(item),
                    "all",
                    "none",
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
    def post_data_sampling_models_update(self, request_info, **kwargs):
        # Declare
        tenant_id = None
        records_list = None
        query_string = None

        describe = False

        # component is static
        component = "splk-dsm"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                records_list = resp_dict["records_list"]
                # handle records_list, if not an object attempt json loads
                if not isinstance(records_list, list) and not isinstance(records_list, dict):
                    try:
                        records_list = json.loads(records_list)
                    except Exception as e:
                        return {
                            "payload": f"records_list is not a valid JSON: {str(e)}",
                            "status": 500,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint updates records, it requires a POST call with the following information:",
                "resource_desc": "Update Data Sampling custom models",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_data_sampling/write/data_sampling_models_update\" body=\"{'tenant_id':'mytenant','component':'splk-dsm','records_list':'<redacted_json_records>'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
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

        # Data collection
        collection_name = "kv_trackme_dsm_data_sampling_custom_models_tenant_" + str(
            tenant_id
        )
        collection = service.kvstore[collection_name]

        # records summary
        records = []

        # debug
        logger.info(f'records_list="{json.dumps(records_list, indent=0)}"')

        # loop
        for item in records_list:
            # debug
            logger.info(f'item="{item}"')

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
                # Update and audit
                try:
                    # Update the record
                    newrecord = {
                        "model_id": item.get("model_id"),
                        "model_name": item.get("model_name"),
                        "model_regex": item.get("model_regex"),
                        "model_type": item.get("model_type"),
                        "sourcetype_scope": item.get("sourcetype_scope"),
                        "mtime": time.time(),
                    }
                    collection.data.update(str(key), json.dumps(newrecord))

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
                        "update data sampling models",
                        str(item),
                        str(component),
                        json.dumps(item, indent=1),
                        "The data sampling model was updated successfully",
                        str(update_comment),
                    )

                    result = {
                        "action": "delete",
                        "result": "success",
                        "record": newrecord,
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
                        "update data sampling models",
                        str(item),
                        str(component),
                        str(newrecord),
                        str(e),
                        str(update_comment),
                    )

                    result = {
                        "action": "delete",
                        "result": "failure",
                        "record": newrecord,
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
                    "update data sampling models",
                    str(item),
                    str(component),
                    "none",
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
