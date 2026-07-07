# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from validator import json_sanitizer, cummulative_validator
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from service.app_kvstore_service import KVStoreService

investigate_settings = None
oauth_settings = None
cloudlock_settings = None
cloudlock_index = None
s3_indexes = None


class ListSettings(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def masker(self, result):
        for obj in result:
            if 'token' in obj.keys():
                obj.update({"token": '************'})
            if 'apiKey' in obj.keys():
                obj.update({"apiKey": '************'})
            if 'apiSecret' in obj.keys():
                obj.update({"apiSecret": '************'})
        return result

    def get_value(self, params, key, default=None):
        value = params.get(key, default)
        if not cummulative_validator(str(value)):
            raise Exception('{0} validation failed'.format(key))
        return value if value else ''

    def clear_collection_if_new_field(self, session_token, collection, collection_name, collection_keys):
        data_fetched = json.loads(collection.query_items(collection_name, session_token))
        if len(data_fetched) != 0:
            prev_record = data_fetched[-1]
            for k in collection_keys:
                if k not in prev_record:
                    collection.delete_all_items(collection_name, session_token)
                    break

    def handle(self, in_string):
        try:
            kv_store_name = None
            response_body = None
            list1 = []
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            page_size = params["query"]["page_size"]
            if not cummulative_validator(str(page_size)):
                raise Exception('Page size validation failed')
            page_number = params["query"]["page_number"]
            if not cummulative_validator(str(page_number)):
                raise Exception('Page number validation failed')
            sort_field = params["query"]["sort_field"]
            if not cummulative_validator(str(sort_field)):
                raise Exception('Sort field validation failed')
            sort_direction = params["query"]["sort_direction"]
            if sort_direction != "-1":
                if not cummulative_validator(str(sort_direction)):
                    raise Exception('Sort direction validation failed')

            _skip = None
            if page_number and page_size:
                _skip = (int(page_number) - 1) * int(page_size)
            if sort_direction:
                sort_direction = int(sort_direction)

            endpoint = self.get_value(params, 'rest_path')
            if endpoint:
                endpoint = endpoint.split('/')[-1]

            if endpoint == 'investigate_settings':
                global investigate_settings
                if not investigate_settings:
                    investigate_settings = KVStoreService('investigate_settings', session_token)
                fetched_res = json.loads(
                    investigate_settings.query_items('investigate_settings', session_token, sort_by=sort_field,
                                                     sort_direction=sort_direction))
                response_body = self.masker(fetched_res)
            if endpoint == 'cloudlock_settings':
                global cloudlock_settings
                if not cloudlock_settings:
                    cloudlock_settings = KVStoreService('cloudlock_settings', session_token)
                fetched_res = json.loads(
                    cloudlock_settings.query_items('cloudlock_settings', session_token, sort_by=sort_field,
                                                   sort_direction=sort_direction))
                response_body = self.masker(fetched_res)
            if endpoint == 'oauth_settings':
                global oauth_settings
                if not oauth_settings:
                    oauth_settings = KVStoreService('oauth_settings', session_token)
                fetched_res = json.loads(
                    oauth_settings.query_items('oauth_settings', session_token, sort_by=sort_field,
                                               sort_direction=sort_direction))
                response_body = self.masker(fetched_res)
            if endpoint == 's3_indexes':
                global s3_indexes
                if not s3_indexes:
                    s3_indexes = KVStoreService('s3_indexes', session_token)
                s3_indexes_keys = ['dns_index', 'proxy_index', 'firewall_index', 'dlp_index', 'ravpn_index', 'createdDate']
                self.clear_collection_if_new_field(session_token, s3_indexes, 's3_indexes', s3_indexes_keys)
                response_body = json.loads(s3_indexes.query_items('s3_indexes', session_token,
                                                                  sort_by=sort_field, sort_direction=sort_direction))

            data = response_body[_skip:int(page_size) * int(page_number)]
            api_response = {"data": data, "recordsTotal": len(response_body), "recordsFiltered": len(response_body)}
            return {'payload': api_response, 'status': 200}
        except Exception as e:
            Logger().error("API: list_settings, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
