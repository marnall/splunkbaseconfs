# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import requests
import time
from validator import get_host
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from enums import DestinationListAPIEndpoints, InvestigateAPIS
from reporting_api_client import ReportingAPIClient
from token_service import TokenService
from exceptions import ReportingAPIClientException

oauth_settings = None
cloudlock_settings = None
investigate_health_check = None
cloudlock_health_check = None
destination_lists_health_check = None

class ValidateLicense(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            result_func = dict()
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            api_client = ReportingAPIClient(session_token)
            endpoint = params["rest_path"].split('/')[-1]
            new_call_flag = params["query"]['new_call_flag']
            header = params.get('headers', [])
            host = get_host(header)
            the_url = None
            the_token = None
            headers = None
            global oauth_settings
            if endpoint == 'investigate':
                if new_call_flag == 'True':
                    if not oauth_settings:
                        oauth_settings = KVStoreService('oauth_settings', session_token)
                        oauth_settings = json.loads(oauth_settings.query_items('oauth_settings', session_token, {
                            'status':'active',
                            'orgId': api_client.org_id
                        }))
                        if len(oauth_settings) == 0:
                            return {'payload': {'message': 'Oauth settings are empty'}, 'status': 200}   
                    path = InvestigateAPIS.TOP_MILLION.value
                    counter = 0
                    result_func[endpoint] = 'n'
                    res_bdy = api_client.send_request(path=path, method='get', headers=headers)
                    if res_bdy.status_code == 200:
                        result_func[endpoint] = 'y'
                    elif res_bdy.status_code == 429:
                        t = 1
                        while counter < 10:
                            if api_client.send_request(path=path, method='get', headers=headers).status_code == 200:
                                result_func[endpoint] = 'y'
                                break
                            counter += 1
                            time.sleep(t)
                            t = t+0.5
                    else:
                        while counter < 2:
                            if api_client.send_request(path=path, method='get', headers=headers).status_code == 200:
                                result_func[endpoint] = 'y'
                                break
                            counter += 1
                    return {'payload': result_func, 'status': 200}
                else:
                    global investigate_health_check
                    if not investigate_health_check:
                        investigate_health_check = KVStoreService('investigate_health_check', session_token)
                    investigate_health_check_data = json.loads(
                        investigate_health_check.query_items('investigate_health_check', session_token))
                    if investigate_health_check_data[-1]['investigateURLStatus'] == "200":
                        result_func[endpoint] = 'y'
                    else:
                        result_func[endpoint] = 'n'
            elif endpoint == 'cloudlock':
                if new_call_flag == 'True':
                    global cloudlock_settings
                    if not cloudlock_settings:
                        cloudlock_settings = KVStoreService('cloudlock_settings', session_token)
                    cloudlock_settings_data = json.loads(cloudlock_settings.query_items('cloudlock_settings',
                                                                                        session_token))
                    if len(cloudlock_settings_data) == 0:
                        return {'payload': {'message': 'cloudlock settings are empty'}, 'status': 200}

                    payload = TokenService.get_token(session_token, 'cloudlock_settings', host=host)
                    if payload['payload']:
                        the_token = payload['payload']['clear_token']
                    else:
                        return {'payload': {'message': 'cloudlock settings are empty'}, 'status': 200}
                    for obj in cloudlock_settings_data:
                        if obj['status'] == 'active':
                            the_url = obj['url'] + '/incidents?order=created_at&limit=1&count_total=false'
                            headers = {'Authorization': 'Bearer ' + the_token,
                                       'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
                            break
                    if not the_url and not the_token and not headers:
                        return {'payload': {'message': 'cloudlock Credentials not active'}, 'status': 200}
                else:
                    global cloudlock_health_check
                    if not cloudlock_health_check:
                        cloudlock_health_check = KVStoreService('cloudlock_health_check', session_token)
                    cloudlock_health_check_data = json.loads(
                        cloudlock_health_check.query_items('cloudlock_health_check', session_token))
                    if cloudlock_health_check_data[-1]['cloudlockURLStatus'] == "200":
                        result_func[endpoint] = 'y'
                    else:
                        result_func[endpoint] = 'n'
            elif endpoint == 'destination_lists':
                if new_call_flag == 'True':
                    if not oauth_settings:
                        oauth_settings = KVStoreService('oauth_settings', session_token)
                        oauth_settings = json.loads(oauth_settings.query_items('oauth_settings', session_token, {
                            'status':'active',
                            'orgId': api_client.org_id
                        }))
                        if len(oauth_settings) == 0:
                            return {'payload': {'message': 'Oauth settings are empty'}, 'status': 200}
                    api_client = ReportingAPIClient(session_token)
                    path = DestinationListAPIEndpoints.GET_DESTINATION_LISTS.value
                    counter = 0
                    result_func[endpoint] = 'n'
                    res_bdy = api_client.send_request(path=path, method='get', headers=headers)
                    if res_bdy.status_code == 200:
                        result_func[endpoint] = 'y'
                    elif res_bdy.status_code == 429:
                        t = 1
                        while counter < 10:
                            if api_client.send_request(path=path, method='get', headers=headers).status_code == 200:
                                result_func[endpoint] = 'y'
                                break
                            counter += 1
                            time.sleep(t)
                            t = t+0.5
                    else:
                        while counter < 2:
                            if api_client.send_request(path=path, method='get', headers=headers).status_code == 200:
                                result_func[endpoint] = 'y'
                                break
                            counter += 1
                    return {'payload': result_func, 'status': 200}
                else:
                    global destination_lists_health_check
                    if not destination_lists_health_check:
                        destination_lists_health_check = KVStoreService('destination_lists_health_check', session_token)
                    destination_lists_health_check_data = json.loads(
                        destination_lists_health_check.query_items('destination_lists_health_check', session_token))
                    if destination_lists_health_check_data[-1]['destinationListsURLStatus'] == "200":
                        result_func[endpoint] = 'y'
                    else:
                        result_func[endpoint] = 'n'
            
            elif endpoint == 'access':
                if new_call_flag == 'True':
                    if not oauth_settings:
                        oauth_settings = KVStoreService('oauth_settings', session_token)
                        oauth_settings = json.loads(oauth_settings.query_items('oauth_settings', session_token, {
                            'status':'active',
                            'orgId': api_client.org_id
                        }))
                    if len(oauth_settings) == 0:
                        return {'payload': {'message': 'Oauth settings are empty'}, 'status': 200}
                    result_func[endpoint] = 'n'
                    ztna_endpoint_status = self._is_ztna_endpoint_active(api_client)
                    if ztna_endpoint_status:
                        result_func[endpoint] = 'y'
                        return {'payload': result_func, 'status': 200}
                    ravpn_index_status = self._is_ravpn_index_configured(session_token, api_client.org_id)
                    if ravpn_index_status:
                        result_func[endpoint] = 'y'
                    return {'payload': result_func, 'status': 200}
            
            if new_call_flag == 'True':
                counter = 0
                result_func[endpoint] = 'n'
                if requests.get(the_url, headers=headers).status_code == 200:
                    result_func[endpoint] = 'y'
                elif requests.get(the_url, headers=headers).status_code == 429:
                    t = 1
                    while counter < 10:
                        if requests.get(the_url, headers=headers).status_code == 200:
                            result_func[endpoint] = 'y'
                            break
                        counter += 1
                        time.sleep(t)
                        t=t+0.5
                else:
                    while counter < 2:
                        if requests.get(the_url, headers=headers).status_code == 200:
                            result_func[endpoint] = 'y'
                            break
                        counter += 1

            return {'payload': result_func, 'status': 200}
        except ReportingAPIClientException as e:
            Logger().error("API: fetch_destination_lists, Exception : {0}".format(str(e.error_msg)))
            return {'payload': {"message": str(e.error_msg)}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: validate_license, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
    
    def _is_ztna_endpoint_active(self ,api_client: ReportingAPIClient) -> bool:
        endpoint = "/requests-by-timerange/ztna?from=-1minutes&to=now&limit=1&offset=0"
        headers = {
            'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x',
            'timerange': "minute"
        }
        counter = 0
        active = False
        res_bdy = api_client.send_request(path=endpoint, method='get', headers=headers)
        if res_bdy.status_code == 200:
            active =True
        elif res_bdy.status_code == 429:
            t = 1
            while counter < 10:
                if api_client.send_request(path=endpoint, method='get', headers=headers).status_code == 200:
                    active = True
                    break
                counter += 1
                time.sleep(t)
                t = t+0.5
        else:
            while counter < 2:
                if api_client.send_request(path=endpoint, method='get', headers=headers).status_code == 200:
                    active = True
                    break
                counter += 1
        return active

    def _is_ravpn_index_configured(self, session_token: str, org_id: str) -> bool:
        s3_indexes = KVStoreService('s3_indexes', session_token)
        s3_indexes_record = json.loads(s3_indexes.query_items('s3_indexes', session_token, {
            'orgId': org_id
        }))
        if len(s3_indexes_record) == 0:
            return False
        if s3_indexes_record[-1].get('ravpn_index') is not None:
            return True
        return False
    