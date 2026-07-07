"""This file validates account."""
import requests
import datetime
import os
import json
import hmac
import hashlib
import base64
from urllib.parse import urlparse

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.admin_external import GetSessionKey
from splunk.rest import simpleRequest  # to fetch proxy from Splunk
from solnlib import log
from solnlib.splunkenv import make_splunkhome_path

# Set up logging context for account validation
try:
    log_directory = make_splunkhome_path(['var', 'log', 'splunk', 'TA-bloodhound-enterprise'])
    # Ensure directory exists
    os.makedirs(log_directory, exist_ok=True)
    log.Logs.set_context(
        directory=log_directory,
        namespace='TA_bloodhound_enterprise'
    )
except Exception:
    # Fallback to default logging if path setup fails
    log.Logs.set_context(
        namespace='TA_bloodhound_enterprise'
    )
logger = log.Logs().get_logger('account_validation')


class ValidateAccount(Validator):
    """Validate account class."""

    __URL_FORMAT = (
            " __REST_CREDENTIAL__#TA-bloodhound-enterprise#configs"
            "/conf-ta_bloodhound_enterprise_settings:proxy``splunk_cred_sep``1:"
        )
    __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)


    def __init__(self, *args, **kwargs):
        """Param: validator: user-defined validating function."""
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    @classmethod
    def set_session_key(cls, session_key):
        """Set session key (no-op, kept for compatibility with handler).
        
        The session key is now obtained directly via GetSessionKey().session_key
        in the get_proxy() method, so this method is maintained for compatibility
        but doesn't need to store the session key.
        """
        pass

    def get_proxy(self):
        """Fetch proxy settings from Splunk configuration."""
        proxy_settings = None
        try:
            logger.info("[CONFIG] Fetching proxy settings from Splunk configuration")
            session_key = GetSessionKey().session_key
            _, response_content = simpleRequest(
                f"/servicesNS/nobody/{self.my_app}/TA_bloodhound_enterprise_settings/proxy",
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
            proxy_info = json.loads(response_content)["entry"][0]["content"]
            if int(proxy_info.get("proxy_enabled", 0)) == 0:
                logger.info("[CONFIG] Proxy is disabled in configuration")
                return None

            proxy_url = proxy_info.get("proxy_url")
            proxy_port = proxy_info.get("proxy_port")
            proxy_type = proxy_info.get("proxy_type", "http")
            proxy_username = proxy_info.get("proxy_username", "")
            proxy_password = None
            logger.info(f"[CONFIG] Proxy enabled - URL: {proxy_url}, Port: {proxy_port}, Type: {proxy_type}, Username: {proxy_username[:3] if proxy_username else 'None'}...")

            if proxy_username:
                try:
                    logger.info("[CONFIG] Fetching proxy password from Splunk credentials")
                    _, response_content = simpleRequest(
                        "/servicesNS/nobody/{}/storage/passwords/".format(self.my_app)
                        + self.__URL_ENCODE,
                        sessionKey=session_key,
                        getargs={"output_mode": "json"},
                        raiseAllErrors=True,
                    )
                    response_dict = json.loads(response_content)["entry"][0]["content"]
                    cred = json.loads(response_dict.get("clear_password", "{}"))
                    proxy_password = cred.get("proxy_password", None)
                    logger.info("[CONFIG] Proxy password retrieved successfully")
                except Exception as e:
                    logger.error(f"[CONFIG] Error while fetching proxy password: {str(e)}")
                    self.put_msg("Error While Fetching Proxy")

            # add mechanism for fetching passwords
            if proxy_username and proxy_password:
                proxy_username = requests.compat.quote_plus(proxy_username)
                proxy_password = requests.compat.quote_plus(proxy_password)
                proxy_uri = f"{proxy_type}://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}"
            else:
                proxy_uri = f"{proxy_type}://{proxy_url}:{proxy_port}"

            proxy_settings = {"http": proxy_uri, "https": proxy_uri}
            logger.info(f"[CONFIG] Successfully retrieved proxy settings - Type: {proxy_type}, URI: {proxy_uri}, Port: {proxy_port}")


        except Exception as e:
            logger.error(f"[CONFIG] Exception in get_proxy(): {type(e).__name__}: {str(e)}", exc_info=True)
            self.put_msg("Error while fetching proxy information.")
        logger.info(f"[CONFIG] get_proxy() returning: {proxy_settings}")
        return proxy_settings

    def get_verify_ssl_certificates(self):
        """Return True to verify SSL certs, False to skip (e.g. internal CA). Default True. Same as rest_client."""
        try:
            session_key = GetSessionKey().session_key
            _, response_content = simpleRequest(
                f"/servicesNS/nobody/{self.my_app}/TA_bloodhound_enterprise_settings/connection",
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=False,
            )
            data = json.loads(response_content)
            entries = data.get("entry") or []
            if not entries:
                return True
            connection_info = entries[0].get("content") or {}
            val = connection_info.get("verify_ssl_certificates", "1")
            return str(val).strip().lower() in ("1", "true", "yes")
        except Exception as e:
            logger.warning(f"[CONFIG] Could not read connection settings, defaulting to verify SSL: {e}")
            return True

    def validate(self, value, data):
        """
        Check if the given value is valid.

        param value: value to validate.
        param data: whole payload in request.
        return: True or False
        """
        response = None
        token_key = data["token_key"]
        token_id = data["token_id"]
        domain_name = data["domain_name"]
        uri = '/api/v2/available-domains'
        method = 'GET'
        headers = {}
        logger.info(f"[VALIDATION] Starting account validation - Domain: {domain_name}, Token ID: {token_id[:8]}...")
        
        try:
            digester = hmac.new(token_key.encode(), None, hashlib.sha256)
            digester.update(f'{method}{uri}'.encode())
            digester = hmac.new(digester.digest(), None, hashlib.sha256)
            datetime_formatted = datetime.datetime.now().astimezone().isoformat('T')
            digester.update(datetime_formatted[:13].encode())
            digester = hmac.new(digester.digest(), None, hashlib.sha256)

            headers = {
                'User-Agent': 'BHE-Splunk-v1.1.0',
                'Authorization': f'bhesignature {token_id}',
                'RequestDate': datetime_formatted,
                'Signature': base64.b64encode(digester.digest()).decode(),
                'Content-Type': 'application/json',
            }

            # Fetch proxy settings
            logger.info("[VALIDATION] Calling get_proxy() to fetch proxy settings")
            proxy_settings = self.get_proxy()
            logger.info(f"[VALIDATION] get_proxy() returned: {proxy_settings}")

        except Exception as e:
            logger.error(f"[VALIDATION] Error while generating headers: {str(e)}", exc_info=True)
            self.put_msg("Error While generating headers.")
            return False

        if not domain_name.startswith("https://"):
            domain_name = "https://" + domain_name

        url_parser = urlparse(domain_name)
        domain_name = f"https://{url_parser.netloc}"
        url = f"{domain_name}{uri}"
        logger.info(f"[VALIDATION] Making validation request to: {url}")

        verify_ssl = self.get_verify_ssl_certificates()
        logger.info(f"[VALIDATION] verify_ssl={verify_ssl}")

        try:
            response = requests.get(
                url,
                headers=headers,
                proxies=proxy_settings,
                timeout=10,
                verify=verify_ssl,
            )
            response.raise_for_status()
            if response.status_code in (200, 201):
                try:
                    response.json()
                    logger.info(f"[VALIDATION] Account validation successful - Domain: {domain_name}")
                    self.put_msg("Credentials are correct!")
                    return True
                except Exception as e:
                    error_msg = f"Some error occurred while converting response in json. Response data - {response.content}"
                    logger.error(f"[VALIDATION] {error_msg}: {str(e)}")
                    self.put_msg(error_msg)
                    return False
            else:                
                error_msg = "Please verify your Tenant Domain, Token ID and Token Key are correct."
                logger.error(f"[VALIDATION] Validation failed with status code {response.status_code} - {error_msg}")
                self.put_msg(error_msg)
        except requests.exceptions.ProxyError as e:
            error_msg = (
                "Unable to validate credentials due to proxy connection error. "
                "Please check your proxy configuration in Settings or disable proxy if not needed."
            )
            logger.error(f"[VALIDATION] Proxy error during validation: {str(e)}")
            self.put_msg(error_msg)
            return False
        except Exception as e:
            if response is not None and response.status_code == 401:
                error_msg = "Please verify your Token ID and Token Key are correct."
                logger.error(f"[VALIDATION] Authentication failed (401 Unauthorized): {error_msg}: {str(e)}")
                self.put_msg(error_msg)
                return False
            else:
                error_msg = f"Please verify Tenant Domain, Token ID and Token Key are correct. {url} - {response.content if response else 'No response'}"
                logger.error(f"[VALIDATION] Validation failed: {str(e)} - {error_msg}")
                self.put_msg(error_msg)
                return False
