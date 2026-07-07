# encoding = utf-8
from __future__ import print_function

import sys
import math
import json
import concurrent.futures
from datetime import datetime
from pytz import timezone
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from exceptions import ReportingAPIClientException, UmbrellaDashboardAPIClientException
from enums import UmbrellaReportingAPIEndpoints
from reporting_api_client import ReportingAPIClient
from service.app_kvstore_service import KVStoreService
from global_org_client import GlobalOrgClient

sys.path.append(dirname(abspath(__file__)))


class UmbrellaDashboardAPIClient(PersistentServerConnectionApplication):

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

    def process_trend_response(self, data, span):
        """This method is used to process the received data and form a response in required format."""

        rsp = []
        blocktrendcountcurrent = [{"value": 0}]
        blocktrendcountprevious = [{"value": 0}]

        # if len(data) > 1:
        #     diff = data[1][0]['timestamp'] - data[0][0]['timestamp']
        #     span = round(diff / 1000)

        for chunk in data:
            # NOTE: removed logic of summing counts as per yaron's input given on 12 sept 2023
            # allowedrequests_list = []
            # blockedrequests_list = []
            #
            # for ele in chunk:
            #     allowedrequests_list.append(ele['counts']['allowedrequests'])
            #     blockedrequests_list.append(ele['counts']['blockedrequests'])
            #
            # allowedrequests_count = sum(allowedrequests_list)
            # blockedrequests_count = sum(blockedrequests_list)

            rsp.append({"label": chunk[0]['date'] + " " + chunk[0]['time'],
                        "value1": chunk[0]['counts']['allowedrequests'],
                        "value2": chunk[0]['counts']['blockedrequests'],
                        "_span": span})

        if len(rsp) == 1:
            blocktrendcountcurrent = rsp[0]['value2']
            blocktrendcountprevious = rsp[0]['value2']
        elif len(rsp) > 1:
            blocktrendcountcurrent = rsp[len(rsp) - 1]['value2']
            blocktrendcountprevious = rsp[len(rsp) - 2]['value2']

        return rsp, blocktrendcountcurrent, blocktrendcountprevious

    def fetch_result(self, query, from_timestamp, to_timestamp):
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

        difference = int(to_timestamp) - int(from_timestamp)
        prev_from_timestamp = int(from_timestamp) - difference

        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x',
                   'timerange': time_range}

        overall_requests_path = UmbrellaReportingAPIEndpoints.TOTAL_REQUESTS.value \
            .format(query, from_timestamp, to_timestamp, tz)
        trend_path = UmbrellaReportingAPIEndpoints.REQUESTS_BY_TIME_RANGE.value \
            .format(query, from_timestamp, to_timestamp, tz)
        blocked_category_path = UmbrellaReportingAPIEndpoints.TOP_CATEGORIES.value \
            .format(query, from_timestamp, to_timestamp, tz)
        total_blocked_request_current = UmbrellaReportingAPIEndpoints.TOTAL_BLOCKED_REQUESTS.value \
            .format(query, from_timestamp, to_timestamp, tz)
        total_blocked_request_previous = UmbrellaReportingAPIEndpoints.TOTAL_BLOCKED_REQUESTS.value \
            .format(query, str(prev_from_timestamp), from_timestamp, tz)

        # overall requests count
        overall_requests_res = self.send_request(overall_requests_path, headers)
        if query == 'dns':
            response['dnsoverallrequests'] = [{"value": overall_requests_res.json()['data']['count']}]
        elif query == 'proxy':
            response['swgtotalrequest'] = [{"value": overall_requests_res.json()['data']['count']}]
        elif query == "firewall":
            response['cdfwtotalrequest'] = [{"value": overall_requests_res.json()['data']['count']}]
        elif query == 'ztna':
            response['ztnatotalrequest'] = [{"value": overall_requests_res.json()['data']['count']}]
        total_blocked_current = self.send_request(total_blocked_request_current, headers)
        total_blocked_previous = self.send_request(total_blocked_request_previous, headers)

        # trend
        trend_res = self.send_request(trend_path, headers)
        rsp = trend_res.json()['data']
        block_trend_rsp = []
        for ele in rsp:
            block_trend_rsp.append({"label": ele['date'] + " " + ele['time'],
                                    "value": ele['counts']['blockedrequests'],
                                    "_span": span})
        chunks = self.create_chuncks(rsp, math.ceil(len(rsp) / 10))
        trend_rsp, current_count, previous_count = self.process_trend_response(
            chunks, span)

        total_blocked_count_current = total_blocked_current.json()['data']['count']
        total_blocked_count_previous = total_blocked_previous.json()['data']['count']

        if query == 'dns':
            response['dnsblocktrend'] = block_trend_rsp
            response['dnsblocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
            response['dnsblocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
            response['dnsblockedvsalloweddestination'] = trend_rsp
        elif query == 'proxy':
            response['swgblocktrend'] = block_trend_rsp
            response['swgblocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
            response['swgblocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
            response['swgblockedvsalloweddestination'] = trend_rsp
        elif query == 'firewall':
            response['cdfwblocktrend'] = block_trend_rsp
            response['cdfwblocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
            response['cdfwblocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
            response['cdfwblockedvsalloweddestination'] = trend_rsp
        elif query == 'ztna':
            response['ztnablocktrend'] = block_trend_rsp
            response['ztnablocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
            response['ztnablocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
            response['ztnablockedvsalloweddestination'] = trend_rsp
        # top blocked category
        if query != 'firewall' and query != 'ztna':
            blocked_category_res = self.send_request(blocked_category_path, headers)
            res = []
            for ele in blocked_category_res.json()['data'][:10]:
                res.append({"label": ele['category']['label'], "value": ele['count']})
            if query == 'dns':
                response['dnsblockeddnsategory'] = res
            elif query == 'proxy':
                response['swgtopblockeddnscategory'] = res

        return response

    def convert_timestamp_to_gmt(self, timestamp):
        """This method is used to convert system timestamp into GMT timestamp."""

        # step1- convert epoch to date time and it will give system date time
        date_time = datetime.fromtimestamp(float(timestamp) / 1000)

        # step2- convert system date time to GMT date time
        gmt_date_time = date_time.astimezone(timezone('GMT'))

        # step3- convert GMT date time to epoch
        epoch = datetime(gmt_date_time.year, gmt_date_time.month, gmt_date_time.day,
                         gmt_date_time.hour, gmt_date_time.minute, gmt_date_time.second).timestamp()

        # step4- convert seconds epoch to milliseconds
        epoch_in_ms = int(epoch) * 1000

        # step5- calculate diff between system epoch and GMT epoch
        diff = int(timestamp) - epoch_in_ms

        # step6- add diff into system epoch
        return int(timestamp) + diff

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
        """This is umbrella_dashboard_api_client handler."""

        try:
            params = Common().parse_in_string(in_string)
            self.session_token = params['session']['authtoken']
            self.reporting_api_client_inst = ReportingAPIClient(self.session_token)
            self.global_org_client = GlobalOrgClient(self.session_token)
            from_timestamp = params["query"]['from']
            to_timestamp = params["query"]['to']
            if params["query"]['type'] == 'dns':
                result = self.fetch_result('dns', from_timestamp, to_timestamp)
                return {"payload": result, "status": 200}
            elif params["query"]['type'] == 'swg':
                result = self.fetch_result('proxy', from_timestamp, to_timestamp)
                return {"payload": result, "status": 200}
            elif params["query"]['type'] == 'cdfw':
                result = self.fetch_result('firewall', from_timestamp, to_timestamp)
                return {"payload": result, "status": 200}
            elif params["query"]['type'] == 'ztna':
                result = self.fetch_result('ztna', from_timestamp, to_timestamp)
                return {"payload": result, "status": 200}
            else:
                raise Exception('Invalid panel type!')
        except ReportingAPIClientException as e:
            Logger().error("API: reporting_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: umbrella_dashboard_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": str(e)}, "status": 500}


# # encoding = utf-8
# from __future__ import print_function

# import sys
# import math
# import json
# import concurrent.futures
# from datetime import datetime
# from pytz import timezone
# from os.path import dirname, abspath
# sys.path.append(dirname(abspath(__file__)))
# import os
# from splunk.persistconn.application import PersistentServerConnectionApplication
# from logger import Logger
# from common import Common
# from exceptions import ReportingAPIClientException, UmbrellaDashboardAPIClientException
# from enums import UmbrellaReportingAPIEndpoints
# from reporting_api_client import ReportingAPIClient
# from service.app_kvstore_service import KVStoreService

# sys.path.append(dirname(abspath(__file__)))


# class UmbrellaDashboardAPIClient(PersistentServerConnectionApplication):

#     def __init__(self, command_line, command_arg):
#         """This is constructor of class UmbrellaDashboardAPIClient."""

#         PersistentServerConnectionApplication.__init__(self)
#         self.reporting_api_client_inst = None
#         self.session_token = None

#     def create_chuncks(self, lst, n):
#         """This method is used to create chunks of n size from given lst"""

#         if n == 0:
#             return []

#         chunks_list = []
#         for i in range(0, len(lst), n):
#             chunks_list.append(lst[i:i + n])
#         return chunks_list

#     def process_trend_response(self, data, span):
#         """This method is used to process the received data and form a response in required format."""

#         rsp = []
#         blocktrendcountcurrent = [{"value": 0}]
#         blocktrendcountprevious = [{"value": 0}]

#         # if len(data) > 1:
#         #     diff = data[1][0]['timestamp'] - data[0][0]['timestamp']
#         #     span = round(diff / 1000)

#         for chunk in data:
#             # NOTE: removed logic of summing counts as per yaron's input given on 12 sept 2023
#             # allowedrequests_list = []
#             # blockedrequests_list = []
#             #
#             # for ele in chunk:
#             #     allowedrequests_list.append(ele['counts']['allowedrequests'])
#             #     blockedrequests_list.append(ele['counts']['blockedrequests'])
#             #
#             # allowedrequests_count = sum(allowedrequests_list)
#             # blockedrequests_count = sum(blockedrequests_list)

#             rsp.append({"label": chunk[0]['date'] + " " + chunk[0]['time'],
#                         "value1": chunk[0]['counts']['allowedrequests'],
#                         "value2": chunk[0]['counts']['blockedrequests'],
#                         "_span": span})

#         if len(rsp) == 1:
#             blocktrendcountcurrent = rsp[0]['value2']
#             blocktrendcountprevious = rsp[0]['value2']
#         elif len(rsp) > 1:
#             blocktrendcountcurrent = rsp[len(rsp) - 1]['value2']
#             blocktrendcountprevious = rsp[len(rsp) - 2]['value2']

#         return rsp, blocktrendcountcurrent, blocktrendcountprevious

#     def fetch_result(self, query, from_timestamp, to_timestamp):
#         """This method is used to fetch the result from umbrella dns."""

#         response = {}
#         time_range = "hour"
#         span = 3600
#         tz = self.fetch_timezone()
#         # if greater than 24 hours
#         if (int(to_timestamp) - int(from_timestamp)) > 86400000:
#             time_range = "day"
#             span = 86400
#         # if less than or equal to 1 hour
#         elif (int(to_timestamp) - int(from_timestamp)) <= 3600000:
#             time_range = "minute"
#             span = 60

#         difference = int(to_timestamp) - int(from_timestamp)
#         prev_from_timestamp = int(from_timestamp) - difference

#         headers = {'Content-Type': 'application/json',
#                 'Accept': 'application/json',
#                 'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x',
#                 'timerange': time_range}

#         overall_requests_path = UmbrellaReportingAPIEndpoints.TOTAL_REQUESTS.value \
#             .format(query, from_timestamp, to_timestamp, tz)
#         trend_path = UmbrellaReportingAPIEndpoints.REQUESTS_BY_TIME_RANGE.value \
#             .format(query, from_timestamp, to_timestamp, tz)
#         blocked_category_path = UmbrellaReportingAPIEndpoints.TOP_CATEGORIES.value \
#             .format(query, from_timestamp, to_timestamp, tz)
#         total_blocked_request_current = UmbrellaReportingAPIEndpoints.TOTAL_BLOCKED_REQUESTS.value \
#             .format(query, from_timestamp, to_timestamp, tz)
#         total_blocked_request_previous = UmbrellaReportingAPIEndpoints.TOTAL_BLOCKED_REQUESTS.value \
#             .format(query, str(prev_from_timestamp), from_timestamp, tz)

#         # overall requests count
#         overall_requests_res = self.send_request(overall_requests_path, headers)
#         if query == 'dns':
#             response['dnsoverallrequests'] = [{"value": overall_requests_res.json()['data']['count']}]
#         elif query == 'proxy':
#             response['swgtotalrequest'] = [{"value": overall_requests_res.json()['data']['count']}]
#         elif query == 'firewall':
#             response['cdfwtotalrequest'] = [{"value": overall_requests_res.json()['data']['count']}]
#         elif query == 'ztna':
#             response['ztnatotalrequest'] = [{"value": overall_requests_res.json()['data']['count']}]

#         total_blocked_current = self.send_request(total_blocked_request_current, headers)
#         total_blocked_previous = self.send_request(total_blocked_request_previous, headers)

#         # trend
#         trend_res = self.send_request(trend_path, headers)
#         rsp = trend_res.json()['data']
#         block_trend_rsp = []
#         for ele in rsp:
#             block_trend_rsp.append({"label": ele['date'] + " " + ele['time'],
#                                     "value": ele['counts']['blockedrequests'],
#                                     "_span": span})
#         chunks = self.create_chuncks(rsp, math.ceil(len(rsp) / 10))
#         trend_rsp, current_count, previous_count = self.process_trend_response(
#             chunks, span)

#         total_blocked_count_current = total_blocked_current.json()['data']['count']
#         total_blocked_count_previous = total_blocked_previous.json()['data']['count']

#         if query == 'dns':
#             response['dnsblocktrend'] = block_trend_rsp
#             response['dnsblocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
#             response['dnsblocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
#             response['dnsblockedvsalloweddestination'] = trend_rsp
#         elif query == 'proxy':
#             response['swgblocktrend'] = block_trend_rsp
#             response['swgblocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
#             response['swgblocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
#             response['swgblockedvsalloweddestination'] = trend_rsp
#         elif query == 'firewall':
#             response['cdfwblocktrend'] = block_trend_rsp
#             response['cdfwblocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
#             response['cdfwblocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
#             response['cdfwblockedvsalloweddestination'] = trend_rsp
#         elif query == 'ztna':
#             response['ztnablocktrend'] = block_trend_rsp
#             response['ztnablocktrendcountcurrent'] = [{"value": total_blocked_count_current}]
#             response['ztnablocktrendcountprevious'] = [{"value": total_blocked_count_previous}]
#             response['ztnablockedvsalloweddestination'] = trend_rsp

#         # top blocked category
#         if query != 'firewall' and query != "ztna":
#             a=10
#             blocked_category_res = self.send_request(blocked_category_path, headers)
#             b=20
#             res = []
#             for ele in blocked_category_res.json()['data'][:10]:
#                 res.append({"label": ele['category']['label'], "value": ele['count']})
#             if query == 'dns':
#                 response['dnsblockeddnsategory'] = res
#             elif query == 'proxy':
#                 response['swgtopblockeddnscategory'] = res

#         # path_list = [overall_requests_path, trend_path, blocked_category_path]
#         # if query == 'firewall':
#         #     path_list = [overall_requests_path, trend_path]
#         # response = {}

#         # # concurrent API calls
#         # with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
#         #     future_collection = {executor.submit(self.send_request, path, headers):
#         #                          path for path in path_list}
#         #     for future in concurrent.futures.as_completed(future_collection):
#         #         path = future_collection[future]
#         #         data = future.result()
#         #         if path == overall_requests_path:
#         #             rsp = [{"value": data.json()['data']['count']}]
#         #             if query == 'dns':
#         #                 response['dnsoverallrequests'] = rsp
#         #             elif query == 'proxy':
#         #                 response['swgtotalrequest'] = rsp
#         #             else:
#         #                 response['cdfwtotalrequest'] = rsp
#         #         if path == trend_path:
#         #             rsp = data.json()['data']
#         #             block_trend_rsp = []
#         #             for ele in rsp:
#         #                 block_trend_rsp.append({"label": ele['date']+" "+ele['time'],
#         #                                         "value": ele['counts']['blockedrequests'],
#         #                                         "_span": span})
#         #             chunks = self.create_chuncks(rsp, math.ceil(len(rsp) / 10))
#         #             trend_rsp, current_count, previous_count = self.process_trend_response(
#         #                 chunks, span)
#         #
#         #             if query == 'dns':
#         #                 response['dnsblocktrend'] = block_trend_rsp
#         #                 response['dnsblocktrendcountcurrent'] = [{"value": current_count}]
#         #                 response['dnsblocktrendcountprevious'] = [{"value": previous_count}]
#         #                 response['dnsblockedvsalloweddestination'] = trend_rsp
#         #             elif query == 'proxy':
#         #                 response['swgblocktrend'] = block_trend_rsp
#         #                 response['swgblocktrendcountcurrent'] = [{"value": current_count}]
#         #                 response['swgblocktrendcountprevious'] = [{"value": previous_count}]
#         #                 response['swgblockedvsalloweddestination'] = trend_rsp
#         #             else:
#         #                 response['cdfwblocktrend'] = block_trend_rsp
#         #                 response['cdfwblocktrendcountcurrent'] = [{"value": current_count}]
#         #                 response['cdfwblocktrendcountprevious'] = [{"value": previous_count}]
#         #                 response['cdfwblockedvsalloweddestination'] = trend_rsp
#         #         if path == blocked_category_path:
#         #             rsp = []
#         #             for ele in data.json()['data'][:10]:
#         #                 rsp.append({"label": ele['category']['label'], "value": ele['count']})
#         #             if query == 'dns':
#         #                 response['dnsblockeddnsategory'] = rsp
#         #             elif query == 'proxy':
#         #                 response['swgtopblockeddnscategory'] = rsp

#         return response

#     def convert_timestamp_to_gmt(self, timestamp):
#         """This method is used to convert system timestamp into GMT timestamp."""

#         # step1- convert epoch to date time and it will give system date time
#         date_time = datetime.fromtimestamp(float(timestamp) / 1000)

#         # step2- convert system date time to GMT date time
#         gmt_date_time = date_time.astimezone(timezone('GMT'))

#         # step3- convert GMT date time to epoch
#         epoch = datetime(gmt_date_time.year, gmt_date_time.month, gmt_date_time.day,
#                          gmt_date_time.hour, gmt_date_time.minute, gmt_date_time.second).timestamp()

#         # step4- convert seconds epoch to milliseconds
#         epoch_in_ms = int(epoch) * 1000

#         # step5- calculate diff between system epoch and GMT epoch
#         diff = int(timestamp) - epoch_in_ms

#         # step6- add diff into system epoch
#         return int(timestamp) + diff

#     def send_request(self, path, headers):
#         """This is helper method to send request to reporting API using reporting_api_client and fetch response."""
#         # return self.reporting_api_client_inst.send_request(path, 'get', headers=headers)

#         return self.reporting_api_client_inst.send_request(path, 'get', headers=headers)

#     def fetch_timezone(self):
#         """This method is used to fetch the timezone from kv store"""

#         tz = 'UTC'
#         oauth_settings = KVStoreService('oauth_settings', self.session_token)
#         oauth_settings = json.loads(oauth_settings.query_items('oauth_settings', self.session_token,
#                                                                query_conditions={"status": "active"}))
#         if len(oauth_settings) == 0:
#             Logger().error("timezone setting not found!")
#         else:
#             oauth_settings = oauth_settings[-1]
#             tz = oauth_settings['timezone']

#         return tz

#     def handle(self, in_string):
#         """This is umbrella_dashboard_api_client handler."""

#         try:
#             params = Common().parse_in_string(in_string)
#             print(params,"ssssssssssssssss")
#             self.session_token = params['session']['authtoken']
#             self.reporting_api_client_inst = ReportingAPIClient(self.session_token)
#             from_timestamp = params["query"]['from']
#             to_timestamp = params["query"]['to']
#             if params["query"]['type'] == 'dns':
#                 result = self.fetch_result('dns', from_timestamp, to_timestamp)
#                 return {"payload": result, "status": 200}
#             elif params["query"]['type'] == 'swg':
#                 result = self.fetch_result('proxy', from_timestamp, to_timestamp)
#                 return {"payload": result, "status": 200}
#             elif params["query"]['type'] == 'cdfw':
#                 result = self.fetch_result('firewall', from_timestamp, to_timestamp)
#                 return {"payload": result, "status": 200}
#             elif params["query"]['type'] == 'ztna':
#                 result = self.fetch_result('ztna', from_timestamp, to_timestamp)
#                 return {"payload": result, "status": 200}
#             else:
#                 raise Exception(f'{params} Invalid panel type!')
#         except ReportingAPIClientException as e:
#             Logger().error("API: reporting_api_client, Exception : {0}".format(str(e)))
#             return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
#         except Exception as e:
#             Logger().error("API: umbrella_dashboard_api_client, Exception : {0}".format(str(e)))
#             return {"payload": {"error_msg": str(e)}, "status": 500}
