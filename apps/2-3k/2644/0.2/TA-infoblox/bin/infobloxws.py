# Author: Dominique Vocat
# contact the infoblox api via REST and queries stuff, returns the json to splunk.
# Version 0.1: initial implementation of the REST to Splunk wrapper, implements search
# Version 0.2: small changes, includes a new parameter max_results and uses it for non search calls.

import sys,splunk.Intersplunk,os,ConfigParser,urllib,urllib2,json,logging,logging.handlers
from ConfigParser import SafeConfigParser
from optparse import OptionParser

Debugging="no"

def setup_logging(n):
	logger = logging.getLogger(n) # Root-level logger
	if Debugging == "yes":
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.ERROR)
	SPLUNK_HOME = os.environ['SPLUNK_HOME']
	LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
	LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
	LOGGING_STANZA_NAME = 'python'
	LOGGING_FILE_NAME = "infoblox.log"
	BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
	LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
	splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
	splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
	logger.addHandler(splunk_log_handler)
	splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
	return logger

# start the logger
try:
	logger = setup_logging("infobloxws")
	logger.info( "INFO: Go Go Gadget Go!" )

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	

# -----------=================-----------------
# handle parameters
# -----------=================-----------------

# define empty lists
result_set = []
results = []

#named options
try:
	logger.info( "getting Splunk options..." )
	keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
	section_name = options.get('server','default')
	api = options.get('api', '')
	searchkey = options.get('searchkey', '')
	searchvalue = options.get('searchvalue','')
	objtype = options.get('objtype','All') #used in api="search" only
	max_results = options.get('max_results','100') #limit to 100 by default, Dominique Vocat 7.9.2015@13:10
	return_fields = options.get('return_fields','') #pass return fields list (comma separated list... fairly goofy but hey...)

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	logger.info( "INFO: no option provided using [default]!" )

# -----------=================-----------------
# read config file
# -----------=================-----------------
if Debugging == "yes":
	logger.debug( "DEBUG - section name: " + section_name )
	print section_name
	logger.debug( "DEBUG - ipaddress: " + ipaddress )
	print ipaddress

# set path to .conf file
try:
	logger.info( "read the .conf..." )
	scriptDir = sys.path[0]
	configLocalFileName = os.path.join(scriptDir,'..','local','infoblox.conf')
	#print configLocalFileName
	parser = SafeConfigParser()
	# read .conf options if empty use settings from [default] in infoblox.conf
	parser.read(configLocalFileName)
	if not os.path.exists(configLocalFileName):
		splunk.Intersplunk.generateErrorResults(': No config found! Check your infoblox.conf in local.')	
		exit(0)

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	logger.error( "ERROR: No config found! Check your infoblox.conf in local." )

# use user provided options or get [default] stanza options
try:
	logger.info( "read the default options from .conf..." )
	SERVER = parser.get(section_name, 'server')
	USERNAME = parser.get(section_name, 'user')
	PASSWORD = parser.get(section_name, 'password')

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	logger.error( "ERROR: No [default] section seems to be defined." )


# -----------=================-----------------
# request the webservice
# -----------=================-----------------
if Debugging == "yes":
	print SERVER
	print USERNAME
	print PASSWORD
	logger.debug( "DEBUG - SERVER " + SERVER )
	logger.debug( "DEBUG - USERNAME " + USERNAME )
	logger.debug( "DEBUG - PASSWORD " + PASSWORD )

try:
    #example LOCATION_URL="https://chhs-aibl011.helvetia.ch/wapi/v1.2.1/"
    #example get call url="https://chhs-aibl011.helvetia.ch/wapi/v1.2.1/ipv4address?ip_address=" + ipaddress
    #example get network containers... https://chhs-aibl011/wapi/v1.2.1/networkcontainer?_max_results=100
    # to do: handle non search calls differently... like, just get the damn listing. Also handle the max_results.
    url="https://"+SERVER+"/wapi/v1.2.1/"+api
    if api == "search":
        #looks like we will search a bit, handle parameters accordingly
        values={searchkey : searchvalue, 'objtype' : objtype}
    else:
        #looks like we won't search so we just do get some listing
        #if there are some return fields specified then send them along, else fail back to default by no passing a parameter (Dominique Vocat 11.09.2015)
        if return_fields == "":
            values={'_max_results' : max_results}
        else:
            values={'_max_results' : max_results, '_return_fields' : return_fields}
    data = urllib.urlencode(values)

    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, USERNAME, PASSWORD)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    #req = urllib2.Request(url, data)
    ##pagehandle = urllib2.urlopen(url)
    #pagehandle = urllib2.urlopen(req)
    pagehandle = urllib2.urlopen(url+"?"+data)


    # -----------=================-----------------
    # handle json2splunk
    # -----------=================-----------------

    results=json.loads(pagehandle.read())

    splunk.Intersplunk.outputResults( results )

except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
