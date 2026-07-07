"""
Modular Input Script

Copyright (C) 2012 Splunk, Inc.
All Rights Reserved

"""

import os
import os.path as op
import re
import sys
import threading
import time
import urllib
from defusedxml import minidom

import requests
import splunk.rest as rest

from requests_toolbelt.adapters import host_header_ssl

import credentials as cred
import logger_manager as log
from authhandlers import TokenAuth
from responsehandlers import ViolinResponseHandler
import tokens

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

myapp = __file__.split(os.sep)[-3]
APP_DIR = op.join(SPLUNK_HOME, "etc", "apps", myapp, "bin")
logger = log.setup_logging('violin_fsp')


class ModInputConfigBasic(object):
    """
    Handles ModInput related config, password encryption/decryption
    """

    encrypted = ""

    def __init__(self, meta_configs):
        self.meta_configs = meta_configs
        self.session_key = meta_configs.get("session_key")
        self.server_uri = meta_configs.get("server_uri")
        self.realm = meta_configs.get("realm")
        self.auth_user = meta_configs.get("username")
        self.auth_password = meta_configs.get("password")
        self.stanza_name = meta_configs.get("name")
        self.cred_manager = cred.CredentialManager(self.session_key,
                                                   self.server_uri)
        self.app = myapp
        if self.auth_password is not None:
            try:
                self.encrypt_new_credentials()
            except Exception:
                logger.exception("Violin FSP Error: Error while setting password")
            try:
                self.mask_input_credential()
            except Exception:
                logger.exception("Violin FSP Error: Error while masking password")
        else:
            self.auth_password = self.decrypt_existing_credentials()
            if self.auth_password is None:
                logger.error("Violin FSP Error: Error while getting password")

    def encrypt_new_credentials(self):
        """
        Stores auth_password in passwords.conf
        :return: None
        """
        cred_manager = cred.CredentialManager(self.session_key, self.server_uri)
        if cred_manager.get_encrypted_password(self.realm, self.auth_user, self.app, log_exception=False) is None:
            cred_manager.create(self.realm, self.auth_user, self.auth_password, self.app)
        else:
            cred_manager.update(self.realm, self.auth_user, self.auth_password, self.app)

    def decrypt_existing_credentials(self):
        """
        Retrieves auth_password from passwords.conf
        :return: password
        """
        cred_manager = cred.CredentialManager(self.session_key, self.server_uri)
        return cred_manager.get_clear_password(self.realm, self.auth_user, self.app)

    def mask_input_credential(self):
        """
        Masks auth_password in inputs.conf
        :return: None
        """
        path = self.server_uri + "/services/data/inputs/" + self.stanza_name.split("://")[0] + "/" + \
            urllib.quote(self.stanza_name.split("://")[1], safe="")
        rsp, content = rest.simpleRequest(path, method='GET', sessionKey=self.session_key, raiseAllErrors=True)
        data = rest.format.parseFeedDocument(content)
        content = data[0].toPrimitive()
        app_name = content['eai:acl']['app']
        path = self.server_uri + "/servicesNS/nobody/" + app_name + "/properties/inputs/" + urllib.quote(
            self.stanza_name, safe="")
        rest.simpleRequest(path, method='POST', sessionKey=self.session_key, postargs={"password": self.encrypted},
                           raiseAllErrors=True)


SCHEME = """<scheme>
    <title>Violin Systems REST Modular Input</title>
    <description>REST API input for polling data from Violin Systems FSPs</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>
            <arg name="name">
                <title>Host</title>
            </arg>
            <arg name="username">
                <title>Username</title>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="password">
                <title>Password</title>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="cert_path">
                <title>SSL Certificate Path.</title>
                <description>SSL Certificate path. No need to give path in case of CA signed certificate.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


def do_validate():
    """
    To validate inputs in mod-input
    :return: none
    """
    config = get_validation_config()
    username = config.get("username")
    password = config.get("password")
    sourcetype = config.get("sourcetype")

    cert_path = config.get('cert_path')
    verify = True
    if cert_path and cert_path.strip() != "":
        verify = cert_path.strip()

    # Validate sourcetype
    if sourcetype != "violin:fsp:rest":
        print "<error><message>Source type must be violin:fsp:rest</message></error>"
        sys.exit(2)

    # validate authentication

    custom_auth_handler_args = {"auth_type": "basic", "node": config.get('stanza')}
    custom_auth_handler_instance = TokenAuth(**custom_auth_handler_args)

    cookies, cert_host = custom_auth_handler_instance.get_session_id(username, password, verify)
    if not cookies:
        print """<error><message>Authentication Failed !
         Please verify Host, Username and Password of Concerto to Connect.</message></error>"""
        sys.exit(2)


def do_run(config):
    """
    main function which collects data and indexes it
    
    :param config: configuration of mod-input
    :return: none
    """
    original_endpoint = config.get("endpoint")
    session_token = config.get("session_key")
    node = config.get('node')

    cert_path = config.get('cert_path')
    verify = True
    if cert_path and cert_path.strip() != "":
        verify = cert_path.strip()

    # params
    auth_type = "basic"
    response_type = "json"

    response_handler_instance = ViolinResponseHandler()

    custom_auth_handler_args = {"auth_type": auth_type, "session_key": session_token, "endpoint": original_endpoint,
                                "node": node}
    auth = TokenAuth(**custom_auth_handler_args)

    try:
        if auth:
            cookies, cert_host = auth.get_session_id(config.get("username"), config.get("password"), verify)

            try:
                endpoint_list = replace_tokens(original_endpoint, cookies, cert_host, verify)
                for endpoint in endpoint_list:
                    data = call_endpoint(cookies, cert_host, endpoint, verify)
                    handle_output(response_handler_instance, data, response_type, endpoint, node, original_endpoint)
            except Exception as e:
                logger.error("Violin FSP Error: Error in calling endpoint %s , %s, %s" % (
                    e.args, str(e), original_endpoint))

    except Exception as e:
        logger.error("Violin FSP Error: Looks like an error: %s" % str(e))
        sys.exit(2)


def call_endpoint(cookies, cert_host, endpoint, verify):
    """
    To call and get response from an API call
    
    :param cookies: cookie for current session for API call
    :param cert_host: issuer of certificate
    :param endpoint: URL for API call
    :param verify: value to decide way of certificate verification while executing api call
    :return: response in simple text
    """
    try:
        request_session = requests.Session()
        request_session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
        headers = {"Host": cert_host}
        data = request_session.get(endpoint, cookies=cookies, verify=verify, headers=headers)
        return data.text
    except Exception as e:
        logger.error("Violin FSP Error: Unable to call endpoint %s , %s" % (endpoint, e))


def replace_tokens(original_endpoint, cookie, cert_host, verify):
    """
    To replace token and generate new endpoints, if it does not contain any token then will be returned as is.
    
    :param original_endpoint: endpoint containing token
    :param cookie: cookie for current session for API call
    :param cert_host: issuer of certificate
    :param verify: value to decide way of certificate verification while executing api call
    :return: list of generated endpoints
    """
    try:
        # for token in substitution_tokens:
        substitution_tokens = re.findall("\$(\w+)\$", str(original_endpoint))
        if substitution_tokens:
            response_data = getattr(tokens, substitution_tokens[0])(original_endpoint, cookie, cert_host, verify)
            return response_data
        else:
            return [original_endpoint]

    except Exception as e:
        logger.error("Violin FSP Error: Error in calling token data: %s for token %s for endpoint %s" % (
            str(e.args), substitution_tokens[0], original_endpoint))


def usage():
    """
    To provide usage of this modular input
    :return: none
    """
    print "usage: %s [--scheme|--validate-arguments]"
    logger.error("Violin FSP Error: Incorrect Program Usage")
    sys.exit(2)


def do_scheme():
    """
    To get scheme of modular input, which will be used by splunkd
    :return: none
    """
    print SCHEME


def handle_output(response_handler_instance, output, response_type, endpoint, node, original_endpoint):
    """
    To handle response of API call
    
    :param output: response in simple text
    :param response_type: type of response from API call
    :param endpoint: URL of API call
    :param node: host for API call
    :param original_endpoint: endpoint without replacing token
    :return: none
    """
    try:
        response_handler_instance(output, response_type, node, endpoint, original_endpoint)
        sys.stdout.flush()
    except RuntimeError as e:
        logger.error("Violin FSP Error: Looks like an error while handling the response : %s for endpoint %s" % (
            str(e), endpoint))


# read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_input_config():
    """
    To read configuration of modular input from std input for execution of modular input
    :return: configuration as dictionary
    """
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = minidom.parseString(config_str)
        root = doc.documentElement

        session_key_node = root.getElementsByTagName("session_key")[0]
        if session_key_node and session_key_node.firstChild and \
                session_key_node.firstChild.nodeType == session_key_node.firstChild.TEXT_NODE:
            data = session_key_node.firstChild.data
            config["session_key"] = data

        server_uri_node = root.getElementsByTagName("server_uri")[0]
        if server_uri_node and server_uri_node.firstChild and \
                server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:
            data = server_uri_node.firstChild.data
            config["server_uri"] = data

        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logger.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logger.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logger.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                                param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logger.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
                checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception("Invalid configuration received from Splunk.")

    except Exception, e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))
    return config


# read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    """
    To read configuration of modular input from std input for validation of modular input configs
    :return: configuration as dictionary
    """
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = minidom.parseString(val_str)
    root = doc.documentElement

    logger.debug("Violin FSP: XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logger.debug("Violin FSP: XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logger.debug("Violin FSP: Found param %s" % name)
            if name and param.firstChild and \
                    param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data


# run savedsearches to fill lookups
def run_savedsearches():
    """
    To run savedsearches which will fill lookups
    :return: none
    """
    try:
        rest.simpleRequest('/servicesNS/nobody/violin-app-fsp/saved/searches/VMEM_FSP_Mapping/dispatch',
            sessionKey=config.get('session_key'), method='POST', raiseAllErrors=True)
        rest.simpleRequest('/servicesNS/nobody/violin-app-fsp/saved/searches/VMEM_LUN_Mapping/dispatch',
            sessionKey=config.get('session_key'), method='POST', raiseAllErrors=True)
        rest.simpleRequest('/servicesNS/nobody/violin-app-fsp/saved/searches/VMEM_Client_LUN_Mapping/dispatch',
            sessionKey=config.get('session_key'), method='POST', raiseAllErrors=True)
        rest.simpleRequest('/servicesNS/nobody/violin-app-fsp/saved/searches/VMEM_TimeMark_Mapping/dispatch',
            sessionKey=config.get('session_key'), method='POST', raiseAllErrors=True)
    except Exception as e:
        logger.error("Violin FSP Error: error while dispatching savedsearch: %s" % str(e))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
        else:
            usage()
    else:
        inputs_file = op.join(APP_DIR, 'inputs.txt')
        try:
            endpoint_lines = open(inputs_file, 'r').read().splitlines()
        except IOError as e:
            logger.error("Violin FSP Error: IO error for inputs.txt : %s" % str(e))
            sys.exit(1)
        config = get_input_config()
        config['realm'] = config.get('name')
        config['node'] = config.get('name').split('://')[-1]

        mod_input = ModInputConfigBasic(config)
        is_initial = True
        if not config.get("password"):
            config['password'] = mod_input.auth_password
            is_initial = False

        for endpoint in endpoint_lines:
            config['endpoint'] = 'https://' + config.get('node') + str(endpoint)

            requester = threading.Thread(target=do_run, args=(config,))
            requester.start()

        # To run savedsearches at create or update mod-input only
        if is_initial:
            time.sleep(60)
            run_savedsearches()

    sys.exit(0)
