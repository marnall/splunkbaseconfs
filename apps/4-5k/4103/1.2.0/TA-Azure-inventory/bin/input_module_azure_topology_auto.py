
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
import re
import azure.auth as azauth
import azure.utils as azutil
import azure.resource_groups as azrg
import azure.topology as aztopology

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    subscription_id = helper.get_arg("subscription_id")
    tenant_id = helper.get_arg("tenant_id")
    api_version = "2018-11-01"
    
    access_token = azauth.get_access_token(global_client_id, global_client_secret, tenant_id)
    
    network_watcher_url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Network/networkWatchers?api-version=%s" % (subscription_id, api_version)
    network_watchers = azutil.get_items(helper, access_token, network_watcher_url)
    
    resource_group_locations = azrg.get_resource_groups_by_location(helper, access_token, subscription_id)
    
    # The resource groups are grouped by location, so loop through locations
    for location in resource_group_locations:
        
        # Get the network watcher(s) for this location
        for watcher in network_watchers:
            if watcher["location"] == location:
                
                # Get the resource group and name for this network watcher
                resourceGroupName = re.search('\/resourceGroups\/(.+?)\/providers', watcher["id"]).group(1)
                networkWatcherName = watcher["name"]
                
                # Get resource groups in the same location as this watcher
                for targetResourceGroupName in resource_group_locations[location]:
                    
                    # Get the topology for this resource group
                    topology = aztopology.get_topology_by_rg(access_token, subscription_id, api_version, resourceGroupName, networkWatcherName, targetResourceGroupName)
                    
                    if len(topology) > 0:
                        for key, resource in topology.iteritems():
                            
                            e = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(resource))
                            ew.write_event(e)