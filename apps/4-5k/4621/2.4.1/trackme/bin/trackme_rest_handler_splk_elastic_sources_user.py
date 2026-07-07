#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_elastic_sources.py"
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
    "trackme.rest.splk_elastic_sources_user",
    "trackme_rest_api_splk_elastic_sources_user.log",
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerSplkElasticSourcesRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerSplkElasticSourcesRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_splk_elastic_sources(self, request_info, **kwargs):
        response = {
            "resource_group_name": "splk_elastic_sources",
            "resource_group_desc": "Endpoints related to the management of Elastic Sources (read only operations)",
        }

        return {"payload": response, "status": 200}

    # get all records
    def post_elastic_show(self, request_info, **kwargs):
        """
        dedicated:
        | trackme mode=post url="/services/trackme/v2/splk_elastic_sources/elastic_show" body="{'tenant_id': 'mytenant', 'elastic_type': 'dedicated'}"
        """

        """
        shared:
        | trackme mode=post url="/services/trackme/v2/splk_elastic_sources/elastic_show" body="{'tenant_id': 'mytenant', 'elastic_type': 'shared'}"
        """

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
                elastic_type = resp_dict["elastic_type"]
                if not elastic_type in ("shared", "dedicated"):
                    return {
                        "payload": {
                            "tenant_id": tenant_id,
                            "elastic_type": elastic_type,
                            "response": "Unsupported value for elastic_type, valid options are: shared | dedicated",
                        },
                        "status": 500,
                    }

        else:
            # body is required in this endpoint, if not submitted describe the usage
            describe = True

        if describe:
            response = {
                "describe": "This endpoint retrieves currently defined Elastic Sources, it requires a POST call with the following information:",
                "resource_desc": "Get Elastic Sources",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/splk_elastic_sources/elastic_show\" body=\"{'tenant_id': 'mytenant', 'elastic_type': 'dedicated'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "elastic_type": "The type of elastic sources, valid options are: shared | dedicated",
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
            if elastic_type == "shared":
                collection_name = "kv_trackme_dsm_elastic_shared_tenant_" + str(
                    tenant_id
                )
            elif elastic_type == "dedicated":
                collection_name = "kv_trackme_dsm_elastic_dedicated_tenant_" + str(
                    tenant_id
                )
            collection = service.kvstore[collection_name]

            return {"payload": collection.data.query(), "status": 200}

        except Exception as e:
            logger.error(f'Warn: exception encountered="{str(e)}"')
            return {"payload": f'Warn: exception encountered="{str(e)}"'}
