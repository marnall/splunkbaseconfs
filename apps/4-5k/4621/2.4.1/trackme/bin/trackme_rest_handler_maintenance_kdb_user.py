#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_maintenance_kdb_user.py"
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

logger = setup_logger(
    "trackme.rest.maintenance_kdb_user", "trackme_rest_api_maintenance_kdb_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerMaintenanceKdbRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerMaintenanceKdbRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_maintenance_kdb(self, request_info, **kwargs):
        response = {
            "resource_group_name": "maintenance_kdb",
            "resource_group_desc": "The maintenance knowledge database can be used to influence the SLA calculations by adding and maintaining knowledge of planned operations or outages, these endpoints cover read only operations only",
        }

        return {"payload": response, "status": 200}

    # Get all records
    def post_maintenance_kdb_get_records(self, request_info, **kwargs):
        # Declare
        describe = False
        time_format = "epoch"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            if not describe:
                try:
                    resp_dict = json.loads(str(request_info.raw_args["payload"]))
                except Exception as e:
                    resp_dict = []

                # Get the time_format, this is optional and valid options are: human,epoch (default: epoch)
                try:
                    time_format = resp_dict["time_format"]
                    if time_format not in ("human", "epoch"):
                        # render error
                        return {
                            "payload": {
                                "response": f"Invalid time_format, valid options are: human,epoch (default: epoch), time_format={time_format}"
                            },
                            "status": 500,
                        }
                except Exception as e:
                    time_format = "epoch"

        else:
            # body is not required in this endpoint
            describe = False

        if describe:
            response = {
                "describe": "This endpoint allows to retrieve existing maintenance knowledge records in the database, it requires a POST with the following options:",
                "resource_desc": "Retrieve maintenance knowledge records in the database",
                "resource_spl_example": "| trackme mode=post url=\"/services/trackme/v2/maintenance_kdb/maintenance_kdb_get_records\" body=\"{'time_format': 'human'}\"",
                "options": [
                    {
                        "time_format": "Optional, valid options are: human,epoch (default: epoch), time_format=epoch",
                    }
                ],
            }

            return {"payload": response, "status": 200}

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )

        logger.setLevel(loglevel)

        collection_name = "kv_trackme_maintenance_kdb"
        collection = service.kvstore[collection_name]

        # Get records
        try:
            records = collection.data.query()
        except Exception as e:
            error_msg = f'An exception was encountered while attempting to retrieve maintenance knowledge database records, exception="{str(e)}"'
            logger.error(error_msg)
            return {
                "payload": {"response": error_msg},
                "status": 500,
            }

        # if time format is human, loop through records and convert the following fields from epoch to human readable using %c: time_start, time_end, time_expire (only if not eual to 0), ctime, mtime
        if time_format == "human":
            for record in records:

                # tenants_scope: verify if a field called tenants_scope is present in the record, if not add, add one with the value of "*"
                if "tenants_scope" not in record:
                    record["tenants_scope"] = "*"

                for field in [
                    "time_start",
                    "time_end",
                    "time_expiration",
                    "ctime",
                    "mtime",
                ]:
                    if field in record:
                        field_value = record[field]
                        # try to load as an int
                        try:
                            field_value = int(round(float(field_value), 0))
                        except Exception as e:
                            pass

                        if record[field] != 0:
                            # store a new version of the original epochtime value in a field suffixed with _epoch
                            record[f"{field}_epoch"] = field_value
                            record[field] = time.strftime(
                                "%c", time.localtime(field_value)
                            )

        # loop through records and create a new field called enabled, if is_disabled is set to 0, then enabled is set to true, otherwise is set to false
        for record in records:
            if "is_disabled" in record:
                if record["is_disabled"] == 0:
                    record["enabled"] = True
                else:
                    record["enabled"] = False

        return {"payload": records, "status": 200}
