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

"""Graph Query template to pull the list of all asset groups"""
ASSETGROUPS_GRAPHQL_QUERY_TEMPLATE = """
query {{
    assetGroups {{
        edges {{
            node {{
                id,
                name
            }},
        }}
    }}
}}
"""

"""Graph Query template to pull the list of all IPs within an asset group"""
IPS_PER_ASSETGROUP_GRAPHQL_QUERY_TEMPLATE = """
{{
  assetGroups(f: {{field: "id", op: EQ, value: "{ag_id}"}}) {{
    edges {{
      node {{
        id
        name
        ipRanges(count: {page_count}, page: {page_num}) {{
          pageInfo {{
            hasNextPage
          }}
          edges {{
            node {{
              id
              cidr
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""

"""Graphql query to pull the list of all domains for the asset group"""
DOMAINS_PER_ASSETGROUP_GRAPHQL_QUERY_TEMPLATE = """
{{
  assetGroups(f: {{field: "id", op: EQ, value: "{ag_id}"}}) {{
    edges {{
      node {{
        id
        name
        domains(count: {page_count}, page: {page_num}) {{
          pageInfo {{
            hasNextPage
          }}
          edges {{
            node {{
              id
              name
            }}
          }}
        }}
      }}
    }}
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
    opt_assetnote_api_key = helper.get_arg('assetnote_api_key')
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
                  'limit_pages_returned': opt_limit_num_pages_returned}
    
    # Printing all the current parameters to internal log
    msg = ("assetnote_index: {assetnote_index}, "
           "assetnote_sourcetype: {assetnote_sourcetype}, "
           "assetnote_source: {assetnote_source}, "
           "assetnote_instance: {assetnote_instance}, "
           "sleep_time: {sleep_time},"
           "backoff_time: {backoff_time},"
           "num_retries: {num_retries},"
           "page_count: {page_count},"
           "limit_pages_returned: {limit_pages_returned}")
    debug(helper, all_params, msg)

    # Asset groups information - which includes IDs, names, and corresponding
    # IPs, domains
    asset_groups = []

    # ------------------------------------------------------------------------
    # Get all the Asset groups from Assetnote
    # ------------------------------------------------------------------------
    debug(helper, all_params,
         "Requesting asset groups for instance: {assetnote_instance} page-wise...")
    
    all_params['try'] = 0
    all_params['page_load_success'] = False
    
    while not all_params['page_load_success'] and \
              all_params['try'] < all_params['num_retries']:
        
        all_params['try'] += 1
        
        debug(helper, all_params, 
             "Try: {try}. Requesting asset groups from AssetNote...")
        graphql_query = ASSETGROUPS_GRAPHQL_QUERY_TEMPLATE.format(**all_params)
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
            err_msg  = "Error in send_http_request for requesting asset groups in try: {try}. "
            err_msg += "Error: {}, {}".format(err_class, raw_err_msg)
            info(helper, all_params, err_msg)
            
        # Page was not loaded successfully, so wait for some time before
        # re-requesting the page
        if status_code == 200:
                all_params['page_load_success'] = True
        else:
            all_params['page_load_success'] = False
            debug(helper, all_params, 
                "Sleeping {backoff_time}s before requesting asset groups...")
            time.sleep(all_params['backoff_time'])


    # ------------------------------------------------------------------------
    # Parse the JSON response with the Asset groups from Assetnote
    # ------------------------------------------------------------------------
    
    if status_code == 200:

        debug(helper, all_params,
             "Parsing response to get the list of all asset groups JSON...")
        resp_json = resp.json()
        
        debug(helper, all_params, 
            "Getting the list of asset groups  edges...")
        asset_groups_edges_list = []
        if 'data' in resp_json:
            if 'assetGroups' in resp_json['data']:
                if 'edges' in resp_json['data']['assetGroups']:
                    asset_groups_edges_list = resp_json['data']['assetGroups']['edges']

        debug(helper, all_params, 
            "Getting the ids, names of ALL asset group from each edge...")
        for asset_group_edge in asset_groups_edges_list:
            if 'node' in asset_group_edge:
                asset_group_edge_node = asset_group_edge['node']
                if 'id' in asset_group_edge_node:
                    asset_group_id = asset_group_edge_node.get('id', '')
                    asset_group_name = asset_group_edge_node.get('name', '')
                    
                    all_params['ag_id'] = asset_group_id
                    all_params['ag_name'] = asset_group_name
                    debug(helper, all_params, 
                          "Added asset_group with id: {ag_id}, name: {ag_name}")
                          
                    asset_groups.append({'id': asset_group_id, 
                                         'name': asset_group_name})
        
        debug(helper, all_params,
              "Counting number of asset groups found")
        num_asset_groups = len(asset_groups)
        all_params['num_asset_groups'] = num_asset_groups
        info(helper, all_params, 
            "Number of asset groups found: {num_asset_groups}")

    else:
        
        info(helper, all_params, "Error encountered when retrieving page: {page_num}...")
        info(helper, all_params, "Error: ")
        info(helper, all_params,
             str(resp_json), format_params=False)
        get_next_page = False
        
        
    # ------------------------------------------------------------------------
    # Get the IPs for each asset group (paginated)
    # ------------------------------------------------------------------------
    for asset_group in asset_groups:
        
        asset_group_id = asset_group['id']
        asset_group_name = asset_group['name']
        all_params['ag_id'] = asset_group_id
        all_params['ag_name'] = asset_group_name
        
        debug(helper, all_params,
              "Making POST req to get IPs for asset group: {ag_id}, {ag_name}")
             
        get_next_page = True
        all_params['page_num'] = 1
        
        while get_next_page:
            
            all_params['try'] = 0
            all_params['page_load_success'] = False
            
            while not all_params['page_load_success'] and \
                      all_params['try'] < all_params['num_retries']:
                
                all_params['try'] += 1
                
                debug(helper, all_params, 
                     "Try: {try}, Page: {page_num}. Requesting IPs for asset group from AssetNote...")
                graphql_query = IPS_PER_ASSETGROUP_GRAPHQL_QUERY_TEMPLATE.format(**all_params)
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
                    err_msg  = "Error in send_http_request for requesting IPs for page: {page_num} in try: {try}. "
                    err_msg += "Error: {}, {}".format(err_class, raw_err_msg)
                    info(helper, all_params, err_msg)
                    
                # Page was not loaded successfully, so wait for some time before
                # re-requesting the page
                if status_code == 200:
                        all_params['page_load_success'] = True
                else:
                    all_params['page_load_success'] = False
                    info(helper, all_params, 
                        "Sleeping {backoff_time}s before re-requesting...")
                    time.sleep(all_params['backoff_time'])

            debug(helper, all_params, 
                  "Parsing the response to determine the IPs...")
            if status_code == 200:
                
                resp_json = resp.json()
                
                debug(helper, all_params, 
                      "Get all the IPs from page: {page_num}")
                      
                asset_group_ip_ranges = []
                resp_json_domains_edges = None
                resp_json_domains = None
                if 'data' in resp_json:
                    resp_json_data = resp_json['data']
                    if 'assetGroups' in resp_json_data:
                        resp_json_asset_groups = resp_json_data['assetGroups']
                        if 'edges' in resp_json_asset_groups:
                            resp_json_edges = resp_json_asset_groups['edges']
                            if isinstance(resp_json_edges,
                                          list):
                                resp_json_edges = resp_json_edges[0]
                            if 'node' in resp_json_edges:
                                resp_json_node = resp_json_edges['node']
                                if 'domains' in resp_json_node:
                                    resp_json_domains = resp_json_node['domains']
                                    if 'edges' in resp_json_domains:
                                        resp_json_domains_edges = resp_json_domains['edges']
                                        if isinstance(resp_json_domains_edges,dict) or \
                                           isinstance(resp_json_domains_edges,str):
                                               resp_json_domains_edges = [resp_json_domains_edges]

                if resp_json_domains_edges:
                    helper.log_debug(str(resp_json_domains_edges))
                    for edge in resp_json_domains_edges:
                        if 'node' in edge:
                            if 'cidr' in edge['node']:
                                ip_range = edge['node']['cidr']
                                all_params['ip_range'] = ip_range
                                debug(helper, all_params,
                                      "Adding cidr: {ip_range} to ip_ranges")
                                asset_group_ip_ranges.append(ip_range)
                
                debug(helper, all_params, 
                      "Counting number of IP ranges found")
                num_ip_ranges = len(asset_group_ip_ranges)
                all_params['num_ip_ranges'] = len(asset_group_ip_ranges)
                info(helper, all_params,
                     "Number of IP ranges found on page: {page_num} is: {num_ip_ranges}")
            
                debug(helper, all_params, 
                      "Checking if the next page exists for page: {page_num}")
                if resp_json_domains:
                    if 'pageInfo' in resp_json_domains:
                        resp_json_page_info = resp_json_domains['pageInfo']
                        if 'hasNextPage' in resp_json_page_info:
                            get_next_page = resp_json_page_info['hasNextPage']
                            debug(helper, all_params,
                                  "No more pages of IPs after page: {page_num}")
                
            else:
                debug(helper, all_params,
                     "Error obtaining page: {page_num} when requesting IPs. Moving to next page.")
                
                all_params['page_num'] += 1            
        
        
    