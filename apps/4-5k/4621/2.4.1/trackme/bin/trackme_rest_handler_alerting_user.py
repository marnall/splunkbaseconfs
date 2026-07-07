#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_configuration.py"
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
    "trackme.rest.alerting_user", "trackme_rest_api_alerting_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import run_splunk_search, trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerAlertingReadOps_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerAlertingReadOps_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_alerting_user(self, request_info, **kwargs):
        response = {
            "resource_group_name": "alerting",
            "resource_group_desc": "These endpoints handle alerting operations (read-only operations)",
        }

        return {"payload": response, "status": 200}

    # Shows alerts per tenant
    def post_get_tenant_alerts(self, request_info, **kwargs):
        """
        | trackme mode=post url=\"/services/trackme/v2/alerting/read/get_tenant_alerts\" body=\"{'tenant_id':'mytenant'}\"
        """

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
                tenant_id = resp_dict["tenant_id"]
        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint retrieves alerts for a specific tenant. It requires a POST call with the following options:",
                "resource_desc": "Get operational status for a TrackMe tenant",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/alerting/read/get_tenant_alerts\" body=\"{'tenant_id':'mytenant'}\"",
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
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        # Define the SPL query
        kwargs_search = {
            "app": "trackme",
            "earliest_time": "-5m",
            "latest_time": "now",
            "output_mode": "json",
            "count": 0,
        }
        searchquery = "| `get_tenant_alerts(" + str(tenant_id) + ")`"

        query_results = []
        try:
            reader = run_splunk_search(
                service,
                searchquery,
                kwargs_search,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    query_results.append(item)
            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}
