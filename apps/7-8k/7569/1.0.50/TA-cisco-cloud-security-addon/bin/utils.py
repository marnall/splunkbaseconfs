"""Utility functions for the models."""

import logging
from logging.handlers import RotatingFileHandler
import os
from common import Common
import import_declare_test
import boto3
import json
import splunk.rest as rest
import splunk
import time
import ipaddress
from typing import Dict, Any, List, Optional, Tuple, Union
from urllib.parse import quote
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from botocore.config import Config
from exceptions import S3ValidationError
from splunktaucclib.rest_handler.error import RestError
import requests
import base64
from solnlib import conf_manager
from solnlib.soln_exceptions import ConfManagerException


def get_conf_stanza_details(
    session_key: str,
    conf_file: str,
    stanza_name: str,
    use_credential_realm: bool = True,
) -> dict:
    """
    Retrieves configuration details for a given stanza from a Splunk conf file.

    Args:
        session_key (str): The Splunk session key for authentication.
        conf_file (str): The name of the configuration file.
        stanza_name (str): The stanza within the configuration file to retrieve.
        use_credential_realm (bool): If True, scopes ConfManager to the credential
            decryption realm. Required for conf files with encrypted fields
            (e.g., passwords, secret keys). Set to False for conf files with
            only plain-text settings. Defaults to True.

    Returns:
        dict: The configuration details for the specified stanza.

    Raises:
        Exception: If the configuration cannot be retrieved.
    """
    ta_name = import_declare_test.ta_name
    try:
        kwargs = {"session_key": session_key, "app": ta_name}
        if use_credential_realm:
            kwargs["realm"] = (
                f"__REST_CREDENTIAL__#{ta_name}#configs/conf-{conf_file}"
            )
        cfm = conf_manager.ConfManager(**kwargs)
        return cfm.get_conf(conf_file).get(stanza_name)
    except ConfManagerException:
        raise Exception(
            f"Failed to retrieve configuration: {conf_file}"
        )


class AddonSettings:
    """Centralized reader for add-on global settings.

    Reads settings from ta_cisco_cloud_security_addon_settings.conf,
    stanza [addon_settings]. Provides typed properties with validation
    and sensible defaults.

    Usage:
        settings = AddonSettings(session_key)
        workers = settings.max_concurrent_threads
    """

    CONF_FILE = "ta_cisco_cloud_security_addon_settings"
    STANZA = "addon_settings"

    # Defaults and bounds for each setting
    _MAX_THREADS_DEFAULT = 1
    _MAX_THREADS_MIN = 1
    _MAX_THREADS_MAX = 10

    def __init__(self, session_key: str):
        self._session_key = session_key
        self._settings = self._load()

    def _load(self) -> dict:
        """Load settings from conf file. Returns empty dict on failure."""
        try:
            return get_conf_stanza_details(
                session_key=self._session_key,
                conf_file=self.CONF_FILE,
                stanza_name=self.STANZA,
                use_credential_realm=False,
            )
        except Exception:
            return {}

    @property
    def max_concurrent_threads(self) -> int:
        """Maximum number of concurrent worker threads (1-10, default 1)."""
        raw = self._settings.get(
            "max_concurrent_threads", self._MAX_THREADS_DEFAULT
        )
        try:
            value = int(raw)
            return max(
                self._MAX_THREADS_MIN,
                min(value, self._MAX_THREADS_MAX),
            )
        except (ValueError, TypeError):
            return self._MAX_THREADS_DEFAULT

def make_splunk_request(
    method: str,
    endpoint: str,
    session_key: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Any] = None,
    json_data: Optional[Dict[str, Any]] = None,
    use_json_output: bool = True,
    addon_namespace: Optional[bool] = None,
    clear_credentials: bool = False,
    count: Optional[int] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Union[Tuple[Dict[str, Any], Any], Dict[str, Any]]:
    """
    Make a request to the Splunk REST API.

    Args:
        method (str): The HTTP method to use (e.g., 'GET', 'POST', 'PUT', 'DELETE').
        endpoint (str): The endpoint to request (e.g., '/services/data/indexes').
            If addon_namespace is True, endpoint will be prefixed with the namespace path.
            If addon_namespace is False, endpoint should contain the complete URL.
        session_key (str): Splunk session key for authentication.
        headers (Dict[str, str], optional): HTTP headers to include in the request.
        params (Dict[str, Any], optional): URL parameters to include in the request.
        data (Any, optional): Data to send in the request body.
        json_data (Dict[str, Any], optional): JSON data to send in the request body.
        use_json_output (bool, optional): If True, will return parsed JSON response instead of raw tuple.
        addon_namespace (bool, optional): If True, uses import_declare_test.ta_name as namespace.
        clear_credentials (bool, optional): If True, get clear passwords for encrypted fields.
        count (int, optional): If provided, will be added to params as 'count'.
        max_retries (int, optional): Maximum number of retry attempts for recoverable errors.
        retry_delay (float, optional): Delay in seconds between retry attempts.

    Returns:
        If use_json_output is False:
            tuple[dict[str, Any], Any]: A tuple of (serverResponse, serverContent)
            - serverResponse: a dict of HTTP status information
            - serverContent: the body content
        If use_json_output is True:
            Dict[str, Any]: The parsed JSON response

    Raises:
        Exception: If the HTTP request fails for any reason.
    """

    # Prepare the full endpoint URL if addon_namespace is True
    if addon_namespace:
        endpoint = f"/servicesNS/nobody/{import_declare_test.ta_name}/{endpoint}"

    # Setup request parameters
    kwargs = {"sessionKey": session_key}
    if headers is not None:
        kwargs["headers"] = headers
    # Setup parameters and ensure JSON output if requested
    request_params = params or {}
    if use_json_output:
        request_params["output_mode"] = "json"
    # Add credential clearing parameter if requested
    if clear_credentials:
        request_params["--cred--"] = 1
    if count is not None:
        request_params["count"] = count
    if request_params:
        kwargs["getargs"] = request_params
    if data is not None:
        kwargs["postargs"] = data
    if json_data is not None:
        kwargs["jsonargs"] = json_data

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            response = rest.simpleRequest(
                endpoint, method=method, raiseAllErrors=True, **kwargs
            )

            if use_json_output:
                return json.loads(response[1])
            return response

        except (splunk.InternalServerError, splunk.SplunkdConnectionException) as e:
            last_exception = e
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            else:
                raise Exception(
                    f"HTTP Request failed after {max_retries + 1} attempts: {e}"
                )
        except Exception as e:
            raise Exception(f"HTTP Request failed: {e}")

    # This should never be reached, but just in case
    raise Exception(
        f"HTTP Request failed after {max_retries + 1} attempts: {last_exception}"
    )


def send_ui_notification(session_key: str, message: str, severity: str = "info"):
    """
    Sends a UI notification.

    Args:
        session_key (str): The Splunk session key for authentication.
        message (str): The message to display in the notification.
        severity (str): The severity level of the notification (e.g., "info", "warning", "error").
    """
    data = {
        "name": "message",
        "value": f"Cisco Secure Access Add-on for Splunk: {message}",
        "severity": severity,
    }
    try:
        make_splunk_request(
            method="POST",
            endpoint="messages",
            session_key=session_key,
            data=data,
            use_json_output=False,
        )
    except Exception as e:
        pass


def str_to_boolean(value: Union[str, bool, int, None]) -> bool:
    """
    Converts Splunk string boolean representations to Python boolean values.

    Args:
        value: The value to convert. Can be boolean, string, or numeric.

    Returns:
        bool: True if value is considered true, False otherwise.
    """
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        # Normalize the string value to uppercase for comparison
        value = value.upper()
        if value in ("TRUE", "T", "Y", "YES", "1"):
            return True
        elif value in ("FALSE", "F", "N", "NO", "NONE", "0", ""):
            return False


def bool_to_str(value: bool) -> str:
    """
    Converts a boolean value to its string representation.

    Args:
        value (bool): The boolean value to convert.

    Returns:
        str: "1" if value is True, "0" if value is False.
    """
    return "1" if value else "0"


def get_proxy_url_dict(session_key: str) -> Union[Dict[str, str], None]:
    """
    Returns a dictionary containing the http and https proxy URLs
    based on the proxy settings stored in the Splunk configuration.

    Args:
        session_key (str): The Splunk session key for authentication.

    Returns:
        Union[Dict[str, str], None]: A dictionary with "http" and "https" keys
        containing the proxy URLs, or None if no proxy is configured.

    Raises:
        Exception: If there is an error retrieving the proxy settings.
    """
    proxy_endpoint = "TA_cisco_cloud_security_addon_settings/proxy"
    try:
        response = make_splunk_request(
            method="GET",
            endpoint=proxy_endpoint,
            session_key=session_key,
            use_json_output=True,
            addon_namespace=True,
            clear_credentials=True,
        )
        proxy_config = response.get("entry", [{}])[0].get("content", {})
        if not proxy_config:
            return
        if not str_to_boolean(proxy_config.get("proxy_enabled")):
            return
        if not proxy_config.get("proxy_url") or not proxy_config.get("proxy_type"):
            return
        proxy_url = proxy_config.get("proxy_url")
        proxy_type = proxy_config.get("proxy_type")
        proxy_port = proxy_config.get("proxy_port", 0)
        proxy_username = proxy_config.get("proxy_username", "")
        proxy_password = proxy_config.get("proxy_password", "")
        if proxy_username:
            if not proxy_password:
                return
            # percent encode special characters
            proxy_username = quote(proxy_username)
            proxy_password = quote(proxy_password)
        proxy_credentials = (
            f"{proxy_username}:{proxy_password}@" if proxy_username else ""
        )
        host = (
            f"{proxy_type}://{proxy_credentials}[{proxy_url}]:{proxy_port}"
            if is_ipv6_address(address=proxy_url)
            else f"{proxy_type}://{proxy_credentials}{proxy_url}:{proxy_port}"
        )
        return {
            "http": host,
            "https": host,
        }

    except Exception as e:
        raise Exception(f"Failed to retrieve proxy settings: {e}")


def is_ipv6_address(address: str) -> bool:
    """
    Checks if the given IP address is an IPv6 address.

    Args:
        address (str): The IP address to check.

    Returns:
        bool: True if the IP address is IPv6, False otherwise.
    """
    try:
        ipaddress.IPv6Address(address)
        return True
    except ipaddress.AddressValueError:
        return False


def get_dir_prefix(prefix: str) -> str:
    """
    Returns the directory prefix from a given S3 prefix.

    Args:
        prefix (str): The S3 prefix from which to extract the directory prefix.

    Returns:
        str: The directory prefix, ensuring it ends with a slash.
        If the prefix is empty, returns "/".
        If the prefix does not contain a directory, returns "/".
    """
    if not prefix:
        return "/"
    dir_prefix = prefix.rstrip("/").rsplit("/", 1)
    dir_prefix = list(filter(None, dir_prefix))
    return dir_prefix[0] + "/" if len(dir_prefix) > 1 else "/"

def get_logger(log_name, log_level=logging.INFO):
    log_file = os.path.join(Common().log_path, f"{log_name}.log")
    logger = logging.getLogger(log_name)

    handler_exists = any(
        [True for item in logger.handlers if item.baseFilename == log_file]
    )

    if not handler_exists:
        file_handler = RotatingFileHandler(
            log_file, mode="a", maxBytes=25000000, backupCount=5
        )
        format_string = (
            "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%("
            "funcName)s:%(lineno)d | %(message)s "
        )
        formatter = logging.Formatter(format_string)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(log_level)
        logger.propagate = False

    return logger

class S3Utility:
    """
    A utility class for validating S3 credentials and bucket details.
    """

    def __init__(self, session_key: str):
        """
        Initializes the S3Utility with the Splunk session key.

        Args:
            session_key (str): The Splunk session key for authentication.
        """
        self._session_key = session_key
        self.proxy_config = None
        proxy_url_dict = get_proxy_url_dict(session_key)
        if proxy_url_dict:
            self.proxy_config = Config(
                proxies=proxy_url_dict,
            )

    def validate_keys(
        self, region: str, access_key_id: str, secret_access_key: str
    ) -> None:
        """
        Validates the S3 credentials.

        Args:
            region (str): The AWS region.
            access_key_id (str): The AWS access key ID.
            secret_access_key (str): The AWS secret access key.

        Raises:
            S3ValidationError: If any of the S3 credentials are invalid.
        """
        if not region or not access_key_id or not secret_access_key:
            raise S3ValidationError(
                "Invalid S3 credentials. Please provide valid access key, secret key, and region.",
            )
        try:
            kwargs = {
                "aws_access_key_id": access_key_id,
                "aws_secret_access_key": secret_access_key,
                "region_name": region,
            }
            if self.proxy_config:
                kwargs["config"] = self.proxy_config
            sts_client = boto3.client(
                "sts",
                **kwargs,
            )
            sts_client.get_caller_identity()

        except NoCredentialsError:
            raise S3ValidationError("No credentials provided.")
        except PartialCredentialsError:
            raise S3ValidationError("Incomplete credentials provided.")
        except ClientError as e:
            raise S3ValidationError("Invalid AWS access key id or secret access key.")
        except Exception as e:
            raise S3ValidationError(f"An unexpected error occurred: {e}")

    def get_event_type_prefixes(
        self,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        prefix: str,
    ) -> List[str]:
        """
        Retrieves the event type prefixes from the specified S3 bucket and prefix.

        Args:
            region (str): The AWS region.
            access_key_id (str): The AWS access key ID.
            secret_access_key (str): The AWS secret access key.
            bucket_name (str): The name of the S3 bucket.
            prefix (str): The S3 prefix to validate.

        Returns:
            List[str]: A list of event type prefixes found in the specified S3 bucket and prefix.

        Raises:
            S3ValidationError: If the provided S3 credentials are invalid or if the bucket is not accessible.
        """
        if (
            not region
            or not access_key_id
            or not secret_access_key
            or not bucket_name
        ):
            raise S3ValidationError(
                "Invalid S3 credentials. Please provide valid access key, secret key, bucket name, and region."
            )
        try:
            kwargs = {
                "aws_access_key_id": access_key_id,
                "aws_secret_access_key": secret_access_key,
                "region_name": region,
            }
            if self.proxy_config:
                kwargs["config"] = self.proxy_config
            s3_client = boto3.client("s3", **kwargs)
            bucket = s3_client.list_objects_v2(
                Bucket=bucket_name, Delimiter="/", Prefix=prefix
            )
        except (NoCredentialsError, PartialCredentialsError):
            raise S3ValidationError(
                "Invalid S3 credentials. Please provide valid access key, secret key, bucket name, region, and prefix."
            )
        except ClientError as e:
            error = e.response.get("Error", {})
            error_code = error.get("Code", "Unknown")
            error_msg = error.get("Message", "Unknown error")
            raise S3ValidationError(
                f"Unable to access S3 bucket '{bucket_name}': {error_msg if error_code != 'SignatureDoesNotMatch' else 'Invalid credentials or signature.'}"
            )
        except Exception as e:
            raise S3ValidationError(f"An unexpected error occurred: {e}")
        prefixes = bucket.get("CommonPrefixes", [])
        return [p["Prefix"] for p in prefixes]

class SSEUtility:
    """
    A utility class for interacting with the Cisco SSE API.
    """

    def __init__(self):
        """
        Initializes the SSEUtility with default API endpoint and headers.

        Sets the Cisco SSE API token endpoint URL and default headers for requests.
        """
        self.BASE_URL = "https://api.sse.cisco.com"
        self.headers = {"User-Agent": "CiscoCloudSecurityAddonForSplunk/python-requests/3x"}
        self.endpoint = "auth/v2/token"

    def make_api_request(
        self,
        url: str,
        method: str = "POST",
        headers: Dict[str, str] = None,
        data: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        proxies: Dict[str, str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        A helper function to make API requests.

        Args:
            url (str): The API endpoint URL.
            method (str): The HTTP method (default is "POST").
            headers (Dict[str, str]): The HTTP headers.
            data (Dict[str, Any]): The form-encoded data to send in the request body.
            json_data (Dict[str, Any]): The JSON data to send in the request body.
            proxies (Dict[str, str]): Proxy settings.
            timeout (int): The timeout for the request in seconds.

        Returns:
            Dict[str, Any]: The JSON response from the API.

        Raises:
            Exception: If the API call fails.
        """
        headers = headers or {}
        headers.update(self.headers)
        try:
            # Make the API request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                proxies=proxies,
                timeout=timeout,
            )

            # Raise an exception for HTTP errors
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 401:
                    raise Exception("Invalid credentials: Unauthorized access to the API.")
                raise http_err

            # Return the JSON response
            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    def generate_access_token(self, client_id: str, client_secret: str) -> str:
        """
        Generates an access token using the Cisco SSE token API.

        Args:
            client_id (str): The client ID for authentication.
            client_secret (str): The client secret for authentication.

        Returns:
            str: The access token.

        Raises:
            RestError: If the API call fails or the token cannot be generated.
        """
        # API endpoint
        url = f"{self.BASE_URL}/{self.endpoint}"

        # Encode client credentials in Base64
        base64_credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()

        # Prepare headers
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Prepare payload
        payload = {"grant_type": "client_credentials"}

        try:
            # Make the API request using the helper function
            response_data = self.make_api_request(url=url, headers=headers, data=payload)

            # Check if the access token is present in the response
            access_token = response_data.get("access_token")
            if not access_token:
                raise RestError(
                    status=401,
                    message="Invalid Secure Access Client Id or Secure Access Client Secret",
                )

            return access_token

        except RestError as re:
            # Re-raise the RestError as is
            raise
        except Exception as e:
            # Always raise the specific RestError for invalid credentials
            raise RestError(
                status=401,
                message="Invalid Secure Access Client Id or Secure Access Client Secret",
            )

