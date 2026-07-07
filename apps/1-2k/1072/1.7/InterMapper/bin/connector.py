# InterMapper for Splunk App - InterMapper HTTP API Common Functions 

import logging

from urllib2 import urlopen, Request
from shutil import copyfileobj
from tempfile import TemporaryFile

class HTTPConnector(object):
    host = None
    port = None
    https = False
    logger = None
    getHeaders = None
    serverBaseURL = None

    def __init__(self, host='127.0.0.1', port=None, https=False, auth=None, logLevel=logging.INFO):
        # Fill local fields
        self.host = host
        self.https = https
        if self.https:
            protocol = 'https'
        else:
            protocol = 'http'
        self.port = port
        if (self.port != None):
            self.serverBaseURL = '%s://%s:%s' % (protocol, host, str(port))
        else:
            self.serverBaseURL = '%s://%s' % (protocol, host)
            
        if auth:
            self.getHeaders = {"Authorization": "Basic " + auth}

        # Logging Setup Code
        self.logger = logging.getLogger("splunk.apps.intermapper.connector")
        self.logger.setLevel(logLevel)

        # Log constructor completion
        self.logger.debug('action=\"Initializing Base URL\" url=\"%s\"', self.serverBaseURL)
        
        
    ## Core Function ##
    
    def getURL(self, relative_url, actionString='GETting URL'):
        try:
            url = '%s/%s' % (self.serverBaseURL, relative_url)
            self.logger.debug('action=\"%s\" url=\"%s\" message=\"begin\"', actionString, url)
            memoryFile = TemporaryFile()
            if self.getHeaders:
                request = Request(url=url, headers=self.getHeaders)
                urlBody = urlopen(request)
            else:
                urlBody = urlopen(url)
            copyfileobj(urlBody, memoryFile)
            urlBody.close()
            memoryFile.flush()
            memoryFile.seek(0)
            self.logger.debug('action=\"%s\" url=\"%s\" message=\"success\"', actionString, url)
            return memoryFile
#            return urlBody
        except Exception as e:
            self.logger.error('action=\"%s\" url=\"%s\" message=\"%s\"', actionString, url, str(e))
            raise
    
    ## Convenience Functions ##
    
    def getTable(self, tableName, fields=None, otherparams=None):
        actionString = 'GETting table'
        
        if (fields != None):
            if (otherparams!=None) and ("=" in otherparams):
                tableUrl = '~export/%s?fields=%s&%s' % (tableName, fields, otherparams)
            else:
                tableUrl = '~export/%s?fields=%s' % (tableName, fields)
        else:
            if (otherparams!=None) and ("=" in otherparams):
                tableUrl = '~export/%s?%s' % (tableName, otherparams)
            else: 
                tableUrl = '~export/%s' % (tableName)        
        self.logger.debug('HP-DEBUG: getTable(), tableName=\"%s\" url=\"%s\"', tableName, tableUrl)        
        return self.getURL(tableUrl, actionString)    
  
    def getMapImage(self, mapId, actionString='GETting map image'):
        req_url = "%s/document/main/*map.png" % (mapId)
        return self.getURL(req_url, actionString)
    
    def getMapBgImage(self, mapId, actionString='GETting map bg image'):
        req_url = "%s/document/main/*mapbg" % (mapId)
        return self.getURL(req_url, actionString)
    
    def getMapHTML(self, mapId, actionString='GETting map HTML'):
        req_url = mapId
        return self.getURL(req_url, actionString)
