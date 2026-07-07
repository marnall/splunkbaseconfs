# Author: Dominique Vocat
# contact the prtg api via REST and queries stuff, returns the json to splunk.

import sys,splunk.Intersplunk,os,ConfigParser,urllib,urllib2,json,logging,logging.handlers,time
from ConfigParser import SafeConfigParser
from optparse import OptionParser

Debugging="no"

min_time_key    = "info_min_time"
max_time_key    = "info_max_time"
query_id_key    = "info_search_time"
search_name_key = "search_name"
infinity        = 10E200

(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)

if isgetinfo:
    #  outputInfo(streaming, generating, retevs, reqsop, preop, timeorder=False, clear_req_fields=False, req_fields = None)
    splunk.Intersplunk.outputInfo(False,     False,      False,  True,   "| rest /services/search/jobs count=1 | addinfo", False)

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
	LOGGING_FILE_NAME = "prtg.log"
	BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
	LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
	splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
	splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
	logger.addHandler(splunk_log_handler)
	splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
	return logger

# start the logger
try:
	logger = setup_logging("prtgws")
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
       # example /api/table.xml?content=groups&output=csvtable&columns=objid,probe,group,name,downsens,partialdownsens,downacksens,upsens,warnsens,pausedsens,unusualsens,undefinedsens
       #only for table view
	content = options.get('content', 'messages')
	count = options.get('count', '500')
	columns = options.get('columns', '') # default could be: objid,datetime,parent,type,name,status,message
	#objtype = options.get('objtype','All') #used in api="search" only

	#===========  get search time info ===================
	#results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
	if api == "historicdata":
		try:
			results = splunk.Intersplunk.readResults(None, None, True)
			min_time = results[0]["info_min_time"]
			max_time = results[0]["info_max_time"]
			#example /api/historicdata.csv?id=objectid&avg=0&sdate=2009-01-20-00-00-00&edate=2009-01-21-00-00-00
			#only for historical data - dateformat is yyyy-mm-dd-hh-mm-ss
			sdate = str(time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(float(min_time))))
			#sdate = options.get('sdate','')
			edate = str(time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(float(max_time))))
			#edate = options.get('sdate','')
		except Exception, e:
			import traceback
			stack =  traceback.format_exc()
			splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	id = options.get('id','')
	avg = options.get('avg','0') # 0 is all, default

	results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

	mystarttime= options.get('starttime', '')
	myendtime = options.get('endtime', '')
	logger.info( "mystarttime " + mystarttime)
	logger.info( "myendtime " + myendtime)

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
	configLocalFileName = os.path.join(scriptDir,'..','local','prtg.conf')
	#print configLocalFileName
	parser = SafeConfigParser()
	# read .conf options if empty use settings from [default] in prtg.conf
	parser.read(configLocalFileName)
	if not os.path.exists(configLocalFileName):
		splunk.Intersplunk.generateErrorResults(': No config found! Check your prtg.conf in local.')	
		exit(0)

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	logger.error( "ERROR: No config found! Check your prtg.conf in local." )

# use user provided options or get [default] stanza options
try:
	logger.info( "read the default options from .conf..." )
	SERVER = parser.get(section_name, 'server')
	PROTOCOL = parser.get(section_name, 'protocol')
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
    if api == "table":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        url=PROTOCOL+"://"+SERVER+"/api/table.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'output' : 'csvtable',
                 'count' : count,
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "messages":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        if columns == '':
            columns="objid,datetime,parent,type,name,status,message"
        url=PROTOCOL+"://"+SERVER+"/api/table.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : api,
                 'output' : 'csvtable',
                 'count' : count,
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "history":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        if columns == '':
            columns="dateonly,timeonly,user,message"
        url=PROTOCOL+"://"+SERVER+"/api/table.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : api,
                 'output' : 'csvtable',
                 'count' : count,
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "sensortree":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        url=PROTOCOL+"://"+SERVER+"/api/table.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : api,
                 'count' : count,
                 'output' : 'xml',
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "devices":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        if columns == '':
            columns="objid,group,device,sensor,status,priority,favorite"
        url=PROTOCOL+"://"+SERVER+"/api/table.csv"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : api,
                 'output' : 'csvtable',
                 'count' : count,
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "sensors":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        if columns == '':
            columns="objid,group,device,sensor,status,priority,favorite"
        url=PROTOCOL+"://"+SERVER+"/api/table.csv"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : api,
                 'output' : 'csvtable',
                 'count' : count,
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "alarms":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        if columns == '':
            columns="objid,group,device,sensor,status,priority,favorite"
        url=PROTOCOL+"://"+SERVER+"/api/table.csv"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : 'sensors',
                 'count' : count,
                 'output' : 'csvtable',
                 'count' : '*',
                 #'filter_status' : '4,5,10',
                 #'filter_status' : '5',
                 #'filter_status' : '10',
                 'columns' : columns}
        data = urllib.urlencode(values)

    if api == "tickets":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        if columns == '':
            columns= "name,tags,status,message,priority,datetime,tickettype,modifiedby"
        url=PROTOCOL+"://"+SERVER+"/api/table.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : api,
                 'output' : 'csvtable',
                 'count' : count,
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "groups":
        #url="https://"+SERVER+"/wapi/v1.2.1/"+api
        if columns == '':
            columns= "objid,probe,group,name,downsens,partialdownsens,downacksens,upsens,warnsens,pausedsens,unusualsens,undefinedsens"
        url=PROTOCOL+"://"+SERVER+"/api/table.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'content' : api,
                 'output' : 'csvtable',
                 'count' : count,
                 'columns' : columns,
                 'id' : id}
        data = urllib.urlencode(values)

    if api == "historicdata":
        url=PROTOCOL+"://"+SERVER+"/api/historicdata.csv"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'id': id,
                 'sdate' : sdate,
                 'edate' : edate,
                 'avg' : avg}
        data = urllib.urlencode(values)

    if api == "sensordetails":
        url=PROTOCOL+"://"+SERVER+"/api/getsensordetails.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'id': id}
        data = urllib.urlencode(values)

    if api == "status":
        url=PROTOCOL+"://"+SERVER+"/api/getstatus.xml"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'id': '0'}
        data = urllib.urlencode(values)

    if api == "sensortypes":
        url=PROTOCOL+"://"+SERVER+"/api/sensortypesinuse.json"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD}
        data = urllib.urlencode(values)

    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, USERNAME, PASSWORD)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    pagehandle = urllib2.urlopen(url+"?"+data)


    # -----------=================-----------------
    # handle json2splunk
    # -----------=================-----------------

    #results=json.loads(pagehandle.read())
    #results=pagehandle.read()

    if api == "sensordetails":
        #results=json.loads(pagehandle.read())
        results=pagehandle.read()
        results = results.replace("\r","")
        results = results.replace("\n","")
        print "_raw\n"+results #splunk.Intersplunk.outputResults( results )
    elif api == "sensortree":
        #results=json.loads(pagehandle.read())
        results=pagehandle.read()
        results = results.replace("\r","")
        results = results.replace("\n","")
        print "_raw\n"+results #splunk.Intersplunk.outputResults( results )
    elif api == "sensortypes":
        results=json.loads(pagehandle.read())
        print results # splunk.Intersplunk.outputResults( results )
    elif api == "status":
        results=pagehandle.read()
        results = results.replace("\r","")
        results = results.replace("\n","")
        print "_raw\n"+results # splunk.Intersplunk.outputResults( results )
    else:
        results=pagehandle.read()
        print results
    #splunk.Intersplunk.outputResults( results )

except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

