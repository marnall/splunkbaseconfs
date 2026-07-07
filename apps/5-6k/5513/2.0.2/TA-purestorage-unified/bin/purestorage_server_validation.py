import requests
import os
import json
import traceback

import splunk.admin as admin
import splunk.version as ver
import splunk.rest as rest
import purestorage_unified_utils as utils

from splunktaucclib.rest_handler.endpoint.validator import Validator
from distutils.version import LooseVersion
import input_module_purestorage_flasharray
import logger_manager as log
from distutils.version import StrictVersion
logger = log.setup_logging('purestorage_unified_ta_server_validation')


class GetSessionKey(admin.MConfigHandler):
    """Description: Get Splunk session key."""

    def __init__(self):
        """Init."""
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    """Account validator class."""

    __URL_FORMAT = "__REST_CREDENTIAL__#TA-purestorage-unified#configs/conf-ta_purestorage_unified_settings:proxy" \
        "``splunk_cred_sep``1:"
    __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)

    def __init__(self, *args, **kwargs):
        """
        Init method.

        :param validator: user-defined validating function
        """
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
            "/servicesNS/nobody/{}/configs/conf-ta_purestorage_unified_settings/proxy"
            .format(self.my_app),
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=True)
        proxy_info = json.loads(response_content)['entry'][0]['content']
        if int(proxy_info.get("proxy_enabled", 0)) == 0:
            return proxy_settings

        proxy_port = proxy_info.get('proxy_port')
        proxy_url = proxy_info.get('proxy_url')
        proxy_type = proxy_info.get('proxy_type')
        proxy_username = proxy_info.get('proxy_username', '')
        proxy_password = ''

        if proxy_username:
            try:
                _, response_content = rest.simpleRequest(
                    "/servicesNS/nobody/{}/storage/passwords/".format(
                        self.my_app) + self.__URL_ENCODE,
                    sessionKey=session_key,
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True)
                response_dict = json.loads(
                    response_content)['entry'][0]['content']
                cred = json.loads(response_dict.get('clear_password', '{}'))
                proxy_password = cred.get("proxy_password", None)
            except Exception as e:
                self.put_msg("Error While Fetching Proxy")
                logger.exception(
                    "Error While fetching proxy \n Error: {}".format(str(e)))
        proxy_settings = self.get_proxy_setting(proxy_type, proxy_username,
                                                proxy_password, proxy_url,
                                                proxy_port)
        return proxy_settings

    def get_proxy_setting(self, proxy_type, proxy_username, proxy_password,
                          proxy_url, proxy_port):
        """Function To get Proxy Setting."""
        if proxy_username and proxy_password:
            proxy_username = requests.compat.quote_plus(proxy_username)
            proxy_password = requests.compat.quote_plus(proxy_password)
            proxy_uri = "%s://%s:%s@%s:%s" % (proxy_type, proxy_username,
                                              proxy_password, proxy_url,
                                              proxy_port)
        else:
            proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)
        proxy_settings = {"http": proxy_uri, "https": proxy_uri}

        return proxy_settings

    def check_api_version(self, header, resp, server_address, verify_ssl,
                          proxy_settings):
        """
        This checks for the REST API Versions supported by FlashBlade.

        :param header : Header to be passed in Endpoint
        :param resp : response from login endpoint
        :param server_address : ip address of FlashBlade Server
        :param verify_ssl : should verify ssl or not
        :param proxy_settings : settings for proxy server
        :return False if api version less than 1.5, True otherwise
        """
        del header['api-token']
        header['x-auth-token'] = resp.headers['x-auth-token']
        supported_version_list = requests.get(server_address + "/api/api_version",
                                              header,
                                              verify=verify_ssl,
                                              proxies=proxy_settings)
        flashblade_api_version = LooseVersion(
            str(supported_version_list.json()['versions'][-1]))
        min_support = LooseVersion("1.5")
        if flashblade_api_version < min_support:
            msg = 'Purity FlashBlade version below 2.2.9 is not supported.'\
                ' Please Upgrade to latest Purity Version available'
            logger.error(msg)
            self.put_msg(msg)
            return False

        return True

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
                "Error while fetching proxy information.\n Error: {}".format(
                    exception))
            self.put_msg(
                "Error while fetching proxy information.")
            return False

        server_address = data['server_address']
        user_agent = "Splunk/{}".format(splunk_version)
        error_msg_prefix = "Connection unsuccessful."
        verify_ssl = utils.read_conf_file(GetSessionKey().session_key, "verify_ssl")

        if server_address.startswith('https://') or server_address.startswith('http://'):
            self.put_msg(
                "The server address {} should not include the scheme/protocol.".format(server_address))
            logger.error(
                "The server address {} should not include the scheme/protocol.".format(server_address))
            return False
        else:
            server_address = "https://{}".format(server_address)
        if data['account_type'] == 'flash_blade_account':
            blade_config_message = "Error occured while configuring Flash Blade System:"
            # Set parameters
            api_token = data.get('api_token')
            if not api_token:
                logger.error("{blade_msg} Authentication Token is required.".format(
                    blade_msg=blade_config_message))
                self.put_msg("Authentication Token is required.")
                return False
            header = {
                'api-token': api_token,
                'user-agent': user_agent
            }
            config_details = {
                'server_address': server_address,
                'x_auth_token': api_token,
                'user_agent': user_agent,
                'proxy_settings': proxy_settings,
                'verify_ssl': verify_ssl
            }
            try:
                response = requests.post("{}/api/login".format(server_address),
                                         headers=header,
                                         verify=verify_ssl,
                                         proxies=proxy_settings)
                response.raise_for_status()
                config_details['x_auth_token'] = response.headers.get(
                    'x-auth-token')
                return self.check_api_version(header, response, server_address,
                                              verify_ssl, proxy_settings)
            except requests.exceptions.ConnectionError as e:
                if 'SSL: CERTIFICATE_VERIFY_FAILED' in str(e):
                    err_msg = 'SSLError: Please verify the SSL certificate for the provided configuration.'
                elif 'SSLEOFError' in str(e):
                    err_msg = 'Connection error: Please check your network connectivity.'
                elif 'Cannot connect to proxy' in str(e):
                    err_msg = "{blade_msg} {msg} Account authentication failed due to proxy error.\
                        \nPlease verify provided proxy settings.".format(
                        blade_msg=blade_config_message, msg=error_msg_prefix)
                else:
                    err_msg = "Unable to connect to server due to an unknown error. Please check\
                        purestorage_unified_ta_server_validation.log for details."
                logger.error("{blade_msg} Error: {exp}.".format(
                    blade_msg=blade_config_message, exp=e))
                self.put_msg(err_msg)
                return False
            except Exception:
                logger.error(
                    "{blade_msg} {msg} Please enter valid Authentication Token, Server Address or Proxy."
                    " Error: {exp}".format(
                        blade_msg=blade_config_message,
                        msg=error_msg_prefix,
                        exp=traceback.format_exc())
                )
                self.put_msg(
                    "{msg} Please enter valid Authentication Token, Server Address or Proxy."
                    .format(msg=error_msg_prefix))
                return False
            return True
        elif data['account_type'] == 'flash_array_account':
            api_token = data.get('api_token')
            array_config_message = "Error occured while configuring Flash Array System:"
            if not api_token:
                logger.error("{array_msg} Authentication Token is required.".format(
                    array_msg=array_config_message))
                self.put_msg("Authentication Token is required.")
                return False
            header = {'Content-type': 'application/json'}
            config_details = {
                'server_address': server_address,
                'api_token': api_token,
                'user_agent': user_agent,
                'proxy_settings': proxy_settings,
                'verify_ssl': verify_ssl
            }
            rest_version = self._choose_rest_version(config_details)
            data = None
            if not rest_version:
                rest_version = "1.18"

            # API token is passed in data for API v1.x
            # API token is passed in header for API v2.x
            if int(rest_version.split(".")[0]) == 2:
                header['api-token'] = api_token
                url = "{}/api/{}/{}".format(server_address, rest_version, "login")
            else:
                data = {'api_token': api_token}
                url = "{}/api/{}/{}".format(server_address,
                                            rest_version, "auth/session")
                data = json.dumps(data).encode("utf-8")

            try:
                response = requests.request(
                    "POST", url, headers=header, data=data, verify=verify_ssl, proxies=proxy_settings)
                response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                if 'SSL: CERTIFICATE_VERIFY_FAILED' in str(e):
                    err_msg = 'SSLError: Please verify the SSL certificate for the provided configuration.'
                elif 'SSLEOFError' in str(e):
                    err_msg = 'Connection error: Please check your network connectivity.'
                elif 'Cannot connect to proxy' in str(e):
                    err_msg = "{array_msg} {msg} Account authentication failed due to proxy error.\
                        \nPlease verify provided proxy settings.".format(
                        array_msg=array_config_message, msg=error_msg_prefix)
                else:
                    err_msg = "Unable to connect to server due to an unknown error. Please check\
                        purestorage_unified_ta_server_validation.log for details."
                logger.error("{array_msg} Error: {exp}.".format(
                    array_msg=array_config_message, exp=e))
                self.put_msg(err_msg)
                return False
            except Exception:
                logger.error(
                    "{array_msg} {msg} Please enter valid Authentication Token, Server Address or Proxy."
                    " Error: {exp}".format(
                        array_msg=array_config_message,
                        msg=error_msg_prefix,
                        exp=traceback.format_exc())
                )
                self.put_msg(
                    "{msg} Please enter valid Authentication Token, Server Address or Proxy."
                    .format(msg=error_msg_prefix))
                return False
            return True
        elif data['account_type'] == 'pure1':
            pure1_config_message = "Error occured while configuring Pure1 System:"
            jwt_token = data['api_token']
            if not jwt_token:
                logger.error("{pure1_msg} Authentication Token is required.".format(
                    pure1_msg=pure1_config_message))
                self.put_msg("Authentication Token is required.")
                return False
            post_data = {'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
                         'subject_token_type': 'urn:ietf:params:oauth:token-type:jwt',
                         'subject_token': jwt_token}       # noqa:  E226
            path = server_address + "/oauth2/1.0/token"
            try:
                response = requests.post(
                    path, data=post_data, verify=verify_ssl, proxies=proxy_settings)
                response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                if 'SSL: CERTIFICATE_VERIFY_FAILED' in str(e):
                    err_msg = 'SSLError: Please verify the SSL certificate for the provided configuration.'
                elif 'SSLEOFError' in str(e):
                    err_msg = 'Connection error: Please check your network connectivity.'
                elif 'Cannot connect to proxy' in str(e):
                    err_msg = "{pure1_msg} {msg} Account authentication failed due to proxy error.\
                        \nPlease verify provided proxy settings.".format(
                        pure1_msg=pure1_config_message, msg=error_msg_prefix)
                else:
                    err_msg = "Unable to connect to server due to an unknown error. Please check\
                        purestorage_unified_ta_server_validation.log for details."
                logger.error("{pure1_msg} Error: {exp}.".format(
                    pure1_msg=pure1_config_message, exp=e))
                self.put_msg(err_msg)
                return False
            except Exception:
                logger.error(
                    "{pure1_msg} {msg} Please enter valid Authentication Token, Server Address or Proxy."
                    " Error: {exp}".format(
                        pure1_msg=pure1_config_message,
                        msg=error_msg_prefix,
                        exp=traceback.format_exc())
                )
                self.put_msg(
                    "{msg} Please enter valid Authentication Token, Server Address or Proxy."
                    .format(msg=error_msg_prefix))
                return False
            return True
        else:
            message = "Field System Type is required."
            logger.error(message)
            self.put_msg(message)
            return False

    def _choose_rest_version(self, config_details):
        """Return the newest REST API version supported by target array."""
        supported_rest_versions = ["1.13", "1.14", "1.15", "1.16", "1.17", "1.18", "2.2"]
        versions = self._list_available_rest_versions(config_details)
        versions = [x for x in versions if x in supported_rest_versions]
        if versions:
            return max(versions, key=StrictVersion)
        else:
            return None

    def _list_available_rest_versions(self, config_details):
        """Return a list of the REST API versions supported by the array."""
        server_address = config_details['server_address']
        url = "{0}/api/api_version".format(server_address)
        verify_ssl = config_details['verify_ssl']
        proxy_settings = config_details['proxy_settings']
        try:
            response = requests.get(
                url, verify=verify_ssl, proxies=proxy_settings)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            base_msg = "Unable to get available versions from Server Address."
            if 'SSL: CERTIFICATE_VERIFY_FAILED' in str(e):
                err_msg = 'SSLError: Please verify the SSL certificate for the provided configuration.'
            elif 'SSLEOFError' in str(e):
                err_msg = 'Connection error: Please check your network connectivity.'
            elif 'Cannot connect to proxy' in str(e):
                err_msg = "Unable to connect to proxy. Please verify the configured proxy settings."
            else:
                err_msg = "Unable to connect to server due to an unknown error. Please check\
                    purestorage_unified_ta_server_validation.log for details."
            logger.error("{}. {} Error: {exp}.".format(
                base_msg, err_msg, exp=e))
            self.put_msg(err_msg)
            return []
        except Exception:
            logger.error(
                "Unable to get available versions from Server Address. Please check Server Address or Proxy."
                " Error: {}".format(traceback.format_exc()))
            self.put_msg(
                "Connection unsuccessful. Please enter valid Server Address or Proxy.")
            return []
        if response.status_code == 200 or response.status_code == 201:
            if "application/json" in response.headers.get("Content-Type", ""):
                content = response.json()
                if isinstance(content, list):
                    content = input_module_purestorage_flasharray.ResponseList(
                        content)
                elif isinstance(content, dict):
                    content = input_module_purestorage_flasharray.ResponseDict(
                        content)
                else:
                    logger.error("Response not in the expected json format.")
                    self.put_msg("Response not in the expected json format.")
                    return []
                content.headers = response.headers
                return content.get("version", [])
        else:
            logger.error(
                "Connection unsuccessful. Please enter valid Server Address or Proxy.")
            self.put_msg(
                "Connection unsuccessful. Please enter valid Server Address or Proxy.")
            return []
