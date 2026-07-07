# encoding = utf-8

import os
import sys
import time
import datetime
import json

def validate_input(helper, definition):
    pass

def utc_timestamp(input_date):
    return int((input_date - datetime.datetime.utcfromtimestamp(0)).total_seconds())

def collect_events(helper, ew):
    
    opt_hostname = helper.get_global_setting('hostname')
    opt_api_token = helper.get_global_setting('csp_api_key')
    opt_t0 = helper.get_arg('t0')
    local = helper.get_input_stanza_names()
    proxy_settings = helper.get_proxy()
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)

    #set dates
    now = datetime.datetime.utcnow()
    ga_date = datetime.datetime(2016, 12, 24, 0, 0)
    helper.log_info("now_utc=        {},now_local=        {}, now_human={}".format(utc_timestamp(now),now.strftime('%s'),now.strftime('%Y-%m-%dT%H:%M:%S.%f%z'))) 
    
    #checkpoint_t0
    checkpoint_t0 = helper.get_check_point(local)
    try:
        t0 = datetime.datetime.utcfromtimestamp(int(checkpoint_t0))
        helper.log_info("checkpoint_strf={}, checkpoint_timestamp={}, checkpoint_human={}".format(checkpoint_t0,utc_timestamp(t0),t0.strftime('%Y-%m-%dT%H:%M:%S.%f%z')))
    except:
        try:
            t0 = datetime.datetime.utcfromtimestamp(int(opt_t0))
            helper.log_info("no checkpoint, reading t0 t0_strf={}, t0_timestamp={}, t0_human={}".format(checkpoint_t0,utc_timestamp(t0),t0.strftime('%Y-%m-%dT%H:%M:%S.%f%z')))
        except:
            t0 = now - datetime.timedelta(hours=12)

    t1 = t0 + datetime.timedelta(hours=12)
    if t1 + datetime.timedelta(minutes=10) > now:  # to deal with 10m, maximum delay to API
        t1 = now - datetime.timedelta(minutes=10)
        
    helper.log_info("t0_timestamp={},  t0_human={}, t1_timestamp={}, t1_human={}, now_timestamp={}  now_human={}".format(
                utc_timestamp(t0), t0.isoformat(), utc_timestamp(t1) ,t1.isoformat(), utc_timestamp(now),now.strftime('%Y-%m-%dT%H:%M:%S.%f%z')))
    if t1<=t0:
        helper.log_error("Skipping this poll because t1<=t0. t1={}, t0={}".format(utc_timestamp(t1),utc_timestamp(t0)))

        raise Exception("Skipping this poll because t1<=t0. t1={}, t0={}".format(utc_timestamp(t1),utc_timestamp(t0)))

    #Get security hits
    
    headers= {'Authorization': 'Token {}'.format(opt_api_token), 
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
        'Cache-Control': "no-cache"}
    method= "GET"
    
    urls= [
    "https://{}/api/dnsdata/v2/dns_event?source=rpz&t0={}&t1={}".format(opt_hostname,utc_timestamp(t0),utc_timestamp(t1)),
    "https://{}/api/dnsdata/v2/dns_event?source=category&t0={}&t1={}".format(opt_hostname,utc_timestamp(t0),utc_timestamp(t1))
    ]
    
    for url in urls:
        helper.log_info("url={}".format(url))
        offset = 0
        limit = 10000
        more_results = True

        while more_results:
            try:
                response = helper.send_http_request(url + "&_offset={}&_limit={}".format(offset, limit), method,
                                                    parameters=None, payload=None,
                                                    headers=headers, cookies=None, verify=False, cert=None,
                                                    timeout=(30, 30), use_proxy=True)
            except:
                raise Exception( "Unable to perform polling from url:{}, status code:{}".format(url, response.status_code))

            try:
                r_json = response.json()
            except:
                helper.log_error("Response is not valid json. Response:{}".format(response.text))

            try:
                if len(r_json["result"]):
                    helper.log_info(
                        "infoblox:api input={} object_count={} url={}".format(helper.get_input_stanza_names(),
                                                                              len(r_json["result"]), url))

                    # Write security hits
                    for result in r_json["result"]:
                        result_data = json.dumps(result)
                        event = helper.new_event(index=helper.get_output_index(), sourcetype=helper.get_sourcetype(),
                                                 data=result_data)
                        ew.write_event(event)

                    if len(response.json()["result"]) < 10000:
                        more_results = False
                else:
                    more_results = False
            except:
                raise Exception("Response is not valid json. Response:{}".format(response.text))

            offset += limit

    helper.save_check_point(local, utc_timestamp(t1))
