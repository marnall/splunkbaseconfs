from __future__ import absolute_import
import json
import os
import sys

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication

import splunklib

from util.constants import (
    METHOD_NOT_ALLOWED, 
    MISSING_KPI_ID, 
    KPI_ID, 
    USER, 
    KVSTORE_KEY)

from base_handler import BaseRestHandler

from logger import get_logger

logger = get_logger()


class DriftDetectionResultsHandler(BaseRestHandler, PersistentServerConnectionApplication):
    """
    Handles requests for fetching drift detection results for a given KPI ID.
    This handler is responsible for processing GET requests to retrieve
    specific drift detection results stored in the Splunk KV Store. It can also
    process DELETE requests to remove specific drift detection results associated
    with a given KPI ID.

    The `handle` method will distinguish between GET and DELETE requests based on
    the request method and perform the corresponding operation.
    """

    def __init__(self, command_line, command_arg):
        BaseRestHandler.__init__(self)

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get("method", "")

            self.initialize_service_if_needed(request)

            kpi_id = self.extract_kpi_id(request)
            if not kpi_id:
                return self.create_response(400, error=MISSING_KPI_ID)

            logger.info(f"Processing request for kpi_id={kpi_id}")

            if method == "GET":
                drift_detection_results = self.handle_get(kpi_id)
                return self.create_response(200, result=drift_detection_results)
            elif method == "DELETE":
                self.handle_delete(kpi_id)
                return self.create_response(200, result=f"Drift detection results for KPI {kpi_id} deleted")
            else:
                return self.create_response(405, error=METHOD_NOT_ALLOWED)

        except splunklib.binding.HTTPError as e:
            logger.exception(e)
            return self.create_response(e.status, error=e.reason)

        except Exception as e:
            logger.exception(e)
            return self.create_response(500, error="Server error")

    def handle_get(self, kpi_id):
        results = self.get_drift_detection_results_from_kv_store(kpi_id)

        if USER in results:
            del results[USER]

        if KVSTORE_KEY in results:
            results[KPI_ID] = results.pop(KVSTORE_KEY)

        return results

    def handle_delete(self, kpi_id):
        self.delete_drift_detection_results_from_kv_store(kpi_id)

    def get_drift_detection_results_from_kv_store(self, kpi_id):
        try:
            collection = self.get_drift_detection_results_collection()
            return collection.data.query_by_id(str(kpi_id))
        except splunklib.binding.HTTPError as e:
            logger.exception(f"Failed to query KV Store for kpi_id={kpi_id}, error: {e}")
            raise e

    def delete_drift_detection_results_from_kv_store(self, kpi_id):
        try:
            collection = self.get_drift_detection_results_collection()
            return collection.data.delete_by_id(str(kpi_id))
        except splunklib.binding.HTTPError as e:
            logger.exception(f"Failed to delete _key={kpi_id} from KV Store, error: {e}")
            raise e

    def extract_kpi_id(self, request):
        return self.extract_path_info(request)
