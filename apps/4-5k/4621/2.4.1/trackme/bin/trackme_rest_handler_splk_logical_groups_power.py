#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_logical_groups.py"
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
    "trackme.rest.splk_logical_groups_power",
    "trackme_rest_api_splk_logical_groups_power.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_audit_event, trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkLogicalGroupsWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkLogicalGroupsWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_logical_groups(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_logical_groups/write",
            "resource_group_desc": "Endpoints related to the management of logical groups (power operations)",
        }

        return {"payload": response, "status": 200}

    # Bulk edit (to be used from the inline Tabulator)
    def post_logical_groups_bulk_edit(self, request_info, **kwargs):
        """
        This function performs a bulk edit on given json data.
        :param request_info: Contains request related information
        :param kwargs: Other keyword arguments
        :return: Status and payload of the bulk edit operation
        """

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
                tenant_id = resp_dict["tenant_id"]
                json_data = resp_dict["json_data"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint performs a bulk edit, it requires a POST call with the following information:",
                "resource_desc": "Perform a bulk edit to one or more entities",
                "resource_spl_example": '| trackme url="/services/trackme/v2/splk_logical_groups/write/logical_groups_bulk_edit" mode="post" body="{\'tenant_id\':\'mytenant\', '
                + "'json_data':[<redacted json data>]}\"",
                "options": [
                    {
                        "tenant_id": "Tenant identifier",
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

        # Data collection
        collection_name = f"kv_trackme_common_logical_group_tenant_{tenant_id}"
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

        # log debug
        logger.debug(f'received json_data="{json_data}"')

        try:
            json_data = json.loads(json_data)
        except:
            pass

        # loop and proceed
        for json_record in json_data:
            keys_to_check = [
                "object_group_name",
                "object_group_min_green_percent",
                "object_group_members",
            ]

            object_group_key = json_record["_key"]

            try:
                if object_group_key in collection_dict:
                    current_record = collection_dict[object_group_key]

                    is_different = False
                    for key in keys_to_check:
                        new_value = json_record.get(key)
                        if current_record.get(key) != new_value:
                            is_different = True
                            current_record[key] = new_value

                    if is_different:
                        current_record["object_group_mtime"] = time.time()

                        # Add for batch update
                        final_records.append(current_record)

                        # Add for reporting
                        entities_list.append(current_record.get("_key"))
                else:
                    raise KeyError(f"Resource not found for object {object_group_key}")

            except Exception as e:
                # increment counter
                failures_count += 1
                exceptions_list.append(
                    f'tenant_id="{tenant_id}", failed to update the entity, object="{object_group_key}", exception="{str(e)}"'
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
                tenant_id,
                request_info.user,
                status,
                "inline bulk edit",
                record.get("object"),
                "splk-dsm",
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

    # Add a new group
    def post_logical_groups_add_grp(self, request_info, **kwargs):
        # define
        tenant_id = None
        object_group_name = None
        object_group_members = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                object_group_name = resp_dict["object_group_name"]

                try:
                    object_group_members = resp_dict["object_group_members"]
                    # object_group_members is expected as a comma separated list of values
                    # We accept comma with or without a space after the separator, let's remove any space after the separator
                    object_group_members = object_group_members.replace(", ", ",")
                    # Split by the separator
                    object_group_members = object_group_members.split(",")
                except Exception as e:
                    object_group_members = []

                # group min percentage is optional and set to 50% if not provided
                try:
                    object_group_min_green_percent = resp_dict[
                        "object_group_min_green_percent"
                    ]
                except Exception as e:
                    object_group_min_green_percent = "50"

                # if object_group_min_green_percent is not a number, raise a 500
                try:
                    object_group_min_green_percent = float(
                        object_group_min_green_percent
                    )
                except Exception as e:
                    response = {
                        "action": "failure",
                        "response": "object_group_min_green_percent is not a number",
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint creates a new logical group, if the group exists already, members mentioned in the query (if any) will be added to the group, it requires a POST call with the following data required:",
                "resource_desc": "Create a new logical group, update if exists already",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/write/logical_groups_add_grp\" body=\"{'tenant_id': 'mytenant', 'object_group_name': 'grp-lb001', 'object_group_members': 'lb-001,lb-002', 'object_group_min_green_percent': '50'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                        "object_group_name": "name of the logical group to be created",
                        "object_group_members": "OPTIONAL: comma separated list of the group members, if not provided and the group exists already the current value will be preserved, will be set to empty group if the the group does not exist yet",
                        "object_group_min_green_percent": "OPTIONAL: minimal percentage of hosts that need to be green for the logical group to be green, if unset defaults to 50. Recommended options for this value: 12.5 / 33.33 / 50",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Retrieve from data
        resp_dict = json.loads(str(request_info.raw_args["payload"]))

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Define the KV query
        query_string = {
            "object_group_name": object_group_name,
        }

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            collection_name = "kv_trackme_common_logical_group_tenant_" + str(tenant_id)
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=600,
            )
            collection = service.kvstore[collection_name]

            # update time for the object
            object_group_mtime = time.time()

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None
                record = json.dumps(
                    {
                        "object_group_name": object_group_name,
                        "object_group_members": object_group_members,
                        "object_group_min_green_percent": str(
                            object_group_min_green_percent
                        ),
                        "object_group_mtime": str(object_group_mtime),
                    }
                )

            # if the group exists already, retrieve its existing members and add our new members
            if key:
                # set an action_desc
                action_desc = "update"

                # create a new list
                object_group_members_new = []

                # add existing members
                for object_group_existing_member in record[0].get(
                    "object_group_members"
                ):
                    object_group_members_new.append(object_group_existing_member)

                # add our new members, if not in there already
                for object_group_new_member in object_group_members:
                    if object_group_new_member not in object_group_members_new:
                        object_group_members_new.append(object_group_new_member)

            else:
                # set an action_desc
                action_desc = "create"

            # proceed
            try:
                if key:
                    # Update the record
                    collection.data.update(
                        str(key),
                        json.dumps(
                            {
                                "object_group_name": object_group_name,
                                "object_group_members": object_group_members_new,
                                "object_group_min_green_percent": str(
                                    object_group_min_green_percent
                                ),
                                "object_group_mtime": str(object_group_mtime),
                            }
                        ),
                    )

                else:
                    # Insert the record
                    collection.data.insert(
                        json.dumps(
                            {
                                "object_group_name": object_group_name,
                                "object_group_members": object_group_members,
                                "object_group_min_green_percent": str(
                                    object_group_min_green_percent
                                ),
                                "object_group_mtime": str(object_group_mtime),
                            }
                        )
                    )

                # Record an audit change
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "Logical group add",
                        str(object_group_name),
                        "logical_group",
                        collection.data.query(query=json.dumps(query_string)),
                        "The logical group was added successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                # render response
                response = {
                    "action": "success",
                    "action_desc": action_desc,
                    "record": collection.data.query(query=json.dumps(query_string)),
                }

                logger.info(json.dumps(response, indent=2))
                return {"payload": response, "status": 200}

            except Exception as e:
                # Record an audit change
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "Logical group add",
                        str(object_group_name),
                        "logical_group",
                        collection.data.query(query=json.dumps(query_string)),
                        "The logical group failed to be created",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                # render response
                response = {
                    "action": "failure",
                    "action_desc": action_desc,
                    "response": f'failed to {action_desc} the KVstore record, exception="{str(e)}"',
                }
                logger.error(json.dumps(response, indent=2))
                return {"payload": response, "status": 500}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Delete group
    def post_logical_groups_del_grp(self, request_info, **kwargs):
        # define
        tenant_id = None
        object_group_name = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]

                object_group_name = resp_dict.get("object_group_name", [])
                # if not a list, turn into a list from CSV
                if not isinstance(object_group_name, list):
                    object_group_name = object_group_name.split(",")

                object_group_key = resp_dict.get("object_group_key", [])
                # if not a list, turn into a list from CSV
                if not isinstance(object_group_key, list):
                    object_group_key = object_group_key.split(",")

                # if both object_group_name and object_group_key are empty or not provided, raise a 500
                if not object_group_name and not object_group_key:
                    response = {
                        "action": "failure",
                        "response": "both object_group_name and object_group_key are empty or not provided",
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

                # else if both are provided in the same time, raise a 500
                elif object_group_name and object_group_key:
                    response = {
                        "action": "failure",
                        "response": "both object_group_name and object_group_key are provided, please provide only one of them",
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint deletes a logical group, it requires a POST call with the following data required:",
                "resource_desc": "Delete a logical group and all membership related to it",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/write/logical_groups_del_grp\" body=\"{'tenant_id': 'mytenant', 'object_group_name': 'grp-lb001'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                        "object_group_name": "(OPTIONAL: submit either by group name or by group key) A comma separated list of logical group names to be deleted",
                        "object_group_key": "(OPTIONAL: submit either by group name or by group key) A comma separated list of logical group keys to be deleted",
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

        # Define the KV query
        query_string = {
            "object_group_name": object_group_name,
        }

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records_summary = []

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # collection
        collection_name = f"kv_trackme_common_logical_group_tenant_{tenant_id}"
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.session_key,
            timeout=600,
        )
        collection = service.kvstore[collection_name]

        # keys list
        keys_list = []

        # if by object_group_key, loop through the list and add each key to keys_list
        if object_group_key:
            for object_group_key_value in object_group_key:
                keys_list.append(object_group_key_value)

        # else by object_group_name, loop through the list, atteempt to retriebve the corresponding key and add it to keys_list
        else:
            for object_group_name_value in object_group_name:
                try:
                    record = collection.data.query(
                        query=json.dumps({"object_group_name": object_group_name_value})
                    )
                    key = record[0].get("_key")
                    keys_list.append(key)
                except Exception as e:
                    key = None

        # loop through the keys_list and delete each record
        for key in keys_list:
            # Proceed
            try:
                # Remove the record
                collection.data.delete(json.dumps({"_key": key}))

                # Record an audit change
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "Logical group delete",
                        str(object_group_name),
                        "logical_group",
                        collection.data.query(query=json.dumps(query_string)),
                        "The logical group was deleted successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                # increment counter
                processed_count += 1
                succcess_count += 1
                failures_count += 0

                # render response
                response = {
                    "action": "success",
                    "action_desc": "delete",
                    "response": f'the record for object_group_name="{object_group_name}" was deleted successfully',
                    "record": record,
                }

                logger.info(json.dumps(response, indent=2))
                records_summary.append(response)

            except Exception as e:
                # render response
                response = {
                    "action": "failure",
                    "action_desc": "delete",
                    "response": f'failed to delete the KVstore record with exception="{str(e)}"',
                }

                logger.error(json.dumps(response, indent=2))
                records_summary.append(response)

        # render HTTP status and summary
        req_summary = {
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "records": records_summary,
        }

        if processed_count > 0 and processed_count == succcess_count:
            return {"payload": req_summary, "status": 200}

        else:
            return {"payload": req_summary, "status": 500}

    # Associate a logical group with a member
    def post_logical_groups_associate_group(self, request_info, **kwargs):
        # define
        tenant_id = None
        object_list = None
        object_group_name = None
        object_group_min_green_percent = None
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
                action = resp_dict["action"]
                object_list = resp_dict["object_list"]
                # turns into a list
                object_list = object_list.split(",")
                object_group_name = resp_dict["object_group_name"]
                # optional
                try:
                    object_group_min_green_percent = resp_dict[
                        "object_group_min_green_percent"
                    ]
                except Exception as e:
                    object_group_min_green_percent = 50

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint associates/unassociates an object with a logical group, "
                + "if action is associate and the logical group does not exist, it will be created. "
                "it requires a POST call with the following data required:",
                "resource_desc": "Manage association on a logical group",
                "resource_spl_example": "| trackme mode=\"post\" url=\"/services/trackme/v2/splk_logical_groups/write/logical_groups_associate_group\" body=\"{'tenant_id': 'mytenant', 'object_group_name': 'object_group_name': 'grp-lb001', 'action': 'unassociate', 'object_list': 'lb-002,lb-003'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                        "object_group_name": "The logical group name",
                        "action": "The action to be performed, valid options are: associate | unassociate",
                        "object_list": "comma separated list of entities to be associated with or unassociated from this logical group",
                        "object_group_min_green_percent": "OPTIONAL, if the group does not exist and is created, optionally specify the min green percentage (defaults to 50)",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Retrieve from data
        resp_dict = json.loads(str(request_info.raw_args["payload"]))

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            # Define the KV query
            query_string = {
                "object_group_name": object_group_name,
            }

            # collection
            collection_name = "kv_trackme_common_logical_group_tenant_" + str(tenant_id)
            service = client.connect(
                owner="nobody",
                app="trackme",
                port=splunkd_port,
                token=request_info.session_key,
                timeout=600,
            )
            collection = service.kvstore[collection_name]

            # Get the record
            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None

            # Render result

            # if unassociate but there is no record, then there is nothing we can do
            if not key and action == "unassociate":
                response = {
                    "action": "failure",
                    "response": f'object_group_name="{object_group_name}" not found',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 404}

            # else if there is no record but action is associate
            elif not key and action == "associate":
                # set new record
                record = {
                    "object_group_name": object_group_name,
                    "object_group_min_green_percent": object_group_min_green_percent,
                    "object_group_members": object_list,
                    "object_group_mtime": time.time(),
                }

                # Update the record
                try:
                    collection.data.insert(json.dumps(record))

                    # register an audit event
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "success",
                            "create and associate logical group",
                            str(object_group_name),
                            "logical_group",
                            collection.data.query(query=json.dumps(query_string)),
                            "The logical group was created successfully",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    # render
                    response = {
                        "action": "success",
                        "response": f'A new logical group object_group_name="{object_group_name}" was successfully created and associated with object_list="{object_list}"',
                        "record": collection.data.query(query=json.dumps(query_string)),
                    }
                    logger.info(json.dumps(response))
                    return {"payload": response, "status": 200}

                except Exception as e:
                    response = {
                        "action": "failure",
                        "response": f'an exception was encountered, exception="{str(e)}"',
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

            else:
                # get current list of associated objects with that logical group, if any
                object_new_list = []
                try:
                    object_current_list = record[0].get("object_group_members")
                except Exception as e:
                    object_current_list = None

                # Loop if we have a value
                if object_current_list:
                    if isinstance(object_current_list, list):
                        for object_value in object_current_list:
                            object_new_list.append(object_value)
                    else:
                        object_new_list.append(record[0].get("object_group_members"))

                # Loop through the submitted list of object, and act depending on the requested action
                for object_value in object_list:
                    if action == "associate":
                        if object_value not in object_new_list:
                            object_new_list.append(object_value)
                    elif action == "unassociate":
                        if object_value in object_new_list:
                            object_new_list.remove(object_value)

                # set new record
                record = {
                    "object_group_name": object_group_name,
                    "object_group_min_green_percent": record[0].get(
                        "object_group_min_green_percent"
                    ),
                    "object_group_members": object_new_list,
                    "object_group_mtime": time.time(),
                }

                # Update the record
                try:
                    collection.data.update(str(key), record)

                    # Record an audit change
                    for object_value in object_list:
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "success",
                                "associate logical group",
                                str(object_value),
                                "logical_group",
                                collection.data.query_by_id(key),
                                "The object was associated successfully",
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )

                    # render
                    if action == "associate":
                        response = {
                            "action": "success",
                            "response": f'the following objects="{object_list}" where successfully associated with the object_group_name="{object_group_name}"',
                            "record": collection.data.query(
                                query=json.dumps(query_string)
                            ),
                        }

                    elif action == "unassociate":
                        response = {
                            "action": "success",
                            "response": f'the following objects="{object_list}" where successfully unassociated from the object_group_name="{object_group_name}"',
                            "record": collection.data.query(
                                query=json.dumps(query_string)
                            ),
                        }

                    # log
                    logger.info(json.dumps(response, indent=4))

                    return {"payload": response, "status": 200}

                except Exception as e:
                    # register an audit event
                    try:
                        trackme_audit_event(
                            request_info.system_authtoken,
                            request_info.server_rest_uri,
                            tenant_id,
                            request_info.user,
                            "failure",
                            "associate logical group",
                            str(object_value),
                            "logical_group",
                            collection.data.query_by_id(key),
                            "The object failed to be associated",
                            str(update_comment),
                        )
                    except Exception as e:
                        logger.error(
                            f'failed to generate an audit event with exception="{str(e)}"'
                        )

                    # render response
                    response = {
                        "action": "failure",
                        "response": f'an exception was encountered, exception="{str(e)}"',
                    }
                    logger.error(json.dumps(response))
                    return {"payload": response, "status": 500}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'general exception, an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Admnistrative endpoint designed to update group members and red/green lists
    def post_logical_groups_update_group_list(self, request_info, **kwargs):
        # define
        tenant_id = None
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
                object_group_key = resp_dict["object_group_key"]
                object_group_members_green = resp_dict["object_group_members_green"]
                object_group_members_red = resp_dict["object_group_members_red"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint is designed to update the list of currently green/red members of the group, "
                + "it used by the Decision Maker to maintain and calculate the logical group availability. "
                "it requires a POST call with the following data required:",
                "resource_desc": "Manage logical group green/red members",
                "resource_spl_example": "| trackme mode=\"post\" url=\"/services/trackme/v2/splk_logical_groups/write/logical_groups_update_group_list\" body=\"{'tenant_id': 'mytenant', 'object_group_key': 'XXXX', 'object_group_members_green': '<python list>', 'object_group_members_red': '<python list>'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                        "object_group_key": "The logical group key",
                        "object_group_members_green": "list of green members",
                        "object_group_members_red": "list of red members",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Retrieve from data
        resp_dict = json.loads(str(request_info.raw_args["payload"]))

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # collection
        collection_name = f"kv_trackme_common_logical_group_tenant_{tenant_id}"
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        collection = service.kvstore[collection_name]

        # Get the record
        try:
            record = collection.data.query(
                query=json.dumps({"_key": object_group_key})
            )[0]
        except Exception as e:
            record = None

        # process
        if not record:
            response = {
                "action": "failure",
                "response": f'object_group_key="{object_group_key}" not found',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 404}

        else:
            # update the record
            record["object_group_mtime"] = time.time()
            record["object_group_members_green"] = object_group_members_green
            record["object_group_members_red"] = object_group_members_red

            # Update KV
            try:
                collection.data.update(object_group_key, record)

                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "success",
                        "update logical group green/red members",
                        record.get("object_group_name"),
                        "logical_group",
                        record,
                        "green/red members lists were updated successfully",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                # set response
                response = {
                    "action": "success",
                    "response": f'the record for object_group_name="{record.get("object_group_name")}" was updated successfully',
                    "record": record,
                }

                # log
                logger.info(json.dumps(response, indent=4))

                return {"payload": response, "status": 200}

            except Exception as e:
                # register an audit event
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        tenant_id,
                        request_info.user,
                        "failure",
                        "update logical group green/red members",
                        record.get("object_group_name"),
                        "logical_group",
                        record,
                        "green/red members lists failed to be updated",
                        str(update_comment),
                    )
                except Exception as e:
                    logger.error(
                        f'failed to generate an audit event with exception="{str(e)}"'
                    )

                # render response
                response = {
                    "action": "failure",
                    "response": f'an exception was encountered, exception="{str(e)}"',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 500}

    # Admnistrative endpoint designed to cleanup a given entity from any logical group
    def post_logical_groups_remove_object_from_groups(self, request_info, **kwargs):
        # define
        tenant_id = None
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
                object_list = resp_dict["object_list"]
                # turns into a list
                object_list = object_list.split(",")

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint is designed to remove a given list of objects from any logical group, "
                + "it used by different endpoints or functions in TrackMe to clean up the group association when removing or disabling certain entities. "
                "it requires a POST call with the following data required:",
                "resource_desc": "Removes a list of objects from any logical group",
                "resource_spl_example": "| trackme mode=\"post\" url=\"/services/trackme/v2/splk_logical_groups/write/logical_groups_remove_object_from_groups\" body=\"{'tenant_id': 'mytenant', 'object_list': 'object1,object2,object3'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                        "object_list": "comma separated list of entities to be removed from any logical group",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Retrieve from data
        resp_dict = json.loads(str(request_info.raw_args["payload"]))

        # Update comment is optional and used for audit changes
        try:
            update_comment = resp_dict["update_comment"]
        except Exception as e:
            update_comment = "API update"

        # counters
        processed_count = 0
        succcess_count = 0
        failures_count = 0

        # records summary
        records_summary = []

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # collection
        collection_name = f"kv_trackme_common_logical_group_tenant_{tenant_id}"
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        collection = service.kvstore[collection_name]

        # Get all records
        collection_records = []
        collection_records_dict = {}
        count_to_process_list = []

        end = False
        skip_tracker = 0
        while not end:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if process_collection_records:
                for item in process_collection_records:
                    collection_records.append(item)
                    collection_records_dict[item.get("_key")] = {
                        "object_group_name": item.get("object_group_name"),
                        "object_group_mtime": item.get("object_group_mtime"),
                        "object_group_members": item.get("object_group_members"),
                        "object_group_members_green": item.get(
                            "object_group_members_green"
                        ),
                        "object_group_members_red": item.get(
                            "object_group_members_red"
                        ),
                        "object_group_min_green_percent": item.get(
                            "object_group_min_green_percent"
                        ),
                    }
                    count_to_process_list.append(item.get("_key"))
                skip_tracker += len(process_collection_records)
            else:
                end = True

        # Loop through the list of objects, if the object is part of object_group_members, it must be purged from all 3 fields
        for object_value in object_list:
            for logical_group_record in collection_records:
                logger.debug(
                    f'inspecting logical_group_record="{logical_group_record}"'
                )

                # get the lists
                object_group_members = logical_group_record.get(
                    "object_group_members", []
                )
                # ensure is a list
                if not isinstance(object_group_members, list):
                    object_group_members = [object_group_members]

                # if a member:
                if object_value in object_group_members:

                    object_group_members_green = logical_group_record.get(
                        "object_group_members_green", []
                    )
                    # ensure is a list
                    if not isinstance(object_group_members_green, list):
                        object_group_members_green = [object_group_members_green]

                    object_group_members_red = logical_group_record.get(
                        "object_group_members_red", []
                    )
                    # ensure is a list
                    if not isinstance(object_group_members_red, list):
                        object_group_members_red = [object_group_members_red]

                    # remove the list, if needed
                    if object_value in object_group_members:
                        object_group_members.remove(object_value)

                    if object_value in object_group_members_green:
                        object_group_members_green.remove(object_value)

                    if object_value in object_group_members_red:
                        object_group_members_red.remove(object_value)

                    # update the record
                    logical_group_record["object_group_members"] = object_group_members
                    logical_group_record["object_group_members_green"] = (
                        object_group_members_green
                    )
                    logical_group_record["object_group_members_red"] = (
                        object_group_members_red
                    )

                    # update the KVstore record
                    try:
                        collection.data.update(
                            logical_group_record.get("_key"),
                            json.dumps(logical_group_record),
                        )

                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "success",
                                "purge object from logical groups",
                                object_value,
                                "logical_group",
                                logical_group_record,
                                "logical group was updated successfully",
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )

                        # set response
                        response = {
                            "action": "success",
                            "response": f'object="{object_value}" was successfully purged from logical group="{logical_group_record.get("object_group_name")}"',
                            "record": logical_group_record,
                        }

                        # increment counter
                        processed_count += 1
                        succcess_count += 1
                        failures_count += 0

                        # add to summary
                        records_summary.append(response)

                    except Exception as e:
                        # register an audit event
                        try:
                            trackme_audit_event(
                                request_info.system_authtoken,
                                request_info.server_rest_uri,
                                tenant_id,
                                request_info.user,
                                "failure",
                                "purge object from logical groups",
                                object_value,
                                "logical_group",
                                logical_group_record,
                                "logical group failed to be updated",
                                str(update_comment),
                            )
                        except Exception as e:
                            logger.error(
                                f'failed to generate an audit event with exception="{str(e)}"'
                            )

                        # render response
                        response = {
                            "action": "failure",
                            "response": f'an exception was encountered, exception="{str(e)}"',
                        }

                        # increment counter
                        processed_count += 1
                        succcess_count += 0
                        failures_count += 1

                        # add to summary
                        records_summary.append(response)

        # render HTTP status and summary

        req_summary = {
            "process_count": processed_count,
            "success_count": succcess_count,
            "failures_count": failures_count,
            "records": records_summary,
        }

        if processed_count > 0 and processed_count == succcess_count:
            return {"payload": req_summary, "status": 200}

        else:
            return {"payload": req_summary, "status": 500}
