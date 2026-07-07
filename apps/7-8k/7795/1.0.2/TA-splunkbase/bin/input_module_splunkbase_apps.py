# encoding = utf-8
import os
import sys
import time
import datetime
import json
from math import ceil

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # filters = definition.parameters.get('filters', None)
pass

def collect_events(helper, ew):

    # Parameters
    query = helper.get_arg('search_query')
    includes = helper.get_arg('fields')
    archive = str(helper.get_arg('include_archived_apps')).lower()
    product = helper.get_arg('splunk_products')
    results_limit = helper.get_arg('results_limit')
    custom_source = helper.get_arg('custom_source')
    custom_sourcetype = helper.get_arg('custom_sourcetype')
    
    # Set default source and sourcetype if not set in inputs
    evt_source = ""
    if custom_source != "" and custom_source != None:
        evt_source = custom_source
    else:
        evt_source = "splunkbase_apps"
    
    evt_sourcetype = ""
    if custom_sourcetype != "" and custom_sourcetype != None:
        evt_sourcetype = custom_sourcetype
    else:
        evt_sourcetype = "splunkbase:apps"
    
    # static vars
    base_url = "https://api.splunkbase.splunk.com"
    api_path = "/api/v2/apps"
    includes_string = "?include="+str(includes)
    # The API seems to max out around 60 per page by default so lets just set this to 50.
    apps_per_page = 50 
    
    # if limit is less than 50, reduce apps per page
    if results_limit and int(results_limit) < 50 and int(results_limit) > 0:
        apps_per_page = int(results_limit)
    limit_string = "&limit="+str(apps_per_page) 
    product_string = "&product="+str(product)
    if archive == "true" or archive == 1 or archive == True:
        archive = "true"
    else:
        archive = "false"
    
    archive_string = "&archive="+str(archive)
    
    # Handle query
    if query != "" and query != None:
        query_string = "&query="+str(query)
    else:
        query_string = ""
    remaining_string = "&order=latest&offset="
    
    
    # FIRST PAGE REQUEST
    url = base_url + api_path + includes_string + limit_string + product_string + archive_string + query_string + remaining_string + "0"
    response = helper.send_http_request(url, method="GET", parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    r_json = response.json()
    
    for app in r_json["results"]:
            event = helper.new_event(time=None,source=evt_source, index=helper.get_output_index(), sourcetype=evt_sourcetype, data=json.dumps(app, sort_keys=True,ensure_ascii=False))
            ew.write_event(event)
    # FINISH FIRST PAGE REQUEST
    
    # if results_limit less than 50, then terminate here.
    if results_limit and int(results_limit) < 50 and int(results_limit) > 0:
        return
    
    # Get number of remaining pages
    total_apps_found = r_json["total"]
    if results_limit and int(results_limit) >= 50 and int(results_limit) < total_apps_found:
        total_apps_found = int(results_limit)

    total_pages_found = ceil(total_apps_found/apps_per_page)
    
    # ALL OTHER REQUEST PAGES WITH OFFSET:
    for i in range(1,total_pages_found):
        
        # No need to request all 50 entries on the last page. Change the limit for last call
        if (int(results_limit) % int(apps_per_page)) != 0 and (i == total_pages_found-1):
                limit_string = "&limit="+str(int(results_limit) % int(apps_per_page)) 
        
        url2 = base_url + api_path + includes_string + limit_string + product_string + archive_string + query_string + remaining_string + str(i*apps_per_page)
        response2 = helper.send_http_request(url2, method="GET", parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
        r_json2 = response2.json()
        for app2 in r_json2["results"]:
            event = helper.new_event(time=None,source=evt_source, index=helper.get_output_index(), sourcetype=evt_sourcetype, data=json.dumps(app2, sort_keys=True,ensure_ascii=False))
            ew.write_event(event)
    
    
