from __future__ import absolute_import
from __future__ import print_function

# encoding = utf-8
# Always put this line at the beginning of this file

import sys
import os
import json
import logging as logger
import incident_intelligence_util

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',
                   datefmt='%m-%d-%Y %H:%M:%S.000 %z',
                   filename=os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk',
                                         'incident_intelligence_commands.log'),
                   filemode='a')
try:
    # For Python 3.0 and later
    from urllib.request import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, ProxyHandler, HTTPBasicAuthHandler, build_opener, install_opener, Request
try:
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import HTTPError

myapp = 'splunk_incident_intelligence_app'


if __name__ == '__main__':

    global settings
    global sessionKey

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("setTestResult  starting")

    org_id = ''
    test_result = ''
    collection_name = 'incident_intelligence_collection'

    try:
        print ("Status")
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('test_result='):
                    eqsign = arg.find('=')
                    test_result = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('org_id='):
                    eqsign = arg.find('=')
                    org_id = arg[eqsign+1:len(arg)]

        logger.info("org_id="+org_id)
        logger.info("test_result="+test_result)
        # Read splunk header and extract session key required to interact with the KV store.
        settings = incident_intelligence_util.get_settings(sys.stdin)

        sessionKey = settings.get('sessionKey')

        query = json.dumps({"org_id": org_id})
        service = incident_intelligence_util.get_service(sessionKey, myapp, logger)
        logger.info('Looking for existing record')
        collection = service.kvstore[collection_name]
        if collection_name in service.kvstore:
            result = None
            try:
                result = collection.data.query(query=query)
                if len(result) > 0:
                    record = {"realm": result[0].get('realm'),
                              "org_id": result[0].get('org_id'),
                              "is_default": result[0].get('is_default'),
                              "test_result": test_result
                              }

                    # Update test_result
                    logger.info('Found an existing record, updating the same record for orgId: ' +
                                result[0].get('org_id'))
                    collection.data.update(result[0].get('_key'), json.dumps(record))
                    print("SUCCESS")
                else:
                    logger.info("Record Not Found")
                    print("FAIL")
            except Exception as e:
                print("FAIL")
                logger.error('Error with updating test_result.')
                logger.error(e)
        else:
            print("FAIL")
            logger.error('Unexpected error - [' + collection_name + '] collection not found in KV store!')

    except Exception as e:
        print("FAIL")
        logger.error('alert recovery Exception:')
        logger.error(e)

    logger.info("setTestResult  completed")
    logger.info("---------------------------------------------------------------------------------------")
