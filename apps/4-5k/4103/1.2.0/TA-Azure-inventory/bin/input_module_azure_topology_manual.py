
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
import re
import azure.auth as azauth
import azure.resource_groups as azrg
import azure.topology as aztopology

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    subscription_id = helper.get_arg("subscription_id")
    tenant_id = helper.get_arg("tenant_id")
    network_watcher_name = helper.get_arg("network_watcher_name")
    network_watcher_resource_group = helper.get_arg("network_watcher_resource_group")
    target_resource_group = helper.get_arg("target_resource_group")
    api_version = "2018-11-01"
    
    access_token = azauth.get_access_token(global_client_id, global_client_secret, tenant_id)
    
    topology = aztopology.get_topology_by_rg(access_token, subscription_id, api_version, network_watcher_resource_group, network_watcher_name, target_resource_group)
                    
    if len(topology) > 0:
        for key, resource in topology.iteritems():
            
            e = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(resource))
            ew.write_event(e)