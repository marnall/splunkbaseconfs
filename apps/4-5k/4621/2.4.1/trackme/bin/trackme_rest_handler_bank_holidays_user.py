#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_bank_holidays_user.py"
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

logger = setup_logger("trackme.rest.bank_holidays.user", "trackme_rest_api_bank_holidays_user.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerBankHolidaysRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerBankHolidaysRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_bank_holidays(self, request_info, **kwargs):
        response = {
            "resource_group_name": "bank_holidays",
            "resource_group_desc": "The bank holidays feature allows admins to preset bank holiday periods which will prevent alerts from triggering, similar to maintenance mode. (read-only operations)",
        }

        return {"payload": response, "status": 200}

    # List all bank holiday periods
    def get_list(self, request_info, **kwargs):
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
                "describe": "This endpoint lists all bank holiday periods. It requires a GET call with no data.",
                "resource_desc": "List all bank holiday periods",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/bank_holidays/list"',
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

        collection_name = "kv_trackme_bank_holidays"
        collection = service.kvstore[collection_name]

        # get all records
        try:
            records = collection.data.query()
            # Convert to list and format dates
            result = []
            for record in records:
                record_dict = dict(record)
                # Format timestamps for readability
                if record_dict.get("start_date"):
                    record_dict["start_date_formatted"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(int(record_dict["start_date"]))
                    )
                if record_dict.get("end_date"):
                    record_dict["end_date_formatted"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(int(record_dict["end_date"]))
                    )
                if record_dict.get("time_created"):
                    record_dict["time_created_formatted"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(int(record_dict["time_created"]))
                    )
                if record_dict.get("time_updated"):
                    record_dict["time_updated_formatted"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(int(record_dict["time_updated"]))
                    )
                result.append(record_dict)
            response = {"periods": result, "count": len(result)}
        except Exception as e:
            logger.error(f'Failed to query bank holidays collection, exception="{str(e)}"')
            response = {"periods": [], "count": 0}

        return {"payload": response, "status": 200}

    # Check if any bank holiday is currently active
    def get_check_active(self, request_info, **kwargs):
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
                "describe": "This endpoint checks if any bank holiday is currently active. It requires a GET call with no data.",
                "resource_desc": "Check if bank holidays are active",
                "resource_spl_example": '| trackme mode=get url="/services/trackme/v2/bank_holidays/check_active"',
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

        collection_name = "kv_trackme_bank_holidays"
        collection = service.kvstore[collection_name]

        current_time = round(time.time(), 0)
        active_periods = []

        try:
            records = collection.data.query()
            for record in records:
                start_date = record.get("start_date")
                end_date = record.get("end_date")
                
                if start_date and end_date:
                    # Check if current time falls within the period
                    if int(start_date) <= current_time <= int(end_date):
                        active_periods.append(dict(record))
        except Exception as e:
            logger.error(f'Failed to query bank holidays collection, exception="{str(e)}"')

        is_active = len(active_periods) > 0
        response = {
            "is_active": is_active,
            "active_periods": active_periods,
            "active_count": len(active_periods),
            "current_time": current_time,
        }

        return {"payload": response, "status": 200}


