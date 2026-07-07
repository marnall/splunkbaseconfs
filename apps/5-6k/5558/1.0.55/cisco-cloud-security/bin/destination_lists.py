# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
import json
from datetime import datetime
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from validator import cummulative_validator, get_host
from logger import Logger
from common import Common
from enums import DestinationListAPIEndpoints
from reporting_api_client import ReportingAPIClient
from exceptions import ReportingAPIClientException

destinations = None

class DestinationLists(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def validator(self, arg, name):
        if not cummulative_validator(arg):
            raise Exception('KV store data [{0}] validation failed'.format(name))
        return arg

    def handle(self, in_string):
        try:
            destination_id = ''
            response_body = None
            headers = None
            page = 1
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
            endpoint = self.validator(str(params["rest_path"]), 'rest_path').split('/')[-1]
            headers = {'Content-Type': 'application/json', 
                        'Accept':'application/json',
                        'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
            api_client = ReportingAPIClient(session_token)
            if endpoint == 'fetch_all_lists':
                path = DestinationListAPIEndpoints.GET_DESTINATION_LISTS.value
                if data['comment']:
                    comment = data['comment']
                else:
                    comment = 'None'
                res_bdy = api_client.send_request(path=path, method='get', headers=headers)
                res_bdy = res_bdy.json()
                response_body = json.dumps(res_bdy)
            elif endpoint == 'fetch_all_destinations':
                destination_id = self.validator(str(params["query"]["d_id"]), 'destination_id')
                if data['comment']:
                    comment = data['comment']
                else:
                    comment = 'None'
                path = DestinationListAPIEndpoints.FETCH_ALL_DESTINATIONS.value.format(destination_id)
                res_bdy = api_client.send_request(path=path, method='get', headers=headers)
                res_bdy = res_bdy.json()
                response_body = json.dumps(res_bdy)
            elif endpoint == 'block_destinations':
                data = json.loads(params['payload'])['data']
                payload = data['destinations_to_be_blocked']
                destination_id = self.validator(data['destination_list_id'], 'destination_list_id')
                if data['comment']:
                    comment = data['comment']
                else:
                    comment = 'None'
                path = DestinationListAPIEndpoints.BLOCK_DESTINATION.value.format(destination_id)
                payload_en = []
                for obj in payload:
                    payload_en.append({'destination':obj['destination'],
                                        'comment':comment})
                res_bdy = api_client.send_request(path=path, method='post', payload=json.dumps(payload_en), headers=headers)
                res_bdy = res_bdy.json()
                if 'error' in res_bdy.keys():
                    raise Exception(f"Failed to add destination: {res_bdy['message']}")
                else:
                    response_body = json.dumps(res_bdy)
                if res_bdy:
                    global destinations
                    if not destinations:
                        destinations = KVStoreService('destinations', session_token)
                    for dest in payload_en:
                        req_dest_id = None
                        while not req_dest_id:
                            path = f'{path}?limit=100&page={str(page)}'
                            res_bdy2 = api_client.send_request(path=path, method='get', headers=headers)
                            res_bdy2 = res_bdy2.json()['data']
                            for dic in res_bdy2:
                                if dic['destination'] == dest["destination"]:
                                    req_dest_id = dic['id']
                                    break
                            if len(res_bdy2)!=0:
                                page = page + 1
                            else:
                                break
                        list_dest = json.loads(destinations.query_items('destinations', session_token, query_conditions={'name':dest['destination'],'destinationListId': str(destination_id),'orgId': api_client.org_id}))
                        if req_dest_id:
                            if len(list_dest) == 0:
                                destinations_insr = destinations.insert_record('destinations',session_token,
                                                                           {
                                                                               'name':self.validator(dest[u"destination"], 'destination'),
                                                                                'id':self.validator(req_dest_id, 'req_dest_id'),
                                                                                'comment':comment,
                                                                                'status':'added',
                                                                                'action':'added',
                                                                                'source':'manual',
                                                                                'modificationtime':self.validator(str(res_bdy['data']['modifiedAt']), 'modifiedAt'),
                                                                                'destinationListId':self.validator(str(res_bdy["data"]["id"]), 'id'),
                                                                                'destinationListName':self.validator(res_bdy["data"]["name"], 'name'),
                                                                                'loggedinuser':self.validator(params['session']['user'], 'user'),
                                                                                'orgId': api_client.org_id
                                                                            })
                            else:
                                dest_info = json.loads(destinations.query_items('destinations', session_token,query_conditions={'destinationListId': str(destination_id), 'id': str(req_dest_id)}))[0]
                                if dest_info:
                                    destinations.update_item_by_key('destinations', dest_info['_key'],
                                                                    session_token,
                                                                    {
                                                                        'name': dest_info['name'],
                                                                        'id': dest_info['id'],
                                                                        'comment': dest_info['comment'],
                                                                        'status':'added',
                                                                        'action':'added',
                                                                        'source':'manual',
                                                                        'modificationtime': self.validator(str(res_bdy['data']['modifiedAt']), 'modifiedAt'),
                                                                        'destinationListId': dest_info['destinationListId'],
                                                                        'destinationListName': dest_info['destinationListName'],
                                                                        'loggedinuser': dest_info['loggedinuser'],
                                                                        'orgId': dest_info['orgId'] if 'orgId' in dest_info else api_client.org_id
                                                                    })
                        else:
                            raise Exception('Destination could not be updated in KVstore')

            elif endpoint == 'delete_destinations':
                data = json.loads(params['payload'])['data']
                payload = data['destinations_to_be_unblocked']
                for i in payload:
                    self.validator(str(i), 'payload[i]')
                destination_list_id = self.validator(str(data['destination_list_id']), 'destination_list_id')
                path = DestinationListAPIEndpoints.REMOVE_DESTINATION.value.format(destination_list_id)
                res_bdy = api_client.send_request(path=path, method='delete',payload=json.dumps(payload), headers=headers)
                res_bdy = res_bdy.json()
                response_body = json.dumps(res_bdy)
                if res_bdy:
                    # global destinations
                    if destinations is None:
                        destinations = KVStoreService('destinations', session_token)

                    for dest in payload:
                        dest_info = json.loads(
                            destinations.query_items(
                                "destinations",
                                session_token,
                                query_conditions={
                                    "destinationListId": str(destination_list_id),
                                    "id": str(dest),
                                    "orgId": api_client.org_id,
                                },
                            )
                        )
                        if len(dest_info) == 0:
                            continue
                        dest_info = dest_info[0]
                        try:
                            comment = dest_info['comment']
                            destinations.update_item_by_key('destinations',dest_info['_key'],session_token,
                                                        {
                                                            'name':dest_info['name'],
                                                            'id':dest_info['id'],
                                                            'comment':comment,
                                                            'status':'removed',
                                                            'action':'removed',
                                                            'source':'manual',
                                                            'modificationtime': self.validator(str(res_bdy["data"]["modifiedAt"]), 'modifiedAt'),
                                                            'destinationListId':dest_info['destinationListId'],
                                                            'destinationListName':dest_info['destinationListName'],
                                                            'loggedinuser':dest_info['loggedinuser'],
                                                            'orgId': dest_info['orgId'] if 'orgId' in dest_info else api_client.org_id
                                                        })
                        except:
                            destinations.update_item_by_key('destinations',dest_info['_key'],session_token,
                                                        {
                                                            'name':dest_info['name'],
                                                            'id':dest_info['id'],
                                                            'comment':'None',
                                                            'status':'removed',
                                                            'action':'removed',
                                                            'source':'manual',
                                                            'modificationtime': self.validator(str(res_bdy["data"]["modifiedAt"]), 'modifiedAt'),
                                                            'destinationListId':dest_info['destinationListId'],
                                                            'destinationListName':dest_info['destinationListName'],
                                                            'loggedinuser':dest_info['loggedinuser'],
                                                            'orgId': dest_info['orgId'] if 'orgId' in dest_info else api_client.org_id
                                                        })
            return {'payload': response_body, 'status': 200}
        except ReportingAPIClientException as e:
            Logger().error("API: destination_lists, Exception : {0}".format(str(e.error_msg)))
            return {'payload': {"message": str(e.error_msg)}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: destination_lists, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
