import sys, os, platform, re
import xml.dom.minidom, xml.sax.saxutils
import logging
import urllib2
import json
import sched, time
from datetime import datetime, date, time
from time import gmtime, strftime, localtime,mktime

#set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

_MI_APP_NAME = 'SDG'
_SPLUNK_HOME = os.getenv("SPLUNK_HOME")
if _SPLUNK_HOME == None:
    _SPLUNK_HOME = os.getenv("SPLUNKHOME")
if _SPLUNK_HOME == None:
    _SPLUNK_HOME = "/opt/splunk"    

_OPERATING_SYSTEM = platform.system()
_APP_HOME = _SPLUNK_HOME + "/etc/apps/"+_MI_APP_NAME+"/"
_LIB_PATH = _APP_HOME + "bin/lib/"
_PID = os.getpid()
_IS_WINDOWS = False

if _OPERATING_SYSTEM.lower() == "windows":
    _IS_WINDOWS = True
    _LIB_PATH.replace("/","\\")
    _APP_HOME.replace("/","\\")
    
#SYSTEM EXIT CODES
_SYS_EXIT_OK = 0
_SYS_EXIT_FAILED_VALIDATION = 7

#necessary to allow unbuffered writing for the Splunk Indexer
class Unbuffered:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)
    
SCHEME = """<scheme>
    <title>sdgAPI</title>
    <description>Get data from an un-authenticated REST API</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="api_url">
                <title>API URL</title>
                <description>The URL</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    """ Prints the Scheme """
    doPrint(SCHEME)

def get_source(s):
    return "sdgAPI:" + s
        
def print_error(s):
    """ print any errors that occur """
    doPrint("<error><message>%s</message></error>" % escape(s))
    logging.error(s)

def validate_conf(config, key):
    """ Validate that required key is in the config as parsed from stdin """
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

#read XML configuration passed from splunkd
def get_config():
    """ Read XML Configuration data passed from splunkd on stdin """
    config = {}
    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
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

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        # just some validation: make sure these keys are present (required)
        validate_conf(config, "api_url")
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

def get_validation_data():
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

def validate_arguments():
    val_data = get_validation_data()
    try:  
        try: str(val_data["api_url"])
        except: raise Exception, "API URL must be a string"
    except Exception, e:
        print_error("Invalid configuration specified: %s" % str(e))
        sys.exit(_SYS_EXIT_FAILED_VALIDATION)
        
def doPrint(s):
    """ A wrapper Function to output data by same method (print vs sys.stdout.write)"""
    sys.stdout.write(s)

def escape(s):
    """ A wrapper function to force conformity on xml escaping, and for ease of reading """
    return xml.sax.saxutils.escape(s)

def do_event(string, sourcetype, source):
    """ Outputs a single broken event to the Splunk Processor """
    if len(string) < 1:
        string = "empty_event"
    string = escape(string)
    dostr = "<event><data>%s</data><source>%s</source><sourcetype>%s</sourcetype></event>" %(re.sub(r"[\r\n]+"," ",string), escape(source), escape(sourcetype))
    doPrint(dostr)    
    
def do_done_event(sourcetype, source):
    """ Outputs a single done even for an unbroken event to the Splunk Processor """
    dostr = "<event><source>%s</source><sourcetype>%s</sourcetype><done/></event>" %(escape(source), escape(sourcetype))
    doPrint(dostr)
    
def init_stream():
    """ Sends the XML for starting a Stream """
    logging.debug("Setting up stream")
    doPrint("<stream>")
    
def end_stream():
    """ Sends the XML for ending a Stream """
    logging.debug("Ending Stream")
    doPrint("</stream>")
    
def getAPIResults(url):
    """ SENDS THE JSON FROM THE API CALL """
    logging.debug("Getting URL: %s"%url)
    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    return(response.read())

def addCustomFields(apiResult):
	r = json.loads(apiResult)
	r["timestamp"] = "%s"%(strftime("%a, %d %b %Y %H:%M:%S %Z", localtime()))
        return json.dumps(r)


def run():
    """ The Main function that starts the action. """
    sys.stdout = Unbuffered(sys.stdout)
    config = get_config()  
    stanza = config["name"]
    sourcetype = config["sourcetype"]
    source = get_source(stanza[(stanza.rfind("/")+1):])    
        
    init_stream()    
    logging.info("source=%s sourcetype=%s stanza=%s operation=running_api"%(source,sourcetype,stanza))
    do_event(addCustomFields("%s"%(getAPIResults(config["api_url"]))),sourcetype,source)
    do_done_event(sourcetype,source)
    end_stream()
    

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        elif sys.argv[1] == "--test":
            doPrint('No tests for the scheme present')
        else:
            doPrint('You giveth weird arguments')
    else:
        run()

    sys.exit(_SYS_EXIT_OK)
