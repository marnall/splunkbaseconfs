import os
import json
import logging
import time
import requests
import logging.handlers
from splunk.persistconn.application import PersistentServerConnectionApplication
import traceback
import re
import random
from typing import Dict, Any, Tuple, Optional
import re
import certifi

def setup_logger(level):
    """
    Initializes and configures a rotating file logger for the Cyble Threat Intelligence module.

    The logger writes logs to the Splunk log directory under:
    $SPLUNK_HOME/var/log/splunk/CybleThreatIntel_Configuration_IOC.log

    Logs are automatically rotated when they reach 25 MB, keeping up to 5 backups.

    :param level: Logging level (e.g., logging.INFO, logging.DEBUG).
    :type level: int
    :return: Configured logger instance.
    :rtype: logging.Logger
    """
    logger = logging.getLogger("custom_rest")
    logger.propagate = False
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(
            os.environ["SPLUNK_HOME"],
            "var",
            "log",
            "splunk",
            "CybleThreatIntel_Configuration_IOC.log",
        ),
        maxBytes=25_000_000,
        backupCount=5,
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.INFO)


def build_proxy_url(scheme: str, host: str, port: int, username: str = "", password: str = "") -> str:
    """
    Builds a complete proxy URL, including optional authentication credentials.

    Example:
        https://user:pass@proxy.example.com:8080

    :param scheme: The proxy protocol (e.g., 'http', 'https').
    :type scheme: str
    :param host: The proxy hostname or IP address.
    :type host: str
    :param port: The proxy port number.
    :type port: int
    :param username: Optional username for proxy authentication.
    :type username: str
    :param password: Optional password for proxy authentication.
    :type password: str
    :return: A formatted proxy URL string.
    :rtype: str
    """
    if username and password:
        return f"{scheme}://{username}:{password}@{host}:{port}"
    elif username:
        return f"{scheme}://{username}@{host}:{port}"
    else:
        return f"{scheme}://{host}:{port}"


def make_payload() -> Dict[str, Any]:
    """
    Constructs the default JSON payload for Cyble API validation requests.

    The payload filters alerts by a specific date range and retrieves the most recent alert.
    It is primarily used for testing or validating API connectivity and structure.

    :return: A dictionary representing the Cyble API request payload.
    :rtype: Dict[str, Any]
    """
    return {
        "orderBy": [{"created_at": "desc"}],
        "skip": 0,
        "take": 1,
        "filters": {
            "created_at": {
                "gte": "2022-06-01T18:30:00.000Z",
                "lte": "2022-06-01T18:30:00.000Z",
            }
        },
        "countOnly": False,
        "taggedAlert": False,
        "withDataMessage": True,
        "hide_data": True,
    }

def try_post(url: str, headers: Dict[str, str], payload: Dict[str, Any],
             proxies: Optional[Dict[str, str]], timeout: float, cert_path: Optional[str] = None, logger=None
            ) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Sends an HTTP POST request and returns a structured result tuple.

    Handles proxy errors, request timeouts, and general request exceptions gracefully.

    :param url: The endpoint URL to send the POST request to.
    :type url: str
    :param headers: HTTP headers to include in the request.
    :type headers: Dict[str, str]
    :param payload: The JSON body of the request.
    :type payload: Dict[str, Any]
    :param proxies: Proxy configuration dictionary (if applicable).
    :type proxies: Optional[Dict[str, str]]
    :param timeout: Maximum time (in seconds) before the request times out.
    :type timeout: float
    :return: A tuple (success, status_code, response_text, error_message)
    :rtype: Tuple[bool, Optional[int], Optional[str], Optional[str]]
    """
    try:
        if cert_path and os.path.exists(cert_path):    
            response = requests.post(url, data=json.dumps(payload), headers=headers, proxies=proxies, timeout=timeout, verify=certifi.where())
        else:
            response = requests.post(url, data=json.dumps(payload), headers=headers, proxies=proxies, timeout=timeout, verify=True)
        return True, response.status_code, response.text, None
    except requests.exceptions.ProxyError as e:
        return False, None, None, f"ProxyError: {e}"
    except requests.exceptions.Timeout:
        return False, None, None, "Timeout"
    except requests.exceptions.RequestException as e:
        return False, None, None, f"RequestException: {e}"
    

def is_int(n):
    """
    Checks whether a given value is an integer or a string representing an integer.

    Example:
        is_int(5) → True
        is_int("10") → True
        is_int("abc") → False

    :param n: Value to be checked.
    :type n: Any
    :return: True if the value is an integer or integer string, False otherwise.
    :rtype: bool
    """
    return isinstance(n, int) or (isinstance(n, str) and re.match(r"^-?\d+$", n))

def in_range(n, min_val, max_val):
    """
    Validates whether a given numeric value (or string) lies within a specified inclusive range.

    Example:
        in_range("5", 1, 10) → True
        in_range(15, 1, 10) → False

    :param n: The value to be checked (integer or string).
    :type n: Any
    :param min_val: Minimum allowed value.
    :type min_val: int
    :param max_val: Maximum allowed value.
    :type max_val: int
    :return: True if value is within range, False otherwise.
    :rtype: bool
    """
    try:
        v = int(n)
        return min_val <= v <= max_val
    except ValueError:
        return False


def is_valid_proxy_url(u):
    """
    Validate whether the given string is a properly formatted proxy URL.

    The function checks if the URL:
      - Is a non-empty string.
      - Starts with either "http://" or "https://".
      - Contains a valid hostname (letters, digits, dots, or hyphens).
      - Contains a valid port number (1–65535).
      - Does not have invalid host formats (e.g., leading/trailing dots or consecutive dots).

    Args:
        u (str): The proxy URL to validate. Example: "http://example.com:8080"

    Returns:
        bool: True if the proxy URL is valid, otherwise False.
    """
    if not u or not isinstance(u, str):
        return False
    m = re.match(r"^(https?):\/\/([A-Za-z0-9.-]+):(\d{1,5})$", u)
    if not m:
        return False
    host = m.group(2)
    port_str = m.group(3)
    if host.startswith(".") or host.endswith(".") or ".." in host:
        return False
    port = int(port_str)
    return 1 <= port <= 65535


class validation(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        """
        Initializes the validation handler for the Cyble IOCs Configuration.

        :param command_line: The command line string provided by Splunk when the input runs.
        :type command_line: str
        :param command_arg: The argument dictionary or string provided by Splunk.
        :type command_arg: Any
        """
        super().__init__()

    def parse_form_data(self, form_data):
        """
        Parses and normalizes incoming form data from the Splunk input setup page.

        Converts a list of key-value pairs (as provided by Splunk's setup form) into
        a dictionary for easier access and processing.

        Example:
            Input: [["api_key", "abc123"], ["days", "15"]]
            Output: {"api_key": "abc123", "days": "15"}

        :param form_data: A list of key-value pairs received from Splunk's setup UI.
        :type form_data: List[List[str, str]]
        :return: A dictionary mapping field names to their respective values.
        :rtype: Dict[str, str]
        """
        parsed = {}
        for [key, value] in form_data:
            parsed[key] = value
        return parsed

    def send_request(self, api_key: str, proxy_config: Optional[Dict[str, Any]] = None, cert_path: Optional[str] = None):
        """
        Validates Cyble API connectivity using the provided API key and optional proxy settings.

        This function performs an authenticated POST request to the Cyble IOCs endpoint
        to ensure the API key and network configurations are valid.
        Includes exponential backoff retry logic for transient network or rate-limit errors.

        Retry behavior:
        - Retries up to 3 times on HTTP 408, 409, 429, or 5xx responses.
        - Delay doubles with each retry (base 1s, max 45s).
        - Random jitter is added to avoid synchronized retries.

        :param api_key: The Cyble API key used for authentication.
        :type api_key: str
        :param proxy_config: Optional dictionary containing proxy configuration fields:
                            {
                                "enabled": bool,
                                "proxy_url": str,
                                "proxy_username": str,
                                "proxy_api_key": str
                            }
        :type proxy_config: Optional[Dict[str, Any]]
        :return: A structured dictionary indicating validation result:
                {
                    "status": 200|400,
                    "payload": "valid" | error message
                }
        :rtype: Dict[str, Any]
        """
        url = "https://api.cyble.ai/engine/api/v4/y/iocs"
        logger.info(f"Starting Cyble IOCs API validation.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = make_payload()
        proxies = None
        
        if proxy_config and proxy_config.get("enabled"):
            proxy_url = proxy_config.get("proxy_url", "").strip()
            proxy_user = proxy_config.get("proxy_username", "").strip()
            proxy_pass = proxy_config.get("proxy_api_key", "").strip()

            if proxy_url:
                try:
                    scheme, rest = proxy_url.split("://", 1)
                    host_port = rest.split("@")[-1] 
                    host, port = host_port.split(":")
                    
                    proxies = {
                        "http": build_proxy_url(scheme, host, int(port), proxy_user, proxy_pass),
                        "https": build_proxy_url(scheme, host, int(port), proxy_user, proxy_pass),
                    }
                except Exception as e:
                    logger.info(f"Failed to build proxy URL: {e}")
            else:
                logger.info("Proxy enabled but proxy_url missing.")
        else:
            logger.info("Proxy not enabled. Connecting directly.")

        # ----------------------------
        # Retry logic
        # ----------------------------

        max_attempts = 3
        base_delay = 1
        factor = 2
        max_delay = 45
        timeout_secs = 45  

        for attempt in range(1, max_attempts + 1):
            logger.info(f"Attempt {attempt}...")

            ok, status, body, error = try_post(url, headers, payload, proxies, timeout_secs, cert_path,logger)
            
            if ok and status and 200 <= status < 300:
                logger.info(f"Success: {status}")
                return {"status": 200, "payload": "valid"}

            elif ok and status in [408, 409, 429] or (status and 500 <= status < 600):
                delay = min(base_delay * (factor ** (attempt - 1)), max_delay) + random.uniform(0, 1)
                logger.info(f"Retryable error {status}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
                continue

            elif not ok:
                logger.info(f"Request failed: {error}")
                if attempt < max_attempts:
                    delay = min(base_delay * (factor ** (attempt - 1)), max_delay) + random.uniform(0, 1)
                    logger.info(f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    continue
                else:
                    return {"status": 400, "payload": f"Failed after retries: {error}"}
            else:
                logger.info(f"Non-retryable error: {status}")
                return {"status": 400, "payload": f"Invalid response: {status}"}

        return {"status": 400, "payload": "Request failed after maximum retries. Please check the credentials and network connectivity."}

    def handle(self, in_string):
        """
        Handles incoming setup validation requests from Splunk’s input configuration UI.

        This method:
        - Parses the setup form data submitted from Splunk’s UI.
        - Validates user inputs such as API key, interval, and proxy configuration.
        - Calls `send_request()` to verify Cyble API connectivity.
        - Returns a structured response indicating success or detailed validation errors.

        Validation rules include:
        - Name: Required, <= 256 chars, alphanumeric + spaces/underscores/hyphens.
        - API Key: Required, 1–255 chars.
        - Days: Integer between 1–15.
        - Interval: Integer between 3600 (1 hr) and 172800 (48 hr).
        - Proxy: Valid URL format (http/https with numeric port) if enabled.

        :param in_string: The raw JSON string input from Splunk setup validation.
        :type in_string: str
        :return: JSON-compatible dictionary containing validation status and message:
                {
                    "status": 200|400,
                    "payload": "valid" | error message,
                    "headers": {"Content-Type": "application/json"}
                }
        :rtype: Dict[str, Any]
        """
        try:
            in_dict = json.loads(in_string)
            payload = self.parse_form_data(in_dict.get("form", []))
            logger.info(f"Received validation request.")

            Name = (payload.get("Name") or "").strip()
            api_key = (payload.get("api_key") or "").strip()
            days = payload.get("days")
            interval = payload.get("interval")

            # Proxy settings
            proxy_enabled = str(payload.get("proxy.enabled", "")).lower() in ("true", "1", "on")
            proxy_url = (payload.get("proxy_url") or "").strip()
            proxy_username = (payload.get("proxy_username") or "").strip()
            proxy_password = (payload.get("proxy_api_key") or "").strip()
            certificate_content = (payload.get("certificate") or "").strip()

            # Input validation
            if not Name:
                return {"status": 400, "payload": "Name is required", "headers": {"Content-Type": "application/json"}}

            if not api_key:
                return {"status": 400, "payload": "API Key is required", "headers": {"Content-Type": "application/json"}}
            
            if not days:
                return {"status": 400, "payload": "Days is required", "headers": {"Content-Type": "application/json"}}
            
            if not interval:
                return {"status": 400, "payload": "Interval is required", "headers": {"Content-Type": "application/json"}}  
            
            if len(Name) > 256:
                return {
                    "status": 400,
                    "payload": "Name cannot exceed 256 characters",
                    "headers": {"Content-Type": "application/json"}
                }
            
            if not re.match(r'^[A-Za-z0-9_\-\s]+$', Name):
                return {
                    "status": 400,
                    "payload": "Name can only contain letters, numbers, spaces, underscores, and hyphens",
                    "headers": {"Content-Type": "application/json"}
                }
            
            if not (0 < len(api_key) < 256):
                return {"status": 400, "payload": "API Key length must be between 1 and 255 characters", "headers": {"Content-Type": "application/json"}}
            
            if days and str(days).strip():
                if not is_int(days) or not in_range(days, 1, 15):
                    return {"status": 400, "payload": "Days must be an integer between 1 and 15", "headers": {"Content-Type": "application/json"}}

            try:
                interval_val = int(interval)
                min_seconds = 60
                max_seconds = 172800           
                if not (min_seconds <= interval_val <= max_seconds):
                    return {"status": 400, "payload": "Interval must be between 3600 (1 hr) and 172800 (48 hr) seconds", "headers": {"Content-Type": "application/json"}}
            except ValueError:
                return {"status": 400, "payload": "Interval must be a valid number (in seconds)", "headers": {"Content-Type": "application/json"}}
            
            if proxy_password and not proxy_username:
                return {"status": 400, "payload": "Proxy Username is required when Proxy Password is provided", "headers": {"Content-Type": "application/json"}}

            if proxy_enabled:
                if not proxy_url or not is_valid_proxy_url(proxy_url):
                    return {"status": 400, "payload": "Proxy URL must be http://host:port or https://host:port with valid numeric port", "headers": {"Content-Type": "application/json"}}
                if proxy_password and not proxy_username:
                    return {"status": 400, "payload": "Proxy Username is required when Proxy Password is provided", "headers": {"Content-Type": "application/json"}}
                if proxy_username and (not proxy_url or not is_valid_proxy_url(proxy_url)):
                    return {"status": 400, "payload": "Proxy URL is required when Proxy Username is provided", "headers": {"Content-Type": "application/json"}}
            else:
                if any([proxy_url, proxy_username, proxy_password]):
                    return {"status": 400, "payload": "Enable Proxy to use proxy settings", "headers": {"Content-Type": "application/json"}}

            if certificate_content:
                if not (
                    certificate_content.startswith("-----BEGIN CERTIFICATE-----")
                    and certificate_content.strip().endswith("-----END CERTIFICATE-----")
                ):
                    return {
                        "status": 400,
                        "payload": "Invalid certificate format. Must be PEM encoded (BEGIN/END CERTIFICATE).",
                        "headers": {"Content-Type": "application/json"}
                    }
            else:
                logger.info("No certificate provided.")


            logger.info("All validations passed successfully.")

            proxy_cfg = {
                "enabled": proxy_enabled,
                "proxy_url": proxy_url,
                "proxy_username": proxy_username,
                "proxy_api_key": proxy_password,
            }

            cert_path = None

            if certificate_content:
                try:
                    ca_bundle_path = certifi.where()

                    with open(ca_bundle_path, "ab") as f:  
                        f.write(b"\n")
                        f.write(certificate_content.encode("utf-8"))
                    
                    cert_path = ca_bundle_path
                    
                except Exception as e:
                    logger.error(f"Failed to append certificate: {e}")
                    return {
                        "status": 400,
                        "payload": "Failed to append certificate to CA bundle.",
                        "headers": {"Content-Type": "application/json"},
                    }
    
            response = self.send_request(api_key, proxy_cfg, cert_path)

            response["headers"] = {"Content-Type": "application/json"}
            logger.info(f"Received response from Cyble : {response}")
            return response

        except Exception:
            logger.error("Error in handle method:")
            logger.error(traceback.format_exc())
            response = {"status": 400, "payload": "Internal processing error."}
            response["headers"] = {"Content-Type": "application/json"}
            return response
