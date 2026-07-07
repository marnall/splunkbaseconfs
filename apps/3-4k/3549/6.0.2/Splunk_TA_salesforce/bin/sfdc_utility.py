#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import hashlib
import json
import logging
import re
import traceback
from typing import Optional, Tuple, Union, Dict, Any
from urllib.parse import quote

import requests
import sfdc_consts as sc
from solnlib import conf_manager, log, utils
from splunk import rest


def get_hashed_value(value: str) -> str:
    """Function to get the hash value

    :param value: Value to be hashed
    :return:      SHA256 hashed value
    """
    return hashlib.sha256(  # nosemgrep: fips-python-detect-crypto
        value.encode("utf-8")
    ).hexdigest()


class SFDCUtil:
    def __init__(
        self,
        log_file: str,
        input_items: Dict[str, Any] = {},
        account_info: Dict[str, Any] = {},
        proxies: Dict[str, Any] = {},
        sslconfig: Union[bool, str] = True,
        session_key: str = "",
        file_checkpoint_dir: Optional[str] = None,
    ) -> None:
        self.account_info = account_info
        self.input_items = input_items
        self.session_key = session_key
        self.logger = self.get_logger(log_file)
        self.sslconfig = sslconfig
        self.proxies = proxies
        self.file_checkpoint_dir = file_checkpoint_dir

    def _update_conf(
        self, conf_file: str, fields: Dict[str, Any], encrypted: bool = True
    ) -> None:
        """Function to update the conf file

        :param conf_file: Conf file to be updated
        :param fields:    Dict of fields which value needs to be encrypted
        """
        cfm = conf_manager.ConfManager(
            self.session_key,
            sc.APP_NAME,
            realm=f"__REST_CREDENTIAL__#{sc.APP_NAME}#configs/conf-{conf_file}",
        )
        conf = cfm.get_conf(conf_file)
        encrypted_keys = list(fields.keys()) if encrypted else []
        conf.update(self.account_info["name"], fields, encrypted_keys)

    def _delete_conf(self, conf_file: str, stanza_name: str) -> None:
        """Function to delete the conf file stanza

        :param conf_file: Conf file to be deleted
        :param stanza_name: Stanza name to be deleted
        """
        cfm = conf_manager.ConfManager(
            self.session_key,
            sc.APP_NAME,
            realm=f"__REST_CREDENTIAL__#{sc.APP_NAME}#configs/conf-{conf_file}",
        )
        conf = cfm.get_conf(conf_file)
        conf.delete(stanza_name)

    def update_access_token_in_conf_file(self, content: Dict) -> None:
        """Function to update the newly generated access token in conf file

        :param content: String containing information of newly generated access token
        """
        self.logger.debug(
            f"Saving the newly generated access token associated with account '{self.account_info['name']}'..."
        )
        if self.account_info["auth_type"] == "oauth":
            encrypt_fields = {
                "access_token": str(content["access_token"]),
                "client_secret": str(self.account_info["client_secret"]),
                "refresh_token": str(content["refresh_token"]),
            }
        else:
            encrypt_fields = {
                "access_token": content["access_token"],
                "client_secret_oauth_credentials": str(
                    self.account_info["client_secret_oauth_credentials"]
                ),
            }
        self._update_conf(sc.ACCOUNT_CONF_FILE, encrypt_fields)

    def _regenerate_oauth_access_tokens(self) -> bool:
        """Function to regenerate the expired access token

        :return: Boolean value indicating success or failure in generating access token
        """

        self.logger.info(
            f"Generating a new access token associated with account '{self.account_info['name']}'..."
        )

        response = self.get_token()

        if not response.ok:
            log.log_authentication_error(
                self.logger,
                requests.exceptions.HTTPError(
                    f"Error: {response.reason}", response=response
                ),
                msg_before=(
                    "Error occurred while regenerating the access token associated "
                    f"with account '{self.account_info['name']}'. "
                    f"Status={response.status_code}, Reason={response.reason}"
                ),
            )
            return False

        content = json.loads(response.content)
        self.account_info["access_token"] = str(content["access_token"])
        self.update_access_token_in_conf_file(content)
        self.logger.info(
            f"New access token associated with account '{self.account_info['name']}' generated "
            "and saved successfully in the configuration file"
        )
        return True

    def get_basic_header(self) -> Dict[str, Any]:
        """Function to get the basic header to be used in API call

        :return: Dict containing header information
        """
        if self.account_info["auth_type"] == "basic":
            header = {
                "Authorization": f"Bearer {self.account_info['sfdc_session_key']}"
            }
        else:
            header = {"Authorization": f"Bearer {self.account_info['access_token']}"}
        return header

    def make_rest_api(
        self, url: str, header: Dict[str, Any], method: str = "GET"
    ) -> Tuple[Optional[int], str]:
        """Function to make the REST API call

        :param url:    Url for API call
        :param header: Dict containing header information
        :param method: API method to be used (GET|POST)
        :return:       Tuple with optional status code and content of API response
        """
        content = ""
        for retry in range(3):
            try:
                if retry > 0:
                    self.logger.info(f"Retry count: {retry + 1}/3")
                self.logger.debug(
                    f"Invoking request to '{url}' using [{method}] method"
                )
                response = requests.request(
                    method,
                    url,
                    headers=header,
                    proxies=self.proxies,
                    timeout=120,
                    verify=self.sslconfig,
                )
                content = response.text
                self.logger.debug(
                    f"Received response with status code {response.status_code} for URL: {url}"
                )
                if response.status_code not in (200, 201):
                    http_error = requests.exceptions.HTTPError(
                        f"{response.status_code} Error: {response.reason} for url: {url}",
                        response=response,
                    )
                    log.log_authentication_error(
                        self.logger,
                        http_error,
                        msg_before=(
                            f"Error response from Salesforce REST API for input '{self.input_items['name']}', "
                            f"with status code = {response.status_code}"
                        ),
                    )
                    if response.status_code in (400, 404):
                        return response.status_code, content
                    if response.status_code in (401, 403):
                        if self.account_info["auth_type"] == "basic":
                            return response.status_code, content
                        log.log_authentication_error(
                            self.logger,
                            http_error,
                            msg_before="Failure potentially caused by expired access token. Regenerating access token.",
                        )
                        access_token_updated_status = (
                            self._regenerate_oauth_access_tokens()
                        )
                        if not access_token_updated_status:
                            log.log_authentication_error(
                                self.logger,
                                http_error,
                                msg_before=(
                                    "Unable to generate a new access token. "
                                    "Failure potentially caused by the oauth configuration. To fix the issue, "
                                    f"reconfigure the account associated with input: {self.input_items['name']}"
                                ),
                            )
                            return response.status_code, ""
                        header.update(
                            {
                                "Authorization": f"Bearer {self.account_info['access_token']}"
                            }
                        )
                        continue
                    return response.status_code, ""
                return response.status_code, content
            except Exception as e:
                log.log_exception(
                    self.logger,
                    e,
                    "REST API call Error",
                    msg_before=f"Failure occurred while connecting to {url}.\nTraceback: {traceback.format_exc()}",
                )

        return None, content

    def _regex_search(self, pattern: str, content: str) -> Dict[str, Any]:
        """Function to extract match to a pattern

        :return: Dict of pattern match
        """
        matches = re.search(pattern=pattern, string=content)
        return matches.groupdict() if matches else {}

    def extract_session_id(self, content: str) -> Optional[str]:
        """Function to extract salesforce session id while using basic auth

        :return: Dict of pattern match
        """
        return self._regex_search(sc.SESSION_ID_REGEX, content).get("sessionId")

    def extract_server_url(self, content: str) -> Optional[str]:
        """Function to extract salesforce server url while using basic auth

        :return: Dict of pattern match
        """
        return self._regex_search(sc.SERVER_URL_REGEX, content).get("serverUrl")

    def extract_user_account_id(self, content: str) -> Optional[str]:
        """Function to extract user Account Id

        :return: Dict of pattern match
        """
        return self._regex_search(sc.USER_ID_BASIC_REGEX, content).get("userid")

    def get_sslconfig(self) -> Union[bool, str]:
        """Function to get sslconfig from conf file

        :return: True or path of the ca_certs file
        """
        sslconfig: Union[bool, str] = True
        general_settings = self.get_conf_data(sc.SETTINGS_CONF_FILE, "general")
        if general_settings:
            ca_certs_path = general_settings.get("ca_certs_path") or ""
            if ca_certs_path:
                sslconfig = ca_certs_path
        return sslconfig

    def ensure_access_token(self) -> None:
        """Ensures that an access token exists in the specified conf file
        :return: None
        """
        self.logger.info(
            "Ensuring that an access token exists in the specified conf file"
        )
        self.logger.info(f"for the account info{self.account_info}")
        if not self.account_info.get("access_token"):
            self._regenerate_oauth_access_tokens()

    def get_token(self) -> requests.Response:
        if self.account_info["auth_type"] == "oauth":
            payload = {
                "grant_type": "refresh_token",
                "client_id": self.account_info["client_id"],
                "client_secret": self.account_info["client_secret"],
                "refresh_token": self.account_info["refresh_token"],
            }
        else:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.account_info["client_id_oauth_credentials"],
                "client_secret": self.account_info["client_secret_oauth_credentials"],
            }

        sfdc_token_regeneration_url = (
            f"https://{self.account_info['endpoint']}/services/oauth2/token"
        )
        return requests.request(
            "POST",
            sfdc_token_regeneration_url,
            data=payload,
            proxies=self.proxies,
            verify=self.sslconfig,
        )

    def login_sfdc(self) -> requests.models.Response:
        """Function to login to the salesforce

        :return: Response of API call
        """
        rq_body = (
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<env:Envelope xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">'
            "<env:Body>"
            '<n1:login xmlns:n1="urn:partner.soap.sforce.com">'
            f"<n1:username>{self.account_info['username']}</n1:username>"
            f"<n1:password><![CDATA[{self.account_info['password']}]]>{self.account_info.get('token') or ''}"
            "</n1:password>"
            "</n1:login></env:Body>"
            "</env:Envelope>"
        )

        url = f"https://{self.account_info['endpoint']}/services/Soap/u/{self.account_info['sfdc_api_version']}/"
        header = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "login"}
        self.logger.debug(f"Invoking request to '{url}' using [POST] method")
        response = requests.request(
            "POST",
            url,
            headers=header,
            data=rq_body,
            proxies=self.proxies,
            timeout=120,
            verify=self.sslconfig,
        )
        return response

    def handle_failed_login(self, content: str) -> Tuple[str, str]:
        """Function to handle failed login to the salesforce

        :param content: String containing response content
        :return:        Tuple of string indicating the login failure reason
        """
        error = self._regex_search(sc.FAULT_CODE_REGEX, content)
        fault_code = error.get("faultcode", sc.DEFAULT_ERROR)
        error_description = self._regex_search(sc.FAULT_STRING_REGEX, content)
        fault_string = error_description.get("faultstring", sc.DEFAULT_ERROR)

        code_msg_tbl = {
            "INVALID_LOGIN": "Invalid username, password, security token; or user locked out.",
            "LOGIN_MUST_USE_SECURITY_TOKEN": (
                "When accessing Salesforce, either via a desktop client "
                "or the API from outside of your company's trusted networks, you must add a security token "
                "to your password to log in."
            ),
            "REQUEST_LIMIT_EXCEEDED": "Login Failed, TotalRequests Limit exceeded.",
        }

        fault_msg = code_msg_tbl.get(fault_code, sc.DEFAULT_ERROR)
        return fault_string, fault_msg

    def is_account_missing(self) -> bool:
        """Function to check whether account is associated to the input or not

        :return: Boolean value
        """
        if "account" not in self.input_items:
            ui_error_msg = (
                f"Account configuration is missing for input '{self.input_items['name']}' "
                "in Splunk Add-on for Salesforce. Fix the configuration to resume data collection."
            )
            error_msg = (
                ui_error_msg
                + f" Exiting the invocation of input '{self.input_items['name']}'"
            )
            log.log_configuration_error(
                self.logger,
                Exception("Account configuration is missing"),
                msg_before=error_msg,
            )
            rest.simpleRequest(
                "messages",
                self.session_key,
                postargs={
                    "severity": "error",
                    "name": f"SFDC error message for input: {self.input_items['name']}",
                    "value": ui_error_msg,
                },
                method="POST",
            )
            return True
        return False

    def get_hashed_value(self, value: str) -> str:
        """Function to get the hash value

        :param value: Value to be hashed
        :return:      SHA256 hashed value
        """
        return hashlib.sha256(  # nosemgrep: fips-python-detect-crypto
            value.encode("utf-8")
        ).hexdigest()

    def get_conf_data(
        self,
        conf_file: str,
        stanza_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Function to get the conf file data

        :param conf_file:   Name of the conf file
        :param stanza_name: Stanza name to get the information for
        :return:            Dict containing conf file data
        """
        conf_data = {}
        try:
            cfm = conf_manager.ConfManager(
                self.session_key,
                sc.APP_NAME,
                realm=f"__REST_CREDENTIAL__#{sc.APP_NAME}#configs/conf-{conf_file}",
            )
            cfm_conf_file = cfm.get_conf(conf_file)
            if stanza_name:
                conf_data = cfm_conf_file.get(stanza_name)
            else:
                conf_data = cfm_conf_file.get_all()

        except conf_manager.ConfManagerException:
            log.log_exception(
                self.logger,
                conf_manager.ConfManagerException,
                "Get conf file data Error",
                msg_before=f"Encountered the error while reading {conf_file}.conf.\nTraceback: {traceback.format_exc()}",
            )
        return conf_data

    def get_logger(self, log_file: str) -> logging.Logger:
        """Function to get the logger

        :param log_file: Log file associated with logger
        :return:         Logging object
        """
        logger = log.Logs().get_logger(log_file)
        logging_config = self.get_conf_data(sc.SETTINGS_CONF_FILE, "logging")
        log_level = logging_config.get("loglevel") or "INFO"
        logger.setLevel(log_level)
        return logger

    def get_account_id(self) -> Optional[str]:
        """Function to fetch user account id to be added in Splunk event

        :return: String containing user Account Id
        """
        self.logger.debug(
            f"Fetching User Account Id for input '{self.input_items['name']}'"
        )
        header = self.get_basic_header()
        header.update({"Accept": "application/json"})
        url = f"{self.account_info['sfdc_server_url']}/services/oauth2/userinfo"
        _, content = self.make_rest_api(url, header, "POST")
        if not content:
            return None
        content = json.loads(content)
        if not isinstance(content, dict):
            return None
        user_id = content.get("user_id")
        self.logger.debug(
            f"Successfully fetched the user Account Id for input '{self.input_items['name']}'"
        )
        return user_id

    def build_proxy_info(self) -> dict:
        """Function to build the proxy information

        :return: Dict containing the proxy configuration to be used in API call
        """
        proxy_info: dict = {}
        proxy_config = self.get_conf_data(sc.SETTINGS_CONF_FILE, "proxy")

        if not utils.is_true(proxy_config.get("proxy_enabled")):
            self.logger.info("Proxy is not enabled")
            return proxy_info

        proxy_type = proxy_config["proxy_type"]
        rdns = utils.is_true(proxy_info.get("proxy_rdns"))

        # socks5 causes the DNS resolution to happen on the client
        # socks5h causes the DNS resolution to happen on the proxy server
        if rdns and proxy_type == "socks5":
            proxy_type = "socks5h"

        if proxy_config["proxy_url"] and proxy_config["proxy_port"]:
            if proxy_config.get("proxy_username") and proxy_config.get(
                "proxy_password"
            ):
                encoded_user = quote(proxy_config["proxy_username"])
                encoded_password = quote(proxy_config["proxy_password"])
                proxy_info = {
                    "http": (
                        f"{proxy_type}://{encoded_user}:{encoded_password}"
                        f'@{proxy_config["proxy_url"]}:{int(proxy_config["proxy_port"])}'
                    )
                }
            else:
                self.logger.info("Proxy has no credentials found")
                proxy_info = {
                    "http": f'{proxy_type}://{proxy_config["proxy_url"]}:{int(proxy_config["proxy_port"])}'
                }
            proxy_info["https"] = proxy_info["http"]

        return proxy_info
