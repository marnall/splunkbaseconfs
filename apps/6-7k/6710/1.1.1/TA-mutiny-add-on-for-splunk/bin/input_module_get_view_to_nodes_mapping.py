
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import Timeout
    
def validate_input(helper, definition):
    pass

def outputChildNodesForView(viewid):
    try:
        childNodeResponse = requests.get(mutiny_site + "/api/views/" + viewid + "/childNodes/", auth = HTTPBasicAuth(username,password), timeout = (3,5))
    except Timeout:
        print("Timed out making REST API call to Mutiny: "+ mutiny_site)
    else:
        childNode = json.loads(childNodeResponse.text)
        output = {'viewid': viewid, 'nodes': childNode}
        return output

#main program

def getViews():

    try:
        #Call to get all views:
        response = requests.get(mutiny_site + "/api/views/", auth = HTTPBasicAuth(username,password), timeout= (3,5))
    except Timeout:
        print("Timed out making REST API call to Mutiny: " + mutiny_site+"/api/views/")

    else:
        if response.status_code != 200:
            print("Call to mutiny failed with HTTP response code: "+str(response.status_code))
        else:
            jsonResponse = json.loads(response.text)
            childnodes_output = []
            #iterate over all the views:
            for views in jsonResponse:
                viewid = views['id']
                childnodes_output.append(outputChildNodesForView(viewid))
            return childnodes_output


def collect_events(helper, ew):
    
    global username
    global password
    global mutiny_site
    global_mutiny_server_address = helper.get_global_setting("mutiny_server_address")
    mutiny_site = global_mutiny_server_address
    global_account = helper.get_arg('global_account')
    username = global_account['username'] 
    password = global_account['password']

    
    all_views = getViews()
    
    
    for view in all_views:
        source_name = "mutiny:"+str(view['viewid'])
        event = helper.new_event(
                    data = json.dumps(view),
                    source = source_name,
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype())
        ew.write_event(event) 

    