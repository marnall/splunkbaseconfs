import requests
import os
import json

import splunk.admin as admin
import splunk.version as ver
import splunk.rest as rest
from solnlib.utils import is_true

from splunktaucclib.rest_handler.endpoint.validator import Validator
import logger_manager as log
import TA_cisco_cybervision_utils as utils

logger = log.setup_logging("ta_cisco_cybervision_server_validation")


class GetSessionKey(admin.MConfigHandler):
    """Class to initialize session key."""

    def __init__(self):
        """Initializes session key."""
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    """Class to Validate account fields."""

    __URL_FORMAT = (
        "__REST_CREDENTIAL__#TA-cisco_cybervision#configs"
        "/conf-ta_cisco_cybervision_settings:proxy``splunk_cred_sep``1:"
    )
    __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)

    def __init__(self, *args, **kwargs):
        """:param validator: user-defined validating function."""
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def get_proxy(self):
        """
        Gives information of proxy if proxy is enable.

        :return: dictionary having proxy information
        """
        session_key = GetSessionKey().session_key
        proxy_settings = None

        _, response_content = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-ta_cisco_cybervision_settings/proxy".format(
                self.my_app
            ),
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )
        proxy_info = json.loads(response_content)["entry"][0]["content"]

        proxy_enabled = proxy_info.get("proxy_enabled")
        if not proxy_enabled:
            logger.info("Proxy is not enabled.")
            return proxy_settings

        proxy_port = proxy_info.get("proxy_port")
        proxy_url = proxy_info.get("proxy_url")
        proxy_type = proxy_info.get("proxy_type")
        proxy_username = proxy_info.get("proxy_username", "")
        proxy_password = ""

        if proxy_username:
            try:
                _, response_content = rest.simpleRequest(
                    "/servicesNS/nobody/{}/storage/passwords/".format(self.my_app)
                    + self.__URL_ENCODE,
                    sessionKey=session_key,
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True,
                )
                response_dict = json.loads(response_content)["entry"][0]["content"]
                cred = json.loads(response_dict.get("clear_password", "{}"))
                proxy_password = cred.get("proxy_password", None)
            except Exception as e:
                self.put_msg("Error While Fetching Proxy \n Error: {}".format(str(e)))
                logger.exception(
                    "Error While fetching proxy \n Error: {}".format(str(e))
                )
        proxy_settings = self.get_proxy_setting(
            proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
        )
        return proxy_settings

    def get_proxy_setting(
        self, proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
    ):
        """Function To get Proxy Setting."""
        if proxy_username and proxy_password:
            proxy_username = requests.compat.quote_plus(proxy_username)
            proxy_password = requests.compat.quote_plus(proxy_password)
            proxy_uri = "%s://%s:%s@%s:%s" % (
                proxy_type,
                proxy_username,
                proxy_password,
                proxy_url,
                proxy_port,
            )
        else:
            proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)
        proxy_settings = {"http": proxy_uri, "https": proxy_uri}

        return proxy_settings

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        # Get Splunk Version
        splunk_version = ver.__version__
        # Get proxy settings information
        try:
            proxy_settings = self.get_proxy()
        except Exception as exception:
            logger.exception(
                "Error while fetching proxy information.\n Error: {}".format(exception)
            )
            self.put_msg("Error while fetching proxy information.")
            return False

        ip_address = data["ip_address"]
        user_agent = "Splunk/{}".format(splunk_version)
        if not ip_address.startswith("https://"):
            self.put_msg("IP Address must start with https.")
            logger.error("IP Address must start with https.")
            return False
        api_token = data.get("api_token")
        if not api_token:
            self.put_msg("API Token is required.")
            logger.error("API Token is required.")
            return False
        verify_ssl = utils.VERIFY_SSL
        header = {"x-token-id": api_token, "user-agent": user_agent}
        try:
            connector = data.copy()
            use_ca_cert = connector.get("use_ca_cert")
            custom_certificate = connector.get("custom_certificate").strip()
            if is_true(use_ca_cert) and custom_certificate:
                logger.info("Custom CA Certificate has been provided.")
                cert_file_loc = utils.CERT_FILE_LOC.format(
                    cert_name=connector.get("copy_account_name").strip()
                )
                cert_dir_loc = os.path.dirname(cert_file_loc)
                if not os.path.exists(cert_dir_loc):
                    os.makedirs(cert_dir_loc)
                    logger.info("custom_certs directory has been created.")
                with open(cert_file_loc, "w") as f:
                    f.write(custom_certificate)
                verify_ssl = cert_file_loc
                logger.info(
                    "Custom CA Certificate has been copied at {}.".format(cert_file_loc)
                )

            request_url = f"{ip_address}/api/3.0/version"
            logger.info(
                f"Performing API request to Url {request_url}, verify: {verify_ssl}, proxies: {proxy_settings}"
            )

            try:
                response = requests.get(
                    request_url,
                    headers=header,
                    verify=verify_ssl,
                    proxies=proxy_settings,
                    timeout=10,
                )
                logger.info(
                    f"Received response with status code {response.status_code} and text: {response.text}"
                )
                response.raise_for_status()
            except Exception as e:
                request_error_msg = (
                    "To verify the server, an API GET request was performed to the endpoint '/api/3.0/version'. "
                    "While performing the request, an error occured: {}".format(str(e))
                )
                self.put_msg(request_error_msg)
                logger.error(request_error_msg)
                return False
            return True

        except requests.exceptions.SSLError as e:
            ssl_error_msg = (
                "SSL certificate verification failed. Please add a valid "
                "SSL Certificate or Change VERIFY_SSL flag to False.  {}".format(str(e))
            )
            self.put_msg(ssl_error_msg)
            logger.error(ssl_error_msg)
            if (
                is_true(use_ca_cert)
                and custom_certificate
                and os.path.exists(cert_file_loc)
            ):
                os.remove(cert_file_loc)
                logger.info(
                    "Custom CA Certificate has been deleted {}.".format(cert_file_loc)
                )
            return False
        except Exception as e:
            error_msg = "An error occurred while validating the server address of the account: {}".format(
                str(e)
            )
            self.put_msg(error_msg)
            logger.error(error_msg)
            return False
