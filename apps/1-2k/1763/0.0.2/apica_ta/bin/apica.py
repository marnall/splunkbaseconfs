
import sys,logging,os,time,re
import xml.dom.minidom

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

RESPONSE_HANDLER_INSTANCE = None
SPLUNK_PORT = 8089
STANZA = None
SESSION_TOKEN = None
REGEX_PATTERN = None

#dynamically load in any eggs in the config dir. See the Splunk snmp_ta example for more details...
EGG_DIR = SPLUNK_HOME + "/etc/apps/apica/bin/"

for filename in os.listdir(EGG_DIR):
    if filename.endswith(".egg"):
        sys.path.append(EGG_DIR + filename) 
       
import requests,json
from requests.auth import HTTPBasicAuth
from requests.auth import HTTPDigestAuth
from requests_oauthlib import OAuth1
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import WebApplicationClient 
from requests.auth import AuthBase
from splunklib.client import connect
from splunklib.client import Service
           
logging.root
logging.root.setLevel(logging.ERROR)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

SCHEME = """<scheme>
    <title>Apica</title>
    <description>Integrator for polling data from the Apica WPM endpoints</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>WPM check input name</title>
                <description>The Splunk name to be used to refer to this WPM check</description>
            </arg>
                   
            <arg name="endpoint">
                <title>WPM check endpoint URL</title>
                <description>URL to use for the check query. The base URL for all WPM checks should be: http://api-wpm.apicasystem.com/v3/ </description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="http_method">
                <title>Check HTTP Operation/Method</title>
                <description>The HTTP method to use. Defaults to GET which. POST and PUT are also supported through the API (http://api-wpm.apicasystem.com/v3/help) however push operations are not currently supported from this app. If you have a need for such capability please contact the OI team.  </description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="auth_type">
                <title>Authentication Type</title>
                <description>Authentication method to use : basic | none. Apica WPM requires basic auth for the majority of inspection calls.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="auth_user">
                <title>Apica WPM user name</title>
                <description>Authentication user for basic auth</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="auth_password">
                <title>Apica WPM API user password</title>
                <description>Authentication password for basic auth</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="http_proxy">
                <title>HTTP Proxy Address</title>
                <description>HTTP Proxy Address</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="https_proxy">
                <title>HTTPs Proxy Address</title>
                <description>HTTPs Proxy Address</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="request_timeout">
                <title>Request Timeout</title>
                <description>Time in seconds to use for request timeout, defaults to 30</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="backoff_time">
                <title>Post error retry time</title>
                <description>Time in seconds to wait for retry after error or timeout, defaults to 30</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="polling_interval">
                <title>Polling interval</title>
                <description>Time in seconds to poll the Apica URL endpoint, defaults to 60</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_validate():
    config = get_validation_config()

def do_run():

    config = get_input_config() 

    server_uri = config.get("server_uri")
    global SPLUNK_PORT
    global STANZA
    global SESSION_TOKEN
    SPLUNK_PORT = server_uri[18:]
    STANZA = config.get("name")
    SESSION_TOKEN = config.get("session_key")


    endpoint=config.get("endpoint")
    http_method=config.get("http_method","GET")
    auth_type=config.get("auth_type","none")
    auth_user=config.get("auth_user")
    auth_password=config.get("auth_password")
    response_type="json"
    streaming_request=0


    http_proxy=config.get("http_proxy")
    https_proxy=config.get("https_proxy")

    proxies={}

    if not http_proxy is None:
        proxies["http"] = http_proxy
    if not https_proxy is None:
        proxies["https"] = https_proxy


    request_timeout=int(config.get("request_timeout",30))
    backoff_time=int(config.get("backoff_time",30))
    polling_interval=int(config.get("polling_interval",60))
    response_filter_pattern=None


    if response_filter_pattern:
        global REGEX_PATTERN
        REGEX_PATTERN = re.compile(response_filter_pattern)

    response_handler_args={}
    response_handler_args_str=None
    response_handler="DefaultResponseHandler"

    module = __import__("responsehandlers")
    class_ = getattr(module,response_handler)

    global RESPONSE_HANDLER_INSTANCE
    RESPONSE_HANDLER_INSTANCE = class_(**response_handler_args)


    try:
        auth=None
        if auth_type == "basic":
            auth = HTTPBasicAuth(auth_user, auth_password)

        req_args = {"verify" : False ,"stream" : bool(streaming_request) , "timeout" : float(request_timeout)}

        if auth:
            req_args["auth"]= auth
        if proxies:
            req_args["proxies"]= proxies

        while True:

            if "params" in req_args:
                req_args_params_current = dictParameterToStringFormat(req_args["params"])
            else:
                req_args_params_current = ""
            if "headers" in req_args:
                req_args_headers_current = dictParameterToStringFormat(req_args["headers"])
            else:
                req_args_headers_current = ""
            if "data" in req_args:
                req_args_data_current = req_args["data"]
            else:
                req_args_data_current = ""

            try:
              if http_method == "GET":
                  r = requests.get(endpoint,**req_args)

            except requests.exceptions.Timeout,e:
                logging.error("HTTP Request Timeout error: %s" % str(e))
                time.sleep(float(backoff_time))
                continue
            except Exception as e:
                logging.error("Exception performing request: %s" % str(e))
                time.sleep(float(backoff_time))
                continue
            try:
                r.raise_for_status()
                if streaming_request:
                    for line in r.iter_lines():
                        if line:
                            handle_output(r,line,response_type,req_args,endpoint)
                else:
                    handle_output(r,r.text,response_type,req_args,endpoint)
            except requests.exceptions.HTTPError,e:
                error_output = r.text
                error_http_code = r.status_code
                logging.error("HTTP Request error: %s" % str(e))
                time.sleep(float(backoff_time))
                continue

            time.sleep(float(polling_interval))

    except RuntimeError,e:
        logging.error("Looks like an error: %s" % str(e))
        sys.exit(2) 
     
def checkParamUpdated(cached,current,rest_name):
    
    if not (cached == current):
        try:
            args = {'host':'localhost','port':SPLUNK_PORT,'token':SESSION_TOKEN}
            service = Service(**args)   
            item = service.inputs.__getitem__(STANZA[7:])
            item.update(**{rest_name:current})
        except RuntimeError,e:
            logging.error("Looks like an error updating the modular input parameter %s: %s" % (rest_name,str(e),))   
        
                       
def dictParameterToStringFormat(parameter):
    
    if parameter:
        return ''.join('{}={},'.format(key, val) for key, val in parameter.items())[:-1] 
    else:
        return None

            
def handle_output(response,output,type,req_args,endpoint): 
    
    try:
        if REGEX_PATTERN:
            search_result = REGEX_PATTERN.search(output)
            if search_result == None:
                return   
        RESPONSE_HANDLER_INSTANCE(response,output,type,req_args,endpoint)
        sys.stdout.flush()               
    except RuntimeError,e:
        logging.error("Looks like an error handle the response output: %s" % str(e))

def print_validation_error(s):
    print "<error><message>%s</message></error>" % encodeXMLText(s)
    
def print_xml_single_instance_mode(s):
    print "<stream><event><data>%s</data></event></stream>" % encodeXMLText(s)
    
def print_simple(s):
    print "%s\n" % s

def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text
  
def usage():
    print "usage: %s [--scheme|--validate-arguments]"
    logging.error("Incorrect Program Usage")
    sys.exit(2)

def do_scheme():
    print SCHEME

def get_input_config():
    config = {}

    try:
        config_str = sys.stdin.read()

        doc = xml.dom.minidom.parseString(config_str)
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
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

def get_validation_config():
    val_data = {}

    val_str = sys.stdin.read()

    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logging.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logging.debug("XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logging.debug("Found param %s" % name)
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
