
# encoding = utf-8

import os
import sys
import time
import datetime
import json
from elasticsearch import Elasticsearch


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def isCheckpoint(check_file, _id):
    with open(check_file, 'r') as file:
        log_list = file.read().splitlines()
        return ( _id in log_list)

def write2Checkpoint(check_file, _id):
    with open(check_file,'a') as file:
        file.writelines( _id + '\n')

def elasticsearch_search(helper,opt_elasticsearch_domain_port,username,password,opt_elasticsearch_index,opt_elasticsearch_date_field_name,opt_time_range,start,size):
    
    domain,port = opt_elasticsearch_domain_port.split(":")
    port = int(port)
    client = Elasticsearch(
            hosts=[{
            "host": domain,
            "port": port,
            "scheme": "https",
        }],
            verify_certs=False,
            #headers={"Content-Type": "application/json"},
            basic_auth=(username, password)
    )
    
        # Create the initial search query.
    search_query = {
            "bool": {
                "must": [
                    {
                        "range": {
                            opt_elasticsearch_date_field_name: {
                                "gte": "now-" + opt_time_range,
                                "lte": "now"
                            }
                        }
                    }
                ]
            }
    }

    helper.log_debug("Search query={}".format(search_query))
    search_params = {
        "index": opt_elasticsearch_index,
        "query": search_query,
        "size": size,
        "from": start,
        "sort": [ { opt_elasticsearch_date_field_name: "asc" }],
    }

    counter = 0 
    # Perform the initial search.
    response = client.search(**search_params, scroll="1m")
    scroll_id = response["_scroll_id"]
    hits = response["hits"]["hits"]

    # Store the initial hits in a list
    all_hits = hits

    while len(hits) > 0:
        # Perform the scroll request
        response = client.scroll(scroll_id=scroll_id, scroll="1m")
        scroll_id = response["_scroll_id"]
        hits = response["hits"]["hits"]
        
        # Append the hits to the list
        all_hits.extend(hits)
        

    # Return the results.
    helper.log_debug("Found {} hits".format(len(all_hits)))
    return all_hits
    

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # elasticsearch_account = definition.parameters.get('elasticsearch_account', None)
    # elasticsearch_index = definition.parameters.get('elasticsearch_index', None)
    # elasticsearch_date_field_name = definition.parameters.get('elasticsearch_date_field_name', None)
    # time_range = definition.parameters.get('time_range', None)
    # custom_sourcetype = definition.parameters.get('custom_sourcetype', None)
    pass

def collect_events(helper, ew):

    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    check_point_key = "%s_obj_checkpoint" % helper.get_input_stanza_names()
    checkpoint_data = {}
    
    username = helper.get_arg('elasticsearch_account').get("username")
    password = helper.get_arg('elasticsearch_account').get("password")
    helper.log_debug("username={}".format(username))
    
    opt_elasticsearch_domain_port = helper.get_arg('elasticsearch_domain_port')
    opt_elasticsearch_index = helper.get_arg('elasticsearch_index')
    opt_elasticsearch_date_field_name = helper.get_arg('elasticsearch_date_field_name')
    opt_time_range = helper.get_arg('time_range')
    opt_custom_sourcetype = helper.get_arg('custom_sourcetype')
    
    opt_source_type = helper.get_arg('custom_sourcetype')
    
    if opt_source_type:
        sourcetype = opt_source_type
    else:
        sourcetype= "elasticsearch:"+opt_elasticsearch_index+":json"
        
    start = 0
    size = 1000
    
    check_file = os.path.join('/', os.path.dirname(os.path.abspath(__file__)), 'checkpoint', 'elasticsearch_'+helper.get_input_stanza_names())
    
    # Build the path
    checkpoint_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'checkpoint')
    check_file = os.path.join(checkpoint_dir, 'checkpointElastic_'+helper.get_input_stanza_names())
    
    # Create the directory if it doesn't exist
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    
    # Create the file if it doesn't exist
    if not os.path.exists(check_file):
        with open(check_file, 'w') as f:
            f.write('')  # Write empty content
    
    documents = elasticsearch_search(helper,opt_elasticsearch_domain_port,username,password,opt_elasticsearch_index,opt_elasticsearch_date_field_name,opt_time_range,start,size)
    
    for doc in documents:
        _id = json.dumps(doc['_id'])
        date_time = doc['_source'][opt_elasticsearch_date_field_name]
        data = json.dumps(doc['_source'], ensure_ascii=False)
        #helper.log_debug(data)
        if not isCheckpoint(check_file, _id):
            write2Checkpoint(check_file, _id)
            event = helper.new_event(data=data, time=date_time, index=helper.get_output_index(), source=helper.get_input_type(), sourcetype=sourcetype, done=True, unbroken=True)
            ew.write_event(event)


    

    
