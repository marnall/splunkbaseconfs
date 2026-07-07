# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from splunk.persistconn.application import PersistentServerConnectionApplication
from validator import cummulative_validator, date_validator, get_host, json_sanitizer
from logger import Logger
from common import Common
from enums import DestinationListAPIEndpoints
from reporting_api_client import ReportingAPIClient
from exceptions import FetchDestinationException, ReportingAPIClientException


class FetchDestinationLists(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def validator(self, arg, method, name):
        if method == 'cu':
            if not cummulative_validator(arg):
                raise Exception('KV store data [{0}] validation failed'.format(name))
            return arg
        elif method == 'da':
            if not date_validator(arg):
                raise Exception('KV store date [{0}] validation failed'.format(name))
            return arg
        return arg

    def handle(self, in_string):
        Logger().info("fetching destination lists...")
        try:
            data = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            method = params['method']
            header = params.get('headers', [])
            host = get_host(header)
            if method == 'post':
                data = json.loads(params['payload'])['data']
                if data:
                    api_outh_settings_data = data['oauth_settings']
                    api_key = api_outh_settings_data['apiKey']
                    api_secret = api_outh_settings_data['apiSecret']
                    base_url = api_outh_settings_data['baseURL']
                    if not all([api_key, api_secret, base_url]):
                        raise FetchDestinationException(error_code=500,
                                                        error_msg='Please enter all the Umbrella API settings.')
                    api_client = ReportingAPIClient(session_token, api_key, api_secret, base_url)
                    api_client.generate_token()
                else:
                    api_client = ReportingAPIClient(session_token)
                headers = {'Content-Type': 'application/json', 
                           'Accept': 'application/json', 
                           'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
                path = DestinationListAPIEndpoints.GET_DESTINATION_LISTS.value
                res_bdy = api_client.send_request(path=path, method='get', headers=headers)
                res_bdy = res_bdy.json()
                if res_bdy:
                    response_body = {}
                    res_list = [i for i in res_bdy["data"]]
                    response_body.update({"data": res_list})
                    return {'payload': json.dumps(json_sanitizer(response_body)), 'status': 200}
                else:
                    raise FetchDestinationException(error_code=res_bdy.status_code,
                                                    error_msg='Failed to fetch destination lists. '
                                                              'Please check Umbrella API settings.')
        except ReportingAPIClientException as e:
            Logger().error("API: fetch_destination_lists, Exception : {0}".format(str(e.error_msg)))
            return {'payload': {"message": str(e.error_msg)}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: fetch_destination_lists, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
