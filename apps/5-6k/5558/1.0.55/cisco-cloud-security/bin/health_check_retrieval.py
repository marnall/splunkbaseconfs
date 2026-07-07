# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import splunklib.results as results
from validator import json_sanitizer
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from validator import cummulative_validator

kv_health_check_investigate = None
kv_health_check_cloudlock = None
kv_health_check_destination_lists = None


class HealthCheck(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def get_value(self, params, key, default=None):
        value = params.get(key, default)
        if not cummulative_validator(str(value)):
            raise Exception('{0} validation failed'.format(key))
        return value if value else ''

    def handle(self, in_string):
        response = None
        try:
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

            if endpoint == 'investigate':
                global kv_health_check_investigate
                if not kv_health_check_investigate:
                    kv_health_check_investigate = KVStoreService('investigate_health_check', session_token)
                response = json.loads(
                    kv_health_check_investigate.query_items('investigate_health_check', session_token,
                                                            sort_by=sort_field, sort_direction=sort_direction))
            elif endpoint == 'cloudlock':
                global kv_health_check_cloudlock
                if not kv_health_check_cloudlock:
                    kv_health_check_cloudlock = KVStoreService('cloudlock_health_check', session_token)
                response = json.loads(
                    kv_health_check_cloudlock.query_items('cloudlock_health_check', session_token,
                                                            sort_by=sort_field, sort_direction=sort_direction))
            elif endpoint == 'destinationlists':
                global kv_health_check_destination_lists
                if not kv_health_check_destination_lists:
                    kv_health_check_destination_lists = KVStoreService('destination_lists_health_check', session_token)
                response = json.loads(
                    kv_health_check_destination_lists.query_items('destination_lists_health_check', session_token,
                                                            sort_by=sort_field, sort_direction=sort_direction))
            data = response[_skip:int(page_size)*int(page_number)]
            api_response = {"data":data,"recordsTotal":len(response),"recordsFiltered":len(response)}
            response_body = json.dumps(json_sanitizer(api_response))
            return {'payload': response_body, 'status': 200}
        except Exception as e:
            Logger().error("API: health_check_retrieval, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
