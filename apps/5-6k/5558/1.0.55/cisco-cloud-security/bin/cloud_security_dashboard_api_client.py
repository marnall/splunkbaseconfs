# encoding = utf-8
from __future__ import print_function

import sys
import math
import json
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from exceptions import ReportingAPIClientException, UmbrellaDashboardAPIClientException
from enums import CloudSecurityAPIEndpoints
from reporting_api_client import ReportingAPIClient
from service.app_kvstore_service import KVStoreService
from global_org_client import GlobalOrgClient

sys.path.append(dirname(abspath(__file__)))


class CloudSecurityDashboardAPIClient(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        """This is constructor of class UmbrellaDashboardAPIClient."""

        PersistentServerConnectionApplication.__init__(self)
        self.reporting_api_client_inst = None
        self.session_token = None
        self.global_org_client = None

    def create_chuncks(self, lst, n):
        """This method is used to create chunks of n size from given lst"""

        if n == 0:
            return []

        chunks_list = []
        for i in range(0, len(lst), n):
            chunks_list.append(lst[i:i + n])
        return chunks_list

    def process_trend_response(self, data, span, field):
        """This method is used to process the received data and form a response in required format."""

        rsp = []
        # if len(data) > 1:
        #     diff = data[1][0]['timestamp'] - data[0][0]['timestamp']
        #     span = round(diff / 1000)

        for chunk in data:
            # NOTE: removed logic of summing counts as per yaron's input given on 12 sept 2023
            # requests_list = []
            #
            # for ele in chunk:
            #     requests_list.append(ele['counts'][field])
            #
            # requests_count = sum(requests_list)

            rsp.append({"label": chunk[0]['date'] + " " + chunk[0]['time'],
                        "value": chunk[0]['counts'][field],
                        "_span": span})

        return rsp

    def fetch_result(self, from_timestamp, to_timestamp):
        """This method is used to fetch the result from umbrella dns."""

        response = {}
        time_range = "hour"
        span = 3600
        tz = self.fetch_timezone()
        # if greater than 24 hours
        if (int(to_timestamp) - int(from_timestamp)) > 86400000:
            time_range = "day"
            span = 86400
        # if less than or equal to 1 hour
        elif (int(to_timestamp) - int(from_timestamp)) <= 3600000:
            time_range = "minute"
            span = 60

        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x',
                   'timerange': time_range}

        total_requests_path = CloudSecurityAPIEndpoints.TOTAL_REQUESTS_TREND.value \
            .format(from_timestamp, to_timestamp, tz)
        security_requests_path = CloudSecurityAPIEndpoints.SECURITY_REQUESTS_TREND.value \
            .format(from_timestamp, to_timestamp, tz)

        total_requests_trend = self.send_request(total_requests_path, headers)
        rsp = total_requests_trend.json()['data']
        chunks = self.create_chuncks(rsp, math.ceil(len(rsp) / 10))
        total_requests_trend_res = self.process_trend_response(chunks, span, "requests")
        blocked_requests_trend_res = self.process_trend_response(chunks, span, "blockedrequests")

        security_requests_trend = self.send_request(security_requests_path, headers)
        rsp = security_requests_trend.json()['data']
        chunks = self.create_chuncks(rsp, math.ceil(len(rsp) / 10))
        security_requests_trend_res = self.process_trend_response(chunks, span, "blockedrequests")

        response['totalrequesttrend'] = total_requests_trend_res
        response['totalblocktrend'] = blocked_requests_trend_res
        response['totalsecurityblocktrend'] = security_requests_trend_res
        return response

    def send_request(self, path, headers):
        """This is helper method to send request to reporting API using reporting_api_client and fetch response."""

        return self.reporting_api_client_inst.send_request(path, 'get', headers=headers)

    def fetch_timezone(self):
        """This method is used to fetch the timezone from kv store"""

        tz = 'UTC'
        oauth_settings = KVStoreService('oauth_settings', self.session_token)
        oauth_settings = json.loads(
            oauth_settings.query_items(
                "oauth_settings",
                self.session_token,
                query_conditions={
                    "status": "active",
                    "orgId": self.global_org_client.global_org,
                },
            )
        )
        if len(oauth_settings) == 0:
            Logger().error("timezone setting not found!")
        else:
            oauth_settings = oauth_settings[-1]
            tz = oauth_settings['timezone']

        return tz

    def handle(self, in_string):
        """This is cloud_security_dashboard_api_client handler."""

        try:
            params = Common().parse_in_string(in_string)
            self.session_token = params['session']['authtoken']
            self.reporting_api_client_inst = ReportingAPIClient(self.session_token)
            self.global_org_client = GlobalOrgClient(self.session_token)
            from_timestamp = params["query"]['from']
            to_timestamp = params["query"]['to']
            result = self.fetch_result(from_timestamp, to_timestamp)
            return {"payload": result, "status": 200}
        except ReportingAPIClientException as e:
            Logger().error("API: reporting_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: cloud_security_dashboard_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": str(e)}, "status": 500}
