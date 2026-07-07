# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import requests
from validator import json_sanitizer, cummulative_validator, get_host
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from service.app_kvstore_service import KVStoreService
from token_service import TokenService


cloudlock_settings = None
class RetrieveIncident(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            id = None
            cloudlockToken = None
            cloudlockURL = None
            permission = None
            headers = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
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
            
            id = params["query"]["id"]
            permission = (permission == 'Yes') or (params["query"]["search_flag"] == "1")
            if not cummulative_validator(str(id)):
                raise Exception('Argument id validation failed')

            # Logger().info("API: retrieve_incident, URL: {0}/incidents/{1}".format(cloudlockURL,str(id)))
            main_response = json.loads(requests.get('{0}/incidents/{1}'.format(cloudlockURL, str(id)), headers=headers).content)

            if 'message' not in list(main_response.keys()):
                main_created_at = main_response["created_at"]
                incident_status_value_list = ["NEW", "IN PROGRESS", "RESOLVED", "DISMISSED"]
                incident_status_value = main_response["incident_status"]
                for i in incident_status_value_list:
                    main_response.update({str(i): (1 if i == incident_status_value else 0)})
                inci_originid = main_response["entity"]["origin_id"]
                resp_ueba = json.loads(requests.get('{0}/activities?ids={1}'.format(cloudlockURL, str(inci_originid)), headers=headers).content)
                resp_ueba.update({'main_created_at': main_created_at})
                if resp_ueba['total'] != 0 and permission:
                    main_response.update({'ueba_data_set': resp_ueba})
                    main_response.update({'event_type': 'UEBA'})
                else:
                    inci_entityid = main_response['entity']['id']
                    resp_dlp = json.loads(requests.get('{0}/incident_entities/{1}'.format(cloudlockURL, str(inci_entityid)), headers=headers).content)
                    # Logger().info("API: retrieve_incident, resp_dlp : {0}".format(str(resp_dlp)))
                    if 'message' not in list(resp_dlp.keys()):
                        resp_dlp.update({'main_created_at': main_created_at})
                        if resp_dlp['origin_subtype'] == 'app':
                            if permission:
                                main_response.update({'app_data_set': resp_dlp})
                                main_response.update({'event_type': 'APP'})
                            else:
                                main_response = {'message': "Unable to display data due to lack of permission"}
                        else:
                            if permission:
                                main_response.update({'dlp_data_set': resp_dlp})
                                main_response.update({'event_type': 'DLP'})
                            else:
                                main_response = {'message': "Unable to display data due to lack of permission"}
                    else:
                        # Logger().info("API: retrieve_incident, resp_dlp before exception : {0}".format(str(resp_dlp)))
                        raise Exception('A resource with that ID does not exist')
                if (resp_ueba['total'] != 0 and not permission):
                    main_response = {'message': "Unable to display data due to lack of permission"}
            else:
                # Logger().info("API: retrieve_incident, main_response before exception : {0}".format(str(main_response)))
                raise Exception('A resource with that ID does not exist')
            return {'payload': main_response, 'status': 200}
        except Exception as e:
            Logger().error("API: retrieve_incident, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
