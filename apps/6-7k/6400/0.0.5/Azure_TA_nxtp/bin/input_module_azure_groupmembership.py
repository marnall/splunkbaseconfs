
# encoding = utf-8

import os
import sys
import time
import datetime
import json
from azure_ta_nxtp.graph import Request, ManagementConnection, strip_empties_from_dict

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
    # tenant_id = definition.parameters.get('tenant_id', None)
    # client_id = definition.parameters.get('client_id', None)
    # client_secret = definition.parameters.get('client_secret', None)
    pass

# Azure Groups
# Azure Groups
def collect_events(helper, ew):
    startTime = datetime.datetime.now().timestamp()
    api_manager = ManagementConnection(helper)
    groups = {}
    helper.log_info("Started fetching all Groups - User Correlations")
    for user in Request(connection=api_manager, endpoint="users", mode="GET").run():
        helper.log_debug(f"Fetching all groups for User: {user}")
        for group in Request(connection=api_manager, endpoint=f"users/{user['id']}/memberOf").run():
            id = group['id']
            if groups.get(id, 0) == 0:
                groups[id] = {}
                groups[id] = {'displayName' : group['displayName'], 'id' : group['id']}
                groups[id]['userId'] = [user['id']]
            else:
                groups[id]['userId'].append(user['id'])
    for group in groups:
        ew.write_event(
            helper.new_event(
                source=f"azure:{helper.get_arg('tenant_id')}",
                data=json.dumps(groups[group]),
            )
        )
    timeToFetch = datetime.datetime.now().timestamp() - startTime
    helper.log_info(f"Successfully wrote all {len(groups)} Groups in {timeToFetch:.2f} Seconds!")