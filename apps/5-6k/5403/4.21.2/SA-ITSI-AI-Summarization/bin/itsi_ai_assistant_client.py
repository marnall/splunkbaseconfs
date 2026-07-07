import os
import sys
from typing import Dict, Any, List

import requests
from requests.exceptions import RequestException
# Do NOT `import exec_anaconda` and then run `exec_anaconda.exec_anaconda()` here.
# Importing exec_anaconda in this context can cause "no payload" errors because it terminates the process running the REST server.
# For further details: https://cd.splunkdev.com/sparta/aie/itsi-ai-assistants/episode-summarization/-/merge_requests/44
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import splunklib
from util.splunk_util import SplunkUtil

from constants import *

from util import setup_logging
from util.context_logging import get_context_logger, set_current_summarization_id

class ITSIAIAssistantClient:
    """
    Client for interacting with the ITSI SCS episode summary generation service.
    """

    def __init__(self, base_url: str, service: splunklib.client.Service) -> None:
        """
        Initialize the ITSI AI Assistant Client.

        Args:
            base_url (str): The base URL of the SCS service.
            service (splunklib.client.Service): An authenticated Splunk service instance.
        """
        if not base_url:
            raise ValueError("Base URL cannot be empty.")

        if not service:
            raise ValueError("Service instance cannot be empty.")

        self.base_url = base_url.rstrip("/")
        self.service = service
        
        # Initialize context logger that automatically includes summarization ID
        logger = setup_logging.get_logger(ITSI_SUMMARY_WORKER_LOGGER_NAME)
        self.logger = get_context_logger(logger)

    
    def check_service_health(self, request_id: str = None):
        url = f"{self.base_url}/health"

        scs_token = self._get_scs_token()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {scs_token}"}
        
        # Add request ID to headers if provided
        if request_id:
            headers[ITSI_REQ_ID] = request_id

        try:
            self.logger.info(f"Sending health check to ITSI AI Assistant service: URL={url}")
            response = requests.get(url, headers=headers, timeout=1000)

            if response.status_code == 200:
                self.logger.info("Successfully received health check response from ITSI AI Assistant service.")
                return True
            else:
                self.logger.warning(f"SCS health check failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.exception(f"Unexpected error during ITSI AI Assistant service health check: {str(e)}")
            return False

    def generate_summary(self, payload: Dict[str, Any], summarization_id: str, request_id: str) -> Dict[str, Any]:
        """
        Send a payload to the SCS service to generate a summary and RCA.

        Args:
            payload Dict[str, Any]: The payload to send to the SCS service.
            summarization_id (str): The summarization ID for context logging and tracing.
            request_id (str): Unique request ID for tracing.

        Returns:
            Dict[str, Any]: The response from the SCS service containing the summary and RCA.

        Raises:
            Exception: If the service call fails or returns an error.
        """
        if not payload:
            raise ValueError("The payload field is missing.")

        # Set the summarization context for logging
        set_current_summarization_id(summarization_id)

        url = f"{self.base_url}/summary"
        scs_token = self._get_scs_token()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {scs_token}"}
        
        headers[SUMMARIZATION_ID] = summarization_id
        headers[ITSI_REQ_ID] = request_id

        # TODO: Add retries and exponential backoff for robustness
        try:
            self.logger.debug(f"Sending request with request_id={request_id} to SCS service: URL={url}, Payload={payload}")
            response = requests.post(url, json=payload, headers=headers, timeout=1000)

            if response.status_code != 200:
                self.logger.error(f"SCS service returned an error: {response.status_code} - {response.text}")
                response.raise_for_status()

            self.logger.info("Successfully received response from SCS service.")
            return response.json()
        except RequestException as e:
            self.logger.exception(f"Request to SCS service failed: {str(e)}")
            raise Exception(f"Failed to generate summary: {str(e)}") from e

    def _get_scs_token(self) -> str:
        # Get the system-scoped service to retrieve the SCS token
        system_scoped_service = SplunkUtil.get_splunk_system_user_service(self.service)

        # Retrieve the SCS token using the system-scoped service
        scs_token = SplunkUtil.get_scs_token(system_scoped_service)

        return scs_token

    def get_keywords_for_logs(self, alert_string: str, types: List[str], summarization_id: str, request_id: str) -> List[str]:
        """
        Send an alert string and types list to the SCS service's keyword extraction endpoint to get a list of keywords
        that can be used for searching and filtering logs from custom queries.

        Args:
            alert_string (str): The alert string to extract keywords from SCS. Must be a non-empty string.
            types (List[str]): The types list to extract keywords from SCS.
            summarization_id (str): The summarization ID for context logging and tracing.
            request_id (str): The unique request ID for context logging and tracing.

        Returns:
            List[str]: A list of keywords derived from the alert string. Returns empty list if extraction fails.

        Raises:
            ValueError: If alert_string is not a string or is empty.
            Exception: If the SCS service call fails or returns an error.
        """
        # Input validation
        if not alert_string.strip():
            raise ValueError("Alert string cannot be empty or contain only whitespace.")

        # Set the summarization context for logging
        if summarization_id:
            set_current_summarization_id(summarization_id)

        scs_token = self._get_scs_token()
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {scs_token}",
            SUMMARIZATION_ID: summarization_id,
            ITSI_REQ_ID: request_id
        }
        
        # Prepare payload with context information
        payload = {
            ALERT_STRING: alert_string,
            TYPES_KEY: types
        }

        url = f"{self.base_url}/keywords"

        try:
            self.logger.debug(f"Sending keyword extraction request to SCS service: URL={url}. Keyword extraction payload: {payload}")
            response = requests.post(url, json=payload, headers=headers, timeout=200)

            if response.status_code != 200:
                self.logger.error(f"SCS service returned {response.status_code} for keyword extraction.")
                return []

            response_data = response.json()

            # Validate response structure
            if not isinstance(response_data, dict) or 'keywords' not in response_data or not isinstance(response_data['keywords'], list):
                self.logger.warning(f"SCS keyword service returned unexpected response_data: {response_data}")
                return []
            
            return response_data['keywords']

        except Exception as e:
            self.logger.exception(f"Unexpected error during keyword extraction: {str(e)}")
            raise Exception(f"Failed to get keywords for logs: {str(e)}") from e
