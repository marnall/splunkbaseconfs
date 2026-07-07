# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import requests
import splunklib.client as client
import splunklib.results as results
from validator import cummulative_validator, get_host
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common


class FetchSearchJobResults(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            main_response = []
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            search_job_id = params["query"]["s_id"]
            header = params.get('headers', [])
            host = get_host(header)
            if not cummulative_validator(str(search_job_id)):
                raise Exception('Search job id validation failed')            
            page_size = int(params["query"]["page_size"]) if "page_size" in params["query"] else 0
            page_number = int(params["query"]["page_number"]) if "page_number" in params["query"] else 0
            service = client.connect(host=host, token=session_token, app="cisco-cloud-security")
            jb = service.jobs[search_job_id]
            kwargs = {"count": page_size, "offset": (page_number - 1) * page_size}
            for result in results.ResultsReader(jb.results(**kwargs)):
                main_response.append(result)
            return {'payload': main_response, 'status': 200}
        except Exception as e:
            Logger().error("API: fetch_search_job_results, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
