# Copyright (C) 2017-2025 Sideview LLC.
"""
This code in this particular file is distributed under the MIT license, and was
originally derived from Dominique Vocat's TA_ciscoaxl app (also distributed under
the MIT License).
"""


import base64
import json
import logging
import logging.handlers
import os
import re
import sys
import time
import traceback
import xml.etree.ElementTree
import ssl
import types
import urllib.error
import urllib.request
from http.client import IncompleteRead
from urllib.request import pathname2url

import splunk.Intersplunk
import splunk.rest

from splunk import ResourceNotFound
from splunk.models.base  import SplunkAppObjModel
from splunk.models.field import Field

from suds.client import Client
from suds import WebFault




try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError



APP_NAME = "SA_cisco_cdr_axl"
SPLUNK_HOME = os.environ["SPLUNK_HOME"]
WSDL_FILENAME = "AXLAPI.wsdl"
XSD_FILENAME = "AXLSoap.xsd"

URI = "/servicesNS/nobody/SA_cisco_cdr_axl/configs/conf-ciscoaxl"
LOG_FILE_PATH = os.path.join(SPLUNK_HOME, "var", "log", "splunk", APP_NAME + ".log")
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

PATCH_FOR_INITIAL_TRUNCATED_RESPONSE = True

def get_logger():
    """ we use our own log file, although regrettably this is still
    left to be handled by the _internal data input"""

    our_logger = logging.getLogger(APP_NAME)
    if not our_logger.handlers:
        our_logger.propagate = False
        our_logger.setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler(LOG_FILE_PATH, mode="a")
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        our_logger.addHandler(handler)
    return our_logger

logger = get_logger()


def check_license(session_key):
    """ check that there is a valid license file for this app."""
    uri = "/services/sa_cisco_cdr_axl_license"
    try:
        _response, content = splunk.rest.simpleRequest(uri, raiseAllErrors=True, sessionKey=session_key)
        license = json.loads(content)

        if license["it"] == 0:
            license_type = "License"
        else:
            license_type = "Trial license"

        if license["le"] != 0 and license["le"] < time.time():
            raise ValueError("%s is expired" % license_type)
        if license["pr"] != APP_NAME:
            raise ValueError("%s is for a different app" % license_type)

    except splunk.ResourceNotFound:
        raise ValueError("No license is loaded for the %s app. Contact Sideview to get a valid trial license, or to get a copy of your paid license." % APP_NAME)


class SplunkStoredCredential(SplunkAppObjModel):
    """Class for managing secure credential storage."""

    resource = 'storage/passwords'

    clear_password = Field()
    encr_password = Field()
    username = Field()
    password = Field()
    realm = Field()


def get_password(host, user, app, session_key):
    """ get the cleartext password from the storage/passwords stanza represented by the
    host and user """
    _cred_id = "%s:%s" % (host, user)
    q_id = SplunkStoredCredential.build_id(_cred_id, app, 'nobody')
    q = SplunkStoredCredential.get(q_id, session_key)
    return q.clear_password


def set_password(host, user, app, session_key, password):
    """ remember, if you find yourself debugging Splunk's encrypted password endpoint
    that any user with the list_storage_passwords capability (which may be many or most users) can
    run this search in splunk:
    | rest /servicesNS/-/-/storage/passwords | fields username realm clear_password

    and see not just the current cleartext password of the auth that you're troubleshooting.
    but the cleartext passwords for every single credential stored in Splunk's encrypted password
    endpoint.  O_O  Splunk knows this and is apparently OK with it.
        """
    logger.info("Saving auth info in splunk's encrypted password store")
    _cred_id = "%s:%s" % (host, user)

    # First see if this credential exists.
    # more precisely, see if this host+username combination already exists in this app.
    q_id = SplunkStoredCredential.build_id(_cred_id, app, 'nobody')
    try:
        SplunkStoredCredential.get(q_id, session_key)

        logger.info("Found existing credential")

        try:
            logger.info("Updating existing credential")
            postargs = {'password': password}
            cred = SplunkStoredCredential.manager()._put_args(q_id, postargs, sessionKey=session_key)
            logger.debug("Updated existing credential")
        except Exception:
            logger.error("Exception updating existing credential")
            logger.error(traceback.format_exc())

    except ResourceNotFound:
        logger.info("No existing credential found. Creating a new one.")
        cred = SplunkStoredCredential(app, 'nobody', user, sessionKey=session_key)
        cred.realm = host
        cred.password = password
        cred.create()
        logger.debug("created a new credential")
    except Exception:
        logger.error("unexpected Exception while creating new credential in /admin/passwords")
        logger.error(traceback.format_exc())


def get_command_options():
    """ tease out any options that were passed to the given command """
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    logger.debug("keywords are %s", keywords)
    logger.debug("options are %s", options)
    return keywords, options


def path_to_url(path):
    """ gets a file URL for silly libraries that need such things"""
    return urlparse.urljoin('file:', pathname2url(path))


def log_error(msg, e=None):
    """ marshal these screams of anguish into results pls."""

    logger.error(msg)
    logger.error(e)
    if e:
        stack = traceback.format_exc()
        logger.error(stack)
        splunk.Intersplunk.generateErrorResults("Error :  %s Traceback: '%s'. %s" % (msg, e, stack))
    else:
        splunk.Intersplunk.generateErrorResults("Error : %s" % msg)


def add_provenance_fields(results, stanza):
    """ can't know where you're going without knowing where you came from"""
    for result in results:
        result["axlHost"] = stanza["host"]
        result["axlPort"] = stanza["port"]
        result["axlUser"] = stanza["user"]
    return results


def is_authentication_error(e):
    """ my god it's full of stars. """

    try:
        # if soapy just does raise(Exception((status, reason))) because it is 2003
        # e.args is ((401, "whoa"))
        # e.args[0] is (401,"whoa")
        # e.args[0][0] is 401
        if e.args and len(e.args) > 0 and len(e.args[0]) > 0 and e.args[0][0] == 401:
            return True
    except Exception as e2:
        pass
    try:
        # Note e is possibly sometimes of TypeNotFound,  if you do columns="name, description"
        if e.message and e.message[0] == 401:
            return True
    except Exception as e2:
        pass
    return False


def atom_response_to_stanza_list(conf_response):
    """ convert the weird stanzaname stuff to a more sensible dict."""
    nodes = []
    if not conf_response["entry"]:
        raise Exception("No ciscoaxl.conf stanzas were seen at all")

    for stanza in conf_response["entry"]:

        # ignore disabled ones.
        if "disabled" in stanza["content"] and stanza["content"]["disabled"]:
            continue

        segments = stanza["name"].split(":")
        if len(segments) != 3:
            raise ValueError("invalid stanza in ciscoaxl.conf - [%s]. It must be of the form [host:port:username]" % stanza["name"])
        node = {}
        node["host"] = segments[0]
        node["port"] = segments[1]
        node["user"] = segments[2]
        node["name"] = stanza["name"]

        content_keys = ["methodwhitelist", "queryblacklist", "password", "wsdl_subdirectory", "timeout"]
        for key in content_keys:
            if key in stanza["content"]:
                node[key] = stanza["content"][key]
        nodes.append(node)
    return nodes


def get_active_connections(session_key):
    """ get the current configured stanzas from ciscoaxl.conf"""
    try:
        _response, content = splunk.rest.simpleRequest(URI, postargs={}, getargs={"output_mode": "json"}, raiseAllErrors=True, sessionKey=session_key)
    except Exception as e:
        raise Exception("failed to make the rest request for ciscoaxl.conf - " + str(e))

    logger.info("we have read the stanzas (if any) from ciscoaxl.conf.")

    return atom_response_to_stanza_list(json.loads(content))


def get_connection(stanza, session_key):
    """ get the given stanza from ciscoaxl.conf"""
    uri = URI + "/" + stanza
    _response, content = splunk.rest.simpleRequest(uri, postargs={}, getargs={"output_mode": "json"}, raiseAllErrors=True, sessionKey=session_key)
    return atom_response_to_stanza_list(json.loads(content))


def update_connection(stanza, session_key):
    """ update the stanza in ciscoaxl.conf"""

    ## Note - we don't really update this, we just POST to make sure its enabled.
    #existing_stanza = get_connection(stanza, session_key)

    uri = URI + "/" + stanza
    postargs = {
        "disabled":"false"
    }
    _response, _content = splunk.rest.simpleRequest(uri, method="POST", postargs=postargs, getargs={}, raiseAllErrors=True, sessionKey=session_key)
    return True


def create_connection(stanza, session_key):
    """ post the stanza to ciscoaxl.conf """
    uri = "/servicesNS/nobody/SA_cisco_cdr_axl/configs/conf-ciscoaxl"
    postargs = {
        "name": stanza
    }
    try:
        _response, _content = splunk.rest.simpleRequest(uri, sessionKey=session_key, postargs=postargs, method='POST', raiseAllErrors=True)
        return True

    except splunk.AuthorizationFailed:
        logger.error("received a 403 from splunkd when we tried to create the new connection stanza by posting to ", uri)
        return False

    except ResourceNotFound:
        return False


def delete_connection(stanza, session_key):
    """ Delete the stanza from ciscoaxl.conf """
    try:
        existing_stanza = get_connection(stanza, session_key)
    except splunk.AuthorizationFailed:
        logger.error("received a 403 from splunkd when we tried to get the details for a connection stanza from ", URI)
        existing_stanza = False
    except ResourceNotFound:
        logger.error("received a 404 from splunkd when we tried to get the details for a connection stanza from ", URI)
        existing_stanza = False

    if existing_stanza:
        uri = URI + "/" + stanza
        _response, _content = splunk.rest.simpleRequest(uri, method="DELETE", postargs={}, getargs={}, raiseAllErrors=True, sessionKey=session_key)
        return True
    return False


def filter_connections_to_specified_servers(stanzas, server_arg):
    """ given a set of connections (stanza dicts), and a specified server arg,
    (comma separated string), return a list of connections that
    match the server arg """
    servers = server_arg.split(",")
    # iterate over a copy so we can remove() from the original
    for stanza in list(stanzas):
        keep = False
        # is the entire literal stanza name one of the values
        if stanza["name"] in servers:
            keep = True
        if stanza["host"] in servers:
            keep = True
        if not keep:
            stanzas.remove(stanza)
    return stanzas


def get_unsupported_value_message(configured_stanzas, options):
    """ between the configured stanzas and the server directive in options,
    the user has told us to talk to zero servers or one that doesnt exist. """
    message = "unknown error"
    if "server" in options:
        message = "invalid / unsupported value for server: " + options["server"]
    return message


def check_directory_traversal(subdirectory_path):
    """ Throw exception if the given path is not actually within this app.  """
    app_path = os.path.join(SPLUNK_HOME, "etc", "apps", "SA_cisco_cdr_axl")
    relative_path = os.path.relpath(subdirectory_path, start=app_path)
    if relative_path.startswith(os.pardir):
        raise ValueError("configured wsdl_subdirectory is not strictly contained within %s" % app_path)


def get_wsdl_path(subdirectory):
    """ returns the path to the WSDL file. does a lot of checks along the way. """
    subdirectory_path = os.path.join(SPLUNK_HOME, "etc", "apps", "SA_cisco_cdr_axl", subdirectory)
    check_directory_traversal(subdirectory_path)
    wsdl_path = os.path.join(subdirectory_path, WSDL_FILENAME)
    xsd_path = os.path.join(subdirectory_path, XSD_FILENAME)
    #normal pythonic approach would be to catch the error.
    # But a) in python3 it's FileNotFoundError and in python2 it's something else.
    # b) This suds client may well throw other weird errors or the same in other cases,
    # c) I'm not positive that windows wont have some lame OSError equivalent too.
    # so we just raise a simple IOError
    wsdl_missing = not os.path.exists(wsdl_path)
    xsd_missing = not os.path.exists(xsd_path)
    if wsdl_missing or xsd_missing:
        error_message_template = "wsdl_subdirectory was specified in ciscoaxl.conf as %s, but %s found there"
        if wsdl_missing and xsd_missing:
            error_message = error_message_template % (subdirectory_path, "neither %s nor %s were" % (WSDL_FILENAME, XSD_FILENAME))
        elif wsdl_missing:
            error_message = error_message_template % (subdirectory_path, WSDL_FILENAME + " was not")
        elif xsd_missing:
            error_message = error_message_template % (subdirectory_path, XSD_FILENAME + " was not")
        raise IOError(error_message)
    return wsdl_path



def add_password_to_conf(conf, session_key):
    password = get_password(conf["host"], conf["user"], APP_NAME, session_key)
    conf["password"] = password
    return conf

def get_client(conf, session_key, path="/axl/", remote_wsdl_path=None):
    """ wrapper for the suds client hoop jumping"""

    if remote_wsdl_path:
        remote_wsdl_url = "https://%s:%s%s" % (conf["host"], conf["port"], remote_wsdl_path)
        wsdl = remote_wsdl_url
    else:
        wsdl_path = get_wsdl_path(conf["wsdl_subdirectory"])
        wsdl = path_to_url(wsdl_path)

    location = "https://%s:%s%s" % (conf["host"], conf["port"], path)
    logger.debug("Making the actual AXL request. wsdl=%s   location=%s", wsdl, location)

    auth_str = '%s:%s' % (conf["user"], conf["password"])

    base64string = base64.b64encode(auth_str.encode("utf-8"))
    base64string = base64string.decode("utf-8").replace('\n', '')

    conf["timeout"] = int(conf["timeout"])

    # I don't think we ever need the following header. Or maybe I hope we dont.
    # and if we do, in the below 'listUser' is the method being called by ciscoaxl
    # which for ciscoaxlquery is most likely 'executeSQLQuery'
    # but getting the CUCM version would require more research.
    #
    # -H 'SOAPAction: CUCM:DB ver=11.5 listUser' \
    #
    authentication_header = {
        "Authorization": "Basic %s" % base64string,
        "Content-Type": "text/xml",
        "cache-control": "no-cache",
        "connection": "keep-alive"
    }
    return Client(wsdl, timeout=conf["timeout"], location=location, headers=authentication_header)


def check_against_method_whitelist(stanza, method):
    """ check the nice list """
    try:
        if not stanza["methodwhitelist"]:
            m_error = "The methodwhitelist key is blank in your ciscoaxl.conf and due to a high risk of this being a mistake in configuration management, the command will not be run"
            logger.error(m_error)
            splunk.Intersplunk.generateErrorResults('Error: %s (method=%s)' % (m_error, method))
            sys.exit()
        if not method_matches_whitelist(method, stanza["methodwhitelist"]):
            logger.warning("method name attempted that did not match whitelist. method was not run. - %s", method)
            splunk.Intersplunk.generateErrorResults('Error: your method did not match the configured methodwhitelist regex and was not run: (method=%s)' % method)
            sys.exit()
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        splunk.Intersplunk.generateErrorResults("Uncaught exception matching against methodwhitelist regex. Check your regex for errors -  %s" % stanza["queryblacklist"])
        sys.exit()


def method_matches_whitelist(method, methodwhitelist):
    """ actually run the regex. """
    pattern = re.compile(methodwhitelist, re.IGNORECASE)
    match = pattern.search(method)
    if not match:
        return False
    return True


def query_matches_blacklist(query, blacklist):
    """ check the naughty list """
    pattern = re.compile(blacklist, re.IGNORECASE)
    match = pattern.search(query)
    if match:
        return True
    return False


def get_method_verb(method_name):
    """ given method of "listFoo", returns "list" """
    verb = []
    for char in method_name:
        if char.islower():
            verb.append(char)
        else:
            return "".join(verb)
    return "ERROR - no lowercase 'verb' prefix found in method name %s" % method_name


def get_skip_limit_clauses(error_message, reduce_by):
    """ Given one of the 'request too large' messages from the soap server, it extracts the
    total result count, the suggested row count, and returns those PLUS a list of SKIP LIMIT
    clauses that will cover the same results with multiple queries"""

    pattern = re.compile("Total rows matched: (\\d+) rows. Suggestive Row Fetch: less than (\\d+) rows", re.IGNORECASE)
    match = pattern.search(error_message)

    if not match:
        logger.error(error_message)
        raise ValueError("received Query request too large message, but no suggested row fetch was found")
    total = int(match[1])
    increment = max(int(round(int(match[2]) / reduce_by, -3)), 500)
    clauses = []
    for i in range(0, total, increment):
        clauses += ["SKIP %s LIMIT %s" % (i, increment)]
    return total, increment, clauses


def wrap_in_skip_limit_clause(clause, query):
    """ the actual part where we wrap the query in a SKIP/LIMIT clause. """
    return "SELECT %s * FROM (\n%s\n)" % (clause, query)


def build_soap_request_xml_for_ris_query(results):
    wrapper = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap="http://schemas.cisco.com/ast/soap">
   <soapenv:Header/>
   <soapenv:Body>
      <soap:selectCmDevice>
         <soap:StateInfo></soap:StateInfo>
         <soap:CmSelectionCriteria>
            <soap:MaxReturnedDevices>1000</soap:MaxReturnedDevices>
            <soap:DeviceClass>Any</soap:DeviceClass>
            <soap:Model>255</soap:Model>
            <soap:Status>Any</soap:Status>
            <soap:NodeName></soap:NodeName>
            <soap:SelectBy>Name</soap:SelectBy>
            <soap:SelectItems>
            %s
            </soap:SelectItems>
            <soap:Protocol>Any</soap:Protocol>
            <soap:DownloadStatus>Any</soap:DownloadStatus>
         </soap:CmSelectionCriteria>
      </soap:selectCmDevice>
   </soapenv:Body>
</soapenv:Envelope>"""

    list_xml = []

    for item in results:
        device_name = item.get('name', None)
        if device_name is not None:
            list_xml.append("""
       <soap:item>
          <soap:Item>%s</soap:Item>
       </soap:item>""" % device_name)

    return wrapper % "".join(list_xml)


def make_soap_request_for_ris_query(host, port, user, password, soap_request_xml):

    location = "https://%s:%s/realtimeservice2/services/RISService70?wsdl" % (host, port)
    credentials = base64.b64encode(('%s:%s' % (user, password)).encode()).decode()
    headers = {'SOAPAction': '"http://schemas.cisco.com/ast/soap/action/#RisPort#SelectCmDeviceExt"',
               'Content-Type': 'text/xml; charset=utf-8',
               'Authorization': 'Basic ' + credentials}
    if isinstance(soap_request_xml, str):
        soap_request_xml = soap_request_xml.encode('utf-8')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(location, data=soap_request_xml, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return types.SimpleNamespace(text=resp.read().decode('utf-8', errors='replace'),
                                         status_code=resp.status)
    except urllib.error.HTTPError as e:
        return types.SimpleNamespace(text=e.read().decode('utf-8', errors='replace'),
                                     status_code=e.code)


def get_results_for_ris_query(response_xml, status_code, namespaces):
    tree = xml.etree.ElementTree.fromstring(response_xml)

    if status_code >= 400:
        logger.error(status_code)
        #axl.log_error("HTTP error %s received with user=%s host=%s port=%s location=%s" % (status_code, user, host, port, location), logger)
        sys.exit()

    """
<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
<soapenv:Body>
<ns1:selectCmDeviceResponse xmlns:ns1="http://schemas.cisco.com/ast/soap">
<ns1:selectCmDeviceReturn>
<ns1:SelectCmDeviceResult>
    <ns1:TotalDevicesFound>0</ns1:TotalDevicesFound>
    <ns1:CmNodes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="1" />
</ns1:SelectCmDeviceResult>
<ns1:StateInfo></ns1:StateInfo>
</ns1:selectCmDeviceReturn>
</ns1:selectCmDeviceResponse>
</soapenv:Body></soapenv:Envelope>
"""
    body = tree.find("{http://schemas.xmlsoap.org/soap/envelope/}Body")

    device_response = body.find("ns1:selectCmDeviceResponse", namespaces)
    logger.error(device_response)
    device_return = device_response.find("ns1:selectCmDeviceReturn", namespaces)
    logger.error(device_return)
    device_result = device_return.find("ns1:SelectCmDeviceResult", namespaces)
    logger.error(device_result)

    cm_nodes = device_result.find("ns1:CmNodes", namespaces)

    total_devices_found = device_result.find("ns1:TotalDevicesFound", namespaces)
    if total_devices_found.text == "0":
        logger.error("no devices found")
    logger.error(cm_nodes)
    if "ns1:Server.RateControl" in response_xml:
        logger.error("we hit rate limit, we were too fast!")

    node_and_device_dict = convert_ris_cm_nodes_to_dict(cm_nodes, namespaces)

    return node_and_device_dict


def convert_ris_cm_nodes_to_dict(cm_nodes, namespaces):
    """
        this will return a dict like:
        {
        "cluster1": {
            "device1": {stuff and things},
            "device2": {stuff and things}
        },
        "cluster2": {
            "device3": {stuff and things},
            "device4": {stuff and things}
        }
    """
    node_and_device_dict = {}
    for node in cm_nodes:
        cm_node_name = node.find("ns1:Name", namespaces).text
        node_and_device_dict[cm_node_name] = {}

        for device in node.find("ns1:CmDevices", namespaces):

            device_name = device.find("ns1:Name", namespaces).text
            node_and_device_dict[cm_node_name][device_name] = {}

            for key in device:
                tag_name = re.sub(r'\{.+\}', '', key.tag)

                # THIS IS WEIRD
                # SOME OF THESE ARE STRAIGHT TEXT KEY SLIKE <THING>12</THING>
                # others are complex nested XML with no text content.
                if key.text and key.text.strip():
                    node_and_device_dict[cm_node_name][device_name][tag_name] = key.text.strip()

    return node_and_device_dict


def get_results_for_axl_method(stanza, options, columns, method, session_key):
    """ does the actual work of talking to AXL to fulfill the query """

    #pickling known good output,  takes this from about 90 seconds, to 3 seconds.
    if "testmode" in options:
        if options["testmode"] == "1":
            with open('mock_ciscoaxl_output_for_%s' % stanza["user"], 'r') as dump_file:
                return json.load(dump_file)

        options.pop("testmode", None)


    if "host" not in stanza or "port" not in stanza or "user" not in stanza:
        log_error("Somehow either the host, port or user information seems to be missing from the stanzas in local/ciscoaxl.conf")
        sys.exit()

    try:
        add_password_to_conf(stanza, session_key)
    except splunk.AuthorizationFailed as e:
        splunk.Intersplunk.generateErrorResults("Error - your Splunk user account lacks the capability to read the secret password for the AXL host(s). 403 received from Splunkd.")
        sys.exit()

    try:
        client = get_client(stanza, session_key)
    except splunk.AuthorizationFailed as e:
        splunk.Intersplunk.generateErrorResults("Error - your user account lacks the minimum capabilities required to run this search command.")
        sys.exit()


    available_method_names = []
    for available_method in client.wsdl.services[0].ports[0].methods.values():
        available_method_names.append(available_method.name)

    results = []
    if method == "help":
        for method_name in available_method_names:
            method_verb = get_method_verb(method_name)
            white_listed = method_matches_whitelist(method_name, stanza["methodwhitelist"])

            results.append({
                "verb": method_verb,
                "method": method_name,
                "whitelisted": white_listed
            })

    else:
        if method in available_method_names:
            method_to_call = getattr(client.service, method)
        else:
            splunk.Intersplunk.generateErrorResults("%s is not listed in the available method names (%s)" % (method, ",".join(available_method_names)))
            sys.exit()

        try:
            result = method_to_call(options, columns)

        except URLError as e:
            logger.error(e)
            logger.info(traceback.format_exc())
            splunk.Intersplunk.generateErrorResults("could not connect to host=%s:%s - %s" % (stanza["host"], stanza["port"], str(e)))
            sys.exit()

        except Exception as e:
            if is_authentication_error(e):
                logger.error(e)
                logger.info(traceback.format_exc())
                splunk.Intersplunk.generateErrorResults("401 unauthorized - user/pass not accepted by host=%s:%s with username %s - check your auth info by going to Supporting App for AXL > Update credentials" % (stanza["host"], stanza["port"], stanza["user"]))
            # oops. we caught it, but we have no idea what it is.
            else:

                # TODO - for 4** and 5** get the actual message,  ie e.message[1]
                logger.error(e)
                logger.error(traceback.format_exc())
                soap_error_message = "Unexpected SOAP Client Error - check your wsdl and xsd files! %s" % str(e)
                splunk.Intersplunk.generateErrorResults(soap_error_message)
            sys.exit()

        if result["return"] == "":
            return []

        # this doesn't seem like how we're supposed to get results out of
        # this object but it appears to work reliably.
        for result in result[0][0]:
            results.append(dict(result))

    results = add_provenance_fields(results, stanza)
    #with open('mock_ciscoaxl_output_for_%s' % stanza["user"], 'w') as dump_file:
    #    json.dump(results, dump_file)
    return results


def get_count_for_sql_query(query, client):
    """ At the moment this is only used in an unusual corner case that we've seen
    many times but only on 12.5 and 12.5.1,  where we cant evenget CM to give us
    the "suggestive row fetch" message back, and where instead it terminates the
    connection right in the middle of the first response, thus throwing
    IncompleteRead in our SOAP client. """

    count_query = "select count(*) from (%s)" % query
    result = client.service.executeSQLQuery(sql=count_query)
    rows = [dict(n) for n in result['return']['row']]
    return rows[0]["count"]

def run_as_set_of_smaller_queries(clauses, increment, query, client):
    result = None
    for i, clause in enumerate(clauses):
        new_query = wrap_in_skip_limit_clause(clause, query)

        #just giving the PBX a few cycles of rest before we send it another one.
        time.sleep(2)

        logger.info("requesting a chunk of %s rows using the following query:\n%s", increment, new_query)

        #it's possible that this should swallow IncompleteRead just like the outer call does...
        if i == 0:
            result = client.service.executeSQLQuery(sql=new_query)
        else:
            logger.info("we have accumulated %s rows", len(result["return"]["row"]))

            new_rows = client.service.executeSQLQuery(sql=new_query)
            logger.info("received %s new rows from the current query", len(new_rows["return"]["row"]))
            result["return"]["row"] += new_rows["return"]["row"]
    return result


def get_results_for_sql_query(stanza, options, query, session_key):
    """ does most of the work for the ciscoaxl_query command.  """
    try:
        if not stanza["queryblacklist"]:
            q_error = "The queryblacklist key is blank in your ciscoaxl.conf and due to a high risk of this being a mistake in configuration management, the command will not be run"
            logger.error(q_error)
            splunk.Intersplunk.generateErrorResults('Error: %s (query=%s)' % (q_error, query))
            sys.exit()
        if query_matches_blacklist(query, stanza["queryblacklist"]):
            logger.warning("ciscoaxlquery - sql query attempted that matched queryblacklist. Query was not run.  - %s", query)
            splunk.Intersplunk.generateErrorResults('Error: your SQL query contained a term matching the queryblacklist and was not run: %s' % query)
            sys.exit()

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        splunk.Intersplunk.generateErrorResults("Uncaught exception matching against queryblacklist. Check your regex for errors -  %s" % stanza["queryblacklist"])
        sys.exit()

    if "testmode" in options:
        if options["testmode"] == "1":
            with open('mock_ciscoaxlquery_output_for_%s' % stanza["user"], 'r') as dump_file:
                return json.load(dump_file)
        options.pop("testmode", None)

    stanza["timeout"] = int(stanza["timeout"])
    try:
        add_password_to_conf(stanza, session_key)
    except splunk.AuthorizationFailed as e:
        splunk.Intersplunk.generateErrorResults("Error - your Splunk user account lacks the capability to read the secret password for the AXL host(s). 403 received from Splunkd.")
        sys.exit()

    try:
        client = get_client(stanza, session_key)
    except splunk.AuthorizationFailed as e:
        logger.error(e)
        splunk.Intersplunk.generateErrorResults("Error - your user account lacks the minimum capabilities required to run this search command.")
        sys.exit()

    result = {
        "return":""
    }
    try:
        #FORCE_INCOMPLETE_READ = True
        #if FORCE_INCOMPLETE_READ:
        #    raise IncompleteRead(True)
        result = client.service.executeSQLQuery(sql=query)

    except URLError as e:
        logger.error(e)
        logger.info(traceback.format_exc())
        splunk.Intersplunk.generateErrorResults("could not connect to host=%s:%s - %s" % (stanza["host"], stanza["port"], str(e)))
        sys.exit()

    except WebFault as e:
        if str(e).find("Query request too large") != -1 and hasattr(e, 'fault') and e.fault.faultcode == "soapenv:Server":
            total, increment, clauses = get_skip_limit_clauses(str(e), 2)

            logger.warning("received message from server saying request matched %s rows. We will try and get %s at a time using skip limit clauses.", total, increment)
            try:
                result = run_as_set_of_smaller_queries(clauses, increment, query, client)

            except IncompleteRead as e2:
                logger.warning("even after breaking SQL into multiple smaller queries with SKIP/LIMIT, we still got IncompleteRead")
                total, increment, clauses = get_skip_limit_clauses(str(e), 20)
                logger.warning("retrying with only %s rows at a time using skip limit clauses.", increment)
                result = run_as_set_of_smaller_queries(clauses, increment, query, client)

        else:
            log_error("unexpected error received from server", e)
            sys.exit()

    except IncompleteRead as e:
        logger.error(e)


        if PATCH_FOR_INITIAL_TRUNCATED_RESPONSE:

            message = "Response stopped abruptly from host=%s:%s on our very first request. We are making a separate count(*) request to get the total, so we can break it into smaller queries of 500 rows each." % (stanza["host"], stanza["port"])
            logger.error(message)

            try:
                # We do a SELECT count query to get the total
                total_count = get_count_for_sql_query(query, client)
                logger.info("received %s from our count(*) query", total_count)

                # then we use that to break the larger query into N subqueries.
                fake_message = "Total rows matched: %s rows. Suggestive Row Fetch: less than 500 rows" % total_count
                total, increment, clauses = get_skip_limit_clauses(fake_message, 2)

                result = run_as_set_of_smaller_queries(clauses, increment, query, client)

            except IncompleteRead as e2:
                logger.error(e2)
                message = "IncompleteRead raised even on our fallback query.  This CM node (%s) is having a problem and cannot return 500 rows without terminating its connection halfway through the SOAP response." % stanza["host"]
                logger.error(message)
                logger.info(traceback.format_exc())
                splunk.Intersplunk.generateErrorResults(message)
                sys.exit()
        else:
            message = "Response stopped abruptly from host=%s:%s on our very first request, raising IncompleteRead on our side. Unfortunately we don't know the total number of rows matched yet so we cannot devise a set of SKIP/LIMIT clauses." % (stanza["host"], stanza["port"])
            logger.error(message)
            logger.error(traceback.format_exc())
            splunk.Intersplunk.generateErrorResults(message)
            sys.exit()




    #another thing that can happen is socket.timeout "The read operation timed out"

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())


        if is_authentication_error(e):
            logger.error(e)
            splunk.Intersplunk.generateErrorResults("401 unauthorized - user/pass not accepted by %s:%s with username=%s - check your auth info in ciscoaxl.conf" % (stanza["host"], stanza["port"], stanza["user"]))
        # oops. we caught it, but we have no idea what it is.
        else:
            log_error("exception making the actual AXL API call for this ciscoaxlquery command.", e)
        sys.exit()

    if result["return"] == "":
        return []

    rows = [dict(n) for n in result['return']['row']]
    logger.info("AXL query returned %s rows", len(rows))
    #logger.debug(json.dumps(rows, indent=4))
    add_provenance_fields(rows, stanza)

    with open('dump_output_for_%s' % stanza["user"], 'w') as dump_file:
        json.dump(rows, dump_file)
    return rows
