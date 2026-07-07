# Author: Dominique Vocat
# contact the CiscoAXL api via HTTP and queries stuff, returns the data to splunk.
# Version 0.1: (10.12.2015 -vtd) initial implementation of the CiscoAXL to Splunk wrapper
# Version 0.2: (18.12.2015 -vts) added regex test to prevent usage of modifying commands

# inspired heavily by http://stackoverflow.com/questions/22845943/getting-correct-attribute-nesting-with-python-suds-and-cisco-axl

import sys,splunk.Intersplunk,os,ConfigParser,urllib,urllib2,logging,logging.handlers,csv,io,re
from ConfigParser import SafeConfigParser
from optparse import OptionParser
from suds.client import Client
from suds import WebFault
from suds.transport.https import HttpAuthenticated
from collections import defaultdict

# -----------=================-----------------
# handle parameters
# -----------=================-----------------

# define empty lists
result_set = []
results = []

#named options
try:
	keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
	section_name = options.get('server','default')
	api = options.get('api', '')
	searchkey = options.get('searchkey', '')
	searchvalue = options.get('searchvalue','SEP')
	describe = options.get('describe','false')
	query = keywords[0] #query = sys.argv[1]


except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

# -----------=================-----------------
# read config file
# -----------=================-----------------
# set path to .conf file
try:
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
# use user provided options or get [default] stanza options
try:
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
# check if there are dangerous sql commands in the query
# -----------=================-----------------
queryblacklist = parser.get(section_name, 'queryblacklist')

#pattern = re.compile('INSERT|DROP|ALTER|DEL|APPEND|UPDATE', re.IGNORECASE)
pattern = re.compile(queryblacklist, re.IGNORECASE)
match = pattern.search(query)
if match:
	#print 'Error: you tried to modify or use a forbidden command: ', match.group()
	splunk.Intersplunk.generateErrorResults('Error: you tried to modify or use a forbidden command: %s' % match.group())
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

#results = []
results = defaultdict(set)
try:
	result = client.service.executeSQLQuery(sql=query)
except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

if result["return"] == "":
	result_list = []
else:
	result_list = [ dict(n) for n in result['return']['row'] ]
	header = dict(result['return']['row'][0]).keys()

splunk.Intersplunk.outputResults(result_list)