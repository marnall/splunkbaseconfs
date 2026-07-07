# encoding = utf-8

import json
import os
import sys
import time
from datetime import datetime
import ta_assetnote_declare
from custom_checkpoint_manager import FallbackCheckpointHelper

"""Special prefix added to each log message"""
LOG_PREFIX = "AssetNote"

"""Number of event logs to load per page"""
EVENTLOGS_PER_PAGE_COUNT = 25

"""Graph Query template to pull the list of all user event logs"""
USEREVENTLOGS_GRAPHQL_QUERY_TEMPLATE = """
query GetUserEventLogs {{
  userEventLogs(s: [{{
      field: "timestamp",
      dir: DESC
    }}], f: [{pull_time_after}], count: {page_count}, page: {page_num}) {{
    ...DataTableConnectionMeta
    edges {{
      node {{
        id
        description
        userEmail
        userIpAddress
        action
        modelClassName
        timestamp
        automated
        __typename
      }}
      __typename
    }}
    __typename
    pageInfo {{
    	hasNextPage
    }}
  }}
}}

fragment DataTableConnectionMeta on Connection {{
  totalCount
  modelInfo {{
    modelName
    relationships {{
      relationshipName
      relationshipModel
      __typename
    }}
    __typename
  }}
  __typename
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
    # Initialize fallback checkpoint helper
    # ------------------------------------------------------------------------
    checkpoint_helper = FallbackCheckpointHelper(helper, "TA-assetnote")
    
    # ------------------------------------------------------------------------
    # Collect user input
    # ------------------------------------------------------------------------
    opt_assetnote_api_key = helper.get_arg('assetnote_account')['password']
    opt_assetnote_instance = helper.get_arg('assetnote_instance')
    opt_sleep_time_per_page = int(helper.get_arg('sleep_time_per_page'))
    opt_num_retries_per_page = int(helper.get_arg('num_retries_per_page'))
    opt_backoff_time_per_page_retry = int(helper.get_arg('backoff_time_per_page_retry'))
    opt_limit_num_pages_returned = int(helper.get_arg('limit_num_pages_returned'))
    
    last_pull_time = checkpoint_helper.get_check_point('user_events_last_pull_time')
    if not last_pull_time:
        info(helper, {}, 
            "ASSETNOTE USEREVENTS LOG INFO: Last pull time checkpoint not set, pulling all data for assets from Assetnote.")
        opt_pull_datetime_after = '{field: "timestamp", op: GT, value: "2000-01-01T00:00:00Z"}'
    else:
        opt_pull_datetime_after = '{{field: "timestamp", op: GT, value: "{}"}}'.format(last_pull_time)
        info(helper, {"last_pull_time": last_pull_time}, 
            "ASSETNOTE USEREVENTS LOG INFO: Last pull time checkpoint IS set. Pulling all data from {last_pull_time}.")
    
    all_params = {'assetnote_index': helper.get_output_index(),
                  'assetnote_sourcetype': helper.get_sourcetype(),
                  'assetnote_source': helper.get_input_type(),
                  'assetnote_api_key': opt_assetnote_api_key,
                  'assetnote_instance': opt_assetnote_instance,
                  'sleep_time': opt_sleep_time_per_page,
                  'backoff_time': opt_backoff_time_per_page_retry,
                  'num_retries': opt_num_retries_per_page,
                  'page_count': EVENTLOGS_PER_PAGE_COUNT,
                  'limit_num_pages_returned': opt_limit_num_pages_returned,
                  'audit_logs_count': 0,
                  'limit_pages_returned': opt_limit_num_pages_returned,
                  'pull_time_after': opt_pull_datetime_after}
    
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
    # Get all the audit logs from Assetnote
    # ------------------------------------------------------------------------
    debug(helper, all_params,
         "Requesting audit logs for instance: {assetnote_instance} page-wise...")
    
    all_params['try'] = 0
    all_params['page_load_success'] = False
    
    user_event_logs = []
    get_next_page = True
    all_params['page_num'] = 1

    while get_next_page:
        
        all_params['try'] = 0
        all_params['page_load_success'] = False
        
        while not all_params['page_load_success'] \
            and all_params['try'] < all_params['num_retries']:
            
            all_params['try'] += 1

            info(helper, all_params, 
                 "Try: {try}. Requesting page: {page_num} for user event logs from AssetNote...")
            graphql_query = USEREVENTLOGS_GRAPHQL_QUERY_TEMPLATE.format(**all_params)
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
                # Attempt to make HTTP request to load the page with assets
                resp = helper.send_http_request(url=url_to_call,
                                                method=method, 
                                                payload=payload,
                                                headers=headers,
                                                verify=True,
                                                use_proxy=True,
                                                timeout=20)
                status_code = resp.status_code
                resp_text = resp.text
                    
            except Exception as e:
                
                # Log the exception occurred to log file
                status_code = -1
                resp_json = ""
                err_class = str(e.__class__)
                raw_err_msg = str(e)
                err_msg  = "Error in send_http_request for page: {page_num} for try: {try}. "
                err_msg += "Error: {}, {}".format(err_class, raw_err_msg)
                info(helper, all_params, err_msg)
                
            # Page was not loaded successfully, so wait for some time before
            # re-requesting the page
            if status_code == 200:
                    all_params['page_load_success'] = True
            else:
                all_params['page_load_success'] = False
                info(helper, all_params, 
                    "Sleeping {backoff_time}s before requesting same page...")
                time.sleep(all_params['backoff_time'])
                
            
        info(helper, all_params,
            "Checking if page: {page_num} obtained successfully...")
            
        if (status_code == -1) or (status_code != 200 or "data" not in resp_text):
            
            info(helper, all_params, "Error encountered when retrieving page: {page_num}...")
            info(helper, all_params, "Error: ")
            info(helper, all_params, str(resp_text), format_params=False)
            get_next_page = False
            
        else:

            info(helper, all_params,
                 "Parsing page: {page_num} response for user event logs as JSON...")
                 
            resp_json = resp.json()
            all_params['user_event_log_count'] = 0
            info(helper, all_params, 
                "Listing the number of user event logs on the page obtained...")
            events_on_page = resp_json['data']['userEventLogs']['edges']
            for event_on_page in events_on_page:
                user_event_logs.append(event_on_page)
                all_params['user_event_log_count'] = len(user_event_logs)
                
            info(helper, all_params, 
                "Number of user event logs after page: {page_num} is: {user_event_log_count}")

            info(helper, all_params,
                "Checking if another page exists from page: {page_num} response...")
                
            info(helper, all_params, 
                 "Calculating the number of user event logs in the page...")
            all_params['event_log_count_per_page'] = len(events_on_page)
            
            if len(events_on_page) > 0:
                info(helper, all_params, 
                    "Creating all {event_log_count_per_page} user logs as an event...")
                new_event = helper.new_event(json.dumps(events_on_page, indent=4),
                                index=all_params['assetnote_index'],
                                sourcetype=all_params['assetnote_sourcetype'],
                                source=all_params['assetnote_source'])
                                
                info(helper, all_params, 
                    "Writing an event to Splunk index: {assetnote_index}, sourcetype: {assetnote_sourcetype}, source: {assetnote_source}...")
                ew.write_event(new_event)
            
            
            info(helper, all_params, 
                    "Checking if next page should be obtained...")
            get_next_page_in_resp = resp_json['data']['userEventLogs']['pageInfo']['hasNextPage']
            if get_next_page_in_resp:
                
                info(helper, all_params, 
                    "Checking if limit of number of pages to return has been hit...")
                if all_params['limit_pages_returned'] > 0:
                    if int(all_params['page_num']) >= all_params['limit_pages_returned']:
                        
                        info(helper, all_params, 
                            "Limit hit! Stopping extraction of more pages...")
                        current_time = datetime.utcnow().isoformat()[:-3]+'Z'
                        checkpoint_helper.save_check_point('assets_last_pull_time', current_time)
                        get_next_page = False
            else:
                
                info(helper, all_params, 
                    "Stopping as no indication if next page is available...")
                current_time = datetime.utcnow().isoformat()[:-3]+'Z'
                checkpoint_helper.save_check_point('user_events_last_pull_time', current_time)    
                get_next_page = False
                    
            if get_next_page:
                
                info(helper, all_params, 
                     "Incrementing page counter...") 
                all_params['page_num'] += 1
                
                info(helper, all_params, 
                     "Next page to get: {page_num}...")
                
                info(helper, all_params, 
                     "Sleeping for {sleep_time}s before requesting next page...")
                time.sleep(all_params['sleep_time'])