"""Account Validation Module for CTIX Accounts.

This module provides validation functionality for CTIX account credentials
by calling the CTIX ping endpoint to verify authentication.
"""
import ta_cyware_ctix_declare  # noqa: F401

import re
import time
import requests
from ta_cyware_ctix import proxy_helper
from ta_cyware_ctix.logging_helper import get_logger
from ta_cyware_ctix.constants import USER_AGENT
from ta_cyware_ctix.ctix_connector import CTIXConnector

from splunk_aoblib.rest_migration import ConfigMigrationHandler

# Error codes
INVALID_ACCESS_ID = "INVALID_ACCESS_ID"
INVALID_SIGNATURE = "INVALID_SIGNATURE"
INVALID_SECRET_KEY = "INVALID_SECRET_KEY"
TOKEN_EXPIRED = "TOKEN_EXPIRED"
CONNECTION_ERROR = "CONNECTION_ERROR"
INVALID_BASE_URL = "INVALID_BASE_URL"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
MISSING_CTIX_API = "MISSING_CTIX_API"

# User-friendly error messages
ERROR_MESSAGES = {
    INVALID_ACCESS_ID: "Invalid Access ID provided. Please verify your Access ID.",
    INVALID_SECRET_KEY: "Invalid Secret Key. Please verify your Secret Key.",
    TOKEN_EXPIRED: "Authentication token expired. Please try again.",
    CONNECTION_ERROR: "Unable to connect to Cyware Threat Intel. Please verify Base URL and network connectivity.",
    INVALID_BASE_URL: "Base URL must use HTTPS protocol for secure connections.",
    MISSING_CTIX_API: "Base URL must end with /ctixapi. Example: https://your-domain.com/ctixapi",
}

# Logger
logger = get_logger("account_validator")


class SessionKeyProvider(ConfigMigrationHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def parse_error_response(response):
    """
    Parse CTIX error response to extract error type and message.

    Args:
        response (requests.Response): HTTP response object

    Returns:
        tuple: (error_code, error_message)
    """
    try:
        error_data = response.json()
        errors = error_data.get("errors", {})
        server_error = errors.get("server", {})

        if server_error:
            title = server_error.get("title", "")
            message = server_error.get("message", "")

            # Map error titles to error codes
            if "TokenExpired" in title:
                return TOKEN_EXPIRED, message
            elif "Base64DecodingError" in title:
                return INVALID_SIGNATURE, message
            elif "InvalidCredentialsProvided" in title:
                return INVALID_SECRET_KEY, message
            elif "InvalidOpenAPICredentialsProvoded" in title or "Invalid Access ID" in message:
                return INVALID_ACCESS_ID, message

        # Fallback to status code based error (when server_error is not present)
        message = error_data.get("message", "")
        if response.status_code == 401:
            return INVALID_CREDENTIALS, message if message else "Invalid credentials were provided."
        elif response.status_code == 400:
            return INVALID_SIGNATURE, message if message else "Invalid signature or token expired"
        elif response.status_code == 404:
            return INVALID_BASE_URL, message if message else "Invalid base URL provided."

        return CONNECTION_ERROR, error_data.get("message", "Unknown error occurred")
    except (ValueError, KeyError) as e:
        logger.warning("Failed to parse error response: %s", str(e))
        return CONNECTION_ERROR, "Failed to parse error response"


def validate_ctix_account(base_url, access_id, secret_key, timeout=10):
    """
    Validate CTIX account credentials by calling the ping endpoint.

    Args:
        base_url (str): CTIX API base URL
        access_id (str): CTIX Access ID
        secret_key (str): CTIX Secret Key (decrypted)
        timeout (int): Request timeout in seconds (default: 10)

    Returns:
        dict: Validation result with keys:
            - valid (bool): Whether credentials are valid
            - error_code (str): Error code if invalid
            - user_message (str): User-friendly error message
            - detailed_error (str): Detailed error for logging
            - status_code (int): HTTP status code
    """
    # Validate HTTPS
    if not base_url or not base_url.strip().startswith("https://"):
        return {
            "valid": False,
            "error_code": INVALID_BASE_URL,
            "user_message": ERROR_MESSAGES[INVALID_BASE_URL],
            "detailed_error": "Base URL must start with https://",
            "status_code": None
        }

    # Clean base URL
    base_url = base_url.rstrip("/")

    # Validate ctixapi path
    ctixapi_pattern = r"^https://[^/]+(?:/[^/]+)*/ctixapi/?$"
    if not re.match(ctixapi_pattern, base_url + "/"):
        return {
            "valid": False,
            "error_code": MISSING_CTIX_API,
            "user_message": ERROR_MESSAGES[MISSING_CTIX_API],
            "detailed_error": "Base URL must end with /ctixapi",
            "status_code": None
        }

    # Validate required fields
    if not access_id or not secret_key:
        return {
            "valid": False,
            "error_code": CONNECTION_ERROR,
            "user_message": "Access ID and Secret Key are required.",
            "detailed_error": "Missing required credentials",
            "status_code": None
        }

    # Generate authentication parameters
    expires = int(time.time() + 25)
    try:
        connector = CTIXConnector("", access_id, secret_key, "")
        signature = connector.signature(expires)
    except Exception as e:
        logger.error("Failed to generate signature: %s", str(e))
        return {
            "valid": False,
            "error_code": INVALID_SIGNATURE,
            "user_message": ERROR_MESSAGES[INVALID_SECRET_KEY],
            "detailed_error": f"Signature generation failed: {str(e)}",
            "status_code": None
        }

    # Build ping URL
    ping_url = f"{base_url}/ping/"
    params = {
        "AccessID": access_id,
        "Expires": expires,
        "Signature": signature
    }

    # Make request with proxy support
    try:
        session_key = SessionKeyProvider().session_key
        proxy_config = proxy_helper.get_proxy_config(session_key, logger)
        from ta_cyware_ctix import ssl_helper
        ssl_verify = ssl_helper.get_ssl_verify(session_key, logger)

        response = requests.get(
            ping_url,
            params=params,
            timeout=timeout,
            proxies=proxy_config,
            verify=ssl_verify,
            headers={'User-Agent': USER_AGENT}
        )

        # Check response status
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get("result") == "pong":
                    return {
                        "valid": True,
                        "error_code": None,
                        "user_message": None,
                        "detailed_error": None,
                        "status_code": 200
                    }
                else:
                    return {
                        "valid": False,
                        "error_code": CONNECTION_ERROR,
                        "user_message": ERROR_MESSAGES[CONNECTION_ERROR],
                        "detailed_error": f"Unexpected response format: {result}",
                        "status_code": 200
                    }
            except ValueError:
                return {
                    "valid": False,
                    "error_code": CONNECTION_ERROR,
                    "user_message": ERROR_MESSAGES[CONNECTION_ERROR],
                    "detailed_error": "Invalid JSON response from server",
                    "status_code": 200
                }

        # Handle error responses
        error_code, error_message = parse_error_response(response)
        return {
            "valid": False,
            "error_code": error_code,
            "user_message": ERROR_MESSAGES.get(error_code, error_message),
            "detailed_error": f"HTTP {response.status_code}: {response.text}",
            "status_code": response.status_code
        }

    except requests.exceptions.Timeout:
        logger.error("Request timeout while validating account")
        return {
            "valid": False,
            "error_code": CONNECTION_ERROR,
            "user_message": ERROR_MESSAGES[CONNECTION_ERROR],
            "detailed_error": f"Request timeout after {timeout} seconds",
            "status_code": None
        }

    except requests.exceptions.SSLError as e:
        logger.error("SSL error while validating account: %s", str(e))
        return {
            "valid": False,
            "error_code": CONNECTION_ERROR,
            "user_message": "SSL certificate verification failed. Please verify the Base URL.",
            "detailed_error": f"SSL error: {str(e)}",
            "status_code": None
        }

    except requests.exceptions.ConnectionError as e:
        logger.error("Connection error while validating account: %s", str(e))
        return {
            "valid": False,
            "error_code": CONNECTION_ERROR,
            "user_message": ERROR_MESSAGES[CONNECTION_ERROR],
            "detailed_error": f"Connection error: {str(e)}",
            "status_code": None
        }

    except Exception as e:
        logger.error("Unexpected error while validating account: %s", str(e))
        return {
            "valid": False,
            "error_code": CONNECTION_ERROR,
            "user_message": ERROR_MESSAGES[CONNECTION_ERROR],
            "detailed_error": f"Unexpected error: {str(e)}",
            "status_code": None
        }
