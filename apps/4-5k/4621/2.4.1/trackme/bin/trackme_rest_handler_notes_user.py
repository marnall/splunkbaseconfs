#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_notes.py"
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

logger = setup_logger("trackme.rest.notes_user", "trackme_rest_api_notes_user.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_getloglevel,
    trackme_parse_describe_flag,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerNotesRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerNotesRead_v2, self).__init__(command_line, command_arg, logger)

    def get_resource_group_desc_notes(self, request_info, **kwargs):
        response = {
            "resource_group_name": "notes",
            "resource_group_desc": "Notes allow users to publish notes associated with entities (read-only operations)",
        }

        return {"payload": response, "status": 200}

    def post_get_notes_for_object(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        object_id = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # tenant_id is required
                tenant_id = resp_dict.get("tenant_id", None)
                if tenant_id is None:
                    error_msg = f'tenant_id="{tenant_id}", tenant_id is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

                # object_id is required
                object_id = resp_dict.get("object_id", None)
                if object_id is None:
                    error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", object_id is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves notes for a given object_id. It requires a POST call with the following information:",
                "resource_desc": "Get notes for an entity",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/notes/get_notes_for_object\" mode=\"post\" body=\"{'tenant_id': 'mytenant', 'object_id': 'netscreen:netscreen:firewall'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_id": "The object_id (entity keyid) to retrieve notes for",
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

        collection_name = f"kv_trackme_notes_tenant_{tenant_id}"
        
        try:
            collection = service.kvstore[collection_name]
            
            # Query for notes matching the object_id
            query = json.dumps({"object_id": object_id})
            notes = collection.data.query(query=query)
            
            # Sort by mtime descending (newest first)
            notes_list = list(notes)
            notes_list.sort(key=lambda x: x.get("mtime", 0), reverse=True)
            
            return {
                "payload": notes_list,
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", failed to retrieve notes from KVstore collection, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }

