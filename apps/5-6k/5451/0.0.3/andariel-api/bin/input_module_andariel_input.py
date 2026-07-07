# encoding = utf-8

import os
import sys
import time
import datetime
import json
import logging


def write_to_index(helper, ew, data):
    try:
        data = str(data)
        event = helper.new_event(data,
                                 time=None,
                                 host=None,
                                 index=None,
                                 source=None,
                                 sourcetype=None,
                                 done=True,
                                 unbroken=True)
        ew.write_event(event)
        return True
    except:
        return False


def do_request(url,
               method,
               helper,
               parameters=None,
               payload=None,
               headers=None,
               cookies=None,
               verify=False,
               cert=None,
               timeout=None,
               use_proxy=True):
    response = helper.send_http_request(url,
                                        method,
                                        parameters=parameters,
                                        payload=payload,
                                        headers=headers,
                                        cookies=cookies,
                                        verify=verify,
                                        cert=cert,
                                        timeout=timeout,
                                        use_proxy=use_proxy)
    
    r_headers = response.headers
    r_text = response.text
    r_json = response.json()
    r_cookies = response.cookies
    historical_responses = response.history
    r_status = response.status_code
    if r_status == 200:
        logging.info('api response received successfully')
        return r_json
    elif r_status == 401: 
        logging.error('BAD API-KEY')
        return []
    elif r_status >= 500:
        logging.error(f'API server error: {r_status}')
        return []
    else:
        logging.error(f'API connection error: {r_status}, {r_text}')
        return []
        
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    # response.raise_for_status()


def get_iocapi(keyword, apikey, helper):
    url = "https://adv-gate.com/iocapi/?q=" + keyword
    headers = {"Apikey": apikey}
    payload = {"sort" : {"@timestamp" : "desc"}}
    data = do_request(url=url, 
                      method="get", 
                      headers=headers,
                      payload=payload,
                      helper=helper)
    result_rows = []
    if "hits" in data:
        if "hits" in data["hits"]:
            for result_line in data["hits"]["hits"]:
                result_rows.append(result_line)
    return result_rows


def get_botapi(keyword, apikey, helper):
    url = "https://adv-gate.com/botapi/?q=" + keyword
    headers = {"Apikey": apikey}
    payload = {"sort" : {"@timestamp" : "desc"}}
    data = do_request(url=url, 
                      method="get", 
                      headers=headers, 
                      payload=payload, 
                      helper=helper)
    result_rows = []
    if "hits" in data:
        if "hits" in data["hits"]:
            for result_line in data["hits"]["hits"]:
                result_rows.append(result_line)
    return result_rows


def get_darkapi(keyword, apikey, helper):
    url = "https://adv-gate.com/darkapi/?q=" + keyword
    headers = {"Apikey": apikey}
    payload = {"sort" : {"date_collect" : "desc"}}
    data = do_request(url=url, 
                      method="get", 
                      headers=headers,
                      payload=payload,
                      helper=helper)
    result_rows = []
    if "hits" in data:
        if "hits" in data["hits"]:
            for result_line in data["hits"]["hits"]:
                result_rows.append(result_line)
    return result_rows


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # adv_gate_api_key = definition.parameters.get('adv_gate_api_key', None)
    # keyword = definition.parameters.get('keyword', None)
    # botapi = definition.parameters.get('botapi', None)
    # iocapi = definition.parameters.get('iocapi', None)
    pass


def collect_events(helper, ew):
    apikey = str(helper.get_arg('andariel_api_key'))
    query = str(helper.get_arg('search_keyword'))
    api_name = helper.get_arg('api_name')

    data = []
    if api_name == "iocapi":
        data = get_iocapi(query, apikey, helper)
    elif api_name == "botapi":
        data = get_botapi(query, apikey, helper)
    elif api_name == "darkapi":
        data = get_darkapi(query, apikey, helper)
    for line in data:
        if "_source" in line:
            if "@timestamp" in line["_source"]:
                line["_source"]["date_collect"] = str(line["_source"]["@timestamp"]).split(".")[0]
                del line["_source"]["@timestamp"]
        line = json.dumps(line).replace("'", "")
        # line = str(line).replace('"', "|")
        # line = line.replace("'", '"')
        # line = line.replace("|", "'")
        # line = line.replace("None", "null").replace("True", "true").replace("False", "false")
        write_to_index(helper, ew, line)

    # {'proxy_url': '172.23.155.151',
    #  'proxy_port': '2922',
    #  'proxy_username': '',
    #  'proxy_password': '',
    #  'proxy_type': 'http',
    #  'proxy_rdns': False}
    # proxy_settings = helper.get_proxy()

