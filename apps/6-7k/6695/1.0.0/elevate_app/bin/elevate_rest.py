'''
Modular Input for polling the Elevate REST API

October 2022

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Elevate Security
'''

import sys,logging,os,time,re
import xml.dom.minidom
from datetime import datetime
import requests,json
from splunklib.client import connect
from splunklib.client import Service
from croniter import croniter
import splunk.entity as entity
from logging.handlers import TimedRotatingFileHandler
           
requests.packages.urllib3.disable_warnings()

#environment variables
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#used for processing requests
RESPONSE_HANDLER_INSTANCE = None
STANZA = None
REGEX_PATTERN = None
DELIMITER = None

#app naming constants
APP_NAME = "elevate_app"
CONF_FILE = "elevate"
STANZA_NAME = "elevate_settings"

#HTTP Header constants
HTTP_HEADER_API_KEY = "X-API-KEY"
HTTP_HEADER_TENANT = "X-Tenant"

#for connecting to the Splunk REST API
SESSION_TOKEN = None
SPLUNK_SERVICE = None

#for interacting with the elevate.conf file
CONF_STANZA = None
CONF_STANZA_OBJECT = None

#default management port/host , but may be different sometimes
SPLUNK_PORT = 8089 
SPLUNK_HOST = "localhost"

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","elevate_modularinput.log")

# Set up a specific logger
logger = logging.getLogger('elevate_rest_modinput')
logger.propagate = False

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

SCHEME = """<scheme>
    <title>Elevate REST</title>
    <description>Elevate REST API input</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>Elevate REST input name</title>
                <description>Name of this REST input</description>
            </arg>     
            <arg name="endpoint">
                <title>API Endpoint</title>
                <description>API Endpoint to send the HTTP GET request to</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            
            <arg name="verify">
                <title>Enable Verification of SSL Certificates ?</title>
                <description>Enable this to verify Server and Client Certificates using the default bundled "certifi" CA Bundle , values are 0 for false | 1 for true , https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="ca_bundle_path">
                <title>Certificate Authority Bundle Path</title>
                <description>Full path to your CA Bundle if you don't want to use the default bundled "certifi" CA Bundle ie: /path/to/cacert.pem, https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="client_cert_path">
                <title>Client Certificate</title>
                <description>Full path to your client certificate ie: /path/to/client.crt</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="client_key_path">
                <title>Client Unencrypted Private Key</title>
                <description>Full path to your unencrypted private key ie: /path/to/client.key</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="client_bundled_path">
                <title>Bundled Client Certificate/Unencrypted Private Key</title>
                <description>Alternatively to declaring your certificate and key seperately above , you can enter the full path to your bundled client certificate/unencrypted private key file ie: /path/to/client.pem</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="http_header_propertys">
                <title>HTTP Header Propertys</title>
                <description>Custom HTTP header propertys : key=value,key2=value2</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="url_args">
                <title>URL Arguments</title>
                <description>Custom URL arguments : key=value,key2=value2</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="streaming_request">
                <title>Streaming Request</title>
                <description>Whether or not this is a HTTP streaming request : true | false</description>
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
                <description>Request Timeout in seconds</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="backoff_time">
                <title>Backoff Time</title>
                <description>Time in seconds to wait for retry after error or timeout</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="polling_interval">
                <title>Polling Interval</title>
                <description>Interval time in seconds to poll the endpoint</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            
            <arg name="delimiter">
                <title>Delimiter</title>
                <description>Delimiter to use for any multi "key=value" field inputs</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="index_error_response_codes">
                <title>Index Error Responses</title>
                <description>Whether or not to index error response codes : true | false</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="response_handler">
                <title>Response Handler</title>
                <description>Python classname of custom response handler</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="response_handler_args">
                <title>Response Handler Arguments</title>
                <description>Response Handler arguments string ,  key=value,key2=value2</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="response_filter_pattern">
                <title>Response Filter Pattern</title>
                <description>Python Regex pattern, if present , responses must match this pattern to be indexed</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            
        </args>
    </endpoint>
</scheme>
"""

def get_current_datetime_for_cron():
    current_dt = datetime.now()
    #dont need seconds/micros for cron
    current_dt = current_dt.replace(second=0, microsecond=0)
    return current_dt
            
def do_validate():
    config = get_validation_config() 


def get_credentials():
   
   try:
      # list all credentials
      entities = entity.getEntities(['storage', 'passwords'], namespace=APP_NAME ,count=0,
                                    owner='nobody', sessionKey=SESSION_TOKEN)
   except Exception as e:
      logger.error("Could not get credentials from Splunk. Error: %s" % str(e))
      return {}

   return entities.items()


def do_run(config):
    
    global STANZA
    global SESSION_TOKEN 
    global DELIMITER

    STANZA = config.get("name")

    logger.info("%s : Executing Elevate REST Modular Input" % STANZA)

    SESSION_TOKEN = config.get("session_key")

    logger.info("Getting the Splunk management port and host")

    server_settings = entity.getEntity('/server','settings', namespace=APP_NAME, owner='nobody', sessionKey=SESSION_TOKEN)

    SPLUNK_PORT = server_settings['mgmtHostPort']
    SPLUNK_HOST = server_settings['host']

    logger.info("Port %s " % SPLUNK_PORT)
    logger.info("Host %s " % SPLUNK_HOST)

    logger.info("Getting the Splunk SDK Service")

    service_args = {'host':SPLUNK_HOST,'port':SPLUNK_PORT,'token':SESSION_TOKEN,'owner':'nobody','app':APP_NAME,'sharing':'global'}
    SPLUNK_SERVICE = Service(**service_args)  

 
    logger.info("Reading in the settings stanza from elevate.conf")
 
    
    CONF_STANZA_OBJECT = SPLUNK_SERVICE.confs[CONF_FILE][STANZA_NAME]

    #prune out None values so our defaults kick in
    CONF_STANZA = {k: v for k, v in CONF_STANZA_OBJECT.content().items() if v is not None}

    #update log level with the global app level
    log_level = logging.getLevelName(CONF_STANZA .get("log_level","INFO"))
    logger.setLevel(log_level)
    
    logger.info("Building the Elevate URL")

    api_host = CONF_STANZA .get("api_host","api.elevatesecurity.com")
    endpoint=config.get("endpoint")

    if endpoint is None:
        logger.error("No REST Endpoint has been set")
        return

    endpoint = "https://"+api_host+endpoint

    logger.info("Elevate URL is %s " % endpoint)

    logger.info("Getting the Elevate API Key and Tenant ID")

    tenant_id = CONF_STANZA .get("tenant_id",None)

    if tenant_id is None:
        logger.error("No Tenant ID has been set")
        return

    api_key = None
    credentials_list = get_credentials()
 
    for i, c in credentials_list:

        if c['eai:acl']['app'] ==  APP_NAME:
            username =  c['username']
            clear_password = c['clear_password']
            if username == tenant_id:
                api_key = clear_password
    
    if api_key is None:
        logger.error("No API Key has been set")
        return
    
            
    #Delimiter to use for any multi "key=value" field inputs
    DELIMITER=config.get("delimiter",",")  
          
    http_header_propertys={}
    http_header_propertys_str=config.get("http_header_propertys")
    if not http_header_propertys_str is None:
        http_header_propertys = dict((k.strip(), v.strip()) for k,v in 
              (item.split('=',1) for item in http_header_propertys_str.split(DELIMITER)))

    logger.info("Adding the Elevate API Key and Tenant ID to the HTTP request headers")

    http_header_propertys[HTTP_HEADER_API_KEY] = api_key
    http_header_propertys[HTTP_HEADER_TENANT] = tenant_id
    http_header_propertys["Content-Type"] = "application/json"
    
       
    url_args={} 
    url_args_str=config.get("url_args")
    if not url_args_str is None:
        url_args = dict((k.strip(), v.strip()) for k,v in 
              (item.split('=',1) for item in url_args_str.split(DELIMITER)))       
    
    streaming_request=int(config.get("streaming_request",0))
    
    https_proxy=config.get("https_proxy")
    
    proxies={}
       
    if not https_proxy is None:
        proxies["https"] = https_proxy 
        
         
    request_timeout=int(config.get("request_timeout",30))
    
    backoff_time=int(config.get("backoff_time",10))
    
    
    polling_interval_string = config.get("polling_interval","60")
    
    if polling_interval_string.isdigit():
        polling_type = 'interval'
        polling_interval=int(polling_interval_string)   
    else:
        polling_type = 'cron'
        cron_start_date = datetime.now()
        cron_iter = croniter(polling_interval_string, cron_start_date)
    
    index_error_response_codes=int(config.get("index_error_response_codes",0))
    
    response_filter_pattern=config.get("response_filter_pattern")
    
    if response_filter_pattern:
        global REGEX_PATTERN
        REGEX_PATTERN = re.compile(response_filter_pattern)
        
    response_handler_args={} 
    response_handler_args_str=config.get("response_handler_args")
    if not response_handler_args_str is None:
        response_handler_args = dict((k.strip(), v.strip()) for k,v in 
              (item.split('=',1) for item in response_handler_args_str.split(DELIMITER)))
      
    
    default_response_handler = "DefaultResponseHandler"

    response_handler=config.get("response_handler",default_response_handler)
    module = __import__("responsehandlers")
    class_ = getattr(module,response_handler)

    global RESPONSE_HANDLER_INSTANCE
    RESPONSE_HANDLER_INSTANCE = class_(logger,**response_handler_args)
      
    try: 

        req_args = {"stream" : bool(streaming_request) , "timeout" : float(request_timeout)}

        if url_args:
            req_args["params"]= url_args
        if http_header_propertys:
            req_args["headers"]= http_header_propertys
        if proxies:
            req_args["proxies"]= proxies
        

        verify_ssl=int(config.get("verify",0))
        ca_bundle_path=config.get("ca_bundle_path")
        client_bundled_path=config.get("client_bundled_path")
        client_cert_path=config.get("client_cert_path")
        client_key_path=config.get("client_key_path")

        if verify_ssl:
            if ca_bundle_path:
                req_args["verify"]= ca_bundle_path
            if client_bundled_path:
                req_args["cert"]= client_bundled_path
            elif client_cert_path and client_key_path:
                req_args["cert"]= (client_cert_path,client_key_path)
            else:
                pass           
        else:
            req_args["verify"]= False   

                                              
        while True:
             
            logger.info("%s : Entered Polling Loop" % STANZA)

            if polling_type == 'cron':
                next_cron_firing = cron_iter.get_next(datetime)
                while get_current_datetime_for_cron() != next_cron_firing:
                    logger.info("%s : Sleeping until next CRON firing" % STANZA)
                    time.sleep(float(10))
            
                                    
                  
            logger.info("%s : Executing HTTP Request" % STANZA)
            try:
                r = requests.get(endpoint,**req_args)
                    
            except requests.exceptions.Timeout as e:
                logger.error("%s : HTTP Request Timeout error: %s" % (STANZA,str(e)))
                time.sleep(float(backoff_time))
                continue
            except Exception as e:
                logger.error("%s : Exception performing request: %s" % (STANZA,str(e)))
                time.sleep(float(backoff_time))
                continue
            try:
                r.raise_for_status()
                if streaming_request:
                    for line in r.iter_lines():
                        if line:
                            handle_output(r,line,req_args,endpoint)  
                else:                    
                    handle_output(r,r.text,req_args,endpoint)
            except requests.exceptions.HTTPError as e:
                error_output = r.text
                error_http_code = r.status_code
                if index_error_response_codes:
                    error_event=""
                    error_event += 'http_error_code = %s error_message = %s' % (error_http_code, error_output) 
                    print_xml_single_instance_mode(error_event)
                    sys.stdout.flush()
                logger.error("%s : HTTP Request error: %s Code: %s Message: %s" % (STANZA,str(e),error_http_code, error_output))
                time.sleep(float(backoff_time))
                continue
            
                 
                   
            if polling_type == 'interval': 
                logger.info("%s : Sleeping until next Interval time firing" % STANZA)                        
                time.sleep(float(polling_interval))
            
    except RuntimeError as e:
        logger.error("%s : Looks like an error: %s" % (STANZA,str(e)))
        sys.exit(2) 
                             
            
def handle_output(response,output,req_args,endpoint): 
    
    try:
        if REGEX_PATTERN:
            search_result = REGEX_PATTERN.search(output)
            if search_result == None:
                return 

        RESPONSE_HANDLER_INSTANCE(response,output,req_args,endpoint)
       
        sys.stdout.flush()               
    except RuntimeError as e:
        logger.error("%s : Looks like an error handle the response output: %s" % (STANZA,str(e)))

# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print("<error><message>%s</message></error>" % encodeXMLText(s))
    
# prints XML stream
def print_xml_single_instance_mode(s):
    print("<stream><event><data>%s</data></event></stream>" % encodeXMLText(s))
    
# prints simple stream
def print_simple(s):
    print("%s\n" % s)

def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text
  
def usage():
    print("usage: %s [--scheme|--validate-arguments]")
    logger.error("Incorrect Program Usage")
    sys.exit(2)

def do_scheme():
    print(SCHEME)

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_input_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
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
                            

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception("Invalid configuration received from Splunk.")

        
    except Exception as e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))

    return config

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logger.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logger.debug("XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logger.debug("Found param %s" % name)
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
        config = get_input_config()
        do_run(config)

        
    sys.exit(0)
