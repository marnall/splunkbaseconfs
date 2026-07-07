from __future__ import absolute_import
import json
import os
import sys
import time

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication

import splunklib

from util.constants import (KVSTORE_KEY, 
                            IS_DRIFT_DETECTED, 
                            END_TIME, 
                            START_TIME, 
                            LAST_DRIFT_AT,
                            METHOD_NOT_ALLOWED,
                            START_TIME_MISSING_MSG, 
                            START_TIME_INVALID_FORMAT_MSG, 
                            END_TIME_INVALID_FORMAT_MSG,
                            START_TIME_GREATER_THAN_END_TIME_MSG)

from base_handler import BaseRestHandler

from logger import get_logger

logger = get_logger()


class DriftedKPIListHandler(BaseRestHandler, PersistentServerConnectionApplication):
    """
    Handles requests for fetching a list of KPI IDs where drift has been detected.
    This class processes GET requests to return a list of KPI IDs that have associated
    drift detection results, indicating that drift has occurred for these KPIs.

    The handler accesses the Splunk KV Store to retrieve the list of KPI IDs and
    returns them to the requester.
    """

    def __init__(self, _command_line, _command_arg):
        BaseRestHandler.__init__(self)

    def handle(self, in_string):
        try:
            request = self.parse_request(in_string)
            method = request.get("method", "GET").upper()  # Default to GET if not specified

            if method != "GET":
                return self.create_response(405, error=METHOD_NOT_ALLOWED)

            return self.process_get_request(request)
        except splunklib.binding.HTTPError as e:
            logger.exception(e)
            return self.create_response(e.status, error=str(e.reason))
        except ValueError as e:
            return self.create_response(400, error=str(e))
        except Exception as e:
            logger.exception(e)
            return self.create_response(500, error="Internal server error")

    @staticmethod
    def parse_request(in_string):
        """
        Parses the incoming request string into a JSON object.
        """
        return json.loads(in_string)

    def process_get_request(self, request):
        """
        Processes the GET request.
        """
        self.initialize_service_if_needed(request)

        query = self.extract_query_parameters(request)
        start_time, end_time = self.validate_and_extract_times(query)

        if start_time > end_time:
            return self.create_response(400, error=START_TIME_GREATER_THAN_END_TIME_MSG)

        drifted_kpis = self.retrieve_drifted_kpis_in_range(start_time=start_time, end_time=end_time)
        return self.create_response(200, result=drifted_kpis)

    def validate_and_extract_times(self, query):
        """
        Validates and extracts start_time and end_time from the query parameters.
        """
        start_time_str = query.get(START_TIME)
        if start_time_str is None:
            raise ValueError(START_TIME_MISSING_MSG)

        if not self.is_valid_epoch(start_time_str):
            raise ValueError(START_TIME_INVALID_FORMAT_MSG)

        end_time_str = query.get(END_TIME, str(int(time.time())))
        if not self.is_valid_epoch(end_time_str):
            raise ValueError(END_TIME_INVALID_FORMAT_MSG)

        return int(start_time_str), int(end_time_str)

    def retrieve_drifted_kpis_in_range(self, start_time, end_time):
        """
        Retrieves and returns drifted KPI IDs within the given time range.
        """
        response = self.get_kv_store_data()
        drifted_kpis = [entry[KVSTORE_KEY] for entry in response if
                        self._entry_matches_time_range(entry, start_time, end_time)]
        return drifted_kpis

    def get_kv_store_data(self):
        """
        Retrieves data from the KV Store collection.
        """
        try:
            collection = self.get_drift_detection_results_collection()
            return collection.data.query()
        except splunklib.binding.HTTPError as e:
            logger.exception(f"Failed to query KV Store, error: {e}")
            raise e

    @staticmethod
    def _entry_matches_time_range(entry, start_time, end_time):
        """
        Checks if the entry's last_drift_at is within the start and end times.
        """
        if entry.get(IS_DRIFT_DETECTED, False):
            last_drift_at = int(entry.get(LAST_DRIFT_AT, 0))
            return start_time <= last_drift_at <= end_time
        return False
