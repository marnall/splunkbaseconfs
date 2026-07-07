'''
Pubnub Modular Input Script
'''

import sys,logging,os,time,re,threading,hashlib
import xml.dom.minidom
from datetime import datetime
#for running on Universal Forwarders where the library is not present
try:
    import splunk.entity as entity
except:
    pass
from logging.handlers import TimedRotatingFileHandler
           
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","pubnubmodinput_app_modularinput.log")

# Set up a specific logger
logger = logging.getLogger('pubnubmodinput')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
log_handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

RESPONSE_HANDLER_INSTANCE = None


#dynamically load in any eggs
EGG_DIR = os.path.join(SPLUNK_HOME,"etc","apps","pubnub_ta","bin")

for filename in os.listdir(EGG_DIR):
    if filename.endswith(".egg"):
        sys.path.append(os.path.join(EGG_DIR ,filename)) 

       

SCHEME = """<scheme>
    <title>Pubnub</title>
    <description>Pubnub input for subscribing to Pubnub channels</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>Pubnub input name</title>
                <description>Name of this Pubnub input</description>
            </arg>
            <arg name="activation_key">
                <title>Activation Key</title>
                <description>Visit http://www.baboonbones.com/#activation to obtain a non-expiring key</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="key">
                <title>Key</title>
                <description>Subscribe key</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="channel">
                <title>Channel</title>
                <description>Pubnub channel</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
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
            <arg name="log_level">
                <title>Log Level</title>
                <description>Logging level (info, error, debug etc..)</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            
        </args>
    </endpoint>
</scheme>
"""

def get_credentials(session_key):
   myapp = 'pubnub_ta'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=session_key)
   except Exception as e:
      logger.error("Could not get credentials from splunk. Error: %s" % str(e))
      return {}

   return entities.items()

def do_validate():
    config = get_validation_config() 
    #TODO
    #if error , print_validation_error & sys.exit(2) 
    
def _callback(message, channel):
    handle_output(message)
 
def _error(message):
    handle_output(message)
 

def do_run(config):
    
    
    SESSION_TOKEN = config.get("session_key")
    activation_key = config.get("activation_key").strip()
    app_name = "Pubnub Modular Input"

    try: 
        
        log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s stanza:{0}'.format(config.get("name"))) )

    except: # catch *all* exceptions
        e = sys.exc_info()[1]
        logger.error("Couldn't update logging templates: %s" % str(e))
    
    if len(activation_key) > 32:
        activation_hash = activation_key[:32]
        activation_ts = activation_key[32:][::-1]
        current_ts = time.time()
        m = hashlib.md5()
        m.update((app_name + activation_ts).encode('utf-8'))
        if not m.hexdigest().upper() == activation_hash.upper():
            logger.error("Trial Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % app_name)
            sys.exit(2)
        if ((current_ts - int(activation_ts)) > 604800):
            logger.error("Trial Activation key for App '%s' has now expired. Please visit http://www.baboonbones.com/#activation to purchase a non expiring key." % app_name)
            sys.exit(2)
    else:
        m = hashlib.md5()
        m.update((app_name).encode('utf-8'))
        if not m.hexdigest().upper() == activation_key.upper():
            logger.error("Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % app_name)
            sys.exit(2)

    credentials_list = get_credentials(SESSION_TOKEN)

    for i, c in credentials_list:
        replace_key='{encrypted:%s}' % c['username']

        for k, v in config.items():
            config[k] = v.replace(replace_key,c['clear_password'])
            
        
    delimiter = ','
    
    #params
    
    key=config.get("key",)
    channel=config.get("channel")
    
    
    response_handler_args={} 
    response_handler_args_str=config.get("response_handler_args")
    if not response_handler_args_str is None:
        response_handler_args = dict((k.strip(), v.strip()) for k,v in 
              (item.split('=',1) for item in response_handler_args_str.split(delimiter)))
        
    response_handler=config.get("response_handler","DefaultResponseHandler")
    module = __import__("responsehandlers")
    class_ = getattr(module,response_handler)

    global RESPONSE_HANDLER_INSTANCE
    RESPONSE_HANDLER_INSTANCE = class_(**response_handler_args)

    try:
        from pubnubsdk import Pubnub
    except Exception as e:
        logger.error("Looks like an error importing the pubnubsdk module: %s" % str(e))
        sys.exit(2)

   
    pubnub = Pubnub(subscribe_key=key,publish_key=None)
    
    try: 
 
        pubnub.subscribe(channels=channel, callback=_callback, error=_error)

            
    except RuntimeError as e:
        logger.error("Looks like an error: %s" % str(e))
        sys.exit(2) 
        
  

def handle_output(message): 
    
    try:  
        RESPONSE_HANDLER_INSTANCE(message)
        sys.stdout.flush()               
    except RuntimeError as e:
        logger.error("Looks like an error handle the response output: %s" % str(e))

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

        #change log level from configuration stanza if present
        log_level = logging.getLevelName(config.get("log_level","INFO"))
        logger.setLevel(log_level)

        do_run(config)
        
    sys.exit(0)
