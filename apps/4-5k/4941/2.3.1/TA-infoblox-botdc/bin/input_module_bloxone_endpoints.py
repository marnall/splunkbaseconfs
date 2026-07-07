
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import splunklib.client as splunkClient

def validate_input(helper, definition):
    pass

def utc_timeformat(input_date):
    return datetime.datetime.strftime(datetime.datetime.fromtimestamp(int((input_date - datetime.datetime.utcfromtimestamp(0)).total_seconds())),"%Y-%m-%dT%H:%M:%S")


def flatten_json(y):
    global out
    out_array = []
    
    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    for z in y:
        out = {}
        flatten(z)
        out_array.append(out)
    return out_array
    
def collect_events(helper, ew):
    
    opt_hostname = helper.get_global_setting('hostname')
    opt_api_token = helper.get_global_setting('csp_api_key')
    headers= {"Authorization": "Token {}".format(opt_api_token)}
    loglevel = helper.get_log_level()
    proxy_settings = helper.get_proxy()
    
    account = helper.get_arg('global_account')
    username = account['username']
    password = account['password']
    
    
    splunk_server = helper.get_global_setting("server")
    splunk_app = helper.get_app_name()
    local = helper.get_input_stanza_names()
    collection_name = "botdc_endpoints_collection"
    
    # 1 Get active devices
        
    connected_time = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    url= "https://{}/api/atcep/v1/roaming_devices?_offset=10000000&_limit=1&_filter=connected_time>\"{}\"".format(opt_hostname,utc_timeformat(connected_time))
    headers= {'Authorization': 'Token {}'.format(opt_api_token), 
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
            'Cache-Control': "no-cache"}
    method= "GET"
    try:
        response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=(30,30), use_proxy=True)
        try:
            r_json = response.json()
            try:
                if r_json["total_result_count"]:
                    result_data= json.dumps(r_json)
                    event = helper.new_event(index=helper.get_output_index(), sourcetype="infoblox_active_endpoint_count", data = result_data)
                    ew.write_event(event)
            except:
                raise Exception("No result returned in this poll, connected_time=" + utc_timesformat(connected_time))
        except:
            helper.log_error("Response is not valid json. Response:{}".format(response.text))
            raise Exception("Response is not valid json. Response:{}".format(response.text))
    except:
        raise Exception('Unable to perform polling from url:{}, status code:{}'.format(url,response.status_code))
   
   #2 Acquire list of all endpoints and put it into kvstore 

    splunkService = splunkClient.connect(username=username, password=password, owner='nobody', app=splunk_app)
    if not collection_name in splunkService.kvstore:
        splunkService.kvstore.create(collection_name)
    
    collection = splunkService.kvstore[collection_name]
    collection.data.delete()

    offset=0
    iter=0
    
    while offset >= 0 and iter < 1000: #considering max 1M endpoints
        headers= {'Authorization': 'Token {}'.format(opt_api_token), 
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
            'Cache-Control': "no-cache"}
        method= "GET"
        url = "https://{}/api/atcep/v1/roaming_devices?_limit=1000&_offset={}".format(opt_hostname,offset)
        iter+=1    
        
        try:
            response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=(30,30), use_proxy=True)
            r_json = response.json()
            if len(r_json["results"])>0:
                data = flatten_json(r_json["results"])
                collection.data.batch_save(*data)
                offset+=1000
                
            else:
                offset =-1

        except:
        	raise Exception
        	break
