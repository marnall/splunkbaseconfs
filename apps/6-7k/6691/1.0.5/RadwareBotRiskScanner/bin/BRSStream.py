#!/usr/bin/env python

import sys
import json
import requests
from concurrent.futures import ThreadPoolExecutor

from splunk import rest
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

# class doubleQuoteDict(dict):
#     def __str__(self):
#         return json.dumps(self)

@Configuration()
class getbrsCommand(StreamingCommand):
    """

    ##Syntax

    <command> | getbrs

    ##Description

    Radware Bot Risk Scanner

    """
    # default to 8 threads and adjust it based on # of cores
    _thread_count = 8
    # default to 1 sec
    _request_timeout = 1

    _app_name = "RadwareBotRiskScanner"
    _default_output_field_name = "BRSResponse"
    _splunk_kv_config_collection_name = "radware_brs_config"
    _splunk_brs_config_api_end_point = "api_end_point"
    _splunk_brs_config_access_token = "access_token"

    SPLUNK_STORAGE_REALM = "radware_brs_stream_command"
    SPLUNK_STORAGE_USER_NAME = "radware_brs_access_token"

    inputfield = Option(
        doc='''
        **Syntax:** **inputfield=***<fieldname>*
        **Description:** Name of the input field send to API''',
        require=True, validate=validators.Fieldname())

    # outputfield = Option(
    #     doc='''
    #     **Syntax:** **inputfield=***<fieldname>*
    #     **Description:** Name of the field which holds response data from API''',
    #     require=False, validate=validators.Fieldname())
    
    # api_end_point = Option(
    #     doc='''
    #     **Syntax:** **api_end_point=***<fieldname>*
    #     **Description:** Name of the field which holds api end point''',
    #     require=False, validate=validators.Match("http://.*", r"^http://.*"), default=None)

    # request_type = Option(
    #     doc='''
    #     **Syntax:** **request_type=***<fieldname>*
    #     **Description:** Name of the field which holds type fo request either IP/UA''',
    #     require=False, validate=validators.Fieldname(), default='ip')

    access_token = Option(
        doc='''
        **Syntax:** **access_token=***<fieldname>*
        **Description:** Name of the field which holds access token''',
        require=False, default=None)

    def fetch_default_config(self):
        """
        Fetch configurations
        """
        self.pool = ThreadPoolExecutor(self._thread_count) # 8 threads, adjust to taste and # of cores
        # Secured Radware Bot Risk Scanner endpoint to fetch data
        self.api_end_point = "https://botriskscanner.shieldsquare.net"
        self.access_token = self.get_access_token()

    def get_access_token(self):
        try:
            session_key = self.search_results_info.auth_token
            service_params = {
                'output_mode':'json'
                }
            user_name = self.SPLUNK_STORAGE_REALM + ':' + self.SPLUNK_STORAGE_USER_NAME
            endpoint = "/servicesNS/nobody/{}/storage/passwords/{}".format(self._app_name, user_name) 
            response_status, response_content = rest.simpleRequest(endpoint, sessionKey=session_key, 
                                                                   getargs=service_params, raiseAllErrors=True)
            if response_content:
                password_obj = json.loads(response_content)
                return password_obj['entry'][0]['content']['clear_password']
        except Exception as e:
            self.logger.error("status=error, app=RadwareBotRiskScanner, action=get_access_token, error_msg=%s", e, exc_info=True)
            return None

    def http_request(self, request_url, json_body, headers):
        """
        
        :param request_url: 
        :param json_body:
        :param headers: 
        :return: 
        """
        # if its not https throw error and exit
        if not request_url.startswith("https"):
            self.logger.error("status=error, app=RadwareBotRiskScanner, action=trigger_request, error_msg=URL should be https", exc_info=True)
            return None    
        try:
            response = requests.post(url=request_url, json=json_body, headers=headers, timeout=self._request_timeout)
            if response.status_code != 200:
                self.logger.error("status=error, app=RadwareBotRiskScanner, action=trigger_request, response={}".format(str(response.text)), exc_info=True)
                return None 
            data = response.json()
            return json.dumps(data)
        except Exception as e:
            self.logger.error("status=error, app=RadwareBotRiskScanner, action=trigger_request, error_msg={}".format(str(e)), exc_info=True)
            return None

    def stream(self, records):
        # Put your record transformation code here
        self.fetch_default_config()
        chunk = []
        headers = {'BRS-Key': self.access_token}
        request_url = f"{self.api_end_point}/v2/api/getbrs"
        
        # Process record and triggers call to Radware backend end point
        def fetch_data(record):
            try:
                data = dict(record)
                # _data = doubleQuoteDict(data)
                response = self.http_request(request_url=request_url, json_body=data, headers=headers)
                return {self.inputfield: record['address'], 'date': record['date'], 'hour': record['hour'], 'umin': record['umin'], 'totalhits': record['totalhits'], self._default_output_field_name: response}
                # return {self.inputfield: record[self.inputfield], 'count': record['count'], self._default_output_field_name: response}
            except Exception as e:
                self.logger.error("status=error, app=RadwareBotRiskScanner, action=fetch_data_exexcption, record={}, error_msg={}".format(str(record), str(e)), exc_info=True)
                # return {self.inputfield: record[self.inputfield], 'count': record['count'], self._default_output_field_name: None}
                return {self.inputfield: record['address'], 'date': record['date'], 'hour': record['hour'], 'umin': record['umin'], 'totalhits': record['totalhits'], self._default_output_field_name: None}

        for record in records:
            chunk.append(record)
            if len(chunk) == self._thread_count:
                self.logger.error("############################################################################################", exc_info=True)
                self.logger.error("status=error, app=RadwareBotRiskScanner, action=stream_step_one, chunk={}".format(str(chunk)), exc_info=True)
                results = self.pool.map(fetch_data, chunk)
                for result in results:
                    # self.logger.error("status=error, app=RadwareBotRiskScanner, action=stream_res_one, results={}".format(str(result)), exc_info=True)
                    yield result
                chunk = []
                self.logger.error("############################################################################################", exc_info=True)
        if chunk:
            self.logger.error("############################################################################################", exc_info=True)
            self.logger.error("status=error, app=RadwareBotRiskScanner, action=stream_step_two, chunk={}".format(str(chunk)), exc_info=True)
            results = self.pool.map(fetch_data, chunk)
            for result in results:
                # self.logger.error("status=error, app=RadwareBotRiskScanner, action=stream_res_two, results={}".format(str(result)), exc_info=True)
                yield result
            chunk = []
            self.logger.error("############################################################################################", exc_info=True)

dispatch(getbrsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
