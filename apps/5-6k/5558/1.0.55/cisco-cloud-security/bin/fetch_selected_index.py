# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import requests
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from global_org_client import GlobalOrgClient

cloudlock_index = None
s3_indexes = None
investigate_settings = None
appdiscovery_index = None
privateapp_index = None
alerts_index = None

class FetchSelectedIndex(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            response = dict()
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            endpoint = params["rest_path"].split('/')[-1]
            self.global_org_client = GlobalOrgClient(session_token)
            if endpoint == 'cloudlock_index':
                global cloudlock_index
                if not cloudlock_index:
                    cloudlock_index = KVStoreService('cloudlock_index', session_token)
                cloudlock_index_data = json.loads(cloudlock_index.query_items('cloudlock_index', session_token))
                if len(cloudlock_index_data) == 0:
                    raise Exception('Index for cloudlock is not selected')
                else:
                    response = cloudlock_index_data[-1]
            elif endpoint == 'investigate_index':
                global investigate_settings
                if not investigate_settings:
                    investigate_settings = KVStoreService('investigate_settings', session_token)
                investigate_settings_data = json.loads(
                    investigate_settings.query_items(
                        "investigate_settings",
                        session_token,
                        {"orgId": self.global_org_client.global_org},
                    )
                )
                if len(investigate_settings_data) == 0:
                    raise Exception('Investigate index is not configured')
                investigate_index = None
                for obj in investigate_settings_data:
                    if obj['status'] == 'active':
                        investigate_index = obj['index']
                        response.update({'investigate_index':investigate_index})
                        break
                if not investigate_index:
                    raise Exception('Investigate index is not configured')
            elif endpoint == 'appdiscovery_index':
                global appdiscovery_index
                if not appdiscovery_index:
                    appdiscovery_index = KVStoreService('appdiscovery_index', session_token)
                appdiscovery_index_data = json.loads(
                    appdiscovery_index.query_items(
                        "appdiscovery_index",
                        session_token,
                        {"orgId": self.global_org_client.global_org},
                    )
                )
                if len(appdiscovery_index_data) == 0:
                    raise Exception('Index for App Discovery is not selected')
                else:
                    response = appdiscovery_index_data[-1]
            elif endpoint == 's3_indexes':
                global s3_indexes
                if not s3_indexes:
                    s3_indexes = KVStoreService('s3_indexes', session_token)
                s3_indexes_data = json.loads(
                    s3_indexes.query_items(
                        "s3_indexes",
                        session_token,
                        {"orgId": self.global_org_client.global_org},
                    )
                )
                if len(s3_indexes_data) == 0:
                    raise Exception('Indexes for S3 are not selected')
                else:
                    response = s3_indexes_data[-1]
            elif endpoint == 'privateapp_index':
                global privateapp_index
                if not privateapp_index:
                    privateapp_index = KVStoreService('privateapp_index', session_token)
                privateapp_index_data = json.loads(
                    privateapp_index.query_items(
                        "privateapp_index",
                        session_token,
                        {"orgId": self.global_org_client.global_org},
                    )
                )
                if len(privateapp_index_data) == 0:
                    raise Exception('Index for Private Apps is not selected')
                else:
                    response = privateapp_index_data[-1]
            elif endpoint == 'alerts_index':
                global alerts_index
                if not alerts_index:
                    alerts_index = KVStoreService('alerts_index', session_token)
                alerts_index_data = json.loads(
                    alerts_index.query_items(
                        "alerts_index",
                        session_token,
                        {"orgId": self.global_org_client.global_org},
                    )
                )
                if len(alerts_index_data) == 0:
                    raise Exception('Index for Alerts is not configured')
                else:
                    response = alerts_index_data[-1]
            return {'payload': response, 'status': 200}

        except Exception as e:
            Logger().error("API: fetch_selected_index, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
