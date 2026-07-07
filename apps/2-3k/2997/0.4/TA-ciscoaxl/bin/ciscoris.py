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
from suds.cache import NoCache
import requests  
import xml.etree.ElementTree  
from requests.auth import HTTPBasicAuth 
import splunk.mining.dcutils as dcu 
from time import sleep
from itertools import izip_longest
import time
start_time = time.time()

#model='255'  #all
Debugging="no"

def setup_logging(n):
    logger = dcu.getLogger()
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
    logger = setup_logging("ciscoris")
    #logger.info( "INFO: Go Go Gadget Go!" )

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
    #logger.info( "getting Splunk options..." )
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    section_name = options.pop('server','default') #stanza in the .conf in ../local/
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
    #logger.info( "INFO: no option provided using [default]!" )

# -----------=================-----------------
# read config file
# -----------=================-----------------

# set path to .conf file
try:
    #logger.info( "read the .conf..." )
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
    #logger.info( "read the default options from .conf..." )
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
# the padding for the array of devices. The soap/wsdl is broken anyway, this is waaaay faster
# -----------=================-----------------

prefix_xml = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<soapenv:Body>
<ns1:SelectCmDevice xmlns:ns1="http://schemas.cisco.com/ast/soap/" soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<StateInfo/>
<CmSelectionCriteria xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns2="http://schemas.cisco.com/ast/soap/" soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xsi:type="ns2:CmSelectionCriteria">
<MaxReturnedDevices>200</MaxReturnedDevices>
<Class>Phone</Class>
<Model>255</Model>
<Status>Any</Status>
<SelectBy>Name</SelectBy>
<SelectItems soapenc:arrayType="ns2:SelectItem[2]" xsi:type="soapenc:Array">"""

postfix_xml="""
</SelectItems>
</CmSelectionCriteria>
</ns1:SelectCmDevice>
</soapenv:Body>
</soapenv:Envelope>"""

# -----------=================-----------------
# request the webservice
# -----------=================-----------------
#cmserver = SERVER
location = 'https://' + SERVER + ':' + '8443' + '/realtimeservice/services/RisPort'
username = USERNAME
password = PASSWORD

try:
    #loop over the items in the result, combine a maximum of 200, post the request, wait a few seconds and get the next 200... add all to the results set and move on.
    list_xml = ""
    for item in results:
        #logger.info("results loop item")
        #do chunks of 200 max - handled by streaming=true and maxinputs=200

        result = {}        
        searchvalue = item.get('name', None)
        if searchvalue != None:
            #logger.info("searchvalue: " + searchvalue)
            list_xml = list_xml + """<item xmlns:ns3="http://schemas.cisco.com/ast/soap/" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" soapenv:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xsi:type="ns3:SelectItem"><Item>{}</Item></item>""".format(searchvalue)

            
    try: #get the intermediate results
        raw_xml = prefix_xml + list_xml + postfix_xml # all in one go
        #logger.info("request: -----==============------------\n" + raw_xml)
        headers={'SOAPAction': '"http://schemas.cisco.com/ast/soap/action/#RisPort#SelectCmDeviceExt"',   
                 'Content-Type': 'text/xml; charset=utf-8'}  
        response=requests.post(location,data=raw_xml,headers=headers, auth=HTTPBasicAuth(username, password),verify=False)  
        #logger.info("response: -----==============------------\n" + response.text)
        tree = xml.etree.ElementTree.fromstring(response.text)  
        CmNodes = tree.find("{http://schemas.xmlsoap.org/soap/envelope/}Body").find("{http://schemas.cisco.com/ast/soap/}SelectCmDeviceResponse").find("SelectCmDeviceResult").find("CmNodes")
        if "ns1:Server.RateControl" in response.text: 
            logger.error("we hit rate limit, we were too fast!")
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

    #logger.info(CmNodes)
    for item in results: # merge both result sets
        # Here we are going to add the gathered info to the results set
        for node in CmNodes: 
            #logger.info("checking node...")
            for devs in node.find("CmDevices"):
                if devs.find('Name').text == item['name']: # match made in heaven :-)
                    #logger.info("handling node: " + devs.find('Name').text)
                    item['risname'] = devs.find('Name').text
                    item['IpAddress'] = devs.find('IpAddress').text
                    item['Status'] = devs.find('Status').text
                    item['LoginUserId'] = devs.find('LoginUserId').text
                    item['DirNumber'] = devs.find('DirNumber').text
                    item['Class'] = devs.find('Class').text
                    item['Model'] = devs.find('Model').text
                    item['Product'] = devs.find('Product').text
                    item['BoxProduct'] = devs.find('BoxProduct').text
                    item['Httpd'] = devs.find('Httpd').text
                    item['RegistrationAttempts'] = devs.find('RegistrationAttempts').text
                    item['IsCtiControllable'] = devs.find('IsCtiControllable').text
                    item['Status'] = devs.find('Status').text
                    item['StatusReason'] = devs.find('StatusReason').text
                    item['PerfMonObject'] = devs.find('PerfMonObject').text
                    item['DChannel'] = devs.find('DChannel').text
                    item['Description'] = devs.find('Description').text

    splunk.Intersplunk.outputResults( results )
    need_to_wait = 4 - (time.time() - start_time)
    logger.info("we spent " + str((time.time() - start_time)) + " seconds processing...")
    # rate limiter "el cheapo"
    if need_to_wait > 0:
        sleep("speed deamon, we were to fast - we need to wait an additional " + need_to_wait)
    logger.info("done here...")

except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
    #print result # so we know whats going on
