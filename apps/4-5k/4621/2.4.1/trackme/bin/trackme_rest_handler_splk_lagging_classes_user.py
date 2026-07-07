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

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_lagging_classes_user",
    "trackme_rest_api_splk_lagging_classes_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import trackme decision maker
from trackme_libs_decisionmaker import convert_epoch_to_datetime

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkLaggingClassesRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkLaggingClassesRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_lagging_classes(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_lagging_classes",
            "resource_group_desc": "Endpoints related to the management of lagging classes for splk-feeds components (read only operations)",
        }

        return {"payload": response, "status": 200}

    # get all records
    def post_lagging_classes_show(self, request_info, **kwargs):

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
                                "payload": f'Invalid component="{component}", valid options for events are: dsm / dhm',
                                "status": 400,
                            }
                    except Exception as e:
                        return {
                            "payload": "Error: component is required for events lagging classes",
                            "status": 400,
                        }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves all lagging classes, it requires a POST call with the following information:",
                "resource_desc": "Get lagging classes",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/splk_lagging_classes/lagging_classes_show" body=\'{"tenant_id": "mytenant", "lagging_class_type": "events", "component": "dsm"}\'',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "lagging_class_type": "The type of lagging classes, valid options are: events | metrics",
                        "component": "CONDITIONAL: the component (dsm / dhm), required when lagging_class_type is events",
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
            # Data collection - component-specific for events
            if lagging_class_type == "events":
                collection_name = (
                    f"kv_trackme_{component}_lagging_classes_tenant_{tenant_id}"
                )
            elif lagging_class_type == "metrics":
                collection_name = f"kv_trackme_mhm_lagging_classes_tenant_{tenant_id}"
            collection = service.kvstore[collection_name]

            records = collection.data.query()
            results_records = []
            for item in records:
                mtime = item.get("mtime")
                if mtime:
                    mtime = convert_epoch_to_datetime(mtime)
                else:
                    mtime = "N/A"

                ctime = item.get("ctime")
                if ctime:
                    ctime = convert_epoch_to_datetime(ctime)
                else:
                    ctime = "N/A"

                # records differ in structure
                if lagging_class_type == "events":
                    results_records.append(
                        {
                            "_key": item.get("_key"),
                            "level": item.get("level"),
                            "name": item.get("name"),
                            "match_mode": item.get("match_mode", "exact"),
                            "value_delay": item.get("value_delay", ""),
                            "delay_mode": item.get("delay_mode", "static"),
                            "variable_delay_default": item.get("variable_delay_default", ""),
                            "variable_delay_slots": item.get("variable_delay_slots", ""),
                            "value_lag": item.get("value_lag", ""),
                            "comment": item.get("comment", ""),
                            "ctime": ctime,
                            "mtime": mtime,
                        }
                    )

                elif lagging_class_type == "metrics":
                    results_records.append(
                        {
                            "_key": item.get("_key"),
                            "metric_category": item.get("metric_category"),
                            "metric_max_lag_allowed": item.get(
                                "metric_max_lag_allowed"
                            ),
                            "comment": item.get("comment", ""),
                            "mtime": mtime,
                        }
                    )

            return {"payload": results_records, "status": 200}

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}
