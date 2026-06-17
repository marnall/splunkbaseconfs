import logging
import logging.handlers
import os
import re
import select
import socket
import ssl
import sys
import urllib
from collections import deque
import json


from excel_export.clients.async_http_client import AsyncHTTPRequest


SPLUNK_HOME = os.environ.get('SPLUNK_HOME')
LOG_FILENAME = os.path.join(SPLUNK_HOME, 
                            'var', 'log', 'splunk',
                            'json_http_client.log')

logger = logging.getLogger('json_https_client')
logger.setLevel(logging.WARN)
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME,
                                               maxBytes=1024000,
                                               backupCount=5)
f = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(f)
handler.setLevel(logging.WARN)
logger.addHandler(handler)

class JSONHttpsClient:
    def __init__(self, host, port, use_ssl, user, token, 
                 search, namespace, parameters, callback,
                 sid=None, etype=None, page_size=100):
        self.callback = callback 
        self.host = host
        self.use_ssl = use_ssl
        self.parameters = parameters
        self.port = port
        self.search = search.strip()
        self.user = user
        self.session_key = token
        self.page_size = page_size
        self.decoder = json.JSONDecoder()
        self.count = 0
        
        self.ibuffer =  deque()
        self.frag = ''

        scheme = "http"

        self.headers = headers = {  
            "User-Agent" : "excel-json-client/0.1",
            "Host":  "%s:%s" %(host,port),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Authorization": "Splunk %s" % token
        }

        if use_ssl:
            scheme = "https"

        if sid:
            self.path = '/servicesNS/%s/%s/search/jobs/%s/%s/export'\
                            % (user, namespace, sid, etype)
        else:
            self.path = '/servicesNS/%s/%s/search/jobs/export' % (user, namespace)
            if not self.search.strip().startswith(('search ', '|')):
                self.search = 'search ' + self.search
            self.parameters['search'] = self.search

        path = self.path
        qstr = urllib.urlencode(self.parameters)
        url = scheme + '://' + host + ":" + str(port) + path + "?" + qstr

        logger.debug("creating raw connection to %s on port %s" % (self.host, self.port))

        try:
            AsyncHTTPRequest(url,headers=headers,closed=self.handle_close,
                body=self.handle_body, response=self.handle_response)
            logger.debug("connection to %s on port %s succeeded" % (self.host, self.port))
        except:
            logger.error("connection to %s on port %s failed" % (self.host, self.port))
            raise

    # APP-815:  JsonHttpsClient now enocdes JSON objects ASAP intead of waiting    
    def enqueue(self):
        try:
            """ use raw_decode to handle dangling comma from splunk4 """
            (json_obj,index) = self.decoder.raw_decode(self.frag)
            self.ibuffer.append(json_obj)
        except:
            logger.error('!!!json decode failed!!!')
        self.frag = ''

    ''' callback for async_http_client ''' 
    def handle_close(self):
        """ Flush callback """

        logger.debug('closing connection to %s on port %s' % (self.host, self.port))
        self.enqueue()
        self.flush_buffer()
        self.callback.close()

    ''' callback for async_http_client ''' 
    def handle_body(self,data):
        """ Pass JSON-like structures to callback """
        for line in data.splitlines():
            ''' don't do rstrip... no guarantee , is not in the middle of a
                valid datastream. we will defer to raw_decode
            '''
            logger.debug(line)
            if self.frag.endswith(('}','},')) and line.startswith('{'):

                self.enqueue()
                self.frag = line
            else:
                self.frag += line

            ''' add 1 to buffer length so we dont flush on empty '''
            if not ((len(self.ibuffer) + 1) % self.page_size ):
                self.flush_buffer()


    ''' directly invoke callback.add_data with the json objects in our buffer
        TODO: we should just take a single callback as our init params. the 
        assumption about an add_data() method is dangerous
    '''
    def flush_buffer(self):
        self.count += len(self.ibuffer)
        logger.debug("record count: %d . flushing buffer." % self.count)
        for obj in self.ibuffer:
            self.callback.add_data(obj)
        self.ibuffer.clear()

    ''' callback for async_http_client '''
    def handle_response(self,obj,resp):
        logger.debug("server responded with %s" % resp.status)

