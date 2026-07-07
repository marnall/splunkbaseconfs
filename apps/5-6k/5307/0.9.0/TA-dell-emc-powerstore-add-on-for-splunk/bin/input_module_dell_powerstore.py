
# encoding = utf-8

import datetime
import json
import os
import requests
import sys
import time
from requests.auth import HTTPBasicAuth

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

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # ip_address = definition.parameters.get('ip_address', None)
    # global_account = definition.parameters.get('global_account', None)
    # compute = definition.parameters.get('compute', None)
    pass

def collect_events(helper, ew):
        
    # Get input settings
    global_account = helper.get_arg('global_account')
    username = global_account['username']
    password = global_account['password']
    ip_address = helper.get_arg("ip_address")

    # Get what to collect
    compute  = helper.get_arg('compute')
    migration  = helper.get_arg('migration')
    monitoring  = helper.get_arg('monitoring')
    protection  = helper.get_arg('protection')
    settings  = helper.get_arg('settings')
    storage  = helper.get_arg('storage')
    support  = helper.get_arg('support')
    system_and_hardware  = helper.get_arg('system_and_hardware')


    helper.log_info("PowerStore START: Beginning collection for: " + ip_address)
    start = time.time()
    
######################    
# Compute Collection #
######################
    if compute is True:
        helper.log_info("Dell PowerStore - Compute: Trying Compute collection for: " + ip_address)
        #host api call
        try:
            helper.log_info("Dell PowerStore - Compute: host beginning data collection for: " + ip_address)
            host_url = 'https://' + ip_address + '/api/rest/host?select=*'
            host_response = requests.get(host_url, auth=HTTPBasicAuth(username, password), verify=False)
            host_path = json.loads(host_response.text)
            host_count = len(host_path)
            helper.log_info("Dell PowerStore - Compute: " + str(host_count) + " host counted for: " + ip_address)
            host_counter = 0
            #iterate throught the payload into events
            while host_counter < host_count:
                host_path = json.loads(host_response.text)[host_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:host", data=json.dumps(host_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Compute: host event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Compute: host CANNOT write event for: " + ip_address)
                host_counter += 1
        except:
            helper.log_error("Dell PowerStore - Compute: host could not call api for: " + ip_address)

        #host_group api call
        try:
            helper.log_info("Dell PowerStore - Compute: host_group beginning data collection for: " + ip_address)
            host_group_url = 'https://' + ip_address + '/api/rest/host_group?select=*'
            host_group_response = requests.get(host_group_url, auth=HTTPBasicAuth(username, password), verify=False)
            host_group_path = json.loads(host_group_response.text)
            host_group_count = len(host_group_path)
            helper.log_info("Dell PowerStore - Compute: " + str(host_group_count) + " host_group counted for: " + ip_address)
            host_group_counter = 0
            #iterate throught the payload into events
            while host_group_counter < host_group_count:
                host_group_path = json.loads(host_group_response.text)[host_group_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:host_group", data=json.dumps(host_group_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Compute: host_group event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Compute: host_group CANNOT write event for: " + ip_address)
                host_group_counter += 1
        except:
            helper.log_error("Dell PowerStore - Compute: host_group could not call api for: " + ip_address)
        
        #host_volume_mapping api call
        try:
            helper.log_info("Dell PowerStore - Compute: host_volume_mapping beginning data collection for: " + ip_address)
            host_volume_mapping_url = 'https://' + ip_address + '/api/rest/host_volume_mapping?select=*'
            host_volume_mapping_response = requests.get(host_volume_mapping_url, auth=HTTPBasicAuth(username, password), verify=False)
            host_volume_mapping_path = json.loads(host_volume_mapping_response.text)
            host_volume_mapping_count = len(host_volume_mapping_path)
            helper.log_info("Dell PowerStore - Compute: " + str(host_volume_mapping_count) + " host_volume_mapping counted for: " + ip_address)
            host_volume_mapping_counter = 0
            #iterate throught the payload into events
            while host_volume_mapping_counter < host_volume_mapping_count:
                host_volume_mapping_path = json.loads(host_volume_mapping_response.text)[host_volume_mapping_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:host_volume_mapping", data=json.dumps(host_volume_mapping_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Compute: host_volume_mapping event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Compute: host_volume_mapping CANNOT write event for: " + ip_address)
                host_volume_mapping_counter += 1
        except:
            helper.log_error("Dell PowerStore - Compute: host_volume_mapping could not call api for: " + ip_address)

        #host_virtual_volume_mapping api call
        try:
            helper.log_info("Dell PowerStore - Compute: host_virtual_volume_mapping beginning data collection for: " + ip_address)
            host_virtual_volume_mapping_url = 'https://' + ip_address + '/api/rest/host_virtual_volume_mapping?select=*'
            host_virtual_volume_mapping_response = requests.get(host_virtual_volume_mapping_url, auth=HTTPBasicAuth(username, password), verify=False)
            host_virtual_volume_mapping_path = json.loads(host_virtual_volume_mapping_response.text)
            host_virtual_volume_mapping_count = len(host_virtual_volume_mapping_path)
            helper.log_info("Dell PowerStore - Compute: " + str(host_virtual_volume_mapping_count) + " host_virtual_volume_mapping counted for: " + ip_address)
            host_virtual_volume_mapping_counter = 0
            #iterate throught the payload into events
            while host_virtual_volume_mapping_counter < host_virtual_volume_mapping_count:
                host_virtual_volume_mapping_path = json.loads(host_virtual_volume_mapping_response.text)[host_virtual_volume_mapping_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:host_virtual_volume_mapping", data=json.dumps(host_virtual_volume_mapping_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Compute: host_virtual_volume_mapping event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Compute: host_virtual_volume_mapping CANNOT write event for: " + ip_address)
                host_virtual_volume_mapping_counter += 1
        except:
            helper.log_error("Dell PowerStore - Compute: host_virtual_volume_mapping could not call api for: " + ip_address)

        #discovered_initiator api call
        try:
            helper.log_info("Dell PowerStore - Compute: discovered_initiator beginning data collection for: " + ip_address)
            discovered_initiator_url = 'https://' + ip_address + '/api/rest/discovered_initiator?select=*'
            discovered_initiator_response = requests.get(discovered_initiator_url, auth=HTTPBasicAuth(username, password), verify=False)
            discovered_initiator_path = json.loads(discovered_initiator_response.text)
            discovered_initiator_count = len(discovered_initiator_path)
            helper.log_info("Dell PowerStore - Compute: " + str(discovered_initiator_count) + " discovered_initiator counted for: " + ip_address)
            discovered_initiator_counter = 0
            #iterate throught the payload into events
            while discovered_initiator_counter < discovered_initiator_count:
                discovered_initiator_path = json.loads(discovered_initiator_response.text)[discovered_initiator_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:discovered_initiator", data=json.dumps(discovered_initiator_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Compute: discovered_initiator event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Compute: discovered_initiator CANNOT write event for: " + ip_address)
                discovered_initiator_counter += 1
        except:
            helper.log_error("Dell PowerStore - Compute: discovered_initiator could not call api for: " + ip_address)

        #vcenter api call
        try:
            helper.log_info("Dell PowerStore - Compute: vcenter beginning data collection for: " + ip_address)
            vcenter_url = 'https://' + ip_address + '/api/rest/vcenter?select=*'
            vcenter_response = requests.get(vcenter_url, auth=HTTPBasicAuth(username, password), verify=False)
            vcenter_path = json.loads(vcenter_response.text)
            vcenter_count = len(vcenter_path)
            helper.log_info("Dell PowerStore - Compute: " + str(vcenter_count) + " vcenter counted for: " + ip_address)
            vcenter_counter = 0
            #iterate throught the payload into events
            while vcenter_counter < vcenter_count:
                vcenter_path = json.loads(vcenter_response.text)[vcenter_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:vcenter", data=json.dumps(vcenter_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Compute: vcenter event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Compute: vcenter CANNOT write event for: " + ip_address)
                vcenter_counter += 1
        except:
            helper.log_error("Dell PowerStore - Compute: vcenter could not call api for: " + ip_address)

        #virtual_machine api call
        try:
            helper.log_info("Dell PowerStore - Compute: virtual_machine beginning data collection for: " + ip_address)
            virtual_machine_url = 'https://' + ip_address + '/api/rest/virtual_machine?select=*'
            virtual_machine_response = requests.get(virtual_machine_url, auth=HTTPBasicAuth(username, password), verify=False)
            virtual_machine_path = json.loads(virtual_machine_response.text)
            virtual_machine_count = len(virtual_machine_path)
            helper.log_info("Dell PowerStore - Compute: " + str(virtual_machine_count) + " virtual_machine counted for: " + ip_address)
            virtual_machine_counter = 0
            #iterate throught the payload into events
            while virtual_machine_counter < virtual_machine_count:
                virtual_machine_path = json.loads(virtual_machine_response.text)[virtual_machine_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:virtual_machine", data=json.dumps(virtual_machine_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Compute: virtual_machine event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Compute: virtual_machine CANNOT write event for: " + ip_address)
                virtual_machine_counter += 1
        except:
            helper.log_error("Dell PowerStore - Compute: virtual_machine could not call api for: " + ip_address)

########################    
# Migration Collection #
########################
    if migration is True:
        helper.log_info("Dell PowerStore - Migration: Trying Compute collection for: " + ip_address)

        #import_host_initiator api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_host_initiator beginning data collection for: " + ip_address)
            import_host_initiator_url = 'https://' + ip_address + '/api/rest/import_host_initiator?select=*'
            import_host_initiator_response = requests.get(import_host_initiator_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_host_initiator_path = json.loads(import_host_initiator_response.text)
            import_host_initiator_count = len(import_host_initiator_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_host_initiator_count) + " import_host_initiator counted for: " + ip_address)
            import_host_initiator_counter = 0
            #iterate throught the payload into events
            while import_host_initiator_counter < import_host_initiator_count:
                import_host_initiator_path = json.loads(import_host_initiator_response.text)[import_host_initiator_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_host_initiator", data=json.dumps(import_host_initiator_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_host_initiator event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_host_initiator CANNOT write event for: " + ip_address)
                import_host_initiator_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_host_initiator could not call api for: " + ip_address)


        #import_host_system api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_host_system beginning data collection for: " + ip_address)
            import_host_system_url = 'https://' + ip_address + '/api/rest/import_host_system?select=*'
            import_host_system_response = requests.get(import_host_system_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_host_system_path = json.loads(import_host_system_response.text)
            import_host_system_count = len(import_host_system_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_host_system_count) + " import_host_system counted for: " + ip_address)
            import_host_system_counter = 0
            #iterate throught the payload into events
            while import_host_system_counter < import_host_system_count:
                import_host_system_path = json.loads(import_host_system_response.text)[import_host_system_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_host_system", data=json.dumps(import_host_system_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_host_system event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_host_system CANNOT write event for: " + ip_address)
                import_host_system_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_host_system could not call api for: " + ip_address)


        #import_host_volume api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_host_volume beginning data collection for: " + ip_address)
            import_host_volume_url = 'https://' + ip_address + '/api/rest/import_host_volume?select=*'
            import_host_volume_response = requests.get(import_host_volume_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_host_volume_path = json.loads(import_host_volume_response.text)
            import_host_volume_count = len(import_host_volume_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_host_volume_count) + " import_host_volume counted for: " + ip_address)
            import_host_volume_counter = 0
            #iterate throught the payload into events
            while import_host_volume_counter < import_host_volume_count:
                import_host_volume_path = json.loads(import_host_volume_response.text)[import_host_volume_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_host_volume", data=json.dumps(import_host_volume_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_host_volume event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_host_volume CANNOT write event for: " + ip_address)
                import_host_volume_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_host_volume could not call api for: " + ip_address)


        #import_psgroup api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_psgroup beginning data collection for: " + ip_address)
            import_psgroup_url = 'https://' + ip_address + '/api/rest/import_psgroup?select=*'
            import_psgroup_response = requests.get(import_psgroup_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_psgroup_path = json.loads(import_psgroup_response.text)
            import_psgroup_count = len(import_psgroup_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_psgroup_count) + " import_psgroup counted for: " + ip_address)
            import_psgroup_counter = 0
            #iterate throught the payload into events
            while import_psgroup_counter < import_psgroup_count:
                import_psgroup_path = json.loads(import_psgroup_response.text)[import_psgroup_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_psgroup", data=json.dumps(import_psgroup_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_psgroup event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_psgroup CANNOT write event for: " + ip_address)
                import_psgroup_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_psgroup could not call api for: " + ip_address)


        #import_psgroup_volume api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_psgroup_volume beginning data collection for: " + ip_address)
            import_psgroup_volume_url = 'https://' + ip_address + '/api/rest/import_psgroup_volume?select=*'
            import_psgroup_volume_response = requests.get(import_psgroup_volume_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_psgroup_volume_path = json.loads(import_psgroup_volume_response.text)
            import_psgroup_volume_count = len(import_psgroup_volume_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_psgroup_volume_count) + " import_psgroup_volume counted for: " + ip_address)
            import_psgroup_volume_counter = 0
            #iterate throught the payload into events
            while import_psgroup_volume_counter < import_psgroup_volume_count:
                import_psgroup_volume_path = json.loads(import_psgroup_volume_response.text)[import_psgroup_volume_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_psgroup_volume", data=json.dumps(import_psgroup_volume_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_psgroup_volume event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_psgroup_volume CANNOT write event for: " + ip_address)
                import_psgroup_volume_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_psgroup_volume could not call api for: " + ip_address)


        #import_session api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_session beginning data collection for: " + ip_address)
            import_session_url = 'https://' + ip_address + '/api/rest/import_session?select=*'
            import_session_response = requests.get(import_session_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_session_path = json.loads(import_session_response.text)
            import_session_count = len(import_session_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_session_count) + " import_session counted for: " + ip_address)
            import_session_counter = 0
            #iterate throught the payload into events
            while import_session_counter < import_session_count:
                import_session_path = json.loads(import_session_response.text)[import_session_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_session", data=json.dumps(import_session_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_session event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_session CANNOT write event for: " + ip_address)
                import_session_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_session could not call api for: " + ip_address)


        #import_storage_center api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_storage_center beginning data collection for: " + ip_address)
            import_storage_center_url = 'https://' + ip_address + '/api/rest/import_storage_center?select=*'
            import_storage_center_response = requests.get(import_storage_center_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_storage_center_path = json.loads(import_storage_center_response.text)
            import_storage_center_count = len(import_storage_center_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_storage_center_count) + " import_storage_center counted for: " + ip_address)
            import_storage_center_counter = 0
            #iterate throught the payload into events
            while import_storage_center_counter < import_storage_center_count:
                import_storage_center_path = json.loads(import_storage_center_response.text)[import_storage_center_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_storage_center", data=json.dumps(import_storage_center_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_storage_center event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_storage_center CANNOT write event for: " + ip_address)
                import_storage_center_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_storage_center could not call api for: " + ip_address)


        #import_storage_center_consistency_group api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_storage_center_consistency_group beginning data collection for: " + ip_address)
            import_storage_center_consistency_group_url = 'https://' + ip_address + '/api/rest/import_storage_center_consistency_group?select=*'
            import_storage_center_consistency_group_response = requests.get(import_storage_center_consistency_group_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_storage_center_consistency_group_path = json.loads(import_storage_center_consistency_group_response.text)
            import_storage_center_consistency_group_count = len(import_storage_center_consistency_group_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_storage_center_consistency_group_count) + " import_storage_center_consistency_group counted for: " + ip_address)
            import_storage_center_consistency_group_counter = 0
            #iterate throught the payload into events
            while import_storage_center_consistency_group_counter < import_storage_center_consistency_group_count:
                import_storage_center_consistency_group_path = json.loads(import_storage_center_consistency_group_response.text)[import_storage_center_consistency_group_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_storage_center_consistency_group", data=json.dumps(import_storage_center_consistency_group_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_storage_center_consistency_group event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_storage_center_consistency_group CANNOT write event for: " + ip_address)
                import_storage_center_consistency_group_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_storage_center_consistency_group could not call api for: " + ip_address)


        #import_storage_center_volume api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_storage_center_volume beginning data collection for: " + ip_address)
            import_storage_center_volume_url = 'https://' + ip_address + '/api/rest/import_storage_center_volume?select=*'
            import_storage_center_volume_response = requests.get(import_storage_center_volume_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_storage_center_volume_path = json.loads(import_storage_center_volume_response.text)
            import_storage_center_volume_count = len(import_storage_center_volume_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_storage_center_volume_count) + " import_storage_center_volume counted for: " + ip_address)
            import_storage_center_volume_counter = 0
            #iterate throught the payload into events
            while import_storage_center_volume_counter < import_storage_center_volume_count:
                import_storage_center_volume_path = json.loads(import_storage_center_volume_response.text)[import_storage_center_volume_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_storage_center_volume", data=json.dumps(import_storage_center_volume_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_storage_center_volume event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_storage_center_volume CANNOT write event for: " + ip_address)
                import_storage_center_volume_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_storage_center_volume could not call api for: " + ip_address)


        #import_unity api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_unity beginning data collection for: " + ip_address)
            import_unity_url = 'https://' + ip_address + '/api/rest/import_unity?select=*'
            import_unity_response = requests.get(import_unity_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_unity_path = json.loads(import_unity_response.text)
            import_unity_count = len(import_unity_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_unity_count) + " import_unity counted for: " + ip_address)
            import_unity_counter = 0
            #iterate throught the payload into events
            while import_unity_counter < import_unity_count:
                import_unity_path = json.loads(import_unity_response.text)[import_unity_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_unity", data=json.dumps(import_unity_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_unity event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_unity CANNOT write event for: " + ip_address)
                import_unity_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_unity could not call api for: " + ip_address)


        #import_unity_consistency_group api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_unity_consistency_group beginning data collection for: " + ip_address)
            import_unity_consistency_group_url = 'https://' + ip_address + '/api/rest/import_unity_consistency_group?select=*'
            import_unity_consistency_group_response = requests.get(import_unity_consistency_group_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_unity_consistency_group_path = json.loads(import_unity_consistency_group_response.text)
            import_unity_consistency_group_count = len(import_unity_consistency_group_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_unity_consistency_group_count) + " import_unity_consistency_group counted for: " + ip_address)
            import_unity_consistency_group_counter = 0
            #iterate throught the payload into events
            while import_unity_consistency_group_counter < import_unity_consistency_group_count:
                import_unity_consistency_group_path = json.loads(import_unity_consistency_group_response.text)[import_unity_consistency_group_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_unity_consistency_group", data=json.dumps(import_unity_consistency_group_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_unity_consistency_group event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_unity_consistency_group CANNOT write event for: " + ip_address)
                import_unity_consistency_group_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_unity_consistency_group could not call api for: " + ip_address)


        #import_unity_volume api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_unity_volume beginning data collection for: " + ip_address)
            import_unity_volume_url = 'https://' + ip_address + '/api/rest/import_unity_volume?select=*'
            import_unity_volume_response = requests.get(import_unity_volume_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_unity_volume_path = json.loads(import_unity_volume_response.text)
            import_unity_volume_count = len(import_unity_volume_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_unity_volume_count) + " import_unity_volume counted for: " + ip_address)
            import_unity_volume_counter = 0
            #iterate throught the payload into events
            while import_unity_volume_counter < import_unity_volume_count:
                import_unity_volume_path = json.loads(import_unity_volume_response.text)[import_unity_volume_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_unity_volume", data=json.dumps(import_unity_volume_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_unity_volume event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_unity_volume CANNOT write event for: " + ip_address)
                import_unity_volume_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_unity_volume could not call api for: " + ip_address)


        #import_vnx_array api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_vnx_array beginning data collection for: " + ip_address)
            import_vnx_array_url = 'https://' + ip_address + '/api/rest/import_vnx_array?select=*'
            import_vnx_array_response = requests.get(import_vnx_array_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_vnx_array_path = json.loads(import_vnx_array_response.text)
            import_vnx_array_count = len(import_vnx_array_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_vnx_array_count) + " import_vnx_array counted for: " + ip_address)
            import_vnx_array_counter = 0
            #iterate throught the payload into events
            while import_vnx_array_counter < import_vnx_array_count:
                import_vnx_array_path = json.loads(import_vnx_array_response.text)[import_vnx_array_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_vnx_array", data=json.dumps(import_vnx_array_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_vnx_array event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_vnx_array CANNOT write event for: " + ip_address)
                import_vnx_array_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_vnx_array could not call api for: " + ip_address)


        #import_vnx_consistency_group api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_vnx_consistency_group beginning data collection for: " + ip_address)
            import_vnx_consistency_group_url = 'https://' + ip_address + '/api/rest/import_vnx_consistency_group?select=*'
            import_vnx_consistency_group_response = requests.get(import_vnx_consistency_group_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_vnx_consistency_group_path = json.loads(import_vnx_consistency_group_response.text)
            import_vnx_consistency_group_count = len(import_vnx_consistency_group_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_vnx_consistency_group_count) + " import_vnx_consistency_group counted for: " + ip_address)
            import_vnx_consistency_group_counter = 0
            #iterate throught the payload into events
            while import_vnx_consistency_group_counter < import_vnx_consistency_group_count:
                import_vnx_consistency_group_path = json.loads(import_vnx_consistency_group_response.text)[import_vnx_consistency_group_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_vnx_consistency_group", data=json.dumps(import_vnx_consistency_group_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_vnx_consistency_group event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_vnx_consistency_group CANNOT write event for: " + ip_address)
                import_vnx_consistency_group_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_vnx_consistency_group could not call api for: " + ip_address)


        #import_vnx_volume api call
        try:
            helper.log_info("Dell PowerStore - Migration: import_vnx_volume beginning data collection for: " + ip_address)
            import_vnx_volume_url = 'https://' + ip_address + '/api/rest/import_vnx_volume?select=*'
            import_vnx_volume_response = requests.get(import_vnx_volume_url, auth=HTTPBasicAuth(username, password), verify=False)
            import_vnx_volume_path = json.loads(import_vnx_volume_response.text)
            import_vnx_volume_count = len(import_vnx_volume_path)
            helper.log_info("Dell PowerStore - Migration: " + str(import_vnx_volume_count) + " import_vnx_volume counted for: " + ip_address)
            import_vnx_volume_counter = 0
            #iterate throught the payload into events
            while import_vnx_volume_counter < import_vnx_volume_count:
                import_vnx_volume_path = json.loads(import_vnx_volume_response.text)[import_vnx_volume_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:import_vnx_volume", data=json.dumps(import_vnx_volume_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: import_vnx_volume event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: import_vnx_volume CANNOT write event for: " + ip_address)
                import_vnx_volume_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: import_vnx_volume could not call api for: " + ip_address)


        #migration_recommendation api call
        try:
            helper.log_info("Dell PowerStore - Migration: migration_recommendation beginning data collection for: " + ip_address)
            migration_recommendation_url = 'https://' + ip_address + '/api/rest/migration_recommendation?select=*'
            migration_recommendation_response = requests.get(migration_recommendation_url, auth=HTTPBasicAuth(username, password), verify=False)
            migration_recommendation_path = json.loads(migration_recommendation_response.text)
            migration_recommendation_count = len(migration_recommendation_path)
            helper.log_info("Dell PowerStore - Migration: " + str(migration_recommendation_count) + " migration_recommendation counted for: " + ip_address)
            migration_recommendation_counter = 0
            #iterate throught the payload into events
            while migration_recommendation_counter < migration_recommendation_count:
                migration_recommendation_path = json.loads(migration_recommendation_response.text)[migration_recommendation_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:migration_recommendation", data=json.dumps(migration_recommendation_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: migration_recommendation event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: migration_recommendation CANNOT write event for: " + ip_address)
                migration_recommendation_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: migration_recommendation could not call api for: " + ip_address)


        #migration_session api call
        try:
            helper.log_info("Dell PowerStore - Migration: migration_session beginning data collection for: " + ip_address)
            migration_session_url = 'https://' + ip_address + '/api/rest/migration_session?select=*'
            migration_session_response = requests.get(migration_session_url, auth=HTTPBasicAuth(username, password), verify=False)
            migration_session_path = json.loads(migration_session_response.text)
            migration_session_count = len(migration_session_path)
            helper.log_info("Dell PowerStore - Migration: " + str(migration_session_count) + " migration_session counted for: " + ip_address)
            migration_session_counter = 0
            #iterate throught the payload into events
            while migration_session_counter < migration_session_count:
                migration_session_path = json.loads(migration_session_response.text)[migration_session_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:migration_session", data=json.dumps(migration_session_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Migration: migration_session event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Migration: migration_session CANNOT write event for: " + ip_address)
                migration_session_counter += 1
        except:
            helper.log_error("Dell PowerStore - Migration: migration_session could not call api for: " + ip_address)
            
#########################    
# Monitoring Collection #
#########################
    if monitoring is True:
        helper.log_info("Dell PowerStore - Monitoring: Trying Monitoring collection for: " + ip_address)
        #alert api call
        try:
            helper.log_info("Dell PowerStore - Monitoring: alert beginning data collection for: " + ip_address)
            alert_url = 'https://' + ip_address + '/api/rest/alert?select=*'
            alert_response = requests.get(alert_url, auth=HTTPBasicAuth(username, password), verify=False)
            alert_path = json.loads(alert_response.text)
            alert_count = len(alert_path)
            helper.log_info("Dell PowerStore - Monitoring: " + str(alert_count) + " alert counted for: " + ip_address)
            alert_counter = 0
            #iterate throught the payload into events
            while alert_counter < alert_count:
                alert_path = json.loads(alert_response.text)[alert_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:alert", data=json.dumps(alert_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Monitoring: alert event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Monitoring: alert CANNOT write event for: " + ip_address)
                alert_counter += 1
        except:
            helper.log_error("Dell PowerStore - Monitoring: alert could not call api for: " + ip_address)


        #event api call
        try:
            helper.log_info("Dell PowerStore - Monitoring: event beginning data collection for: " + ip_address)
            event_url = 'https://' + ip_address + '/api/rest/event?select=*'
            event_response = requests.get(event_url, auth=HTTPBasicAuth(username, password), verify=False)
            event_path = json.loads(event_response.text)
            event_count = len(event_path)
            helper.log_info("Dell PowerStore - Monitoring: " + str(event_count) + " event counted for: " + ip_address)
            event_counter = 0
            #iterate throught the payload into events
            while event_counter < event_count:
                event_path = json.loads(event_response.text)[event_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:event", data=json.dumps(event_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Monitoring: event event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Monitoring: event CANNOT write event for: " + ip_address)
                event_counter += 1
        except:
            helper.log_error("Dell PowerStore - Monitoring: event could not call api for: " + ip_address)


        #job api call
        try:
            helper.log_info("Dell PowerStore - Monitoring: job beginning data collection for: " + ip_address)
            job_url = 'https://' + ip_address + '/api/rest/job?select=*'
            job_response = requests.get(job_url, auth=HTTPBasicAuth(username, password), verify=False)
            job_path = json.loads(job_response.text)
            job_count = len(job_path)
            helper.log_info("Dell PowerStore - Monitoring: " + str(job_count) + " job counted for: " + ip_address)
            job_counter = 0
            #iterate throught the payload into events
            while job_counter < job_count:
                job_path = json.loads(job_response.text)[job_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:job", data=json.dumps(job_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Monitoring: job event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Monitoring: job CANNOT write event for: " + ip_address)
                job_counter += 1
        except:
            helper.log_error("Dell PowerStore - Monitoring: job could not call api for: " + ip_address)


        #metrics api call
        try:
            helper.log_info("Dell PowerStore - Monitoring: metrics beginning data collection for: " + ip_address)
            metrics_url = 'https://' + ip_address + '/api/rest/metrics?select=*'
            metrics_response = requests.get(metrics_url, auth=HTTPBasicAuth(username, password), verify=False)
            metrics_path = json.loads(metrics_response.text)
            metrics_count = len(metrics_path)
            helper.log_info("Dell PowerStore - Monitoring: " + str(metrics_count) + " metrics counted for: " + ip_address)
            metrics_counter = 0
            #iterate throught the payload into events
            while metrics_counter < metrics_count:
                metrics_path = json.loads(metrics_response.text)[metrics_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:metrics", data=json.dumps(metrics_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Monitoring: metrics event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Monitoring: metrics CANNOT write event for: " + ip_address)
                metrics_counter += 1
        except:
            helper.log_error("Dell PowerStore - Monitoring: metrics could not call api for: " + ip_address)

#########################    
# Protection Collection #
#########################
    if protection is True:
        helper.log_info("Dell PowerStore - Protection: Trying Protection collection for: " + ip_address)
        #policy api call
        try:
            helper.log_info("Dell PowerStore - Protection: policy beginning data collection for: " + ip_address)
            policy_url = 'https://' + ip_address + '/api/rest/policy?select=*'
            policy_response = requests.get(policy_url, auth=HTTPBasicAuth(username, password), verify=False)
            policy_path = json.loads(policy_response.text)
            policy_count = len(policy_path)
            helper.log_info("Dell PowerStore - Protection: " + str(policy_count) + " policy counted for: " + ip_address)
            policy_counter = 0
            #iterate throught the payload into events
            while policy_counter < policy_count:
                policy_path = json.loads(policy_response.text)[policy_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:policy", data=json.dumps(policy_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Protection: policy event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Protection: policy CANNOT write event for: " + ip_address)
                policy_counter += 1
        except:
            helper.log_error("Dell PowerStore - Protection: policy could not call api for: " + ip_address)


        #remote_system api call
        try:
            helper.log_info("Dell PowerStore - Protection: remote_system beginning data collection for: " + ip_address)
            remote_system_url = 'https://' + ip_address + '/api/rest/remote_system?select=*'
            remote_system_response = requests.get(remote_system_url, auth=HTTPBasicAuth(username, password), verify=False)
            remote_system_path = json.loads(remote_system_response.text)
            remote_system_count = len(remote_system_path)
            helper.log_info("Dell PowerStore - Protection: " + str(remote_system_count) + " remote_system counted for: " + ip_address)
            remote_system_counter = 0
            #iterate throught the payload into events
            while remote_system_counter < remote_system_count:
                remote_system_path = json.loads(remote_system_response.text)[remote_system_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:remote_system", data=json.dumps(remote_system_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Protection: remote_system event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Protection: remote_system CANNOT write event for: " + ip_address)
                remote_system_counter += 1
        except:
            helper.log_error("Dell PowerStore - Protection: remote_system could not call api for: " + ip_address)


        #replication_rule api call
        try:
            helper.log_info("Dell PowerStore - Protection: replication_rule beginning data collection for: " + ip_address)
            replication_rule_url = 'https://' + ip_address + '/api/rest/replication_rule?select=*'
            replication_rule_response = requests.get(replication_rule_url, auth=HTTPBasicAuth(username, password), verify=False)
            replication_rule_path = json.loads(replication_rule_response.text)
            replication_rule_count = len(replication_rule_path)
            helper.log_info("Dell PowerStore - Protection: " + str(replication_rule_count) + " replication_rule counted for: " + ip_address)
            replication_rule_counter = 0
            #iterate throught the payload into events
            while replication_rule_counter < replication_rule_count:
                replication_rule_path = json.loads(replication_rule_response.text)[replication_rule_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:replication_rule", data=json.dumps(replication_rule_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Protection: replication_rule event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Protection: replication_rule CANNOT write event for: " + ip_address)
                replication_rule_counter += 1
        except:
            helper.log_error("Dell PowerStore - Protection: replication_rule could not call api for: " + ip_address)


        #replication_session api call
        try:
            helper.log_info("Dell PowerStore - Protection: replication_session beginning data collection for: " + ip_address)
            replication_session_url = 'https://' + ip_address + '/api/rest/replication_session?select=*'
            replication_session_response = requests.get(replication_session_url, auth=HTTPBasicAuth(username, password), verify=False)
            replication_session_path = json.loads(replication_session_response.text)
            replication_session_count = len(replication_session_path)
            helper.log_info("Dell PowerStore - Protection: " + str(replication_session_count) + " replication_session counted for: " + ip_address)
            replication_session_counter = 0
            #iterate throught the payload into events
            while replication_session_counter < replication_session_count:
                replication_session_path = json.loads(replication_session_response.text)[replication_session_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:replication_session", data=json.dumps(replication_session_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Protection: replication_session event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Protection: replication_session CANNOT write event for: " + ip_address)
                replication_session_counter += 1
        except:
            helper.log_error("Dell PowerStore - Protection: replication_session could not call api for: " + ip_address)


        #snapshot_rule api call
        try:
            helper.log_info("Dell PowerStore - Protection: snapshot_rule beginning data collection for: " + ip_address)
            snapshot_rule_url = 'https://' + ip_address + '/api/rest/snapshot_rule?select=*'
            snapshot_rule_response = requests.get(snapshot_rule_url, auth=HTTPBasicAuth(username, password), verify=False)
            snapshot_rule_path = json.loads(snapshot_rule_response.text)
            snapshot_rule_count = len(snapshot_rule_path)
            helper.log_info("Dell PowerStore - Protection: " + str(snapshot_rule_count) + " snapshot_rule counted for: " + ip_address)
            snapshot_rule_counter = 0
            #iterate throught the payload into events
            while snapshot_rule_counter < snapshot_rule_count:
                snapshot_rule_path = json.loads(snapshot_rule_response.text)[snapshot_rule_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:snapshot_rule", data=json.dumps(snapshot_rule_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Protection: snapshot_rule event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Protection: snapshot_rule CANNOT write event for: " + ip_address)
                snapshot_rule_counter += 1
        except:
            helper.log_error("Dell PowerStore - Protection: snapshot_rule could not call api for: " + ip_address)

#######################    
# Settings Collection #
#######################
    if settings is True:
        helper.log_info("Dell PowerStore - Settings: Trying Settings collection for: " + ip_address)
        #license api call
        try:
            helper.log_info("Dell PowerStore - Settings: license beginning data collection for: " + ip_address)
            license_url = 'https://' + ip_address + '/api/rest/license?select=*'
            license_response = requests.get(license_url, auth=HTTPBasicAuth(username, password), verify=False)
            license_path = json.loads(license_response.text)
            license_count = len(license_path)
            helper.log_info("Dell PowerStore - Settings: " + str(license_count) + " license counted for: " + ip_address)
            license_counter = 0
            #iterate throught the payload into events
            while license_counter < license_count:
                license_path = json.loads(license_response.text)[license_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:license", data=json.dumps(license_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: license event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: license CANNOT write event for: " + ip_address)
                license_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: license could not call api for: " + ip_address)


        #logout api call
        try:
            helper.log_info("Dell PowerStore - Settings: logout beginning data collection for: " + ip_address)
            logout_url = 'https://' + ip_address + '/api/rest/logout?select=*'
            logout_response = requests.get(logout_url, auth=HTTPBasicAuth(username, password), verify=False)
            logout_path = json.loads(logout_response.text)
            logout_count = len(logout_path)
            helper.log_info("Dell PowerStore - Settings: " + str(logout_count) + " logout counted for: " + ip_address)
            logout_counter = 0
            #iterate throught the payload into events
            while logout_counter < logout_count:
                logout_path = json.loads(logout_response.text)[logout_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:logout", data=json.dumps(logout_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: logout event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: logout CANNOT write event for: " + ip_address)
                logout_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: logout could not call api for: " + ip_address)


        #software_installed api call
        try:
            helper.log_info("Dell PowerStore - Settings: software_installed beginning data collection for: " + ip_address)
            software_installed_url = 'https://' + ip_address + '/api/rest/software_installed?select=*'
            software_installed_response = requests.get(software_installed_url, auth=HTTPBasicAuth(username, password), verify=False)
            software_installed_path = json.loads(software_installed_response.text)
            software_installed_count = len(software_installed_path)
            helper.log_info("Dell PowerStore - Settings: " + str(software_installed_count) + " software_installed counted for: " + ip_address)
            software_installed_counter = 0
            #iterate throught the payload into events
            while software_installed_counter < software_installed_count:
                software_installed_path = json.loads(software_installed_response.text)[software_installed_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:software_installed", data=json.dumps(software_installed_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: software_installed event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: software_installed CANNOT write event for: " + ip_address)
                software_installed_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: software_installed could not call api for: " + ip_address)


        #software_package api call
        try:
            helper.log_info("Dell PowerStore - Settings: software_package beginning data collection for: " + ip_address)
            software_package_url = 'https://' + ip_address + '/api/rest/software_package?select=*'
            software_package_response = requests.get(software_package_url, auth=HTTPBasicAuth(username, password), verify=False)
            software_package_path = json.loads(software_package_response.text)
            software_package_count = len(software_package_path)
            helper.log_info("Dell PowerStore - Settings: " + str(software_package_count) + " software_package counted for: " + ip_address)
            software_package_counter = 0
            #iterate throught the payload into events
            while software_package_counter < software_package_count:
                software_package_path = json.loads(software_package_response.text)[software_package_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:software_package", data=json.dumps(software_package_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: software_package event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: software_package CANNOT write event for: " + ip_address)
                software_package_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: software_package could not call api for: " + ip_address)


        #email_notify_destination api call
        try:
            helper.log_info("Dell PowerStore - Settings: email_notify_destination beginning data collection for: " + ip_address)
            email_notify_destination_url = 'https://' + ip_address + '/api/rest/email_notify_destination?select=*'
            email_notify_destination_response = requests.get(email_notify_destination_url, auth=HTTPBasicAuth(username, password), verify=False)
            email_notify_destination_path = json.loads(email_notify_destination_response.text)
            email_notify_destination_count = len(email_notify_destination_path)
            helper.log_info("Dell PowerStore - Settings: " + str(email_notify_destination_count) + " email_notify_destination counted for: " + ip_address)
            email_notify_destination_counter = 0
            #iterate throught the payload into events
            while email_notify_destination_counter < email_notify_destination_count:
                email_notify_destination_path = json.loads(email_notify_destination_response.text)[email_notify_destination_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:email_notify_destination", data=json.dumps(email_notify_destination_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: email_notify_destination event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: email_notify_destination CANNOT write event for: " + ip_address)
                email_notify_destination_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: email_notify_destination could not call api for: " + ip_address)


        #chap_config api call
        try:
            helper.log_info("Dell PowerStore - Settings: chap_config beginning data collection for: " + ip_address)
            chap_config_url = 'https://' + ip_address + '/api/rest/chap_config?select=*'
            chap_config_response = requests.get(chap_config_url, auth=HTTPBasicAuth(username, password), verify=False)
            chap_config_path = json.loads(chap_config_response.text)
            chap_config_count = len(chap_config_path)
            helper.log_info("Dell PowerStore - Settings: " + str(chap_config_count) + " chap_config counted for: " + ip_address)
            chap_config_counter = 0
            #iterate throught the payload into events
            while chap_config_counter < chap_config_count:
                chap_config_path = json.loads(chap_config_response.text)[chap_config_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:chap_config", data=json.dumps(chap_config_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: chap_config event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: chap_config CANNOT write event for: " + ip_address)
                chap_config_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: chap_config could not call api for: " + ip_address)


        #local_user api call
        try:
            helper.log_info("Dell PowerStore - Settings: local_user beginning data collection for: " + ip_address)
            local_user_url = 'https://' + ip_address + '/api/rest/local_user?select=*'
            local_user_response = requests.get(local_user_url, auth=HTTPBasicAuth(username, password), verify=False)
            local_user_path = json.loads(local_user_response.text)
            local_user_count = len(local_user_path)
            helper.log_info("Dell PowerStore - Settings: " + str(local_user_count) + " local_user counted for: " + ip_address)
            local_user_counter = 0
            #iterate throught the payload into events
            while local_user_counter < local_user_count:
                local_user_path = json.loads(local_user_response.text)[local_user_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:local_user", data=json.dumps(local_user_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: local_user event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: local_user CANNOT write event for: " + ip_address)
                local_user_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: local_user could not call api for: " + ip_address)


        #login_session api call
        try:
            helper.log_info("Dell PowerStore - Settings: login_session beginning data collection for: " + ip_address)
            login_session_url = 'https://' + ip_address + '/api/rest/login_session?select=*'
            login_session_response = requests.get(login_session_url, auth=HTTPBasicAuth(username, password), verify=False)
            login_session_path = json.loads(login_session_response.text)
            login_session_count = len(login_session_path)
            helper.log_info("Dell PowerStore - Settings: " + str(login_session_count) + " login_session counted for: " + ip_address)
            login_session_counter = 0
            #iterate throught the payload into events
            while login_session_counter < login_session_count:
                login_session_path = json.loads(login_session_response.text)[login_session_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:login_session", data=json.dumps(login_session_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: login_session event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: login_session CANNOT write event for: " + ip_address)
                login_session_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: login_session could not call api for: " + ip_address)


        #keystore_archive api call
        try:
            helper.log_info("Dell PowerStore - Settings: keystore_archive beginning data collection for: " + ip_address)
            keystore_archive_url = 'https://' + ip_address + '/api/rest/keystore_archive?select=*'
            keystore_archive_response = requests.get(keystore_archive_url, auth=HTTPBasicAuth(username, password), verify=False)
            keystore_archive_path = json.loads(keystore_archive_response.text)
            keystore_archive_count = len(keystore_archive_path)
            helper.log_info("Dell PowerStore - Settings: " + str(keystore_archive_count) + " keystore_archive counted for: " + ip_address)
            keystore_archive_counter = 0
            #iterate throught the payload into events
            while keystore_archive_counter < keystore_archive_count:
                keystore_archive_path = json.loads(keystore_archive_response.text)[keystore_archive_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:keystore_archive", data=json.dumps(keystore_archive_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: keystore_archive event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: keystore_archive CANNOT write event for: " + ip_address)
                keystore_archive_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: keystore_archive could not call api for: " + ip_address)


        #role api call
        try:
            helper.log_info("Dell PowerStore - Settings: role beginning data collection for: " + ip_address)
            role_url = 'https://' + ip_address + '/api/rest/role?select=*'
            role_response = requests.get(role_url, auth=HTTPBasicAuth(username, password), verify=False)
            role_path = json.loads(role_response.text)
            role_count = len(role_path)
            helper.log_info("Dell PowerStore - Settings: " + str(role_count) + " role counted for: " + ip_address)
            role_counter = 0
            #iterate throught the payload into events
            while role_counter < role_count:
                role_path = json.loads(role_response.text)[role_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:role", data=json.dumps(role_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: role event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: role CANNOT write event for: " + ip_address)
                role_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: role could not call api for: " + ip_address)


        #security_config api call
        try:
            helper.log_info("Dell PowerStore - Settings: security_config beginning data collection for: " + ip_address)
            security_config_url = 'https://' + ip_address + '/api/rest/security_config?select=*'
            security_config_response = requests.get(security_config_url, auth=HTTPBasicAuth(username, password), verify=False)
            security_config_path = json.loads(security_config_response.text)
            security_config_count = len(security_config_path)
            helper.log_info("Dell PowerStore - Settings: " + str(security_config_count) + " security_config counted for: " + ip_address)
            security_config_counter = 0
            #iterate throught the payload into events
            while security_config_counter < security_config_count:
                security_config_path = json.loads(security_config_response.text)[security_config_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:security_config", data=json.dumps(security_config_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: security_config event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: security_config CANNOT write event for: " + ip_address)
                security_config_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: security_config could not call api for: " + ip_address)


        #x509_certificate api call
        try:
            helper.log_info("Dell PowerStore - Settings: x509_certificate beginning data collection for: " + ip_address)
            x509_certificate_url = 'https://' + ip_address + '/api/rest/x509_certificate?select=*'
            x509_certificate_response = requests.get(x509_certificate_url, auth=HTTPBasicAuth(username, password), verify=False)
            x509_certificate_path = json.loads(x509_certificate_response.text)
            x509_certificate_count = len(x509_certificate_path)
            helper.log_info("Dell PowerStore - Settings: " + str(x509_certificate_count) + " x509_certificate counted for: " + ip_address)
            x509_certificate_counter = 0
            #iterate throught the payload into events
            while x509_certificate_counter < x509_certificate_count:
                x509_certificate_path = json.loads(x509_certificate_response.text)[x509_certificate_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:x509_certificate", data=json.dumps(x509_certificate_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: x509_certificate event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: x509_certificate CANNOT write event for: " + ip_address)
                x509_certificate_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: x509_certificate could not call api for: " + ip_address)


        #audit_event api call
        try:
            helper.log_info("Dell PowerStore - Settings: audit_event beginning data collection for: " + ip_address)
            audit_event_url = 'https://' + ip_address + '/api/rest/audit_event?select=*'
            audit_event_response = requests.get(audit_event_url, auth=HTTPBasicAuth(username, password), verify=False)
            audit_event_path = json.loads(audit_event_response.text)
            audit_event_count = len(audit_event_path)
            helper.log_info("Dell PowerStore - Settings: " + str(audit_event_count) + " audit_event counted for: " + ip_address)
            audit_event_counter = 0
            #iterate throught the payload into events
            while audit_event_counter < audit_event_count:
                audit_event_path = json.loads(audit_event_response.text)[audit_event_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:audit_event", data=json.dumps(audit_event_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: audit_event event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: audit_event CANNOT write event for: " + ip_address)
                audit_event_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: audit_event could not call api for: " + ip_address)


        #ip_pool_address api call
        try:
            helper.log_info("Dell PowerStore - Settings: ip_pool_address beginning data collection for: " + ip_address)
            ip_pool_address_url = 'https://' + ip_address + '/api/rest/ip_pool_address?select=*'
            ip_pool_address_response = requests.get(ip_pool_address_url, auth=HTTPBasicAuth(username, password), verify=False)
            ip_pool_address_path = json.loads(ip_pool_address_response.text)
            ip_pool_address_count = len(ip_pool_address_path)
            helper.log_info("Dell PowerStore - Settings: " + str(ip_pool_address_count) + " ip_pool_address counted for: " + ip_address)
            ip_pool_address_counter = 0
            #iterate throught the payload into events
            while ip_pool_address_counter < ip_pool_address_count:
                ip_pool_address_path = json.loads(ip_pool_address_response.text)[ip_pool_address_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:ip_pool_address", data=json.dumps(ip_pool_address_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: ip_pool_address event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: ip_pool_address CANNOT write event for: " + ip_address)
                ip_pool_address_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: ip_pool_address could not call api for: " + ip_address)


        #ip_port api call
        try:
            helper.log_info("Dell PowerStore - Settings: ip_port beginning data collection for: " + ip_address)
            ip_port_url = 'https://' + ip_address + '/api/rest/ip_port?select=*'
            ip_port_response = requests.get(ip_port_url, auth=HTTPBasicAuth(username, password), verify=False)
            ip_port_path = json.loads(ip_port_response.text)
            ip_port_count = len(ip_port_path)
            helper.log_info("Dell PowerStore - Settings: " + str(ip_port_count) + " ip_port counted for: " + ip_address)
            ip_port_counter = 0
            #iterate throught the payload into events
            while ip_port_counter < ip_port_count:
                ip_port_path = json.loads(ip_port_response.text)[ip_port_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:ip_port", data=json.dumps(ip_port_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: ip_port event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: ip_port CANNOT write event for: " + ip_address)
                ip_port_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: ip_port could not call api for: " + ip_address)


        #network api call
        try:
            helper.log_info("Dell PowerStore - Settings: network beginning data collection for: " + ip_address)
            network_url = 'https://' + ip_address + '/api/rest/network?select=*'
            network_response = requests.get(network_url, auth=HTTPBasicAuth(username, password), verify=False)
            network_path = json.loads(network_response.text)
            network_count = len(network_path)
            helper.log_info("Dell PowerStore - Settings: " + str(network_count) + " network counted for: " + ip_address)
            network_counter = 0
            #iterate throught the payload into events
            while network_counter < network_count:
                network_path = json.loads(network_response.text)[network_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:network", data=json.dumps(network_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: network event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: network CANNOT write event for: " + ip_address)
                network_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: network could not call api for: " + ip_address)


        #ntp api call
        try:
            helper.log_info("Dell PowerStore - Settings: ntp beginning data collection for: " + ip_address)
            ntp_url = 'https://' + ip_address + '/api/rest/ntp?select=*'
            ntp_response = requests.get(ntp_url, auth=HTTPBasicAuth(username, password), verify=False)
            ntp_path = json.loads(ntp_response.text)
            ntp_count = len(ntp_path)
            helper.log_info("Dell PowerStore - Settings: " + str(ntp_count) + " ntp counted for: " + ip_address)
            ntp_counter = 0
            #iterate throught the payload into events
            while ntp_counter < ntp_count:
                ntp_path = json.loads(ntp_response.text)[ntp_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:ntp", data=json.dumps(ntp_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: ntp event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: ntp CANNOT write event for: " + ip_address)
                ntp_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: ntp could not call api for: " + ip_address)


        #dns api call
        try:
            helper.log_info("Dell PowerStore - Settings: dns beginning data collection for: " + ip_address)
            dns_url = 'https://' + ip_address + '/api/rest/dns?select=*'
            dns_response = requests.get(dns_url, auth=HTTPBasicAuth(username, password), verify=False)
            dns_path = json.loads(dns_response.text)
            dns_count = len(dns_path)
            helper.log_info("Dell PowerStore - Settings: " + str(dns_count) + " dns counted for: " + ip_address)
            dns_counter = 0
            #iterate throught the payload into events
            while dns_counter < dns_count:
                dns_path = json.loads(dns_response.text)[dns_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:dns", data=json.dumps(dns_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: dns event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: dns CANNOT write event for: " + ip_address)
                dns_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: dns could not call api for: " + ip_address)


        #smtp_config api call
        try:
            helper.log_info("Dell PowerStore - Settings: smtp_config beginning data collection for: " + ip_address)
            smtp_config_url = 'https://' + ip_address + '/api/rest/smtp_config?select=*'
            smtp_config_response = requests.get(smtp_config_url, auth=HTTPBasicAuth(username, password), verify=False)
            smtp_config_path = json.loads(smtp_config_response.text)
            smtp_config_count = len(smtp_config_path)
            helper.log_info("Dell PowerStore - Settings: " + str(smtp_config_count) + " smtp_config counted for: " + ip_address)
            smtp_config_counter = 0
            #iterate throught the payload into events
            while smtp_config_counter < smtp_config_count:
                smtp_config_path = json.loads(smtp_config_response.text)[smtp_config_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:smtp_config", data=json.dumps(smtp_config_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: smtp_config event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: smtp_config CANNOT write event for: " + ip_address)
                smtp_config_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: smtp_config could not call api for: " + ip_address)


        #physical_switch api call
        try:
            helper.log_info("Dell PowerStore - Settings: physical_switch beginning data collection for: " + ip_address)
            physical_switch_url = 'https://' + ip_address + '/api/rest/physical_switch?select=*'
            physical_switch_response = requests.get(physical_switch_url, auth=HTTPBasicAuth(username, password), verify=False)
            physical_switch_path = json.loads(physical_switch_response.text)
            physical_switch_count = len(physical_switch_path)
            helper.log_info("Dell PowerStore - Settings: " + str(physical_switch_count) + " physical_switch counted for: " + ip_address)
            physical_switch_counter = 0
            #iterate throught the payload into events
            while physical_switch_counter < physical_switch_count:
                physical_switch_path = json.loads(physical_switch_response.text)[physical_switch_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:physical_switch", data=json.dumps(physical_switch_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Settings: physical_switch event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Settings: physical_switch CANNOT write event for: " + ip_address)
                physical_switch_counter += 1
        except:
            helper.log_error("Dell PowerStore - Settings: physical_switch could not call api for: " + ip_address)

######################    
# Storage Collection #
######################
    if storage is True:
        helper.log_info("Dell PowerStore - Storage: Trying Storage collection for: " + ip_address)
        #storage_container api call
        try:
            helper.log_info("Dell PowerStore - Storage: storage_container beginning data collection for: " + ip_address)
            storage_container_url = 'https://' + ip_address + '/api/rest/storage_container?select=*'
            storage_container_response = requests.get(storage_container_url, auth=HTTPBasicAuth(username, password), verify=False)
            storage_container_path = json.loads(storage_container_response.text)
            storage_container_count = len(storage_container_path)
            helper.log_info("Dell PowerStore - Storage: " + str(storage_container_count) + " storage_container counted for: " + ip_address)
            storage_container_counter = 0
            #iterate throught the payload into events
            while storage_container_counter < storage_container_count:
                storage_container_path = json.loads(storage_container_response.text)[storage_container_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:storage_container", data=json.dumps(storage_container_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: storage_container event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: storage_container CANNOT write event for: " + ip_address)
                storage_container_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: storage_container could not call api for: " + ip_address)


        #virtual_volume api call
        try:
            helper.log_info("Dell PowerStore - Storage: virtual_volume beginning data collection for: " + ip_address)
            virtual_volume_url = 'https://' + ip_address + '/api/rest/virtual_volume?select=*'
            virtual_volume_response = requests.get(virtual_volume_url, auth=HTTPBasicAuth(username, password), verify=False)
            virtual_volume_path = json.loads(virtual_volume_response.text)
            virtual_volume_count = len(virtual_volume_path)
            helper.log_info("Dell PowerStore - Storage: " + str(virtual_volume_count) + " virtual_volume counted for: " + ip_address)
            virtual_volume_counter = 0
            #iterate throught the payload into events
            while virtual_volume_counter < virtual_volume_count:
                virtual_volume_path = json.loads(virtual_volume_response.text)[virtual_volume_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:virtual_volume", data=json.dumps(virtual_volume_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: virtual_volume event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: virtual_volume CANNOT write event for: " + ip_address)
                virtual_volume_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: virtual_volume could not call api for: " + ip_address)


        #volume api call
        try:
            helper.log_info("Dell PowerStore - Storage: volume beginning data collection for: " + ip_address)
            volume_url = 'https://' + ip_address + '/api/rest/volume?select=*'
            volume_response = requests.get(volume_url, auth=HTTPBasicAuth(username, password), verify=False)
            volume_path = json.loads(volume_response.text)
            volume_count = len(volume_path)
            helper.log_info("Dell PowerStore - Storage: " + str(volume_count) + " volume counted for: " + ip_address)
            volume_counter = 0
            #iterate throught the payload into events
            while volume_counter < volume_count:
                volume_path = json.loads(volume_response.text)[volume_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:volume", data=json.dumps(volume_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: volume event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: volume CANNOT write event for: " + ip_address)
                volume_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: volume could not call api for: " + ip_address)


        #nas_server api call
        try:
            helper.log_info("Dell PowerStore - Storage: nas_server beginning data collection for: " + ip_address)
            nas_server_url = 'https://' + ip_address + '/api/rest/nas_server?select=*'
            nas_server_response = requests.get(nas_server_url, auth=HTTPBasicAuth(username, password), verify=False)
            nas_server_path = json.loads(nas_server_response.text)
            nas_server_count = len(nas_server_path)
            helper.log_info("Dell PowerStore - Storage: " + str(nas_server_count) + " nas_server counted for: " + ip_address)
            nas_server_counter = 0
            #iterate throught the payload into events
            while nas_server_counter < nas_server_count:
                nas_server_path = json.loads(nas_server_response.text)[nas_server_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:nas_server", data=json.dumps(nas_server_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: nas_server event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: nas_server CANNOT write event for: " + ip_address)
                nas_server_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: nas_server could not call api for: " + ip_address)


        #nfs_server api call
        try:
            helper.log_info("Dell PowerStore - Storage: nfs_server beginning data collection for: " + ip_address)
            nfs_server_url = 'https://' + ip_address + '/api/rest/nfs_server?select=*'
            nfs_server_response = requests.get(nfs_server_url, auth=HTTPBasicAuth(username, password), verify=False)
            nfs_server_path = json.loads(nfs_server_response.text)
            nfs_server_count = len(nfs_server_path)
            helper.log_info("Dell PowerStore - Storage: " + str(nfs_server_count) + " nfs_server counted for: " + ip_address)
            nfs_server_counter = 0
            #iterate throught the payload into events
            while nfs_server_counter < nfs_server_count:
                nfs_server_path = json.loads(nfs_server_response.text)[nfs_server_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:nfs_server", data=json.dumps(nfs_server_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: nfs_server event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: nfs_server CANNOT write event for: " + ip_address)
                nfs_server_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: nfs_server could not call api for: " + ip_address)


        #smb_server api call
        try:
            helper.log_info("Dell PowerStore - Storage: smb_server beginning data collection for: " + ip_address)
            smb_server_url = 'https://' + ip_address + '/api/rest/smb_server?select=*'
            smb_server_response = requests.get(smb_server_url, auth=HTTPBasicAuth(username, password), verify=False)
            smb_server_path = json.loads(smb_server_response.text)
            smb_server_count = len(smb_server_path)
            helper.log_info("Dell PowerStore - Storage: " + str(smb_server_count) + " smb_server counted for: " + ip_address)
            smb_server_counter = 0
            #iterate throught the payload into events
            while smb_server_counter < smb_server_count:
                smb_server_path = json.loads(smb_server_response.text)[smb_server_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:smb_server", data=json.dumps(smb_server_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: smb_server event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: smb_server CANNOT write event for: " + ip_address)
                smb_server_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: smb_server could not call api for: " + ip_address)


        #file_interface api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_interface beginning data collection for: " + ip_address)
            file_interface_url = 'https://' + ip_address + '/api/rest/file_interface?select=*'
            file_interface_response = requests.get(file_interface_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_interface_path = json.loads(file_interface_response.text)
            file_interface_count = len(file_interface_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_interface_count) + " file_interface counted for: " + ip_address)
            file_interface_counter = 0
            #iterate throught the payload into events
            while file_interface_counter < file_interface_count:
                file_interface_path = json.loads(file_interface_response.text)[file_interface_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_interface", data=json.dumps(file_interface_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_interface event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_interface CANNOT write event for: " + ip_address)
                file_interface_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_interface could not call api for: " + ip_address)


        #file_ndmp api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_ndmp beginning data collection for: " + ip_address)
            file_ndmp_url = 'https://' + ip_address + '/api/rest/file_ndmp?select=*'
            file_ndmp_response = requests.get(file_ndmp_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_ndmp_path = json.loads(file_ndmp_response.text)
            file_ndmp_count = len(file_ndmp_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_ndmp_count) + " file_ndmp counted for: " + ip_address)
            file_ndmp_counter = 0
            #iterate throught the payload into events
            while file_ndmp_counter < file_ndmp_count:
                file_ndmp_path = json.loads(file_ndmp_response.text)[file_ndmp_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_ndmp", data=json.dumps(file_ndmp_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_ndmp event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_ndmp CANNOT write event for: " + ip_address)
                file_ndmp_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_ndmp could not call api for: " + ip_address)


        #file_virus_checker api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_virus_checker beginning data collection for: " + ip_address)
            file_virus_checker_url = 'https://' + ip_address + '/api/rest/file_virus_checker?select=*'
            file_virus_checker_response = requests.get(file_virus_checker_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_virus_checker_path = json.loads(file_virus_checker_response.text)
            file_virus_checker_count = len(file_virus_checker_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_virus_checker_count) + " file_virus_checker counted for: " + ip_address)
            file_virus_checker_counter = 0
            #iterate throught the payload into events
            while file_virus_checker_counter < file_virus_checker_count:
                file_virus_checker_path = json.loads(file_virus_checker_response.text)[file_virus_checker_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_virus_checker", data=json.dumps(file_virus_checker_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_virus_checker event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_virus_checker CANNOT write event for: " + ip_address)
                file_virus_checker_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_virus_checker could not call api for: " + ip_address)


        #performance_rule api call
        try:
            helper.log_info("Dell PowerStore - Storage: performance_rule beginning data collection for: " + ip_address)
            performance_rule_url = 'https://' + ip_address + '/api/rest/performance_rule?select=*'
            performance_rule_response = requests.get(performance_rule_url, auth=HTTPBasicAuth(username, password), verify=False)
            performance_rule_path = json.loads(performance_rule_response.text)
            performance_rule_count = len(performance_rule_path)
            helper.log_info("Dell PowerStore - Storage: " + str(performance_rule_count) + " performance_rule counted for: " + ip_address)
            performance_rule_counter = 0
            #iterate throught the payload into events
            while performance_rule_counter < performance_rule_count:
                performance_rule_path = json.loads(performance_rule_response.text)[performance_rule_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:performance_rule", data=json.dumps(performance_rule_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: performance_rule event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: performance_rule CANNOT write event for: " + ip_address)
                performance_rule_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: performance_rule could not call api for: " + ip_address)


        #file_system api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_system beginning data collection for: " + ip_address)
            file_system_url = 'https://' + ip_address + '/api/rest/file_system?select=*'
            file_system_response = requests.get(file_system_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_system_path = json.loads(file_system_response.text)
            file_system_count = len(file_system_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_system_count) + " file_system counted for: " + ip_address)
            file_system_counter = 0
            #iterate throught the payload into events
            while file_system_counter < file_system_count:
                file_system_path = json.loads(file_system_response.text)[file_system_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_system", data=json.dumps(file_system_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_system event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_system CANNOT write event for: " + ip_address)
                file_system_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_system could not call api for: " + ip_address)


        #smb_share api call
        try:
            helper.log_info("Dell PowerStore - Storage: smb_share beginning data collection for: " + ip_address)
            smb_share_url = 'https://' + ip_address + '/api/rest/smb_share?select=*'
            smb_share_response = requests.get(smb_share_url, auth=HTTPBasicAuth(username, password), verify=False)
            smb_share_path = json.loads(smb_share_response.text)
            smb_share_count = len(smb_share_path)
            helper.log_info("Dell PowerStore - Storage: " + str(smb_share_count) + " smb_share counted for: " + ip_address)
            smb_share_counter = 0
            #iterate throught the payload into events
            while smb_share_counter < smb_share_count:
                smb_share_path = json.loads(smb_share_response.text)[smb_share_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:smb_share", data=json.dumps(smb_share_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: smb_share event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: smb_share CANNOT write event for: " + ip_address)
                smb_share_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: smb_share could not call api for: " + ip_address)


        #volume_group api call
        try:
            helper.log_info("Dell PowerStore - Storage: volume_group beginning data collection for: " + ip_address)
            volume_group_url = 'https://' + ip_address + '/api/rest/volume_group?select=*'
            volume_group_response = requests.get(volume_group_url, auth=HTTPBasicAuth(username, password), verify=False)
            volume_group_path = json.loads(volume_group_response.text)
            volume_group_count = len(volume_group_path)
            helper.log_info("Dell PowerStore - Storage: " + str(volume_group_count) + " volume_group counted for: " + ip_address)
            volume_group_counter = 0
            #iterate throught the payload into events
            while volume_group_counter < volume_group_count:
                volume_group_path = json.loads(volume_group_response.text)[volume_group_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:volume_group", data=json.dumps(volume_group_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: volume_group event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: volume_group CANNOT write event for: " + ip_address)
                volume_group_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: volume_group could not call api for: " + ip_address)


        #file_tree_quota api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_tree_quota beginning data collection for: " + ip_address)
            file_tree_quota_url = 'https://' + ip_address + '/api/rest/file_tree_quota?select=*'
            file_tree_quota_response = requests.get(file_tree_quota_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_tree_quota_path = json.loads(file_tree_quota_response.text)
            file_tree_quota_count = len(file_tree_quota_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_tree_quota_count) + " file_tree_quota counted for: " + ip_address)
            file_tree_quota_counter = 0
            #iterate throught the payload into events
            while file_tree_quota_counter < file_tree_quota_count:
                file_tree_quota_path = json.loads(file_tree_quota_response.text)[file_tree_quota_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_tree_quota", data=json.dumps(file_tree_quota_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_tree_quota event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_tree_quota CANNOT write event for: " + ip_address)
                file_tree_quota_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_tree_quota could not call api for: " + ip_address)


        #file_user_quota api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_user_quota beginning data collection for: " + ip_address)
            file_user_quota_url = 'https://' + ip_address + '/api/rest/file_user_quota?select=*'
            file_user_quota_response = requests.get(file_user_quota_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_user_quota_path = json.loads(file_user_quota_response.text)
            file_user_quota_count = len(file_user_quota_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_user_quota_count) + " file_user_quota counted for: " + ip_address)
            file_user_quota_counter = 0
            #iterate throught the payload into events
            while file_user_quota_counter < file_user_quota_count:
                file_user_quota_path = json.loads(file_user_quota_response.text)[file_user_quota_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_user_quota", data=json.dumps(file_user_quota_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_user_quota event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_user_quota CANNOT write event for: " + ip_address)
                file_user_quota_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_user_quota could not call api for: " + ip_address)


        #file_dns api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_dns beginning data collection for: " + ip_address)
            file_dns_url = 'https://' + ip_address + '/api/rest/file_dns?select=*'
            file_dns_response = requests.get(file_dns_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_dns_path = json.loads(file_dns_response.text)
            file_dns_count = len(file_dns_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_dns_count) + " file_dns counted for: " + ip_address)
            file_dns_counter = 0
            #iterate throught the payload into events
            while file_dns_counter < file_dns_count:
                file_dns_path = json.loads(file_dns_response.text)[file_dns_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_dns", data=json.dumps(file_dns_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_dns event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_dns CANNOT write event for: " + ip_address)
                file_dns_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_dns could not call api for: " + ip_address)


        #file_ftp api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_ftp beginning data collection for: " + ip_address)
            file_ftp_url = 'https://' + ip_address + '/api/rest/file_ftp?select=*'
            file_ftp_response = requests.get(file_ftp_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_ftp_path = json.loads(file_ftp_response.text)
            file_ftp_count = len(file_ftp_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_ftp_count) + " file_ftp counted for: " + ip_address)
            file_ftp_counter = 0
            #iterate throught the payload into events
            while file_ftp_counter < file_ftp_count:
                file_ftp_path = json.loads(file_ftp_response.text)[file_ftp_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_ftp", data=json.dumps(file_ftp_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_ftp event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_ftp CANNOT write event for: " + ip_address)
                file_ftp_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_ftp could not call api for: " + ip_address)


        #file_interface_route api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_interface_route beginning data collection for: " + ip_address)
            file_interface_route_url = 'https://' + ip_address + '/api/rest/file_interface_route?select=*'
            file_interface_route_response = requests.get(file_interface_route_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_interface_route_path = json.loads(file_interface_route_response.text)
            file_interface_route_count = len(file_interface_route_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_interface_route_count) + " file_interface_route counted for: " + ip_address)
            file_interface_route_counter = 0
            #iterate throught the payload into events
            while file_interface_route_counter < file_interface_route_count:
                file_interface_route_path = json.loads(file_interface_route_response.text)[file_interface_route_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_interface_route", data=json.dumps(file_interface_route_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_interface_route event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_interface_route CANNOT write event for: " + ip_address)
                file_interface_route_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_interface_route could not call api for: " + ip_address)


        #file_kerberos api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_kerberos beginning data collection for: " + ip_address)
            file_kerberos_url = 'https://' + ip_address + '/api/rest/file_kerberos?select=*'
            file_kerberos_response = requests.get(file_kerberos_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_kerberos_path = json.loads(file_kerberos_response.text)
            file_kerberos_count = len(file_kerberos_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_kerberos_count) + " file_kerberos counted for: " + ip_address)
            file_kerberos_counter = 0
            #iterate throught the payload into events
            while file_kerberos_counter < file_kerberos_count:
                file_kerberos_path = json.loads(file_kerberos_response.text)[file_kerberos_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_kerberos", data=json.dumps(file_kerberos_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_kerberos event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_kerberos CANNOT write event for: " + ip_address)
                file_kerberos_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_kerberos could not call api for: " + ip_address)


        #file_ldap api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_ldap beginning data collection for: " + ip_address)
            file_ldap_url = 'https://' + ip_address + '/api/rest/file_ldap?select=*'
            file_ldap_response = requests.get(file_ldap_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_ldap_path = json.loads(file_ldap_response.text)
            file_ldap_count = len(file_ldap_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_ldap_count) + " file_ldap counted for: " + ip_address)
            file_ldap_counter = 0
            #iterate throught the payload into events
            while file_ldap_counter < file_ldap_count:
                file_ldap_path = json.loads(file_ldap_response.text)[file_ldap_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_ldap", data=json.dumps(file_ldap_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_ldap event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_ldap CANNOT write event for: " + ip_address)
                file_ldap_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_ldap could not call api for: " + ip_address)


        #file_nis api call
        try:
            helper.log_info("Dell PowerStore - Storage: file_nis beginning data collection for: " + ip_address)
            file_nis_url = 'https://' + ip_address + '/api/rest/file_nis?select=*'
            file_nis_response = requests.get(file_nis_url, auth=HTTPBasicAuth(username, password), verify=False)
            file_nis_path = json.loads(file_nis_response.text)
            file_nis_count = len(file_nis_path)
            helper.log_info("Dell PowerStore - Storage: " + str(file_nis_count) + " file_nis counted for: " + ip_address)
            file_nis_counter = 0
            #iterate throught the payload into events
            while file_nis_counter < file_nis_count:
                file_nis_path = json.loads(file_nis_response.text)[file_nis_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:file_nis", data=json.dumps(file_nis_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: file_nis event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: file_nis CANNOT write event for: " + ip_address)
                file_nis_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: file_nis could not call api for: " + ip_address)


        #nfs_export api call
        try:
            helper.log_info("Dell PowerStore - Storage: nfs_export beginning data collection for: " + ip_address)
            nfs_export_url = 'https://' + ip_address + '/api/rest/nfs_export?select=*'
            nfs_export_response = requests.get(nfs_export_url, auth=HTTPBasicAuth(username, password), verify=False)
            nfs_export_path = json.loads(nfs_export_response.text)
            nfs_export_count = len(nfs_export_path)
            helper.log_info("Dell PowerStore - Storage: " + str(nfs_export_count) + " nfs_export counted for: " + ip_address)
            nfs_export_counter = 0
            #iterate throught the payload into events
            while nfs_export_counter < nfs_export_count:
                nfs_export_path = json.loads(nfs_export_response.text)[nfs_export_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:nfs_export", data=json.dumps(nfs_export_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Storage: nfs_export event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Storage: nfs_export CANNOT write event for: " + ip_address)
                nfs_export_counter += 1
        except:
            helper.log_error("Dell PowerStore - Storage: nfs_export could not call api for: " + ip_address)

######################    
# Support Collection #
######################
    if support is True:
        helper.log_info("Dell PowerStore - Support: Trying Support collection for: " + ip_address)
        #service_config api call
        try:
            helper.log_info("Dell PowerStore - Support: service_config beginning data collection for: " + ip_address)
            service_config_url = 'https://' + ip_address + '/api/rest/service_config?select=*'
            service_config_response = requests.get(service_config_url, auth=HTTPBasicAuth(username, password), verify=False)
            service_config_path = json.loads(service_config_response.text)
            service_config_count = len(service_config_path)
            helper.log_info("Dell PowerStore - Support: " + str(service_config_count) + " service_config counted for: " + ip_address)
            service_config_counter = 0
            #iterate throught the payload into events
            while service_config_counter < service_config_count:
                service_config_path = json.loads(service_config_response.text)[service_config_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:service_config", data=json.dumps(service_config_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Support: service_config event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Support: service_config CANNOT write event for: " + ip_address)
                service_config_counter += 1
        except:
            helper.log_error("Dell PowerStore - Support: service_config could not call api for: " + ip_address)


        #service_user api call
        try:
            helper.log_info("Dell PowerStore - Support: service_user beginning data collection for: " + ip_address)
            service_user_url = 'https://' + ip_address + '/api/rest/service_user?select=*'
            service_user_response = requests.get(service_user_url, auth=HTTPBasicAuth(username, password), verify=False)
            service_user_path = json.loads(service_user_response.text)
            service_user_count = len(service_user_path)
            helper.log_info("Dell PowerStore - Support: " + str(service_user_count) + " service_user counted for: " + ip_address)
            service_user_counter = 0
            #iterate throught the payload into events
            while service_user_counter < service_user_count:
                service_user_path = json.loads(service_user_response.text)[service_user_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:service_user", data=json.dumps(service_user_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Support: service_user event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Support: service_user CANNOT write event for: " + ip_address)
                service_user_counter += 1
        except:
            helper.log_error("Dell PowerStore - Support: service_user could not call api for: " + ip_address)


        #maintenance_window api call
        try:
            helper.log_info("Dell PowerStore - Support: maintenance_window beginning data collection for: " + ip_address)
            maintenance_window_url = 'https://' + ip_address + '/api/rest/maintenance_window?select=*'
            maintenance_window_response = requests.get(maintenance_window_url, auth=HTTPBasicAuth(username, password), verify=False)
            maintenance_window_path = json.loads(maintenance_window_response.text)
            maintenance_window_count = len(maintenance_window_path)
            helper.log_info("Dell PowerStore - Support: " + str(maintenance_window_count) + " maintenance_window counted for: " + ip_address)
            maintenance_window_counter = 0
            #iterate throught the payload into events
            while maintenance_window_counter < maintenance_window_count:
                maintenance_window_path = json.loads(maintenance_window_response.text)[maintenance_window_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:maintenance_window", data=json.dumps(maintenance_window_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - Support: maintenance_window event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - Support: maintenance_window CANNOT write event for: " + ip_address)
                maintenance_window_counter += 1
        except:
            helper.log_error("Dell PowerStore - Support: maintenance_window could not call api for: " + ip_address)
    
#############################    
# Sys & Hardware Collection #
#############################
    if system_and_hardware is True:
        helper.log_info("Dell PowerStore - System_and_Hardware: Trying System_and_Hardware collection for: " + ip_address)
        #appliance api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: appliance beginning data collection for: " + ip_address)
            appliance_url = 'https://' + ip_address + '/api/rest/appliance?select=*'
            appliance_response = requests.get(appliance_url, auth=HTTPBasicAuth(username, password), verify=False)
            appliance_path = json.loads(appliance_response.text)
            appliance_count = len(appliance_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(appliance_count) + " appliance counted for: " + ip_address)
            appliance_counter = 0
            #iterate throught the payload into events
            while appliance_counter < appliance_count:
                appliance_path = json.loads(appliance_response.text)[appliance_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:appliance", data=json.dumps(appliance_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: appliance event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: appliance CANNOT write event for: " + ip_address)
                appliance_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: appliance could not call api for: " + ip_address)


        #cluster api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: cluster beginning data collection for: " + ip_address)
            cluster_url = 'https://' + ip_address + '/api/rest/cluster?select=*'
            cluster_response = requests.get(cluster_url, auth=HTTPBasicAuth(username, password), verify=False)
            cluster_path = json.loads(cluster_response.text)
            cluster_count = len(cluster_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(cluster_count) + " cluster counted for: " + ip_address)
            cluster_counter = 0
            #iterate throught the payload into events
            while cluster_counter < cluster_count:
                cluster_path = json.loads(cluster_response.text)[cluster_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:cluster", data=json.dumps(cluster_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: cluster event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: cluster CANNOT write event for: " + ip_address)
                cluster_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: cluster could not call api for: " + ip_address)


        #node api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: node beginning data collection for: " + ip_address)
            node_url = 'https://' + ip_address + '/api/rest/node?select=*'
            node_response = requests.get(node_url, auth=HTTPBasicAuth(username, password), verify=False)
            node_path = json.loads(node_response.text)
            node_count = len(node_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(node_count) + " node counted for: " + ip_address)
            node_counter = 0
            #iterate throught the payload into events
            while node_counter < node_count:
                node_path = json.loads(node_response.text)[node_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:node", data=json.dumps(node_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: node event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: node CANNOT write event for: " + ip_address)
                node_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: node could not call api for: " + ip_address)


        #hardware api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: hardware beginning data collection for: " + ip_address)
            hardware_url = 'https://' + ip_address + '/api/rest/hardware?select=*'
            hardware_response = requests.get(hardware_url, auth=HTTPBasicAuth(username, password), verify=False)
            hardware_path = json.loads(hardware_response.text)
            hardware_count = len(hardware_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(hardware_count) + " hardware counted for: " + ip_address)
            hardware_counter = 0
            #iterate throught the payload into events
            while hardware_counter < hardware_count:
                hardware_path = json.loads(hardware_response.text)[hardware_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:hardware", data=json.dumps(hardware_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: hardware event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: hardware CANNOT write event for: " + ip_address)
                hardware_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: hardware could not call api for: " + ip_address)


        #eth_port api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: eth_port beginning data collection for: " + ip_address)
            eth_port_url = 'https://' + ip_address + '/api/rest/eth_port?select=*'
            eth_port_response = requests.get(eth_port_url, auth=HTTPBasicAuth(username, password), verify=False)
            eth_port_path = json.loads(eth_port_response.text)
            eth_port_count = len(eth_port_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(eth_port_count) + " eth_port counted for: " + ip_address)
            eth_port_counter = 0
            #iterate throught the payload into events
            while eth_port_counter < eth_port_count:
                eth_port_path = json.loads(eth_port_response.text)[eth_port_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:ethport", data=json.dumps(eth_port_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: eth_port event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: eth_port CANNOT write event for: " + ip_address)
                eth_port_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: eth_port could not call api for: " + ip_address)


        #fc_port api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: fc_port beginning data collection for: " + ip_address)
            fc_port_url = 'https://' + ip_address + '/api/rest/fc_port?select=*'
            fc_port_response = requests.get(fc_port_url, auth=HTTPBasicAuth(username, password), verify=False)
            fc_port_path = json.loads(fc_port_response.text)
            fc_port_count = len(fc_port_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(fc_port_count) + " fc_port counted for: " + ip_address)
            fc_port_counter = 0
            #iterate throught the payload into events
            while fc_port_counter < fc_port_count:
                fc_port_path = json.loads(fc_port_response.text)[fc_port_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:fc_port", data=json.dumps(fc_port_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: fc_port event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: fc_port CANNOT write event for: " + ip_address)
                fc_port_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: fc_port could not call api for: " + ip_address)


        #sas_port api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: sas_port beginning data collection for: " + ip_address)
            sas_port_url = 'https://' + ip_address + '/api/rest/sas_port?select=*'
            sas_port_response = requests.get(sas_port_url, auth=HTTPBasicAuth(username, password), verify=False)
            sas_port_path = json.loads(sas_port_response.text)
            sas_port_count = len(sas_port_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(sas_port_count) + " sas_port counted for: " + ip_address)
            sas_port_counter = 0
            #iterate throught the payload into events
            while sas_port_counter < sas_port_count:
                sas_port_path = json.loads(sas_port_response.text)[sas_port_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:sas_port", data=json.dumps(sas_port_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: sas_port event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: sas_port CANNOT write event for: " + ip_address)
                sas_port_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: sas_port could not call api for: " + ip_address)


        #veth_port api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: veth_port beginning data collection for: " + ip_address)
            veth_port_url = 'https://' + ip_address + '/api/rest/veth_port?select=*'
            veth_port_response = requests.get(veth_port_url, auth=HTTPBasicAuth(username, password), verify=False)
            veth_port_path = json.loads(veth_port_response.text)
            veth_port_count = len(veth_port_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(veth_port_count) + " veth_port counted for: " + ip_address)
            veth_port_counter = 0
            #iterate throught the payload into events
            while veth_port_counter < veth_port_count:
                veth_port_path = json.loads(veth_port_response.text)[veth_port_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:vethport", data=json.dumps(veth_port_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: veth_port event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: veth_port CANNOT write event for: " + ip_address)
                veth_port_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: veth_port could not call api for: " + ip_address)


        #bond api call
        try:
            helper.log_info("Dell PowerStore - System_and_Hardware: bond beginning data collection for: " + ip_address)
            bond_url = 'https://' + ip_address + '/api/rest/bond?select=*'
            bond_response = requests.get(bond_url, auth=HTTPBasicAuth(username, password), verify=False)
            bond_path = json.loads(bond_response.text)
            bond_count = len(bond_path)
            helper.log_info("Dell PowerStore - System_and_Hardware: " + str(bond_count) + " bond counted for: " + ip_address)
            bond_counter = 0
            #iterate throught the payload into events
            while bond_counter < bond_count:
                bond_path = json.loads(bond_response.text)[bond_counter]
                try:
                    event = helper.new_event(host=ip_address, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="dell:powerstore:bond", data=json.dumps(bond_path), done=True, unbroken=False)
                    ew.write_event(event)
                    helper.log_info("Dell PowerStore - System_and_Hardware: bond event data created for: " + ip_address)
                except:
                    helper.log_error("ERROR Dell PowerStore - System_and_Hardware: bond CANNOT write event for: " + ip_address)
                bond_counter += 1
        except:
            helper.log_error("Dell PowerStore - System_and_Hardware: bond could not call api for: " + ip_address)


################
# Finishing up #
################
    helper.log_info("FINISH: Ending collection for: " + ip_address)
    end_time = round(time.time()-start,2)
    helper.log_info("FINISH: Collection took: " + str(end_time) + " secs to collect data for: " + ip_address)