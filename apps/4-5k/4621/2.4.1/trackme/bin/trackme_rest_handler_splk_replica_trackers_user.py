#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_replica_trackers.py"
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
    "trackme.rest.splk_replica_trackers_user",
    "trackme_rest_api_splk_replica_trackers_user.log",
)


# import rest handler
import trackme_rest_handler

# import TrackMe libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkReplicaTrackerRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkReplicaTrackerRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_replica_trackers(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_replica_trackers",
            "resource_group_desc": "Endpoints related to the management of replica trackers (user operations)",
        }

        return {"payload": response, "status": 200}

    # get all records
    def post_replica_tracker_show(self, request_info, **kwargs):
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
                "describe": "This endpoint retrieves all records for the replica tracker collection, it requires a POST call with the following information:",
                "resource_desc": "Get Hybrid trackers",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_replica_trackers/replica_tracker_show\" body=\"{'tenant_id': 'mytenant'}\"",
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
            collection_name = "kv_trackme_common_replica_trackers_tenant_" + str(
                tenant_id
            )
            collection = service.kvstore[collection_name]

            return {"payload": collection.data.query(), "status": 200}

        except Exception as e:
            logger.error(f'Warn: exception encountered="{str(e)}"')
            return {"payload": f'Warn: exception encountered="{str(e)}"'}
