import sys
import time
import urllib
import util

import splunk.Intersplunk
import splunk.rest

logger = util.get_logger()

'''
Commands: cleankvstore
Optional arguments: <ttl-in-seconds>
Description: This command is used to clear the data which reaches MAX_TTL. Default TTL is 86400(s).
'''


MAX_TTL_IN_SECONDS = 86400  #default ttl is 1 day
CURRENT_TIMESTAMP = int(time.time())
COLLECTIONS = ["kpi_search_collection", "request_search_collection"]
APP_NAME = "splunk_app_akamai"

if len(sys.argv) >= 2:
    try:
        MAX_TTL_IN_SECONDS = int(sys.argv[1])
    except Exception, e:
        splunk.Intersplunk.parseError("invalid TTL. Usage: cleankvstore (<ttl-in-second>)")

settings = dict()
latestTimestamp = CURRENT_TIMESTAMP - MAX_TTL_IN_SECONDS
results = splunk.Intersplunk.readResults(settings = settings, has_header = True)
sessionKey = settings['sessionKey']

logger.debug("TTL:%d" % MAX_TTL_IN_SECONDS)
logger.debug("Timestamp:%d" % latestTimestamp)

query = urllib.urlencode({"query":'{"ts":{"$lt":%d}}' % latestTimestamp})
for collection in COLLECTIONS:
    url = '%s/servicesNS/nobody/%s/storage/collections/data/%s?%s' % \
          (splunk.rest.makeSplunkdUri(), APP_NAME, collection, query)
    response, content = splunk.rest.simpleRequest(url, sessionKey=sessionKey, method='DELETE', raiseAllErrors=True)
    logger.info('response: %s', response)

splunk.Intersplunk.outputResults(results)
