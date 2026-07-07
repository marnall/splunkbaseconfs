# encoding = utf-8
from __future__ import print_function
import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import splunklib.client as client
from validator import get_host
from logger import Logger
from common import Common

class FetchIndexes(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        main_response = []
        try:
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
            service = client.connect(host=host, token=session_token)
            ind_list = service.indexes.list()
            for i in ind_list:
                main_response.append(i.name)
            return {'payload': main_response, 'status': 200}
        except Exception as e:
            Logger().error("API: fetch_indexes, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
