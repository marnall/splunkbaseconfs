from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import time
from decimal import Decimal
import splunk.Intersplunk as si
import json
import logging as logger
import voUtils

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','victorops_set_test_alert.log'),
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

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'victorops_app', 'lib']))
import splunklib.client as client
import splunk.rest
from splunk.clilib.bundle_paths import make_splunkhome_path

myapp = 'victorops_app'

def unquote(s):
    """unquote('abc%20def') -> 'abc def'."""
    mychr = chr
    myatoi = int
    list = s.split('%')
    res = [list[0]]
    myappend = res.append
    del list[0]
    for item in list:
        if item[1:2]:
            try:
                myappend(mychr(myatoi(item[:2], 16))
                     + item[2:])
            except ValueError:
                myappend('%' + item)
        else:
            myappend('%' + item)
    return "".join(res)

# Internal method to read command header from splunk.
def getSettings(input_buf):

    settings = {}
    # get the header info
    input_buf = sys.stdin
    # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
    attr = last_attr = None
    while True:
        line = input_buf.readline()
        line = line[:-1] # remove lastcharacter(newline)
        if len(line) == 0:
            break

        colon = line.find(':')
        if colon < 0:
            if last_attr:
               settings[attr] = settings[attr] + '\n' + unquote(line)
            else:
               continue

        # extract it and set value in settings
        last_attr = attr = line[:colon]
        val  = unquote(line[colon+1:])
        settings[attr] = val

    return(settings)

if __name__ == '__main__':

    global settings
    global sessionKey

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("setTestResult  starting");

    api_key = ''
    test_result = ''
    collection_name = 'mycollection'

    try:
        print ("Status")
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('api_key='):
                    eqsign = arg.find('=')
                    api_key = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('test_result='):
                    eqsign = arg.find('=')
                    test_result = arg[eqsign+1:len(arg)]

        logger.info("api_key="+api_key);
        logger.info("test_result="+test_result);
        # Read splunk header and extract session key required to interact with the KV store.
        settings = getSettings(sys.stdin);

        sessionKey = settings.get('sessionKey');

        query=json.dumps({"api_key": api_key});
        service = voUtils.getService(sessionKey, myapp, logger);
        logger.info('Looking for existing record, query: ' + json.dumps(query));
        collection = service.kvstore[collection_name];
        if collection_name in service.kvstore:
            result = None;
            try:
                result = collection.data.query(query=query);
                if len(result) > 0:
                    record = { "org_name" : result[0].get('org_name'),
                           "api_key": api_key,
                           "routing_key": result[0].get('routing_key'),
                           "is_default" : result[0].get('is_default'),
                           "test_result" : test_result
                    }

                    # Update test_result
                    logger.info('Found existing record, updating, result: ' + json.dumps(result) +
                                ', update record:  ' + json.dumps(record));
                    collection.data.update(result[0].get('_key'), json.dumps(record));
                    print ("SUCCESS")
                else:
                    logger.info("Record Not Found")
                    print ("FAIL")
            except Exception as e:
                print ("FAIL")
                logger.error('Error with updating test_result. Query: ' + json.dumps(query));
                logger.error(e);
        else:
            print ("FAIL")
            logger.error('Unexpected error - [' + collection_name + '] collection not found in KV store!');


    except Exception as e:
        print ("FAIL")
        logger.error('alert recovery Exception:');
        logger.error(e);

    logger.info("setTestResult  completed");
    logger.info("---------------------------------------------------------------------------------------")
