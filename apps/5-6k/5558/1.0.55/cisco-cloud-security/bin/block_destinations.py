# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from validator import cummulative_validator
from service.app_kvstore_service import KVStoreService
from logger import Logger
from reporting_api_client import ReportingAPIClient
from enums import DestinationListAPIEndpoints
from exceptions import ReportingAPIClientException

destinations = None


def validator(arg, name):
    if not cummulative_validator(arg):
        raise Exception('KV store data [{0}] validation failed'.format(name))
    return arg


def main():
    try:
        Logger().info("AL: block_destinations: execution started")
        if len(sys.argv) > 1 and sys.argv[1] == "--execute":
            main_res = json.loads(sys.stdin.read())
            configur = main_res['configuration']
            payload_res = main_res['result']
            session_token = main_res['session_key']
            _owner = main_res['owner']
            field = validator(configur['field_name'],'field_name')
            if configur['comment']:
                comment = configur['comment']
            else:
                comment = 'None'
            destination_id = validator(configur['destination_list_id'],'destination_list_id')
            kvstore_service = KVStoreService(session_token)
            destination_list = json.loads(
                kvstore_service.query_items(
                    "selected_destination_lists",
                    session_token,
                    query_conditions={"dest_list_id": str(destination_id)},
                )
            )
            if len(destination_list) == 0:
                raise Exception(
                    f"Destination List with ID {destination_id} not found in selected_destination_lists KV Store."
                )
            org_id = destination_list[-1].get('orgId')
            if not org_id:
                raise Exception(
                    f"org_id not found for Destination List with ID {destination_id}."
                )
            if field in list(payload_res.keys()):
                destination_req = str(payload_res[field])
                if destination_req.endswith("."):
                    destination_req = destination_req[:-1]
                payload = [{"destination": validator(str(destination_req),'destination_req'),
                            "comment" : comment}]
                headers = {'Content-Type': 'application/json', 
                           'Accept': 'application/json',
                           'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
                api_client = ReportingAPIClient(session_token, org_id=org_id)
                path = DestinationListAPIEndpoints.BLOCK_DESTINATION.value.format(destination_id)
                res_bdy = api_client.send_request(path=path, method='post', payload=json.dumps(payload), headers=headers)
                res_bdy = res_bdy.json()
                if 'error' in res_bdy.keys():
                    raise Exception(f"Failed to add destination: {res_bdy['message']}")
                if res_bdy:
                    global destinations
                    if not destinations:
                        destinations = KVStoreService('destinations', session_token)
                    page = 1
                    for dest in payload:
                        req_dest_id = None
                        while not req_dest_id:
                            path = f'{path}?limit=100&page={str(page)}'
                            res_bdy2 = api_client.send_request(path=path, method='get', headers=headers)
                            res_bdy2 = res_bdy2.json()['data']
                            for dic in res_bdy2:
                                if dic['destination'] == dest["destination"]:
                                    req_dest_id = dic['id']
                                    break
                            page += 1
                        list_dest = json.loads(destinations.query_items('destinations', session_token, query_conditions={'name': dest["destination"],'destinationListId': str(destination_id),'orgId':org_id}))
                        if len(list_dest) == 0:
                            destinations_insr = destinations.insert_record('destinations', session_token,
                                                                        {'name':validator(dest[u"destination"], 'destination'),
                                                                            'id':validator(req_dest_id, 'req_dest_id'),
                                                                            'comment':comment,
                                                                            'status': 'added',
                                                                            'action':'added',
                                                                            'source':'alert',
                                                                            'modificationtime':validator(str(res_bdy["data"]["modifiedAt"]), 'modifiedAt'),
                                                                            'destinationListId':validator(str(res_bdy["data"]["id"]), 'destinationListId'),
                                                                            'destinationListName':validator(res_bdy["data"]["name"], 'destinationListName'),
                                                                            'loggedinuser':validator(_owner, 'loggedinuser'),
                                                                            'orgId': org_id})
                        else:
                            dest_info = json.loads(destinations.query_items('destinations', session_token,
                                            query_conditions={'destinationListId': str(destination_id), 'id': str(req_dest_id), 'orgId': org_id}))[0]
                            destinations.update_item_by_key('destinations', dest_info['_key'],
                                                            session_token,
                                                            {
                                                                'name': dest_info['name'],
                                                                'id': dest_info['id'],
                                                                'comment': dest_info['comment'],
                                                                'status': 'added',
                                                                'action':'added',
                                                                'source':'alert',
                                                                'modificationtime': validator(str(res_bdy["data"]["modifiedAt"]), 'modifiedAt'),
                                                                'destinationListId': dest_info['destinationListId'],
                                                                'destinationListName': dest_info['destinationListName'],
                                                                'loggedinuser': dest_info['loggedinuser'],
                                                                'orgId': dest_info['orgId']
                                                            })
        Logger().info("AL: block_destinations: execution completed")
    except ReportingAPIClientException as e:
        Logger().error("AL: block_destinations: Exception: {0}".format(str(e.error_msg)))
    except Exception as e:
        Logger().error("AL: block_destinations: Exception: {0}".format(str(e)))

if __name__ == '__main__':
    main()
