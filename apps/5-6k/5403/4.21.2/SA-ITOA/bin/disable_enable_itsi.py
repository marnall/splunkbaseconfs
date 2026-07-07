# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
disable_enable_itsi.py
A script that allows for the following:
    - Move objects from kvstore collection(s) to a file on disk
    - Restore objects from file on disk to kvstore:
        - by replacing existing kv store data
        - by appending to existing kv store data if possible
"""

import sys
import getpass
import json
from collections import defaultdict
import splunk.rest as rest

from splunk import auth
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
import itsi_py3
from ITOA.setup_logging import logger
from ITOA.saved_search_utility import SavedSearch
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.service_template.service_template_utils import ServiceTemplateUtils
from itsi.objects.itsi_backup_restore import ItsiBackupRestore


SPLUNKD_HOST_PATH = 'https://localhost'
SPLUNKD_PORT = '8089'
SPLUNK_USER = 'admin'

block_list = ['udp', 'ssl', 'splunktcptoken', 'all', 'http',
              'oneshot', 'script', 'tcp', 'cooked', 'monitor']

print('\n#################################################\n'
      '              Enable/Disable ITSI               \n'
      'Use this script to enable and disable ITSI. \n'
      'The following knowledge objects are disabled\n'
      'when you execute this script:\n'
      '  * All ITSI modular inputs\n'
      '  * All scheduled, ad-hoc, and base searches\n'
      '  * Rules Engine Java processes\n'
      'You have the choice to disable modular inputs,\n'
      'saved searches, or both.\n'
      'Warning:\n'
      'This script does not terminate ongoing processes\n'
      'such as service template syncs and backup/restore jobs.\n'
      'It is advised to wait for those operations to\n'
      'complete before disabling ITSI.\n'
      '##################################################\n')


def toggle_ui(is_visible):
    try:
        postargs = {'visible': is_visible}
        response, content = rest.simpleRequest('/services/apps/local/itsi',
                                               sessionKey=session_key,
                                               postargs=postargs,
                                               method='POST')
        if response.status != 200 and response.status != 201:
            logger.error("Failed to set UI access to: %s, error: %s", False, response)
        else:
            if is_visible:
                logger.info("Successfully enabled UI access.")
            else:
                logger.info("Successfully disabled UI access.")
    except Exception as e:
        logger.exception(e)


if __name__ == '__main__':
    retries = 3
    splunkd_port = None
    handle_mi = False
    handle_ss = False
    count_updated_mi = 0
    count_updated_ss = 0
    while not splunkd_port and retries:
        splunkd_port = input(('Enter splunkd port. Press enter to use'
                              ' %s: ') % SPLUNKD_PORT)
        if not splunkd_port.strip():
            splunkd_port = SPLUNKD_PORT
        else:
            try:
                int(splunkd_port)
            except ValueError:
                retries -= 1
                print('Invalid port. Try again. {} retries left.'.format(retries))
                continue
    if not retries and not splunkd_port:
        print('You have reached the maximum number of retries. Run the script again.')
        sys.exit(0)

    hostpath = SPLUNKD_HOST_PATH + ':' + splunkd_port + ''
    print('Your Splunk instance is: %s' % hostpath)

    retries = 3
    session_key = None
    while not session_key and retries:
        username = SPLUNK_USER
        password = getpass.getpass(prompt='Enter password for %s: ' % username)

        print('Trying to obtain a Splunk session key...')
        try:
            session_key = auth.getSessionKey(username, password, hostpath)
        except Exception as e:
            retries -= 1
            print('Encountered an error when logging in - ' + str(e))
            print('Try again. %d retries left.' % retries)

    if not retries and not session_key:
        print('You have reached the maximum number of retries. Run the script again.')
        sys.exit(0)
    print('Splunk session key successfully obtained\n')
    print('Perform precheck...\n')
    status = ServiceTemplateUtils(session_key, 'nobody').service_template_sync_job_in_progress_or_sync_now()
    if status.get('status', False):
        print('One or more service templates are currently syncing. Please wait for them to complete.\n')
        sys.exit(0)
    backup_restore_interface = ItsiBackupRestore(session_key, 'nobody')
    if backup_restore_interface.is_any_backup_restore_job_in_progress('owner'):
        print('A backup or restore operation is in progress. Please wait for the operation to complete.\n')
        sys.exit(0)

    print('Precheck completed.\n')

    option = input('Enter Y to disable ITSI and N to enable ITSI: (Y/N)? ')
    if option.strip().lower() == 'y':
        action = 'disable'
    else:
        action = 'enable'

    if action == 'disable':
        delete_option = input('Do you want to disable all modular inputs? (Y/N) ')
        if delete_option.strip().lower() == 'y':
            handle_mi = True
        delete_option = input('Do you want to disable all saved searches? (Y/N) ')
        if delete_option.strip().lower() == 'y':
            handle_ss = True
    elif action == 'enable':
        enable_option = input('Do you want to enable all modular inputs? (Y/N) ')
        if enable_option.strip().lower() == 'y':
            handle_mi = True
        enable_option = input('Do you want to enable all saved searches? (Y/N) ')
        if enable_option.strip().lower() == 'y':
            handle_ss = True

    snapshot_search_cache = defaultdict()
    snapshot_mod_cache = defaultdict()

    params = {
        'output_mode': 'json'
    }
    # Get a list of all the mod inputs
    try:
        response, content = rest.simpleRequest(
            '/servicesNS/nobody/SA-ITOA/data/inputs/',
            sessionKey=session_key,
            getargs=params,
            raiseAllErrors=False
        )
    except Exception as e:
        logger.exception(e)

    new_content = json.loads(content)
    entry_list = new_content.get('entry')

    # Get all the KPI searches
    searches = SavedSearch.get_all_searches(session_key, 'itsi', 'nobody')

    print('\n##############################################################################')
    print('A total of {0} modular inputs and {1} saved searches were found on the system.'.format(len(entry_list),
                                                                                                  len(searches)))
    print('################################################################################\n')
    confirm = input('Please confirm before proceeding (Y/N)? ')
    if confirm.strip().lower() != 'y':
        print('Abort........')
        sys.exit(0)

    # Get the content from the itsi_configuration_snapshot collection first
    # ITSI is already enabled if this collection is empty.
    snapshot_uri = '/servicesNS/nobody/SA-ITOA/storage/collections/data/itsi_configuration_snapshot'
    try:
        response, content = rest.simpleRequest(
            snapshot_uri,
            sessionKey=session_key,
            raiseAllErrors=False,
            getargs=params
        )
    except Exception as e:
        logger.exception(e)

    try:
        for item in json.loads(content):
            if item.get('object_type') == 'mod_input':
                snapshot_mod_cache[item.get('name')] = item.get('disabled')
            else:
                snapshot_search_cache[item.get('name')] = item.get('disabled')
    except Exception:
        print('Unable to create snapshot cache, maybe the KVStore is not available, please try it again')
        sys.exit(1)

    if action == 'disable':
        print('Disable ITSI UI\n')
        toggle_ui(False)
    elif action == 'enable':
        if len(snapshot_mod_cache) == 0 and len(snapshot_search_cache) == 0:
            print('All knowledge objects are already in their current state. There is no need to enable them again.')
            sys.exit(0)
        print('Enable ITSI UI\n')
        toggle_ui(True)

    if handle_ss:
        retry = []
        # managing all the savedsearches
        if action == 'disable':
            if len(snapshot_search_cache) > 0:
                # already disabled
                print('ITSI disable is already performed!\n')
                sys.exit(0)
        for search in searches:
            if action == 'disable':
                disabled = False
                if search.get('disabled').strip() == '1':
                    disabled = True
                data = {'name': search.name,
                        'disabled': disabled,
                        'object_type': 'saved_search'}
                rsp, content = rest.simpleRequest(snapshot_uri,
                                                  sessionKey=session_key,
                                                  raiseAllErrors=False,
                                                  jsonargs=json.dumps(data),
                                                  method='POST')
                # then disabled all the searches
                if search.get('disabled').strip() == '1':
                    print('Search: {0} is already disabled'.format(search.name))
                    continue
                search_param = {
                    'disabled': '1'
                }
                try:
                    is_update = SavedSearch.update_search(session_key,
                                                          search.name,
                                                          **search_param)
                    print('Disable search: {0}'.format(search.name))
                    count_updated_ss += 1
                except Exception:
                    print('Error while disabling search = {0}'.format(search.name))
            elif action == 'enable':
                # enable the search
                if not snapshot_search_cache.get(search.name, False):
                    search_param = {
                        'disabled': '0'
                    }
                    try:
                        is_update = SavedSearch.update_search(session_key,
                                                              search.name,
                                                              **search_param)
                        print('Enable search: {0}'.format(search.name))
                        if is_update:
                            count_updated_ss += 1
                    except Exception:
                        print('Error while enabling search = {0}'.format(search.name))
                        retry.append(search.name)
        # this could only happen in enable case
        if len(retry) > 0:
            for search in searches:
                if search.name in retry:
                    # enable the search
                    if not snapshot_search_cache.get(search.name, False):
                        search_param = {
                            'disabled': '0'
                        }
                        try:
                            is_update = SavedSearch.update_search(session_key,
                                                                  search.name,
                                                                  **search_param)
                            print('Enable search: {0}'.format(search.name))
                            if is_update:
                                count_updated_ss += 1
                        except Exception:
                            print('Retry enabling failed for search = {0}'.format(search.name))

    if handle_mi:
        # managing all the mod inputs
        if action == 'disable':
            if len(snapshot_mod_cache) > 0:
                # already disabled
                print('ITSI disable is already performed!\n')
                sys.exit(0)
        for entry in entry_list:
            name = entry.get('name')
            if name in block_list:
                continue
            response, content = rest.simpleRequest(
                '/servicesNS/nobody/SA-ITOA/data/inputs/' + name,
                sessionKey=session_key,
                getargs=params,
                raiseAllErrors=False
            )
            parsed_content = json.loads(content)
            modinput_list = parsed_content.get('entry')
            for modinput in modinput_list:
                modinput_name = modinput.get('name')
                key_name = name + '___' + modinput_name
                if action == 'disable':
                    # populate the snapshot before disable
                    disabled = modinput.get('content', {}).get('disabled')
                    data = {'name': key_name,
                            'disabled': disabled,
                            'object_type': 'mod_input'}
                    rsp, content = rest.simpleRequest(snapshot_uri,
                                                      sessionKey=session_key,
                                                      raiseAllErrors=False,
                                                      jsonargs=json.dumps(data),
                                                      method='POST')
                    if not disabled:
                        status = ITOAInterfaceUtils.control_modular_input(session_key,
                                                                          'SA-ITOA',
                                                                          'nobody',
                                                                          name,
                                                                          modinput_name,
                                                                          action)
                        if status:
                            print('Modular input {0} disabled successfully.'.format(key_name))
                            count_updated_mi += 1
                        else:
                            print('Failed to disable modular input {0}.'.format(key_name))
                    else:
                        print('Modular input {0} is already disabled.'.format(key_name))
                elif action == 'enable':
                    if not snapshot_mod_cache.get(key_name, False):
                        status = ITOAInterfaceUtils.control_modular_input(session_key,
                                                                          'SA-ITOA',
                                                                          'nobody',
                                                                          name,
                                                                          modinput_name,
                                                                          action)
                        if status:
                            print('Modular input {0} enabled successfully'.format(key_name))
                            count_updated_mi += 1
                        else:
                            print('Failed to enable modular input {0}'.format(key_name))

    print('\n########################################################################')
    print('A total of {0} modular inputs and {1} saved searches have been updated.'.format(count_updated_mi,
                                                                                           count_updated_ss))
    print('########################################################################\n')

    # If everything is enabled, clear the cache.
    if action == 'enable':
        filter_data = {}
        get_args = {}
        if handle_mi and handle_ss:
            pass
        elif handle_mi:
            filter_data['object_type'] = 'mod_input'
        elif handle_ss:
            filter_data['object_type'] = 'saved_search'
        get_args['query'] = json.dumps(filter_data)
        try:
            response, content = rest.simpleRequest(
                snapshot_uri,
                sessionKey=session_key,
                getargs=get_args,
                raiseAllErrors=False,
                method='DELETE')
        except Exception as e:
            logger.exception(e)

    count_updated_mi = 0
    count_updated_ss = 0
