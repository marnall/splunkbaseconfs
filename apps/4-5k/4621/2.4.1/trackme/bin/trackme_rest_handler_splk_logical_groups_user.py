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
    "trackme.rest.splk_logical_groups_user",
    "trackme_rest_api_splk_logical_groups_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkLogicalGroupsRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkLogicalGroupsRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_logical_groups(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_logical_groups",
            "resource_group_desc": "Endpoints related to the management of logical groups (read only operations)",
        }

        return {"payload": response, "status": 200}

    # Get the entire data sources collection as a Python array
    def post_logical_groups_collection(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/logical_groups_collection\" body=\"{'tenant_id': 'mytenant'}\"
        """

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

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        if describe:
            response = {
                "describe": "This endpoint retrieves all records, it requires a POST call with the following information:",
                "resource_desc": "Get logical groups",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/logical_groups_collection\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                    }
                ],
            }

            return {"payload": response, "status": 200}

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
            collection_name = "kv_trackme_common_logical_group_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            # get records
            collection_records = collection.data.query()
            response_records = []

            # loop through records, process
            for record in collection_records:
                try:
                    # convert the field object_group_mtime to object_group_mtime_human
                    object_group_mtime = float(record.get("object_group_mtime"))
                    object_group_mtime_human = time.strftime(
                        "%d %b %Y %H:%M", time.localtime(object_group_mtime)
                    )
                    record["object_group_mtime_human"] = object_group_mtime_human
                except:
                    pass

                # try loading object_group_members as a list (from csv)
                try:
                    object_group_members = record.get("object_group_members")
                    object_group_members = object_group_members.split(",")
                    record["object_group_members"] = object_group_members
                except:
                    pass

                # try loading object_group_members_green as a list (from csv)
                try:
                    object_group_members_green = record.get(
                        "object_group_members_green"
                    )
                    object_group_members_green = object_group_members_green.split(",")
                    record["object_group_members_green"] = object_group_members_green
                except:
                    pass

                # try loading object_group_members_red as a list (from csv)
                try:
                    object_group_members_red = record.get("object_group_members_red")
                    object_group_members_red = object_group_members_red.split(",")
                    record["object_group_members_red"] = object_group_members_red
                except:
                    pass

                response_records.append(record)

            # Render
            return {"payload": response_records, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Get group
    def post_logical_groups_get_grp(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/logical_groups_get_grp\" body=\"{'tenant_id': 'mytenant', 'object_group_name': 'grp-lb001'}\"
        """

        # define
        tenant_id = None
        object_group_name = None
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
                object_group_name = resp_dict["object_group_name"]

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieve a specific logical group record, it requires a GET call with the following information:",
                "resource_desc": "Get a logical group",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/logical_groups_get_grp\" body=\"{'tenant_id': 'mytenant', 'object_group_name': 'grp-lb001'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                        "object_group_name": "name of the logical group",
                    }
                ],
            }

            return {"payload": response, "status": 200}

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

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                record = collection.data.query(query=json.dumps(query_string))
                key = record[0].get("_key")

            except Exception as e:
                key = None

            # Render result
            if key:
                return {"payload": collection.data.query_by_id(key), "status": 200}

            else:
                response = {
                    "action": "failure",
                    "response": f'object="{object_group_name}" not found',
                }
                logger.error(json.dumps(response))
                return {"payload": response, "status": 404}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}

    # Get groups (simplified list for multiselect)
    def post_logical_groups_get_grps(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/logical_groups_get_grps\" body=\"{'tenant_id': 'mytenant'}\"
        """

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

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves a simplified list of logical groups for use in UI components like multiselects, it requires a POST call with the following information:",
                "resource_desc": "Get logical groups list",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_logical_groups/logical_groups_get_grps\" body=\"{'tenant_id': 'mytenant'}\"",
                "options": [
                    {
                        "tenant_id": "The tenant identifier",
                    }
                ],
            }

            return {"payload": response, "status": 200}

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
            collection_name = "kv_trackme_common_logical_group_tenant_" + str(tenant_id)
            collection = service.kvstore[collection_name]

            # get records
            collection_records = collection.data.query()
            response_records = []

            # loop through records, return simplified structure
            for record in collection_records:
                simplified_record = {
                    "_key": record.get("_key"),
                    "object_group_name": record.get("object_group_name"),
                }
                response_records.append(simplified_record)

            # Sort by group name for easier selection
            response_records.sort(key=lambda x: x.get("object_group_name", ""))

            # Render
            return {"payload": response_records, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}
