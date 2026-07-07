#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_splk_deleted_entities_user.py"
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
    "trackme.rest.splk_deleted_entities_user",
    "trackme_rest_api_splk_deleted_entities_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_getloglevel,
    trackme_parse_describe_flag,
)

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkDeletedEntitiesRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkDeletedEntitiesRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_deleted_entities(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_deleted_entities",
            "resource_group_desc": "Endpoints related to the management of deleted entities",
        }

        return {"payload": response, "status": 200}

    # Get object entities
    def post_get_perm_deleted_entities(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # get tenant_id
                tenant_id = resp_dict["tenant_id"]

                # get the component
                component = resp_dict.get("component", None)
                if not component:
                    return {
                        "payload": {
                            "error": "component must be provided, valid options are: dsm/dhm/mhm/wlk/flx/fqm"
                        },
                        "status": 500,
                    }
                elif component not in ("dsm", "dhm", "mhm", "wlk", "flx", "fqm"):
                    return {
                        "payload": {
                            "error": "Invalid option for component, valid options are: dsm/dhm/mhm/wlk/flx/fqm"
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves the list of permanently deleted entities, it requires a POST call with the following information:",
                "resource_desc": "Retrieve permanently deleted entities for a tenant/component",
                "resource_spl_example": "| trackme url=\"/services/trackme/v2/splk_deleted_entities/get_perm_deleted_entities\" mode=\"post\" body=\"{'tenant_id':'mytenant', 'component': 'dsm'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "Component identifier, valid options are: dsm/dhm/mhm/wlk/flx/fqm",
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

        # Data collection
        collection_name = (
            f"kv_trackme_common_permanently_deleted_objects_tenant_{tenant_id}"
        )
        collection = service.kvstore[collection_name]

        # get records
        try:
            kvrecords = collection.data.query(
                query=json.dumps({"object_category": f"splk-{component}"})
            )

            # each record contains a ctime field in epochtime, create a new field called ctime_human in readable format using strftime %c
            for record in kvrecords:
                record["ctime_human"] = time.strftime(
                    "%c", time.localtime(float(record["ctime"]))
                )

            return {"payload": kvrecords, "status": 200}

        except Exception as e:
            error_msg = f"Error retrieving records from collection: {collection_name}, error: {str(e)}"
            logger.error(error_msg)
            return {"payload": error_msg, "status": 500}
