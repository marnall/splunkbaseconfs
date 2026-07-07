#!/usr/bin/env python

import sys
import json
import requests

from splunk import rest
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class savebrsCommand(StreamingCommand):
    """

    ##Syntax

    <command> | savebrs

    ##Description

    Radware Bot Risk Scanner

    """
    # default to 1 sec
    _request_timeout = 1
    api_end_point = "https://botriskscanner.shieldsquare.net"
    _app_name = "RadwareBotRiskScanner"
    _default_output_field_name = "Response"

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
            return 0
        try:
            response = requests.post(url=request_url, json=json_body, headers=headers, timeout=self._request_timeout)
            data = response.json()
            self.logger.error(data)
            if "message" in data  and "Invalid promotional code" in data['message']:
                return 2
            elif response.status_code != 200:
                self.logger.error("status=error, app=RadwareBotRiskScanner, action=trigger_request, response={}".format(str(response.text)), exc_info=True)
                return 0
            self.logger.error("BRS response: {}".format(data))
            return 1
        except Exception as e:
            self.logger.error("status=error, app=RadwareBotRiskScanner, action=trigger_request, error_msg={}".format(str(e)), exc_info=True)
            return 0

    def stream(self, records):
        # Put your record transformation code here
        headers = []
        request_url = f"{self.api_end_point}/v2/api/savebrs"
        # Process record and triggers call to Radware backend end point
        def fetch_data(record):
            try:
                data = dict(record)
                response = self.http_request(request_url=request_url, json_body=data, headers=headers)
                return {'access_token': record['access_token'], 'email': record['email'], 'promo_code': record['promo_code'], self._default_output_field_name: response}
            except Exception as e:
                self.logger.error("status=error, app=RadwareBotRiskScanner, action=fetch_data_exexcption, record={}, error_msg={}".format(str(record), str(e)), exc_info=True)
                return {'access_token': record['access_token'], 'email': record['email'], 'promo_code': record['promo_code'], self._default_output_field_name: 0}

        for record in records:
            self.logger.error("BRS configs: {}".format(record))
            yield fetch_data(record)
            
dispatch(savebrsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
