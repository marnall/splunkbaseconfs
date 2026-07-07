#!/usr/bin/env python

import sys
import json
import requests

from splunk import rest
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class getssqscoreCommand(StreamingCommand):
    """

    ##Syntax

    <command> | getssqscore

    ##Description

    Simple Test App for Radware Bot Risk Score

    """
    _app_name = "RadwareBotRiskScore"
    _default_output_field_name = "SSQResponse"
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

    request_type = Option(
        doc='''
        **Syntax:** **request_type=***<fieldname>*
        **Description:** Name of the field which holds type fo request either IP/UA''',
        require=False, validate=validators.Fieldname(), default='ip')

    access_token = Option(
        doc='''
        **Syntax:** **access_token=***<fieldname>*
        **Description:** Name of the field which holds access token''',
        require=False, validate=validators.Fieldname(), default=None)


    def fetch_default_config(self):
        """
        Fetch configurations
        """
        # Secured Radware Bot Risk Score endpoint to fetch data
        self.api_end_point = "https://botriskscore.shieldsquare.net"
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
            self.logger.error("status=error, app=RadwareBotRiskScore, action=get_access_token, error_msg=%s", e, exc_info=True)
            return None

    def trigger_request(self, request_url, parameters, headers):
        """
        
        :param request_url: 
        :param parameters:
        :param headers: 
        :return: 
        """
        # if its not https throw error and exit
        if not request_url.startswith("https"):
            self.logger.error("status=error, app=RadwareBotRiskScore, action=trigger_request, error_msg=URL should be https", exc_info=True)
            return None    
        try:
            response = requests.get(url=request_url, params=parameters, headers=headers)
            if response.status_code != 200:
                return None 
            data = response.json()
            return json.dumps(data)
        except Exception as e:
            self.logger.error("status=error, app=RadwareBotRiskScore, action=trigger_request, error_msg={}".format(str(e)), exc_info=True)
            return None

    def stream(self, events):
        # Put your event transformation code here
        self.fetch_default_config()
        
        request_url = f"{self.api_end_point}/v1/api/{self.request_type}"
        headers = {'BRS-Key': self.access_token}
        
        for event in events:
            _input = event[self.inputfield]
            parameters = {"value" : _input}
            response = self.trigger_request(request_url, parameters, headers)
            # _res_field = self.outputfield if self.outputfield else self._default_output_field_name
            _res_field = self._default_output_field_name
            event[_res_field] = response
            yield event

dispatch(getssqscoreCommand, sys.argv, sys.stdin, sys.stdout, __name__)