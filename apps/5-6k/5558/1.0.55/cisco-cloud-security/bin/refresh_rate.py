# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common

refresh_rate = None

class RefreshRate(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            global refresh_rate
            if not refresh_rate:
                refresh_rate = KVStoreService('refresh_rate', session_token)

            referesh_rate_data = json.loads(refresh_rate.query_items('refresh_rate',
                            session_token))
            if len(referesh_rate_data)==0:
                raise Exception('Refresh rate is not selected for fetching')
            else:
                main_response = referesh_rate_data[-1]

            return {'payload': main_response, 'status': 200}
        except Exception as e:
            Logger().error("API: refresh_rate, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
