"""
Modular Input Script

Copyright (C) 2012 Splunk, Inc.
All Rights Reserved

"""

# Standard library imports
import os
import os.path as op
import sys
import urllib
import json
import time
import xml.dom.minidom
import xml.sax.saxutils
import re
import requests


# Splunk imports
import splunk.rest as rest

# Local imports
import credentials as cred
import logger_manager as log
from auth_handlers import TokenAuth
from response_handlers import TruSTARResponseHandler

# Get path to splunk home
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

RESPONSE_HANDLER_INSTANCE = None

# Get current app name
myapp = __file__.split(os.sep)[-3]
APP_DIR = op.join(SPLUNK_HOME, "etc", "apps", myapp, "bin")
# Set up logger
logger = log.setup_logging('trustar_modinput')
# Set default error message
message = "Unknown error encountered. Please contact TruSTAR for further details."
proxy_port_match = r"^0*(?:6553[0-5]|655[0-2][0-9]|65[0-4][0-9]{2}|6[0-4][0-9]{3}|[1-5][0-9]{4}|[1-9][0-9]{1,3}|[0-9])$"
input_name = r"^[\d\w\-\_\s]+$"
# Set default waiting time
WAIT_TIME = 60000
# Set default timestamp range for first report and indicator poll call
REPORT_LOOKUP_DEFAULT_TIMESTAMP = 86400 * 1000      # 24 hours
INDICATOR_LOOKUP_DEFAULT_TIMESTAMP = 1209600 * 1000   # 14 days


class ModInputConfigApiKey(object):
    """ Handles ModInput related config, encryption/decryption
    """
    
    encrypted = ""

    def __init__(self, meta_configs):
        """ Initializes ModInputConfigApiKey object with the specified configurations.

        :param meta_configs: configuration parameters
        """
        
        self.meta_configs = meta_configs
        # Splunk session key
        self.session_key = meta_configs["session_key"]
        # Splunk server URI
        self.server_uri = meta_configs["server_uri"]
        
        self.mod_input_name = meta_configs.get("name", "").split("://")[-1]
        
        # Get URL of TruSTAR instance
        self.url = meta_configs["trustar_url"].strip('/')
        # Get API key
        self.auth_api_key = meta_configs.get("api_key")
        
        # Get API secret
        self.auth_api_secret = meta_configs.get("api_secret")

        # Get Enclave ID
        self.enclave_id = meta_configs.get("enclave_id")
        
        # Get Proxy Password
        self.https_proxy_password = meta_configs.get("https_proxy_password")
        # Get Proxy Username
        self.https_proxy_username = meta_configs.get("https_proxy_username")
        # Get stanza name
        self.stanza_name = meta_configs.get("name")
        # Initiate object of "CredentialManager" class
        self.cred_manager = cred.CredentialManager(self.session_key, self.server_uri)
        # Get app name
        self.app = myapp

        # Encrypt and mask credentials if already available
        if self.auth_api_key and self.auth_api_secret or self.https_proxy_password:
            if self.https_proxy_password:
                try:
                    self.encrypt_new_credentials('https_proxy_password', self.https_proxy_password)
                except Exception:
                    logger.exception("TruSTAR Error: Error while setting proxy password.")
            try:
                self.encrypt_new_credentials('key', self.auth_api_key)
                self.encrypt_new_credentials('secret', self.auth_api_secret)
            except Exception:
                logger.exception("TruSTAR Error: Error while setting API and secret key.")

            try:
                self.mask_input_credential()
            except Exception:
                logger.exception("TruSTAR Error: Error while masking API and secret key and password.")
        # Decrypt credentials, if are not available
        else:
            self.auth_api_key = self.decrypt_existing_credentials('key')
            self.auth_api_secret = self.decrypt_existing_credentials('secret')
            if self.https_proxy_username and self.https_proxy_username!="None":
                self.https_proxy_password = self.decrypt_existing_credentials('https_proxy_password')
            # Log error if api_key or api_secret is not available
            if self.auth_api_key is None or self.auth_api_secret is None:
                logger.error("TruSTAR Error: Error while getting API key or Secret key")
            if self.https_proxy_username and self.https_proxy_password is None:
                logger.error("TruSTAR Error: Error while getting proxy password.")

    def encrypt_new_credentials(self, key_type, key):
        """ Stores auth_password in passwords.conf

        :param key_type: type of key (key or secret)
        :param key: value of key
        """

        cred_manager = cred.CredentialManager(self.session_key, self.server_uri)
        stanza_name = self.mod_input_name+"_"+key_type

        if cred_manager.get_encrypted_password(self.app, stanza_name, self.app, log_exception=False) is None:
            cred_manager.create(self.app, stanza_name, key, self.app)
        else:
            cred_manager.update(self.app, stanza_name, key, self.app)

    def decrypt_existing_credentials(self, key_type):
        """ Retrieves auth_password from passwords.conf.

        :param key_type: type of key (key or secret)
        :return: clear password
        """

        cred_manager = cred.CredentialManager(self.session_key, self.server_uri)
        stanza_name = self.mod_input_name+"_"+key_type
        
        return cred_manager.get_clear_password(self.app, stanza_name, self.app)

    def mask_input_credential(self):
        """ Masks auth_password in inputs.conf.
        """
        argsValues={}
        if not self.https_proxy_password:
            argsValues={"api_key": self.encrypted, "api_secret": self.encrypted}
        else:
            argsValues={"api_key": self.encrypted, "api_secret": self.encrypted, "https_proxy_password": self.encrypted}
        
        stanza_name = self.mod_input_name

        # Prepare URL to make call
        path = self.server_uri + "/services/data/inputs/" + self.stanza_name.split("://")[0] + "/" +\
            urllib.quote(stanza_name, safe="")

        try:
            # Make REST call            
            rsp, content = rest.simpleRequest(path, method='GET', sessionKey=self.session_key, raiseAllErrors=True)
        except Exception as exe:
            logger.error("TruSTAR Error: Error while getting content : %s " % str(exe))
        # Parse data
        data = rest.format.parseFeedDocument(content)
        content = data[0].toPrimitive()
        # Get app name
        app_name = content['eai:acl']['app']
        # Prepare URL to make call
        path = self.server_uri + "/servicesNS/nobody/" + app_name + "/properties/inputs/" + \
            urllib.quote(self.stanza_name, safe="")
        
        # Make REST call to POST required data
        
        try:
            rest.simpleRequest(path, method='POST', sessionKey=self.session_key,
                           postargs=argsValues, raiseAllErrors=True)
        except Exception as exe:
            logger.error("TruSTAR Error: Error while updating the call : %s " % str(exe))


SCHEME = """<scheme>
    <title>TruSTAR Configuration</title>
    <description>REST API input for polling data from TruSTAR endpoints</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>
            <arg name="name">
                <title>Rest Input Name</title>
                <description>Rest Input name can only contain Letters, Number, Space , '-' and '_'.</description>
                <validation>
                    validate(match(name, '^[\d\w\s\_\-]+$'), "Rest Input name can only contain Letters, Number, Space , '-' and '_'.")
                </validation>
            </arg>
            <arg name="trustar_url">
                <title>URL To Connect</title>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
                <validation>
                    validate(match(trustar_url, '^(https://)\S+'), "URL: TruSTAR URL must begin with 'https://'")
                </validation>
            </arg>
            <arg name="api_key">
                <title>API Authentication Key</title>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="api_secret">
                <title>API Secret</title>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="start_time_to_fetch_reports">
                <title>Date (UTC in "YYYY-MM-DD hh:mm:ss" format)</title>
                <description>Date since when you want to fetch reports and indicators from TruSTAR during first polling. Default max will be 24 hours ago for reports and default 14 days ago maximum for indicators.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="cert_path">
                <title>SSL Certificate Path</title>
                <description>Path for the custom certificate.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
                <validation>
                    validate(match(cert_path, '^[\s\S]{0,2000}$'), "Certificate Path: Certificate Path must not exceed 2000 characters")
                </validation>
            </arg>
            <arg name="https_proxy">
                <title>HTTPS Proxy Address</title>
                <description>Use proxy address starting with (http:// or https://) to communication with the TruSTAR station, e.g. http://10.10.1.10 or https://10.0.1.10</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="https_proxy_port">
                <title>HTTPS Proxy Port</title>
                <description>Proxy port to use for communication with the TruSTAR station, e.g. 3128</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="https_proxy_username">
                <title>HTTPS Proxy Username</title>
                <description>Username to use for communication with the TruSTAR station.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="https_proxy_password">
                <title>HTTPS Proxy Password</title>
                <description>Password to use for communication with the TruSTAR station.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="enable_data_collection">
                <title>Enable Data Collection</title>
                <description>To enable data collection check the box.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="enclave_id">
                <title>Enclave IDs</title>
                <description>Enter Enclave ID's to pull data from. If multiple ID's, use comma separated values.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="tags">
                <title>Tags</title>
                <description>Enter tags to filter by indicators list. If multiple tags, use comma separated values.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


def get_notification_message(message, session_key):
    """
    Post notification on splunk
    :param message: error message
    :param session_key: current session key
    """
    postargs = {
        'severity': 'error', 
        'name': myapp,
        'value': myapp + ' modular input validation failed: ' + message
    }
    try:
        rest.simpleRequest('/services/messages', session_key, postargs=postargs)
    except:
        logger.exception("Failed to give notification message")


def print_error(message, session_key):
    """
    Print error
    :param message: error message
    :param session_key: current session key
    """
    get_notification_message(message, session_key)
    print ("<error><message>%s</message></error>" % xml.sax.saxutils.escape(message))
    logger.error(message)
    sys.exit(1)


def check_previous_input(config_params):
    """
    Check if input already exist
    :params config_params: configuration parameters
    """
    session_key = config_params.get('session_key')
    stanza = config_params.get('name')
    try:
        # Make REST call
        _, content = rest.simpleRequest("/services/properties/inputs?output_mode=json", method='GET', sessionKey=session_key, raiseAllErrors=True)
    except Exception as exe:
        print_error("TruSTAR Error: Error while getting previous input content : %s " % str(exe), session_key)
    data = json.loads(content)['entry']
    for result in data:
        input_name = result.get('name')
        if input_name and ("trustar://" in input_name) and stanza!=input_name:
            print_error("TruSTAR Error: Multiple inputs are not allowed. Input with name '%s' already exist." % str(result['name']).split('://')[1], session_key)


def create_proxy_uri(session_key, proxy_server, proxy_port, proxy_server_username, proxy_server_password):
    """ 
    Create proxy URI to use in API call
    :param session_key: current session key
    :param proxy_server: proxy server
    :param proxy_port: proxy port
    :param proxy_server_username: proxy username
    :param proxy_server_password: proxy password
    :return http://10.10.1.10:3128 or https://user:pass@10.10.1.10:3128 proxy
    """
    proxies = None
    if not (proxy_server or proxy_port):
        return proxies
    
    if not (proxy_server.startswith("http://") or proxy_server.startswith("https://")):
        print_error("TruSTAR Error: Proxy server must start with protocol (http:// or https://).", session_key)
    if not proxy_port or not re.search(proxy_port_match, proxy_port):
        print_error("TruSTAR Error: Proxy port should not be empty and port number should not exceed 65535.", session_key)
    try:
        if proxy_server_username:
            if not proxy_server_password:
                print_error("TruSTAR Error: Please Provide with proxy password.", session_key)
                
            try:
                protocol = proxy_server.split("://")[0]
                server = proxy_server.split("://")[1]
                proxies = protocol+"://"+proxy_server_username+":"+proxy_server_password+"@"+server+":"+proxy_port
            except Exception as exe:
                logger.error("TruSTAR Error: Error while creating proxy path using credentials: %s " % str(exe))     
        else:
            proxies = proxy_server+":"+proxy_port
    except Exception as exe:
        logger.error("TruSTAR Error: Error while creating proxy: %s" % str(exe))
    return proxies


def validate_enclave_ids(enclave_ids, basic_args):
    """
    Validatie entered enclaved ids
    :param enclve_ids: enclave ids given by user
    :param basic_args: basic details
    """
    session_key = basic_args.get("session_key")
    if enclave_ids:
        enclaves = get_enclaves(basic_args, validation=True)
        enclave_ids = enclave_ids.split(',')
        not_found = []
        not_read = []
        msg = ""
        for enclave in enclave_ids:
            enclave = enclave.strip()
            if not enclaves.get(enclave):
                not_found.append(enclave)
            elif enclaves.get(enclave) and not enclaves[enclave].get('read'):
                not_read.append(enclave)
        if not_found:
            msg = "Enclave id(s) "+ json.dumps(not_found) + " not found."
        if not_read:
            msg += " You do not have READ permission on "+ json.dumps(not_read) + " enclave id(s)."
        if msg:
            print_error(msg, session_key)


def validate_certificate(cert_path, session_key):
    """
    Validation certificate information
    :param cert_path: path of certificate
    :param session_key: current session key
    :return verify parameter
    """
    verify = True
    # Strip out spaces from certificate path if path is not empty string
    if cert_path and cert_path.strip() != "":
        if not re.match("^[\s\S]{,2000}$", cert_path):
            logger.error("TruSTAR Error: Certificate Path must not exceed 2000 characters")
            print_error("Certificate Path must not exceed 2000 characters.", session_key)

        if not os.path.exists(cert_path):
            logger.error("TruSTAR Error: Provided certificate path doesn't exist")
            print_error("Provided certificate path doesn't exist.", session_key)       

        # Override verify with the provided certificate path
        verify = cert_path.strip()
    return verify


def do_validate():
    """ 
    To validate inputs in mod-input
    """

    # Get configuration parameters
    try:
        config_params = get_validation_config()
    except Exception as exe:
        logger.error("TruSTAR Error: Failed to obtain configurations of modular input %s %s" % (exe.args, str(exe)))
        sys.exit(2)

    if not config_params:
        logger.error("TruSTAR Error: No configuration parameters found.")
        sys.exit(2)

    # Check if input already exist or not
    check_previous_input(config_params)
    # Get URL of TruSTAR instance
    url = config_params.get("trustar_url").strip('/')
    # Get API key
    api_key = config_params.get("api_key")
    # Get API secret
    secret_key = config_params.get("api_secret")
    # Get certificate path
    cert_path = config_params.get('cert_path')
    # Get date since when to fetch reports from TruSTAR during first poll
    start_time = config_params.get("start_time_to_fetch_reports")
    # Get proxy server address
    proxy_server = config_params.get('https_proxy')
    # Get proxy server port
    proxy_port = config_params.get('https_proxy_port')
    # Get proxy server username
    proxy_server_username = config_params.get('https_proxy_username')
    # Get proxy server password
    proxy_server_password = config_params.get('https_proxy_password')
    # Get stanza name
    stanza = config_params.get('name').split("//")[-1]
    # Get enclave ids
    enclave_ids = config_params.get('enclave_id', None)
    # Get session key
    session_key = config_params.get('session_key')
    
    if not stanza or not re.search(input_name, stanza):
        print_error("TruSTAR Error: Rest input name can only contain Number, Letters, Spaces, '-' and '_'.", session_key)

    proxies = create_proxy_uri(session_key, proxy_server, proxy_port, proxy_server_username, proxy_server_password)

    # Display error in case any sourcetype is provided
    sourcetype = config_params.get("sourcetype")
    if sourcetype:
        logger.error("TruSTAR Error: Source type must be \"Automatic\"."
                     " By default the events would be classified and assigned to"
                     " trustar:reports sourcetype")

        print_error("Source type must be \"Automatic\".By default the events would be classified and assigned to trustar:reports sourcetype.", session_key)

    # Validate "start_time_to_fetch_reports" if present
    if start_time:
        try:
            time.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except:
            logger.error("TruSTAR Error: Date should be in YYYY-DD-MM hh:mm:ss format, but got {}".format(start_time))
            print_error("TruSTAR Error: Date should be in YYYY-DD-MM hh:mm:ss format.", session_key)

    verify = validate_certificate(cert_path, session_key)

    custom_auth_handler_args = {"url": url}
    
    # Update arguments if proxy settings are available
    if proxies:
        custom_auth_handler_args.update({"proxies": proxies})

    # Initialize object of "TokenAuth" class
    custom_auth_handler_instance = TokenAuth(**custom_auth_handler_args)

    # Get access token
    access_token = custom_auth_handler_instance.get_access_token(api_key, secret_key, verify)

    # Provide error and exit if access_token is not available
    if not access_token:
        print_error("Authentication Failed ! Please verify URL, API key and Secret Key of TruSTAR to Connect.", session_key)

    basic_args = {
        "auth": custom_auth_handler_instance,
        "config": config_params,
        "access_token": access_token.get('access_token'),
        "url": url,
        "verify": verify,
        "proxies": proxies,
        "session_key": session_key
    }
    validate_enclave_ids(enclave_ids, basic_args)


def set_token(checkpoint_dir, stanza_name, type, token_timestamp):
    """ 
    Set timestamp in checkpoint file. This would be used in next request.
    :param checkpoint_dir: directory where checkpoint file is stored
    :param stanza_name: modular input stanza name which is to be used as file name
    :param type: key of token_timestamp
    :param token_timestamp: timestamp to be saved
    """
    timestamp = get_token(checkpoint_dir, stanza_name)
    if not timestamp:
        timestamp["token_timestamp"] = {}
    token_path = os.path.join(checkpoint_dir, urllib.quote(stanza_name, safe=""))
    try:
        with open(token_path, 'w+') as state_file:
            timestamp['token_timestamp'][type] = token_timestamp
            state_file.write(json.dumps(timestamp))
    except IOError as ioe:
        logger.error("TruSTAR Error: Error while setting token: %s" % str(ioe))
        exit(-1)


def get_token(checkpoint_dir, stanza_name):
    """ 
    Obtain any saved timestamp from checkpoint file.
    :param checkpoint_dir: directory where checkpoint file is stored
    :param stanza_name: directory where checkpoint file is stored which is to be used as file name
    :return: timestamp
    """

    token_path = os.path.join(checkpoint_dir, urllib.quote(stanza_name, safe=""))
    token_timestamp = {}
    if os.path.isfile(token_path):
        try:
            with open(token_path, 'r') as state_file:
                json_data = state_file.read()
                token_timestamp = json.loads(json_data)
        except IOError as ioe:
            logger.error("TruSTAR Error: Error while getting token, hence considering default value for "
                         "timestamp: %s" % str(ioe))

    return token_timestamp


def do_run(config):
    """ 
    Function that collects data and indexes it.
    :param config: configuration of mod-input
    """
    # Get base URL
    url = config.get('url')
    # Get modular input name
    stanza_name = config.get('name')
    # Get date since when to fetch reports from TruSTAR during first poll
    start_time = config.get("start_time_to_fetch_reports")
    # Get certificate path
    cert_path = config.get('cert_path')
    # Get proxy server settings
    proxy_server = config.get('https_proxy')
    # Get proxy server port
    proxy_port = config.get('https_proxy_port')
    # Get proxy server username
    proxy_server_username = config.get('https_proxy_username')
    # Get proxy server password
    proxy_server_password = config.get('https_proxy_password')
    session_key = config.get('session_key')
    # Get enclave ids
    enclave_ids = config.get("enclave_id", None)
    # Get tags
    tags = config.get("tags", [])

    if start_time:
        try:
            start_time = start_time.strip()
            start_time = time.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except:
            logger.error("TruSTAR Error: Date should be in YYYY-DD-MM hh:mm:ss format,"
                            " but got {}".format(start_time))
            return

    proxies = create_proxy_uri(session_key, proxy_server, proxy_port, proxy_server_username, proxy_server_password)

    # Get checkpoint directory path
    checkpoint_directory = config.get('checkpoint_dir')
    verify = True
    # Strip out spaces from certificate path if path is not empty string
    if cert_path and cert_path.strip() != "":
        verify = cert_path.strip()

    global RESPONSE_HANDLER_INSTANCE
    # Initialize object of "TruSTARResponseHandler" class
    RESPONSE_HANDLER_INSTANCE = TruSTARResponseHandler()

    custom_auth_handler_args = {"url": url}
    # Update arguments if proxy settings are available
    if proxies:
        custom_auth_handler_args.update({"proxies": proxies})

    # Initialize object of "TokenAuth" class
    auth = TokenAuth(**custom_auth_handler_args)

    try:
        if auth:
            # Get access_token using API key and API secret
            response = auth.get_access_token(config.get("api_key"), config.get("api_secret"), verify)
            access_token = response.get("access_token")
            if access_token:
                # Get reports
                data_retrieval_endpoint = url + '/api/1.3/reports'

                # Dictionary to store indicators fetched with reports
                report_indicators = {}

                basic_args = {
                    "auth": auth,
                    "config": config,
                    "access_token": access_token,
                    "data_retrieval_endpoint": data_retrieval_endpoint,
                    "verify": verify,
                    "proxies": proxies,
                    "url": url,
                    "stanza_name": stanza_name,
                    "checkpoint_directory": checkpoint_directory
                }
                try:
                    # For /reports API call
                    # Get current time in epoch seconds
                    current_timestamp = int(time.time() * 1000)
                    current_remaining = False
                    # Obtain saved timestamp from checkpoint file if present
                    token_timestamp = get_token(checkpoint_directory, stanza_name.split("://")[1])
                    # Prepare request parameters
                    if token_timestamp:
                        if token_timestamp['token_timestamp'].get("to",None):
                            time_dict = {'from': token_timestamp['token_timestamp']["from"], 'to': token_timestamp['token_timestamp']["to"]}
                            current_remaining = True
                        else:
                            time_dict = {'from': token_timestamp['token_timestamp']["current"], 'to': current_timestamp}
                    # First poll
                    else:
                        time_dict, from_time = set_time_for_first_poll(start_time,
                                                                       current_timestamp,
                                                                       REPORT_LOOKUP_DEFAULT_TIMESTAMP)
                    total_reports = 0
                    if not token_timestamp or not token_timestamp['token_timestamp'].get("to", None):
                        set_token(checkpoint_directory, stanza_name.split("://")[1], "current", current_timestamp)
                        set_token(checkpoint_directory, stanza_name.split("://")[1], "from", time_dict.get("from"))
                        set_token(checkpoint_directory, stanza_name.split("://")[1], "to", time_dict.get("to"))

                    enclaves = get_enclaves(basic_args)
                    basic_args["enclaves"] = enclaves
                    while time_dict:
                        new_time_dict = {'to': time_dict['to'], 'from': time_dict['from']}
                        # Update param dict with enclave ids
                        if enclave_ids:
                            new_time_dict.update({'enclaveIds': enclave_ids})
                        logger.debug("Request parameters: " + str(new_time_dict))

                        while new_time_dict:
                            # If timeframe is greater than 14 days, convert it to 14 days timeframe
                            if new_time_dict.get('to') - new_time_dict.get('from') > REPORT_LOOKUP_DEFAULT_TIMESTAMP:
                                new_time_dict['from'] = new_time_dict['to'] - REPORT_LOOKUP_DEFAULT_TIMESTAMP
                            # Make REST call for data retrieval
                            data = call_endpoint(basic_args["access_token"], data_retrieval_endpoint, verify, proxies, params=new_time_dict)
                            success, data = handle_error(data, basic_args, params=new_time_dict)
                            if not success:
                                if data.get('other_error'):
                                    raise Exception(str(data["error"]))
                                return

                            has_next = data.get("hasNext")
                            reports_list = data.get("items",[])
                            # Pass reports list for further processing if available
                            update_and_index_report(reports_list, basic_args)
                            total_reports += len(reports_list)

                            # Continue fetching reports if total reports in response are greater than 25
                            while has_next and len(reports_list)>0:
                                # Get updated time of last report
                                earliest_updated_time = int(reports_list[len(reports_list)-1].get("updated",0))
                                # Prepare request parameters
                                set_token(checkpoint_directory, stanza_name.split("://")[1], "to", earliest_updated_time)
                                new_time_dict['to'] = earliest_updated_time
                                
                                logger.debug("Request parameters: " + str(new_time_dict))
                                # Make REST call for data retrieval
                                data = call_endpoint(basic_args["access_token"], data_retrieval_endpoint, verify, proxies, params=new_time_dict)
                                success, data = handle_error(data, basic_args, params=new_time_dict)
                                if not success:
                                    if data.get('other_error'):
                                        raise Exception(str(data["error"]))
                                    return

                                has_next = data.get("hasNext")
                                reports_list = data.get("items",[])
                                update_and_index_report(reports_list, basic_args)
                                total_reports += len(reports_list)

                            set_token(checkpoint_directory, stanza_name.split("://")[1], "to", new_time_dict['from'])
                            new_time_dict['to'] = new_time_dict['from']
                            new_time_dict['from'] = time_dict['from']
                            if new_time_dict['from'] >= new_time_dict['to']:
                                new_time_dict = {}
                        set_token(checkpoint_directory, stanza_name.split("://")[1], "to", 0)
                        set_token(checkpoint_directory, stanza_name.split("://")[1], "from", 0)
                        if current_remaining:
                            time_dict = {'from': token_timestamp['token_timestamp'].get("current"), 'to': current_timestamp}
                            current_remaining = False
                        else:
                            time_dict = {}
                    set_token(checkpoint_directory, stanza_name.split("://")[1], "current", current_timestamp)
                    logger.debug("Total Reports: " + str(total_reports))
                # Handle any exception encountered
                except Exception as exe:
                    logger.error("TruSTAR Error: Error in calling endpoint %s , %s, %s" % (exe.args, str(exe), data_retrieval_endpoint))

                # Get indicators
                data_retrieval_endpoint = url + "/api/1.3/indicators"
                basic_args["data_retrieval_endpoint"] = data_retrieval_endpoint
                try:
                    # For /indicators API call
                    # Get current time in epoch seconds
                    current_timestamp = int(time.time() * 1000)

                    # Obtain saved timestamp from checkpoint file if present
                    token_file = stanza_name.split("://")[1] + "_indicator"
                    token_timestamp = get_token(checkpoint_directory, token_file)
                    # Prepare request parameters
                    if token_timestamp:
                        params = {"from": token_timestamp["token_timestamp"]["current"], "to": current_timestamp}
                    # First poll
                    else:
                        params, from_time = set_time_for_first_poll(start_time,
                                                                    current_timestamp,
                                                                    INDICATOR_LOOKUP_DEFAULT_TIMESTAMP)
                        set_token(checkpoint_directory, token_file, "current", from_time)

                    total_indicators = 0
                    params["pageNumber"] = 0
                    params["pageSize"] = 1000
                    # Update param dict with enclave ids
                    if enclave_ids:
                        params["enclaveIds"] = enclave_ids

                    # Update param dict with tag ids
                    update_tags(tags, enclave_ids, params, basic_args)

                    logger.debug("Request parameters: " + str(params))
                    # Make REST call for data retrieval

                    data = call_endpoint(basic_args["access_token"], data_retrieval_endpoint, verify, proxies, params=params)
                    success, data = handle_error(data, basic_args, params=params)
                    if not success:
                        if data.get('other_error'):
                            raise Exception(str(data["error"]))
                        return
                    
                    indicator_list = data.get("items", [])
                    has_next = data.get("hasNext")
                    page_number = data.get("pageNumber")
                    update_and_index_indicators(indicator_list, basic_args)
                    total_indicators += len(indicator_list)

                    while has_next and len(indicator_list)>0:
                        params["pageNumber"] = page_number + 1
                        logger.debug("Request parameters for getting indicators: " + str(params))
                        data = call_endpoint(basic_args["access_token"], data_retrieval_endpoint, verify, proxies, params=params)
                        success, data = handle_error(data, basic_args, params=params)
                        if not success:
                            if data.get('other_error'):
                                raise Exception(str(data["error"]))
                            return

                        indicator_list = data.get("items", [])
                        has_next = data.get("hasNext")
                        page_number = data.get("pageNumber")
                        update_and_index_indicators(indicator_list, basic_args)
                        total_indicators += len(indicator_list)

                    set_token(checkpoint_directory, token_file, "current", current_timestamp)
                    logger.debug("Total Indicators: " + str(total_indicators))
                # Handle any exception encountered
                except Exception as e:
                    logger.error("TruSTAR Error: Error in calling endpoint %s , %s, %s" % (
                        e.args, str(e), data_retrieval_endpoint))

    # Handle any exception encountered
    except Exception as exe:
        logger.error("TruSTAR Error: Looks like an error: %s" % str(exe))
        sys.exit(2)


def set_time_for_first_poll(start_time, current_timestamp, default_timestamp):
    """
    Set timestamp for first invocation of input
    Only use given start_time if within the last 14 days

    :param start_time: start time given by user
    :param current_timestamp: current time
    :return dictionary with time information and from time
    """
    # Default max is 14 days from current timestamp
    from_time = int(current_timestamp - default_timestamp)

    if start_time:
        start_time_timestamp = int(time.mktime(start_time) * 1000)
        if start_time_timestamp > from_time:
            from_time = start_time_timestamp

    time_dict = {'from': from_time, 'to': current_timestamp}
    logger.debug("First poll time range: %s" % str(time_dict))
    return time_dict, from_time


def validate_tags(tag_ids, tags, tag_list):
    """
    Validatie entered tag names
    :param tag_ids: tag ids found
    :param tags: tag names given by user
    :param tag_list: list of all tags
    """
    if len(tag_ids) != len(tags):
        tag_name = [tag.get('name') for tag in tag_list]
        not_found_tag = []
        for tag in tags:
            if not tag in tag_name:
                not_found_tag.append(tag)
        if not_found_tag:
            logger.error("TruSTAR Error: Tag(s)" + str(not_found_tag) + " not found. Hence, skipping these tags.")


def update_tags(tags, enclave_ids, params, basic_args):
    """
    Update parameter with tags information
    :param tags: tag ids
    :param enclave_ids: list of enclaves in response
    :param params: parameters to pass in request
    :param basic_args: basic details
    """
    if tags:
        tag_list = get_indicator_tags(enclave_ids, basic_args)
        if not isinstance(tag_list, list):
            logger.error("TruSTAR Error: Failed to get tag ids of tags")
            raise Exception("Failed to get tag ids of tags")

        tags = tags.strip().split(',')
        tags = [tag.strip() for tag in tags]
        tag_ids = []
        for tag in tag_list:
            if tag.get("name") in tags:
                tag_ids.append(tag.get("guid"))

        validate_tags(tag_ids, tags, tag_list)
        if tag_ids:
            params["tagIds"] = ",".join(tag_ids)


def update_and_index_report(reports_list, basic_args):
    """
    Get the required details of reports (i.e. indicators, indicator count, enclaves) and index it
    :param reports_list: list of reports in response
    :param basic_args: basic details
    """
    data_retrieval_endpoint, enclaves, url, checkpoint_directory, stanza_name = basic_args.get('data_retrieval_endpoint'), \
                                                                                basic_args.get('enclaves'), \
                                                                                basic_args.get('url'), \
                                                                                basic_args.get('checkpoint_directory'), \
                                                                                basic_args.get('stanza_name')
    for report in reports_list:
        indicator_data = get_indicators(report.get('id', 0), basic_args)
        if not isinstance(indicator_data, list):
            logger.error("TruSTAR Error: Failed to get indicators for Report ID: " + str(report.get('id', 0)))
            raise Exception("Failed to get indicators for Report ID: " + str(report.get('id', 0)))
        report['queryDate'] = int(time.time() * 1000)
        enclave_ids = report.pop('enclaveIds', [])
        enclave_list= get_enclave_list(enclaves, enclave_ids)

        report['indicators'] = indicator_data
        report['indicatorsCount'] = len(indicator_data)
        report['enclaves'] = enclave_list

        handle_output(report, data_retrieval_endpoint, url, stanza_name)
        report_updated_time = int(report.get("updated",0))
        set_token(checkpoint_directory, stanza_name.split("://")[1], "to", report_updated_time)


def update_and_index_indicators(indicator_list, basic_args):
    """
    Get the required details of indicators (i.e enclaves) and index it
    :param indicator_list: list of indicators in response
    :param basic_args: basic details
    """
    data_retrieval_endpoint, enclaves, url, stanza_name  = basic_args.get('data_retrieval_endpoint'), basic_args.get('enclaves'), basic_args.get('url'), basic_args.get('stanza_name')
    indicator_set = [i for n, i in enumerate(indicator_list) if i not in indicator_list[n + 1:]]
    indicator_list_with_enclaves = get_indicator_enclaves(indicator_set, basic_args)
    if not isinstance(indicator_list, list):
        logger.error("TruSTAR Error: Failed to get metadata of indicators")
        raise Exception("Failed to get metadata of indicators")
    for indicator in indicator_list_with_enclaves:
        enclave_ids = indicator.pop('enclaveIds', [])
        enclave_list = get_enclave_list(enclaves, enclave_ids)
        indicator['enclaves'] = enclave_list
        handle_output(indicator, data_retrieval_endpoint, url, stanza_name)


def get_enclave_list(enclaves, enclave_ids):
    """
    Given list of enclave IDs, gets list of enclave objects
    :param enclaves: total available enclaves
    :param enclave_ids: enclaves in response
    :return list of enclaves
    """
    enclave_list = []
    if enclaves:
        for id in enclave_ids:
            enclave = enclaves.get(id)
            if enclave:
                enclave.pop("timestamp", None)
                enclave_list.append(enclave)
    return enclave_list


def handle_error(data, basic_args, params):
    """
    Handles error scenarios
    :param data: response of request
    :param basic_args: basic details
    :param params: parameters to pass in request
    :retrun response of request
    """
    auth, config, access_token, data_retrieval_endpoint, verify, proxies = basic_args.get('auth'), basic_args.get('config'), basic_args.get('access_token'), basic_args.get('data_retrieval_endpoint'), basic_args.get('verify'), basic_args.get('proxies')
    # Retry once if token expires
    if isinstance(data, dict) and data.get("error") == "Authentication error":
        # Get access token in case it is expired
        logger.debug("Access token expired")
        response = auth.get_access_token(config.get("api_key"), config.get("api_secret"), verify)
        access_token = response.get("access_token")
        if not access_token:
            return 0, data
        basic_args["access_token"] = access_token
        # Call endpoint with new access_token
        data = call_endpoint(basic_args["access_token"], data_retrieval_endpoint, verify, proxies, params=params)

        if isinstance(data, dict) and data.get("error") == "Authentication error":
            logger.error("TruSTAR Error: Failed to authenticate the provided access token")
            return 0, data

    # Log error and return if the response code is other than 200
    if isinstance(data, dict) and data.get("error_code", 200) != 200:
        data['other_error'] = True
        logger.error("TruSTAR Error: %s " % str(data["error"]))
        return 0, data
    return 1, data


def get_enclaves(basic_args, validation=False):
    """
    Get all available enclaves
    :param basic_args: basic details
    :param validation: boolean value to know which function is calling this
    :return: dict of all available enclaves
    """
    auth, config, access_token, url, verify, proxies = basic_args.get('auth'), basic_args.get('config'), basic_args.get('access_token'), basic_args.get('url'), basic_args.get('verify'), basic_args.get('proxies')
    data_retrieval_endpoint = url + "/api/1.3/enclaves"
    stanza_name = config.get('name')
    data = call_endpoint(basic_args.get('access_token'), data_retrieval_endpoint, verify, proxies)
    enclaves = {}
    if isinstance(data, dict) and data.get("error") == "Authentication error":
        # Get access token in case it is expired
        response = auth.get_access_token(config.get("api_key"), config.get("api_secret"), verify)
        access_token = response.get("access_token")
        if not access_token:
            return 0
        basic_args['access_token'] = access_token
        # Call endpoint with new access_token
        data = call_endpoint(basic_args.get('access_token'), data_retrieval_endpoint, verify, proxies)

        if isinstance(data, dict) and data.get("error") == "Authentication error":
            logger.error("TruSTAR Error: Failed to authenticate the provided access token")
            return enclaves

    # Log error and return if the response code is other than 200
    if isinstance(data, dict) and data.get("error_code", 200) != 200:
        logger.error("TruSTAR Error: %s " % str(data["error"]))
        return enclaves
    for enclave in data:
        enclaves[enclave.get('id')] = enclave
        if not validation:
            handle_output(enclave, data_retrieval_endpoint, url, stanza_name)
    logger.debug("enclaves: " + str(enclaves))
    return enclaves


def get_indicators(report_id, basic_args):
    """
    Get indicators associated with report_id
    :param report_id: id of report
    :param basic_args: basic details
    :return: indicator data associated with given report_id
    """
    data_retrieval_endpoint, verify, proxies = basic_args.get('data_retrieval_endpoint'), basic_args.get('verify'), basic_args.get('proxies')
    data_retrieval_endpoint += '/{}/indicators'.format(report_id)
    page_number = 0
    params = {'pageNumber':page_number, 'pageSize':50}
    logger.debug("Getting indicators for Report ID: " + str(report_id))
    logger.debug("Request parameters for getting indicators: " + str(params))

    data = call_endpoint(basic_args.get('access_token'), data_retrieval_endpoint, verify, proxies, params=params)
    success, data = handle_error(data, basic_args, params)
    if not success:
        return 0

    has_next = data.get('hasNext')
    indicator_list = data['items']
    final_indicators = data['items']
    while has_next and len(indicator_list)>0:
        params['pageNumber'] = page_number + 1
        logger.debug("Request parameters for getting indicators: " + str(params))
        data = call_endpoint(basic_args.get('access_token'), data_retrieval_endpoint, verify, proxies, params=params)
        success, data = handle_error(data, basic_args, params)
        if not success:
            return 0
        has_next = data.get('hasNext')
        indicator_list = data['items']
        page_number = data.get('pageNumber')
        final_indicators += data['items']

    return final_indicators


def get_indicator_tags(enclave_ids, basic_args):
    """
    Get indicator tags
    :param enclave_ids: enclave ids
    :param basic_args: basic details
    :return: indicator tags
    """
    data_retrieval_endpoint, verify, proxies = basic_args.get('data_retrieval_endpoint'), basic_args.get('verify'), basic_args.get('proxies')
    data_retrieval_endpoint += '/tags'
    params = None
    if enclave_ids is not None:
        params = {'enclaveIds': enclave_ids}

    logger.debug("Request parameters for getting indicator tags: " + str(params))
    data = call_endpoint(basic_args.get('access_token'), data_retrieval_endpoint, verify, proxies, params=params)
    success, data = handle_error(data, basic_args, params)
    if not success:
        return 0
    return data


def get_indicator_enclaves(indicators, basic_args):
    """
    Gets and sets enclave information about indicators
    :param indicators: list of indicators
    :param basic_args: basic details
    :return: list of indicators
    """
    if indicators:
        url, verify, proxies = basic_args.get('url'), basic_args.get('verify'), basic_args.get('proxies')
        data_retrieval_endpoint = url + "/api/1.3/indicators/metadata"
        params = [{"value": str(indicator.get('value'))} for indicator in indicators
                                 if indicator.get('value') != "" and indicator.get('value') is not None]
        # This endpoint must be a POST considering the GET endpoint is depracated
        data = call_endpoint(basic_args.get('access_token'),
                             data_retrieval_endpoint,
                             verify,
                             proxies,
                             params=params,
                             post_request=True)
        success, data = handle_error(data, basic_args, params)
        if not success:
            return 0
        indicator_with_enclaves = {}
        for indicator in data:
            indicator_with_enclaves[indicator.get('value')] = indicator.get('enclaveIds', [])
        for indicator in indicators:
            indicator['enclaveIds']=indicator_with_enclaves.get(indicator['value'],[])
    return indicators


def handle_wait_time(data, data_retrieval_endpoint, headers, verify, params, proxies):
    """
    Handles API rate limit
    :param data: response of request
    :param data_retrieval_endpoint: endpoint to get data
    :param headers: headers to pass in request
    :param verify: SSL certification
    :param params: parameters to pass in request
    :param proxies: proxy uri
    :return response of request
    """
    waiting_time = data.json().get('waitTime',WAIT_TIME)
    while data.status_code == 429 and waiting_time <= WAIT_TIME:
        logger.debug(data.json().get("message", message))
        logger.debug("Going to sleep for: {} milliseconds".format(waiting_time))
        time.sleep((waiting_time/1000) + 1)
        data = requests.get(url=data_retrieval_endpoint, headers=headers, verify=verify, params=params, proxies=proxies)
        if data.status_code == 429:
            waiting_time = data.json().get('waitTime',WAIT_TIME)
    return data


def handle_failures(data):
    """
    Handles API failures
    :param data: response of request
    """
    error_dict = {}
    if data.status_code == 429:
        error_dict = {"error_code": data.status_code, "error": data.json().get("message", message)}
    elif data.status_code == 504 or data.status_code == 500:
        msg = "Gateway Timeout" if data.status_code == 504 else message
        error_dict = {"error_code": data.status_code, "error":msg}
    else:
        error_dict = {"error_code": data.status_code, "error": data.json().get("error", message)}
    return error_dict


def call_endpoint(access_token, data_retrieval_endpoint, verify, proxies, params=None, post_request=False):
    """ 
    This method makes REST call on TruSTAR station on the provided endpoint.
    :param access_token: access_token required to make REST call
    :param data_retrieval_endpoint: endpoint to fetch data from
    :param verify: true or path to certificate
    :param proxies: proxy server information
    :param params: request parameters
    """

    headers={
        "Authorization": "Bearer " + access_token,
        "Client-Type":"API",
        "Client-Version": "1.3",
        "Client-Metatag": "SPLUNK"
    }
    proxies = {"https": proxies} if proxies else None

    try:
        if post_request:
            headers['Content-Type'] = 'application/json; charset=utf-8'
            data = requests.post(url=data_retrieval_endpoint, headers=headers, verify=verify, data=json.dumps(params), proxies=proxies)
        else:
            # Make REST call with parameters
            data = requests.get(url=data_retrieval_endpoint, headers=headers, verify=verify, params=params, proxies=proxies)

        if data.status_code == 504 or data.status_code == 500:
            msg = "Gateway Timeout: " if data.status_code==504 else message
            logger.debug(msg + str(data.status_code))
            logger.debug("Retrying to connect server: " + str(data_retrieval_endpoint))
            data = requests.get(url=data_retrieval_endpoint, headers=headers, verify=verify, params=params, proxies=proxies)

        elif data.status_code == 429:
            data = handle_wait_time(data, data_retrieval_endpoint, headers, verify, params, proxies)

        if data.status_code == 400 and data.json().get('error') == "invalid_request":
            auth_error_dict = {"error_code": 400, "error": "Authentication error"}
            return auth_error_dict

        # Failure scenario
        if data.status_code != 200:
            return handle_failures(data)

        # Return response in json format
        return data.json()
    # Handle any exception encountered
    except Exception as exe:
        logger.error("TruSTAR Error: Unable to call endpoint %s , %s" % (data_retrieval_endpoint, exe))
        sys.exit(1)


def usage():
    """ Method to provide usage of this modular input.
    """

    print ("usage: %s [--scheme|--validate-arguments]")
    logger.error("TruSTAR Error: Incorrect Program Usage")
    sys.exit(2)


def do_scheme():
    """ To get scheme of modular input, which will be used by splunkd
    """

    print (SCHEME)


def handle_output(output, data_retrieval_endpoint, url, stanza_name):
    """ 
    To handle response of API call.
    :param output: response of API call
    :param data_retrieval_endpoint: endpoint to fetch data from
    :param url: TruSTAR station URL
    :param stanza_name: provided modular input name
    """

    try:
        # Call __call__() method of "TruSTARResponseHandler" class
        RESPONSE_HANDLER_INSTANCE(output, data_retrieval_endpoint, url, stanza_name)
        sys.stdout.flush()
    # Handle RuntimeError exception, if encountered
    except RuntimeError as e:
        logger.error("TruSTAR Error: Looks like an error while handling the response : %s for endpoint %s" % (
            str(e), data_retrieval_endpoint))


def print_xml_params(params, config_dict):
    for param in params:
        param_name = param.getAttribute("name")
        logger.debug("XML: found param '%s'" % param_name)
        if param_name and param.firstChild and param.firstChild.nodeType == param.firstChild.TEXT_NODE:
            data = param.firstChild.data
            config_dict[param_name] = data
            if not (param_name=="https_proxy_password" or param_name=="api_secret"):
                logger.debug("XML: '%s' -> '%s'" % (param_name, data))


def get_input_config_util(conf_node, config_dict):
    if conf_node:
        logger.debug("XML: found configuration")
        stanza = conf_node.getElementsByTagName("stanza")[0]
        if stanza:
            stanza_name = stanza.getAttribute("name")
            if stanza_name:
                logger.debug("XML: found stanza " + stanza_name)
                config_dict["name"] = stanza_name

                params = stanza.getElementsByTagName("param")
                print_xml_params(params, config_dict)


def get_input_config():
    """ To read configuration of modular input from standard input for execution of modular input
    :return: configuration dictionary
    """

    config_dict = {}

    try:
        # Read everything from stdin
        config_str = sys.stdin.read()

        # Parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        # Get root element
        root = doc.documentElement

        # Get all the required values by parsing the XML configurations obtained by reading the standard input
        session_key_node = root.getElementsByTagName("session_key")[0]

        if session_key_node and session_key_node.firstChild and \
                session_key_node.firstChild.nodeType == session_key_node.firstChild.TEXT_NODE:
            data = session_key_node.firstChild.data
            config_dict["session_key"] = data

        server_uri_node = root.getElementsByTagName("server_uri")[0]
        if server_uri_node and server_uri_node.firstChild and \
                server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:
            data = server_uri_node.firstChild.data
            config_dict["server_uri"] = data

        conf_node = root.getElementsByTagName("configuration")[0]
        get_input_config_util(conf_node, config_dict)

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
                checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config_dict["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config_dict:
            raise Exception("Invalid configuration received from Splunk.")

    # Handle any exception encountered
    except Exception as exe:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(exe))
    return config_dict


def get_validation_config():
    """ To read configuration of modular input from standard input for validation of modular input configs.
    :return: configuration as dictionary
    """

    # Read everything from stdin
    val_str = sys.stdin.read()
    # Parse XML
    doc = xml.dom.minidom.parseString(val_str)
    # Get root element element of XML content
    root = doc.documentElement
    # Get first element with tag name "item" from XML content
    item_node = root.getElementsByTagName("item")[0]
    session_key = ""
    server_uri = ""
    session_key_node = root.getElementsByTagName("session_key")[0]
    if session_key_node and session_key_node.firstChild and \
            session_key_node.firstChild.nodeType == session_key_node.firstChild.TEXT_NODE:
        session_key = session_key_node.firstChild.data

    server_uri_node = root.getElementsByTagName("server_uri")[0]
    if server_uri_node and server_uri_node.firstChild and \
            server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:
        server_uri = server_uri_node.firstChild.data

    if item_node:
        val_data = dict()
        # Get value of name attribute of element having tag name "name"
        name = item_node.getAttribute("name")
        val_data["stanza"] = name
        val_data["name"] = "trustar://"+name
        val_data["session_key"] = session_key
        val_data["server_uri"] = server_uri
        # Get elements with tag name "param"
        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            # Get value of "name" attribute
            name = param.getAttribute("name")

            # Update val_data dictionary
            if name and param.firstChild and param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

        return val_data

    return None


if __name__ == '__main__':
    if len(sys.argv) > 1:
        
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
        else:
            usage()
    else:
        
        # Get dictionary containing configurations
        config = get_input_config()
        # Get URL of TruSTAR instance and strip out trailing '/' if present
        config['url'] = config.get('trustar_url').strip('/')
        # Initialize object of "ModInputConfigApiKey" class
        mod_input = ModInputConfigApiKey(config)

        # Set "API secret", "API key" and "Proxy Password" if not found in configurations
        if not config.get("api_secret"):
            config['api_secret'] = mod_input.auth_api_secret
        if not config.get("api_key"):
            config['api_key'] = mod_input.auth_api_key
        if not config.get("https_proxy_password"):
            config["https_proxy_password"] = mod_input.https_proxy_password

        data_collection_status = int(str(config['enable_data_collection']))

        if data_collection_status != 0:
            do_run(config)
    sys.exit(0)
