'''
Modular Input for Yammer

This provides the means to index different stream from Yammer, such as messages.

Copyright (C) 2013 Denver Water.
http://www.denverwater.org
All Rights Reserved

@author Henri van den Bulk

./splunk cmd splunkd print-modinput-config yammer yammer://Messages | ./splunk cmd python /Users/henivandenbulk/projects/splunk/etc/apps/yammer_ta/bin/yammer.py

'''

import sys,logging,os,time,re
import xml.dom.minidom
    
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

RESPONSE_HANDLER_INSTANCE = None
SPLUNK_PORT = 8089
STANZA = None
SESSION_TOKEN = None
REGEX_PATTERN = None

#dynamically load in any eggs in /etc/apps/snmp_ta/bin
EGG_DIR = SPLUNK_HOME + "/etc/apps/yammer_ta/bin/"
os.environ['REQUESTS_CA_BUNDLE'] = EGG_DIR + '/cacert.pem'

for filename in os.listdir(EGG_DIR):
    if filename.endswith(".egg"):
        sys.path.append(EGG_DIR + filename) 
       
import requests
import json
#from requests_oauthlib import OAuth2Session
#from oauthlib.oauth2 import WebApplicationClient 
#from requests.auth import AuthBase

from splunklib.client import connect
from splunklib.client import Service

import yampy

# Import the specific errors
from yampy.errors import ResponseError, NotFoundError, InvalidAccessTokenError, \
    RateLimitExceededError, UnauthorizedError

#set up logging
logging.root
logging.root.setLevel(logging.ERROR)
#logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
#with zero args , should go to STD ERR

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

SCHEME = """<scheme>
    <title>Yammer</title>
    <description>Poll data from the Yammer REST API</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>Yammer REST API endpoint name</title>
                <description>Name of this Yammer REST API endpoint</description>
            </arg>
                   
            <arg name="yammer_access_token">
                <title>Yammer Access Authentication Token</title>
                <description>Yammer Authentication Token</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>

            <arg name="yammer_api_resource">
                <title>Yammer Resource</title>
                <description>Resource to get from Yammer</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>            
           
            <arg name="yammer_client_id">
                <title>Yammer Client ID</title>
                <description>Client ID for your application defined in Yammer</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="yammer_client_secret">
                <title>Yammer Client Secret</title>
                <description>Yammer Client secret</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>

            <arg name="url_args">
                <title>URL Arguments</title>
                <description>Custom URL arguments : key=value,key2=value2</description>
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
            
        </args>
    </endpoint>
</scheme>
"""

def do_validate():
    config = get_validation_config() 
    #TODO
    #if error , print_validation_error & sys.exit(2) 
    
def do_run():

    logging.info("Starting Yammer input")
    
    config = get_input_config() 
    
    #setup some globals
    server_uri = config.get("server_uri")
    global SPLUNK_PORT
    global STANZA
    global SESSION_TOKEN 
    SPLUNK_PORT = server_uri[18:]
    STANZA = config.get("name")
    SESSION_TOKEN = config.get("session_key")
   
    #params
         
    #access_token=config.get("access_token")
    access_token=config.get("yammer_access_token")  
       
    #oauth2_client_id=config.get("oauth2_client_id")
    #client_secret=config.get("oauth2_client_secret")
    client_id=config.get("yammer_client_id")
    client_secret=config.get("yammer_client_secret")
                 
    url_args={} 
    url_args_str=config.get("url_args")
    if not url_args_str is None:
        url_args = dict((k.strip(), v.strip()) for k,v in 
              (item.split('=') for item in url_args_str.split(";")))
        
    last_yammer_indexed_id = None
    page = 0           

    request_timeout=int(config.get("request_timeout",30))
    
    backoff_time=int(config.get("backoff_time",10))
    
    polling_interval=int(config.get("polling_interval",60))
        
    yammer_api_resource = config.get("yammer_api_resource")
        
    try: 
  
        # Create the client to communicate with Yammer
        #authenticator = yampy.Authenticator(client_id=client_id, client_secret=client_secret)
        yammer = yampy.Yammer(access_token=access_token)

        #client = WebApplicationClient(client_id)
        #oauth2 = OAuth2Session(client, token=token,auto_refresh_url=oauth2_refresh_url,auto_refresh_kwargs=oauth2_refresh_props,token_updater=oauth2_token_updater)
   
        req_args = {"verify" : False, "timeout" : float(request_timeout)}

        if url_args:
            req_args["params"]= url_args
                          
        # Set the last message id based on the settings
        if "newer_than" in req_args:
            last_yammer_indexed_id = req_args["params"]["newer_than"] 
            logging.info("Last Checkpoint=%s", last_yammer_indexed_id)

        if last_yammer_indexed_id:
            req_args["params"]["newer_than"] = last_yammer_indexed_id
                    

        while True:
                        
            if "params" in req_args:
                req_args_params_current = dictParameterToStringFormat(req_args["params"])
            else:
                req_args_params_current = ""
            if "data" in req_args:
                req_args_data_current = req_args["data"]
            else:
                req_args_data_current = ""
             
            try:
                data = None

                if yammer_api_resource == "messages":
                    data = yammer.messages.all(older_than=None, newer_than=last_yammer_indexed_id, limit=None, threaded=None)
                elif yammer_api_resource == "users":
                    
                    data = yammer.users.all(page=page, letter=None, sort_by=None, reverse=None);
                    page += 1
                    if len(data) == 0:
                        page = 1


            except yampy.errors.RateLimitExceededError,e:
                logging.error("Exceeped the Rate: %s" % str(e))
                time.sleep(float(backoff_time))
                continue

            except requests.exceptions.Timeout,e:
                logging.error("HTTP Request Timeout error: %s" % str(e))
                time.sleep(float(backoff_time))
                continue
            except Exception as e:
                logging.error("Exception performing request: %s" % str(e))
                time.sleep(float(backoff_time))
                continue
            try:
                                    
                handle_output(yammer_api_resource, data, req_args)

            except requests.exceptions.HTTPError,e:

                logging.error("HTTP Request error: %s" % str(e))
                time.sleep(float(backoff_time))
                continue
            
            
            if "data" in req_args:   
                checkParamUpdated(req_args_data_current,req_args["data"],"request_payload")
            if "params" in req_args:
                checkParamUpdated(req_args_params_current,dictParameterToStringFormat(req_args["params"]),"url_args")
            if "headers" in req_args:
                checkParamUpdated(req_args_headers_current,dictParameterToStringFormat(req_args["headers"]),"http_header_propertys")
                               
            time.sleep(float(polling_interval))
            
    except RuntimeError,e:
        logging.error("Looks like an error: %s" % str(e))
        sys.exit(2) 
     
def checkParamUpdated(cached,current,rest_name):
    
    if not (cached == current):
        try:
            logging.info("Setting %s" % current)
            args = {'host':'localhost','port':SPLUNK_PORT,'token':SESSION_TOKEN}
            service = Service(**args)   
            item = service.inputs.__getitem__(STANZA[7:])
            item.update(**{rest_name:current})
        except RuntimeError,e:
            logging.error("Looks like an error updating the modular input parameter %s: %s" % (rest_name,str(e),))   
        

def getUserReference(messages, user_id, sender_type="user"):

    for ref in messages.references:
        if ref["id"] == user_id and ref["type"] == sender_type:
            return ref

    return None    

def indexYammerMessages(messages, req_args):

        last_yammer_indexed_id = None
        for yammer_message in messages.messages:

#            if "sender_id" in yammer_message:
                #user = getUser(messages, yammer_message.sender_id, yammer_message.sender_type) 
                #if user:
                #    msg["sender"] = user

            print_xml_stream(json.dumps(yammer_message))
            if "id" in yammer_message:
                message_id = yammer_message["id"]
                if message_id > last_yammer_indexed_id:
                    last_yammer_indexed_id = message_id

        # Dump the reference information
        # for reference in output["references"]:
#        for reference in messages.references:            
#            if reference["type"] == "user":
#                print_xml_stream(json.dumps(reference), "yammer_user")
#            if reference["type"] == "group":
#                print_xml_stream(json.dumps(reference), "yammer_group")

        if not "params" in req_args:
            req_args["params"] = {}

      
        req_args["params"]["newer_than"] = last_yammer_indexed_id

 
def indexYammerUsers(users, req_args):

        for user in users:

            print_xml_stream(json.dumps(user))

        if not "params" in req_args:
            req_args["params"] = {}


def indexYammerFollowing(messages, req_args):

    indexYammerMessages(messages, reg_args)

                       
def dictParameterToStringFormat(parameter):
    
    if parameter:
        return ''.join('{}={},'.format(key, val) for key, val in parameter.items())[:-1] 
    else:
        return None
    
#
#            
def handle_output(resource, data,req_args): 
    """ Handles calling the correct indexing depending on the Yammer resource """  
    try:
        #RESPONSE_HANDLER_INSTANCE(response,req_args)
        if data:
            func = "indexYammer" + resource.title()
            logging.debug("Calling %s" % func)

            getattr(sys.modules[__name__], func)(data, req_args)

            sys.stdout.flush()               

    except RuntimeError,e:
        logging.error("Looks like an error handle the response output: %s" % str(e))

# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print "<error><message>%s</message></error>" % encodeXMLText(s)
    
# prints XML stream
def print_xml_single_instance_mode(s):
    print "<stream><event><data>%s</data></event></stream>" % encodeXMLText(s)
    
# prints simple stream
def print_simple(s):
    print "%s\n" % s

# prints XML stream
def print_xml_stream(s, source_type=None):
    if source_type == None:
        print "<stream><event unbroken=\"1\"><data>%s</data><done/></event></stream>" % encodeXMLText(s)
    else:
        print "<stream><event unbroken=\"1\"><data>%s</data><sourcetype>%s</sourcetype><done/></event></stream>" % (encodeXMLText(s), encodeXMLText(source_type))

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
            logging.debug("session_key: %s" % data)    

        server_uri_node = root.getElementsByTagName("server_uri")[0]
        if server_uri_node and server_uri_node.firstChild and server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:
            data = server_uri_node.firstChild.data
            config["server_uri"] = data   
            logging.debug("server_uri: %s" % data)    
            
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

        #checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        #if checkpnt_node and checkpnt_node.firstChild and \
        #   checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
        #    config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
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
