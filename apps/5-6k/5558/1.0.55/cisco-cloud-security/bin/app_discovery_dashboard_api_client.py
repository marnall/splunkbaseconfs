# encoding = utf-8
from __future__ import print_function

import sys
import json
from datetime import datetime
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
import urllib.parse

from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from exceptions import ReportingAPIClientException
from enums import AppDiscoveryAPIEndpoints
from reporting_api_client import ReportingAPIClient
from service.app_kvstore_service import KVStoreService
from global_org_client import GlobalOrgClient

sys.path.append(dirname(abspath(__file__)))


class AppDiscoveryDashboardAPIClient(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        """This is constructor of class UmbrellaDashboardAPIClient."""

        PersistentServerConnectionApplication.__init__(self)
        self.reporting_api_client_inst = None
        self.session_token = None
        self.global_org_client = None

    def fetch_result(self, query, limit=10, page_no=0, app_id=None, sort='weightedRisk', order='desc', search_param=None, label=None):
        """This method is used to fetch the result for app discovery API."""

        response = []
        offset = page_no * limit
        tz = self.fetch_timezone()
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}

        if query == 'getCount':
            total_count = AppDiscoveryAPIEndpoints.TOTAL_COUNT.value
            rsp = self.send_request(total_count, headers)
            Logger().info("{0} applications discovered on {1}".format(str(rsp.json()['discovered_apps_count']),
                                                                      datetime.now()))
            response = [{"value": rsp.json()['discovered_apps_count']}]
        elif query == 'getSearchCount':
            search_count = AppDiscoveryAPIEndpoints.SEARCH_APP_COUNT.value.format(tz, search_param)
            rsp = self.send_request(search_count, headers)
            total_app_count = len(rsp.json()["items"])
            Logger().info("{0} applications discovered on {1}".format(total_app_count, datetime.now()))
            response = [{"value": total_app_count}]
        elif query == 'listApplications':
            applications = AppDiscoveryAPIEndpoints.LIST_APPLICATIONS.value.format(limit, offset, tz, sort, order)
            rsp = self.send_request(applications, headers)
            for i in rsp.json()['items']:
                response.append({
                    "id": i['id'],
                    "name": i['name'],
                    "label": i['label'],
                    "weightedRisk": i['weightedRisk'],
                    "category": i['category'],
                    "appType": i['appType'],
                    "dnsRequests": i['sources'][2]['requests'],
                    "dnsBlockedRequests": i['sources'][2]['blockedRequests'],
                    "totalWebTraffic": i['sources'][1]['totalTraffic'],
                    "blockedWebTraffic": i['sources'][1]['blockedBytesOut'],
                    "firewallEvents": i['sources'][0]['events'],
                    "blockedFirewallEvents": i['sources'][0]['blockedEvents'],
                    "firstDetected": i['firstDetected'],
                    "lastDetected": i['lastDetected']
                })
        elif query == 'getAppDetails':
            app_details = AppDiscoveryAPIEndpoints.GET_APP_DETAILS.value.format(app_id, tz)
            rsp = self.send_request(app_details, headers)
            rsp = rsp.json()
            response.append({
                "id": rsp['id'],
                "name": rsp['name'],
                "label": rsp['label'],
                "weightedRisk": rsp['weightedRisk'],
                "category": rsp['category'],
                "appType": rsp['appType'],
                "dnsRequests": rsp['sources'][2]['requests'],
                "dnsBlockedRequests": rsp['sources'][2]['blockedRequests'],
                "totalWebTraffic": rsp['sources'][1]['totalTraffic'],
                "blockedWebTraffic": rsp['sources'][1]['blockedBytesOut'],
                "firewallEvents": rsp['sources'][0]['events'],
                "blockedFirewallEvents": rsp['sources'][0]['blockedEvents'],
                "firstDetected": rsp['firstDetected'],
                "lastDetected": rsp['lastDetected'],
                "description": rsp['description'],
                "url": rsp['url'],
                "vendor": rsp['vendor'],
                "identitiesCount": rsp['identitiesCount']
            })
        elif query == 'getAppIdentities':
            app_identities = AppDiscoveryAPIEndpoints.GET_APP_IDENTITIES.value.format(app_id, limit, offset, tz)
            rsp = self.send_request(app_identities, headers)
            for i in rsp.json()['items']:
                response.append({
                    "id": i['id'],
                    "name": i['name'],
                    "dnsRequests": i['sources'][2]['requests'],
                    "dnsBlockedRequests": i['sources'][2]['blockedRequests'],
                    "totalWebTraffic": i['sources'][1]['totalTraffic'],
                    "blockedWebTraffic": i['sources'][1]['blockedBytesOut'],
                    "firewallEvents": i['sources'][0]['events'],
                    "blockedFirewallEvents": i['sources'][0]['blockedEvents'],
                    "firstDetected": i['firstDetected'],
                    "lastDetected": i['lastDetected']
                })
        elif query == "searchAppByParameter":
            applications = AppDiscoveryAPIEndpoints.LIST_APPLICATIONS.value.format(limit, offset, tz, sort, order)
            if search_param:
                applications = f"{applications}&{search_param}"
            rsp = self.send_request(applications, headers)
            for i in rsp.json()['items']:
                response.append({
                    "id": i['id'],
                    "name": i['name'],
                    "label": i['label'],
                    "weightedRisk": i['weightedRisk'],
                    "category": i['category'],
                    "appType": i['appType'],
                    "dnsRequests": i['sources'][2]['requests'],
                    "dnsBlockedRequests": i['sources'][2]['blockedRequests'],
                    "totalWebTraffic": i['sources'][1]['totalTraffic'],
                    "blockedWebTraffic": i['sources'][1]['blockedBytesOut'],
                    "firewallEvents": i['sources'][0]['events'],
                    "blockedFirewallEvents": i['sources'][0]['blockedEvents'],
                    "firstDetected": i['firstDetected'],
                    "lastDetected": i['lastDetected']
                })
        elif query == "changeAppLabel":
            applications = AppDiscoveryAPIEndpoints.CHANGE_APP_LABLE.value.format(app_id)
            payload = { "label": label }
            response = self.send_patch_request(applications, headers=headers, payload=payload).json()

        return response

    def send_patch_request(self, path, headers, payload):
        """This is helper method to send request to reporting API using reporting_api_client and fetch response."""

        return self.reporting_api_client_inst.send_request(path, 'patch', headers=headers, payload=json.dumps(payload))

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
            response = []
            params = Common().parse_in_string(in_string)
            self.session_token = params['session']['authtoken']
            self.reporting_api_client_inst = ReportingAPIClient(self.session_token)
            self.global_org_client = GlobalOrgClient(self.session_token)
            query = params["query"]['query']
            if query == "getCount":
                response = self.fetch_result(query)
            elif query == "getSearchCount":
                search_param = params["query"]['search_param']
                if not search_param:
                    raise Exception('search parameter is required')
                if 'weightedRisk' in search_param or 'labels' in search_param:
                    param = search_param.split('=')
                    search_param = param[1].split()
                    if len(search_param)==1:
                        search_param = param[0]+'='+search_param[0].lower()
                    else:
                        # convert to camel case
                        search_param = param[0]+'='+search_param[0].lower() + ''.join(search_param.capitalize() for search_param in search_param[1:])
                search_param = search_param.split("=")[0]+'='+urllib.parse.quote(search_param.split("=")[1])
                Logger().error("appdicovery search_param : {0}".format(search_param))
                response = self.fetch_result(query, search_param=search_param)
            elif query == "listApplications":
                limit = int(params["query"]['limit'])
                page_no = int(params["query"]['page']) - 1
                sort = params["query"]['sort']
                if sort and sort != 'weightedRisk' and sort != 'firstDetected':
                    raise Exception('Invalid sort value! Expected one of ["weightedRisk", "firstDetected"].')
                order = params["query"]['order']
                if order and order != 'asc' and order != 'desc':
                    raise Exception('Invalid order value! Expected one of ["asc", "desc"].')
                response = self.fetch_result(query, limit=limit, page_no=page_no, sort=sort, order=order)
            elif query == "getAppDetails":
                app_id = params["query"]['appId']
                response = self.fetch_result(query, app_id=app_id)
            elif query == "getAppIdentities":
                limit = int(params["query"]['limit'])
                page_no = int(params["query"]['page']) - 1
                app_id = params["query"]['appId']
                response = self.fetch_result(query, limit=limit, page_no=page_no, app_id=app_id)
            elif query == "searchAppByParameter":
                limit = int(params["query"]['limit'])
                page_no = int(params["query"]['page']) - 1
                search_param = params["query"]['search_param']
                if not search_param:
                    raise Exception('search parameter is required')
                if 'weightedRisk' in search_param or 'labels' in search_param:
                    param = search_param.split('=')
                    search_param = param[1].split()
                    if len(search_param)==1:
                        search_param = param[0]+'='+search_param[0].lower()
                    else:
                        # convert to camel case
                        search_param = param[0]+'='+search_param[0].lower() + ''.join(search_param.capitalize() for search_param in search_param[1:])
                search_param = search_param.split("=")[0]+'='+urllib.parse.quote(search_param.split("=")[1])
                response = self.fetch_result(query, limit=limit, page_no=page_no, search_param=search_param)
            elif query == "changeAppLabel":
                app_id = params["query"]['appId']
                label = params["query"]['label']
                if not label:
                    raise Exception ("label data is required")
                response = self.fetch_result(query, app_id=app_id, label=label)
            else:
                raise Exception('Invalid query! Expected one of ["getCount", "listApplications", '
                                '"getAppDetails", "getAppIdentities", "searchAppByParameter", "changeAppLabel"].')
            return {"payload": response, "status": 200}
        except ReportingAPIClientException as e:
            Logger().error("API: reporting_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: app_discovery_dashboard_api_client, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": str(e)}, "status": 500}
