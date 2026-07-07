"""This modules contain util class for validations."""
import json
import requests
import traceback
import time

import splunk.admin as admin
import splunk.rest as rest
from splunktaucclib.rest_handler.endpoint.validator import Validator
from requests.compat import quote_plus
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true
from solnlib.conf_manager import ConfManager
from setup_logger import setup_logging
from ta_mimecast_for_splunk_declare import ta_name as APP_NAME
from mimecast_exceptions import CredentialMissing, AccessTokenGenerationFailed

logger = setup_logging("ta_mimecast_for_splunk_utils")

URL_MAPPING = {
    "mimecast_siem_ci": {
        "uri": "/siem/v1/batch/events/ci?type=entities",
        "method": "GET"
    },
    "mimecast_siem": {
        "uri": "/siem/v1/batch/events/cg?type=av",
        "method": "GET"
    },
    "mimecast_audit": {
        "uri": "/api/audit/get-audit-events",
        "method": "POST"
    },
    "mimecast_data_leak_prevention": {
        "uri": "/api/dlp/get-logs",
        "method": "POST"
    },
    "mimecast_service_health": {
        "uri": "/api/email/get-email-queues",
        "method": "POST"
    },
    "mimecast_threat_intel_feed_regional": {
        "uri": "/api/ttp/threat-intel/get-feed",
        "method": "POST"
    },
    "mimecast_threat_intel_feed_targeted": {
        "uri": "/api/ttp/threat-intel/get-feed",
        "method": "POST"
    },
    "mimecast_ttp_attachment_protect": {
        "uri": "/api/ttp/attachment/get-logs",
        "method": "POST"
    },
    "mimecast_ttp_impersonation_protect": {
        "uri": "/api/ttp/impersonation/get-logs",
        "method": "POST"
    },
    "mimecast_ttp_url": {
        "uri": "/api/ttp/url/get-logs",
        "method": "POST"
    },
    "mimecast_awareness_training": {
        "uri": "/api/awareness-training/company/get-safe-score-details",
        "method": "POST"
    }
}

REST_CALL_URL = "__REST_CREDENTIAL__#{0}#{1}"
CONF_ACCOUNT_ENDPOINT = "configs/conf-ta_mimecast_for_splunk_account"
CONTENT_TYPE = "application/x-www-form-urlencoded"


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def get_proxy_clear_password(session_key):
    """
    Get clear password from splunk passwords.conf.

    :return: str/None: proxy password if available else None.
    """
    logger.debug("Reading proxy password in clear text.")
    try:
        manager = CredentialManager(
            session_key,
            app=APP_NAME,
            realm=REST_CALL_URL.format(
                APP_NAME, "configs/conf-ta_mimecast_for_splunk_settings"
            ),
        )
    except CredentialNotExistException:
        return None
    else:
        logger.debug("Proxy password found. Returning.")
        return json.loads(manager.get_password("proxy")).get("proxy_password")


def get_account_clear_credentials(session_key, user):
    """
    Get clear password from splunk passwords.conf.

    :return: str/None: account password if available else None.
    """
    logger.debug("Reading account credentials in clear text.")
    try:
        manager = CredentialManager(
            session_key,
            app=APP_NAME,
            realm=REST_CALL_URL.format(
                APP_NAME, CONF_ACCOUNT_ENDPOINT
            ),
        )
    except CredentialNotExistException:
        return None
    else:
        logger.debug("Account credentials found. Returning.")
        return json.loads(manager.get_password(user))


def get_proxy_configuration(session_key):
    """
    Get proxy configuration settings.

    :return: proxy configuration dict.
    """
    rest_endpoint = (
        "/servicesNS/nobody/{}/TA_mimecast_for_splunk_settings/proxy".format(APP_NAME)
    )

    _, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    logger.debug("Returning proxy details.")
    return json.loads(content)["entry"][0]["content"]


def get_proxy_uri(session_key, proxy_settings=None):
    """
    Generate proxy uri from provided configurations.

    :param session_key: Splunk Session Key
    :param proxy_settings: Proxy configuration dict. Defaults to None.
    :return: if proxy configuration available returns uri string else None.
    """
    logger.debug("Reading proxy configurations.")

    if not proxy_settings:
        proxy_settings = get_proxy_configuration(session_key)

    if is_true(proxy_settings.get("proxy_enabled", 0)):

        logger.info("Proxy is enabled. Using proxy server.")
        if proxy_settings.get("proxy_username"):
            proxy_settings["proxy_password"] = get_proxy_clear_password(session_key)

        http_uri = proxy_settings["proxy_url"]

        if proxy_settings.get("proxy_port"):
            http_uri = "{}:{}".format(http_uri, proxy_settings.get("proxy_port"))

        if proxy_settings.get("proxy_username") and proxy_settings.get(
            "proxy_password"
        ):
            http_uri = "{}:{}@{}".format(
                quote_plus(proxy_settings["proxy_username"], safe=""),
                quote_plus(proxy_settings["proxy_password"], safe=""),
                http_uri,
            )

        http_uri = "{}://{}".format(proxy_settings["proxy_type"], http_uri)

        proxy_data = {"http": http_uri, "https": http_uri}

        return proxy_data
    else:
        logger.info("Proxy is disabled or not configured. Skipping proxy.")
        return None


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_file = ConfManager(
        session_key,
        APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()


def get_valid_access_token(session_key, account_name):
    """
    Get a valid access token for the specified account.

    This method handles three cases for token regeneration:
    1) No access token in conf
    2) Access token is expired (check from expires_at timestamp stored in conf)
    3) Access token is expired (check from api call if it's giving 401 error with expire_access_token)

    :param session_key: Splunk session key
    :param account_name: Account name/stanza
    :return: Valid access token
    """
    logger.info("Getting valid access token for account: {}.".format(account_name))

    # Get account configuration
    account_conf = read_conf_file(session_key, "ta_mimecast_for_splunk_account", account_name)
    if not account_conf:
        logger.error("Account configuration not found for: {}.".format(account_name))
        raise CredentialMissing(f"Account configuration not found for: {account_name}")

    client_id = account_conf.get("client_id")
    base_url = account_conf.get("base_url")
    client_secret = get_account_clear_credentials(session_key, account_name).get("client_secret")

    if not all([client_id, base_url, client_secret]):
        logger.error("Missing required account configuration for: {}.".format(account_name))
        raise CredentialMissing(f"Missing required account configuration for: {account_name}")

    # Check if we have a valid token stored
    access_token = get_account_clear_credentials(session_key, account_name).get("access_token")
    expires_at = account_conf.get("expires_at")

    current_time = int(time.time())

    # Case 1: No access token in conf
    if not access_token:
        logger.info("No access token found in configuration, generating new token.")
        return generate_and_store_token(session_key, account_name, client_id, client_secret, base_url)

    # Case 2: Access token is expired (check from expires_at timestamp)
    if expires_at and int(expires_at) <= current_time:
        logger.info(
            "Access token expired (expires_at: {}, current_time: {}), generating new token."
            .format(expires_at, current_time)
        )
        return generate_and_store_token(session_key, account_name, client_id, client_secret, base_url)

    logger.info("Using existing valid access token.")
    return access_token


def generate_and_store_token(session_key, account_name, client_id, client_secret, base_url):
    """
    Generate a new access token and store it in the account configuration.

    :param session_key: Splunk session key
    :param account_name: Account name/stanza
    :param client_id: OAuth client ID
    :param client_secret: OAuth client secret
    :param base_url: Mimecast API base URL
    :return: New access token
    """
    logger.info("Generating new access token for account: {}.".format(account_name))

    # Get proxy settings
    proxy_settings = None
    try:
        proxy_settings = get_proxy_uri(session_key)
    except Exception:
        logger.error("Error getting proxy settings: {}.".format(traceback.format_exc()))
        proxy_settings = None

    # Prepare OAuth token request
    uri = "/oauth/token"
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    url = base_url + uri
    payload = "client_id={}&client_secret={}&grant_type=client_credentials".format(
        client_id, client_secret
    )

    # Get app version for user agent
    app_file = read_conf_file(session_key, "app", stanza="launcher")
    app_version = app_file.get("version", "unknown")

    headers = {
        "Content-Type": CONTENT_TYPE,
        "User-Agent": "{}-{}".format(APP_NAME, app_version),
    }

    try:
        response = requests.request(
            "POST", url, headers=headers, data=payload, proxies=proxy_settings
        )

        if response.ok and response.json().get("access_token"):
            access_token = response.json()["access_token"]
            expires_in = response.json().get("expires_in", 1799)
            expires_at = int(time.time()) + expires_in - 30  # 30 second buffer

            # Store the new token and expiration in account configuration
            update_account_token(session_key, account_name, access_token, expires_at, client_secret)

            logger.info("Successfully generated and stored new access token.")
            return access_token
        else:
            logger.error("Failed to generate access token: {}.".format(response.text))
            raise AccessTokenGenerationFailed(f"Failed to generate access token: {response.text}")

    except Exception as e:
        logger.error("Exception generating access token: {}.".format(str(e)))
        raise AccessTokenGenerationFailed(f"Exception generating access token: {str(e)}")


def update_account_token(session_key, account_name, access_token, expires_at, client_secret):
    """
    Update the account configuration with new token and expiration.

    :param session_key: Splunk session key
    :param account_name: Account name/stanza
    :param access_token: New access token
    :param expires_at: Token expiration timestamp
    """
    logger.info("Updating account configuration with new token for: {}.".format(account_name))

    try:
        realm = REST_CALL_URL.format(APP_NAME, CONF_ACCOUNT_ENDPOINT)

        cfm = ConfManager(session_key, APP_NAME, realm=realm)
        conf = cfm.get_conf('ta_mimecast_for_splunk_account')
        conf.update(
            account_name,
            {
                'expires_at': str(expires_at),
                'access_token': access_token,
                'client_secret': client_secret
            },
            ['access_token', 'client_secret']
        )

        logger.info("Successfully updated account configuration with new token.")

    except Exception as e:
        logger.error("Failed to update account configuration: {}.".format(str(e)))


def is_token_expired_response(response):
    """
    Check if the API response indicates token expiration.

    :param response: HTTP response object
    :return: True if response indicates token expiration, False otherwise
    """
    if response.status_code != 401:
        return False

    try:
        response_data = response.json()
        fail_array = response_data.get("fail", [])

        for fail_item in fail_array:
            if fail_item.get("code") == "token_expired" or "Access Token Expired" in fail_item.get("message", ""):
                logger.info("API response indicates token expiration.")
                return True

    except (ValueError, KeyError):
        logger.debug("Response is not valid JSON or missing expected fields.")

    return False


def refresh_token_if_needed(session_key, account_name, response):
    """
    Refresh token if the API response indicates token expiration.

    :param session_key: Splunk session key
    :param account_name: Account name/stanza
    :param response: HTTP response object that may indicate token expiration
    :return: New access token if refreshed, None otherwise
    """
    if is_token_expired_response(response):
        logger.info("Token expired detected in API response, refreshing token.")

        # Get account configuration to regenerate token
        account_conf = read_conf_file(session_key, "ta_mimecast_for_splunk_account", account_name)
        if not account_conf:
            logger.error("Account configuration not found for token refresh: {}.".format(account_name))
            return None

        client_id = account_conf.get("client_id")
        base_url = account_conf.get("base_url")
        client_secret = get_account_clear_credentials(session_key, account_name).get("client_secret")

        try:
            return generate_and_store_token(session_key, account_name, client_id, client_secret, base_url)
        except Exception as e:
            logger.error("Failed to refresh token: {}.".format(str(e)))
            return None

    return None


class ValidateMimecastAccount(Validator):
    """Validator for Mimecast Credentials."""

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        logger.info("Initiating configuration validation.")
        logger.info("Reading proxy and user data.")

        sessionkey = GetSessionKey().session_key
        proxy_settings = None

        mimecast_client_id = data.get("client_id")
        try:
            proxy_settings = get_proxy_uri(sessionkey)
        except Exception:
            logger.error(
                "An unexpected exception occurred: {}".format(traceback.format_exc())
            )
            proxy_settings = None

        mimecast_client_secret = data.get("client_secret")
        base_url = data.get("base_url")

        uri = "/oauth/token"
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        url = base_url + uri
        payload = "client_id={}&client_secret={}&grant_type=client_credentials".format(
            mimecast_client_id, mimecast_client_secret
            )

        app_file = read_conf_file(sessionkey, "app", stanza="launcher")
        app_version = app_file.get("version")

        headers = {
            "Content-Type": CONTENT_TYPE,
            "User-Agent": "{}-{}".format(APP_NAME, app_version),
        }
        response = None

        logger.info("Validating the provided configurations.")
        try:
            response = requests.request(
                "POST", url, headers=headers, data=payload, proxies=proxy_settings
            )
            if response.ok and response.json()["access_token"]:
                data["access_token"] = response.json()["access_token"]
                expires_in = response.json()["expires_in"] if response.json().get("expires_in") else 1799
                data["expires_at"] = int(time.time()) + expires_in - 30
                msg = "Configured Successfully"
                self.put_msg(msg)
                logger.info(msg)
                return True
            response.raise_for_status()
            msg = "Unable to configure new account. Error: {}".format(response.text)
            self.put_msg(msg)
            logger.error(msg)
            return False
        except Exception as e:
            if (
                "response" in locals()
                and response is not None
                and response.status_code == 401
            ):
                msg = "Invalid Credentials. Please enter the valid Client ID and Client Secret"
            elif (
                "response" in locals()
                and response is not None
                and response.status_code == 500
            ):
                msg = "Internal server error. Cannot verify Mimecast instance."
            else:
                msg = (
                    "Unable to request Mimecast instance. "
                    "Please validate the provided Mimecast Credentials and "
                    "Proxy configurations or check the network connectivity. "
                )
            self.put_msg(msg)
            logger.error(str(e))
            logger.error(msg)
            return False


class ValidateMimecastInput(Validator):
    """Validator for Mimecast Credentials."""

    def __init__(self, input_type):
        """Intiliaze the instance."""
        self.input_type = input_type
        self.api_uri = URL_MAPPING[input_type]["uri"]
        self.api_method = URL_MAPPING[input_type]["method"]

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        user = data.get("credentials")

        sessionkey = GetSessionKey().session_key
        conf_file = read_conf_file(sessionkey, "ta_mimecast_for_splunk_account", user)

        mimecast_client_id = conf_file.get("client_id")
        base_url = conf_file.get("base_url")
        mimecast_client_secret = get_account_clear_credentials(sessionkey, user).get("client_secret")

        logger.info("Initiating configuration validation.")
        logger.info("Reading proxy and user data.")

        proxy_settings = None
        try:
            proxy_settings = get_proxy_uri(sessionkey)
        except Exception:
            logger.error(
                "An unexpected exception occurred: {}".format(traceback.format_exc())
            )
            proxy_settings = None

        app_file = read_conf_file(sessionkey, "app", stanza="launcher")
        app_version = app_file.get("version")

        headers = {
            "Content-Type": CONTENT_TYPE,
            "User-Agent": "{}-{}".format(APP_NAME, app_version),
        }
        response = None
        api_res = None
        msg = (
                    "Unable to request Mimecast instance. "
                    "Please validate the provided Mimecast Credentials and "
                    "Proxy configurations or check the network connectivity. "
            )

        logger.info("Validating the provided configurations.")

        try:
            # Use centralized token management
            access_token = get_valid_access_token(sessionkey, user)

            endpoint_url = base_url + self.api_uri
            request_headers = {
                "Authorization": "Bearer {}".format(access_token),
                "Accept": "application/json",
                "User-Agent": "{}-{}".format(APP_NAME, app_version),
            }
            api_res = requests.request(
                self.api_method,
                endpoint_url,
                headers=request_headers,
                proxies=proxy_settings
            )

            # Check if token expired and retry with new token
            if api_res.status_code == 401:
                new_token = refresh_token_if_needed(sessionkey, user, api_res)
                if new_token:
                    request_headers["Authorization"] = f"Bearer {new_token}"
                    api_res = requests.request(
                        self.api_method,
                        endpoint_url,
                        headers=request_headers,
                        proxies=proxy_settings
                    )

            api_res.raise_for_status()
            if api_res.ok:
                msg = "Input Configured Successfully"
                self.put_msg(msg)
                logger.info(msg)
                return True

        except Exception as e:
            if (
                "api_res" in locals()
                and api_res is not None
                and api_res.status_code in [401, 403]
            ):
                msg = (
                    'The selected credentials "{}" does not have the permissions for this Input. '
                    'Please select the appropriate credentials OR '
                    'update your API application permissions.'.format(user)
                )
            self.put_msg(msg)
            logger.error(str(e))
            logger.error(msg)
            return False
