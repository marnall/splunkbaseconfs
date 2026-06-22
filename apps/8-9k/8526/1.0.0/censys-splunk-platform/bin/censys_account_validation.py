import import_declare_test  # noqa: F401
import requests
import time

from splunktaucclib.rest_handler.endpoint.validator import Validator
from solnlib.splunkenv import get_splunkd_uri
import splunklib.client as client

import common.log as log
import common.proxy as proxy
from common.exceptions import CustomException
from common.api_client import get_session
from common.config_manager import get_proxy_data, is_true
from common.session_manager import get_session_key
from utils import (
    get_mgmt_hostname_and_port,
    get_splunk_version,
    get_python_version,
    get_censys_version,
)
from common.consts import (
    APP_NAME,
    PROTOCOL,
    Endpoints,
    API_REQUEST_TIMEOUT,
    PROXY_VALIDATION_ENDPOINT,
    INTERNAL_VERIFY_SSL,
)


class CensysAPIValidation(Validator):
    """Validator for checking the validity of Censys credentials."""

    def validate(self, value, data):
        """
        Validate the provided API key by making a request to the Censys API.

        Args:
            value: The value being validated (not used).
            data: Dictionary containing the API key.

        Returns:
            bool: True if validation is successful, False otherwise.
        """
        logger = log.get_logger("censys_validator")
        logger.info("Validating Censys Account...")
        org_id = data.get("organization_id")
        url = f"{PROTOCOL}{Endpoints.CENSYS_SERVER_ADDRESS}{Endpoints.CENSYS_ACCOUNT_ORGANIZATIONS.format(org_id)}"
        apikey = data.get("api_key", "")
        session_key = get_session_key(logger)
        headers = {"Authorization": f"Bearer {apikey}", "Accept": "application/json"}
        splunk_version = get_splunk_version(session_key)
        python_version = get_python_version()
        censys_version = get_censys_version()
        ts = time.time()
        user_agent = f"CensysSplunk/{censys_version} (Splunk/{splunk_version}; Python/{python_version}; ts={ts})"
        headers.update(
            {
                "User-Agent": user_agent
            }
        )
        proxy_settings = None
        proxy_data = get_proxy_data(logger, session_key)
        if proxy_data and is_true(proxy_data.get("proxy_enabled")):
            proxy_settings = proxy.get_proxies(proxy_data)
        try:
            session = get_session(proxies=proxy_settings, verify=True, headers=headers)
            response = session.get(
                url,
                timeout=API_REQUEST_TIMEOUT,
            )
            logger.debug(f"Censys API response code: {response.status_code}")
            if response.status_code == 200:
                logger.info("Account validation was completed successfully")
                return True
            else:
                logger.error(f"Error occurred. Response: {response.text}")
                self.put_msg(
                    "Connection Unsuccessful. Please verify API key or Organization ID is valid"
                )
                return False
        except requests.exceptions.ProxyError as proxy_error:
            logger.error(f"Proxy configuration error: {proxy_error}")
            self.put_msg("Proxy connection error. Please check proxy configurations")
            return False
        except Exception as e:
            logger.error(f"Validation error occurred: {e}")
            self.put_msg(
                "Connection Unsuccessful. Please verify API key or Organization ID is valid"
            )
            return False


class CensysProxyValidation(Validator):
    """Validator for checking the validity of proxy configuration."""

    def validate(self, value, data):
        """
        Validate the configured proxy by attempting to reach an external endpoint.

        Args:
            value: The value being validated (not used directly, proxy is read from config).
            data: Dictionary containing the stanza data (not used directly here).

        Returns:
            bool: True if validation is successful, False otherwise.
        """
        logger = log.get_logger("censys_proxy_validator")
        logger.info("Validating Censys Proxy configuration...")

        proxy_settings = None

        # If proxy is not enabled, there is nothing to validate – treat as success.
        if not int(value):
            logger.info("Proxy is not enabled. Skipping proxy validation.")
            return True

        proxy_settings = proxy.get_proxies(data)
        test_url = f"{PROTOCOL}{PROXY_VALIDATION_ENDPOINT}"

        try:
            logger.debug(
                f"Attempting proxy validation by reaching {test_url} "
                f"with timeout={API_REQUEST_TIMEOUT}"
            )
            response = requests.get(
                test_url,
                proxies=proxy_settings,
                timeout=API_REQUEST_TIMEOUT,
            )
            logger.debug(f"Proxy validation HTTP status code: {response.status_code}")

            if response.status_code == 200:
                logger.info("Proxy validation was completed successfully.")
                return True
            else:
                logger.error(
                    f"Proxy validation failed. Response code: {response.status_code}, "
                    f"Response: {response.text}"
                )
                self.put_msg(
                    "Proxy connection unsuccessful. Please verify proxy host, port, "
                    "and authentication details."
                )
                return False

        except requests.exceptions.ProxyError as proxy_error:
            logger.error(f"Proxy configuration error during validation: {proxy_error}")
            self.put_msg("Proxy connection error. Please check proxy configurations.")
            return False
        except requests.exceptions.ConnectTimeout as timeout_error:
            logger.error(f"Proxy connection timeout during validation: {timeout_error}")
            self.put_msg(
                "Proxy validation timed out. Please verify that the proxy can reach external networks."
            )
            return False
        except Exception as e:
            logger.error(f"Proxy validation error occurred: {e}")
            self.put_msg(
                "Proxy validation failed. Please verify proxy settings and network connectivity."
            )
            return False


class CensysSplunkEsSavedSearchesValidation(Validator):
    """Validator for Censys Splunk ES saved searches configuration."""

    def validate(self, value, data):
        """
        Validate Censys Splunk ES saved searches configuration.

        Args:
            value: The value to validate
            data: The data to validate

        Returns:
            bool: True if validation passes, False otherwise
        """
        logger = log.get_logger("censys_splunk_es_validator")
        logger.info("Validating Censys Splunk ES saved searches...")
        try:
            # Get Conf object of apps settings
            session_key = get_session_key(logger)

            if not self.is_splunk_es_app_exists(logger, session_key):
                self.put_msg("Splunk ES app is not installed.")
                return False

            global_account = data.get("global_account", "")
            run_saved_searches_for = data.get("run_saved_searches_for", "")

            new_cron = "*/30 * * * *"
            if run_saved_searches_for == "EVERY_SIXTY_MINUTES":
                new_cron = "*/60 * * * *"

            # Creating client for connecting server
            _, port = get_mgmt_hostname_and_port()
            service = client.connect(port=port, token=session_key, app=APP_NAME)
            censys_host_enrichment_ss = service.saved_searches[
                "censys_notable_index_host_enrichment"
            ]
            censys_web_property_enrichment_ss = service.saved_searches[
                "censys_notable_index_web_property_enrichment"
            ]
            censys_certificate_enrichment_ss = service.saved_searches[
                "censys_notable_index_certificate_enrichment"
            ]
            try:
                if not global_account:
                    censys_host_enrichment_ss.disable()
                    censys_web_property_enrichment_ss.disable()
                    censys_certificate_enrichment_ss.disable()
                    self.put_msg("Please select Censys Account.")
                    return False
                if bool(int(value)):
                    censys_splunk_account_name_definition = (
                        f"param.global_account={global_account}"
                    )
                    service.post(
                        "properties/macros/censys_splunk_account_name",
                        definition=censys_splunk_account_name_definition,
                    )

                    kwargs = {
                        "cron_schedule": new_cron,
                        "disabled": "0",
                    }
                    censys_host_enrichment_ss.update(**kwargs).refresh()
                    censys_web_property_enrichment_ss.update(**kwargs).refresh()
                    censys_certificate_enrichment_ss.update(**kwargs).refresh()

                else:
                    censys_splunk_account_name_definition = (
                        "param.global_account=<acc_name>"
                    )
                    service.post(
                        "properties/macros/censys_splunk_account_name",
                        definition=censys_splunk_account_name_definition,
                    )

                    censys_host_enrichment_ss.disable()
                    censys_web_property_enrichment_ss.disable()
                    censys_certificate_enrichment_ss.disable()
            except Exception as e:
                logger.error(
                    "Error while updating macro censys_splunk_account_name: {}".format(
                        str(e)
                    )
                )
                self.put_msg(
                    "Error while updating macro censys_splunk_account_name: {}".format(
                        str(e)
                    )
                )
                return False
        except Exception as e:
            logger.error(
                "Error while validating Splunk ES saved searches: {}".format(str(e))
            )
            self.put_msg(
                "Error while validating Splunk ES saved searches: {}".format(str(e))
            )
            return False
        return True

    def is_splunk_es_app_exists(self, logger, session_key):
        """
        Check if splunk es is installed.

        Args:
            logger: Logger object
            session_key: Session key

        Returns:
            bool: True if splunk es is installed, False otherwise
        """
        try:
            logger.info("Validating the Splunk ES app exists.")
            headers = {
                "Authorization": "Splunk {}".format(session_key),
                "Content-Type": "application/json",
            }
            response = requests.get(
                get_splunkd_uri() + "/servicesNS/-/SplunkEnterpriseSecuritySuite/",
                headers=headers,
                verify=INTERNAL_VERIFY_SSL,
            )
            if response.status_code != 200:
                logger.error("Splunk ES app does not exist.")
                msg = (
                    "Configure the Splunk ES app to use 'Splunk ES Enrichment' feature"
                )
                raise CustomException(msg)
            return True
        except Exception as e:
            logger.error(
                "Error while validating the Splunk ES app exists: {}".format(str(e))
            )
            self.put_msg(str(e))
            return False
