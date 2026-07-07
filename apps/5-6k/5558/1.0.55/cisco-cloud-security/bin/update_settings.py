# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from validator import json_sanitizer, cummulative_validator, date_validator, get_host
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from token_service import TokenService
from global_org_client import GlobalOrgClient

dashboard_settings = None
cloudlock_settings = None
selected_destination_lists = None
refresh_rate = None
s3_indexes = None


class UpdateSettings(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        self.global_org_client = None

    def validator(self, arg, method, name):
        if method == 'cu':
            if not cummulative_validator(arg):
                raise Exception('KV store data [{0}] validation failed'.format(name))
            return arg
        elif method == 'da':
            if not date_validator(arg):
                raise Exception('KV store date [{0}] validation failed'.format(name))
            return arg
        return arg

    def handle(self, in_string):
        try:
            data = None
            dashboard_data = None
            investigate_data = None
            cloudlock_data = None
            selected_destination_lists_data = None
            refresh_rate_data = None
            s3_indexes_data = None
            oauth_credentials = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            method = params['method']
            header = params.get('headers', [])
            host = get_host(header)
            self.global_org_client = GlobalOrgClient(session_token)

            global dashboard_settings
            global cloudlock_settings
            global selected_destination_lists
            global refresh_rate
            global s3_indexes

            if not dashboard_settings:
                dashboard_settings = KVStoreService('dashboard_settings', session_token)
            if not cloudlock_settings:
                cloudlock_settings = KVStoreService('cloudlock_settings', session_token)
            if not selected_destination_lists:
                selected_destination_lists = KVStoreService('selected_destination_lists', session_token)
            if not refresh_rate:
                refresh_rate = KVStoreService('refresh_rate', session_token)
            if not s3_indexes:
                s3_indexes = KVStoreService('s3_indexes', session_token)

            if method == 'post':
                data = json.loads(params['payload'])['data']
                if 'Dashboard' in list(data.keys()):
                    dashboard_data = data['Dashboard']
                if 'cloudlock' in list(data.keys()):
                    cloudlock_data = data['cloudlock']
                if 'selected_destination_lists' in list(data.keys()):
                    selected_destination_lists_data = data['selected_destination_lists']
                if 'refresh_rate' in list(data.keys()):
                    refresh_rate_data = data['refresh_rate']
                if 's3_indexes' in list(data.keys()):
                    s3_indexes_data = data['s3_indexes']

                if dashboard_data:
                    is_collection_cleared = False
                    search_interval = dashboard_data['search_interval']
                    interval_pre_value = json.loads(dashboard_settings.query_items('dashboard_settings', session_token))
                    if len(interval_pre_value) != 0:
                        interval_prev_record = interval_pre_value[-1]
                        dashboard_settings_keys = ['search_interval']
                        for k in dashboard_settings_keys:
                            if k not in interval_prev_record:
                                dashboard_settings.delete_all_items('dashboard_settings', session_token)
                                is_collection_cleared = True
                                break
                        if is_collection_cleared is False:
                            key = interval_prev_record["_key"]
                            dashboard_settings.update_item_by_key('dashboard_settings', key, session_token,
                                                                  {'search_interval': search_interval})
                    else:
                        dashboard_settings.insert_record('dashboard_settings', session_token,
                                                         {'search_interval': search_interval})
                if selected_destination_lists_data is not None:
                    if "orgId" not in data:
                        raise Exception('Organization ID is required in selected destination lists data')
                    self._verify_org_id_match(data["orgId"])
                    if len(selected_destination_lists_data) != 0:
                        selected_destination_lists.delete_items_by_condition(
                            "selected_destination_lists",
                            session_token,
                            {"orgId": data["orgId"]},
                        )
                        for ele in selected_destination_lists_data:
                            sel_dest_insr = selected_destination_lists.insert_record(
                                "selected_destination_lists",
                                session_token,
                                {
                                    "dest_list_id": self.validator(
                                        ele["dest_list_id"], "cu", "dest_list_id"
                                    ),
                                    "dest_list_name": self.validator(
                                        ele["dest_list_name"], "cu", "dest_list_name"
                                    ),
                                    "role": self.validator(ele["role"], "cu", "role"),
                                    "orgId": self.validator(data["orgId"], "cu", "orgId"),
                                },
                            )
                    else:
                        selected_destination_lists.delete_items_by_condition(
                            "selected_destination_lists",
                            session_token,
                            {"orgId": data["orgId"]},
                        )
                if cloudlock_data:
                    cloudlock_settings_data = json.loads(
                        cloudlock_settings.query_items('cloudlock_settings', session_token))
                    is_collection_cleared = False
                    if len(cloudlock_settings_data) != 0:
                        cloudlock_prev_record = cloudlock_settings_data[-1]
                        cloudlock_settings_keys = ['userName', 'createdDate', 'configName', 'url', 'token',
                                                   'showIncidentDetails', 'showUEBA', 'status', 'cloudlock_start_date']
                        for k in cloudlock_settings_keys:
                            if k not in cloudlock_prev_record:
                                cloudlock_settings.delete_all_items('cloudlock_settings', session_token)
                                is_collection_cleared = True
                                break
                        if is_collection_cleared is False:
                            key = cloudlock_prev_record["_key"]
                            cloudlock_settings.update_item_by_key('cloudlock_settings', key, session_token,
                                                                  {'userName': cloudlock_prev_record['userName'],
                                                                   'createdDate': cloudlock_prev_record['createdDate'],
                                                                   'configName': cloudlock_prev_record['configName'],
                                                                   'url': cloudlock_prev_record['url'],
                                                                   'token': '',
                                                                   'showIncidentDetails': cloudlock_prev_record['showIncidentDetails'],
                                                                   'showUEBA': cloudlock_prev_record['showUEBA'],
                                                                   'status': 'inactive',
                                                                   'cloudlock_start_date': cloudlock_prev_record['cloudlock_start_date']})
                            # 'index': cloudlock_prev_record['index']})

                    if cloudlock_data['configName'] != '' and cloudlock_data['url'] != '' and cloudlock_data[
                        'token'] != '':
                        token = self.validator(cloudlock_data['token'], 'cu', 'token')
                        TokenService.set_token(session_token, token, 'cloudlock_settings', host=host)
                        Logger().info("cloudlock_start_date to be saved in kvstore is " + cloudlock_data['cloudlock_start_date'])
                        cld_insr = cloudlock_settings.insert_record('cloudlock_settings', session_token,
                                                                    {'userName': self.validator(
                                                                        cloudlock_data['userName'], 'cu',
                                                                        'userName'),
                                                                     'createdDate': self.validator(
                                                                         cloudlock_data['createdDate'], 'da',
                                                                         'createdDate'),
                                                                     'configName': self.validator(
                                                                         cloudlock_data['configName'], 'cu',
                                                                         'configName'),
                                                                     'url': self.validator(
                                                                         cloudlock_data['url'], 'cu', 'url'),
                                                                     'token': '',
                                                                     'showIncidentDetails': str(
                                                                         cloudlock_data['showIncidentDetails']),
                                                                     'showUEBA': cloudlock_data['showUEBA'],
                                                                     'status': 'active',
                                                                     'cloudlock_start_date': self.validator(
                                                                         cloudlock_data['cloudlock_start_date'], 'da',
                                                                         'cloudlock_start_date')})
                        # 'index':self.validator(cloudlock_data['index'],'cu', 'index')})
                    else:
                        raise Exception('Enter All Cloudlock Credentials')
                if refresh_rate_data:
                    rfrsh_insr = refresh_rate.insert_record('refresh_rate', session_token,
                                                            {'refresh_rate': self.validator(refresh_rate_data,
                                                                                            'cu', 'refreshRate')})
                else:
                    rfrsh_data = json.loads(s3_indexes.query_items('refresh_rate', session_token))
                    if len(rfrsh_data) == 0:
                        rfrsh_insr = refresh_rate.insert_record('refresh_rate', session_token, {'refresh_rate': "0"})

                if s3_indexes_data:
                    if "orgId" not in data:
                        raise Exception('Organization ID is required in s3 indexes data')
                    self._verify_org_id_match(data["orgId"])
                    Logger().error("s3_indexes keys : {0}".format(s3_indexes_data.keys()))
                    dns_ind = s3_indexes_data.get('dns')
                    proxy_ind = s3_indexes_data.get('proxy')
                    firewall_ind = s3_indexes_data.get('firewall')
                    dlp_ind = s3_indexes_data.get('dlp')
                    ravpn_ind = s3_indexes_data.get('ravpn')
                    created_date = s3_indexes_data.get('createdDate')
                    s3_indexes_data_fetched = json.loads(s3_indexes.query_items('s3_indexes', session_token, {
                        "orgId": data["orgId"]
                    }))
                    is_collection_cleared = False
                    if len(s3_indexes_data_fetched) != 0:
                        s3_indexes_prev_record = s3_indexes_data_fetched[-1]
                        s3_indexes_keys = ['dns_index', 'proxy_index', 'firewall_index', 'dlp_index','ravpn_index', 'createdDate']
                        for k in s3_indexes_keys:
                            if k not in s3_indexes_prev_record:
                                s3_indexes.delete_items_by_condition('s3_indexes', session_token, {
                                    "orgId": data["orgId"]
                                })
                                is_collection_cleared = True
                                break
                        if is_collection_cleared is False:
                            key = s3_indexes_prev_record["_key"]
                            s3_indexes.update_item_by_key('s3_indexes', key, session_token,
                                                          {'dns_index': dns_ind,
                                                           'proxy_index': proxy_ind,
                                                           'firewall_index': firewall_ind,
                                                           'dlp_index': dlp_ind,
                                                           'ravpn_index': ravpn_ind,
                                                           'createdDate': created_date,
                                                           "orgId": data["orgId"]})
                    if len(s3_indexes_data_fetched) == 0 or is_collection_cleared is True:
                        s3_indexes.insert_record('s3_indexes', session_token,
                                                 {'dns_index': dns_ind,
                                                  'proxy_index': proxy_ind,
                                                  'firewall_index': firewall_ind,
                                                  'dlp_index': dlp_ind,
                                                  'ravpn_index': ravpn_ind,
                                                  'createdDate': created_date,
                                                  "orgId": data["orgId"]})
                return {'payload': 'Application settings saved successfully', 'status': 200}
        except Exception as e:
            Logger().error("API: update_settings, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
        
    
    def _verify_org_id_match(self, org_id):
        """
        Verify that the provided org_id matches the global organization ID.

        :param org_id: The organization ID to verify.
        :raises Exception: If there is a mismatch between the provided org_id and the global organization ID.
        """
        global_org_id = self.global_org_client.global_org
        if org_id != global_org_id:
            raise Exception('Organization ID mismatch error')