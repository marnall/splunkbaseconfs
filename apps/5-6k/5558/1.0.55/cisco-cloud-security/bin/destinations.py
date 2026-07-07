# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from validator import json_sanitizer,escapes
from datetime import datetime as dt
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from validator import cummulative_validator
from logger import Logger
from common import Common
from global_org_client import GlobalOrgClient

destinations = None

class Destinations(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):        
        try:
            main_response = []
            destination_list_id = None
            page_size = None
            page_number = None
            sort_field = None
            sort_direction = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            self.global_org_client = GlobalOrgClient(session_token)
            endpoint = params["rest_path"].split('/')[-1]
            if "dl_id" in params["query"]:
                destination_list_id = params["query"]["dl_id"]
                if not cummulative_validator(str(destination_list_id)):
                    raise Exception('Destination id validation failed')
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
                       
            global destinations
            if not destinations:
                destinations = KVStoreService('destinations', session_token)
                
            _skip = None
            if page_number and page_size:
                _skip = (int(page_number) - 1) * int(page_size)
            if sort_direction:
                sort_direction = int(sort_direction)
            query_conditions = {'status': endpoint,'orgId': self.global_org_client.global_org}
            Logger().info("API: destinations, Query Conditions : {0}".format(str(query_conditions)))
            if destination_list_id:
                query_conditions['destinationListId'] = str(destination_list_id)
            main_response = json.loads(destinations.query_items('destinations', session_token,
                                                                query_conditions=query_conditions, sort_by=sort_field,
                                                                sort_direction=sort_direction))
            Logger().info("API: destinations, Total Records Fetched : {0}".format(len(main_response)))
            Logger().debug("API: destinations, Records Fetched : {0}".format(str(main_response)))
            for response in main_response:
                if 'comment' not in response:
                    response['comment'] = 'None'
            data = main_response[_skip:int(page_size) * int(page_number)]
            api_response = {"data": data, "recordsTotal": len(main_response), "recordsFiltered": len(main_response)}
            return {'payload': api_response, 'status': 200}
        except Exception as e:
            Logger().error("API: destinations, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
