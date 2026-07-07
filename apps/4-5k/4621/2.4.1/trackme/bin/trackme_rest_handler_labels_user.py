#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_labels_user.py"
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

logger = setup_logger("trackme.rest.labels_user", "trackme_rest_api_labels_user.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_getloglevel,
    trackme_parse_describe_flag,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerLabelsRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerLabelsRead_v2, self).__init__(command_line, command_arg, logger)

    def get_resource_group_desc_labels(self, request_info, **kwargs):
        response = {
            "resource_group_name": "labels",
            "resource_group_desc": "Labels allow users to tag entities with colored badges for lifecycle tracking (read-only operations)",
        }

        return {"payload": response, "status": 200}

    def post_get_labels(self, request_info, **kwargs):

        describe = False
        tenant_id = None

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

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all label definitions for a tenant. It requires a POST call with the following information:",
                "resource_desc": "Get all label definitions for a tenant",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/get_labels" mode="post" body="{\'tenant_id\': \'mytenant\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
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

        collection_name = f"kv_trackme_labels_tenant_{tenant_id}"

        try:
            collection = service.kvstore[collection_name]

            # Query all label definitions
            labels = list(collection.data.query())

            # Sort by label_order (numeric), then label_name
            def safe_label_order(x):
                try:
                    return int(x.get("label_order", 999))
                except (ValueError, TypeError):
                    return 999

            labels.sort(key=lambda x: (safe_label_order(x), x.get("label_name", "")))

            return {
                "payload": labels,
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", failed to retrieve labels from KVstore collection, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }

    def post_get_labels_for_object(self, request_info, **kwargs):

        describe = False
        tenant_id = None
        object_id = None
        component = None

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

                # component is required
                component = resp_dict.get("component", None)
                if component is None:
                    error_msg = f'tenant_id="{tenant_id}", component is required'
                    logger.error(error_msg)
                    return {
                        "payload": {"action": "failure", "result": error_msg},
                        "status": 500,
                    }

        else:
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves resolved labels for a specific entity. It requires a POST call with the following information:",
                "resource_desc": "Get labels assigned to an entity",
                "resource_spl_example": '| trackme url="/services/trackme/v2/labels/get_labels_for_object" mode="post" body="{\'tenant_id\': \'mytenant\', \'object_id\': \'myentity\', \'component\': \'dsm\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "object_id": "The object_id (entity keyid)",
                        "component": "The component type (dsm, dhm, mhm, flx, fqm, wlk)",
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

        labels_collection_name = f"kv_trackme_labels_tenant_{tenant_id}"
        assignments_collection_name = f"kv_trackme_label_assignments_tenant_{tenant_id}"

        try:
            labels_collection = service.kvstore[labels_collection_name]
            assignments_collection = service.kvstore[assignments_collection_name]

            # Build label definitions dict
            labels_def = {l["_key"]: l for l in labels_collection.data.query()}

            # Look up assignment by deterministic key
            assignment_key = f"{component}:{object_id}"
            try:
                assignment = assignments_collection.data.query_by_id(assignment_key)
            except Exception:
                assignment = None

            if assignment is None:
                return {"payload": [], "status": 200}

            # Resolve label_ids to full label objects
            label_ids = json.loads(assignment.get("label_ids", "[]"))
            resolved_labels = []
            for lid in label_ids:
                label_def = labels_def.get(lid)
                if label_def:
                    resolved_labels.append({
                        "label_id": lid,
                        "label_name": label_def.get("label_name", ""),
                        "label_color": label_def.get("label_color", "#9e9e9e"),
                        "label_description": label_def.get("label_description", ""),
                    })

            return {
                "payload": resolved_labels,
                "status": 200,
            }

        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}", object_id="{object_id}", component="{component}", failed to retrieve labels, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {"action": "failure", "result": error_msg},
                "status": 500,
            }
