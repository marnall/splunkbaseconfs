# encoding = utf-8

import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # canary_console = definition.parameters.get('canary_console', None)
    pass

def collect_events(helper, ew):

    helper.log_info('TA-thinkst-canary: = = Start Log  = =')

    # Get account information
    global_account = helper.get_arg('canary_console')
    domain_hash = global_account['username']
    api_key = global_account['password']
    
    if not domain_hash.endswith('.canary.tools'):
        domain_hash += '.canary.tools'
        helper.log_info('TA-thinkst-canary: Canary Console hosted at = ' + str(domain_hash))

    # Get proxy configuration
    proxy = helper.get_proxy()

    if proxy:
        helper.log_info('TA-thinkst-canary: Proxy is set')
        helper.log_debug('TA-thinkst-canary: ' + 'Proxy Type: ' + str(proxy['proxy_type']) + ', Proxy URL: ' + str(proxy['proxy_url']) + ', Proxy Port: ' + str(proxy['proxy_port']))
        
        if proxy['proxy_username']:
            helper.log_info('TA-thinkst-canary: Proxy is configured for authentication')
        
        else:
            helper.log_info('TA-thinkst-canary: Proxy is configured without authentication')
            
        proxy_config = True
    
    else:
        helper.log_info('TA-thinkst-canary: Proxy is not set')
        
        proxy_config = False
 
    try:
        ta_version = [ i for i in helper.service.apps.list() if i.name == helper.app][0].content['version']
        helper.log_info('TA-thinkst-canary: TA version retrieved = ' + str(ta_version))
    except:
        ta_version = 'N/A'
        helper.log_info('TA-thinkst-canary: No TA version available.')
    try:
        splunk_version =  helper.service.info['version']
        helper.log_info('TA-thinkst-canary: Splunk version retrieved = ' + str(splunk_version))
    except KeyError:
        splunk_version = 'Unknown_version'
        helper.log_info('TA-thinkst-canary: No Splunk version available.')
    headers = {'User-Agent': 'Splunk API Call TA-Canary ({ta_version}) Splunk ({splunk_version}) '.format(ta_version=ta_version, splunk_version=splunk_version),
               'X-Canary-Auth-Token': api_key}

    fetch_time = int(time.time())
    user_count = 0
    # device_limit = 100
    parameters = {}
    url = "https://{}/api/v1/users/list".format(domain_hash)

    response = helper.send_http_request(url, 'GET', parameters=parameters, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        use_proxy=proxy_config, timeout=(10.0, 30.0))

    # while True:
    if response.status_code == 200:
        r_json = response.json()

        for user in r_json['users']:
            user['fetch_time'] = fetch_time
            user['canary_console'] = domain_hash
            event = helper.new_event(json.dumps(user), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
            ew.write_event(event)
            user_count += 1

    helper.log_info('TA-thinkst-canary: Number of users added = ' + str(user_count))
    helper.log_info('TA-thinkst-canary: = = End Log  = =')
