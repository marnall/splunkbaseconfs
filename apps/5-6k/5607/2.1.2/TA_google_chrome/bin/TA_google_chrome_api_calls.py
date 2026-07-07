from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
import extensions_query
import json
import csv
import time
import shutil
from datetime import datetime
from pathlib import Path

ADDON_NAME = "TA_google_chrome"


def call_retry_decorator(fn):
    # Decorator to retry unsuccessful call up to 5 times

    def wrapper(*args, **kwargs):
        for i in range(5):
            print('Making request to server ...')
            response = fn(*args, *kwargs)
            if isinstance(response, bytes):
                response = response.decode('utf-8')

            if str(response.status_code)[0] == '2':
                return response
            else:
                print('Response error, retrying...')
                time.sleep(3)
        return response

    return wrapper


url_dictionary = {'user_details_url': 'https://admin.googleapis.com/admin/directory/v1/users/{account}',
                  'move_chrome_browser': 'https://www.googleapis.com/admin/directory/v1.1beta1/customer/{customerID}/devices/chromebrowsers/moveChromeBrowsersToOu',
                  'get_orgunits': 'https://admin.googleapis.com/admin/directory/v1/customer/{customerID}/orgunits?type=all_including_parent',
                  'get_policy_schema': 'https://chromepolicy.googleapis.com/v1/customers/{customerID}/policySchemas',
                  'policy_batch_modify_in_orgunit': 'https://chromepolicy.googleapis.com/v1/customers/{customerID}/policies/orgunits:batchModify',
                  'move_chrome_device': 'https://admin.googleapis.com/admin/directory/v1/customer/{customerID}/devices/chromeos/moveDevicesToOu?orgUnitPath={oupath}',
                  'extension_permission': 'https://chromemanagement.googleapis.com/v1/customers/{customerID}/apps/chrome/{extensionID}{version}',
                  'issue_command_device': 'https://admin.googleapis.com/admin/directory/v1/customer/{customerID}/devices/chromeos/{deviceId}:issueCommand',
                  'disable_device': 'https://admin.googleapis.com/admin/directory/v1/customer/{customerID}/devices/chromeos/{deviceId}/action'
                  }

scope_dictionary = {'admin_directory_user_r/w': 'https://www.googleapis.com/auth/admin.directory.user',
                    'admin_directory_chrome_browsers_r/w': 'https://www.googleapis.com/auth/admin.directory.device.chromebrowsers',
                    'admin_directory_chrome_device_r/w': 'https://www.googleapis.com/auth/admin.directory.device.chromeos',
                    'admin_directory_orgunit_r': 'https://www.googleapis.com/auth/admin.directory.orgunit.readonly',
                    'chrome_management_policy_r/w': 'https://www.googleapis.com/auth/chrome.management.policy',
                    'chrome_management_app_details_r': 'https://www.googleapis.com/auth/chrome.management.appdetails.readonly',
                    }


class GoogleWorkflowCalls:

    def __init__(self, sa_key, customerID, admin_email=''):
        '''
        Class to make API requests to Admin workspace (either directory or CBCM)

        :param sa_key: service account private key from json <dict>
        :param customerID: customer ID visible in admin consle account settings <string>
        :param admin_email: optional, depends on call - If used, this email will be visible in admin logs <string>
        '''
        self.__SERVICE_ACCOUNT_KEY = sa_key
        self.__SCOPES = []
        self.response = ''
        self.admin_email = admin_email
        self.customerID = customerID

    def __create_scopes(self, scope):
        '''
        Scope setter, private method

        :param scope: list of scopes (urls) [<string>]
        :return: None
        '''
        self.__SCOPES = scope

    def __make_credentials(self, admin_email=''):
        '''
        Create credential for API call, privet method

        :param admin_email: optional, based on call type. <string>
        :return: service_account.Credentials object
        '''
        # Creates credentials variable
        return service_account.Credentials.from_service_account_info(
            self.__SERVICE_ACCOUNT_KEY,
            scopes=self.__SCOPES,
            subject=admin_email
        )

    def __write_lookup(self, data, file):
        '''
        Writes list of dict into a csv file. All dict needs to have the same keys.
        :param data: list of dictionaries <dict>
        :param file: resulting file save location <pathlib.Path object>
        :return: None
        '''
        with open(file, 'w') as lookup_file:
            writer = csv.writer(lookup_file)
            writer.writerow(data[0].keys())
            for single_dict in data:
                writer.writerow(single_dict.values())

    @call_retry_decorator
    def __make_get_call(self, service_credentials, base_request_url, request_parameters):
        '''
        GET call

        :param service_credentials:  service_account.Credentials object
        :param base_request_url: url to call, <string>
        :param request_parameters: optional, not used <string>
        :return: request.response object
        '''
        session = AuthorizedSession(service_credentials)
        response = session.request(
            'GET',
            base_request_url
        )

        return response

    @call_retry_decorator
    def __make_post_call(self, service_credentials, base_request_url, request_parameters, payload):
        '''
        POST call

        :param service_credentials: service_account.Credentials object
        :param base_request_url: url to call, <string>
        :param request_parameters: optional, not used <string>
        :param payload: request body parsed to json <string>
        :return: request.response object
        '''

        session = AuthorizedSession(service_credentials)
        response = session.request(
            'POST',
            base_request_url,
            data=payload
        )

        return response

    @call_retry_decorator
    def __make_put_call(self, service_credentials, base_request_url, request_parameters, payload):
        '''
        PUT call

        :param service_credentials: service_account.Credentials object
        :param base_request_url: url to call, <string>
        :param request_parameters: optional, not used <string>
        :param payload: request body parsed to json <string>
        :return: request.response object
        '''

        session = AuthorizedSession(service_credentials)
        response = session.request(
            'PUT',
            base_request_url,
            data=payload
        )

        return response

    def get_account_info(self, account_address):
        '''
        Retrieves account information from Admin Console. might contain sensitive data

        :param account_address: email address of queried account <string>
        :return: None
        '''
        self.__create_scopes([scope_dictionary['admin_directory_user_r/w']])

        base_request_url = url_dictionary['user_details_url'].format(account=account_address)

        service_credentials = self.__make_credentials()

        self.response = self.__make_get_call(service_credentials, base_request_url, '')

    def csv_to_dict(self, file):
        '''
        Converts csv data into a list of dict objects

        :param file: contents of a csv file <file_object>
        :return: list of dictionaries <dict>
        '''

        file_marker = csv.DictReader(file)
        file_data = []
        for row in file_marker:
            file_data.append(row)
        return file_data

    def get_extensions_list(self, output_path, dev_prof_ext_path):
        '''
        Creates a csv file with extension details utilising extensions query script (aka CBCM takeout script)
        To minimalize interference with original code, this method calls the script externally, while
        any additional results modification are done outside the query script.
        Method copies last file (if exists) to keep as a reference while adding timestamp of extension first noted occurance.

        :param output_path: resulting file save location <pathlib.Path object>
        :return: None
        '''

        def append_timestamp_and_source_flag():
            '''
            Compares new extensions list with the previous one (if exists) and adds timestamp for each
            new occurrence of an extension

            :return: list of dictionaries <dict>
            '''

            def append_timestamp():
                for row in new_file_data:
                    # adds timestamp for data from admin_console

                    new_file_exists_check_set.add(row['id'])

                    temp_id = row['id'].split(' @ ')
                    row['id'] = temp_id[0]
                    row['version'] = temp_id[1]
                    row['source'] = 'admin_console'

                    key = (row['id'], row['version'])

                    if key in old_timestamp_dict:
                        row['first_occurrence'] = old_timestamp_dict[key]
                    else:
                        row['first_occurrence'] = timestamp

                    data_write_list.append(row)

            def append_api_generated_permissions():
                for row in old_file_data:
                    if row['source'] == 'permission_api':
                        key = row['id'] + ' @ ' + row['version']
                        if key not in new_file_exists_check_set:
                            data_write_list.append(row)

            with open(output_path, 'r') as new_file:
                # compares new and old lookup to find new occurrences of extensions and add timestamp to them

                new_file_data = csv.DictReader(new_file)
                data_write_list = []
                now = datetime.now()
                timestamp = int(now.timestamp())

                if old_file_exists:
                    old_file = open(old_path, 'r')
                    old_file_data = self.csv_to_dict(old_file)

                    # creates dictionary for quick check of timestamp
                    old_timestamp_dict = {(row['id'], row['version']): row['first_occurrence'] for row in old_file_data}
                else:
                    old_timestamp_dict = {}

                new_file_exists_check_set = set()
                append_timestamp()

            if old_file_exists:
                append_api_generated_permissions()
                old_file.close()

            return data_write_list

        class Arguments:
            def __init__(self, admin_email, service_account_key, customerID, output_path, dev_prof_ext_path):
                '''
                internal class used to run extensions query with required arguments
                '''
                self.admin_email = admin_email
                self.service_account_key = service_account_key
                self.customerID = customerID
                self.extension_list_csv = output_path
                self.device_profile_extension_list_csv = dev_prof_ext_path

        old_path = output_path.with_suffix(output_path.suffix + '_old')
        old_file_exists = False

        if Path.exists(output_path):
            # copies old file is exists
            shutil.copyfile(output_path, old_path)
            old_file_exists = True

        args = Arguments(self.admin_email, self.__SERVICE_ACCOUNT_KEY, self.customerID, output_path, dev_prof_ext_path)

        extensions_query.main(args)

        extension_lookup_data = append_timestamp_and_source_flag()

        self.__write_lookup(extension_lookup_data, output_path)

    def get_extension_permission_action(self, extensionId, version, installEvent):
        # orchestrate the get extension permissions alert action
        # API call, and updating the lookup
        self.get_extension_permission(extensionId, version)
        # update the lookup table
        responseData = json.loads(self.response.content)
        self.update_extension_list(responseData, installEvent)

    def get_extension_permission(self, extensionid, version=''):

        if version != '':
            version = '@' + version

        self.__create_scopes([scope_dictionary['chrome_management_app_details_r']])

        base_request_url = url_dictionary['extension_permission'].format(
            customerID=self.customerID,
            extensionID=extensionid,
            version=version)

        service_credentials = self.__make_credentials()

        # store the response
        self.response = self.__make_get_call(service_credentials, base_request_url, '')

    def update_extension_list(self, response, installEvent, extensionListPath='package/lookups/gc_extension_list.csv'):
        '''
        Updates or Creates a row in the gc_extension_list.csv lookup file
            - if the version already exists then updates devices, installed count columns
            - if not exists then writes a new row
        :param response: the response of the get_extension_permission api call
        :return: None
        '''
        # parse response fields
        appId = response['appId']
        latestVersion = response['revisionId']

        # open file and parse as list of dict
        parent_path = Path(__file__).parents[2]
        full_extension_list_path = parent_path.joinpath(extensionListPath)
        # Ensure that the file exists
        if not Path.exists(full_extension_list_path):
            print('The default lookup gc_extension_list.csv does not exist. \
                  The Google Chrome Technology Add-on must have a modular input of type extension_lookup_query configured first.\
                  If this file was deleted from your instance this app will not work properly.')
            return  # early exit
        file = open(full_extension_list_path, 'r')
        extension_list = self.csv_to_dict(file)
        file.close()
        # ensure that file is not empty
        if not extension_list:
            print('The default lookup gc_extension_list.csv is empty. \
                  The Google Chrome Technology Add-on must have a modular input of type extension_lookup_query configured first.\
                  If this file was deleted from your instance this app will not work properly.')
            return  # early exit
        # search for id, version in the current list
        exists = False  # track whether to update or write new value
        writeLookup = False  # track whether to write to lookup
        for extension in extension_list:
            # check if ID and version match
            if extension['id'] == appId and extension['version'] == latestVersion:
                exists = True  # BINGO!
                # check if device not in list
                if installEvent['device_id'] not in extension['installed'].split(','):
                    # update the current line, add device to installed, inc. num installed
                    extension['installed'] += ',' + installEvent['device_id']
                    extension['num_installed'] = str(int(extension['num_installed']) + 1)
                    writeLookup = True
                break
        if not exists:
            writeLookup = True
            # parse permissions objects
            permissions = list(map(lambda permissionObject: permissionObject['type'], response['chromeAppInfo']['permissions']))
            # define data for new line, order of fields matters!
            # id,name,num_permissions,num_installed,num_disabled,num_forced,permissions,installed,disabled,forced,version,source,first_occurrence
            first_occurrence = installEvent['time'].split('.')[0] if installEvent['time'] is not None else int(datetime.now().timestamp())
            new_extension_data = {
                'id': appId,
                'name': installEvent['extension_name'],
                'num_permissions': len(permissions),
                'num_installed': '1',
                'num_disabled': '0',
                'num_forced': '0',
                'permissions': ', '.join(permissions),
                'installed': installEvent['device_id'],
                'disabled': '',
                'forced': '',
                'version': latestVersion,
                'source': 'permission_api',
                'first_occurrence': first_occurrence
            }
            extension_list.append(new_extension_data)

        # write new data
        if writeLookup:
            self.__write_lookup(extension_list, full_extension_list_path)

    def __move_ou_action(self, base_request_url, scope, payload):
        '''
        API call step of moving device between OU's.
        Retries 5 times if successful status is not present in response

        :param base_request_url: url to call, <string>
        :param scope: list of scopes (urls) [<string>]
        :param payload: request body parsed to json <string>
        :return: None
        '''

        self.__create_scopes([scope])

        service_credentials = self.__make_credentials(self.admin_email)

        print('Making post call')

        self.response = self.__make_post_call(service_credentials, base_request_url, '', payload)

    def move_browser_to_OU(self, oupath, deviceID):
        '''
        Call results in changing a managed browser organisation unit in Admin Console

        :param oupath: path of targeted OU <string>
        :param deviceID: device ID used in API calls (directory_device_id) <string>
        :return: None
        '''

        scope = scope_dictionary['admin_directory_chrome_browsers_r/w']

        base_request_url = url_dictionary['move_chrome_browser'].format(customerID=self.customerID)
        payload = json.dumps({'org_unit_path': oupath,
                              'resource_ids': [deviceID]})
        print('Starting request')
        self.__move_ou_action(base_request_url, scope, payload)

    def move_user_to_OU(self, oupath, account_address):
        '''
        Call results in changing users organisation unit in Admin Console
        Retries 5 times if successful status is not present in response

        :param oupath: path of targeted OU <string>
        :param account_address: primary email address of managed account <string>
        :return: None
        '''

        self.__create_scopes([scope_dictionary['admin_directory_user_r/w']])

        base_request_url = url_dictionary['user_details_url'].format(account=account_address)

        service_credentials = self.__make_credentials(admin_email=self.admin_email)

        payload = json.dumps({"orgUnitPath": oupath})

        print('Starting request')
        print('Making PUT call ...')

        self.response = self.__make_put_call(service_credentials, base_request_url, '', payload)

    def get_OU_list(self, output_path):
        '''
        Gets all of existing organisation units from selected Admin console workspace
        Adds a root OU (topmost one) but without its name.
        Retries 5 times if successful status is not present in response

        :param output_path: resulting file save location <pathlib.Path object>
        :return: None
        '''

        org_units_list = []
        data_chunk = {'organizationUnits': []}
        try:

            self.__create_scopes([scope_dictionary['admin_directory_orgunit_r']])

            base_request_url = url_dictionary['get_orgunits'].format(customerID=self.customerID)

            service_credentials = self.__make_credentials('')

            retry_count = 0

            while retry_count < 2:
                self.response = self.__make_get_call(service_credentials, base_request_url, '')

                if self.response.status_code in [200, 201]:

                    data_chunk = json.loads(self.response._content.decode('utf-8'))
                    if 'organizationUnits' not in data_chunk:
                        print('organizationUnits missing in response, retrying...')
                        retry_count += 1
                    else:
                        break
                else:
                    print('Response error - Status:{status}, content : "{content}"'.format(status=self.response.status_code, content=self.response._content))
                    break

            if retry_count < 2:
                org_units_list.extend(data_chunk['organizationUnits'])

        finally:

            print('Request returned {} results, sorting data ...'.format(len(org_units_list)))

            if len(org_units_list) > 0:

                sorted_org_unit_list = sorted(org_units_list, key=lambda d: d['orgUnitPath'])

                # adding missing keys to root value
                sorted_org_unit_list[0]['parentOrgUnitPath'] = ''
                sorted_org_unit_list[0]['parentOrgUnitId'] = ''

                self.__write_lookup(sorted_org_unit_list, output_path)
                print("Results written to '{}'".format(output_path))

            else:
                print("Empty list returned. No changes done")

    def get_policy(self):
        '''
        Gets the policy schema.

        :return: None
        '''

        self.__create_scopes([scope_dictionary['chrome_management_policy_r/w']])
        service_credentials = self.__make_credentials()

        base_request_url = url_dictionary['get_policy_schema'].format(customerID=self.customerID)

        policy_schema = []
        request_parameters = ''

        while True:
            print('Making request to server ...')

            request_url = base_request_url + request_parameters

            self.response = self.__make_get_call(service_credentials, request_url, '')

            if isinstance(self.response, bytes):
                self.response = self.response.decode('utf-8')
            data_chunk = json.loads(self.response._content.decode('utf-8'))

            policy_schema.extend(data_chunk['policySchemas'])

            if 'nextPageToken' not in data_chunk or not data_chunk['nextPageToken']:
                break

            request_parameters = '?pageToken={}'.format(data_chunk['nextPageToken'])

        with open('policy.json', 'w') as f:
            json.dump(policy_schema, f)

    def block_extension(self, org_id, app_id):
        '''
        Blocks extension in selected OU (and, by default, in all of its children)
        Retries 5 times if successful status is not present in response

        :param org_id: id of an Organisation Unit <string>
        :param app_id: extensions google web store id <string>
        :return: None
        '''

        self.__create_scopes([scope_dictionary['chrome_management_policy_r/w']])
        service_credentials = self.__make_credentials()

        base_request_url = url_dictionary['policy_batch_modify_in_orgunit'].format(customerID=self.customerID)

        # request body structure reflects the docs
        # https://developers.google.com/chrome/policy/reference/rest/v1/customers.policies.orgunits/batchModify#ModifyOrgUnitPolicyRequest

        policy_target_key = {
            "targetResource": "orgunits/{org_id}".format(org_id=org_id),
            "additionalTargetKeys": {
                "app_id": "chrome:{app_id}".format(app_id=app_id)
            }
        }

        policy_value = {
            "policySchema": "chrome.users.apps.InstallType",
            "value": {
                "appInstallType": "BLOCKED"
            }
        }

        policy_request = {
            "policyTargetKey": policy_target_key,
            "policyValue": policy_value,
            "updateMask": "appInstallType"
        }

        request_body = {"requests": [policy_request]}

        payload = json.dumps(request_body)

        self.response = self.__make_post_call(service_credentials, base_request_url, '', payload)

    # Chrome OS specific calls

    def __post_action(self, base_request_url, scope, payload):
        '''
        API call step of moving device between OU's.
        Retries 5 times if successful status is not present in response

        :param base_request_url: url to call, <string>
        :param scope: list of scopes (urls) [<string>]
        :param payload: request body parsed to json <string>
        :return: None
        '''

        self.__create_scopes([scope])
        service_credentials = self.__make_credentials(self.admin_email)
        print('Making post call')
        self.response = self.__make_post_call(service_credentials, base_request_url, '', payload)

    def move_os_device_to_OU(self, oupath, deviceID):
        '''
        Call results in changing a managed chrome OS device organisation unit in Admin Console

        :param oupath: path of targeted OU <string>
        :param deviceID: device ID used in API calls (directory_device_id) <string>
        :return: None
        '''

        scope = scope_dictionary['admin_directory_chrome_device_r/w']

        base_request_url = url_dictionary['move_chrome_device'].format(customerID=self.customerID, oupath=oupath)
        payload = json.dumps({"deviceIds": [deviceID]})

        self.__move_ou_action(base_request_url, scope, payload)

    def suspend_user(self, account_address):

        self.__create_scopes([scope_dictionary['admin_directory_user_r/w']])
        base_request_url = url_dictionary['user_details_url'].format(account=account_address)
        service_credentials = self.__make_credentials(admin_email=self.admin_email)
        payload = json.dumps({"suspended": True})
        print('Starting request')
        print('Making PUT call ...')
        self.response = self.__make_put_call(service_credentials, base_request_url, '', payload)

    def reboot_device(self, deviceId):

        scope = scope_dictionary['admin_directory_chrome_device_r/w']
        base_request_url = url_dictionary['issue_command_device'].format(customerID=self.customerID, deviceId=deviceId)
        payload = json.dumps({"commandType": "REBOOT"})
        print('Starting request')
        print('Making POST call ...')
        self.__post_action(base_request_url, scope, payload)

    def wipe_user(self, deviceId):

        scope = scope_dictionary['admin_directory_chrome_device_r/w']
        base_request_url = url_dictionary['issue_command_device'].format(customerID=self.customerID, deviceId=deviceId)
        payload = json.dumps({"commandType": "WIPE_USERS"})
        self.__post_action(base_request_url, scope, payload)

    def disable_device(self, deviceId):

        scope = scope_dictionary['admin_directory_chrome_device_r/w']
        base_request_url = url_dictionary['disable_device'].format(customerID=self.customerID, deviceId=deviceId)
        payload = json.dumps({"action": "disable"})
        self.__post_action(base_request_url, scope, payload)

    def wipe_device(self, deviceId):

        scope = scope_dictionary['admin_directory_chrome_device_r/w']
        base_request_url = url_dictionary['issue_command_device'].format(customerID=self.customerID, deviceId=deviceId)
        payload = json.dumps({"commandType": "REMOTE_POWERWASH"})
        self.__post_action(base_request_url, scope, payload)
