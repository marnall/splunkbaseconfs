# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from validator import cummulative_validator
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from kvstore_migration_utils import migrate_destination_list_collection
from service.app_kvstore_service import KVStoreService
from global_org_client import GlobalOrgClient
from enums import KvStoreCollections

dashboard_settings = None
investigate_settings = None
oauth_settings = None
cloudlock_settings = None

# Valid KV store collection names from KvStoreCollections enum
_VALID_COLLECTIONS = {c.value for c in KvStoreCollections}


def _is_valid_collection(name):
    """Validate collection name against KvStoreCollections enum."""
    return name in _VALID_COLLECTIONS


class KvStoreOperations(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            kv_store_name = None
            response_body = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']

            global dashboard_settings
            global investigate_settings
            global oauth_settings
            global cloudlock_settings
            if not dashboard_settings:
                dashboard_settings = KVStoreService('dashboard_settings', session_token)
            if not investigate_settings:
                investigate_settings = KVStoreService('investigate_settings', session_token)
            if not oauth_settings:
                oauth_settings = KVStoreService('oauth_settings', session_token)
            if not cloudlock_settings:
                cloudlock_settings = KVStoreService('cloudlock_settings', session_token)
            global_org_client = GlobalOrgClient(session_token)

            # code to migrate old kv store records of destinations
            migration_info = migrate_destination_list_collection.cache_info()
            if list(migration_info)[1] == 0:
                migrate_destination_list_collection(session_token)

            if not cummulative_validator(str(params["rest_path"])):
                raise Exception('rest_path validation failed in kv_store_operations API')
            endpoint = params["rest_path"].split('/')[-1]
            method = params['method']

            if endpoint == 'bulk_delete':
                if method != 'post':
                    raise Exception('bulk_delete endpoint only accepts POST requests')

                data = json.loads(params['payload'])
                collections = data.get('collections', [])
                org_id = data.get('orgId', global_org_client.global_org)

                if not collections or not isinstance(collections, list):
                    raise Exception('collections must be a non-empty array')

                kv_store_obj = KVStoreService(session_token=session_token)
                results = []
                for collection_name in collections:
                    try:
                        if not cummulative_validator(str(collection_name)):
                            results.append({
                                'collection': collection_name,
                                'status': 'error',
                                'message': 'KV store name validation failed'
                            })
                            continue

                        if not _is_valid_collection(collection_name):
                            results.append({
                                'collection': collection_name,
                                'status': 'error',
                                'message': 'Invalid collection name'
                            })
                            continue

                        kv_store_obj.delete_items_by_condition(collection_name, session_token, {"orgId": org_id})
                        results.append({
                            'collection': collection_name,
                            'status': 'success',
                            'message': 'Deleted successfully'
                        })
                    except Exception as e:
                        results.append({
                            'collection': collection_name,
                            'status': 'error',
                            'message': str(e)
                        })

                return {'payload': {'results': results}, 'status': 200}

            kv_store_name = params["query"]["kv_store_name"]
            if not cummulative_validator(str(kv_store_name)):
                raise Exception('KV store name validation failed')

            # Get orgId from query params if provided, otherwise use global org
            org_id = params["query"].get("orgId", global_org_client.global_org)

            if kv_store_name:
                kv_store_obj = KVStoreService(kv_store_name, session_token)
                if endpoint == 'delete':
                    # Use orgId filter for deletion
                    kv_store_obj.delete_items_by_condition(kv_store_name, session_token, {"orgId": org_id})
                    response_body = json.dumps({'status': 'success', 'message': 'Deleted successfully'})
                if endpoint == 'fetch':
                    response_body = kv_store_obj.query_items(kv_store_name, session_token, {
                        "orgId": org_id
                    }).decode('utf-8')
                if endpoint == 'update':
                    data_to_be_updated = json.loads(params['payload'])
                    updateFlag = data_to_be_updated['updateFlag']
                    key = data_to_be_updated['_key']
                    queried_settings_data = json.loads(
                        investigate_settings.query_items(
                            kv_store_name, session_token, {"orgId": org_id}
                        )
                    )
                    if len(queried_settings_data) != 0:
                        queried_prev_record = queried_settings_data[-1]
                    else:
                        raise Exception('There are no settings present to update')
                    if updateFlag == 'dashboard':
                        dashboard_settings.update_item_by_key('dashboard_settings', key, session_token,
                                                              {'search_interval': data_to_be_updated['search_interval']})
                    if updateFlag == 'investigate':
                        investigate_settings.update_item_by_key('investigate_settings', key, session_token,
                                                                {'userName': data_to_be_updated['userName'],
                                                                 'createdDate': data_to_be_updated['createdDate'],
                                                                 'configName': data_to_be_updated['configName'],
                                                                 'status': data_to_be_updated['status'],
                                                                 'index': data_to_be_updated['index'],
                                                                 'orgId': data_to_be_updated['orgId']
                                                                })
                    elif updateFlag == 'cloudlock':
                        cloudlock_settings.update_item_by_key('cloudlock_settings', key, session_token,
                                                                {'userName': data_to_be_updated['userName'],
                                                                 'createdDate': data_to_be_updated['createdDate'],
                                                                 'configName': data_to_be_updated['configName'],
                                                                 'url': data_to_be_updated['url'],
                                                                 'token': '',
                                                                 'showIncidentDetails': data_to_be_updated['showIncidentDetails'],
                                                                 'showUEBA': data_to_be_updated['showUEBA'],
                                                                 'status': data_to_be_updated['status'],
                                                                 'cloudlock_start_date':data_to_be_updated['cloudlock_start_date']
                                                                })
                    elif updateFlag == 'oauth_settings':
                        oauth_settings.update_item_by_key('oauth_settings', key, session_token,
                                                          {'userName': data_to_be_updated['userName'],
                                                           'createdDate': data_to_be_updated['createdDate'],
                                                           'configName': data_to_be_updated['configName'],
                                                           'baseURL': data_to_be_updated['baseURL'],
                                                           'apiKey': '',
                                                           'apiSecret': '',
                                                           'storageRegion': data_to_be_updated['storageRegion'],
                                                           'timezone': data_to_be_updated['timezone'],
                                                           'status': data_to_be_updated['status'],
                                                            'orgId': data_to_be_updated['orgId']
                                                           })
            return {'payload': response_body, 'status': 200}
        except Exception as e:
            Logger().error("API: kv_store_operations, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
