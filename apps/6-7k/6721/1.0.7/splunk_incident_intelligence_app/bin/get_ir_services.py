from __future__ import absolute_import
from __future__ import print_function

# encoding = utf-8
# Always put this line at the beginning of this file

import sys
import os
import json
import requests
import logging as logger
import incident_intelligence_util
from splunk_aoblib.rest_helper import TARestHelper

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
realm_to_gql_endpoint_dict = {"lab0": "https://app.lab0.signalfx.com", "rc0": "https://app.rc0.signalfx.com",
                              "us0": "https://app.signalfx.com", "us1": "https://app.us1.signalfx.com",
                              "au0": "https://app.au0.signalfx.com", "eu0": "https://app.eu0.signalfx.com",
                              "jp0": "https://app.jp0.signalfx.com", "mon0": "https://app.mon0.signalfx.com"}
gql_base_ep = "/v2/incidentintelligence/graphql"


def get_proxy(session_key):
    """ if the proxy setting is set. return a dict like
    {
    proxy_url: ... ,
    proxy_port: ... ,
    proxy_username: ... ,
    proxy_password: ... ,
    proxy_type: ... ,
    proxy_rdns: ...
    }
    """
    # return self.setup_util.get_proxy_settings()
    # using custom implementation instead of proxy_settings
    proxy_settings = incident_intelligence_util.get_web_proxy_config(session_key, logger)
    if proxy_settings is None:
        logger.info("Proxy is not set!")
        return {}
    return proxy_settings


def _get_proxy_uri(session_key):
    uri = None
    proxy = get_proxy(session_key)
    if proxy and proxy.get('proxy_url') and proxy.get('proxy_type'):
        uri = proxy['proxy_url']
        if proxy.get('proxy_port'):
            uri = '{0}:{1}'.format(uri, proxy.get('proxy_port'))
        if proxy.get('proxy_username') and proxy.get('proxy_password'):
            uri = '{0}://{1}:{2}@{3}/'.format(proxy['proxy_type'], proxy[
                'proxy_username'], proxy['proxy_password'], uri)
        else:
            uri = '{0}://{1}'.format(proxy['proxy_type'], uri)
    return uri


def send_http_request(session_key, url, method, parameters=None, payload=None, headers=None, cookies=None, verify=True,
                      cert=None, timeout=None, use_proxy=True):
    logger.info("send_http_request started")
    rest_helper = TARestHelper(logger)
    return rest_helper.send_http_request(url=url, method=method, parameters=parameters, payload=payload,
                                         headers=headers, cookies=cookies, verify=verify, cert=cert,
                                         timeout=timeout,
                                         proxy_uri=_get_proxy_uri(session_key) if use_proxy else None)


if __name__ == '__main__':

    global settings
    global sessionKey

    logger.info("---------------------------------------------------------------------------------------")
    logger.info("get_ir_services  starting")

    realm = ''
    org_id = ''
    sfx_token = ''
    collection_name = 'incident_intelligence_ir_services'

    try:
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('sfx_token='):
                    eqsign = arg.find('=')
                    sfx_token = arg[eqsign + 1:len(arg)]
                elif arg.lower().startswith('org_id='):
                    eqsign = arg.find('=')
                    org_id = arg[eqsign + 1:len(arg)]
                elif arg.lower().startswith('realm='):
                    eqsign = arg.find('=')
                    realm = arg[eqsign + 1:len(arg)]

        logger.info("realm=" + realm)
        logger.info("org_id=" + org_id)

        # Read splunk header and extract session key required to interact with the KV store.
        settings = incident_intelligence_util.get_settings(sys.stdin)
        sessionKey = settings.get('sessionKey')

        # get list of IR services
        headers = {"Content-Type": "application/json", "x-sf-token": sfx_token}

        query = """query GetServices {
                      iRServices {
                        id
                        name
                        isDisabled
                        workflows {
                          name
                          id
                          __typename
                        }
                        __typename
                      }
                    }"""

        variables = {}
        endpoint = realm_to_gql_endpoint_dict.get(realm) + gql_base_ep
        logger.info("endpoint={}".format(endpoint))

        # response = requests.post(
        #    url=endpoint,
        #    headers=headers,
        #    json={'query': query, 'variables': variables}
        # )
        response = send_http_request(sessionKey, endpoint, "POST",
                                     parameters=None,
                                     payload={'query': query, 'variables': variables},
                                     headers=headers, cookies=None, verify=True, cert=None,
                                     timeout=None, use_proxy=True)

        logger.info("IR services response={}".format(response))

        # get the response headers
        r_headers = response.headers
        # get the response body as text
        r_text = response.text
        # get response body as json. If the body text is not a json string, raise a ValueError
        r_json = response.json()
        # get response cookies
        r_cookies = response.cookies
        # get redirect history
        historical_responses = response.history
        # get response status code
        r_status = response.status_code

        logger.info("r_text={}".format(r_text))
        logger.info("r_json={}".format(r_json))
        logger.info("r_cookies={}".format(r_cookies))
        logger.info("historical_responses={}".format(historical_responses))
        logger.info("r_status={}".format(r_status))

        if r_status == 200:
            query = json.dumps({"org_id": org_id})

            service = incident_intelligence_util.get_service(sessionKey, myapp, logger)
            logger.info('Looking for existing record, query: ' + json.dumps(query))
            collection = service.kvstore[collection_name]
            if collection_name in service.kvstore:
                result = None
                try:
                    result = collection.data.query(query=query)
                    logger.info("result={}".format(result))
                    data = r_json.get('data')
                    logger.info("data={}".format(data))

                    # if collection is not empty for the org_id, then delete records for the org_id
                    if len(result) > 0:
                        collection.data.delete(query=query)

                    for service in data['iRServices']:
                        logger.info("service={}".format(service))
                        service_id = service.get('id')
                        service_name = service.get('name')
                        logger.info("service_id={}".format(service_id))
                        logger.info("service_name={}".format(service_name))
                        workflow_id = ''
                        for workflow in service['workflows']:
                            logger.info("workflow={}".format(workflow))
                            workflow_id = workflow.get('id')
                            logger.info("workflow_id={}".format(workflow_id))

                        record = {"org_id": org_id,
                                  "name": service_name,
                                  "id": service_id,
                                  "workflow_id": workflow_id
                                  }

                        # insert the records into KV store collection
                        collection.data.insert(json.dumps(record))
                except Exception as e:
                    logger.error('Error with updating test_result. Query: ' + json.dumps(query))
                    logger.error(e)
            else:
                logger.error('Unexpected error - [' + collection_name + '] collection not found in KV store!')

    except Exception as e:
        logger.error('Get IR services Exception:')
        logger.error(e)

    logger.info("get_ir_services completed")
    logger.info("---------------------------------------------------------------------------------------")
