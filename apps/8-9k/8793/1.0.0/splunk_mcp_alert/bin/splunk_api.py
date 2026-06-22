"""Thin wrapper around Splunk's REST API."""

import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class SplunkAPIClient:
    """Client for Splunk REST API calls.

    Args:
        base_url: Splunk management URL (e.g. https://localhost:8089).
        token: Bearer token for authentication.
        timeout: Request timeout in seconds.
    """

    class APIError(Exception):
        """Raised when Splunk API returns a non-2xx status."""

        def __init__(self, status_code: int, message: str):
            self.status_code = status_code
            self.message = message
            super().__init__(f"Splunk API error {status_code}: {message}")

    def __init__(self, base_url: str, token: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def call_api(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a REST call to Splunk.

        Args:
            method: HTTP method (GET, POST, DELETE).
            endpoint: API endpoint path (e.g. /services/saved/searches).
            params: Query parameters.
            data: POST body data.

        Returns:
            Parsed JSON response dict.

        Raises:
            APIError: If the response status is not 2xx.
        """
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}
        params["output_mode"] = "json"

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        logger.debug("Splunk API %s %s", method, endpoint)

        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            verify=False,
            timeout=self.timeout,
        )

        if resp.status_code < 200 or resp.status_code >= 300:
            try:
                error_body = resp.json()
                messages = error_body.get("messages", [])
                error_text = "; ".join(m.get("text", "") for m in messages) or resp.text
            except (json.JSONDecodeError, AttributeError):
                error_text = resp.text
            raise self.APIError(resp.status_code, error_text)

        return resp.json()
