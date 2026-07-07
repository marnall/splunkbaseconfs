# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from datetime import datetime as dt
from collections import defaultdict
from validator import cummulative_validator
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from global_org_client import GlobalOrgClient

destinations = None

class DestinationsChartApi(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            main_response = []
            main_response_body = {}
            earliest_time = None
            latest_time = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            global_org_client = GlobalOrgClient(session_token)
            endpoint = params["rest_path"].split('/')[-1]
            earliest_time = params["query"]["earliest_time"]
            if not cummulative_validator(str(earliest_time)):
                raise Exception('Earliest time validation failed')
            latest_time = params["query"]["latest_time"]
            if not cummulative_validator(str(latest_time)):
                raise Exception('Latest time validation failed')                    
            global destinations
            if not destinations:
                destinations = KVStoreService('destinations', session_token)
            data_set = []
            res = defaultdict(list)
            # dict1 = {}
            list_res = []
            main_response = json.loads(
                destinations.query_items(
                    "destinations",
                    session_token,
                    query_conditions={"action": endpoint, "orgId": global_org_client.global_org},
                )
            )
            for ele in main_response:
                if ele['modificationtime'] >= earliest_time and ele['modificationtime'] <= latest_time:
                    data_set.append(ele)
            for i in data_set:
                res[i['modificationtime']].append(i)
            for itm in res:
                list_res.append((itm,len(res[itm])))
            list_req = sorted(list_res, key=lambda x: x[0])
            main_response_body = {'key':endpoint, 'data':list_req}
            return {'payload': main_response_body, 'status': 200}
        except Exception as e:
            Logger().error("API: destinations_chart_api, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}     
