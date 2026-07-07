# encoding = utf-8
from __future__ import print_function
import sys
import json
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
from datetime import datetime
from splunk.persistconn.application import PersistentServerConnectionApplication
from validator import json_sanitizer, cummulative_validator, date_validator
from kvstore.service import KVStoreService
from common import Common
from logger import Logger

ta_tos = None


class TocFunctionality(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            Logger().error("INSIDE TOC")
            data = None
            response = None
            response_body = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            method = params['method']
            global ta_tos
            if not ta_tos:
                ta_tos = KVStoreService('ta_tos', session_token)
            if method == 'post':
                data = json.loads(params['payload'])['data']

                if not cummulative_validator(data['CustName']):
                    raise Exception('CustName validation failed')
                if not cummulative_validator(data['CustVersion']):
                    raise Exception('CustVersion validation failed')

                if data['CustName'] != '' and data['CustVersion'] != '':
                    toc_insr = ta_tos.add({'CustName': data['CustName'],
                                                    'CustVersion': data['CustVersion'],
                                                    'CustDate': str(datetime.now())})
                    response_body = 'successfully inserted into TOC kvstore'
                else:
                    raise Exception('Enter valid info for TOC')
            elif method == 'get':
                response = json.loads(ta_tos.get())
                if len(response) != 0:
                    response_body = response[-1]
                else:
                    # raise Exception('TOC kvstore is empty')
                    return {'payload': {'message': 'TOC kvstore is empty'}, 'status': 200}
            return {'payload': response_body, 'status': 200}
        except Exception as e:
            Logger().error("API: toc_functionality, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
