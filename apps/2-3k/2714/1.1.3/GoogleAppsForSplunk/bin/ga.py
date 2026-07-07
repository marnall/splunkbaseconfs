import sys, xml.dom.minidom, xml.sax.saxutils, logging, urllib2, ConfigParser, base64, json, os, platform, os.path, sched, time, pickle
from datetime import date, timedelta, datetime
import httplib2, json
from apiclient import errors
from apiclient.discovery import build
from datetime import datetime, timedelta
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage

_MI_APP_NAME = 'Google Apps For Splunk Modular Input'
_SPLUNK_HOME = os.getenv("SPLUNK_HOME")
_SOURCETYPE = None
_SOURCE = None
if _SPLUNK_HOME == None:
    _SPLUNK_HOME = os.getenv("SPLUNKHOME")
if _SPLUNK_HOME == None:
    _SPLUNK_HOME = "/opt/splunk"    

_OPERATING_SYSTEM = platform.system()
_APP_NAME = "GoogleAppsForSplunk"
_APP_HOME = os.path.join(_SPLUNK_HOME,"etc","apps",_APP_NAME)
_CRED_HOME = os.path.join(_APP_HOME,"local")
_BIN_PATH = os.path.join(_APP_HOME,"bin")
_IS_WINDOWS = False

sys.path.insert(0,_BIN_PATH)

import splunk.Intersplunk
import splunk.entity as entity
import logging  as logger
import ast

outputFileName = 'ga.py-log.txt'
outputFileLog = os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk',outputFileName)
logger.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=outputFileLog, filemode='a+', level=logger.INFO, datefmt='%Y-%m-%d %H:%M:%S %z')
logger.Formatter.converter = time.gmtime

class Unbuffered:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

#SYSTEM EXIT CODES
_SYS_EXIT_FAILED_VALIDATION = 7
_SYS_EXIT_FAILED_GET_OAUTH_CREDENTIALS = 6
_SYS_EXIT_FAILURE_FIND_API = 5
_SYS_EXIT_OAUTH_FAILURE = 4

#Necessary
_CRED = None
_DOMAIN = None
        
SCHEME = """<scheme>
    <title>Google Apps For Splunk</title>
    <description>Get data from Google Apps APIs. Make Sure that run_first.py has been executed prior to setting up an Input.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="domain">
                <title>Google Apps Domain</title>
                <description>The Google Apps Domain to query for information</description>
            </arg>
            <arg name="servicename">
                <title>Report Key</title>
                <description>API to Read (report:login, see README for full list)</description>
            </arg>
            <arg name="extraconfig">
                <title>Extra Configuration - JSON Object</title>
                <description>Include extra configuration options for various API calls. If not needed, use: {} as the object.</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

_AVAILAPI = { "report": ["all", "admin","calendar","drive","login","token"],
	      "usage": ["customer","user"] }
#SPLUNK SPECIFIC Modular Input Functions

def do_scheme():
    doPrint(SCHEME)
    # prints XML error data to be consumed by Splunk
    
def escape(s):
    return xml.sax.saxutils.escape(s)

def print_error(s):
    global _SOURCETYPE, _SOURCE
    logging.error("source=%s sourcetype=%s %s"%(_SOURCETYPE,_SOURCE,s))
    doPrint("<error><message>%s</message></error>" % escape(s))

def validate_conf(config, key):
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

_SOURCETYPE = None
_SOURCE = None
def print_debug(s):
    global _SOURCETYPE, _SOURCE
    logging.debug("source=%s sourcetype=%s %s"%(_SOURCE,_SOURCETYPE,s))

def print_info(s):
    global _SOURCETYPE, _SOURCE
    logging.info("app=GoogleAppsForSplunk source=%s sourcetype=%s %s"%(_SOURCE,_SOURCETYPE,s))

_CHECKPOINT = None
def buildCHKFilename(domain, apikey, apivalue):
	return "%s_%s_%s"%(domain,apikey, apivalue)

def get_encoded_file_path(config, filename):
    return os.path.join(config["checkpoint_dir"], "ga_%s"%filename)

def save_checkpoint(config, filename):
    chk_file = get_encoded_file_path(config, filename)
    chk_time = datetime.utcnow().isoformat('T') + 'Z'
    # just create an empty file name
    print_info("action=checkpointing status=save file=%s time=%s"%(chk_file,chk_time))
    f = open(chk_file, "w")
    f.write(chk_time)
    f.close()

def load_checkpoint(config, filename):
    chk_file = get_encoded_file_path(config, filename)
    # try to open this file
    try:
        f = open(chk_file, "r")
        chk_time = "%s"%(f.read().strip())
        f.close()
    except:
        # assume that this means the checkpoint is not there
        wibbly_wobbly_timey_wimey = datetime.utcnow() - timedelta(days=1)
        default_time = wibbly_wobbly_timey_wimey.isoformat('T') + 'Z'
        print_info("action=default_checkpoint time=%s"%default_time)
        return default_time
    print_info("action=checkpoint status=load file=%s time=%s"%(chk_file,chk_time))
    return chk_time

#read XML configuration passed from splunkd
def get_config():
    config = {}
    try:
        # read everything from stdin
        config_str = sys.stdin.read()
        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        chkpointdir = root.getElementsByTagName("checkpoint_dir")[0].firstChild.data
        config["checkpoint_dir"] = chkpointdir
	logging.debug("XML: found checkpoint_dir: %s"%chkpointdir)
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            logging.debug("%s"%conf_node)
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
        validate_conf(config, "domain")
        validate_conf(config, "servicename")
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
        serviceName = val_data["servicename"].split(':')
        valkey = serviceName[0]
        valval = serviceName[1]
	print_info("operation=validating input key=%s value=%s"%(valkey,valval))
        if valval not in _AVAILAPI[valkey]:
            raise Exception, "No Valid Report Key set. Failed excuse was key %s with value %s"%(valkey, valval)
    except IOError, e:
        print_error("OAuth file not found. Did you run the run_first.py? %s"%(str(e)))
        sys.exit(_SYS_EXIT_FAILED_VALIDATION)
    except Exception, e:
        print_error("Invalid configuration specified: %s" % str(e))
        sys.exit(_SYS_EXIT_FAILED_VALIDATION)
    
def gen_date_string():
    st = time.localtime()
    tm = time.mktime(st)
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(tm))

def doPrint(stringIn):
    print stringIn

def init_stream():
    doPrint("<stream>")
    logging.debug("printed start of stream")

def end_stream():
    doPrint("</stream>")
    logging.debug("printed end of stream")

def do_event(event_data):
    global _SOURCETYPE, _SOURCE
    if len(event_data) < 1:
        event_data = ""
    eventxml = "<event><data>%s</data><sourcetype>%s</sourcetype><source>%s</source></event>\n" %(escape(event_data),escape(_SOURCETYPE),escape(_SOURCE))
    doPrint(eventxml)
    logging.debug("printed an event")

def do_done_event():
    global _SOURCETYPE, _SOURCE
    eventxml = "<event><data></data><sourcetype>%s</sourcetype><source>%s</source><done/></event>\n"%(escape(_SOURCETYPE),escape(_SOURCE))
    doPrint(eventxml)
    logging.debug("printed a done event")

def getOAuthCredentials(domain):
    global _CRED
    try:        
	storage = Storage(os.path.join(_CRED_HOME, "GoogleApps."+domain.lower()+".cred"))
	_CRED = storage.get()
    except Exception, e:
        print_error("Getting OAUTH Credentials Failed: %s"%e)
        sys.exit(_SYS_EXIT_FAILED_GET_OAUTH_CREDENTIALS)

def doJsonEvent(events):
	for evt in events:
		do_event(json.dumps(evt))

def adminReportCustomerUsage(http,ak, extConf):
        global _CHECKPOINT
        print_info("function=adminReportCustomerUsage status=starting")
        service = build('admin', 'reports_v1', http=http)
        # Set start time to one week ago, to avoid too many results
        start_time = _CHECKPOINT
        all_logins = []
        page_token = None
        params = {'date': start_time}
        print_info("operation=starting_while_loop_for_pages")
        while True:
          try:
            if page_token:
              params['pageToken'] = page_token
            print_debug("Have A Page? :%s"%page_token)
            current_page = service.userUsageReport().get(**params).execute()
            print_debug("got a current_page:%s"%current_page)
            if "items" in current_page:
                all_logins.extend(current_page['items'])
            page_token = current_page.get('nextPageToken')
            if not page_token:
              break
          except errors.HttpError as error:
            print_error( 'An error occurred: %s' % error)
            break
        print_debug("Have events, will travel: %s"%all_logins)
        doJsonEvent(all_logins)

def adminReportUserUsage(http, ak, extConf):
	global _CHECKPOINT
	print_info("function=adminReportUserUsage status=starting")
	service = build('admin', 'reports_v1', http=http)
	print_debug("built the service")
        # Set start time to one week ago, to avoid too many results
	#2015-04-23T14:24:48.802688Z
	print_debug("checkpoint: %s"%_CHECKPOINT)
        start_time = datetime.strptime(_CHECKPOINT,"%Y-%m-%dT%H:%M:%S.%fZ")
	print_debug("start_time: %s"%start_time)
	rightNow = datetime.utcnow()
	print_debug("rightnow: %s"%rightNow)
	numDays = (rightNow - start_time).days + 4
	print_debug("checkpoint: %s  rightNow:%s numDays:%s "%(start_time,rightNow,numDays))
	if numDays < 1:
		print_info("operation=checkpoint_check numberOfDays=%s checkpoint=%s execution_time=%s"%(numDays,start_time,rightNow))
		return
	reportDates = [ d.strftime("%Y-%m-%d") for d in [ rightNow - timedelta(days=x) for x in range(0,numDays) ] ]
	print_debug("Found Report Dates: %s"%reportDates)
        all_logins = []
	do_done_event()
	print_debug("Ending Stream")
	end_stream()
	for myDate in reportDates:
		init_stream()
		myEvents = []
	        page_token = None
	        params = {'userKey': 'all', 'date': myDate}
	        print_info("operation=starting_while_loop_for_pages date=%s"%myDate)
	        while True:
	          try:
	            if page_token:
	              params['pageToken'] = page_token
	            print_debug("Have A Page? :%s"%page_token)
	            current_page = service.userUsageReport().get(**params).execute()
	            print_debug("got a current_page")
	            if "usageReports" in current_page:
	                myEvents.extend(current_page['usageReports'])
	            page_token = current_page.get('nextPageToken')
	            if not page_token:
	              break
	          except errors.HttpError as error:
	            print 'An error occurred: %s' % error
		    print_error("error=http_error message='%s'"%error)
	            break
		doJsonEvent(myEvents)
		print_debug("Have events, will travel: %s"%len(myEvents))
		do_done_event()
		end_stream()
	init_stream()

def adminReportV1(http, applicationName, extConf):
	global _CHECKPOINT
	print_info("function=adminReportV1 status=starting ")
	service = build('admin', 'reports_v1', http=http)
	# Set start time to one week ago, to avoid too many results
	start_time = _CHECKPOINT
	all_logins = []
	page_token = None
	params = {'applicationName': applicationName, 'userKey': 'all', 'startTime': start_time}
	print_info("operation=starting_while_loop_for_pages")
	while True:
	  try:
	    if page_token:
	      params['pageToken'] = page_token
	    print_debug("Have A Page? :%s"%page_token)
	    current_page = service.activities().list(**params).execute()
	    print_debug("got a current_page:%s"%current_page)
	    if "items" in current_page:
	    	all_logins.extend(current_page['items'])
	    page_token = current_page.get('nextPageToken')
	    if not page_token:
	      break
	  except errors.HttpError as error:
	    print 'An error occurred: %s' % error
	    break
	print_debug("Have events, will travel: %s"%all_logins)
	doJsonEvent(all_logins)

_SERVICE = {
	"report": adminReportV1,
	"customer": adminReportCustomerUsage,
	"user": adminReportUserUsage
}

def run():
  global _SOURCETYPE, _SOURCE, _CHECKPOINT, _CRED
  sys.stdout = Unbuffered(sys.stdout)
  print_info("app=googleapps os=\"%s\" app_home=\"%s\" "%(_OPERATING_SYSTEM,_APP_HOME))
  config = get_config()
  stanza = config["name"]  
  domain = config["domain"]
  reportName = config["servicename"].split(':')
  apivalue = reportName[0]
  apikey = reportName[1]
  chkPointFile = buildCHKFilename(domain, apivalue, apikey)
  extConf = None
  try: extConf = json.loads(config["extraconfig"])
  except: pass
  if apikey not in _AVAILAPI[apivalue]:
      print_error("operation=check_api_value api_value=%s"%(apivalue))
      sys.exit(_SYS_EXIT_FAILURE_FIND_API)
      
  source = "gapps:"+domain
  sT = "gapps:%s:%s" %(apivalue, apikey)
  _SOURCETYPE = sT
  _SOURCE = source
  print_info("set sourcetype to " + sT)
  print_info("set source to " + source)
  getOAuthCredentials(domain)
  init_stream()
  http = httplib2.Http()
  http = _CRED.authorize(http)
  _CHECKPOINT = load_checkpoint(config, chkPointFile)
  try:
	print_info("operation=execute_service apivalue=%s apikey=%s http=%s"%(apivalue,apikey,http))
	if "all" == apikey:
		print_debug("doin it, ALL night long! All night!")
		for ak in _AVAILAPI[apivalue]:
			if "all" == ak: 
				print_debug("not gonna get us.")
			else:
				print_debug("Running apikey for ALL: %s"%ak)
				chkPointFile = buildCHKFilename(domain, apivalue, ak)
				_CHECKPOINT = load_checkpoint(config, chkPointFile)
				_SOURCETYPE = "gapps:%s:%s"%(apivalue, ak)
				print_debug("setting sourcetype: %s"%_SOURCETYPE)
				_SERVICE[apivalue](http,ak,extConf)
				save_checkpoint(config, chkPointFile)
	else:
		ak = apikey
		av = apivalue
		if "usage" == av:
			av = ak
		_SERVICE[av](http,ak,extConf)
		save_checkpoint(config, chkPointFile)
  except Exception, e:
          print_error("operation=run error=\"%s\""%(str((e))))  
  do_done_event()
  print_debug("Ending Stream")
  end_stream() 

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'You giveth weird arguments'
    else:
        run()

    sys.exit(0)
