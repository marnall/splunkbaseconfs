'''
BlueCat DNS Edge Modular Input Script
'''
from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
from builtins import str
from future.utils import raise_
import sys,logging,os
import requests,json
from xml.dom import minidom
from requests.auth import HTTPBasicAuth
from responsehandlers import BlueCatResponseHandler
import splunk.entity as entity
import credential_manager as cred
import urllib.request, urllib.parse, urllib.error
import splunk.rest as rest


# Global variables

APP = __file__.split(os.sep)[-3]
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")


logger = logging.getLogger("root")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


SCHEME = """<scheme>
    <title>BlueCat DNS Edge Modular Input</title>
    <description>Modular Input to fetch data from BlueCat DNS Edge API</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>BlueCat DNS Edge Modular Input</title>
                <description>Name of this input</description>
            </arg>
            <arg name="dns_server">
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="endpoint">
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="siem_credentials">
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="clientId">
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="secretKey">
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>    
        </args>
    </endpoint>
</scheme>
"""

def do_validate():
    config = get_validation_config() 

# Stores the password or client secret in encrypted form in passwords.conf
def set_credentials(session_key, server_uri, realm, stanza_name, password, app):
    cred_manager = cred.CredentialManager(session_key, server_uri)
    if cred_manager.get_encrypted_password(realm, stanza_name, app, log_exception=False) is None:
        cred_manager.create(realm, stanza_name, password, app)
    else:
        cred_manager.update(realm, stanza_name, password, app)

# Retrieves the encrypted password or client secret from passwords.conf in clear text format.
def get_credentials(session_key, server_uri, realm, stanza_name, app):
    cred_manager = cred.CredentialManager(session_key, server_uri)
    return cred_manager.get_clear_password(realm, stanza_name, app)

# Masks the clear text password or client secret in inputs.conf as per Splunk best practices
def mask_credentials(session_key, server_uri, stanza_name, mask,endpoint):
    path = server_uri + "/services/data/inputs/" + stanza_name.split("://")[0] + "/" +\
        urllib.parse.quote(stanza_name.split("://")[1], safe="")
    rsp, content = rest.simpleRequest(path, method='GET', sessionKey=session_key, raiseAllErrors=True)
    data = rest.format.parseFeedDocument(content)
    content = data[0].toPrimitive()
    app_name = content['eai:acl']['app']
    path = server_uri + "/servicesNS/nobody/" + app_name + "/properties/inputs/" + urllib.parse.quote(stanza_name, safe="")
    if endpoint == "/v4/api/policies":
        rest.simpleRequest(path, method='POST', sessionKey=session_key, postargs={"secretKey": mask}, raiseAllErrors=True)
    if endpoint == "/v2/api/customer/dnsQueryLog/stream":
        rest.simpleRequest(path, method='POST', sessionKey=session_key, postargs={"siem_credentials": mask}, raiseAllErrors=True)

# Takes input parameters from inputs.conf stanza , builds EndpointURL and make the REST connection to fetch data from BlueCat DNS Edge server
def do_run():
    config = get_input_config()

    stanza_name = config.get("name")
    endpoint = config.get("endpoint")
    server_uri = config.get("server_uri")
    session_key = config.get("session_key")
    dns_server = config.get("dns_server")
    siem_credentials = config.get("siem_credentials")
    clientId = config.get("clientId")
    secretKey = config.get("secretKey")
    etag = ""
    response_type = "json"
    request_timeout = 230 
    req_args = {}

    if endpoint == "/v1/api/customer/dnsQueryLog/stream":
        if siem_credentials is not None:
            try:
                set_credentials(session_key, server_uri, APP, stanza_name.split("://")[1], siem_credentials, APP)
            except Exception as e:
                logging.error(" Error while setting SIEM credentials for BlueCat DNS Edge Server%s" % str(e))
            try:
                mask_credentials(session_key, server_uri, stanza_name, "",endpoint)
            except Exception as e:
                logging.error("Error while masking SIEM credentials for BlueCat DNS Edge Server: %s" % str(e))
        else:
            siem_credentials = get_credentials(session_key, server_uri, APP, stanza_name.split("://")[1], APP)
            if siem_credentials is None:
                logging.error("Error while getting  SIEM credentials for BlueCat DNS Edge Server: No Credential received")
        headers = {'content-type' : "application/json", "Authorization": "Basic " + siem_credentials }
    if endpoint == "/v2/api/customer/dnsQueryLog/stream":
        if siem_credentials is not None:
            try:
                set_credentials(session_key, server_uri, APP, stanza_name.split("://")[1], siem_credentials, APP)
            except Exception as e:
                logging.error(" Error while setting SIEM credentials for BlueCat DNS Edge Server%s" % str(e))
            try:
                mask_credentials(session_key, server_uri, stanza_name, "",endpoint)
            except Exception as e:
                logging.error("Error while masking SIEM credentials for BlueCat DNS Edge Server: %s" % str(e))
        else:
            siem_credentials = get_credentials(session_key, server_uri, APP, stanza_name.split("://")[1], APP)
            if siem_credentials is None:
                logging.error("Error while getting  SIEM credentials for BlueCat DNS Edge Server: No Credential received")         
        try:
            etag = get_credentials(session_key, server_uri, APP, "etag", APP)
        except:
            pass
        headers = {'content-type' : "application/json", 'accept-encoding' : "gzip;q=0,deflate,sdch", "Authorization": "Basic " + siem_credentials, "ETag" : etag}
        req_args["stream"] = True
    if endpoint == "/v4/api/policies":
        if secretKey is not None:
            try:
                set_credentials(session_key, server_uri, APP, stanza_name.split("://")[1], secretKey, APP)
            except Exception as e:
                logging.error(" Error while setting client secret for BlueCat DNS Edge Server%s" % str(e))
            try:
                mask_credentials(session_key, server_uri, stanza_name, "",endpoint)
            except Exception as e:
                logging.error("Error while masking client secret for BlueCat DNS Edge Server: %s" % str(e))
        else:
            secretKey = get_credentials(session_key, server_uri, APP, stanza_name.split("://")[1], APP)
            if secretKey is None:
                logging.error("Error while getting client secret for BlueCat DNS Edge Server: No client secret received")
        auth_args = {}
        params = {
            "grantType": "ClientCredentials",
            "clientCredentials": {
                "clientId": clientId,
                "clientSecret": secretKey
            }
        }
        headers = {'content-type' : "application/json"}
        auth_args["headers"] = headers
        auth_args["data"] = json.dumps(params)
        auth_args["verify"] = False
        auth_url = "https://api-"+ dns_server + "/v1/api/authentication/token"

        try:
            r = requests.post(auth_url,**auth_args)
            r.raise_for_status()
        except Exception as e:
            logger.error("Received Error : %s for URL %s" % (str(e), auth_url))
            raise
        response =  json.loads(r.text)
        token = response["accessToken"]
        headers = {"Authorization": "Bearer " + token}

    url = "https://api-" + dns_server + endpoint
    req_args["timeout"] = float(request_timeout)
    req_args["headers"] = headers
    req_args["verify"] = False
    try:
        r = requests.get(url,**req_args)
        r.raise_for_status()
    except Exception as e:
        logger.error("Received Error : %s for URL %s" % (str(e), url))
        raise
    if endpoint == "/v2/api/customer/dnsQueryLog/stream":
        try:
            etag = r.headers["etag"]
            set_credentials(session_key, server_uri, APP, "etag", etag, APP)
        except Exception as e:
            pass
    response_handler_instance = BlueCatResponseHandler()
    handle_output(response_handler_instance, r ,response_type,dns_server, endpoint)

#Invokes the appropriate Response Handler for sending output to Splunk index
def handle_output(response_handler_instance, output,type,dns_server, endpoint):
    try:
        response_handler_instance(output,type,dns_server,endpoint)
        sys.stdout.flush()
    except RuntimeError as e:
        logger.error("Looks like an error while handling the response : %s for URL %s" % (str(e), url))

# Prints Usage in case of invalid Script execution method
def usage():
    print("usage: %s [--scheme|--validate-arguments]")
    logger.error("BlueCat DNS Edge Modular Input : Incorrect Program Usage")
    sys.exit(2)

# Introspection
def do_scheme():
    print(SCHEME)

#read XML configuration passed from splunkd.
def get_input_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = minidom.parseString(config_str)
        root = doc.documentElement

        session_key_node = root.getElementsByTagName("session_key")[0]
        if session_key_node and session_key_node.firstChild and session_key_node.firstChild.nodeType == session_key_node.firstChild.TEXT_NODE:
            data = session_key_node.firstChild.data
            config["session_key"] = data

        server_uri_node = root.getElementsByTagName("server_uri")[0]
        if server_uri_node and server_uri_node.firstChild and server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:
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


    except Exception as e:
        raise_(Exception, "Error getting Splunk configuration via STDIN: %s" % str(e))
    return config


#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = minidom.parseString(val_str)
    root = doc.documentElement
    item_node = root.getElementsByTagName("item")[0]
    if item_node:

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data
  



if __name__ == '__main__': 
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":           
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
        else:
            usage()
    else:
        do_run()
        
    sys.exit(0)
