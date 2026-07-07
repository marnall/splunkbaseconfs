
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import azure.utils as azutil
import azure.auth as azauth

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    subscription_id = helper.get_arg("subscription_id")
    tenant_id = helper.get_arg("tenant_id")
    
    disk_api_version = "2018-06-01"
    disk_sourcetype = helper.get_arg("managed_disk_sourcetype")
    collect_disks = helper.get_arg("collect_managed_disk_data")
    
    image_api_version = "2018-06-01"
    image_sourcetype = helper.get_arg("image_sourcetype")
    collect_images = helper.get_arg("collect_image_data")
    
    snapshot_api_version = "2018-06-01"
    snapshot_sourcetype = helper.get_arg("snapshot_sourcetype")
    collect_snapshots = helper.get_arg("collect_snapshot_data")
    
    vm_api_version = "2018-06-01"
    vm_sourcetype = helper.get_arg("virtual_machine_sourcetype")
    collect_vms = helper.get_arg("collect_virtual_machine_data")
    
    access_token = azauth.get_access_token(global_client_id, global_client_secret, tenant_id)
    
    if(access_token):
        
        if(collect_disks):
            helper.log_debug("Collecting managed disk data. sourcetype='%s'" % disk_sourcetype)
            url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/disks?api-version=%s" % (subscription_id, disk_api_version)
            disks = azutil.get_items(helper, access_token, url)
            for disk in disks:
                event = helper.new_event(
                    data=json.dumps(disk),
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=disk_sourcetype)
                ew.write_event(event)
                
        if(collect_images):
            helper.log_debug("Collecting image data. sourcetype='%s'" % image_sourcetype)
            url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/images?api-version=%s" % (subscription_id, image_api_version)
            images = azutil.get_items(helper, access_token, url)
            for image in images:
                event = helper.new_event(
                    data=json.dumps(image),
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=image_sourcetype)
                ew.write_event(event)
                
        if(collect_snapshots):
            helper.log_debug("Collecting snapshot data. sourcetype='%s'" % snapshot_sourcetype)
            url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/snapshots?api-version=%s" % (subscription_id, snapshot_api_version)
            snapshots = azutil.get_items(helper, access_token, url)
            for snapshot in snapshots:
                event = helper.new_event(
                    data=json.dumps(snapshot),
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=snapshot_sourcetype)
                ew.write_event(event)
                
        if(collect_vms):
            helper.log_debug("Collecting virtual machine data. sourcetype='%s'" % vm_sourcetype)
            url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Compute/virtualMachines?api-version=%s" % (subscription_id, disk_api_version)
            vms = azutil.get_items(helper, access_token, url)
            for vm in vms:
                event = helper.new_event(
                    data=json.dumps(vm),
                    source=helper.get_input_type(), 
                    index=helper.get_output_index(),
                    sourcetype=vm_sourcetype)
                ew.write_event(event)
                
    else:
        raise RuntimeError("Unable to obtain access token. Please check the Client ID, Client Secret, and Tenant ID")
        