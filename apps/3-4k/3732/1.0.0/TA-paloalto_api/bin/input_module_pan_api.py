
# encoding = utf-8

import os
import sys
import time
import datetime
import re

def validate_input(helper, definition):
    # TODO
    #api_account = definition.parameters.get('api_account', None)
    pass

def collect_events(helper, ew):

    # sourcetypes to pull into Splunk with relating API command
    sourcetypes = { 'pan:api:config:xml': 'configuration',
                    'pan:api:system:info': '<show><system><info></info></system></show>',
                    'pan:api:system:storage': '<show><system><disk-space></disk-space></system></show>',
                    'pan:api:system:ntp': '<show><ntp></ntp></show>',
                    'pan:api:system:havirtualaddress': '<show><high-availability><virtual-address></virtual-address></high-availability></show>',
                    'pan:api:system:resources': '<show><system><resources></resources></system></show>',
                    'pan:api:system:panoramastatus': '<show><panorama-status></panorama-status></show>',
                    'pan:api:system:processes': '<show><system><resources></resources></system></show>',
                    'pan:api:system:hastate': '<show><high-availability><state></state></high-availability></show>',
                    'pan:api:interface:stats': '<show><counter><interface>all</interface></counter></show>',
                    'pan:api:interface:hardware': '<show><interface>all</interface></show>',
                    'pan:api:session:info': '<show><session><info></info></session></show>',
                    'pan:api:running:resourcemonitor': '<show><running><resource-monitor><minute></minute></resource-monitor></running></show>',
                    'pan:api:chassis:inventory': '<show><chassis><inventory></inventory></chassis></show>',
                    'pan:api:chassis:power': '<show><chassis><power></power></chassis></show>',
                    'pan:api:chassis:status': '<show><chassis><status></status></chassis></show>',
                    'pan:api:check:pendingchanges': '<check><pending-changes></pending-changes></check>'
                }

    # get and set the loglevel from the setup page
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
                
    # get all detailed input stanzas
    stanzas = helper.get_input_stanza()
    
    for stanza in stanzas:
        helper.log_debug('current stanza is: {}'.format(stanza))
        
        opt_api_account = helper.get_arg('api_account', stanza)
        helper.log_debug('current api_account is: {}'.format(opt_api_account['name']))
        
        opt_api_host = helper.get_arg('api_host', stanza)
        helper.log_debug('current api_host is: {}'.format(opt_api_host))
        
        opt_api_url = helper.get_arg('api_url', stanza)
        helper.log_debug('current api_url is: {}'.format(opt_api_url))
        
        idx = helper.get_output_index()
        if type(idx) == dict:
            idx = idx[stanza]
        
        sourcetype = helper.get_arg('api_sourcetype', stanza)
        
        for st in sourcetype:
        
            helper.log_debug('current sourcetype selection is: {}'.format(st))
            url = opt_api_url
            params = {}
        
            # initial command params
            if (st == 'pan:api:config:xml'):
                params['type'] = "export"
                params['category'] = "configuration"
            else:
                params['type'] = "op"
                params['cmd'] = sourcetypes[st]
            
            # set API token
            params['key'] = opt_api_account['password']
        
            # query the API
            response = helper.send_http_request(url,method='GET',parameters=params,payload=None,headers=None,cookies=None,verify=False,cert=None,timeout=None,use_proxy=False)
            
            if(response.raise_for_status()):
                helper.log_error('PAN API rest query issue: {}'.format(st))
                # on error go to next for
            else:
                # clean the XML API response
                if (st != 'pan:api:config:xml'):
                    d = re.sub(r'<response status=\"success\">\s*<result>\s*', '', response.text)
                    d = re.sub(r'</result>\s*</response>\s*', '', d)
                    d = re.sub(r'(?ms)>\s*<', '><', d)
                
                    d = re.sub(r'\s*</time>', '</time>', d)
                
                    if (st != 'pan:api:system:storage' and st != 'pan:api:system:processes'):
                        d = re.sub(r'[\n\r]+', '', d)
                # don't clean the XML API response
                else:
                    d = response.text

                # prepare event for Splunk ingestion
                event = helper.new_event(source=helper.get_input_type() + ':' + stanza, index=idx, sourcetype=st, data=d, host=opt_api_host )

                # write to Splunk
                ew.write_event(event)
                
                helper.log_debug('PAN API rest query events written: {}'.format(st))

                # Sleep for 1 seconds between API calls...don't be mean to the palo's...
                time.sleep(1)
