from __future__ import absolute_import
import os
import re
import sys

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import splunklib.client as client

from util.constants import PATH_INFO, DRIFT_DETECTION_RESULTS_COLLECTION

from logger import get_logger

logger = get_logger()


class BaseRestHandler(object):
    def __init__(self):
        self.service = None

    def initialize_service_if_needed(self, request):
        if self.service is None:
            self._initialize_service(request)

    def _initialize_service(self, request):
        """Initialize the Splunk service connection."""
        try:
            session_key = request["session"]["authtoken"]
            port = self.extract_management_port(request)

            # Prepare arguments for client.Service
            service_kwargs = {
                "token": session_key,
                "owner": "nobody"
            }

            # Only add port to the arguments if it is not None
            if port is not None:
                service_kwargs["port"] = port

            self.service = client.Service(**service_kwargs)
        except Exception as e:
            logger.error(f"Failed to initialize Splunk service connection, error={str(e)}")
            self.service = None

    def get_drift_detection_results_collection(self):
        return self.service.kvstore[DRIFT_DETECTION_RESULTS_COLLECTION]

    @staticmethod
    def extract_path_info(request):
        path_info = request.get(PATH_INFO)
        if not path_info:
            return None
        return path_info.split('/')[-1].strip()

    @staticmethod
    def create_response(status, result=None, error=None):
        """
        Create a response to send back to the client.
        """
        return {
            "payload": {"result": result, "error": error},
            "status": status
        }

    @staticmethod
    def extract_query_parameters(request):
        """
        Extracts query parameters from the input dictionary and converts
        them into a usable dictionary format.

        :param request: The input dictionary containing various attributes,
                           including the 'query' attribute with query parameters.
        :return: A dictionary containing the query parameters.
        """
        query_params_list = request.get('query', [])
        query_params_dict = {}

        for param in query_params_list:
            key, value = param
            query_params_dict[key] = value
        return query_params_dict

    @staticmethod
    def is_valid_epoch(value):
        """
        Validates if the provided value is a valid epoch timestamp (number of seconds since Unix epoch).
        It checks if the value is an integer or a string that can be converted to an integer.

        :param value: The value to validate.
        :return: True if value is a valid epoch timestamp, False otherwise.
        """
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            # If the conversion fails, the value is not a valid epoch timestamp.
            return False

    @staticmethod
    def extract_management_port(request):
        """
        Extracts the port number from the 'rest_uri' within a request dictionary.
        The 'rest_uri' is expected under request['server']['rest_uri'].

        Args:
            request (dict): The request dictionary containing the server information.

        Returns:
            int or None: The extracted port number as an integer, or None if not found.
        """
        try:
            # Extract the rest_uri from the server dictionary
            rest_uri = request.get("server", {}).get("rest_uri", "")

            match = re.search(r':(\d+)', rest_uri)
            if match:
                # Convert the matched group to an integer
                return int(match.group(1))
            else:
                # Return None if no port is found in the URI
                return None
        except ValueError as e:
            # Handle cases where the port number is not a valid integer
            logger.error(f"Invalid port number in request, error={str(e)}")
            return None
