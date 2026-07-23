"""
Custom validator for DarkStrata API credentials.

This validator tests the API connection when saving account configuration.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

try:
    from splunktaucclib.rest_handler.endpoint.validator import Validator
except ImportError:
    # Allow importing without Splunk environment
    class Validator:  # type: ignore[no-redef]
        def put_msg(self, msg: str) -> None:
            pass


# Constants
API_TIMEOUT = 15
USER_AGENT = "Splunk/TA-DarkStrata/1.1.1"


class DarkStrataAPIValidator(Validator):
    """
    Validate DarkStrata API credentials by testing the connection.

    This validator is called when saving account configuration in the
    Splunk UI. It makes a test request to the DarkStrata API to verify
    that the API key is valid and has the required permissions.
    """

    def validate(self, value: str, data: dict[str, Any]) -> bool:
        """
        Test API connection with provided credentials.

        Args:
            value: The value being validated (api_key)
            data: All form data including api_base_url and api_key

        Returns:
            True if connection successful, False otherwise
        """
        api_base_url = data.get("api_base_url", "").rstrip("/")
        api_key = value  # The API key is the value being validated

        if not api_base_url:
            self.put_msg("API Base URL is required")
            return False

        if not api_key:
            self.put_msg("API Key is required")
            return False

        # Validate URL format
        if not api_base_url.startswith("https://"):
            self.put_msg("API Base URL must use HTTPS")
            return False

        try:
            # Make a test request to verify credentials
            response = requests.get(
                f"{api_base_url}/stix/indicators",
                params={"format": "splunk", "limit": "1"},
                headers={
                    "x-api-key": api_key,
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                timeout=API_TIMEOUT,
            )
            response.raise_for_status()
            return True

        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
                if status_code == 401:
                    self.put_msg("Invalid API key - authentication failed")
                elif status_code == 403:
                    self.put_msg("API key does not have required permissions. Ensure the key has 'siem:read' scope.")
                elif status_code == 404:
                    self.put_msg("API endpoint not found. Check the API Base URL is correct.")
                else:
                    self.put_msg(f"API returned error: {status_code}")
            else:
                self.put_msg(f"HTTP error: {e}")
            return False

        except requests.exceptions.ConnectionError:
            self.put_msg("Connection failed. Check the API Base URL and network connectivity.")
            return False

        except requests.exceptions.Timeout:
            self.put_msg("Connection timed out. The API server may be unreachable.")
            return False

        except requests.exceptions.RequestException as e:
            self.put_msg(f"Request failed: {e}")
            return False

        except Exception as e:
            logging.getLogger(__name__).exception("Unexpected error during validation")
            self.put_msg(f"Unexpected error: {e}")
            return False


# Export the validator class - UCC looks for this
darkstrata_api_validator = DarkStrataAPIValidator
