'''
Splunk Modular Input for polling data from Rundeck REST endpoints

This module is the main entry point for Modular Input execution

June 2018

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Rundeck, Inc. ( www.rundeck.com )
'''

import sys,logging,os,time,re,threading,hashlib,json
import xml.dom.minidom
from datetime import datetime
import requests
from requests.utils import quote
from splunklib.client import connect
from splunklib.client import Service
from splunklib.results import ResultsReader
from croniter import croniter
import splunk.entity as entity
from logging.handlers import TimedRotatingFileHandler
from urlparse import urlparse

global myapp
myapp = 'rundeck_app'

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var/log/splunk/rundeck_app_modularinput.log")

# Set up a specific logger
logger = logging.getLogger('Rundeck')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

SCHEME = """<scheme>
    <title>Rundeck</title>
    <description>Poll data from Rundeck REST endpoints</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>
            <arg name="name">
                <title>Rundeck input name</title>
                <description>Name of this Rundeck input</description>
            </arg>
            <arg name="https_api_host">
                <title>Rundeck host</title>
                <description>Your Rundeck host or a comma delimited list of hosts  , ie: foo.myrundeck.com</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="endpoint">
                <title>Endpoint</title>
                <description>REST endpoint with tokens for dynamic properties. Current tokens supported are $api_version$ and $project$</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="endpoint_state">
                <title>Endpoint State</title>
                <description>used internally to read/persist state of endpoints , could use KV store also , buit that is overkill for our very simple state management requirements</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="backfill">
                <title>Backfill</title>
                <description>Whether or not to backfill the entire history (1) or just start from now (0)</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="log_level">
                <title>Log Level</title>
                <description>Logging level (info, error, debug etc..)</description>
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
                <description>Interval time in seconds or a standard CRON pattern to poll the endpoint</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="sequential_mode">
                <title>Sequential Mode</title>
                <description>Whether multiple requests spawned by tokenization are run in parallel or sequentially</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="sequential_stagger_time">
                <title>Sequential Stagger Time</title>
                <description>An optional stagger time period between sequential requests</description>
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

def error_string(e):
    return re.sub("oauth_token=[0-9A-Za-z]+","oauth_token=********************************",str(e))

def get_current_datetime_for_cron():
    current_dt = datetime.now()
    #dont need seconds/micros for cron
    current_dt = current_dt.replace(second=0, microsecond=0)
    return current_dt

def do_validate():
    config = get_validation_config()
    #TODO
    #if error , print_validation_error & sys.exit(2)

def get_authtoken(session_key,host):

   try:
       logger.info("%s : Getting Rundeck auth token from secure Splunk storage" % STANZA)
       args = {'host':'localhost','port':SPLUNK_PORT,'token':session_key,'app':myapp,'owner':'nobody'}
       service = Service(**args)
       storage_passwords = service.storage_passwords
       retrievedCredential = [k for k in storage_passwords if k.content.get('username')==host][0]
       if retrievedCredential is None:
           raise Exception("No auth token was found, have you setup the Rundeck App yet ?")
       else:
           return retrievedCredential.clear_password

   except Exception, e:
      raise Exception("Could not get Rundeck auth token from Splunk. Error: %s"
                      % (myapp, error_string(e)))

def do_run(config,endpoint_list,sequential_mode):

    #parse input params

    #Delimiter to use for any multi "key=value" field inputs
    global delimiter
    delimiter=config.get("delimiter",",")

    http_header_propertys={}
    http_header_propertys_str=config.get("http_header_propertys")
    if not http_header_propertys_str is None:
        http_header_propertys = dict((k.strip(), v.strip()) for k,v in
              (item.split('=',1) for item in http_header_propertys_str.split(delimiter)))

    url_args={}
    url_args_str=config.get("url_args")
    if not url_args_str is None:
        url_args = dict((k.strip(), v.strip()) for k,v in
              (item.split('=',1) for item in url_args_str.split(delimiter)))

    url_args['authtoken'] = ''

    http_proxy=config.get("http_proxy")
    https_proxy=config.get("https_proxy")

    proxies={}

    if not http_proxy is None:
        proxies["http"] = http_proxy
    if not https_proxy is None:
        proxies["https"] = https_proxy

    request_timeout=int(config.get("request_timeout",30))

    backoff_time=int(config.get("backoff_time",10))

    sequential_stagger_time  = int(config.get("sequential_stagger_time",0))

    polling_interval_string = config.get("polling_interval","60")

    if polling_interval_string.isdigit():
        polling_type = 'interval'
        polling_interval=int(polling_interval_string)
    else:
        polling_type = 'cron'
        cron_start_date = datetime.now()
        cron_iter = croniter(polling_interval_string, cron_start_date)

    index_error_response_codes=int(config.get("index_error_response_codes",0))

    backfill=int(config.get("backfill",0))

    response_filter_pattern=config.get("response_filter_pattern")

    if response_filter_pattern:
        REGEX_PATTERN = re.compile(response_filter_pattern)

    response_handler_args={}
    response_handler_args_str=config.get("response_handler_args")
    if not response_handler_args_str is None:
        response_handler_args = dict((k.strip(), v.strip()) for k,v in
              (item.split('=',1) for item in response_handler_args_str.split(delimiter)))

    response_handler=config.get("response_handler","RundeckJSONHandler")
    module = __import__("responsehandlers")
    class_ = getattr(module,response_handler)

    #pass a service object to response handlers if they need it
    args = {'host':'localhost','port':SPLUNK_PORT,'token':SESSION_TOKEN,'app':myapp,'owner':'nobody'}
    service = Service(**args)

    global RESPONSE_HANDLER_INSTANCE
    RESPONSE_HANDLER_INSTANCE = class_(service,logger,**response_handler_args)

    try:

        req_args = {"verify" : False ,"stream" : False , "timeout" : float(request_timeout)}

        if url_args:
            req_args["params"]= url_args
        if http_header_propertys:
            req_args["headers"]= http_header_propertys
        if proxies:
            req_args["proxies"]= proxies

        while True:

            if polling_type == 'cron':
                next_cron_firing = cron_iter.get_next(datetime)
                while get_current_datetime_for_cron() != next_cron_firing:
                    time.sleep(float(10))

            for endpoint in endpoint_list:

                host = get_host(endpoint)

                req_args["params"]["authtoken"] = get_authtoken(SESSION_TOKEN,host)

                try:
                    #restore state if it exists for this endpoint
                    if endpoint in state:
                        for key, val in state[endpoint].items():
                            req_args["params"][key] = val

                    # whether or not to poll from now or backfill for certain endpoints
                    # if there was already a "begin" state from a previous run , this will take precendence
                    if not backfill and not "begin" in req_args["params"] and (endpoint.endswith("executions") or endpoint.endswith("history")):
                        current_millis = int(round(time.time() * 1000))
                        req_args["params"]["begin"] = str(current_millis)

                    logger.info("%s : Sending REST request to %s" % (STANZA,endpoint))
                    r = requests.get(endpoint,**req_args)

                except requests.exceptions.Timeout,e:
                    logger.error("%s : HTTP Request Timeout error: %s" % (STANZA,error_string(e)))
                    time.sleep(float(backoff_time))
                    continue
                except Exception as e:
                    logger.error("%s : Exception performing request: %s" % (STANZA,error_string(e)))
                    time.sleep(float(backoff_time))
                    continue
                try:
                    r.raise_for_status()

                    try:
                        handle_output(r,r.text,state,req_args,endpoint)
                    except Exception as e:
                        logger.error("%s : Exception handling output: %s" % (STANZA,error_string(e)))
                        continue

                except requests.exceptions.HTTPError,e:
                    error_output = r.text
                    error_http_code = r.status_code
                    if index_error_response_codes:
                        error_event=""
                        error_event += 'http_error_code = %s error_message = %s' % (error_http_code, error_output)
                        print_xml_single_instance_mode(error_event)
                        sys.stdout.flush()
                    logger.error("%s : HTTP Request error: %s" % (STANZA,error_string(e)))
                    time.sleep(float(backoff_time))
                    continue

                if sequential_mode and sequential_stagger_time > 0:
                    time.sleep(float(sequential_stagger_time))

            if polling_type == 'interval':
                time.sleep(float(polling_interval))

            #re-evaluate , dynamic token values might have changed
            if sequential_mode:
                #persist state
                update_param("endpoint_state",json.dumps(state))
                endpoint_list = get_endpoint_list(config.get("https_api_host"),config.get("endpoint"))
            else:
                break

    except Exception,e:
        logger.error("%s : Looks like an error: %s" % (STANZA,error_string(e)))
        sys.exit(2)
    except:
        e = sys.exc_info()[0]
        logger.error("%s : Looks like an error: %s" % (STANZA,error_string(e)))
        sys.exit(2)

#pull the host part out of a URI
def get_host(endpoint):
    parsed_uri = urlparse(endpoint)
    host = '{uri.netloc}'.format(uri=parsed_uri)
    return host

def replaceTokens(raw_string):

    try:
        url_list = [raw_string]
        substitution_tokens = re.findall("\$(?:\w+)\$",raw_string)
        for token in substitution_tokens:
            token_response = getattr(sys.modules[__name__],'token_'+token[1:-1])(get_host(raw_string))
            if(isinstance(token_response,list)):
                temp_list = []
                for token_response_value in token_response:
                    for url in url_list:
                        temp_list.append(url.replace(token,token_response_value))
                url_list = temp_list
            else:
                for index,url in enumerate(url_list):
                    url_list[index] = url.replace(token,token_response)
        return url_list
    except:
        e = sys.exc_info()[1]
        logger.error("%s : Looks like an error substituting tokens: %s" % (STANZA,error_string(e)))

def token_project(host):

    project_list=[]

    try:

        args = {'host':'localhost','port':SPLUNK_PORT,'token':SESSION_TOKEN,'app':myapp,'owner':'nobody'}
        service = Service(**args)
        jobs = service.jobs

        # Run a blocking search
        kwargs_blockingsearch = {"exec_mode": "blocking"}
        searchquery_blocking = "`rundeck_project_names(%s)`" % host

        job = jobs.create(searchquery_blocking, **kwargs_blockingsearch)
        result_stream = job.results()
        reader = ResultsReader(result_stream)
        for item in reader:
            for key, value in item.items():
                if key == "project_name":
                    project_list.append(value)
        return project_list
    except Exception,e:
        logger.error("%s : Error executing search to get list of projects : %s" % (STANZA,error_string(e)))
        return project_list

def token_api_version(host):

    #default minimum
    api_version = "18"

    try:

        args = {'host':'localhost','port':SPLUNK_PORT,'token':SESSION_TOKEN,'app':myapp,'owner':'nobody'}
        service = Service(**args)
        jobs = service.jobs

        # Run a blocking search
        kwargs_blockingsearch = {"exec_mode": "blocking"}
        searchquery_blocking = "`rundeck_host_info(%s)`" % host

        job = jobs.create(searchquery_blocking, **kwargs_blockingsearch)
        result_stream = job.results()
        reader = ResultsReader(result_stream)
        for item in reader:
            for key, value in item.items():
                if key == "api_version":
                    api_version = str(value)
        return api_version
    except Exception,e:
        logger.error("%s : Error executing search to get api version : %s" % (STANZA,error_string(e)))
        return api_version

def token_auth_token(host):
    try:

        return get_authtoken(SESSION_TOKEN,host)

    except Exception,e:
        logger.error("%s : Error executing search to get auth token : %s" % (STANZA,error_string(e)))
        return api_version

def update_param(rest_name,rest_value):

    try:
        args = {'host':'localhost','port':SPLUNK_PORT,'token':SESSION_TOKEN,'app':myapp,'owner':'nobody'}
        service = Service(**args)
        item = service.inputs.__getitem__(STANZA[10:])
        item.update(**{rest_name:rest_value})
    except Exception,e:
        logging.error("%s : Looks like an error updating the modular input parameter %s: %s" % (STANZA,rest_name,error_string(e)))

def handle_output(response,output,type,req_args,endpoint):

    try:
        logger.info("Processing Endpoint Response JSON")
        if REGEX_PATTERN:
            search_result = REGEX_PATTERN.search(output)
            if search_result == None:
                return
        RESPONSE_HANDLER_INSTANCE(response,output,type,req_args,endpoint)
        sys.stdout.flush()
    except Exception,e:
        logger.error("%s : Looks like an error handle the response output: %s" % (STANZA,error_string(e)))

# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print "<error><message>%s</message></error>" % encodeXMLText(s)

# prints XML stream
def print_xml_single_instance_mode(s):
    print "<stream><event><data>%s</data></event></stream>" % encodeXMLText(s)

# prints simple stream
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
    logger.error("%s : Incorrect Program Usage" % STANZA)
    sys.exit(2)

def do_scheme():
    print SCHEME

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

            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:

                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")

                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % error_string(e)

    return config

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
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

def get_endpoint_list(host_property,endpoint):
    endpoint_list = []
    for host in host_property.split(','):
        original_endpoint='https://'+host+endpoint
        #token replacement
        logger.info("%s : Performing token replacement" % STANZA)
        endpoint_list.extend(replaceTokens(original_endpoint))

    #prune deadwood from state table
    for key,val in state.items():
        if not key in endpoint_list:
            del state[key]

    return endpoint_list

if __name__ == '__main__':

    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            logger.info("Getting Rundeck Modular Input scheme")
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            logger.info("Performing Rundeck Modular Input validation")
            do_validate()
        else:
            usage()
    else:
        config = get_input_config()

        #change log level from configuration stanza if present
        log_level = logging.getLevelName(config.get("log_level","INFO"))
        logger.setLevel(log_level)

        server_uri = config.get("server_uri")

        #setup some globals

        global SPLUNK_PORT
        global STANZA
        global SESSION_TOKEN
        global REGEX_PATTERN

        REGEX_PATTERN = None
        SPLUNK_PORT = server_uri[18:]
        STANZA = config.get("name")
        SESSION_TOKEN = config.get("session_key")

        endpoint_state = config.get("endpoint_state")
        global state
        state = {}
        try:
            if not endpoint_state is None:
              state = json.loads(endpoint_state)
        except Exception,e:
            logger.error("%s : Error loading the endpoint state: %s" % (STANZA,error_string(e)))

        #host property might be a single host or a comma delimited list of hosts
        endpoint_list = get_endpoint_list(config.get("https_api_host"),config.get("endpoint"))

        sequential_mode=int(config.get("sequential_mode",0))

        #wait until we have some endpoints
        while len(endpoint_list) == 0:
            logger.info("%s : No endpoints available yet ,waiting 30 seconds before trying again" % STANZA)
            time.sleep(30)
            endpoint_list = get_endpoint_list(config.get("https_api_host"),config.get("endpoint"))

        try:
            if bool(sequential_mode):
                logger.info("%s : Running in sequential mode" % STANZA)
                do_run(config,endpoint_list,True)
            else:
                #execute multiple threads in parallel mode
                logger.info("%s : Running in parallel mode" % STANZA)

                while True:
                    threads = []

                    for endpoint in endpoint_list:
                        requester = threading.Thread(target=do_run, args=(config,[endpoint],False))
                        threads.append(requester)
                    #run all the threads
                    for t in threads:
                        t.start()
                    #wait for all threads to complete
                    for t in threads:
                        t.join()
                    #persist state
                    update_param("endpoint_state",json.dumps(state))
                    #flush/reset the auth token cache

                    #re-evaluate , dynamic token values might have changed
                    endpoint_list = get_endpoint_list(config.get("https_api_host"),config.get("endpoint"))
                    if len(endpoint_list) == 0:
                        time.sleep(30)

        except Exception,e:
            logger.error("%s : Looks like an error in the do_run() method: %s" % (STANZA,error_string(e)))
            sys.exit(2)

    sys.exit(0)
