# Author: Dominique Vocat
# contact the CiscoAXL api via HTTP and queries stuff, returns the data to splunk.
# Version 0.1: (10.12.2015 -vtd) initial implementation of the CiscoAXL to Splunk wrapper
# Version 0.2: (29.12.2015 -vtd) generic wrapper of the suds created object. takes first argument as method name,
#                                passes all other named parameters as dict minus columns. reformats columns as dict
#                                for method call parameter to specify the returned columns. Kinda nifty.

# inspired by http://stackoverflow.com/questions/22845943/getting-correct-attribute-nesting-with-python-suds-and-cisco-axl

import sys,splunk.Intersplunk,os,ConfigParser,urllib,urllib2,json,logging,logging.handlers,re
from ConfigParser import SafeConfigParser
from optparse import OptionParser
from suds.client import Client

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
	LOGGING_FILE_NAME = "ciscoaxl.log"
	BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
	LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
	splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
	splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
	logger.addHandler(splunk_log_handler)
	splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
	return logger

# start the logger
try:
	logger = setup_logging("ciscoaxl")
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
	section_name = options.pop('server','default') #section_name = options.get('server','default')
	#print keywords
	#api = sys.argv[1]
	if len(keywords) < 1:
		keywords.append('help')
	api = keywords[0]
	columns = options.pop('columns', '_uuid') #pop columns from options so we don't pass it to the method  used to be options.get('columns', '_uuid')
	columns = dict.fromkeys(columns.split(','),'') #build dict from named parameter
	#print options
	#print columns

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
	configLocalFileName = os.path.join(scriptDir,'..','local','ciscoaxl.conf')
	#print configLocalFileName
	parser = SafeConfigParser()
	# read .conf options if empty use settings from [default] in ciscoaxl.conf
	parser.read(configLocalFileName)
	if not os.path.exists(configLocalFileName):
		splunk.Intersplunk.generateErrorResults(': No config found! Check your ciscoaxl.conf in local.')	
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
	PORT = parser.get(section_name, 'port')

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	logger.error( "ERROR: No [default] section seems to be defined." )

# -----------=================-----------------
# check if there are dangerous apis requested
# -----------=================-----------------
methodwhitelist = parser.get(section_name, 'methodwhitelist')

#pattern = re.compile('list|get|help', re.IGNORECASE)
pattern = re.compile(methodwhitelist, re.IGNORECASE)
match = pattern.search(api)
if not match:
	#print 'Error: you tried to modify or use a forbidden command: ', match.group()
	splunk.Intersplunk.generateErrorResults('Error: you tried to use a potentially harmful command: %s' % api)
	exit()

# -----------=================-----------------
# request the webservice
# -----------=================-----------------
cmserver = SERVER
cmport = PORT
wsdl = 'file://'+os.path.join(scriptDir,'AXLAPI.wsdl')  #'file:///opt/splunk/etc/apps/TA-ciscoaxl/bin/AXLAPI.wsdl'
location = 'https://' + cmserver + ':' + cmport + '/axl/'
username = USERNAME
password = PASSWORD

client = Client(wsdl,location=location, username=username, password=password)

try:
	if api != "help":
		for method in client.wsdl.services[0].ports[0].methods.values():
			#print '%s(%s)' % (method.name, ', '.join('%s: %s' % (part.type, part.name) for part in method.soap.input.body.parts))
			if method.name == api:
				method_to_call = getattr(client.service,method.name)
		#exmple: result = method_to_call({'name':searchvalue+'%'},{'name':'','model':''})
		result = method_to_call(options,columns)
		result_list = [ dict(n) for n in result[0][0]]
		splunk.Intersplunk.outputResults(result_list)
	else:
		print 'method'
		for method in client.wsdl.services[0].ports[0].methods.values():
			#print '%s(%s)' % (method.name, ', '.join('%s: %s' % (part.type, part.name) for part in method.soap.input.body.parts))
			print '%s' % method.name

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	print result # so we know whats going on