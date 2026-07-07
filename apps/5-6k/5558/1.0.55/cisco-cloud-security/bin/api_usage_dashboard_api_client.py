# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
from typing import List
from datetime import datetime

sys.path.append(dirname(abspath(__file__)))

from enums import APIUsageDashboardAPIEndpoints
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from exceptions import ReportingAPIClientException
from reporting_api_client import ReportingAPIClient
from enum import Enum
from logger import Logger

sys.path.append(dirname(abspath(__file__)))

APP_USER_AGENT = "CiscoCloudSecurityAppForSplunk/python-requests/3x"
ADDON_USER_AGENT = "CiscoCloudSecurityAddonForSplunk/python-requests/3x"

class Routes(Enum):
    REQUESTS_SUMMARY = "requests_summary"
    GET_REQUESTS = "get_requests"
    GET_RESPONSES = "get_responses"
    # GET_KEYS = "get_keys" Currently not used. May be needed in future.


class APIUsageDashboardAPIClient(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        """This is constructor of class APIUsageDashboardAPIClient."""

        PersistentServerConnectionApplication.__init__(self)
        self.reporting_api_client = None
        self.session_token = None

        # Route handler mapping
        self.route_handlers = {
            Routes.REQUESTS_SUMMARY: self.handle_requests_summary,
            Routes.GET_REQUESTS: self.handle_get_requests,
            Routes.GET_RESPONSES: self.handle_get_responses,
            # Routes.GET_KEYS: self.handle_get_keys, Currently not used. May be needed in future.
        }

    def handle(self, in_string):
        """Handler for API usage dashboard API client."""
        Logger().info("API: api_usage_dashboard_api_client, Received request")
        try:
            params = Common().parse_in_string(in_string)
            self.session_token = params["session"]["authtoken"]
            self.reporting_api_client = ReportingAPIClient(self.session_token)
            query_params = params.get("query", {})
            Logger().info(
                "Api Usage Dashboard API Client, Query Params: {0}".format(query_params)
            )
            rest_path = params.get("rest_path")
            if not rest_path:
                raise ValueError(
                    "REST path is required for API usage dashboard client."
                )
            route = rest_path.split("/")[-1]
            route_enum = Routes(route)
            handler = self.route_handlers.get(route_enum)
            if not handler:
                raise ValueError(f"Unsupported route: {route}")
            return handler(query_params)
        except ReportingAPIClientException as e:
            Logger().error("API: reporting_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
        except Exception as e:
            Logger().error(
                "API: api_usage_dashboard_api_client, Exception: {0}".format(str(e))
            )
            return {"payload": {"error_msg": str(e)}, "status": 500}

    def handle_requests_summary(self, query_params: dict) -> dict:
        """
        Handles the total requests summary API call.

        Args:
            query_params (dict): Query parameters for the API call.

        Returns:
            dict: A dictionary containing the total requests summary.

        Raises:
            ValueError: If 'from' or 'to' parameters are missing or if optional parameters are provided.
        """
        from_date, to_date = self._validate_and_extract_date_params(query_params)

        if self._has_optional_parameters(**query_params):
            raise ValueError(
                "Optional parameters are not supported for requests summary."
            )
        response = self._get_summary(from_date, to_date)
        return {
            "payload": {
                "entry": [
                    {
                        "content": response if response else {},
                    }
                ]
            },
            "status": 200
        }

    def handle_get_requests(self, query_params: dict) -> dict:
        """
        Handles the get requests API call with flattened response structure.

        Args:
            query_params (dict): Query parameters for the API call.

        Returns:
            dict: A dictionary containing the flattened requests data where each entry
            represents an individual request with associated user agent information.
        """
        from_date, to_date = self._validate_and_extract_date_params(query_params)
        response = self._get_requests(from_date, to_date, **query_params)

        if not response or response.get("count", 0) == 0:
            return {"payload": {"entry": []}, "status": 200}

        # Flatten the response to request level
        flattened_entries = []
        total_count = response.get("count", 0)

        for item in response.get("items", []):
            user_agent = item.get("userAgent", "")
            user_agent_count = item.get("count", 0)

            for request in item.get("requests", []):
                flattened_entry = {
                    "content": {
                        "userAgent": user_agent,
                        "userAgentCount": user_agent_count,
                        "path": request.get("path", ""),
                        "verb": request.get("verb", ""),
                        "requestCount": request.get("count", 0),
                        "from": from_date,
                        "to": to_date,
                        "totalCount": total_count,
                    }
                }
                flattened_entries.append(flattened_entry)

        return {"payload": {"entry": flattened_entries}, "status": 200}

    def handle_get_responses(self, query_params: dict) -> dict:
        """
        Handles the get responses API call with flattened response structure.

        Args:
            query_params (dict): Query parameters for the API call.

        Returns:
            dict: A dictionary containing the flattened responses data where each entry
            represents an individual response with associated status code information.
        """
        from_date, to_date = self._validate_and_extract_date_params(query_params)
        response = self._get_responses(from_date, to_date, **query_params)

        if not response or response.get("count", 0) == 0:
            return {"payload": {"entry": []}, "status": 200}

        # Flatten the response to request level
        flattened_entries = []
        total_count = response.get("count", 0)

        for item in response.get("items", []):
            status_code = item.get("statusCode", "")
            status_count = item.get("count", 0)

            for request in item.get("requests", []):
                flattened_entry = {
                    "content": {
                        "statusCode": status_code,
                        "statusCount": status_count,
                        "path": request.get("path", ""),
                        "verb": request.get("verb", ""),
                        "requestCount": request.get("count", 0),
                        "from": from_date,
                        "to": to_date,
                        "totalCount": total_count,
                    }
                }
                flattened_entries.append(flattened_entry)

        return {"payload": {"entry": flattened_entries}, "status": 200}

    def handle_get_keys(self, query_params: dict) -> dict:
        """
        Handles the get keys API call.

        Args:
            query_params (dict): Query parameters for the API call.

        Returns:
            dict: A dictionary containing the keys data.
        """
        from_date, to_date = self._validate_and_extract_date_params(query_params)
        response = self._get_keys(from_date, to_date, **query_params)
        return {
            "payload": {
                "entry": [
                    {
                        "content": response if response else {},
                    }
                ]
            },
            "status": 200,
        }

    def _validate_and_extract_date_params(self, query_params: dict) -> tuple:
        """
        Validates and extracts 'from' and 'to' date parameters from query parameters.

        Args:
            query_params (dict): Query parameters containing 'from' and 'to' values.

        Returns:
            tuple: A tuple containing (from_date, to_date).

        Raises:
            ValueError: If 'from' or 'to' parameters are missing or have invalid format.
        """
        from_date = query_params.pop("from", None)
        to_date = query_params.pop("to", None)
        if not from_date or not to_date:
            raise ValueError("from and to are required parameters.")

        self._validate_date_format(from_date, "from")
        self._validate_date_format(to_date, "to")

        return from_date, to_date

    def _validate_date_format(self, date_string: str, param_name: str) -> None:
        """
        Validates that a date string is in YYYY-MM-DD format.

        Args:
            date_string (str): The date string to validate.
            param_name (str): The parameter name for error messages.

        Raises:
            ValueError: If the date format is invalid.
        """
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid {param_name} date value. Must be a valid date in YYYY-MM-DD format, got: {date_string}"
            )

    def _get_requests(self, from_date: str, to_date: str, **kwargs) -> dict:
        """
        Fetches API usage requests within a specified date range.

        Args:
            from_date (str): Start date from frontend (e.g., "2025-08-06").
            to_date (str): End date from frontend (e.g., "2025-08-07").
            **kwargs: Additional parameters for filtering requests.
        Returns:
            dict: A dictionary containing information about the API requests.
        """
        return self._fetch_api_usage_data(
            APIUsageDashboardAPIEndpoints.GET_REQUESTS,
            from_date,
            to_date,
            **kwargs,
        )

    def _get_responses(self, from_date: str, to_date: str, **kwargs) -> dict:
        """
        Fetches API usage responses within a specified date range.

        Args:
            from_date (str): Start date (e.g., "2025-08-06").
            to_date (str): End date (e.g., "2025-08-07").
            **kwargs: Additional parameters for filtering responses.
        Returns:
            dict: A dictionary containing information about the API responses.
        """
        return self._fetch_api_usage_data(
            APIUsageDashboardAPIEndpoints.GET_RESPONSES,
            from_date,
            to_date,
            **kwargs,
        )

    def _get_keys(self, from_date: str, to_date: str, **kwargs) -> dict:
        """
        Fetches API usage keys within a specified date range.

        Args:
            from_date (str): Start date (e.g., "2025-08-06").
            to_date (str): End date (e.g., "2025-08-07").
            **kwargs: Additional parameters for filtering keys.
        Returns:
            dict: A dictionary containing information about the API keys.
        """
        return self._fetch_api_usage_data(
            APIUsageDashboardAPIEndpoints.GET_KEYS,
            from_date,
            to_date,
            **kwargs,
        )

    def _get_summary(self, from_date: str, to_date: str, **kwargs) -> dict:
        """
        Fetches API usage summary within a specified date range.

        Args:
            from_date (str): Start date (e.g., "2025-08-06").
            to_date (str): End date (e.g., "2025-08-07").
            **kwargs: Additional parameters for filtering summary.
        Returns:
            dict: A dictionary containing information about the API usage summary.
        """
        return self._fetch_api_usage_data(
            APIUsageDashboardAPIEndpoints.GET_SUMMARY,
            from_date,
            to_date,
            **kwargs,
        )

    def _build_optional_params_uri(self, **kwargs) -> str:
        """
        Builds the optional parameters URI for the API request based on the provided keyword arguments.
        Handles both original case and lowercase parameter names from UI.

        Args:
            **kwargs: Additional parameters for filtering requests.

        Returns:
            str: The URI-encoded optional parameters to be included in the API request.
        """
        optional_params = []
        for param in self._get_optional_params():
            value = kwargs.get(param) or kwargs.get(param.lower())
            if value is not None:
                optional_params.append(f"{param}={value}")
        return "&".join(optional_params)

    def _fetch_api_usage_data(
        self,
        endpoint_enum: APIUsageDashboardAPIEndpoints,
        from_date: str,
        to_date: str,
        **kwargs,
    ) -> dict:
        """
        Generic method to fetch API usage data for different endpoints.

        Args:
            endpoint_enum: The API endpoint enum value (e.g., APIUsageDashboardAPIEndpoints.GET_REQUESTS)
            from_date (str): Start date from frontend (e.g., "2025-08-06")
            to_date (str): End date from frontend (e.g., "2025-08-07")
            **kwargs: Additional parameters for filtering

        Returns:
            dict: A dictionary containing the API response data
        """
        # Build API path with dates
        path = endpoint_enum.value.format(from_date, to_date, APP_USER_AGENT)
        if self._has_optional_parameters(**kwargs):
            path += f"&{self._build_optional_params_uri(**kwargs)}"
        response = self._send_request(path)
        return response.json()

    def _get_optional_params(self) -> List[str]:
        """
        Returns a list of optional parameters that can be used in API requests.

        Returns:
            List[str]: A list of optional parameter names.
        """
        return APIUsageDashboardAPIEndpoints.OPTIONAL_PARAMS.value

    def _has_optional_parameters(self, **kwargs) -> bool:
        """
        Checks if any optional parameters are present in the provided keyword arguments.
        Handles both original case and lowercase parameter names from UI.

        Args:
            **kwargs: Additional parameters for filtering requests.

        Returns:
            bool: True if any optional parameters are present, False otherwise.
        """
        for param in self._get_optional_params():
            if param in kwargs or param.lower() in kwargs:
                return True
        return False

    def _send_request(
        self, path: str, additional_headers: dict = None, params: dict = None
    ):
        """
        Sends a request to the reporting API using the reporting API client.

        Args:
            path (str): The API endpoint path.
            additional_headers (dict, optional): Additional headers for the request.
            params (dict, optional): Query parameters for the request.

        Returns:
            Response: The response object from the API.
        """
        # Default headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": APP_USER_AGENT,
        }

        # If additional headers are provided, merge them with the default headers
        if additional_headers:
            headers.update(additional_headers)

        return self.reporting_api_client.send_request(
            path, "get", headers=headers, params=params
        )
