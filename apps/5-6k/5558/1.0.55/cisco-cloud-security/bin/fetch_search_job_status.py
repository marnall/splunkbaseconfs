# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import splunklib.client as client
from validator import cummulative_validator, get_host
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common


class FetchSearchJobStatus(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            search_job_id = params["query"]["s_id"]
            header = params.get('headers', [])
            host = get_host(header)
            if not cummulative_validator(str(search_job_id)):
                raise Exception('Search job id validation failed')            
            service = client.connect(host=host, token=session_token, app="cisco-cloud-security")
            jb = client.Job(service, search_job_id)
            return {'payload': jb.content, 'status': 200}
        except Exception as e:
            Logger().error("API: fetch_search_job_status, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
