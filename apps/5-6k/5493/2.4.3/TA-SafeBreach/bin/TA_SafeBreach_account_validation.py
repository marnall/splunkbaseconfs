"""This file validates account."""
import requests
import os
import json
import ta_safebreach_declare  # noqa: F401
import splunk.admin as admin
import splunk.version as ver
import splunk.rest as rest
import ta_safebreach_const
from splunktaucclib.rest_handler.endpoint.validator import Validator
from solnlib.server_info import ServerInfo


class GetSessionKey(admin.MConfigHandler):
    """Session key."""

    def __init__(self):
        """Initialize Session Key."""
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    """Validate account class."""

    __URL_FORMAT = (
        "__REST_CREDENTIAL__#TA-SafeBreach#configs"
        "/conf-ta_safebreach_settings:proxy``splunk_cred_sep``1:"
    )
    __URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)

    def __init__(self, *args, **kwargs):
        """Param: validator: user-defined validating function."""
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def get_proxy(self):
        """
        Give information of proxy if proxy is enable.

        return: dictionary having proxy information
        """
        session_key = GetSessionKey().session_key
        proxy_settings = None

        _, response_content = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-ta_safebreach_settings/proxy".format(
                self.my_app
            ),
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )
        proxy_info = json.loads(response_content)["entry"][0]["content"]
        if int(proxy_info.get("proxy_enabled", 0)) == 0:
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
            except Exception:
                self.put_msg("Error While Fetching Proxy")
        proxy_settings = self.get_proxy_setting(
            proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
        )
        return proxy_settings

    def get_proxy_setting(
        self, proxy_type, proxy_username, proxy_password, proxy_url, proxy_port
    ):
        """Get Proxy Settings."""
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

        param value: value to validate.
        param data: whole payload in request.
        return: True or False
        """
        # Get Splunk Version
        splunk_version = ver.__version__

        # Get proxy settings information
        try:
            proxy_settings = self.get_proxy()
        except Exception:
            self.put_msg("Error while fetching proxy information.")
            return False
        response = None
        ip_address = data.get("host_name")
        user_agent = "Splunk/{}".format(splunk_version)
        api_token = data["api_token"]
        account_id = data["account_id"]
        verify_ssl = True if (data.get('verify_ssl') == "1" or ServerInfo(GetSessionKey().session_key).is_cloud_instance()) else False
        header = {"x-apitoken": api_token, "user-agent": user_agent}
        try:
            response = requests.get(
                "https://{}/api/data/v1/accounts/{}/executionsHistoryResults".format(
                    ip_address, account_id
                ),
                headers=header,
                verify=verify_ssl,
                timeout=10,
                proxies=proxy_settings,
            )
            response.raise_for_status()
            if response.status_code in (
                200,
                201,
            ):
                try:
                    response.json()
                    return True
                except Exception:
                    self.put_msg(
                        "Some error occured while converting response in json."
                    )
                    return False
            else:
                self.put_msg(
                    "Please verify your Account Id, API Token and "
                    "SafeBreach Management are correct."
                )
        except requests.exceptions.SSLError:
            self.put_msg(
                "SSL certificate verification failed. Please add a valid "
                "SSL Certificate(Mandatory for Splunk Cloud) or disable Verify Server Certificate checkbox"
            )
            return False

        except requests.exceptions.ProxyError:
            self.put_msg("Invalid Proxy credentials. Please recheck your Proxy settings.")
            return False

        except Exception:
            if response is not None:
                if response.status_code in (401,):
                    self.put_msg(
                        "Please verify your API Token is correct."
                    )
                    return False
            else:
                self.put_msg(
                    "Please verify API Token, SafeBreach Management, Proxy settings or Account Id "
                    "are correct."
                )
                return False
