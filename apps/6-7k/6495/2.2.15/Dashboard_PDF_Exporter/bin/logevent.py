import sys
import json
import os
from future.moves.urllib.parse import urlencode
from future.moves.urllib.request import urlopen, Request
from future.moves.urllib.error import HTTPError, URLError
from splunk.util import unicode
import logging

# def log_event(settings, event, source, sourcetype, host, index):
#     if event is None:
#         sys.stderr.write("ERROR No event provided\n")
#         return False
#     query = [('source', source), ('sourcetype', sourcetype), ('index', index)]
#     if host:
#         query.append(('host', host))
#     url = '%s/services/receivers/simple?%s' % (settings.get('server_uri'), urlencode(query))
#     try:
#         encoded_body = unicode(event).encode('utf-8')
#         req = Request(url, encoded_body, {'Authorization': 'Splunk %s' % settings.get('session_key')})
#         res = urlopen(req)
#         if 200 <= res.code < 300:
#             sys.stderr.write("DEBUG receiver endpoint responded with HTTP status=%d\n" % res.code)
#             return True
#         else:
#             sys.stderr.write("ERROR receiver endpoint responded with HTTP status=%d\n" % res.code)
#             return False
#     except HTTPError as e:
#         sys.stderr.write("ERROR Error sending receiver request: %s\n" % e)
#     except URLError as e:
#         sys.stderr.write("ERROR Error sending receiver request: %s\n" % e)
#     except Exception as e:
#         sys.stderr.write("ERROR Error %s\n" % e)
#     return False

# def internal_logs(meta,event_dict,addon,host):
#         event = json.dumps(event_dict)
#         source = os.path.basename(sys.argv[0])
#         sourcetype = addon
#         index = '_internal'
#         log_event(meta, event, source, sourcetype, host, index)

# if __name__ == "__main__":
#     if len(sys.argv) < 2 or sys.argv[1] != "--execute":
#         sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
#         sys.exit(1)
#     try:
#         settings = json.loads(sys.stdin.read())
#         config = settings['configuration']
#         success = log_event(
#             settings,
#             event=config.get('event'),
#             source=config.get('source'),
#             sourcetype=config.get('sourcetype'),
#             host=config.get('host'),
#             index=config.get('index')
#         )
#         if not success:
#             sys.exit(2)
#     except Exception as e:
#         sys.stderr.write("ERROR Unexpected error: %s\n" % e)
#         sys.exit(3)


logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'Dashboard_PDF_Exporter.log'])
logging.basicConfig(filename=logfile, level=logging.DEBUG)


def log_event(event,server_uri,session_key):
    logging.debug('Log_Event_QUERY_PARAMS: %s', str(event))
    logging.debug('Log_Event_QUERY_PARAMS: %s', str(server_uri))
    logging.debug('Log_Event_QUERY_PARAMS: %s', str(session_key))
    
    query = [('source', "Dashboard_PDF_Exporter.log"), ('sourcetype', "Dashboard_PDF_Exporter"), ('index', "_internal")]
    url = '%s/services/receivers/simple?%s' % (server_uri, urlencode(query))
    try:
        encoded_body = unicode(event).encode('utf-8')
        req = Request(url, encoded_body, {'Authorization': 'Splunk %s' % session_key})
        res = urlopen(req)
        logging.debug('Log_Event_QUERY_PARAMS: %s', str(res))
        
    except Exception as e:
        sys.stderr.write("ERROR Error sending receiver request: %s\n" % e)
        logging.debug('Log_Event_QUERY_PARAMS: %s', str(e))