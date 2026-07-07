# encoding = utf-8

from vrops.vrops import VROpsClient
from collections import defaultdict
import json

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
    # global_account = definition.parameters.get('global_account', None)
    pass

def collect_events(helper, ew):
    endpoint = helper.get_arg("vrops_endpoint")
    use_ssl = helper.get_arg("use_ssl")
    authsrc = helper.get_arg("authsrc")
    account = helper.get_arg('global_account')
    helper.log_info(use_ssl)
    helper.log_info(use_ssl == 1)
    vrops_client = VROpsClient(helper,username=account['username'],password=account['password'],authsource=authsrc,target=endpoint,use_ssl=use_ssl)
    token_check = vrops_client.token_check()
    index = helper.get_output_index()
    sourcetype = helper.get_sourcetype()
    source = helper.get_input_type()

    if token_check: # Check if the client logged in
        metrics = vrops_client.get_metrics() # Get Metrics from VROPS
        metric_dict = {} # Create a dict

        if len(metrics) < 1:
            helper.log_debug("Metrics list returned was empty")
            return True

        for resource in metrics: # Loop through each resource in metrics response
            resource_metrics = resource.get('metrics', None)

            if resource_metrics == None:
                helper.log_info("No Metrics found for Resource")
                continue
            resource = resource.get('resource', {})

            resource_name = resource.get('name', None) # Get resource Name
            resource_uuid = resource.get('uuid', None) # Get Resource UUID
            if resource_name == None:
                helper.log_info(f"No resource name found for resource with uuid {resource_uuid}")
                continue

            for m in resource_metrics: # Loop through each metric in resource
                event_data = metric_dict.get(f'{resource_name}', defaultdict(lambda: "Not Found"))
                event_data['fields'] = event_data.get('fields',  defaultdict(dict))
                event_data['fields']['uuid'] = resource_uuid
                event_data['fields']['resourcekind'] = resource.get('resourcekind', 'Adapter')
                event_data['fields']['adapterkind'] = resource.get('resourcekind', None)
                resource_parent = resource.get('parent', None)

                if resource_parent:
                    event_data['fields']['parent'] = resource_parent

                metric_name = m['name']

                event_data['fields'][f'{metric_name}'] = m.get('value', 0.0)
                event_data['host'] = resource['name']
                event_data['index'] = index
                event_data['sourcetype'] = sourcetype
                event_data['source'] = source
                metric_dict[f'{resource_name}'] = event_data

        for _, event_data in metric_dict.items():
            srct = event_data.get('sourcetype', sourcetype)
            src = event_data.get('source', source)
            ind = event_data.get('index', index)
            host = event_data.get('host', 'null')

            if event_data.get('fields', None):
                data = json.dumps(event_data['fields'])
                event = helper.new_event(source=src, index=ind, sourcetype=srct, data=data, host=host)
                ew.write_event(event)
            else:
                helper.log_info(f"No metrics found for host {host, None}")
    else:
        helper.log_error('Could not retrieve token')
