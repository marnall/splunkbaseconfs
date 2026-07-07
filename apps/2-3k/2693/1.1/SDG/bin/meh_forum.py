import sys
import xml.etree.cElementTree as ET
import time
from time import gmtime, strftime, localtime
import logging as logger
import os
import urllib, urllib2

__author__ = "(Kyle Smith)"
_MI_APP_NAME = 'Meh-Forum-Input'

# Original Script courtosy of George Starcher, georgestarcher.com

#SYSTEM EXIT CODES
_SYS_EXIT_FAILED_SPLUNK_AUTH = 7

#OUTPUT OPTIONS
_DEBUG = 1
_LOG_ACTION = 1

# Setup Alert Script Logging File: will be picked up into index=_internal
os.umask(0)
outputFileName = _MI_APP_NAME+'-log.txt'
outputFileLog = os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk',outputFileName)
logger.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=outputFileLog, filemode='a+', level=logger.INFO, datefmt='%Y-%m-%d %H:%M:%S %z')
logger.Formatter.converter = time.gmtime

def versiontuple(v):
        return tuple(map(int, (v.split("."))))

def logDebug(s):
        """ print any extra debug info """
        if _DEBUG:
                logger.info("script="+_MI_APP_NAME+" %s" % str(s))

def logError(s):
        """ print any errors that occur """
        logger.error("script="+_MI_APP_NAME+" %s" % str(s))

def logAction(s):
        """ log events to show normal activity of the input script """
        if _LOG_ACTION:
                logger.info("script="+_MI_APP_NAME+" %s" % str(s))


def getSplunkVersion(sessionKey):
        """ function to obtain the Splunk software version. This is used to determine parsing of the sessionKey """

        from xml.dom import minidom

        base_url = 'https://localhost:8089'

        request = urllib2.Request(base_url + '/services/server/info',None,headers = { 'Authorization': ('Splunk %s' %sessionKey)})
        server_content = urllib2.urlopen(request)
        serverDoc = minidom.parseString(server_content.read())
        entryInfo = serverDoc.getElementsByTagName('entry')
        key_nodes = entryInfo[0].getElementsByTagName('content')[0].getElementsByTagName('s:key')
        nodes = filter(lambda node: node.attributes['name'].value == 'version', key_nodes)
        version = nodes[0].firstChild.nodeValue

        return(version)

def mehAPIKey(sessionKey):
        """ function to retrieve api key from configs """
        return "<api_key>"
        from xml.dom import minidom
        logDebug("action=get_api_key sessionkey=%s"%sessionKey)
        base_url = 'https://localhost:8089'

        request = urllib2.Request(base_url + '/servicesNS/admin/SDG/sdgep/conf',None,headers = { 'Authorization': ('Splunk %s' %sessionKey)})
        server_content = urllib2.urlopen(request)
        serverDoc = minidom.parseString(server_content.read())
        entryInfo = serverDoc.getElementsByTagName('entry')
        key_nodes = entryInfo[0].getElementsByTagName('content')[0].getElementsByTagName('s:key')
        nodes = filter(lambda node: node.attributes['name'].value == 'apikey', key_nodes)
        apikey = nodes[0].firstChild.nodeValue
        logDebug("action=get_api_key apikey=%s"%apikey)
        return(apikey)

def mehAPILogGet(sessionkey):
        logDebug("action=get_meh")
        apiURL = 'https://www.kimonolabs.com/api/ondemand/dx6xf5le?apikey=QpYn3yCTCAeFY7c5qqM3f754UcEWhlrd&kimmodify=1'
        logDebug("apiurl=%s"%apiURL)

        request = urllib2.Request(apiURL)
        response = urllib2.urlopen(request)

        return(response.read())


def get_logs(sessionkey):

        import json
        result = mehAPILogGet(sessionkey)
        r = json.loads(result)
        r["timestamp"] = "%s"%(strftime("%a, %d %b %Y %H:%M:%S %Z", localtime()))
        logDebug(json.dumps(r))
        print json.dumps(r)

        return()

def exitInputScript(a):
        if _DEBUG:
                logDebug("action=stopped")
        sys.exit(a)

if __name__ == "__main__":

        if _DEBUG:
                logDebug("action=started")

# Obtain the Splunk authentication session key

        # read session key sent from splunkd
        sessionKey = sys.stdin.readline().strip()

        if len(sessionKey) == 0:
                logError("Did not receive a session key from splunkd. ")
                exitInputScript(_SYS_EXIT_FAILED_SPLUNK_AUTH)

# Adjust the returned sessionKey text based on Splunk version

        try:
                splunkVersion = getSplunkVersion(sessionKey)
        except Exception, e:
                logError("type=splunkError error=%s" % str(e))

        try:
                if versiontuple(splunkVersion) < versiontuple("6.1.1"):
                        sessionKey = sessionKey[11:]
                else:
                        sessionKey = urllib.unquote(sessionKey[11:]).decode('utf8')
        except Exception, e:
                logError("type=splunkError error=%s" % str(e))
                exitInputScript(_SYS_EXIT_FAILED_SPLUNK_AUTH)

        logDebug("sessionKey="+sessionKey)
        logDebug("splunkVersion="+splunkVersion)

# Obtain and output the logs from meh

        try:
                get_logs(sessionKey)
        except Exception, e:
                logError("type=GetLogsError error=%s" % str(e))
                exitInputScript(_SYS_EXIT_FAILED_SPLUNK_AUTH)

        exitInputScript(0)
