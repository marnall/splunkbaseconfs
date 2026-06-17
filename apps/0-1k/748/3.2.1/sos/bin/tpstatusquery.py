from splunk import rest
import urllib
import sys
import re
import os, time
import splunk
import splunk.entity as en
import splunk.auth as sa
import splunk.Intersplunk as si
import splunk.clilib.cli_common as comm
from common import get_sos_server, get_btool_internal_host
from xml.dom.minidom import parseString
import logging as logger
logger.basicConfig(level=logger.DEBUG, format='%(asctime)s %(levelname)s %(message)s',
                   filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','entity.log'),
                   filemode='a')
import lxml.etree as etree
SNS="http://dev.splunk.com/ns/rest"


if sys.platform == "win32":
   import msvcrt
   msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)


def usage():
    si.generateErrorResults("Usage: entity <endpoint>")
    exit(0)


def execute():
    try:
 
        results,dummyresults,settings = si.getOrganizedResults()
        args = { 'namespace':'search'}
        # get commandline args
        keywords, options = si.getKeywordsAndOptions()
        # override default args with commandline args
        args.update(options)
        args.update(settings)
        # updating settings allows us to inherit sessionKey for use later
        sessionKey = args.get("sessionKey", None)
        mgmt       = comm.getMgmtUri()
        owner      = args.get("owner", 'admin')
        namespace  = args.get("namespace", None)
        count      = args.get("count", '-1')
        targetserver= args.get("targetserver", None)
        if namespace.lower() == "none":
            namespace = None
        messages = {}
        if sessionKey == None:
            # this shouldn't happen, but it's useful for testing.
            try:
                sessionKey = sa.getSessionKey('admin', 'changeme')
                si.addWarnMessage(messages,  "No session given to 'entity' command. Using default admin account and password.")
            except splunk.AuthenticationFailed, e:
                si.addErrorMessage(messages, "No session given to 'entity' command.")
                return
        if len(keywords) != 1:
            usage()
        # e.g., '/data/inputs/monitor'
        entity = keywords[0]
        logger.info("Entity: %s Args: %s" % (entity, args))
        # we don't care about incoming results
        results = []
        try:
            sos_server = get_sos_server()
            # give us the host based on the monitor endpoint and compare to the targetserver provided in the args
            checkpath=('$SPLUNK_HOME','var','log','splunk')
            checkjoin= urllib.quote(os.path.join(*checkpath),safe="")
            dom = parseString(rest.simpleRequest(mgmt+"/servicesNS/nobody/system/admin/monitor/"+checkjoin,sessionKey=sessionKey)[1])


            checkendpoint=dom.getElementsByTagName('s:key')
            for elements in checkendpoint:
              if elements.attributes['name'].value == "host":
                retrievedhost= elements.childNodes[0].nodeValue
            if retrievedhost == None:
                retrievedhost = get_btool_internal_host()
  
            if targetserver != retrievedhost:
                exit()
            raw={}
            i=0
            # stream the read from the tailing processor endpoint and assign k/v pairs
            for fullpayload in etree.XML(rest.streamingRequest(mgmt+"/servicesNS/nobody/system/"+entity, sessionKey=sessionKey, timeout=90).response.read()):
                for records in fullpayload.findall(".//{%s}key[@name='inputs']/{%s}dict/{%s}key[@name]" % (SNS,SNS,SNS)):
                   item=str(records.attrib["name"])
                   if None!=records.find(".//{%s}key[@name='type']" % SNS):
                     type=records.find(".//{%s}key[@name='type']" % SNS).text
                     if None!=re.search("\'(.*)\'",type):
                      filter=re.search("\'(.*)\'",type).group(0)
                     else:
                      filter="None"
                   else:
                     type="None"
                   if None!=records.find(".//{%s}key[@name='percent']" % SNS):
                      percent=float(records.find(".//{%s}key[@name='percent']" % SNS).text)
                   else:
                      percent="None"
                   if None!=records.find(".//{%s}key[@name='file size']" % SNS):
                      file_size=float(records.find(".//{%s}key[@name='file size']" % SNS).text)
                   else:
                      file_size="None"
                   if None!=records.find(".//{%s}key[@name='file position']" % SNS):
                      file_position=float(records.find(".//{%s}key[@name='file position']" % SNS).text)
                   else:
                      file_position="None"
                   if None!=records.find(".//{%s}key[@name='parent']" % SNS):
                      parent=records.find(".//{%s}key[@name='parent']" % SNS).text
                   else:
                      parent="None"
                   raw['Item'] = item
                   raw['File_Size']=str(file_size)
                   raw['Parent']=parent
                   raw['Percent']=percent
                   raw['File_Position']=file_position
                   raw['sos_server']=sos_server
                   raw['Filter']=filter
                   raw['Status']=type
                   raw['_time']=str(time.time())
                   results.append(raw)
                   i=i+1
                   # grab 35000 row chunks for sending out to pipeline. If less than 20000 in the last chunk  send whatever is left to the pipeline
                   if (i==35000):
                      si.outputStreamResults(results)                  
                      results=[]
                      i=0
                   if (records.getnext() == None):
                      si.outputStreamResults(results)

                   raw={}

        except splunk.ResourceNotFound,e2:
            si.generateErrorResults(str(e2))            
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        logger.error(str(e) + ". Traceback: " + str(stack))
        si.generateErrorResults(str(e))
if __name__ == '__main__':
    execute()


