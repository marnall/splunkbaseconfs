from WunderClass import *

import sys, os, platform, re
import xml.dom.minidom, xml.sax.saxutils
import logging
import urllib2
import json, datetime
import sched, time
from datetime import datetime, timedelta
#set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

_MI_APP_NAME = 'WunderGround'
_SPLUNK_HOME = os.getenv("SPLUNK_HOME")
if _SPLUNK_HOME == None:
    _SPLUNK_HOME = os.getenv("SPLUNKHOME")
if _SPLUNK_HOME == None:
    _SPLUNK_HOME = "/opt/splunkbeta"    

_OPERATING_SYSTEM = platform.system()
_APP_HOME = _SPLUNK_HOME + "/etc/apps/TA-wunderground/"
_LIB_PATH = _APP_HOME + "bin/lib/"
_PID = os.getpid()
_IS_WINDOWS = False

if _OPERATING_SYSTEM.lower() == "windows":
    _IS_WINDOWS = True
    _LIB_PATH.replace("/","\\")
    _APP_HOME.replace("/","\\")
    
#sys.path.insert(0,_LIB_PATH) - Only Needed if importing local libraries

#SYSTEM EXIT CODES
_SYS_EXIT_GPARENT_PID_ONE = 8
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
    <title>Wunderground</title>
    <description>Get data from Wunderground.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="apikey">
                <title>API Key</title>
                <description>The Wunderground API Key to use.</description>
            </arg>
            <arg name="apifeature">
                <title>API Feature</title>
                <description>The Wunderground API Feature to query.</description>
            </arg>
            <arg name="json_configuration">
                <title>JSON Configuration</title>
                <description>A JSON Object with configuration options for the API Calls. See the Wunderground API Documentation and the TA-wunderground/README.txt.</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    """ Prints the Scheme """
    doPrint(SCHEME)

def get_source(config):
    return "wunderground:" + config
        
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
        validate_conf(config, "apikey")
        validate_conf(config, "apifeature")
        validate_conf(config, "json_configuration")
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
        if val_data["apifeature"] not in ["alerts", "almanac","astronomy","conditions","currenthurricane","forecast","forecast10day",
                                          "geolookup", "history","hourly","hourly10day","planner","rawtide","satellite","tide","webcams","yesterday","pws"]:
                raise Exception, "API Feature '%s' not supported"%str(val_data["apifeature"])
        try:
            json_config = val_data["json_configuration"]
            if None == json_config and val_data["apifeatures"] not in ["currenthurricane"]: raise Exception
            else: jCo = json.loads(json_config)            
        except Exception, e: raise Exception, "Must pass a JSON Configuration: %s"%str(e)
        try: 
            apikey = val_data["apikey"]
            if None == apikey: raise Exception
        except: raise Exception, "Must Define API Key"
    except Exception, e:
        print_error("Invalid configuration specified: %s" % str(e))
        sys.exit(_SYS_EXIT_FAILED_VALIDATION)
        
def daterange(start_date, end_date):
    doPrint("wunderground_daterange: Start: %s End:%s"%(start_date, end_date))
    for n in range(int ((end_date - start_date).days+1)):
        yield start_date + timedelta(n)

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
    
def run():
    """ The Main function that starts the action. The thread will sleep for however many seconds are configured via the Input. """
    sys.stdout = Unbuffered(sys.stdout)
    config = get_config()  
    jCO = json.loads(config["json_configuration"])
    wunderBread = WunderAPI(config["apikey"])
    jCO["feature"] = config["apifeature"]
    stanza = config["name"]
    source = get_source(stanza[(stanza.rfind("/")+1):])    
        
    init_stream()    
    while True:
        if not _IS_WINDOWS:
            gparent_pid = os.popen("ps -p %d -oppid="%(os.getppid()) ).read().strip()
            if gparent_pid == 1:
                print_error("Whoa. That process shouldn't be like that.")
                sys.exit(_SYS_EXIT_GPARENT_PID_ONE)
        logging.info("source=%s sourcetype=wunderground stanza=%s operation=running_api"%(source,stanza))
        try:
         if jCO["feature"] == "history":
           fromDate = datetime.strptime(jCO["from"],"%Y-%m-%d")
           toDate = datetime.strptime(jCO["to"],"%Y-%m-%d")
           logging.info("wunderground range: start:%s end:%s"%(fromDate.date(), toDate.date()))
           for single_date in daterange(fromDate,toDate):
               jCO["date"] = single_date.strftime("%Y%m%d")
               logging.info("wunderground range starting: %s "%jCO["date"])
               jS = json.loads(wunderBread.RunAPI(jCO))
               for item in jS:
                item_string = json.dumps(jS[item])
                if "response" != item:
                  for obv in jS[item]["observations"]:
                     logging.info("%s"%obv)
                     utc = obv["utcdate"]
                     obv["_time"] = "%s/%s/%s %s:%s:00 UTC"%(utc["mon"],utc["mday"],utc["year"],utc["hour"],utc["min"])
                     obv["observation_epoch"] = (datetime.strptime(obv["_time"], "%m/%d/%Y %H:%M:%S %Z") - datetime(1970,1,1)).total_seconds()
                     do_event("%s"%(json.dumps(obv)),"wunderground",source)
                else:
                     do_event("%s"%(item_string),"wunderground",source)
                logging.info("sleeping to prevent overrun (see wunderground terms for developer accounts and rate limiting")
                time.sleep(float(15))
         else:
           jS = json.loads(wunderBread.RunAPI(jCO))
  	   for item in jS:
             item_string = json.dumps(jS[item])
             if "response" != item:
                do_event("%s"%(item_string),"wunderground",source)
         do_done_event("wunderground",source)
        except Exception, e: 
             exc_type, exc_obj, tb = sys.exc_info()
             f = tb.tb_frame
             lineno = tb.tb_lineno
             print_error("Exception in RunAPI call: %s line:%d feature:%s params:%s"%(e,lineno,jCO["feature"],jCO))
           
        break
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

    sys.exit(0)
