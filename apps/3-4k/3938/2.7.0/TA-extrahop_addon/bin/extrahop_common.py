# encoding = utf-8
"""Wrapper for API calls to ExtraHop."""
# This file is part of an ExtraHop Supported Integration. Make NO MODIFICATIONS below this line

import requests
import urllib3
import base64
import json
import os
from requests.compat import quote_plus

import splunk.rest as rest
from solnlib import conf_manager
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.server_info import ServerInfo
from solnlib.utils import is_true
from solnlib import conf_manager

from ta_extrahop_addon_declare import ta_name, SETTINGS_CONF_FILE

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
APP_NAME = __file__.split(os.sep)[-3]

class ExtraHopClient(object):
    """ExtraHopClient is a simple wrapper around Requests.

    Session to save authentication and connection data.
    """

    def __init__(self, host, helper, verify_certs):
        """Init method for Client class."""
        self.host = host

        self.session = requests.Session()
        try:
            if helper._get_proxy_uri():
                self.session.proxies = get_proxy_uri(helper.context_meta['session_key'])
        except ValueError as ve:
            raise ValueError(ve)
        self.app_version = get_app_version(helper.context_meta['session_key'])
        self.splunk_version = get_splunk_version(helper.context_meta['session_key'])
        self.set_header_value(helper)
        self.session.verify = verify_certs

    def set_header_value(self, helper):
        """Set the Header value according to instance type."""
        if helper.get_arg("global_account").get("instance_type") == "on_prem_instance":
            api_key = helper.get_arg("global_account").get("api_key")
            self.session.headers = {
                "Accept": "application/json",
                "Authorization": "ExtraHop apikey={}".format(api_key),
                "ExtraHop-Integration": "Splunk-{}-TA-ExtraHop-{}".format(self.splunk_version, self.app_version)
            }
        else:
            client_id = helper.get_arg("global_account").get("client_id")
            client_secret = helper.get_arg("global_account").get("client_secret")
            payload = "grant_type=client_credentials"

            # Create API Token to get Access Token
            API_token = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()

            self.session.headers = {
                'Authorization': 'Basic {}'.format(API_token),
                'Content-Type': 'application/x-www-form-urlencoded',
                "ExtraHop-Integration": "Splunk-{}-TA-ExtraHop-{}".format(self.splunk_version, self.app_version)
            }

            # Get Access Token
            try:
                rsp = self.session.post(f"https://{self.host}/oauth2/token", payload)
                rsp.raise_for_status()
                access_token = rsp.json().get('access_token')
            except Exception as e:
                helper.log_error(f"Request to ExtraHop appliance resulted in an error: {e}")
                raise Exception(
                    f"Request to ExtraHop appliance resulted in an error: {rsp.text} ({rsp.status_code})")
            self.session.headers = {
                "Accept": "application/json",
                "Authorization": "Bearer {}".format(access_token),
                "ExtraHop-Integration": "Splunk-{}-TA-ExtraHop-{}".format(self.splunk_version, self.app_version)
            }

    def get(self, path):
        """Send GET request to ExtraHop API."""
        return self._api_request("get", path)

    def post(self, path, data):
        """Send POST request to ExtraHop API."""
        return self._api_request("post", path, data)

    def _api_request(self, method, path, data=None):
        """Handle API requests to ExtraHop API."""
        url = f"https://{self.host}/api/v1/{path}"

        if method == "get":
            rsp = self.session.get(url)
        elif method == "post":
            rsp = self.session.post(url, data=data)
        else:
            raise ValueError("Unsupported HTTP method {}".format(method))
        try:
            rsp.raise_for_status()
        except Exception:
            raise Exception(
                f"Request to ExtraHop appliance resulted in an error: {rsp.text} ({rsp.status_code})"
            )

        return rsp

def get_splunk_version(session_key):
    """Return the current Splunk Version."""
    try:
        server_info = ServerInfo(session_key)
        return server_info.version
    except:
        return None

def read_file_name(session_key, conf_file, stanza=None):
    """Read Conf file and return the requested stanza values."""
    conf_file = conf_manager.ConfManager(
        session_key,
        APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
    ).get_conf(conf_file)
    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()

def get_app_version(session_key):
        """Get current app version."""
        app_details = read_file_name(session_key, "app", stanza="launcher")
        return app_details.get("version")

def get_proxy_clear_password(session_key):
    """
    Get clear password from splunk passwords.conf.

    :return: str/None: proxy password if available else None.
    """
    try:
        manager = CredentialManager(
            session_key,
            app=APP_NAME,
            realm="__REST_CREDENTIAL__#{0}#{1}".format(
                APP_NAME, "configs/conf-ta_extrahop_addon_settings"
            ),
        )
        return json.loads(manager.get_password("proxy")).get("proxy_password")
    except CredentialNotExistException:
        return None


def get_proxy_configuration(session_key):
    """
    Get proxy configuration settings.

    :return: proxy configuration dict.
    """
    rest_endpoint = "/servicesNS/nobody/{}/TA_extrahop_addon_settings/proxy".format(APP_NAME)

    _, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    return json.loads(content)["entry"][0]["content"]


def get_proxy_uri(session_key, proxy_settings=None):
    """
    Generate proxy uri from provided configurations.

    :param session_key: Splunk Session Key
    :param proxy_settings: Proxy configuration dict. Defaults to None.
    :return: if proxy configuration available returns uri string else None.
    """
    if not proxy_settings:
        proxy_settings = get_proxy_configuration(session_key)

    if proxy_settings.get("proxy_enabled") == "0":
        return None

    if proxy_settings.get("proxy_username"):
        if proxy_settings.get("proxy_password") == "" or proxy_settings.get("proxy_password") is None:
            raise ValueError(
                "Proxy Password is not provided. Please provide the proxy password to perform the data collection."
            )
        proxy_settings["proxy_password"] = get_proxy_clear_password(session_key)

    if all(
        [
            proxy_settings,
            is_true(proxy_settings.get("proxy_enabled")),
            proxy_settings.get("proxy_url"),
            proxy_settings.get("proxy_type"),
        ]
    ):
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

        http_uri = "{}://{}".format(proxy_settings['proxy_type'], http_uri)

        proxy_data = {"http": http_uri, "https": http_uri}

        return proxy_data
    else:
        return None


def get_detection_stanza(session_key, stanza_name, helper):
    """
    Get the detections stanza from the conf file.

    :param session_key: Splunk Session Key
    :param stanza_name: Name of the stanza to be fetched.
    :return: The stanza from the conf file.
    """
    stanza_dict = {}
    try:
        extrahop_settings_obj = conf_manager.ConfManager(session_key, ta_name)
        extrahop_settings_conf = extrahop_settings_obj.get_conf(SETTINGS_CONF_FILE)
        settings_file_stanzas = extrahop_settings_conf.get_all()
        settings_items = list(settings_file_stanzas.items())
        if settings_items:
            for stanza, stanza_info in settings_items:
                if stanza == stanza_name:
                    stanza_dict = stanza_info
    except Exception as e:
        helper.log_error("Error received while fetching conf file: {}".format(e))

    return stanza_dict
