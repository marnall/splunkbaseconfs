#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_vtenant.py"
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
from collections import OrderedDict
import time

splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.vtenants_power", "trackme_rest_api_vtenants_power.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import run_splunk_search, trackme_getloglevel, trackme_parse_describe_flag

# import Splunk SDK client
import splunklib.client as client


class TrackMeHandlerVtenantsWrite_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerVtenantsWrite_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_vtenants(self, request_info, **kwargs):
        response = {
            "resource_group_name": "vtenants/write",
            "resource_group_desc": "Endpoints related to the management of TrackMe Virtual Tenants (power operations)",
        }

        return {"payload": response, "status": 200}

    # Runs a tracker with elevated privileges and as a the system user rather the requester
    def post_run_tenant_tracker(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            if not describe:
                tenant_id = resp_dict["tenant_id"]
                report = resp_dict["report"]
                try:
                    earliest = resp_dict["earliest"]
                except Exception as e:
                    earliest = None
                try:
                    latest = resp_dict["latest"]
                except Exception as e:
                    latest = None
                try:
                    use_savedsearch_time = resp_dict["use_savedsearch_time"]
                    # accept boolean, 0 or 1, true or false (case insensitive)
                    if use_savedsearch_time in ("true", "True", "1"):
                        use_savedsearch_time = True
                    elif use_savedsearch_time in ("false", "False", "0"):
                        use_savedsearch_time = False
                    else:
                        use_savedsearch_time = False
                except Exception as e:
                    use_savedsearch_time = False

        else:
            # body is not required in this endpoint, if not submitted do not describe the usage
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint is designed to execute a Splunk query as the system user, especially to run trackers via the UI with privileges elevation and running on behalf of the system rather than the requester, it requires a POST call with optional data:",
                "resource_desc": "Run TrackMe trackers as the system user",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/vtenants/write/run_tenant_tracker\" body=\"{'tenant_id':'mytenant', 'report': 'mytracker', 'earliest': '-5m', 'latest': 'now'}\"",
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "report": "The name of the TrackMe report, for security reasons its execution will be refused if it is known in TrackMe knowledge objects",
                        "earliest": "The Splunk earliest time quantifier, if not submitted or use_savedsearch_time is True, the earliest time of the search will be used",
                        "latest": "The Splunk latest time quantifier, if not submitted or use_savedsearch_time is True, the latest time of the search will be used",
                        "use_savedsearch_time": "If the savedsearch has earliest and latest times, use them instead of the searchinfo earliest and latest times, True|False",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # performance counter
        start = time.time()

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service - must run as system
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

        # Data collection
        collection_name = "kv_trackme_virtual_tenants"
        collection = service.kvstore[collection_name]

        try:
            vtenant_record = collection.data.query(
                query=json.dumps({"tenant_id": tenant_id})
            )[0]
            vtenant_key = vtenant_record.get("_key")
            logger.debug(
                f'tenant_id="{tenant_id}", vtenant_key="{vtenant_key}", vtenant_report="{json.dumps(vtenant_record)}"'
            )
        except Exception as e:
            error_msg = f'tenant_id="{tenant_id}" cannot be found'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": error_msg,
                },
                "status": 500,
            }

        # get savedsearch definition
        try:
            savedsearch = service.saved_searches[report]
            savedsearch_content = savedsearch.content
            savedsearch_search = savedsearch_content["search"]
            savedsearch_earliest_time = savedsearch_content.get(
                "dispatch.earliest_time"
            )
            savedsearch_latest_time = savedsearch_content.get(
                "dispatch.latest_time"
            )            
            logger.debug(
                f'tenant_id="{tenant_id}", report="{report}", definition="{savedsearch_search}", earliest_time="{savedsearch_earliest_time}", latest_time="{savedsearch_latest_time}"'
            )

        except Exception as e:
            error_msg = f'report="{report}" cannot be found'
            logger.error(error_msg)
            return {
                "payload": {
                    "response": error_msg,
                },
                "status": 500,
            }
        
        # check if the search uses sampling, for splk-fqm only
        try:
            savedsearch_sample_ratio = savedsearch_content.get("dispatch.sample_ratio")
        except Exception as e:
            savedsearch_sample_ratio = None

        # earliest and latest
        if earliest is None or use_savedsearch_time:
            earliest = savedsearch_earliest_time
        if latest is None or use_savedsearch_time:
            latest = savedsearch_latest_time

        # Define the SPL query
        kwargs_search = {
            "app": "trackme",
            "earliest_time": earliest,
            "latest_time": latest,
            "search_mode": "normal",
            "preview": False,
            "time_format": "%s",
            "count": 0,
            "output_mode": "json",
        }

        # if the savedsearch uses sampling, set the sample_ratio
        if savedsearch_sample_ratio:
            kwargs_search["sample_ratio"] = savedsearch_sample_ratio

        # init query results
        query_results = []

        # process
        try:
            logger.info(
                f'tenant_id={tenant_id}, executing report="{report}", search="{savedsearch_search}", earliest="{earliest}", latest="{latest}", requester="{request_info.user}", kwargs_search="{json.dumps(kwargs_search, indent=2)}"'
            )
            # spawn the search and get the results
            reader = run_splunk_search(
                service,
                savedsearch_search,
                kwargs_search,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    query_results.append(item)

            run_time = time.time() - start
            logger.info(
                f'tenant_id={tenant_id}, terminated report="{report}", search="{savedsearch_search}", earliest="{earliest}", latest="{latest}", requester="{request_info.user}", run_time="{run_time}", kwargs_search="{json.dumps(kwargs_search, indent=2)}"'
            )

            return {"payload": query_results, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "response": f'an exception was encountered, exception="{str(e)}"',
            }
            logger.error(json.dumps(response))
            return {"payload": response, "status": 500}
