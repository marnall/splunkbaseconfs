import sys
import os
import json
from future.moves.urllib.parse import urlencode
from future.moves.urllib.request import urlopen, Request
from future.moves.urllib.error import HTTPError, URLError
import logging

logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'splunk-input-control-center.log'])
logging.basicConfig(filename=logfile, level=logging.DEBUG)
from splunk.util import unicode 

def log_event(event,server_uri,session_key):
    logging.debug('Log_Event_QUERY_PARAMS: %s', str(event))
    logging.debug('Log_Event_QUERY_PARAMS: %s', str(server_uri))
    logging.debug('Log_Event_QUERY_PARAMS: %s', str(session_key))
    
    query = [('source', "splunk-input-control-center.log"), ('sourcetype', "splunk-input-control-center"), ('index', "_internal")]
    url = '%s/services/receivers/simple?%s' % (server_uri, urlencode(query))
    try:
        encoded_body = unicode(event).encode('utf-8')
        req = Request(url, encoded_body, {'Authorization': 'Splunk %s' % session_key})
        res = urlopen(req)
        logging.debug('Log_Event_QUERY_PARAMS: %s', str(res))
        
    except Exception as e:
        sys.stderr.write("ERROR Error sending receiver request: %s\n" % e)
        logging.debug('Log_Event_QUERY_PARAMS: %s', str(e))