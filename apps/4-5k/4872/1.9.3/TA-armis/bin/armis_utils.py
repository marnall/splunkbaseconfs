import os
import armis_constants as constant
import re
import json
import traceback
import requests
from requests.compat import quote_plus
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from xml.etree.ElementTree import XML

from splunk import admin
import splunk.entity as entity
import splunk.rest as rest
from solnlib import conf_manager
from proxy_config import read_proxies_from_conf
from splunktaucclib.rest_handler.endpoint.validator import Validator
from log_manager import setup_logging
from solnlib.utils import is_true

logger = setup_logging("proxy_conf")
addon_name = os.path.abspath(__file__).split(os.sep)[-3]
STATUS_FORCELIST = list(range(500, 600)) + [429]


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        constant.APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(constant.APP_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza, only_current_app=True)
    return conf_file.get_all(only_current_app=True)
        

def get_splunk_credentials(session_key):
    """Get credentials of Query API.

    :param session_key: Splunk session key
    :return: Dictionary containing config details
    """
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=addon_name,
            owner="nobody",
            sessionKey=session_key,
            count=-1,
            search=addon_name,
        )
    except Exception:
        logger.exception(
            "message=get_splunk_credentials_error |"
            " Armis Error: Could not get {} credentials from " "splunk.".format(addon_name)
        )
        raise Exception(
            "Armis Error: Could not get {} credentials from " "splunk.".format(addon_name)
        )

    clear_password = None
    response_dict = {}
    for stanza, value in entities.items():
        try:
            password = value["clear_password"]
            password = json.loads(password)
            clear_password = password["splunk_password"]
            break
        except Exception:
            continue

    resp, content = rest.simpleRequest(
        "/servicesNS/nobody/" + addon_name + "/properties/ta_armis_settings/"
        "splunk_rest_host",
        sessionKey=session_key,
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    if clear_password:
        response_dict = {"splunk_password": clear_password}

    content = json.loads(content)

    for item in content["entry"]:
        if item["name"] == "splunk_password":
            continue
        response_dict[item["name"]] = item["content"]

    return response_dict


def get_session_key(helper, session_key=None):
    """Validate the Splunk credentials."""
    try:
        splunkserver = helper.get_global_setting("splunk_rest_host_url") or "localhost"
        if not session_key:
            session_key = helper.context_meta["session_key"]
        splunk_account_info = get_splunk_credentials(session_key)
        splunk_password = splunk_account_info.get("splunk_password", "")
        splunk_username = splunk_account_info.get("splunk_username", "")
        if (splunkserver not in ["127.0.0.1", "localhost"] or splunk_password or splunk_username):
            payload = "username={}&password={}".format(
                quote_plus(splunk_username), quote_plus(splunk_password)
            )
            splunk_server_port = splunk_account_info.get("splunk_rest_port") or '8089'
            splunk_verify_cert = is_true(splunk_account_info["splunk_verify_cert"])
            if splunkserver in ["127.0.0.1", "localhost"]:
                splunk_verify_cert = False
            splunk_url = "".join(
                ["https://", splunkserver, ":", splunk_server_port, "/services/auth/login"]
            )
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            response = requests.post(
                splunk_url,
                headers=headers,
                data=payload,
                verify=splunk_verify_cert,
            )
            session = XML(response.text).findtext("./sessionKey")
            session_key = "%s" % session
            if response.status_code == 401:
                logger.error(
                    " message=get_session_key_response_error | Please check the Splunk KVStore Rest credentials."
                    "| Response code = {} |".format(response.status_code)
                )
                return False
            if not response.status_code == requests.codes.ok:
                logger.error(
                    "message=get_session_key_response_error |"
                    " Error occurred while configuring the Splunk KVStore rest."
                    " Response code = {} Response text = {} |".format(response.status_code, response.text)
                )
                return False
    except requests.exceptions.SSLError as se:
        logger.error(
            "message=get_session_key_ssl_error |"
            " Please verify the SSL certificate for the Splunk KVStore rest configuration : {}".format(
                se
            )
        )
        return False
    except Exception as e:
        logger.error(
            "message=get_session_key_error |"
            " Error occurred while configuring the Splunk KVStore rest.\nError: {}".format(e)
        )
        return False
    return session_key


def get_app_version(session_key):
    """Return the version of TA specified in app.conf."""
    app_conf = read_conf_file(session_key, "app", stanza="launcher")
    version = app_conf.get("version")
    return version


def get_user_agent(session_key=None):
    """Return the user agent to pass in request header."""
    app_version = get_app_version(session_key)
    
    return "Armis Splunk Add-on/{}".format(app_version)


class IntervalValidator(Validator):
    """Invterval Validation."""

    def validate(self, value, data):
        """Validate interval field."""
        interval = data.get("interval")
        try:
            interval = int(interval)
            if interval < 0:
                raise Exception
            return True
        except Exception:
            self.put_msg("Interval should be a positive integer.")
            return False


class VulnerabilityIntervalValidator(Validator):
    """Invterval Validation for vulnerability."""

    def validate(self, value, data):
        """Validate interval field."""
        interval = data.get("interval")
        try:
            interval = int(interval)
            if interval < 86400:
                raise Exception
            return True
        except Exception:
            self.put_msg("Interval value should be greater than or equal to 86400 seconds.")
            return False


class VulnerabilitiesValidator(Validator):
    """API Key Validation for Vulnerabilities."""

    def validate(self, value, data):
        """Validate Invalid/Expired API Key."""
        try:
            self.session = self.requests_retry_session()
            session_key = GetSessionKey().session_key
            global_account = read_conf_file(session_key, "ta_armis_account", stanza=data.get("global_account"))
            self.token_url = "https://{}/api/v1/access_token/".format(global_account["armis_hostname"])
            self.search_url = "https://{}/api/v1/search/".format(global_account["armis_hostname"])
            headers = self.get_token(session_key, global_account["armis_api_key"])
            if headers:
                response = self.fetch_vulnerability(session_key, headers)
                if response.status_code != 200:
                    self.put_msg(response.json().get("message"))
                    return False

                return True
            
        except Exception as e:
            self.put_msg(e)
            return False
    
    def requests_retry_session(self,
                               retries=3,
                               backoff_factor=0.3,
                               status_forcelist=STATUS_FORCELIST,
                               session=None):
        """
        Create and return a session object.

        :param retries: Maximum number of retries to attempt
        :param backoff_factor: Backoff factor used to calculate time between retries.
        :param status_forcelist: A tuple containing the response status codes that should
         trigger a retry.
        :param session: Session object

        :return: Session Object
        """
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def fetch_vulnerability(self, session_key, headers):
        """Fetch Devices from the response."""

        params = {"aql": "in:vulnerabilities", "from": 0, "length": 1}
        proxy_settings = read_proxies_from_conf(session_key)
        if proxy_settings:
            logger.info("Fetching Vulnerabilities Data:Proxy is Enabled")
        else:
            logger.info("Fetching Vulnerabilities Data:Proxy is Disabled")
        response = self.session.get(self.search_url, params=params, headers=headers, proxies=proxy_settings)
        if response is None:
            return False
        return response

    def get_token(self, session_key, armis_api_key):
        """Get Access Token."""
        try:
            proxy_settings = read_proxies_from_conf(session_key)
            data_for_access_token = {"secret_key": armis_api_key}
            if proxy_settings:
                logger.info("Access Token:Proxy is Enabled")
            else:
                logger.info("Access Token:Proxy is Disabled")
            response = self.session.post(self.token_url, data=data_for_access_token, proxies=proxy_settings)
            if response.status_code == 400:
                self.put_msg('Invalid Armis API Key. The API Key is expired. Please regenerate it.')
                return False
            token = response.json().get("data").get("access_token")
            headers = {
                "Authorization": token,
            }
            return headers

        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            self.put_msg(
                "ArmisError: HTTPError or ConnectionError occurred while fetching device data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error: {}".format(quote_plus(str(e)))
            )
            self.put_msg(
                "ArmisDebug: HTTPError or ConnectionError occurred while fetching device data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error trace: {}".format(traceback.format_exc())
            )
            return False

        except Exception as e:
            self.put_msg("ArmisError: Could not retrieve token. Error: {}".format(str(e)))
            return False

            
class AqlQueryValidator(Validator):
    """Aql Query Validation for Devices."""

    def validate(self, value, data):
        """Validate Aql Query field."""
        aql_query = data.get("aql_query")
        try:
            if not re.search("timeFrame:", aql_query) or not re.search("in:devices", aql_query):
                self.put_msg("Device Query field must contain timeFrame and in:devices attributes")
                return False

            if not re.match("[\s\S]*timeFrame:\S\s*([1-9][0-9]*)", aql_query):
                self.put_msg('Please enter timeFrame value in the range of [1-90] days. Ex. timeFrame:"30 days"')
                return False

            self.session = self.requests_retry_session()

            session_key = GetSessionKey().session_key
            global_account = read_conf_file(session_key, "ta_armis_account", stanza=data.get("global_account"))
            self.token_url = "https://{}/api/v1/access_token/".format(global_account["armis_hostname"])
            self.search_url = "https://{}/api/v1/search/".format(global_account["armis_hostname"])
            headers = self.get_token(session_key, global_account["armis_api_key"])
            if headers:
                response = self.fetch_device(session_key, headers, aql_query)
                if response.status_code != 200:
                    self.put_msg(response.json().get("message"))
                    return False

                return True
            
        except Exception as e:
            self.put_msg(e)
            return False

    def requests_retry_session(self,
                               retries=3,
                               backoff_factor=0.3,
                               status_forcelist=STATUS_FORCELIST,
                               session=None):
        """
        Create and return a session object.

        :param retries: Maximum number of retries to attempt
        :param backoff_factor: Backoff factor used to calculate time between retries.
        :param status_forcelist: A tuple containing the response status codes that should
         trigger a retry.
        :param session: Session object

        :return: Session Object
        """
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def fetch_device(self, session_key, headers, aql_query):
        """Fetch Devices from the response."""

        params = {"aql": aql_query, "from": 0, "length": 1}
        proxy_settings = read_proxies_from_conf(session_key)
        if proxy_settings:
            logger.info("Fetching Devices Data:Proxy is Enabled")
        else:
            logger.info("Fetching Devices Data:Proxy is Disabled")
        response = self.session.get(self.search_url, params=params, headers=headers, proxies=proxy_settings)
        if response is None:
            return False
        return response

    def get_token(self, session_key, armis_api_key):
        """Get Access Token."""
        try:
            proxy_settings = read_proxies_from_conf(session_key)
            data_for_access_token = {"secret_key": armis_api_key}
            if proxy_settings:
                logger.info("Access Token:Proxy is Enabled")
            else:
                logger.info("Access Token:Proxy is Disabled")
            response = self.session.post(self.token_url, data=data_for_access_token, proxies=proxy_settings)
            if response.status_code == 400:
                self.put_msg('Invalid Armis API Key. The API Key is expired. Please regenerate it.')
                return False
            token = response.json().get("data").get("access_token")
            headers = {
                "Authorization": token,
            }
            return headers

        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            self.put_msg(
                "ArmisError: HTTPError or ConnectionError occurred while fetching device data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error: {}".format(quote_plus(str(e)))
            )
            self.put_msg(
                "ArmisDebug: HTTPError or ConnectionError occurred while fetching device data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error trace: {}".format(traceback.format_exc())
            )
            return False

        except Exception as e:
            self.put_msg("ArmisError: Could not retrieve token. Error: {}".format(str(e)))
            return False
