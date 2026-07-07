# encoding = utf-8

import json
import os
import sys
import time
import datetime
import ta_assetnote_declare

"""Special prefix added to each log message"""
LOG_PREFIX = "AssetNote"

"""Number of assets to load per page"""
ASSETS_PER_PAGE_COUNT = 25

"""Graph Query template to pull the list of all triage statistics"""
TRIAGESTATISTICS_GRAPHQL_QUERY_TEMPLATE = """
query GetTriageAnalysis {{
  exposureStatisticsOverview {{
    id
    unresolved
    triaged
    ignored
    resolved
    averageTriageTime
    averageResolvedTime
    __typename
  }}
}}
"""

def debug(helper, all_params, msg, format_params=True):
    
    """"
    Write an debug log message
    
    Arguments
    ---------
    helper: helper
        Helper for splunk
    all_params: dict
        Parameters to substitute in the message to print
    msg: str
        Debug message to print to the internal log
    format_params: bool
        Format the parameters out in the original message
    """
    msg_to_log = LOG_PREFIX + ":DEBUG: " + msg
    if format_params:
        helper.log_debug(msg_to_log.format(**all_params))
    else:
        helper.log_debug(msg_to_log)
        
def info(helper, all_params, msg, format_params=True):
    
    """"
    Write an info log message
    
    Arguments
    ---------
    helper: helper
        Helper for splunk
    all_params: dict
        Parameters to substitute in the message to print
    msg: str
        Info message to print to the internal log
    format_params: bool
        Format the parameters out in the original message
    """
    msg_to_log = LOG_PREFIX + ":INFO: " + msg
    if format_params:
        helper.log_info(msg_to_log.format(**all_params))
    else:
        helper.log_info(msg_to_log)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    
    # ------------------------------------------------------------------------
    # Collect user input
    # ------------------------------------------------------------------------
    opt_assetnote_api_key = helper.get_arg('assetnote_account')['password']
    opt_assetnote_instance = helper.get_arg('assetnote_instance')
    opt_sleep_time_per_page = int(helper.get_arg('sleep_time_per_page'))
    opt_num_retries_per_page = int(helper.get_arg('num_retries_per_page'))
    opt_backoff_time_per_page_retry = int(helper.get_arg('backoff_time_per_page_retry'))
    opt_limit_num_pages_returned = int(helper.get_arg('limit_num_pages_returned'))
    
    all_params = {'assetnote_index': helper.get_output_index(),
                  'assetnote_sourcetype': helper.get_sourcetype(),
                  'assetnote_source': helper.get_input_type(),
                  'assetnote_api_key': opt_assetnote_api_key,
                  'assetnote_instance': opt_assetnote_instance,
                  'sleep_time': opt_sleep_time_per_page,
                  'backoff_time': opt_backoff_time_per_page_retry,
                  'num_retries': opt_num_retries_per_page,
                  'page_count': ASSETS_PER_PAGE_COUNT,
                  'limit_num_pages_returned': opt_limit_num_pages_returned}
    
    # Printing all the current parameters to internal log
    msg = ("assetnote_index: {assetnote_index}, "
           "assetnote_sourcetype: {assetnote_sourcetype}, "
           "assetnote_source: {assetnote_source}, "
           "assetnote_instance: {assetnote_instance}, "
           "sleep_time: {sleep_time},"
           "backoff_time: {backoff_time},"
           "num_retries: {num_retries},"
           "page_count: {page_count},"
           "limit_num_pages_returned: {limit_num_pages_returned}")
    debug(helper, all_params, msg)


    # ------------------------------------------------------------------------
    # Get all the triage statistics from Assetnote
    # ------------------------------------------------------------------------
    debug(helper, all_params,
         "Requesting triage statistics for instance: {assetnote_instance} page-wise...")
    
    all_params['try'] = 0
    all_params['page_load_success'] = False
    
    while not all_params['page_load_success'] and \
              all_params['try'] < all_params['num_retries']:
        
        all_params['try'] += 1
        
        debug(helper, all_params, 
             "Try: {try}. Requesting triage statistics from AssetNote...")
        graphql_query = TRIAGESTATISTICS_GRAPHQL_QUERY_TEMPLATE.format(**all_params)
        url_to_call = "https://{assetnote_instance}.assetnotecloud.com/api/v2/graphql".format(**all_params)
        method = "POST"
        auth_header = "X-ASSETNOTE-API-KEY"
        if 'assetnote_api_key' in all_params:
            if all_params['assetnote_api_key'].startswith('anmt_'):
                auth_header = "X-ASSETNOTE-MACHINE-TOKEN"
        headers={
            auth_header: "{assetnote_api_key}".format(**all_params),
            "X-SPLUNK-VERSION": ta_assetnote_declare.version,
            "User-Agent": "Splunk/Assetnote/TA-assetnote/{}".format(ta_assetnote_declare.version)
        }
        payload = dict(query=graphql_query)
        try:
            resp = helper.send_http_request(url=url_to_call,
                                            method=method, 
                                            payload=payload,
                                            headers=headers,
                                            verify=True,
                                            use_proxy=True)
        
            status_code = resp.status_code
            resp_text = resp.text
                
        except Exception as e:
            
            # Log the exception occurred to log file
            status_code = -1
            err_class = str(e.__class__)
            raw_err_msg = str(e)
            err_msg  = "Error in send_http_request for requesting triage statistics in try: {try}. "
            err_msg += "Error: {}, {}".format(err_class, raw_err_msg)
            info(helper, all_params, err_msg)
            
        # Page was not loaded successfully, so wait for some time before
        # re-requesting the page
        if status_code == 200:
                all_params['page_load_success'] = True
        else:
            all_params['page_load_success'] = False
            debug(helper, all_params, 
                "Sleeping {backoff_time}s before re-requesting triage statistics...")
            time.sleep(all_params['backoff_time'])


    # ------------------------------------------------------------------------
    # Parse the JSON response with the triage statistics from Assetnote
    # ------------------------------------------------------------------------
    
    if status_code == 200:

        debug(helper, all_params,
             "Parsing response to get the list of all triage statistics JSON...")
        resp_json = resp.json()
        
        debug(helper, all_params, 
            "Getting the triage statistics...")
        if 'data' in resp_json:
            if 'exposureStatisticsOverview' in resp_json['data']:
                triage_statistics_json = resp_json['data']['exposureStatisticsOverview']

        debug(helper, all_params, 
            "Adding triage statistics to Splunk...")
        
        new_event = helper.new_event(json.dumps(triage_statistics_json, indent=4),
                            index=all_params['assetnote_index'],
                            sourcetype=all_params['assetnote_sourcetype'],
                            source=all_params['assetnote_source'])
                            
        info(helper, all_params, 
            "Writing an event to Splunk index: {assetnote_index}, sourcetype: {assetnote_sourcetype}, source: {assetnote_source}...")
        ew.write_event(new_event)
    else:
        
        info(helper, all_params, "Error encountered when retrieving the triage statistics...")
        info(helper, all_params, "Error: ")
        info(helper, all_params, str(resp_json), format_params=False)
        get_next_page = False
