# Copyright (c) 2022 NetApp, Inc., All Rights Reserved

import ta_netapp_sg_declare  # noqa: F401
import os
import requests
import splunk.admin as admin
import splunk.rest as rest
import json
from traceback import format_exc
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_helper import TARestHelper
import modinput_wrapper.base_modinput
from solnlib.utils import is_true
from input_module_storagegrid_api_input import read_conf_file
from netapp_sso_token import AzureSSOToken, MFATokenError
from netapp_utils import get_proxy_setting


class GetSessionKey(admin.MConfigHandler):
    """Get Session key."""

    def __init__(self):
        """Get session key from self."""
        self.session_key = self.getSessionKey()


class ModInputStorageGridApiInput(modinput_wrapper.base_modinput.BaseModInput):
    """Get logger from modinput."""

    def __init__(self):
        """Create new log file."""
        super(ModInputStorageGridApiInput, self).__init__("ta_netapp_sg", "storagegrid_account_validation")


class ValidateAccount(Validator):
    """For Account Validation."""

    def __init__(self, *args, **kwargs):
        """:param validator: user-defined validating function."""
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def validate(self, value, data):
        """To Validate User Credential."""
        self.helper = TARestHelper()
        self.logger = ModInputStorageGridApiInput()
        __URL_FORMAT = "__REST_CREDENTIAL__#TA_netapp-sg"\
                       "#configs/conf-ta_netapp_sg_settings"\
                       ":proxy``splunk_cred_sep``1:"
        self.__URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)
        self.session_key = GetSessionKey().session_key
        self.proxy_settings = self.get_proxy()
        content_from_conf = read_conf_file(self.session_key, 'ta_netapp_sg_settings', 'additional_parameters')
        GLOBAL_CERT_VERIFY = True if is_true(str(content_from_conf['cert_verify'])) else False

        if self.proxy_settings['http']:
            self.logger.log_info("Proxy is enabled.")

        try:
            if "auth_type" in data.keys() and data["auth_type"] == "azure":
                return self.validate_azure(data, GLOBAL_CERT_VERIFY)
            return self.validate_netapp(data, GLOBAL_CERT_VERIFY)

        except (requests.exceptions.SSLError,
                requests.exceptions.ProxyError, Exception) as e:
            self.handle_error(e)

        return False

    def validate_azure(self, data, global_cert_verify):
        azure_sso = AzureSSOToken(
            data["account_ip"],
            data["username"],
            data["password"],
            self.logger,
            self.proxy_settings,
            global_cert_verify,
        )
        token = azure_sso.get_sso_auth_token()
        if token and "auth_token" in token:
            self.logger.log_info("Account Configured Successfully")
            return True
        else:
            self.put_msg("Invalid Credentials.")
            self.log_and_message("Invalid Credentials.")
            return False

    def validate_netapp(self, data, global_cert_verify):
        payload = json.dumps({
            "username": data["username"],
            "password": data["password"]
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            version = self.get_api_version(str(data["account_ip"]), global_cert_verify)
            return self.authorize_account(str(data["account_ip"]), version, headers, payload, global_cert_verify)
        except Exception as e:
            self.logger.log_error("Error in calling version check or authorize API. Message = %s" % str(e))
            return False

    def get_api_version(self, account_ip, global_cert_verify):
        version_url = f"https://{account_ip}/api/versions"
        response = self.helper.send_http_request(
            version_url,
            "GET",
            verify=global_cert_verify,
            proxy_uri=self.proxy_settings['http'],
            timeout=60.0
        )
        return int(float(response.json()['apiVersion']))

    def authorize_account(self, account_ip, version, headers, payload, global_cert_verify):
        url = f"https://{account_ip}/api/v{version}/authorize"
        response = self.helper.send_http_request(
            url,
            method="POST",
            headers=headers,
            payload=payload,
            verify=global_cert_verify,
            proxy_uri=self.proxy_settings['http'],
            timeout=60.0
        )

        if response.status_code in {200, 201}:
            self.logger.log_info("Account Configured Successfully")
            return True
        else:
            self.put_msg("Please verify NetApp StorageGRID Credentials or proxy Details.")
            self.log_and_message("Please verify NetApp StorageGRID Credentials or proxy Details.")
            return False

    def log_and_message(self, message):
        self.put_msg(message)
        self.logger.log_error(message)

    def handle_error(self, error):
        if isinstance(error, requests.exceptions.SSLError):
            self.put_msg("SSL certificate verification failed. Please add a valid SSL Certificate or Change VERIFY_SSL flag to False")  # noqa: E502
            self.logger.log_debug("Exception during authentication : " + format_exc())
            self.log_and_message("SSL certificate verification failed. Please add a valid SSL Certificate or Change VERIFY_SSL flag to False")
        elif isinstance(error, requests.exceptions.ProxyError):
            self.put_msg("Please Verify Proxy Details")
            self.logger.log_debug("Exception during authentication : " + format_exc())
            self.log_and_message("Please Verify Proxy Details")
        else:
            self.put_msg("Could not connect to NetApp StorageGRID Account. Please recheck NetApp StorageGRID Credentials or Proxy settings.")  # noqa: E502
            self.logger.log_error("Exception {}".format(error))

    def get_proxy(self):
        """
        Give information of proxy if proxy is enable.

        :return: dictionary having proxy information
        """
        proxy_settings = {"http": None, "https": None}
        _, response_content = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-ta_netapp_sg_settings/proxy"
            .format(self.my_app),
            sessionKey=self.session_key,
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
                    sessionKey=self.session_key,
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True)
                response_dict = json.loads(
                    response_content)['entry'][0]['content']
                cred = json.loads(response_dict.get('clear_password', '{}'))
                proxy_password = cred.get("proxy_password", None)
            except Exception as e:
                self.put_msg("Error While Fetching Proxy")
                self.logger.log_error("Error While Fetching Proxy. {}".format(e))

        proxy = {
            "proxy_type": proxy_type,
            "proxy_username": proxy_username,
            "proxy_password": proxy_password,
            "proxy_url": proxy_url,
            "proxy_port": proxy_port,
        }

        proxy_settings = get_proxy_setting(proxy)
        return proxy_settings
