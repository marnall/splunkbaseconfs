# encoding = utf-8

import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
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

    # Set checkpoint ID
    stanza_name = str(helper.get_input_stanza_names())
    helper.log_info('TA-thinkst-canary: Input Name = ' + str(stanza_name))
    
    stanza_checkpoint = str(stanza_name)

    # Set or create checkpoint 
    try:
        last_checkpoint = helper.get_check_point(stanza_checkpoint)
        if last_checkpoint is None:
            last_checkpoint = 0
        helper.log_info('TA-thinkst-canary: Checkpoint data retrieved = ' + str(last_checkpoint))

    except:
        helper.log_info('TA-thinkst-canary: No checkpoint data was found for this input.')
        pass
 
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

    event_count = 0
    parameters = {'limit': 1, 'after_id': last_checkpoint}
    url = "https://{}/api/v1/audit_trail/fetch".format(domain_hash)
    checkpoint_updated = False
    
    while True:
        response = helper.send_http_request(url, 'GET', parameters=parameters, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        use_proxy=proxy_config, timeout=(10.0, 30.0))

        r_json = response.json()
        try:
            if not checkpoint_updated and last_checkpoint < r_json['audit_trail'][0]['id']:
                new_checkpoint = r_json['audit_trail'][0]['id']
                helper.save_check_point(stanza_checkpoint, new_checkpoint)
                helper.log_info('TA-thinkst-canary: New checkpoint = ' + str(new_checkpoint))
                checkpoint_updated = True
        except:
            pass

        for audit_event in r_json['audit_trail']:
            audit_event['canary_console'] = domain_hash
            if audit_event['id'] <= int(last_checkpoint):
                break
            else:
                event = helper.new_event(json.dumps(audit_event), time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
                ew.write_event(event)
                event_count += 1
                # break

        if not r_json['cursor']['next']:
            break

        parameters['cursor'] = r_json['cursor']['next']
        if 'limit' in parameters:
            parameters.pop('after_id')
            parameters.pop('limit')
        
    helper.log_info('TA-thinkst-canary: Number of events added = ' + str(event_count))
    helper.log_info('TA-thinkst-canary: = = End Log  = =')
