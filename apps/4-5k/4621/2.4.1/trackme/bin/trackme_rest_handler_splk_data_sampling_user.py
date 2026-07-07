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
import hashlib

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.splk_data_sampling_user",
    "trackme_rest_api_splk_data_sampling_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import data sampling libs (#1717: renamed from
# `trackmedatasampling_ootb_regex` so the module name follows the
# `trackme_libs_*` convention — preserves the lib-vs-custom-command
# distinction enforced by check_rest_handler_logging_hygiene.py).
from trackme_libs_datasampling_ootb_regex import ootb_regex_list

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDataSamplingRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDataSamplingRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_data_sampling(self, request_info, **kwargs):
        response = {
            "resource_group_name": "data_sampling",
            "resource_group_desc": "Endpoints for the data sampling events recognition engine (read only operations)",
        }

        return {"payload": response, "status": 200}

    # show out of the box rules
    def get_data_sampling_ootb_rules_show(self, request_info, **kwargs):

        # Declare
        describe = False

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

        else:
            describe = False

        if describe:
            response = {
                "describe": "This endpoint retrieves data sampling out of the box rules, it requires a GET call:",
                "resource_desc": "Get Data Sampling out of the box rules",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/splk_data_sampling/data_sampling_ootb_rules_show"',
                "options": [
                    {
                        "describe": "Describe the usage of this endpoint",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        try:
            merged_models_inclusive = []
            model_order = 0
            # Append ootb models to the inclusive list
            for ootb_model in ootb_regex_list:
                model_order += 1
                model_name = ootb_model.get("label")
                model_regex = ootb_model.get("regex")
                merged_models_inclusive.append(
                    {
                        "model_order": model_order,
                        "model_name": model_name,
                        "model_regex": model_regex,
                        "model_type": "inclusive",
                        "model_id": hashlib.sha256(
                            model_name.encode("utf-8")
                        ).hexdigest(),
                        "sourcetype_scope": "*",
                    }
                )
            return {"payload": merged_models_inclusive, "status": 200}
        except Exception as e:
            logger.error(f'exception encountered="{str(e)}"')
            return {"payload": f'exception encountered="{str(e)}"', "status": 500}

    # show custom rules
    def post_data_sampling_rules_show(self, request_info, **kwargs):

        # Declare
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
                "describe": "This endpoint retrieves data sampling custom rules, it requires a POST call with the following information:",
                "resource_desc": "Get Data Sampling custom rules for a given TrackMe tenant",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_data_sampling/data_sampling_rules_show\" body=\"{'tenant_id':'mytenant'}\"",
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

        try:
            # Data collection
            collection_name = (
                "kv_trackme_dsm_data_sampling_custom_models_tenant_" + str(tenant_id)
            )
            collection = service.kvstore[collection_name]
            return {"payload": collection.data.query(), "status": 200}

        except Exception as e:
            logger.error(f'exception encountered="{str(e)}"')
            return {"payload": f'exception encountered="{str(e)}"', "status": 500}
