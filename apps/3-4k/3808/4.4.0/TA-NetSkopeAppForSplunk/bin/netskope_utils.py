"""General Utilities."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "common")))

import ta_netskopeappforsplunk_declare  # noqa: F401

import api.netskope_v2.client
import api.netskope_v1.client

import const
import datetime
import os
import six
import time
import croniter
import json
import requests
import inspect
import re
import socks
import splunk
import utility

try:
    from urllib.parse import quote_plus
except Exception:
    from urllib import quote_plus
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk import admin
from splunk import rest
from solnlib import conf_manager
from solnlib.credentials import CredentialManager
from solnlib.splunkenv import get_splunkd_uri

from calendar import timegm
from requests.exceptions import RequestException
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


# Max allowed size in bytes for Netskope lists
MAX_LIST_SIZE = 8388608

DEFAULT_LAST_DAYS = 7
UTC_FORMAT = r"""%Y-%m-%dT%H:%M:%SZ"""

BASE_URL = "https://{}/api/v1/{}"
SUB_CHECKPOINT_KEY = "{}_sub_checkpoint"

NETSKOPE_API_VERSION = "v1"
ALERTS_ENDPOINT = "alerts"
EVENTS_ENDPOINT = "events"
UPDATE_FILE_HASH_LIST_ENDPOINT = "updateFileHashList"
UPDATE_URL_LIST_ENDPOINT = "updateUrlList"

SKIP_LIMIT = 500000
MAX_WORKER_THREADS = 2
REQUESTS_TIMEOUT = 180
VERIFY_SSL = True
INTERNAL_VERIFY_SSL = False

START_DATETIME_LAST_DAYS = 90
DEFAULT_LAST_DAYS = 7

STATUS_FORCELIST = list(range(500, 600)) + [429]


APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
NETSKOPE_SETTINGS_CONF = "ta_netskopeappforsplunk_settings"
NETSKOPE_ACCOUNT_CONF = "ta_netskopeappforsplunk_account"
NETSKOPE_STORAGE_ACCOUNT_CONF = "ta_netskopeappforsplunk_storage_account"

ERR_MSG_INTERVAL_OUT_OF_RANGE = "Interval is out of range. It should be positive integer."
ERR_MSG_INTERVAL_INVALID = ERR_MSG_INTERVAL_EXCEPTION = "Invalid Interval, please enter valid interval"

GEN_ERROR_MSG = "exception_type={} file_name={} exception_line={} input_name={} message={}"


def current_time_in_milli_sec():
    """Return current time in milli seconds."""
    return float(time.time())


def get_user_agent(hostname, app_version=None, session_key=None, is_webtx=False):
    """Return the user agent to pass in request header."""
    if app_version is None:
        app_version = utility.get_app_version(session_key)
    if is_webtx:
        return "Splunk-TA-{}-{}-WebTx".format(app_version, hostname)
    else:
        return "Splunk-TA-{}-{}".format(app_version, hostname)


def get_check_point(collection, key, session_key=None):
    """Return given key named checkpoint from KV Store."""
    url = "/servicesNS/nobody/{app_name}/storage/collections/data/{collection}/{key}?output_mode=json".format(
        app_name=APP_NAME, collection=quote_plus(collection), key=quote_plus(key)
    )
    args = {}
    try:
        response, content = splunk.rest.simpleRequest(
            url, sessionKey=session_key, getargs=args, method="GET", raiseAllErrors=True
        )
    except Exception as ex:
        if "[HTTP 404]" in str(ex):
            # Key doesn't exists
            return None
        raise ex

    content = json.loads(content.decode())
    return content.get("state")


def set_check_point(collection, key, state, session_key=None):
    """Upsert given key named checkpoint into KV Store."""
    if not session_key:
        session_key = GetSessionKey().session_key
    url = "/servicesNS/nobody/{app_name}/storage/collections/data/{collection}/batch_save?output_mode=json".format(
        app_name=APP_NAME, collection=quote_plus(collection)
    )
    args = [{"_key": key, "state": state}]
    response, content = splunk.rest.simpleRequest(
        url, sessionKey=session_key, jsonargs=json.dumps(args), method="POST", raiseAllErrors=True
    )
    content = json.loads(content.decode())
    return isinstance(content, list)


def create_sourcetype(input_type):
    """Create source type."""
    if input_type == "client":
        input_type = "clients"
    return "netskope:{}".format(input_type)


def lineno():
    """Return the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def filename():
    """Return the current file name in our program."""
    return os.path.split(inspect.currentframe().f_back.f_code.co_filename)[1]


def get_file_from_traceback(exc_tb):
    """
    Return the file name from traceback object.

    :param exc_tb: exception traceback object

    :return: filename from where exception thrown
    """
    return os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]


def reload_batch_input(session_key):
    """
    Reload the inputs present under data/inputs/monitor.

    :param session_key: session_key for Splunk Authentication
    """
    try:
        rest.simpleRequest(
            "/servicesNS/nobody/{}/data/inputs/monitor/_reload".format(APP_NAME),
            session_key,
            method="POST",
            raiseAllErrors=True,
        )
    except Exception as e:
        raise Exception("Error while reloading batch stanza: {}".format(e))


def get_clear_creds(session_key, conf_file, global_account):
    """
    Get unencrypted creds from passwords.conf.

    :return: Token and Service Account (json) in clear text
    """
    manager = CredentialManager(
        session_key,
        app=APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
    )

    clear_creds = None

    try:
        clear_creds = json.loads(manager.get_password(global_account))
    except Exception as e:
        raise Exception(e)

    return clear_creds


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def get_account_stanza(account_name, session_key=None):
    """Return given account stanza."""
    if not session_key:
        session_key = GetSessionKey().session_key

    account_config = get_clear_creds(session_key, NETSKOPE_ACCOUNT_CONF, account_name)
    account_stanza = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF, stanza=account_name)
    account_config["hostname"] = account_stanza.get("hostname")

    return account_config


def get_storage_account_stanza(storage_account_name, session_key=None):
    """Return given account stanza."""
    if not session_key:
        session_key = GetSessionKey().session_key

    account_config = get_clear_creds(session_key, NETSKOPE_STORAGE_ACCOUNT_CONF, storage_account_name)
    account_stanza = read_conf_file(session_key, NETSKOPE_STORAGE_ACCOUNT_CONF, stanza=storage_account_name)
    account_config["dest_container_name"] = account_stanza.get("dest_container_name")

    return account_config


class IntervalValidator(Validator):
    """Invterval Validation."""

    def validate(self, value, data):
        """Validate interval field."""
        interval = data.get("interval")
        try:
            try:
                interval = int(interval)
                if interval <= 0:
                    self.put_msg("Interval should be a positive integer.")
                    return False
                return True
            except ValueError:
                if croniter.croniter.is_valid(interval):
                    return True
                else:
                    self.put_msg("Invalid Interval. Please enter valid interval.")
                    return False
        except Exception:
            self.put_msg("Internal exception occured. Please try again.")
            return False


class WtIntervalValidator(Validator):
    """Extend base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        interval = data.get("interval")
        try:
            interval = int(interval)
            if interval < 86400:
                self.put_msg("Time interval must be a positive integer greater than or equal to 86400.")
                return False
            return True
        except Exception:
            try:
                now = datetime.datetime.now()
                cron = croniter.croniter(interval, now)
                first_invocation = cron.get_next(datetime.datetime)
                second_invocation = cron.get_next(datetime.datetime)
                duration = int((second_invocation - first_invocation).total_seconds())
                if duration < 86400:
                    self.put_msg("Cron schedule must be greater or equal to one day.")
                    return False
            except Exception:
                self.put_msg("Time interval of input must be in seconds or cron schedule.")
                return False
        if len(str(interval).split()) < 6:
            return True
        else:
            self.put_msg("Time interval of input must be in seconds or cron schedule.")
            return False


def get_epoch_time(date_time):
    """Convert datetime object to epoch time."""
    try:
        utc_time = time.strptime(date_time, UTC_FORMAT)
        epoch_time = timegm(utc_time)
        return epoch_time
    except Exception:
        return None


def get_default_datetime(last_days=DEFAULT_LAST_DAYS):
    """Return default datetime."""
    return (datetime.datetime.utcnow() - datetime.timedelta(days=last_days)).strftime(UTC_FORMAT)


def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=STATUS_FORCELIST, session=None):
    """
    Create and return a session object.

    :param retries: Maximum number of retries to attempt
    :param backoff_factor: Backoff factor used to calculate time between retries.
    :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
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


def is_true(val):
    """
    Check truthy value of the given parameter.

    :param val: Parameter of which truthy value is to be checkeds

    :return: True / False
    """
    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False


def make_netskope_url(platform_url, endpoint, api_version=NETSKOPE_API_VERSION):
    """Create Netskope URL."""
    if not (
        platform_url
        and endpoint
        and isinstance(endpoint, six.string_types)
        and isinstance(platform_url, six.string_types)
    ):
        return None
    if not (api_version and isinstance(api_version, six.string_types)):
        api_version = NETSKOPE_API_VERSION
    return "https://{}/api/{}/{}".format(platform_url.strip(), api_version.strip(), endpoint.strip())


def create_uri(proxy_enabled, proxy_settings):
    """
    Create proxy url from the given proxy settings.

    :param proxy_enabled: True if Proxy config is enabled. False otherwise
    :param proxy_settings: Proxy metadata

    :return: Proxy URI
    """
    uri = None
    if is_true(proxy_enabled) and proxy_settings.get("proxy_url") and proxy_settings.get("proxy_type"):
        uri = proxy_settings["proxy_url"]
        if proxy_settings.get("proxy_port"):
            uri = "{}:{}".format(uri, proxy_settings.get("proxy_port"))
        if proxy_settings.get("proxy_username") and proxy_settings.get("proxy_password"):
            uri = "{}://{}:{}@{}/".format(
                proxy_settings["proxy_type"],
                requests.compat.quote_plus(str(proxy_settings["proxy_username"])),
                requests.compat.quote_plus(str(proxy_settings["proxy_password"])),
                uri,
            )
        else:
            uri = "{}://{}".format(proxy_settings["proxy_type"], uri)
    return uri


def create_requests_proxies_helper(proxy_enabled, proxy_settings):
    """
    Create proxy dictionary used in requests module.

    :param proxy_enabled: True if Proxy config is enabled. False otherwise
    :param proxy_settings: Proxy metadata

    :return: Proxy dict
    """
    proxies = {}
    proxy_uri = create_uri(proxy_enabled, proxy_settings)
    if proxy_uri:
        proxies = {"http": proxy_uri, "https": proxy_uri}
    return proxies


def create_requests_proxy_dict(session_key=None):
    """
    Create proxy dictionary used in requests module.

    :return: Proxy dict
    """
    proxies = {}
    proxy_settings, proxy_enabled = get_proxy_config(session_key=session_key)

    # Create Proxy URL
    proxy_uri = create_uri(proxy_enabled, proxy_settings)
    if proxy_uri:
        proxies = {"http": proxy_uri, "https": proxy_uri}

    return proxies


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
        APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all(only_current_app=True)


def get_password(entities, name, field):
    """
    Give password.

    :param entities: dict which will have clear password
    :param name: name of modular input

    :return: password and certificate key password
    """
    password = ""
    for _, value in list(entities.items()):
        if value["username"].partition("`")[0] == str(name) and not value.get("clear_password", "`").startswith("`"):
            cred = {}
            try:
                cred = json.loads(value.get("clear_password", "{}"))
            except ValueError:
                continue
            password = cred.get(field, "")
            break
    return password


def get_account_data(session_key, entities, global_account):
    """
    Return Account information.

    :param session_key: Session Key used to call rest handlers
    :param entities: Entity Object
    :param global_account: Global Account Name
    """
    account_config = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF)
    account_dict = {}

    for stanza in account_config:
        if str(stanza) == global_account:
            account_dict["hostname"] = account_config.get(stanza).get("hostname")
            break

    account_dict["token"] = get_password(entities, global_account, "token")
    account_dict["token_v2"] = get_password(entities, global_account, "token_v2")
    return account_dict


def get_proxy_settings(proxy_config, session_key):
    """
    Give information of proxy if proxy is enabled.

    :return: dictionary having proxy information
    """
    proxy_settings = {}
    proxy_enabled = 0

    if proxy_config.get("proxy_enabled"):
        proxy_enabled = int(proxy_config.get("proxy_enabled"))
        if proxy_enabled:
            proxy_settings["proxy_port"] = proxy_config.get("proxy_port")
            proxy_settings["proxy_url"] = proxy_config.get("proxy_url")
            proxy_settings["proxy_type"] = proxy_config.get("proxy_type")
            try:
                proxy_settings["proxy_username"] = proxy_config.get("proxy_username")
                proxy_creds = get_clear_creds(session_key, NETSKOPE_SETTINGS_CONF, "proxy")
                proxy_settings["proxy_password"] = proxy_creds.get("proxy_password")
            except Exception:
                pass

    return proxy_settings, proxy_enabled


def send_notification(**kwargs):
    """Send the notification splunk UI."""
    uri = get_splunkd_uri()
    url: str = "{}/services/messages".format(uri)
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "Authorization": "Bearer {}".format(kwargs["session_key"]),
    }
    payload = {
        "name": "{}_{}".format(kwargs["input_name"], time.time()),
        "value": kwargs["message"],
        "severity": kwargs["severity"],
    }
    response = requests.post(url, data=payload, headers=headers, verify=INTERNAL_VERIFY_SSL)
    logger = kwargs.get("logger")
    if logger:
        if response.status_code == 201:
            logger.info("Successfully sent the notification.")
        else:
            logger.warn("Failed to send the notification.")


def check_input_config(**kwargs):
    """Check if CSV/JSON input stanza if present or not and send notification."""
    session_key = kwargs['session_key']
    current_input_name = kwargs.get('current_input_name')
    conf_file_stanzas = read_conf_file(session_key, "inputs")
    account_config = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF)

    for input_stanza in conf_file_stanzas:
        if kwargs.get('stanza_to_search') in input_stanza:
            if kwargs.get('is_event'):
                data_types = conf_file_stanzas[input_stanza].get("event_type").split("~")
            else:
                data_types = conf_file_stanzas[input_stanza].get("alert_type").split("~")
            global_account = conf_file_stanzas[input_stanza].get("global_account")
            tenant_name = account_config.get(global_account, {}).get("hostname")
            current_tenant_name = kwargs.get('current_account').get("hostname")

            matched_data_types = []
            if current_tenant_name == tenant_name:
                current_types = kwargs.get('current_types')
                if "All" in data_types:
                    matched_data_types = [event.capitalize() for event in data_types]
                elif "All" in current_types:
                    matched_data_types = [event.capitalize() for event in data_types]
                else:
                    for event in data_types:
                        if event in current_types:
                            matched_data_types.append(event.capitalize())
            if len(matched_data_types) != 0:
                warn_message = "Data duplication might be observed as multiple inputs '{}' and '{}' are "\
                    "found with same tenant name [{}] and type {}.".format(
                        input_stanza.split("://")[-1],
                        current_input_name,
                        tenant_name,
                        matched_data_types,
                    )
                send_notification(
                    message=warn_message,
                    input_name=input,
                    session_key=session_key,
                    severity="warn",
                )
                stanza_name = "netskope_{}_v2{}".format(
                    "events" if kwargs.get('is_event') else "alerts",
                    "_csv" if kwargs.get('is_csv_input') else ""
                )
                modinput_name = "{}://{}".format(stanza_name, current_input_name)
                conf = get_conf_file(session_key, file='inputs', app=const.APP_NAME)
                conf.update(modinput_name, {"is_notification_sent": 1})


def get_proxy_config(session_key=None):
    """
    Give information of proxy if proxy is enabled.

    :return: dictionary having proxy information
    """
    if session_key is None:
        session_key = GetSessionKey().session_key

    # Get proxy configurations
    proxy_configuration = read_conf_file(session_key, NETSKOPE_SETTINGS_CONF, stanza="proxy")

    return get_proxy_settings(proxy_configuration, session_key)


class DatetimeValidator(Validator):
    """To validate Start DateTime Field."""

    def __init__(self, label, *args, **kwargs):
        """Initialize the object."""
        max_days_back = kwargs.pop("max_days_back", None)
        self.max_days_back = max_days_back
        self.is_iterator_input = kwargs.pop("is_iterator_input", False)
        self.is_scripted_input = kwargs.pop("is_scripted_input", False)
        self.label = label
        super(DatetimeValidator, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """Validate start datetime field."""
        input_datetime = value

        if data.get("user_end_datetime") == "":
            data["user_end_datetime"] = get_default_datetime(last_days=0)

        if input_datetime and (isinstance(input_datetime, six.string_types) and input_datetime.strip() != ""):

            regex = r"""^[0-9]{4}-[0-9]{2}-[0-9]{2}[tT][0-9]{2}:[0-9]{2}:[0-9]{2}[zZ]$"""
            if not re.match(regex, input_datetime):
                self.put_msg("Invalid {0} Format. Please enter valid {0}.".format(self.label))
                return False
            input_datetime = input_datetime.upper()
            input_datetime = utility.DateTimeUtil.iso_to_epoch(input_datetime, UTC_FORMAT)
            current_datetime = utility.DateTimeUtil.get_current_epoch()

            if not self.is_iterator_input and input_datetime > current_datetime:
                self.put_msg("{0} should not exceed current datetime. Please enter valid {0}.".format(self.label))
                return False

            if self.is_iterator_input:
                start_datetime = utility.DateTimeUtil.iso_to_epoch(data.get("start_datetime"), UTC_FORMAT)
                if start_datetime > input_datetime:
                    self.put_msg(
                        "{0} should not be less than Start Datetime. Please enter valid {0}.".format(self.label)
                    )
                    return False
                else:
                    if self.is_scripted_input and input_datetime > current_datetime:
                        self.put_msg(
                            "{0} should not exceed current datetime. Please enter valid {0}.".format(self.label)
                        )
                        return False

        # As It is optional field, empty input_datetime will be allowed while validating.
        return True


class QueryValidator(Validator):
    """To Validate Query Syntax."""

    def validate_v1(self, hostname, token, proxies, query, data):
        """Validate query with API v1."""
        session = requests_retry_session()
        headers = {
            "content-type": "application/json",
        }
        endtime = int(time.time())
        starttime = endtime - 300
        payload = {
            "type": "application",
            "starttime": starttime,
            "endtime": endtime,
            "limit": 1,
            "query": query,
            "token": token,
        }
        url = make_netskope_url(endpoint=EVENTS_ENDPOINT, platform_url=hostname)

        if data.get("alert_type"):
            del payload["type"]
            url = make_netskope_url(endpoint=ALERTS_ENDPOINT, platform_url=hostname)

        response = session.get(
            url, headers=headers, data=json.dumps(payload), verify=VERIFY_SSL, proxies=proxies, timeout=REQUESTS_TIMEOUT
        )

        # Create a copy of response to return errors from API
        res = response
        response = response.json()

        # Check if API returned errors
        if response.get("status", "").strip() == "error":
            self.put_msg(
                "Error while validating query. For more details visit: "
                + " https://docs.netskope.com/en/netskope-help/admin-console/skope-it/"
                + "skope-it-query-language/skope-it-query-language-search-examples/"
            )
            return False

        res.raise_for_status()
        return True

    def validate_v2(self, hostname, token, proxies, query, data):
        """Validate query with API v2."""
        timeout = 120
        endtime = int(time.time())
        starttime = endtime - 300
        params = {"limit": 1, "skip": 0, "starttime": starttime, "endtime": endtime, "query": query}
        api_client = api.netskope_v2.client.NetskopeAPIClient(hostname, token, timeout, proxies, retries=0)
        if data.get("alert_type"):
            api_client.alert_events.get(params=params)
        else:
            api_client.page_events.get(params=params)
        return True

    def validate(self, value, data):
        """Validate Query parameter given by user."""
        query = data.get("query")
        if not query:
            return True

        hostname = None
        try:
            regex = r"^.{0,8192}$"
            if not re.match(regex, query):
                self.put_msg("Maximum allowed length of Query is 8192.")
                return False

            session_key = GetSessionKey().session_key

            # Fetch account information
            account_name = data.get("global_account")
            account_config = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF, stanza=account_name)
            account_stanza = get_clear_creds(session_key, NETSKOPE_ACCOUNT_CONF, account_name)
            hostname = account_config.get("hostname")
            token = account_stanza.get("token")
            token_v2 = account_stanza.get("token_v2")
            proxies = create_requests_proxy_dict()

            token_not_exists = (not token) or (isinstance(token, six.string_types) and len(token.strip()) <= 0)
            token_v2_not_exists = (not token_v2) or (
                isinstance(token_v2, six.string_types) and len(token_v2.strip()) <= 0
            )

            if token_not_exists and (not (data.get("alert_type") or data.get("event_type"))):
                self.put_msg(
                    (
                        "API Token V1 not found for selected Netskope Account."
                        "Please select Netskope Account with Token V1 configured."
                    )
                )
                return False

            if not token_not_exists:
                return self.validate_v1(hostname, token, proxies, query, data)
            elif not token_v2_not_exists:
                return self.validate_v2(hostname, token_v2, proxies, query, data)
            else:
                return True

        except (requests.exceptions.ProxyError, socks.ProxyError):
            self.put_msg("Invalid Proxy credentials. Please recheck your Proxy settings.")
            return False

        except RequestException as ex:
            msg = None
            if ex.response:
                msg = ex.response.text
            self.put_msg("Error occured while validating query parameter: {}.".format(msg))
            return False

        except Exception as ex:
            self.put_msg("Error occured while validating query parameter. {}.".format(ex))
            return False

        return True


class TokenV2Validator(Validator):
    """This class validates v2 token."""

    def __init__(self, *args, **kwargs):
        """Initialize the object."""
        self.is_csv_input = kwargs.pop("is_csv_input", False)
        super(TokenV2Validator, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """We define Custom validation here for verifying global_account field."""
        try:
            account_name = data.get("global_account")

            session_key = GetSessionKey().session_key
            is_event = True if data.get("event_type") else False
            endpoint_types = data.get("event_type").split("~") if is_event else data.get("alert_type").split("~")

            account_stanza = get_clear_creds(session_key, NETSKOPE_ACCOUNT_CONF, account_name)

            token_v2 = account_stanza.get("token_v2")
            account_config = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF, stanza=account_name)
            hostname = account_config.get("hostname")
            if not token_v2:
                self.put_msg('Please configure the "Netskope Account" which is configured with V2 token.')
                return False
            else:
                import utils_account
                validation, msg = utils_account.token_v2_validator_iterator(
                    hostname, token_v2, is_event, endpoint_types, self.is_csv_input
                )
                if not validation:
                    self.put_msg(msg)
                    return False
        except Exception as e:
            self.put_msg("Error occured while validating if V2 token exists. Error: {}".format(str(e)))
            return False
        return True


class TokenV1Validator(Validator):
    """This class validates v2 token."""

    def validate(self, value, data):
        """We define Custom validation here for verifying global_account field."""
        try:
            account_name = data.get("global_account")

            session_key = GetSessionKey().session_key

            account_stanza = get_clear_creds(session_key, NETSKOPE_ACCOUNT_CONF, account_name)
            token = account_stanza.get("token")
            if not token:
                self.put_msg('Please configure the "Netskope Account" which is configured with V1 token.')
                return False
        except Exception as e:
            self.put_msg("Error occured while validating if V1 token exists. Error: {}".format(str(e)))
            return False
        return True


class TokenV1andV2Validator(Validator):
    """This class validates v2 token."""

    def validate(self, value, data):
        """We define Custom validation here for verifying global_account field."""
        try:
            account_name = data.get("global_account")

            session_key = GetSessionKey().session_key
            account_stanza = get_clear_creds(session_key, NETSKOPE_ACCOUNT_CONF, account_name)
            token = account_stanza.get("token")
            token_v2 = account_stanza.get("token_v2")

            account_config = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF, stanza=account_name)
            hostname = account_config.get("hostname")
            if (not token) and (not token_v2):
                self.put_msg(
                    'Please configure the "Netskope Account" which is configured ' "with either V1 or V2 token."
                )
                return False
            if token_v2:
                import utils_account

                validation, msg = utils_account.token_v2_validator_waterfall(hostname, token_v2)
                if not validation:
                    self.put_msg(
                        'The V2 token configured in "Netskope Account" must have access to the '
                        "respective endpoints. Error: {}".format(msg)
                    )
                    return False
        except Exception as e:
            self.put_msg("Error occured while validating if V1 and v2 token exists. Error: {}".format(str(e)))
            return False
        return True


class IteratorTokenValidator(Validator):
    """This class validates v2 token for iterator endpoint."""

    def __init__(self, *args, **kwargs):
        """Initialize the object."""
        self.data_type = kwargs.pop("data_type", None)
        super(IteratorTokenValidator, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        """We define Custom validation here for verifying global_account field."""
        try:
            account_name = data.get("global_account")

            session_key = GetSessionKey().session_key

            account_stanza = get_clear_creds(session_key, NETSKOPE_ACCOUNT_CONF, account_name)

            token_v2 = account_stanza.get("token_v2")
            account_config = read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF, stanza=account_name)
            hostname = account_config.get("hostname")

            # Determine event type first
            if self.data_type is None:
                event_type = data.get("event_type")
            else:
                event_type = self.data_type
            iterator_name = account_name + "_" + event_type
            if not token_v2:
                self.put_msg('Please configure the "Netskope Account" which is configured with V2 token.')
                return False
            else:
                import utils_account
                validation, msg, netskope_iterator_name = utils_account.iterator_token_validator(
                    hostname, token_v2, [event_type], iterator_name
                )
                if netskope_iterator_name:
                    data["netskope_iterator_name"] = netskope_iterator_name
                if not validation:
                    self.put_msg(msg)
                    return False
        except Exception as e:
            self.put_msg("Error occured while validating if V2 token exists. Error: {}".format(str(e)))
            return False
        return True


def get_conf_file(
    session_key,
    file,
    app=const.APP_NAME,
    realm="__REST_CREDENTIAL__#{app_name}#configs/conf-inputs".format(app_name=const.APP_NAME)
):
    """Return the conf object of the file.

    :param session_key: Splunk session key.
    :param file: File name to be retrieved.
    :param app: TA Name.
    :param realm: APP realm.
    :return: Conf File Object
    """
    cfm = conf_manager.ConfManager(session_key, app, realm=realm)
    return cfm.get_conf(file)


def fields_include(data, fields):
    """Return dictionary containing only the specified fields from the input data.

    Parameters:
        data (dict): The input data as a dictionary.
        fields (str): A comma-separated string of field names.

    Returns:
        dict: A dictionary containing only the specified fields from the input data.
    """
    default_fields = ["timestamp", "_id"]
    fields_list = [field.strip() for field in fields.split(',') if len(field.strip())]
    [fields_list.insert(0, field) for field in default_fields if field not in fields_list]
    filtered_data = {}
    filtered_data = {field: data.get(field, "") for field in fields_list}
    return filtered_data


def fields_exclude(data, fields):
    """Return dictionary excluding the keys specified in the fields parameter.

    Parameters:
        data (dict): The input data as a dictionary.
        fields (str): A comma-separated string of field names to exclude.

    Returns:
        dict: A dictionary containing all the key-value pairs from the input data dictionary,
              except for the keys specified in the fields parameter.
    """
    fields_list = [field.strip() for field in fields.split(',') if len(field.strip())]
    filtered_data = data
    [filtered_data.pop(field) for field in fields_list if field in filtered_data]
    return filtered_data
