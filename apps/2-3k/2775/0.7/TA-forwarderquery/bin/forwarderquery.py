# Author: Dominique Vocat
# contact the forwarderquery api via REST and queries stuff, returns the json to splunk.

import sys,splunk.Intersplunk,os,ConfigParser
#os.environ['http_proxy']=''
import urllib,urllib2,json,logging,logging.handlers,time
from ConfigParser import SafeConfigParser
from optparse import OptionParser
import xml.etree.cElementTree as ET
import requests
import ast

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
	LOGGING_FILE_NAME = "forwarderquery.log"
	BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
	LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
	splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
	splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
	logger.addHandler(splunk_log_handler)
	splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
	return logger

# start the logger
try:
	logger = setup_logging("forwarderqueryws")
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
	#section_name = options.get('server','default')
	section_name = options.get('stanza','default')
	api = options.get('api', '')
	SERVER = options.get('server','localhost')
	METHOD = options.get('method','get')
	OFFSET = options.get('offset','0')

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

# set path to .conf file
try:
	logger.info( "read the .conf..." )
	scriptDir = sys.path[0]
	configLocalFileName = os.path.join(scriptDir,'..','local','forwarderquery.conf')
	#print configLocalFileName
	parser = SafeConfigParser()
	# read .conf options if empty use settings from [default] in forwarderquery.conf
	parser.read(configLocalFileName)
	if not os.path.exists(configLocalFileName):
		splunk.Intersplunk.generateErrorResults(': No config found! Check your forwarderquery.conf in local.')	
		exit(0)

except Exception, e:
	import traceback
	stack =  traceback.format_exc()
	splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
	logger.error( "ERROR: No config found! Check your forwarderquery.conf in local." )

# use user provided options or get [default] stanza options
try:
	logger.info( "read the default options from .conf..." )
	METHOD = options.get('method', 'GET')
	USERNAME = parser.get(section_name, 'user')
	PASSWORD = parser.get(section_name, 'password')
	PASSWORD = options.get('password', PASSWORD)
	PORT = parser.get(section_name, 'port')
	PORT = options.get('port', PORT)


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
    if api != "":
        url="https://"+SERVER+":"+PORT+api
        #print url        

    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, USERNAME, PASSWORD)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    
    if METHOD != "POST":
        print >> sys.stderr, "not a POST request"
        CONTENTTYPE = options.get('contenttype', 'xml')
        print >> sys.stderr, "CONTENTTYPE= " + str(CONTENTTYPE)
        if CONTENTTYPE == "json" or CONTENTTYPE == "json2": #hack!! cp00vtd 10.10.2016
            print >> sys.stderr, "trying to get json response"
            mydata = options.get('data', '')
            print >> sys.stderr, mydata
            if mydata:
                print >> sys.stderr, "we got parameters to encode"
                tmpdata = ast.literal_eval(mydata)
                #tmpdata.update(ast.literal_eval("{'output_mode':'json'}"))
                print >> sys.stderr, tmpdata
                pagehandle = requests.get(url, auth=(USERNAME, PASSWORD) , verify=False, data=tmpdata)
                print >> sys.stderr, pagehandle.url            
            else:
                print >> sys.stderr, "no further parameters to encode"
                tmpdata = ast.literal_eval("{'output_mode':'json'}")
                #tmpdata = ast.literal_eval("{'output_mode':'json', 'offset':'31'}")
                pagehandle = requests.get(url, auth=(USERNAME, PASSWORD) , verify=False, data=tmpdata)
                print >> sys.stderr, pagehandle.url
                #data = urllib.urlencode(tmpdata)
                #pagehandle = urllib2.urlopen(url,data)
        else:
            mydata = options.get('data', '')
            if mydata:
                print >> sys.stderr, "we have parameters to encode"
                tmpdata = ast.literal_eval(mydata)
                pagehandle = requests.get(url, auth=(USERNAME, PASSWORD) , verify=False, data=tmpdata)
                print >> sys.stderr, pagehandle.url
                print >> sys.stderr, pagehandle
                #pagehandle = urllib2.urlopen(url)
            else:
                #pagehandle = urllib2.urlopen(url)
                pagehandle = requests.get(url, auth=(USERNAME, PASSWORD) , verify=False)
                print >> sys.stderr, pagehandle.url

    if METHOD == "POST": #vtd - 15.08.2016 - allow to pass a parameter data with a notation like this: "{'key':'value','key2':'value2'}"
        print >> sys.stderr, "POST request"
        mydata = options.get('data', '')
        if mydata != "":
            import ast
            tmpdata = ast.literal_eval(mydata)
            data = urllib.urlencode(tmpdata)
            #print url+"?"+data
        else: 
            data = urllib.urlencode('')
        pagehandle = urllib2.urlopen(url,data)
        #print >> sys.stderr, pagehandle.url
        
#---
# can delete items in curl like so (system's output.conf defined indexer)
#  curl -k -u admin:xxxx  https://chhs-sadd101:8089/servicesNS/nobody/system/data/outputs/tcp/server/chhs-ssys001.helvetia.ch%3A9997 --request DELETE
#---
    if METHOD == "DELETE": #vtd - 11.10.2016 - handle DELETE, use requests library nalang
        print >> sys.stderr, "DELETE request"
        #import requests
        requests.delete(url, verify=False)
        #pagehandle = urllib2.urlopen(url,data)


# -----------=================-----------------
# handle json2splunk
# -----------=================-----------------

#results=json.loads(pagehandle.read())
    CONTENTTYPE = options.get('contenttype', '')
    if CONTENTTYPE == "json":
        results=json.dumps(pagehandle.json())
        #print >> sys.stderr, results
        import time
        now = int(time.time())            
        results = results.replace("\r","")
        results = results.replace("\n","")
        results = results.replace("\"","\"\"")
        results = "\"" + results + "\""
        print "_time,host,sourcetype,source,_raw\n "+str(now)+","+SERVER+",rest,"+url+","+results
    elif CONTENTTYPE == "json2":
        if pagehandle.status_code==200:
            data = json.loads(pagehandle.text)
            if "entry" in data:
                results = data["entry"]
                for row in results:
                    #decorate each list item with fields from the returned data
                    if "origin" in data: row["origin"]=data["origin"]
                    if "generator" in data: 
                        row["version"]=data["generator"]["version"]
                        row["build"]=data["generator"]["build"]
                    if "paging" in data: 
                        row["paging:total"]=data["paging"]["total"]
                        row["paging:offset"]=data["paging"]["offset"]
                        row["paging:perPage"]=data["paging"]["perPage"]
                    
                    #flatten notable data
                    if "acl" in row:
                        for acl in row["acl"]:
                            aclitem = str(acl)
                            row[aclitem] = row["acl"][acl]
                        row.pop("acl", None)
                        #alternatively return it as json                        
                        #row["acl"] = json.dumps(row["acl"])
                        #row["acl"].replace("\"", "'")
                    if "perms" in row:
                        if row["perms"] is not None: # there might be "None" values
                            for perm in row["perms"]:
                                permitem = str(perm)
                                row[permitem] = row["perms"][perm]
                            row.pop("perms", None)
                            #alternatively return it as json                        
                            #row["acl"] = json.dumps(row["acl"])
                            #row["acl"].replace("\"", "'")
                    if "content" in row:
                        for content in row["content"]:
                            contentitem = str(content)
                            row[contentitem] = row["content"][content]
                        row.pop("content", None)
                        #alternatively return it as json
                        #row["content"] = json.dumps(row["content"])
                        #row["content"].replace("\"", "'")
                    if "inputs" in row:
                        for field in row["inputs"]:
                            fielditem = str(field)
                            row[fielditem] = json.dumps(row["inputs"][field])
                        row.pop("inputs", None)
                        #alternatively return it as json
                        #row["content"] = json.dumps(row["content"])
                        #row["content"].replace("\"", "'")
                    if "fields" in row:
                        for field in row["fields"]:
                            fielditem = str(field)
                            row[fielditem] = row["fields"][field]
                        row.pop("fields", None)
                        #alternatively return it as json
                        #row["content"] = json.dumps(row["content"])
                        #row["content"].replace("\"", "'")
                    if "links" in row:
                        for link in row["links"]:
                            linkitem = str(link)
                            row[linkitem] = row["links"][link]
                            if linkitem == "alternate":
                                tmppath = row["links"][link][30:]
                                #if we have a filesystem link perform some additional work
                                if row["links"][link][:30] == "/services/admin/file-explorer/": #the url is double "unquoted" possibely due to unicode chars that might be contained
                                    fullpath = urllib.unquote_plus(urllib.unquote_plus(tmppath.encode('ascii')).decode('utf8')) #double url encoded. wee. darn.
                                    row["fullpath"] = fullpath
                                    row["path"] = row["fullpath"][:-len(row["name"])] # generate current path
                                    row["nav"] = "[+] "+row["name"]
                                if row["links"][link] == "/services/admin/file-explorer/":
                                    row["fullpath"] = "/"
                                    row["nav"] = "[-] / "
                        row.pop("links", None)
                        #alternatively return it as json
                        #row["links"] = json.dumps(row["links"])
                        #row["links"].replace("\"", "'")

                # prepend breadcrumbs for file paths in case we have at least one (self generated) fullpath
                tmp = results[0]
                print >> sys.stderr, tmp
                print >> sys.stderr, type(tmp)
                for item in tmp:
                    #decorate each list item with fields from the returned data
                    if "fullpath" in item:
                        fullpath=tmp[item]
                        os=""
                        row={}
                        row["fullpath"]=fullpath #"appended value"
                        row["debug"]="appended value"
                        if "\\" in fullpath: #windows
                            row["ospath"]="windows"
                            os="windows"
                            splitter="\\"
                            #row["parent"] = elements.join()
                        else: # 'nix
                            row["ospath"]="nix"
                            os="*nix"
                            splitter="/"
                            #row["parent"] = elements.join()
                        
                        elements = fullpath.split(splitter)
                        print >> sys.stderr, elements
                        print >> sys.stderr, type(elements)
                        
                        i=0
                        tmp=""
                        crumbs = []
                        if os=="windows": 
                            while i < len(elements) -1: # first element is kinda needed...
                                tmp += splitter+elements[i]
                                crumbs.append(tmp) #+"[-]"
                                i += 1
                        else:
                            while i < len(elements) -2: # no leading element before first split by token (leading /)
                                i += 1
                                tmp += splitter+elements[i]
                                crumbs.append(tmp) #+"[-]"
                        #while i < len(elements) -2:
                        #    tmp += splitter+elements[i]
                        #    crumbs.append(tmp) #+"[-]"
                        #    i += 1
                        print >> sys.stderr, crumbs
                        for item in crumbs:
                            crumb = {}
                            crumb["nav"]="[-] "+ item # unichr(2515)+ - not usable with roboto font
                            if os=="windows":
                                crumb["alternate"]="/services/admin/file-explorer/"+urllib2.quote(item,'') # windows it is single quoted. grrr.
                            else:                                
                                crumb["alternate"]="/services/admin/file-explorer/"+urllib2.quote(urllib2.quote(item,''),'') # danger - if os *nix then it is doublequoted instead of labeling slash not safe, if windows it is single quoted. grrr.
                            crumb["hasSubNodes"]="True"
                            crumb["breadcrumb"]="True"
                            crumb["fullpath"]=fullpath
                            crumb["path"]=fullpath
                            results.append(crumb)
                            #print item
                        #results.append(row)
                splunk.Intersplunk.outputResults(results)
            else:
                splunk.Intersplunk.generateErrorResults("nothing to show")
        else:
            splunk.Intersplunk.generateErrorResults("nothing to show, status code was: " + str(pagehandle.status_code))
    elif CONTENTTYPE == "xml":
        #results=pagehandle.read()
        results=pagehandle.text
        results = results.replace("\r","")
        results = results.replace("\n","")
        print "xmlresults\n "+results
    elif CONTENTTYPE == "raw":
        results = []
        result = {}
        result["_raw"] = pagehandle.text
        results.append(result)
        splunk.Intersplunk.outputResults(results)


except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
