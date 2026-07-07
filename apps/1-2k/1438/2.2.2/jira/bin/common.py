import ConfigParser
import os
import logging

import splunk.bundle as sb
import splunk.Intersplunk as isp

def getSplunkConf():
   results, dummyresults, settings = isp.getOrganizedResults()
   namespace = settings.get("namespace", None)
   owner = settings.get("owner", None)
   sessionKey = settings.get("sessionKey", None)

   conf = sb.getConf('jira', namespace=namespace, owner=owner, sessionKey=sessionKey)
   stanza = conf.get('jira')

   return stanza

def getLocalConf():
   local_conf = ConfigParser.ConfigParser()
   location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
   local_conf.read(location + '/config.ini')

   return local_conf

def flatten(item, keys):
   response = {}
   for (key, replacer) in keys:
      if not replacer:
         response[key] = str(item[key])
      else:
         response[key] = replacer.get(item[key], item[key])

   return response

def api_to_dict(apidata):
   dictdata = {}
   for item in apidata:
      dictdata[item['id']] = item['name']
   return dictdata



LOG_FILENAME = os.path.join(os.environ.get('SPLUNK_HOME'),
                         'var','log','splunk', 
                         'jira.log')
logger = logging.getLogger('jira')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, 
                                               maxBytes=5124800, 
                                               backupCount=4)
f = logging.Formatter("%(asctime)s %(levelname)s %(lineno)d %(message)s")
handler.setFormatter(f)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

   