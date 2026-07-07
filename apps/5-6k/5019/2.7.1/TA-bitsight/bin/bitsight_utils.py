import import_declare_test  # noqa F401
import os
import sys
import json
import requests
import traceback
import socket
from base64 import b64encode
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from requests.compat import quote_plus

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.endpoint import (
    validator
)
from solnlib import utils as sutils
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer
import splunk.admin as admin
import splunk.entity as entity
import splunk.rest as rest
import splunk.clilib.cli_common
import splunklib.client as client
from splunklib.binding import HTTPError
from solnlib import conf_manager
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true
import splunk.version as v

from conf_helper import get_conf_file
import constants as const
from setup_logger import setup_logging
from bitsight_exceptions import BitsightException


logger = setup_logging("ta_bitsight_utils")
APP_NAME = 'TA-bitsight'
UNABLE_TO_REQUEST = 'Unable to request BitSight instance.'
UNRECOGNIZED_ERROR = 'Unrecognized error: {}'


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def resolve_host(hostname):
    """Resolve hostname to IPv4/IPv6 address."""
    try:
        # This returns a list of (family, type, proto, canonname, sockaddr) tuples
        infos = socket.getaddrinfo(hostname, None)

        # Filter for IPv4 and IPv6 addresses
        ipv4_addresses = [info for info in infos if info[0] == socket.AF_INET]
        ipv6_addresses = [info for info in infos if info[0] == socket.AF_INET6]

        # Prefer IPv4, but fallback to IPv6 if necessary
        if ipv4_addresses:
            address = ipv4_addresses[0][4][0]
        elif ipv6_addresses:
            address = ipv6_addresses[0][4][0]
        else:
            return None  # No suitable address found
        return address
    except socket.gaierror:
        return None


def create_service(sessionkey=None):
    """Create Service to communicate with splunk."""
    mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
    hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
    mgmt_port = mgmt_uri.split(":")[-1]

    # Resolve hostname to IPv4 address
    ip_address = resolve_host(hostname)
    if not ip_address:
        raise Exception("Failed to resolve Splunk management URI to an IP address.")

    if not sessionkey:
        sessionkey = GetSessionKey().session_key

    service = client.connect(host=ip_address, port=mgmt_port, token=sessionkey, app=APP_NAME)
    return service


class BitsightCompanyGuidManager(Validator):
    """Class to validate start date paramter."""

    def __init__(self, *args, **kwargs):
        """Init class object."""
        super(BitsightCompanyGuidManager, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)

    def validate(self, value, data):
        """Map the selected companies to their GUID."""
        bitsight_object = BitsightCompanyGuidMapper(GetSessionKey().session_key, "spm")
        company_guid_map = {'Map': []}
        try:
            selected_companies = data.get('company_tree_multiselect')
            response = bitsight_object.get_company_tree()
            if not response:
                msg = f"{UNABLE_TO_REQUEST} "\
                      "Please validate the provided BitSight and "\
                      "Proxy configurations or check the network connectivity."
                raise BitsightException(msg)
            if response.status_code != 200 and response.status_code != 201:
                raise BitsightException(
                    "Not able to get list of reporting feeds . Response Code : {}"
                    "- Response Error : {}".format(response.status_code, response.text)
                )
        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            self.put_msg(message)
            return False

        else:
            companies_list = (json.loads(response.content)).get('results')
            if 'All' in selected_companies:
                selected_companies = [x.get('name') for x in companies_list]
            for company in companies_list:
                comp_name = company['name']
                if comp_name in selected_companies:
                    company_guid_map['Map'].append({comp_name: company['guid']})
        try:
            bitsight_object.update_map(company_guid_map)
        except Exception as e:
            self.put_msg(e)
            logger.error(traceback.format_exc())
            return False
        return True


class BitsightBenchmarkingCompanyGuidManager(Validator):
    """Class to validate start date paramter."""

    def __init__(self, *args, **kwargs):
        """Init class object."""
        super(BitsightBenchmarkingCompanyGuidManager, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)

    def validate(self, value, data):
        """Map the selected companies to their GUID."""
        session_key_splunk = GetSessionKey().session_key
        bitsight_object = BitsightCompanyGuidMapper(session_key_splunk, "benchmarking")
        benchmarking_company_guid_map = {'Map': []}
        try:
            selected_companies = data.get('company_tree_multiselect')
            response = bitsight_object.get_company_tree()
            if not response:
                msg = f"{UNABLE_TO_REQUEST} "\
                      "Please validate the provided BitSight and "\
                      "Proxy configurations or check the network connectivity."
                raise BitsightException(msg)
            if response.status_code != 200 and response.status_code != 201:
                raise BitsightException(
                    "Not able to get list of reporting feeds . Response Code : {}"
                    "- Response Error : {}".format(response.status_code, response.text)
                )
        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            self.put_msg(message)
            return False

        else:
            companies_list = (json.loads(response.content)).get('results')
            if 'All' in selected_companies:
                selected_companies = [x.get('name') for x in companies_list]
            for company in companies_list:
                comp_name = company['name']
                if comp_name in selected_companies:
                    benchmarking_company_guid_map['Map'].append({comp_name: company['guid']})
        try:
            bitsight_object.update_map(benchmarking_company_guid_map)
        except Exception as e:
            self.put_msg(e)
            logger.error(traceback.format_exc())
            return False
        return True


class BitsightAccountValidator(Validator):
    """Class to validate Bitsight Account."""

    def __init__(self, *args, **kwargs):
        """Init class object."""
        super(BitsightAccountValidator, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)

    def validate(self, value, data):
        """Validate the Bitsight Account."""
        try:
            session_key_splunk = GetSessionKey().session_key
            splunk_rest_host_info = get_conf_file(
                file="ta_bitsight_settings",
                session_key=session_key_splunk,
                stanza="authentication"
            )
            if not splunk_rest_host_info.get('api_url', '') or not splunk_rest_host_info.get('bitsight_api_token', ''):
                msg = 'Configuration not found. Please configure BitSight API URL'
                msg += ' and BitSight Token before creating the input.'
                logger.error(msg)
                self.put_msg(msg)
                return False
            else:
                return True
        except Exception as e:
            msg = UNRECOGNIZED_ERROR.format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            return False


class BitsightDateValidator(Validator):
    """Class to validate start date paramter."""

    def __init__(self, *args, **kwargs):
        """Init class object."""
        super(BitsightDateValidator, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)

    def validate(self, value, data):
        """Validate the provided start date."""
        provided_date = data.get("start_date")
        if provided_date.strip() != '':
            try:
                parse(provided_date)
            except Exception:
                self.put_msg("Invalid date. Please check the entered date and try again.")
                return False
        try:
            edit_flag = data.get('edit_flag')
            if edit_flag == 'true':
                logger.info("Skipping date validation in edit mode.")
                return True
            todate = datetime.today()
            time_format = '%Y-%m-%d'
            todate_str = todate.strftime(time_format)
            earliest_date = (todate - relativedelta(days=400)).strftime(time_format)
            if provided_date.strip() == '':
                data['start_date'] = (todate - relativedelta(days=90)).strftime(time_format)
                return True
            elif provided_date < earliest_date:
                self.put_msg('Please enter a date not earlier than 400 days ago.')
                return False
            elif provided_date > todate_str:
                self.put_msg("Cannot fetch data from the future. Please enter an appropriate Start Date")
                return False
            else:
                return True
        except Exception as e:
            msg = UNRECOGNIZED_ERROR.format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            return False


class BitsightMacroManager(Validator):
    """Class provides methods for handling Macros."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(BitsightMacroManager, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)

    def update_macros(self, service, macro_name, indexes_string):
        """Update macro with the indexes provided."""
        service.post("properties/macros/{}".format(macro_name), definition=indexes_string)
        logger.debug("Macro: {} is updated Successfully.".format(macro_name))

    def validate(self, value, data):
        """Update the macros with the provided indexes."""
        try:
            service = create_service()
            indexes = data.get("custom_command_index")
            response_string = "index IN ({})".format(indexes)
            self.update_macros(service, "bitsight_wfh_index", response_string)
            return True

        except HTTPError:
            logger.error("Error while updating Macros: {}".format(traceback.format_exc()))
            self.put_msg("Error while updating Macros. Kindly check log file for more details.")
            return False
        except Exception as e:
            msg = UNRECOGNIZED_ERROR.format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False


def get_credentials(session_key):
    """Get credentials of Query API."""
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=APP_NAME,
            owner="nobody",
            sessionKey=session_key,
            count=-1,
            search=APP_NAME,
        )
    except Exception:
        raise BitsightException(
            "Bitsight Error: Could not get {} credentials from "
            "splunk.".format(APP_NAME)
        )
    api_key = None
    response_dict = {}
    for stanza, value in entities.items():
        try:
            password = value["clear_password"]
            password = json.loads(password)
            api_key = password["bitsight_api_token"]
            break
        except Exception as e:
            logger.error(e)
            continue
    _, content = rest.simpleRequest(
        "/servicesNS/nobody/{}/properties/ta_bitsight_settings/authentication".format(APP_NAME),
        sessionKey=session_key,
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )
    if api_key:
        response_dict = {"api_key": api_key}
    content = json.loads(content)
    for item in content["entry"]:
        if item["name"] == "api_key":
            continue
        response_dict[item["name"]] = item["content"]
    return response_dict


class BitsightCompanyGuidMapper(Validator):
    """Interface for KVstore."""

    def __init__(self, session_key, input_type):
        """Class init method."""
        self.input_type = input_type
        self.session_key = session_key
        self.kvstore_status = self._get_kvstore_status()
        self.service = create_service(session_key)
        if self.input_type == "spm":
            self.collection = self.service.kvstore['company_guid_map']
        elif self.input_type == "benchmarking":
            self.collection = self.service.kvstore['benchmarking_company_guid_map']

    def chunk(self, iterable, chunk_size):
        """Split iterable into chunks of given size."""
        for i in range(0, len(iterable), chunk_size):
            yield iterable[i:i + chunk_size]

    def get_company_tree(self):
        """Method to fetch company tree from Bitsight."""
        account_details = get_credentials(self.session_key)
        api_token = account_details.get("api_key")
        api_url_base = account_details.get('api_url')
        if not (api_url_base and api_token):
            raise TypeError
        response = None
        try:
            response = validate_instance_get_company_tree(api_url_base, api_token, input_type=self.input_type)
        except Exception as e:
            logger.error(e)
        return response

    def _groom(self, data):
        """Method to groom data for kvstore."""
        dict_array = []
        temp_dict = {}
        for each in data['Map']:
            for key, value in each.items():
                temp_dict['_key'] = value  # unique guid
                temp_dict['company_name'] = key  # company name
            dict_array.append(temp_dict)
            temp_dict = {}
        return dict_array

    def update_map(self, definition):
        """Method to update the company-guid map in the KVstore."""
        groomed_data = self._groom(definition)
        for chunked_items in self.chunk(groomed_data, const.MAX_DOCUMENTS_PER_BATCH_SAVE):
            self.collection.data.batch_save(*chunked_items)

    def _get_kvstore_status(self):
        """Get kv store status."""
        _, content = rest.simpleRequest("/services/kvstore/status",
                                        sessionKey=self.session_key,
                                        method="GET",
                                        getargs={"output_mode": "json"},
                                        raiseAllErrors=True)
        data = json.loads(content)["entry"]
        return data[0]["content"]["current"].get("status")

    def get_map(self, input_name=None):
        """Method to fetch map from KVstore."""
        if self.kvstore_status != "ready":
            return None
        else:
            cg_map = self.collection.data.query()
            return cg_map


def get_proxy_clear_password(session_key):
    """
    Get clear password from splunk passwords.conf.

    :return: str/None: proxy password if available else None.
    """
    logger.debug("Reading proxy password in clear text.")
    try:
        manager = CredentialManager(
            session_key,
            app=APP_NAME,
            realm="__REST_CREDENTIAL__#{0}#{1}".format(
                APP_NAME, "configs/conf-ta_bitsight_settings"
            ),
        )
    except CredentialNotExistException:
        return None
    else:
        logger.debug("Proxy password found. Returning.")
        return json.loads(manager.get_password("proxy")).get("proxy_password")


def get_proxy_configuration(session_key):
    """
    Get proxy configuration settings.

    :return: proxy configuration dict.
    """
    rest_endpoint = "/servicesNS/nobody/{}/TA_bitsight_settings/proxy".format(APP_NAME)

    _, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    logger.debug("Returning proxy details.")
    return json.loads(content)["entry"][0]["content"]


def get_proxy_uri(session_key, proxy_settings=None):
    """
    Generate proxy uri from provided configurations.

    :param session_key: Splunk Session Key
    :param proxy_settings: Proxy configuration dict. Defaults to None.
    :return: if proxy configuration available returns uri string else None.
    """
    logger.debug("Reading proxy configurations.")

    if not proxy_settings:
        proxy_settings = get_proxy_configuration(session_key)

    if is_true(proxy_settings.get("proxy_enabled", 0)):

        logger.debug("Proxy is enabled. Using proxy server.")
        if proxy_settings.get("proxy_username"):
            proxy_settings["proxy_password"] = get_proxy_clear_password(session_key)

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
        logger.info("Proxy is disabled or not configured. Skipping proxy.")
        return None


class ValidateBitsightInstance(Validator):
    """Validator for BitSight instance and BitSight API Token."""

    def validate(self, value, data):
        """
        Check if the given value is valid.

        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        logger.info("Initiating configuration validation.")
        logger.info("Reading proxy and user data.")

        bitsight_instance = data.get("api_url")
        bitsight_api_token = data.get("bitsight_api_token")
        logger.info("Validating the provided configurations.")
        try:
            resp = validate_instance_get_company_tree(bitsight_instance, bitsight_api_token)
            resp.raise_for_status()
            _ = resp.json()
            msg = "Configurations validated successfully."
            logger.info(msg)
            self.put_msg(msg)
            return True
        except Exception as e:
            if "resp" in locals() and resp.status_code == 401:
                msg = "Invalid API Token. Please enter the valid BitSight API Token."
            elif "resp" in locals() and resp.status_code == 404:
                msg = "Invalid BitSight API URL. Please validate the provided details."
            elif "resp" in locals() and resp.status_code == 500:
                msg = "Internal server error. Cannot verify BitSight instance."
            else:
                msg = f"{UNABLE_TO_REQUEST} "\
                      "Please validate the provided BitSight and "\
                      "Proxy configurations or check the network connectivity."
            logger.error(str(e))
            logger.error(msg)
            self.put_msg(msg)
            return False


def validate_instance_get_company_tree(api_url_base, api_token, input_type=None):
    """Method to validate BitSight instance and fetch company tree from Bitsight."""
    sessionkey = GetSessionKey().session_key
    proxy_settings = None
    try:
        proxy_settings = get_proxy_uri(sessionkey)
    except Exception:
        logger.error('An unexpected exception occurred: {}'.format(traceback.format_exc()))
        proxy_settings = None
    response = None
    session = requests.Session()
    if input_type == "spm" or input_type is None:
        api_url = api_url_base + 'ratings/v2/portfolio'
        params = {'scope': 'spm', 'limit': const.API_CALL_LIMIT}
    elif input_type == "benchmarking":
        api_url = api_url_base + 'ratings/v2/portfolio'
        params = {'limit': const.API_CALL_LIMIT}
    headers = {'Accept': 'application/json',
                'X-BITSIGHT-CONNECTOR-NAME-VERSION': 'BitSight Security Performance Management for Splunk Add-On {}'.format(get_app_version(sessionkey)),  # noqa
                'X-BITSIGHT-CALLING-PLATFORM-VERSION': 'Splunk-Enterprise {}'.format(v.__version__)}
    api = api_token + ':' + api_token
    user_and_pass = b64encode(api.encode()).decode("ascii")
    headers['Authorization'] = 'Basic %s' % user_and_pass
    response = session.get(api_url, headers=headers, params=params, proxies=proxy_settings)
    return response


def get_proxy_settings(session_key):
    """
    This function reads proxy settings if any, otherwise returns None.

    :param session_key: Session key for the particular modular input
    :return: A dictionary proxy having settings
    """
    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-ta_bitsight_settings".format(
                APP_NAME
            ),
        )
        ta_bitsight_settings_conf = settings_cfm.get_conf(
            "ta_bitsight_settings"
        ).get_all()

        proxy_settings = None
        proxy_stanza = {}
        for k, val in ta_bitsight_settings_conf["proxy"].items():
            proxy_stanza[k] = val
        is_proxy_enabled = proxy_stanza.get("proxy_enabled", 0)

        if not is_proxy_enabled or int(is_proxy_enabled) == 0:
            logger.debug("Proxy is disabled. Returning None")
            return proxy_settings
        proxy_type = proxy_stanza.get("proxy_type")
        proxy_port = proxy_stanza.get("proxy_port")
        proxy_url = proxy_stanza.get("proxy_url")
        proxy_username = proxy_stanza.get("proxy_username", "")
        proxy_password = proxy_stanza.get("proxy_password", "")

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
        logger.debug("Successfully fetched configured proxy details.")
        proxies = {
            "http": proxy_uri,
            "https": proxy_uri,
        }
        return proxies
    except Exception:
        logger.error(
            "Failed to fetch proxy details from configuration. {}".format(
                traceback.format_exc()
            )
        )
        sys.exit(1)


def bitsight_api_call(meta_configs, request_url, headers, req_params=None):
    """Method to get Bitsight data."""
    try:
        logger.debug("GET Request to URL = '{}' with Parameters = '{}'".format(request_url, req_params))

        # Get proxy settings
        proxy_info = get_proxy_settings(meta_configs['session_key'])

        response = requests.request(url=request_url, method="GET", params=req_params,
                                    data=None, verify=True, cert=None, headers=headers,
                                    cookies=None, timeout=300, proxies=proxy_info)

        return response.json()
    except Exception as e:
        logger.error(e)
        raise_webmessage(meta_configs, response=1)


def create_event(input_item, data):
    """Method to create event."""
    event = smi.Event(
        data=data,
        sourcetype=input_item.get('sourcetype'),
        source=input_item.get('sourcetype'),
        index=input_item.get('index'),
    )
    return event


def raise_webmessage(meta_configs, response):
    """Method to define error messages."""
    generic_msg = 'Bitsight Add-on Data input failed to connect with API, \
            Please check credentials in Add-on Configuration or connectivity issues'
    if response == 0:

        msg = "Login Failure,Bitsight Add-on Data input failed to connect with API,\
            Please check credentials in Add-on Configuration."

    elif response == 1:

        msg = "Bitsight Add-on Data input failed to connect with API due to connectivity issues'"

    elif response == 2:

        msg = "Please Add BitSight API-Token, Goto -->Configuration-->Add-onSettings"

    else:

        msg = 'Bitsight Add-on Data input failed to connect with API, \
            Please check credentials in Add-on Configuration or connectivity issues'

    try:
        uri = meta_configs['server_uri'] + '/services/messages/new'
        headers = {'Authorization': ''}
        headers['Authorization'] = 'Splunk ' + meta_configs['session_key']
        data = {'name': 'Custom message from Bitsight Add-on',
                'value': msg,
                'severity': 'warn'}
        requests.post(uri, headers=headers, data=data, verify=True)   # noqa
        sys.exit(generic_msg)

    except Exception as e:

        logger.error(e)
        sys.exit(generic_msg)


def get_app_version(session_key=None):
    """Return the version of TA specified in app.conf."""
    if not session_key:
        session_key = GetSessionKey().session_key
    app_conf = read_conf_file(session_key, "app", stanza="launcher")
    return app_conf.get("version")


def read_conf_file(session_key, file_name, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param file_name: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_manager_obj = conf_manager.ConfManager(
        session_key, APP_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, file_name)
    )
    conf_file = conf_manager_obj.get_conf(file_name)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()


def checkpoint_handler(logger, session_key, meta_configs):
    """
    This function creates as well as handles kv-store checkpoints for each input.

    :param logger: Logger object
    :param session_key: Session key for the particular modular input
    :return checkpoint_exists: True, if checkpoint exists, else False
    :return checkpoint_collection: Checkpoint directory
    """
    try:
        dscheme, dhost, dport = sutils.extract_http_scheme_host_port(meta_configs['server_uri'])
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            APP_NAME.replace("-", "_") + "_checkpointer", session_key, APP_NAME,
            scheme=dscheme, host=dhost, port=dport
        )
        return True, checkpoint_collection
    except Exception:
        logger.error("Error in Checkpoint handling: {}".format(traceback.format_exc()))
        return False, None
