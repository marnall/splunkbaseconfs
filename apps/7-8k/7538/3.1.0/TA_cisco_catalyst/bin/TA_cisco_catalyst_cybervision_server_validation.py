"""Cisco Catalyst Cyber Vision Account Validation Class."""
import import_declare_test  # noqa: F401
import requests
import os

import splunk.admin as admin
import splunk.version as ver
from solnlib.utils import is_true

from splunktaucclib.rest_handler.endpoint.validator import Validator
import utils
import consts
import logger_manager
import cisco_catalyst_exceptions as cce

logger = logger_manager.get_logger("cybervision_account_validation")
ERR_MSG = "{} Please verify the account credentials or Proxy Configuration are correct."


class GetSessionKey(admin.MConfigHandler):
    """Class to initialize session key."""

    def __init__(self):
        """Initialize session key."""
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    """Class to Validate account fields."""

    def __init__(self, *args, **kwargs):
        """:param validator: user-defined validating function."""
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def get_proxy_settings(self, data):
        """
        Get proxy settings information if proxy is enabled.

        :param data: data
        :return: proxy_uri
        """
        if is_true(data.get('enable_proxy')):
            # Get proxy settings information
            proxy_port = data.get('proxy_port')
            proxy_url = data.get('proxy_url')
            proxy_type = data.get('proxy_type')
            proxy_username = data.get('proxy_username', '')
            proxy_password = data.get('proxy_password', '')
            proxy_uri = utils.get_proxy_uri(
                proxy_username, proxy_password, proxy_type, proxy_url, proxy_port
            )
            return {"http": proxy_uri, "https": proxy_uri}
        return None

    def validate_ip_address(self, ip_address):
        """
        Validate IP Address.

        :param ip_address: IP Address
        :return: None
        """
        if not ip_address.startswith('https://'):
            raise ValueError("IP Address must start with https.")

    def validate_api_token(self, api_token):
        """
        Validate API Token.

        :param api_token: API Token
        :return: None
        """
        if not api_token:
            raise ValueError("API Token is required.")

    def get_ssl_and_save_cert_file(self, session_key, use_ca_cert, custom_certificate, account_name):
        """
        Get SSL and save custom certificate file.

        :param session_key: session key
        :param use_ca_cert: use ca certificate
        :param custom_certificate: custom certificate
        :param account_name: account name
        :return: verify_ssl or cert_file_loc
        """
        verify_ssl = utils.get_verify_ssl(session_key, logger)
        if is_true(use_ca_cert) and custom_certificate:
            try:
                cert_file_loc = utils.save_cert_file(
                    custom_certificate, consts.CYBER_VISION_CERT_FILE_LOC.format(cert_name=account_name), logger
                )
                return cert_file_loc
            except OSError as e:
                err_msg = "Error while writing custom certificate to file: {}"
                raise OSError(err_msg.format(e))
            except Exception as e:
                err_msg = "Error while saving custom certificate: {}"
                raise cce.CybervisionFileSaveError(err_msg.format(e))
        return verify_ssl

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        try:
            session_key = GetSessionKey().session_key
            # Get Splunk Version
            splunk_version = ver.__version__
            proxy_settings = self.get_proxy_settings(data)

            ip_address = data['ip_address'].strip(" ").strip("/")
            data['ip_address'] = ip_address
            self.validate_ip_address(ip_address)

            api_token = data.get('api_token')
            self.validate_api_token(api_token)

            user_agent = "Splunk/{}".format(splunk_version)
            error_msg_prefix = "Connection unsuccessful."
            header = {
                'x-token-id': api_token,
                'user-agent': user_agent
            }

            use_ca_cert = data.get("use_ca_cert")
            custom_certificate = data.get("custom_certificate", "").strip()
            account_name = data.get('copy_account_name', "").strip()
            try:
                cert_file_loc = verify_ssl = self.get_ssl_and_save_cert_file(
                    session_key, use_ca_cert, custom_certificate, account_name
                )
                if len(custom_certificate):
                    data.pop("custom_certificate")
            except Exception as e:
                self.put_msg(e)
                logger.error(e)
                return False
            response = requests.get(
                "{}/api/3.0/components".format(ip_address),
                headers=header,
                verify=verify_ssl,
                proxies=proxy_settings,
                timeout=10
            )

            response.raise_for_status()
            if response.status_code == 200 or response.status_code == 201:
                try:
                    response.json()
                    return True
                except Exception:
                    self.put_msg(ERR_MSG.format(error_msg_prefix))
                    logger.error("API Token, IP Address or Proxy Configuration are incorrect.")
                    return False
            else:
                self.put_msg(ERR_MSG.format(error_msg_prefix))
                logger.error("API Token, IP Address or Proxy Configuration are incorrect.")
        except ValueError as e:
            self.put_msg(e)
            logger.error(e)
            return False
        except requests.exceptions.SSLError as e:
            err_msg = (
                "SSL certificate verification failed. Please add a valid SSL Certificate "
                "or Change VERIFY_SSL flag to False: {}"
            )
            self.put_msg(err_msg.format(e))
            logger.error(err_msg.format(e))
            if is_true(use_ca_cert) and custom_certificate and os.path.exists(cert_file_loc):
                os.remove(cert_file_loc)
                logger.info("Custom CA Certificate has been deleted {}.".format(cert_file_loc))
            return False
        except Exception:
            self.put_msg(ERR_MSG.format(error_msg_prefix))
            logger.error(
                "Could not validate account provided IP Address {}.".format(
                    ip_address
                )
            )
            return False
