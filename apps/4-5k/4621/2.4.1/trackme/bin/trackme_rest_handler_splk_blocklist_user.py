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
import copy

splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_blocklist_user", "trackme_rest_api_splk_blocklist_user.log"
)


import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import trackme decision maker
from trackme_libs_decisionmaker import convert_epoch_to_datetime, apply_blocklist

# import trackme libs utils
from trackme_libs_utils import update_wildcard

# import splunk
import splunklib.client as client


class TrackMeHandlerSplkBlocklistRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkBlocklistRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_blocklist(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_blocklist",
            "resource_group_desc": "These endpoints provide capabilities to manage blocklists for feeds tracking. (splk-dsm/dhm/mhm, read only operations)",
        }

        return {"payload": response, "status": 200}

    # get all records
    def post_blocklist_show(self, request_info, **kwargs):

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

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves blocklist records, it requires a POST call with the following information:",
                "resource_desc": "Get blocklist records",
                "resource_spl_example": "| trackme mode=get url=\"/services/trackme/v2/splk_blocklist/blocklist_show\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm | flx | wlk | fqm",
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
            # Data collection
            collection_name = f"kv_trackme_{component}_allowlist_tenant_{tenant_id}"
            collection = service.kvstore[collection_name]

            records = collection.data.query()
            results_records = []
            for item in records:
                mtime = item.get("mtime")
                if mtime:
                    mtime = convert_epoch_to_datetime(mtime)
                else:
                    mtime = "N/A"
                results_records.append(
                    {
                        "_key": item.get("_key"),
                        "object_category": item.get("object_category"),
                        "object": item.get("object"),
                        "action": item.get("action"),
                        "is_rex": item.get("is_rex"),
                        "comment": item.get("comment", ""),
                        "mtime": mtime,
                    }
                )
            return {"payload": results_records, "status": 200}

        except Exception as e:
            error_msg = f'An exception was encountered, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}

    # Simulate a blocklist rule against entities to show which would be blocked
    def post_blocklist_simulate(self, request_info, **kwargs):

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
                        "status": 400,
                    }

                try:
                    component = resp_dict["component"]
                    if component not in ("dsm", "dhm", "mhm", "flx", "wlk", "fqm"):
                        return {
                            "payload": f'Invalid component="{component}"',
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "payload": "component is required, please provide a valid component",
                        "status": 400,
                    }

                try:
                    object_category = resp_dict["object_category"]
                except Exception as e:
                    return {
                        "payload": "object_category is required, please provide a valid object_category",
                        "status": 400,
                    }

                try:
                    object_value = resp_dict["object"]
                except Exception as e:
                    return {
                        "payload": "object is required, please provide a valid object value",
                        "status": 400,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint simulates a blocklist rule against current entities to show which would be blocked, it requires a POST call with the following information:",
                "resource_desc": "Simulate a blocklist rule",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_blocklist/blocklist_simulate\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm', 'object_category': 'index', 'object': 'test*'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm | flx | wlk | fqm",
                        "object_category": "The object category (field name to match against), e.g. index, sourcetype, alias, object, group, app, or any custom field",
                        "object": "The pattern to match, supports exact values, wildcards (*) and regex patterns",
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
            # Apply wildcard conversion (same as blocklist_add does)
            object_value = update_wildcard(object_value)

            # Detect if the pattern is regex (same logic as blocklist_add)
            r = re.match("[\\\\|\\?|\\$|\\^|\\[|\\]|\\{|\\}|\\+]", object_value)
            r2 = re.findall("\\.[\\*|\\+]", object_value)
            is_rex = "true" if (r or r2) else "false"

            # Validate regex pattern if it is a regex
            if is_rex == "true":
                try:
                    re.compile(object_value)
                except re.error as e:
                    return {
                        "payload": {
                            "action": "failure",
                            "response": f"Invalid regex pattern: {str(e)}",
                            "regex_is_valid": "false",
                        },
                        "status": 400,
                    }

            # Build the simulated blocklist rule
            simulated_rule = {
                "object_category": object_category,
                "object": object_value,
                "action": "block",
                "is_rex": is_rex,
            }

            # Build the blocklist dicts as expected by apply_blocklist
            if is_rex == "true":
                blocklist_not_regex = {}
                blocklist_regex = {"simulated": simulated_rule}
            else:
                blocklist_not_regex = {"simulated": simulated_rule}
                blocklist_regex = {}

            # Load all entities from the component's main collection
            data_collection_name = f"kv_trackme_{component}_tenant_{tenant_id}"
            data_collection = service.kvstore[data_collection_name]
            entities = data_collection.data.query()

            total_entities = len(entities)
            matched_entities = []

            for entity in entities:
                # Deep copy to avoid mutating the original record (apply_blocklist modifies in place)
                entity_copy = copy.deepcopy(entity)
                # apply_blocklist returns False if the entity would be blocked
                would_be_allowed = apply_blocklist(
                    entity_copy, blocklist_not_regex, blocklist_regex
                )
                if not would_be_allowed:
                    # This entity would be blocked
                    entity_name = entity.get("object", entity.get("_key", "unknown"))
                    matched_entities.append(entity_name)

            response = {
                "kvstore_collection_entities_count": total_entities,
                "entities_matched_count": len(matched_entities),
                "entities_matched": matched_entities,
                "object_category": object_category,
                "object": object_value,
                "is_rex": is_rex,
                "match_type": "regex" if is_rex == "true" else "exact",
                "result_summary": f'The blocklist rule on field "{object_category}" with pattern "{object_value}" ({("regex" if is_rex == "true" else "exact")} match) would block {len(matched_entities)} out of {total_entities} total entities.',
            }

            return {"payload": response, "status": 200}

        except Exception as e:
            error_msg = f'An exception was encountered, exception="{str(e)}"'
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}
