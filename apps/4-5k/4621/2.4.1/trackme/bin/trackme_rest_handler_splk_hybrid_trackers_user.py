#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_hybrid_trackers.py"
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
from collections import OrderedDict

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_hybrid_trackers_user",
    "trackme_rest_api_splk_hybrid_trackers_user.log",
)


# import rest handler
import trackme_rest_handler

# import TrackMe libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkHybridTrackerRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkHybridTrackerRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_hybrid_trackers(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_hybrid_trackers",
            "resource_group_desc": "Endpoints related to the manage of Hybrid trackers for splk-feeds components (user operations)",
        }

        return {"payload": response, "status": 200}

    # get all records
    def post_hybrid_tracker_show(self, request_info, **kwargs):

        # Declare
        tenant_id = None
        describe = False
        component = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                tenant_id = resp_dict["tenant_id"]
                component = resp_dict["component"]
                if not component in ("dsm", "dhm", "mhm"):
                    return {
                        "payload": {
                            "response": f'Invalid component="{component}", valid options are: dsm|dhm|mhm'
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all records for the hybrid tracker collection, it requires a POST call with the following information:",
                "resource_desc": "Get Hybrid trackers",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_hybrid_trackers/hybrid_tracker_show\" body=\"{'tenant_id': 'mytenant', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "The component, valid options are: dsm | dhm | mhm",
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

        # Declare
        trackers_list = []

        try:
            # Data collection
            collection_name = (
                f"kv_trackme_{component}_hybrid_trackers_tenant_{tenant_id}"
            )
            collection = service.kvstore[collection_name]

            for entity in collection.data.query():
                tracker_name = entity.get("tracker_name")
                knowledge_objects = entity.get("knowledge_objects")
                # try to load as a json
                try:
                    knowledge_objects = json.loads(knowledge_objects)
                except Exception as e:
                    knowledge_objects = {}

                # get the live definition
                ko_json = {}
                ko_json["reports"] = []
                ko_json["macros"] = []
                ko_json["properties"] = {}
                if knowledge_objects:
                    reports_list = knowledge_objects.get("reports", [])
                    macros_list = knowledge_objects.get("macros", [])
                    ko_json["reports"] = reports_list
                    ko_json["macros"] = macros_list

                    for macro_name in macros_list:
                        try:
                            macro = service.macros[macro_name]
                            macro_definition = macro.content["definition"]
                            ko_json["properties"]["root_constraint_macro"] = macro_name
                            ko_json["properties"][
                                "root_constraint_macro_definition"
                            ] = macro_definition
                        except Exception as e:
                            logger.error(
                                f'failed to get the macro definition for the macro="{macro_name}", exception="{str(e)}"'
                            )

                    for report_name in reports_list:

                        # _tracker only
                        if "_tracker" in report_name:
                            try:
                                savedsearch = service.saved_searches[report_name]
                                search_cron_schedule = savedsearch.content[
                                    "cron_schedule"
                                ]
                                search_earliest = savedsearch.content[
                                    "dispatch.earliest_time"
                                ]
                                search_latest = savedsearch.content[
                                    "dispatch.latest_time"
                                ]
                                ko_json["properties"][
                                    "cron_schedule"
                                ] = search_cron_schedule
                                ko_json["properties"]["earliest"] = search_earliest
                                ko_json["properties"]["latest"] = search_latest
                            except Exception as e:
                                logger.error(
                                    f'failed to get the savedsearch definition for the report="{report_name}", exception="{str(e)}"'
                                )

                    # add some key info from knowledge_objects
                    try:
                        ko_json["properties"]["breakby_field"] = knowledge_objects[
                            "properties"
                        ][0].get("breakby_field")
                        ko_json["properties"]["search_mode"] = knowledge_objects[
                            "properties"
                        ][0].get("search_mode")
                    except Exception as e:
                        logger.error(
                            f'failed to get the breakby_field or search_mode from the knowledge_objects, exception="{str(e)}"'
                        )

                # add to the list
                trackers_list.append(
                    {
                        "tracker_name": tracker_name,
                        "knowledge_objects": ko_json,
                    }
                )

            return {"payload": trackers_list, "status": 200}

        except Exception as e:
            error_msg = f'An exception was encountered="{str(e)}"'
            logger.error(error_msg)
            return {"payload": {"response": error_msg}, "status": 500}
