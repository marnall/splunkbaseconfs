# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import requests
from validator import json_sanitizer, cummulative_validator, get_host
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from token_service import TokenService

cloudlock_settings = None

class UpdateIncident(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            data = None
            cloudlockToken = None
            cloudlockURL = None
            permission = None
            headers = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
            method = params['method']
            if method == 'put':
                data = json.loads(params['payload'])
            global cloudlock_settings
            if not cloudlock_settings:
                cloudlock_settings = KVStoreService('cloudlock_settings', session_token)
            cloudlock_settings_data = json.loads(cloudlock_settings.query_items('cloudlock_settings', session_token))

            if len(cloudlock_settings_data) == 0:
                raise Exception('Cloudlock settings are empty')

            payload = TokenService.get_token(session_token, 'cloudlock_settings', host=host)
            if payload['payload']:
                cloudlockToken = payload['payload']['clear_token']
            else:
                raise Exception('Cloudlock Credentials not active')
            for obj in cloudlock_settings_data:
                if obj['status'] == 'active':
                    # cloudlockToken = obj['token']
                    cloudlockURL = obj['url']
                    permission = obj['showIncidentDetails']
                    headers = {'Authorization': 'Bearer ' + str(cloudlockToken),
                                'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
                    break
            if not cloudlockToken and not cloudlockURL and not permission and not headers:
                raise Exception('Cloudlock Credentials not active')
            if cloudlockToken != '' and cloudlockURL != '' and permission != '':
                if data:
                    id = data["id"]
                    incident_status = data["incident_status"]
                    severity = data["severity"]
                url = '{0}/incidents/{1}'.format(cloudlockURL, str(id))
                if cummulative_validator(id) and cummulative_validator(incident_status) and cummulative_validator(severity):
                    response_body = json.dumps(requests.put(url, 
                                            data=json.dumps({'incident_status': incident_status, 
                                            'severity': severity}), headers=headers).json())
                    return {'payload': response_body, 'status': 200}
                else:
                    raise Exception('validation error in update incident API')
        except Exception as e:
            Logger().error("API: update_incident, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}

        