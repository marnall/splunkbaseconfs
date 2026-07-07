'''
A script gets all the roles and rename the capabilities to the new values as needed.
'''

import os
import sys
import json
import getpass
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import rest, auth

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from itsi.itsi_utils import ItsiSettingsImporter

SPLUNKD_HOST_PATH = 'https://localhost'
SPLUNK_USER = 'admin'
SPLUNK_PASSWORD = ''

session_key = auth.getSessionKey(SPLUNK_USER, SPLUNK_PASSWORD, SPLUNKD_HOST_PATH)

capabilities_map = {
    'read-notable_event': 'read_notable_event',
    'write-notable_event': 'write_notable_event',
    'delete-notable_event': 'delete_notable_event',
    'read-notable_event_action': 'read_notable_event_action',
    'execute-notable_event_action': 'execute_notable_event_action',
    'read-module_interface': 'read_module_interface',
    'write-module_interface': 'write_module_interface',
    'delete-module_interface': 'delete_module_interface',
    'read-maintenance_calendar': 'read_maintenance_calendar',
    'write-maintenance_calendar': 'write_maintenance_calendar',
    'delete-maintenance_calendar': 'delete_maintenance_calendar',
}
old_capabilities = capabilities_map.keys()
new_capabilities = list(capabilities_map.values())


def verify_capabilities(capabilities):
    need_to_save = False
    for idx, old_c in enumerate(old_capabilities):
        if old_c in capabilities:
            index = capabilities.index(old_c)
            capabilities[index] = new_capabilities[idx]
            need_to_save = True
    return capabilities, need_to_save


def save_updated_role(role_name, capabilities):
    uri = '/services/authorization/roles/%s' % role_name
    postargs = {'capabilities': capabilities}
    try:
        response, content = rest.simpleRequest(
            uri,
            method='POST',
            sessionKey=session_key,
            postargs=postargs,
            raiseAllErrors=False)
        if response.status != 200:
            print('Unable to rename capabilities for role %s' % role_name)
        else:
            print('Successfully renamed capabilities for role %s' % role_name)
    except Exception as e:
        print('Unable to rename capabilities for role %s' % role_name)
        print(e)


def get_all_roles_and_rename_capabilities():
    uri = '/services/authorization/roles'
    getargs = {'output_mode': 'json', 'count': 0}
    try:
        response, content = rest.simpleRequest(
            uri,
            method='GET',
            getargs=getargs,
            sessionKey=session_key,
            raiseAllErrors=False)
        res = json.loads(content)
        for role_entry in res.get('entry', []):
            role_content = role_entry.get('content', {})
            capabilities = role_content.get('capabilities', [])
            updated_capabilities, need_to_save = verify_capabilities(capabilities)
            if need_to_save:
                role_name = role_entry.get('name', '')
                print('Found capabilities to rename for role %s' % role_name)
                if role_name:
                    save_updated_role(role_name, updated_capabilities)
    except Exception as e:
        print(e)
        return False
    print('Successfully renamed capabilities')
    return True


get_all_roles_and_rename_capabilities()

print("Done")
