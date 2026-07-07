import ssl
from datetime import timezone, datetime
import time
import re
import concurrent.futures

from requests.exceptions import SSLError
from solnlib import splunkenv, log
from solnlib.bulletin_rest_client import BulletinRestClient
from splunklib import client
from oauth_helper import OAuth
import requests
import urllib.parse
import json
from ucc_utils import Util
from appdynamics_utils import normalize_controller_url


class ControllerService:
    """
    Client for the AppDynamics Controller API.

    You must supply credentials in exactly one of two ways:

    1) By account name (lookup from Splunk config + credential storage):
       ControllerService(
           session_key=session_key,
           global_account_name="my_account",
           throw_exceptions=True,  # optional
           logger=logger,          # optional
           duration=5,             # optional, minutes
       )

    2) By pre-resolved account dict (e.g. from a modular input that already
       resolved the account and credentials):
       ControllerService(
           session_key=helper.context_meta["session_key"],
           global_account=opt_global_account,  # dict with appd_controller_url, appd_client_name, appd_client_secret
           helper=helper,
           duration=opt_duration,
           source=helper.get_arg('name'),
       )

    :param session_key: Splunk session key (used for config/proxy and for credential lookup when using global_account_name).
    :param global_account_name: Account stanza name; credentials are looked up from Splunk config and storage.
    :param global_account: Pre-resolved dict with keys appd_controller_url, appd_client_name, appd_client_secret (and optionally name).
    :param helper: Optional input helper (used for logger when no logger passed).
    :param duration: Time window in minutes for range queries (default 5).
    :param throw_exceptions: If True, raise on API errors; else log and return None (default False).
    :param source: Source name for bulletin messages (default "appdynamics").
    :param logger: Optional logger; otherwise derived from helper or default.
    """

    def __init__(
        self,
        session_key=None,
        global_account_name=None,
        global_account=None,
        helper=None,
        duration=5,
        throw_exceptions=False,
        source="appdynamics",
        logger=None,
    ):
        if global_account_name is not None and global_account is not None:
            raise ValueError(
                "ControllerService: supply exactly one of global_account_name or global_account, not both"
            )
        if global_account_name is None and global_account is None:
            raise ValueError(
                "ControllerService: must supply either global_account_name (with session_key for lookup) or global_account dict"
            )

        # helper is only used for logger fallback when logger is None; not stored
        if logger is None:
            if helper is None:
                self.logger = log.Logs().get_logger("appdynamics_controller_service")
            else:
                self.logger = helper.logger
        else:
            self.logger = logger
        if session_key is not None:
            self.logger = Util.apply_log_level(session_key, self.logger)

        client_name = ""
        client_secret = ""

        if global_account_name is not None:
            # Look up account from Splunk config and credential storage
            config = splunkenv.get_conf_stanza(
                "splunk_ta_appdynamics_account", global_account_name, Util.get_app_name(), session_key
            )
            self.controller_url = config["appd_controller_url"]
            client_name = config["appd_client_name"]
            service = client.connect(token=session_key, app="Splunk_TA_AppDynamics")
            for storage_password in service.storage_passwords:
                if storage_password.content.get("username", "").startswith(
                    global_account_name + "``splunk_cred_sep``"
                ):
                    clear = storage_password.content.get("clear_password")
                    if clear and "appd_client_secret" in clear:
                        client_secret = json.loads(clear)["appd_client_secret"]
                        break
            account_label = global_account_name
        else:
            # Use pre-resolved account dict (e.g. from modular input)
            self.controller_url = global_account["appd_controller_url"]
            client_name = global_account["appd_client_name"]
            client_secret = global_account["appd_client_secret"]
            account_label = global_account.get("name", "Unknown")
        self.logger.debug(
            "Creating ControllerService with account=%s controller_url=%s client_name=%s client_secret=%s...%s",
            account_label, self.controller_url, client_name,
            client_secret[:4] if client_secret else "", client_secret[-4:] if client_secret else "",
        )
        self.controller_url = normalize_controller_url(self.controller_url)
        self.proxy = Util.get_proxy(session_key)
        self.max_workers = Util.get_max_workers(session_key)
        self.duration = duration

        self.request_timeout = Util.get_timeout(session_key)
        self.verify_ssl = Util.get_verify_ssl(session_key)
        self.auth_handler = OAuth(
            controller_url=self.controller_url,
            client_name=client_name,
            client_secret=client_secret,
            timeout=self.request_timeout,
            proxies=self.proxy,
            verify_ssl=self.verify_ssl,
        )

        now = round(time.time() * 1000)
        self.timeRangeStart = now - (int(duration) * 60000)
        self.timeRangeStart_rfc3339 = datetime.fromtimestamp(self.timeRangeStart / 1000, tz=timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        self.timeRangeEnd = now
        self.timeRangeEnd_rfc3339 = datetime.fromtimestamp(self.timeRangeEnd / 1000, tz=timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        self.throw_exceptions = throw_exceptions
        self._app_baseline_map = {}
        self._session_key = session_key
        self._source = source
        self._message_client = BulletinRestClient(f"{self._source}", self._session_key, app="Splunk_TA_AppDynamics")
        self._cache_app_map = {}
        self._cache_tier_map = {}
        self._cache_component_id_to_tier_name = {}
        self._cache_node_map = {}
        self._date_patterns = {
            "%Y-%m-%dT%H:%M:%S.%fZ" : r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z',
            "%Y-%m-%dT%H:%M:%SZ" : r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',
        }
        self.logger.debug("Initializing ControllerService for {}".format(self.controller_url))

    def get_controller_url(self):
        return self.controller_url

    def _format_time_rfc3339(self, timestamp_ms):
        """Format millisecond timestamp as RFC3339 (e.g. for security API query params)."""
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _request(self, uri, method="GET", json=None, headers=None, ignore_errors=False):
        if headers is None:
            headers={
                "Authorization": f"Bearer {self.auth_handler.get_token()}",
                "Content-Type": "application/json;charset=UTF-8",
                "Accept": "application/json, text/plain, */*"
            }
        try:
            response = None
            if method.upper() == "POST":
                response = requests.post(
                    url=f"{self.controller_url}{uri}",
                    headers=headers,
                    json=json,
                    timeout=float(self.request_timeout),
                    proxies=self.proxy,
                    verify=self.verify_ssl,
                )
            elif method.upper() == "GET":
                response = requests.get(
                    url=f"{self.controller_url}{uri}",
                    headers=headers,
                    timeout=float(self.request_timeout),
                    proxies=self.proxy,
                    verify=self.verify_ssl,
                )
            else:
                raise Exception(f"Invalid Request Method '{method.upper()}'")
            self.logger.debug(f"Request Method '{method}' URL '{response.request.url}' Payload '{response.request.body}' Response: {response.status_code} - {response.text}")
            if not ignore_errors and response.status_code >= 300:
                self.logger.error(f"Error Request URL '{response.request.url}' Payload '{response.request.body}' Response: {response.status_code} - {response.text}")
                if self.throw_exceptions:
                    raise Exception(f"Error Request URL '{response.request.url}' Response: {response.status_code} - {response.text}")
                else:
                    if self._session_key:
                        self._message_client.create_message(
                            f"AppDynamics '{self._source}' Input: Request {response.request.url} failed with status {response.status_code} and message {response.text}",
                            severity=self._message_client.Severity.WARNING
                        )
                return None
            return response.json()
        except SSLError as ssl_error:
            request_url = response.request.url if response is not None and response.request else f"{self.controller_url}{uri}"
            if self._session_key:
                self._message_client.create_message(
                    f"AppDynamics '{self._source}' Input: Request {request_url} failed with an SSL Error '{ssl_error}', here is some helpful hints for troubleshooting SSL here, openssl version: '{ssl.OPENSSL_VERSION}' verify paths: '{ssl.get_default_verify_paths()}' TA verify ssl setting: '{self.verify_ssl}'",
                    severity=self._message_client.Severity.ERROR
                )
            version_string = ""
            try:
                import requests as _r
                import urllib3 as _u
                version_string = f"requests: {_r.__version__}; urllib3: {_u.__version__}"
            except Exception:
                pass
            self.logger.error(f"SSL ERROR Debug: '{ssl_error}' openssl version: '{ssl.OPENSSL_VERSION}' verify paths: '{ssl.get_default_verify_paths()}' {version_string} TA verify ssl setting: '{self.verify_ssl}' url: '{self.controller_url}{uri}'")
            raise ssl_error
        except Exception as exception:
            if self.throw_exceptions:
                raise exception
            else:
                request_url = response.request.url if response is not None and response.request else f"{self.controller_url}{uri}"
                if self._session_key:
                    self._message_client.create_message(
                        f"AppDynamics '{self._source}' Input: Request {request_url} failed with exception {exception}",
                        severity=self._message_client.Severity.WARNING
                    )
        return None


    def testToken(self):
        try:
            bearer_token = self.auth_handler.get_token()
            if bearer_token:
                return True
        except Exception as e:
            self.logger.debug(f"Test Token Error: {e}")
        return False

    def get_all_app_list(self):
        self.logger.debug("Getting list of applications")
        return self._request("/controller/restui/applicationManagerUiBean/getApplicationsAllTypes")

    def get_apm_app_list(self):
        data = self._request(
            method="POST",
            uri="/controller/restui/v1/app/list/all",
            json={
                "requestFilter": {
                    "filters": [{"field": "TYPE", "criteria": "APM", "operator": "EQUAL_TO"}],
                    "filterAll": False,
                    "queryParams": {"applicationIds": [], "tags": []}
                },
                "searchFilters": [],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd,
                "columnSorts": [{"column": "APP_OVERALL_HEALTH", "direction": "DESC"}],
                "resultColumns": ["NAME"],
                "offset": 0,
                "limit": -1
            }
        )
        if data:
            return data['data']
        return None

    def get_application_summary(self, app_list):
        data = self._request(
            method="POST",
            uri="/controller/restui/v1/app/list/ids",
            json={
                "requestFilter": app_list,
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd,
                "searchFilters": None,
                "columnSorts": None,
                "resultColumns": ["APP_OVERALL_HEALTH", "CALLS", "CALLS_PER_MINUTE", "AVERAGE_RESPONSE_TIME",
                                  "ERROR_PERCENT", "ERRORS", "ERRORS_PER_MINUTE", "NODE_HEALTH", "BT_HEALTH"],
                "offset": 0,
                "limit": -1
            }
        )
        if not data or not isinstance(data.get("data"), list):
            return []
        for item in data['data']:
            item['application_name'] = item['name']
            item['application_id'] = item['id']
            item['deepLink'] = f"{self.controller_url}/controller/#/location=APP_DASHBOARD&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&application={item['id']}&dashboardMode=force"
            item['controller_url'] = self.controller_url
        return data['data']

    def get_tier_node_status(self, app_id):
        data = self._request(
            method="POST",
            uri="/controller/restui/v1/nodes/list/health",
            json={
                "requestFilter": {
                    "queryParams": {
                        "applicationId": app_id,
                        "performanceDataFilter": "REPORTING",
                        "tags": []
                    },
                    "filterAll": False,
                    "filters": []
                },
                "resultColumns": ["NODE_NAME", "TIER"],
                "offset": 0,
                "limit": -1,
                "searchFilters": [],
                "columnSorts": [{"column": "TIER", "direction": "ASC"}],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd
            }
        )
        if not data:
            return {}, []

        node_ids = []
        for node in data['data']:
            node_ids.append(node['nodeId'])
        if len(node_ids) == 0:
            self.logger.debug(f"App ID: {app_id} has no tiers and nodes")
            return {}, []

        data = self._request(
            method="POST",
            uri="/controller/restui/v1/nodes/list/health/ids",
            json={
                "requestFilter": node_ids,
                "resultColumns": ["HEALTH","APP_AGENT_STATUS","APP_AGENT_VERSION","LAST_APP_SERVER_RESTART_TIME","MACHINE_AGENT_STATUS","VM_RUNTIME_VERSION"],
                "offset": 0,
                "limit": -1,
                "searchFilters": [],
                "columnSorts": [{"column": "TIER","direction": "ASC"}],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd
            }
        )
        if not data:
            return {}, []

        tiers = {}
        nodes = []
        status_map = {}
        for item in data['data']:
            if status_map.get(item['componentName']) is None:
                status_map[item['componentName']] = 0b0000
            status_map[item['componentName']] |= self._get_tier_status_binary(item['healthMetricStats']['state'])
            if tiers.get(item['componentName']) is None:
                tiers[item['componentName']] = {'node_count': 0}
            item['application_id'] = app_id
            item['deepLink'] = f"{self.controller_url}/controller/#/location=APP_NODE_MANAGER&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&application={app_id}&node={item['nodeId']}&dashboardMode=force"
            item['controller_url'] = self.controller_url
            nodes.append(item)
            tiers[item['componentName']]['componentName'] = item['componentName']
            tiers[item['componentName']]['tierName'] = item['componentName']
            tiers[item['componentName']]['componentId'] = item['componentId']
            tiers[item['componentName']]['application_id'] = app_id
            tiers[item['componentName']]['node_count'] += 1
            tiers[item['componentName']]['deepLink'] = f"{self.controller_url}/controller/#/location=APP_COMPONENT_MANAGER&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&application={app_id}&component={item['componentId']}&dashboardMode=force"
            tiers[item['componentName']]['controller_url'] = self.controller_url
            tierMetrics = self.get_tier_metrics(app_id, item['componentName'])
            if 'averageResponseTime' in tierMetrics:
                tiers[item['componentName']]['averageResponseTime'] = tierMetrics['averageResponseTime']
            else:
                tiers[item['componentName']]['averageResponseTime'] = 0
            if 'callsPerMinute' in tierMetrics:
                tiers[item['componentName']]['callsPerMinute'] = tierMetrics['callsPerMinute']
            else:
                tiers[item['componentName']]['callsPerMinute'] = 0
            if 'errorsPerMinute' in tierMetrics:
                tiers[item['componentName']]['errorsPerMinute'] = tierMetrics['errorsPerMinute']
            else:
                tiers[item['componentName']]['errorsPerMinute'] = 0

        for component in status_map:
            tiers[component]['state'] = self._get_tier_status_string(status_map[component])
        return tiers, nodes

    def _get_tier_status_string(self, binary):
        if binary & 0b0100 == 0b0100: return 'CRITICAL'
        if binary & 0b0010 == 0b0010: return 'WARNING'
        if binary & 0b0001 == 0b0001: return 'NORMAL'
        return 'UNKNOWN'

    def _get_tier_status_binary(self, status):
        if status == 'NORMAL': return 0b0001
        elif status == 'WARNING': return 0b0010
        elif status == 'CRITICAL': return 0b0100
        else: return 0b1000

    def get_database_summary(self, just_one=False):
        health_data = self._request(
            method="POST",
            uri="/controller/databasesui/databases/list?maxDataPointsPerMetric=1440",
            json={
                "requestFilter": {},
                "resultColumns": ["ID", "NAME", "TYPE"],
                "offset": 0,
                "limit": -1,
                "searchFilters": [],
                "columnSorts": [{"column": "HEALTH", "direction": "ASC"}],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd
            }
        )

        if just_one:
            return
        if not health_data:
            return
        database_ids = [item['configId'] for item in health_data['data']]
        metrics_data = self.fetch_database_data(database_ids)
        if not metrics_data:
            return None
        for item in metrics_data:
            item['deepLink'] = f"{self.controller_url}/controller/#/location=DB_MONITORING_SERVER_DASHBOARD&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&dbServerId={item['id']}"
            item['timeRangeStart'] = self.timeRangeStart
            item['timeRangeEnd'] = self.timeRangeEnd
            item['controller_url'] = self.controller_url
            item['bt_ids'], item['app_ids'] = self.get_database_bt_list( item['id'] )
        return metrics_data

    def get_database_bt_list(self, db_id):
        if int(db_id) == 0:
            return [], []
        data = self._request(
            method="POST",
            uri="/controller/databasesui/snapshot/getBTListViewData",
            json={
                "dbConfigId": -1,
                "dbServerId": db_id,
                "size": 1000,
                "startTime": self.timeRangeStart,
                "endTime": self.timeRangeEnd
            }
        )
        if not data:
            return [], []
        app_ids = []
        bt_ids = []
        for item in data:
            bt_ids.append(item['id'])
            app_ids.append(item['appId'])
        return bt_ids, list(set(app_ids))

    # Function to fetch database data
    def fetch_database_data(self, database_ids):
        data = self._request(
            method="POST",
            uri="/controller/databasesui/databases/list/data?maxDataPointsPerMetric=1440",
            json={
                "requestFilter": database_ids,
                "resultColumns": ["HEALTH", "QUERIES", "TIME_SPENT", "CPU"],
                "offset": 0,
                "limit": -1,
                "searchFilters": [],
                "columnSorts": [{"column": "TIME_SPENT", "direction": "DESC"}],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd
            },
        )
        if data:
            return data['data']
        return None

    def get_server_summary(self, ):
        # Fetch the list of servers
        server_list = self._request(
            method="POST",
            uri="/controller/sim/v2/user/machines/keys",
            json={
                "filter": {
                    "appIds": [],
                    "nodeIds": [],
                    "tierIds": [],
                    "types": ["PHYSICAL", "CONTAINER_AWARE"],
                    "timeRangeStart": self.timeRangeStart,
                    "timeRangeEnd": self.timeRangeEnd
                },
                "sorter": {
                    "field": "HEALTH",
                    "direction": "ASC"
                }
            },
        )
        machine_ids = [server["machineId"] for server in server_list.get("machineKeys", [])]

        # Fetch health and metrics data for the machines
        health_data = self._request(
            method="POST",
            uri="/controller/sim/v2/user/health",
            json={
                "timeRangeSpecifier": "last_1_hour.BEFORE_NOW.-1.-1.60",
                "machineIds": machine_ids
            }
        )
        metrics_data = self._request(
            method="POST",
            uri="/controller/sim/v2/user/metrics/query/machines",
            json={
                "timeRange": f"Custom_Time_Range.BETWEEN_TIMES.{self.timeRangeEnd}.{self.timeRangeStart}.{self.duration}",
                "ids": machine_ids,
                "metricNames": [
                    "Hardware Resources|Machine|Availability",
                    "Hardware Resources|Volumes|Used (%)",
                    "Hardware Resources|CPU|%Busy",
                    "Hardware Resources|CPU|%Stolen",
                    "Hardware Resources|Memory|Used %",
                    "Hardware Resources|Memory|Swap Used %",
                    "Hardware Resources|Disks|Avg IO Utilization (%)",
                    "Hardware Resources|Network|Avg Utilization (%)",
                    "Hardware Resources|Load|Last 1 minute"
                ],
                "baselineId": None,
                "rollups": [1, 1440]
            }
        )

        # Combine data into a single dictionary
        combined_data = {}
        for server in server_list.get("machineKeys", []):
            machine_id = server["machineId"]
            combined_data[machine_id] = {
                "serverName": server["serverName"],
                "deepLink": f"{self.controller_url}/controller/#/location=SERVER_MONITORING_MACHINE_OVERVIEW&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&machineId={machine_id}",
                "health": None,
                'timeRangeStart': self.timeRangeStart,
                'timeRangeEnd': self.timeRangeEnd,
                'controller_url': self.controller_url,
                "metrics": {}
            }

        # Merge health data
        for machine_id, health in health_data.get("health", {}).items():
            if int(machine_id) in combined_data:
                combined_data[int(machine_id)]["health"] = health

        # Merge metrics data
        metrics_data_points = metrics_data.get("data", {}).get("1440", {})
        for machine_id, metrics in metrics_data_points.items():
            if int(machine_id) in combined_data:
                combined_data[int(machine_id)]["metrics"] = metrics.get("metricData", {})
        return combined_data

    def get_business_transactions_summary(self, app_list):
        btData = []
        for application in app_list:
            appBTData = self.get_application_business_transactions(application)
            if appBTData:
                appBTData['deepLink'] = f"{self.controller_url}/controller/#/location=APP_BT_LIST&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&application={appBTData['applicationEntity']['entityDefinition']['entityId']}"
                appBTData['timeRangeStart'] = self.timeRangeStart
                appBTData['timeRangeEnd'] = self.timeRangeEnd
                appBTData['controller_url'] = self.controller_url
                btData.append({"application": appBTData})
        return btData

    def get_application_business_transactions(self, applications):
        data = self._request(
            method="POST",
            uri="/controller/restui/v1/bt/listViewDataByColumnsV2",
            json={
                "requestFilter": {
                    "queryParams": {
                        "applicationIds": applications,
                        "tags": []
                    },
                    "filterAll": False,
                    "filters": []
                },
                "searchFilters": None,
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd,
                "columnSorts": None,
                "resultColumns": ["NAME", "BT_HEALTH", "AVERAGE_RESPONSE_TIME", "CALL_PER_MIN", "ERRORS_PER_MIN",
                                  "PERCENTAGE_ERROR", "PERCENTAGE_SLOW_TRANSACTIONS",
                                  "PERCENTAGE_VERY_SLOW_TRANSACTIONS", "PERCENTAGE_STALLED_TRANSACTIONS",
                                  "END_TO_END_LATENCY_TIME", "MAX_RESPONSE_TIME", "MIN_RESPONSE_TIME", "CALLS",
                                  "SLOW_TRANSACTIONS", "CPU_USED", "TOTAL_ERRORS", "BLOCK_TIME", "WAIT_TIME",
                                  "VERY_SLOW_TRANSACTIONS", "STALLED_TRANSACTIONS"],
                "offset": 0,
                "limit": -1
            },
        )

        if not data:
            return None
        applicationData = data["applicationEntity"]
        for item in data['btListEntries']:
            item['application_name'] = applicationData['name']
            item['application_id'] = applicationData['entityDefinition']['entityId']
            item['deepLink'] = f"{self.controller_url}/controller/#/location=APP_BT_DETAIL&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&application={applicationData['name']}&businessTransaction={item['id']}&dashboardMode=force"
            item['timeRangeStart'] = self.timeRangeStart
            item['timeRangeEnd'] = self.timeRangeEnd
            item['controller_url'] = self.controller_url
            item['business_transaction_id'] = item['id']
            item['business_transaction_name'] = item['name']
        return data['btListEntries']

    def get_application_security_attack_counts(self, appID):
        startedAt = self._format_time_rfc3339(self.timeRangeStart)
        endedAt = self._format_time_rfc3339(self.timeRangeEnd)
        items = self._request(uri=f"/controller/argento/api/apiservice/api/v1/stats/attackCount?applicationId={appID}&startedAt={startedAt}&endedAt={endedAt}")
        if not items:
            return None
        for item in items['items']:
            item['deepLink'] = f"{self.controller_url}/{item['url']}"
            item['timeRangeStart'] = self.timeRangeStart
            item['timeRangeEnd'] = self.timeRangeEnd
        return items

    def get_application_security_business_risk(self, appID):
        startedAt = self._format_time_rfc3339(self.timeRangeStart)
        endedAt = self._format_time_rfc3339(self.timeRangeEnd)
        items = self._request(uri=f"/controller/argento/api/apiservice/api/v1/stats/businessRisk?applicationId={appID}&startedAt={startedAt}&endedAt={endedAt}")
        if not items:
            return None
        self.logger.debug(f"items: {items}")
        self.logger.debug(f"items['items']: {items['items']}")
        for item in items['items']:
            item['deepLink'] = f"{self.controller_url}/{item['url']}"
            item['timeRangeStart'] = self.timeRangeStart
            item['timeRangeEnd'] = self.timeRangeEnd
        return items

    def get_application_security_vulnerabilities_count(self, appID):
        startedAt = self._format_time_rfc3339(self.timeRangeStart)
        endedAt = self._format_time_rfc3339(self.timeRangeEnd)
        items = self._request(uri=f"/controller/argento/api/apiservice/api/v1/stats/vulnCount?applicationId={appID}&startedAt={startedAt}&endedAt={endedAt}")
        if not items:
            return []
        data = []
        for item in items['items']:
            item['deepLink'] = f"{self.controller_url}/{item['url']}"
            item['timeRangeStart'] = self.timeRangeStart
            item['timeRangeEnd'] = self.timeRangeEnd
            data.append(item)
        return data

    def get_application_security_summary(self, app_list, just_one=False):
        data = []
        for app_id in app_list:
            application = {}
            application['application_id'] = app_id
            application['attacks'] = self.get_application_security_attack_counts(app_id)
            if just_one:
                data.append(application)
                break
            application['business_risk'] = self.get_application_security_business_risk(app_id)
            application['vulnerabilities'] = self.get_application_security_vulnerabilities_count(app_id)
            application['controller_url'] = self.controller_url
            data.append(application)
        return data

    def get_dem_web_summary(self):
        # Note to the future me, for dem calls it is time-range and not timeRange as for others
        data = self._request(uri=f"/controller/restui/eumApplications/getAllEumApplicationsData?time-range=Custom_Time_Range.BETWEEN_TIMES.{self.timeRangeEnd}.{self.timeRangeStart}.{self.duration}")
        if not data:
            return []
        for item in data:
            item['deepLink'] = f"{self.controller_url}/controller/#/location=EUM_WEB_MAIN_DASHBOARD&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&application={item['id']}"
            item['timeRangeStart'] = self.timeRangeStart
            item['timeRangeEnd'] = self.timeRangeEnd
            item['controller_url'] = self.controller_url
        return data

    def get_dem_mobile_summary(self):
        # Note to the future me, for dem calls it is time-range and not timeRange as for others
        apps = self._request(uri=f"/controller/restui/eumApplications/getAllMobileApplicationsData?time-range=Custom_Time_Range.BETWEEN_TIMES.{self.timeRangeEnd}.{self.timeRangeStart}.{self.duration}")

        if not apps:
            return []
        data = []
        for app in apps:
            for item in app.get("children", []):
                item['deepLink'] = f"{self.controller_url}/controller/#/location=EUM_MOBILE_MAIN_DASHBOARD&timeRange=last_1_hour.BEFORE_NOW.-1.-1.60&application={item['applicationId']}&platform={item['platform']}&mobileApp={item['mobileAppId']}&internalName={item['internalName']}"
                item['timeRangeStart'] = self.timeRangeStart
                item['timeRangeEnd'] = self.timeRangeEnd
                item['controller_url'] = self.controller_url
                data.append(item)
        return data

    def get_metric_data(self, application_id, metric_path, opt_compress_data_flag="true", opt_baseline_flag="none", just_verify=False, start=None, end=None):
        self.logger.debug(f"get_metric_data application_id: {application_id} metric_path: {metric_path}")
        if start is None:
            start = self.timeRangeStart
        if end is None:
            end = self.timeRangeEnd
        if opt_compress_data_flag == "true" or opt_compress_data_flag is True:
            compress_data_flag = "true"
        else:
            compress_data_flag = "false"
        metric_data = self._request(
            uri=f"/controller/rest/applications/{application_id}/metric-data?metric-path={urllib.parse.quote(metric_path)}&time-range-type=BETWEEN_TIMES&start-time={start}&end-time={end}&output=JSON&rollup={compress_data_flag}"
        )

        if just_verify:
            self.logger.debug(f"verification metric_data: {metric_data}")
            if not metric_data:
                raise Exception("No metric data found")
            if metric_data and 'metricId' in metric_data[0]:
                return metric_data
            raise Exception(f"Not a valid metric")

        if not metric_data:
            return []
        data = []
        if metric_data is not None:
            for metric in metric_data:
                if metric['metricName'] != "METRIC DATA NOT FOUND":
                    metric['baselines'] = []
                    if opt_baseline_flag != "none":
                        baselines = self.get_baselines(application_id, opt_baseline_flag)
                        for baseline in baselines:
                            self.logger.debug(f"Baseline: {json.dumps(baseline)} type: {type(data)}")
                            baseline_data = self.get_baseline_data(application_id, metric, baseline, opt_compress_data_flag)
                            metric['baselines'].append(baseline_data)
                    metric['controller_url'] = self.controller_url
                    data.append(metric)
        return data

    def get_baselines(self, application_id, opt_baseline_flag):
        self.logger.debug(f"get_baselines application_id: {application_id}")

        if application_id in self._app_baseline_map:
            self.logger.debug(f"baselines already cached, returning {self._app_baseline_map[application_id]}")
            return self._app_baseline_map[application_id]

        data = self._request(uri=f"/controller/restui/baselines/getAllBaselines/{application_id}?output=json")
        if not data:
            return None

        if opt_baseline_flag == "default":
            for item in data:
                if item['defaultBaseline']:
                    self.logger.debug(f"Returning Default Baseline: {item}")
                    self._app_baseline_map[application_id] = [item]
                    return [item]
        # Else, return all baselines
        self.logger.debug(f"Returning Baselines: {data} type: {type(data)}")
        self._app_baseline_map[application_id] = data
        return data

    def get_baseline_data(self, application_id, metric, baseline, opt_compress_data_flag):
        self.logger.debug(f"get_baseline_data for {application_id}: {baseline} for metric {metric}")
        granularity = 1
        if opt_compress_data_flag:
            granularity = self.duration
        data = self._request(
            method="POST",
            uri=f"/controller/restui/metricBrowser/getMetricBaselineData?granularityMinutes=10",
            json={
                "metricDataQueries": [
                    {
                        "metricId": metric['metricId'],
                        "entityId": application_id,
                        "entityType": "APPLICATION"
                    }
                ],
                "timeRangeSpecifier": {
                    "type": "BETWEEN_TIMES",
                    "durationInMinutes": None,
                    "endTime": self.timeRangeEnd,
                    "startTime": self.timeRangeStart,
                    "timeRange": None,
                    "timeRangeAdjusted": False
                },
                "metricBaseline": baseline['id'],
                "maxSize": 1440
            },
        )

        if not data:
            return []
        for item in data:
            item['description'] = baseline
        return data

    def get_events(self, opt_event_filter, app_list, query_cursor=None):
        if not query_cursor:
            query_cursor = {
                "timeRange": {
                    "type": "BETWEEN_TIMES",
                    "durationInMinutes": self.duration,
                    "endTime": self.timeRangeEnd,
                    "startTime": self.timeRangeStart,
                    "timeRange": None,
                    "timeRangeAdjusted": False
                }
            }
        data = self._request(
            method="POST",
            uri="/controller/restui/events/query",
            json={
                "queryCursor": query_cursor,
                "eventStreamItemFilter": {
                    "applicationIds": app_list,
                    "policyViolationStartedWarning": self._is_setting(opt_event_filter, "POLICY_OPEN_WARNING"),
                    "policyViolationStartedCritical": self._is_setting(opt_event_filter, "POLICY_OPEN_CRITICAL"),
                    "machineLearningStartedWarning": self._is_setting(opt_event_filter, "ANOMALY_OPEN_WARNING"),
                    "machineLearningStartedCritical": self._is_setting(opt_event_filter, "ANOMALY_OPEN_CRITICAL"),
                    "machineLearningWarningToCritical": self._is_setting(opt_event_filter, "ANOMALY_UPGRADE"),
                    "machineLearningCriticalToWarning": self._is_setting(opt_event_filter, "ANOMALY_DOWNGRADED"),
                    "machineLearningEndedCritical": self._is_setting(opt_event_filter, "ANOMALY_CLOSE_CRITICAL"),
                    "machineLearningEndedWarning": self._is_setting(opt_event_filter, "ANOMALY_CLOSE_WARNING"),
                    "machineLearningCanceledCritical": self._is_setting(opt_event_filter, "ANOMALY_CANCELED_CRITICAL"),
                    "machineLearningCanceledWarning": self._is_setting(opt_event_filter, "ANOMALY_CANCELED_WARNING"),
                    "codeDeadlock": self._is_setting(opt_event_filter, "DEADLOCK"),
                    "resourcePoolLimit": self._is_setting(opt_event_filter, "RESOURCE_POOL_LIMIT"),
                    "applicationDeployment": self._is_setting(opt_event_filter, "APPLICATION_DEPLOYMENT"),
                    "appServerRestart": self._is_setting(opt_event_filter, "APP_SERVER_RESTART"),
                    "appConfigChange": self._is_setting(opt_event_filter, "APPLICATION_CONFIG_CHANGE"),
                    "applicationCrash": self._is_setting(opt_event_filter, "APPLICATION_CRASH"),
                    "clrCrash": self._is_setting(opt_event_filter, "CLR_CRASH"),
                    "license": self._is_setting(opt_event_filter, "LICENSE"),
                    "controllerDiskSpaceLow": self._is_setting(opt_event_filter, "DISK_SPACE"),
                    "agentVersionNewerThanController": self._is_setting(opt_event_filter, "CONTROLLER_AGENT_VERSION_INCOMPATIBILITY"),
                    "agentConfigurationError": self._is_setting(opt_event_filter, "AGENT_CONFIGURATION_ERROR"),
                    "controllerMetricRegistrationLimitReached": self._is_setting(opt_event_filter, "CONTROLLER_METRIC_REG_LIMIT_REACHED"),
                    "agentMetricRegistrationLimitReached": self._is_setting(opt_event_filter, "AGENT_METRIC_BLACKLIST_REG_LIMIT_REACHED"),
                    "devModeConfigUpdate": self._is_setting(opt_event_filter, "DEV_MODE_CONFIG_UPDATE"),
                    "syntheticAvailabilityHealthy": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_HEALTHY_EVENT"),
                    "syntheticAvailabilityWarning": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_WARNING_EVENT"),
                    "syntheticAvailabilityConfirmedWarning": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_CONFIRMED_WARNING_EVENT"),
                    "syntheticAvailabilityOngoingWarning": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_ONGOING_WARNING_EVENT"),
                    "syntheticAvailabilityError": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_ERROR_EVENT"),
                    "syntheticAvailabilityConfirmedError": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_CONFIRMED_ERROR_EVENT"),
                    "syntheticAvailabilityOngoingError": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_ONGOING_ERROR_EVENT"),
                    "syntheticPerformanceHealthy": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_PERF_HEALTHY_EVENT"),
                    "syntheticPerformanceWarning": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_PERF_WARNING_EVENT"),
                    "syntheticPerformanceConfirmedWarning": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_PERF_CONFIRMED_WARNING_EVENT"),
                    "syntheticPerformanceOngoingWarning": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_PERF_ONGOING_WARNING_EVENT"),
                    "syntheticPerformanceCritical": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_PERF_CRITICAL_EVENT"),
                    "syntheticPerformanceConfirmedCritical": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_PERF_CONFIRMED_CRITICAL_EVENT"),
                    "syntheticPerformanceOngoingCritical": self._is_setting(opt_event_filter, "EUM_CLOUD_SYNTHETIC_PERF_ONGOING_CRITICAL_EVENT"),
                    "mobileNewCrash": self._is_setting(opt_event_filter, "MOBILE_CRASH_IOS_EVENT") or self._is_setting(opt_event_filter, "MOBILE_CRASH_ANDROID_EVENT"),
                    "customEventFilters": [],
                    "networkIncluded": self._is_setting(opt_event_filter, "NETWORK"),
                    "clusterEvents": self._is_setting(opt_event_filter, "KUBERNETES"),
                    "businessTransactionIds": [],
                    "applicationComponentIds": [],
                    "applicationComponentNodeIds": [],
                    "timeRange": {
                        "type":"BETWEEN_TIMES",
                        "durationInMinutes": self.duration,
                        "endTime": self.timeRangeEnd,
                        "startTime": self.timeRangeStart,
                        "timeRange": None,
                        "timeRangeAdjusted": False
                    },
                    "policyViolationWarningToCritical": self._is_setting(opt_event_filter, "POLICY_UPGRADED"),
                    "policyViolationCriticalToWarning": self._is_setting(opt_event_filter, "POLICY_DOWNGRADED"),
                    "policyViolationContinuesWarning": self._is_setting(opt_event_filter, "POLICY_CONTINUES_WARNING"),
                    "policyViolationContinuesCritical": self._is_setting(opt_event_filter, "POLICY_CONTINUES_CRITICAL"),
                    "policyViolationEndedWarning": self._is_setting(opt_event_filter, "POLICY_CLOSE_WARNING"),
                    "policyViolationEndedCritical": self._is_setting(opt_event_filter, "POLICY_CLOSE_CRITICAL"),
                    "policyViolationCanceledWarning": self._is_setting(opt_event_filter, "POLICY_CANCELED_WARNING"),
                    "policyViolationCanceledCritical": self._is_setting(opt_event_filter, "POLICY_CANCELED_CRITICAL"),
                    "slowRequest": self._is_setting(opt_event_filter, "SLOW"),
                    "verySlowRequest": self._is_setting(opt_event_filter, "VERY_SLOW"),
                    "stalledRequest": self._is_setting(opt_event_filter, "STALL"),
                    "allError": self._is_setting(opt_event_filter, "APPLICATION_ERROR"),
                    "custom": self._is_setting(opt_event_filter, "CUSTOM"),
                    "agentEvent": self._is_setting(opt_event_filter, "AGENT_EVENT"),
                    "applicationDiscovered": self._is_setting(opt_event_filter, "APPLICATION_DISCOVERED"),
                    "tierDiscovered": self._is_setting(opt_event_filter, "TIER_DISCOVERED"),
                    "nodeDiscovered": self._is_setting(opt_event_filter, "NODE_DISCOVERED"),
                    "machineDiscovered": self._is_setting(opt_event_filter, "MACHINE_DISCOVERED"),
                    "btDiscovered": self._is_setting(opt_event_filter, "BT_DISCOVERED"),
                    "serviceEndpointDiscovered": self._is_setting(opt_event_filter, "SERVICE_ENDPOINT_DISCOVERED"),
                    "backendDiscovered": self._is_setting(opt_event_filter, "BACKEND_DISCOVERED"),
                    "agentEnabledDisabled": self._is_setting(opt_event_filter, "AGENT_STATUS"),
                    "bytecodeTransformerLog": True,
                    "diagnosticSession": self._is_setting(opt_event_filter, "DIAGNOSTIC_SESSION"),
                    "internalUIEvent": self._is_setting(opt_event_filter, "INTERNAL_UI_EVENT"),
                    "appDynamicsInternalDiagnostics": self._is_setting(opt_event_filter, "APPDYNAMICS_INTERNAL_DIAGNOSTICS"),
                    "eumInternalError": self._is_setting(opt_event_filter, "EUM_INTERNAL_ERROR"),
                    "memoryLeakDiagnostics": self._is_setting(opt_event_filter, "MEMORY_LEAK_DIAGNOSTICS"),
                    "systemLog": self._is_setting(opt_event_filter, "SYSTEM_LOG"),
                    "activityTrace": self._is_setting(opt_event_filter, "ACTIVITY_TRACE"),
                    "objectContentSummary": self._is_setting(opt_event_filter, "OBJECT_CONTENT_SUMMARY"),
                    "appDynamicsData": self._is_setting(opt_event_filter, "APPDYNAMICS_DATA"),
                    "azureAutoScaling": self._is_setting(opt_event_filter, "AZURE_AUTO_SCALING"),
                    "agentDiagnostics": self._is_setting(opt_event_filter, "AGENT_DIAGNOSTICS"),
                    "memory": self._is_setting(opt_event_filter, "MEMORY"),
                    "dbmsParameterChanged": True
                }
            },
        )

        if not data:
            return []

        event_data = self._relax_events(data) #move data around and decorate missing data
        event_data = self._filter_events(event_data, opt_event_filter) #remove data that was fetched because of broken filters in appd
        event_data = self._normalize_events(event_data) #flatten and add known but missing tags
        query_cursor = data["queryCursor"]
        if query_cursor is not None and query_cursor.get('moreEvents') is True:
            event_data.extend(self.get_events(opt_event_filter, app_list, query_cursor))
        return event_data

    '''
    filter events: remove events that were fetched but not part of the filter, appd has some bugs, yo
    '''
    def _filter_events(self, event_data, opt_event_filter):
        #this is a workaround to handle the fact that DB_SERVER_PARAMETER_CHANGE events are always sent, even if not requested
        if not self._is_setting(opt_event_filter, "DB_SERVER_PARAMETER_CHANGE"):
            new_event_data = []
            for event in event_data:
                if not event['eventType'] in ["DB_SERVER_PARAMETER_CHANGE", "DB_SERVER_PARAMTER_CHANGE"]:
                    new_event_data.append(event)
            return new_event_data
        return event_data

    '''
    normalize events: add some basic data needed for source identification within splunk
    '''
    def _normalize_events(self, event_data):
        for event in event_data:
            app_name, tier_name, node_name = self._lookup_names(
                event["applicationId"],
                event["applicationComponentNodeId"],
                event.get("applicationComponentId"),
            )
            event['application_name'] = app_name
            event['tier_name'] = tier_name
            event['node_name'] = node_name
            event['controller_url'] = self.controller_url
            event['deepLink'] = f"{self.controller_url}/controller/#/location=APP_EVENT_VIEWER_MODAL&timeRange=Custom_Time_Range.BETWEEN_TIMES.{self.timeRangeEnd}.{self.timeRangeStart}.{self.duration}&application={event['applicationId']}&eventSummary={event['id']}&dbMonitoringMode=false"
        return event_data

    '''
    lookup app, tier, and node names for ids, the actual lookups are cached in get_application and get_nodes 
    '''
    def _tier_name_for_component_id(self, app_id, component_id):
        if component_id is None:
            return ""
        try:
            cid = int(component_id)
        except (TypeError, ValueError):
            return ""
        if cid < 1:
            return ""
        app_id = int(app_id)
        cache = self._cache_component_id_to_tier_name.get(app_id)
        if cache is None:
            cache = {}
            data = self._request(uri=f"/controller/rest/applications/{app_id}/tiers?output=json")
            if data:
                for tier in data:
                    tid = tier.get("id")
                    if tid is not None:
                        cache[int(tid)] = (tier.get("name") or "").strip()
            self._cache_component_id_to_tier_name[app_id] = cache
        return cache.get(cid, "")

    def _lookup_names(self, app_id, node_id, component_id=None):
        app_name = self.get_application(int(app_id))['name']
        tier_name = ""
        node_name = ""
        nodes = self.get_nodes(int(app_id))
        for id in nodes:
            #self.logger.debug(f"iteration to map node {id} == {node_id}")
            if id == node_id:
                tier_name = (nodes[id].get("tierName") or nodes[id].get("applicationComponentName") or "").strip()
                node_name = nodes[id].get("name") or ""
                break
        if not tier_name and component_id is not None:
            tier_name = self._tier_name_for_component_id(app_id, component_id)
        return app_name, tier_name, node_name

    '''
    relax events: named from graph theory, we want to move things around and flatten some data in the event to make it 
        easier for splunk to get at some deeper data
    '''
    def _relax_events(self, eventResponse ):
        relaxed_events = []
        entity_map = eventResponse["entityMap"]
        events = eventResponse["eventStreamUiItems"]
        for event in events:
            if event["affectedEntities"] is not None:
                splunk_entity_list = []
                new_affected_entities = []
                for entity in event["affectedEntities"]:
                    entity_key = f"Type:{entity['entityType']}, id:{entity['entityId']}"
                    new_entity = entity_map.get(entity_key, {})
                    splunk_entity_list.append( f"{new_entity.get('name')}:{new_entity.get('id')}")
                    #if health rule violation, add data to the event
                    if new_entity.get('waitTimeInMinutes') is not None:
                        event['healthRuleName'] = new_entity['name']
                        event['healthRuleId'] = new_entity['id']
                        event['healthRuleDescription'] = new_entity['description']
                        event['healthRuleType'] = new_entity['type']
                    new_affected_entities.append(new_entity)
                event["affectedEntities"] = new_affected_entities
                event["entities"] = splunk_entity_list
            relaxed_events.append(event)
        return relaxed_events

    def _is_setting(self, opt_event_filter, setting):
        if setting in opt_event_filter:
            return True
        return False

    def get_application_security_business_transactions_recommended_actions(self, btUUID):
        data = self._request(uri=f"/controller/argento/api/v2/bts/{btUUID}/actions?order=DESC")
        if not data:
            return []
        return data

    def get_application_security_business_transactions(self):
        bt_data = self._request(uri="/controller/argento/api/v2/bts?sort=businessRiskScore&order=DESC&max=1000")
        if not bt_data:
            return []
        data = []
        def process_bts_query(item):
            try:
                item['recommended_actions'] = self.get_application_security_business_transactions_recommended_actions(item['id'])
                item['controller_url'] = self.controller_url
                data.append(item)
            except Exception as e:
                self.logger.warning("Error fetching recommended actions for bt id=%s: %s", item.get('id'), e)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                list(executor.map(process_bts_query, bt_data.get('btsTableData', [])))
        except Exception as e:
            self.logger.error("Error processing bt security recommendations: %s", e)
        return data

    def get_application_security_list(self, opt_app_list=None):
        data = self._request(uri="/controller/argento/public-api/v1/applications?max=3000")
        if not data:
            return []

        applications = []
        for item in data.get('items', []):
            item['controller_url'] = self.controller_url
            if item['applicationSecurityEnabled'] is True or item['applicationSecurityEnabledComputed'] is True:
                if not opt_app_list:
                    applications.append(item)
                elif item['applicationName'] in opt_app_list:
                    applications.append(item)

        if len(applications) == 0:
            return []
        return applications

    '''New secureapp public api, not quite complete to replace the private api, so leaving this until another release cycle'''
    def get_application_security_attacks_public_api(self, application_id, offset=0) -> []:
        data = self._request(uri=f"/controller/argento/public-api/v1/attacks?applicationId={application_id}&startedAt={self.timeRangeStart_rfc3339}&endedAt={self.timeRangeEnd_rfc3339}&max=3000&offset={offset}")
        if not data:
            return []

        self.logger.info(f"response total array length: {len(data.get('items', []))} total attribute: {data.get('total', 0)}")
        processed_data = []
        for item in data.get('items', []):
            self.logger.info(f"item: {json.dumps(item)}")
            item['controller_url'] = self.controller_url
            processed_data.append(self._process_attack_new(item))
        return processed_data

    def _process_attack_new(self, attack):
        attack_data = self._request(uri=f"/controller/argento/public-api/v1/attacks/{attack['attackSummaryId']}")
        if not attack_data:
            return attack

        for item in attack_data.get("items", []):
            for key, value in item.items():
                attack[key] = value
            return attack
        return attack

    def get_application_security_attacks(self, application_id):
        attack_data = self._request(uri=f"/controller/argento/api/v2/attacks?applicationId={application_id}&sort=lastSeenAt&order=DESC&max=100")
        if not attack_data:
            return []
        data = []
        #this is terrible and inefficient, but it works until something else works
        for item in attack_data.get('attacksTableData', []):
            timestamp = round(self.get_timestamp(item['lastSeenAt']) * 1000)
            if timestamp > self.timeRangeStart and timestamp < self.timeRangeEnd:
                data.append( self._process_attack(item))
        return data

    def _process_attack(self, attack):
        events_data = self._request(uri=f"/controller/argento/api/v2/attacks/{attack['id']}/events?applicationId={attack['appdApplicationId']}&order=ASC&max=10")
        if not events_data:
            return []

        for event in events_data.get('eventsTableData', []):
            event['deepLink'] = f"{self.controller_url}/controller/argento/assets/attacks/{attack['id']}"
            event['attackSummaryId'] = attack['id']
            event['attackName'] = attack['attackName']
            event['applicationId'] = attack['appdApplicationId']
            event['tierId'] = attack['appdTierId']
            event['btId'] = attack['appdBtId']
            event['btName'] = attack['btName']
            event['applicationUrl'] = f"{self.controller_url}{event['applicationUrl']}"
            event['tierUrl'] = f"{self.controller_url}{event['tierUrl']}"
            event['controller_url'] = self.controller_url
            event['firstSeenAt'] = attack['firstSeenAt']
            event['lastSeenAt'] = attack['lastSeenAt']
            event['status'] = attack['attackStatus']
            cve_data = self._get_cve_details( event['cveId'], event['applicationId'])
            event['matchedCveName'] = cve_data['name']
            event['matchedCveDescription'] = cve_data['description']
            event['matchedCveUrl'] = cve_data['nvdUrl']
            event['matchedCveCweName'] = cve_data['cweName']
            event['matchedCveTitle'] = cve_data['cveTitle']
            event['matchedCveSeverity'] = cve_data['severity']
            event['matchedCveDescription'] = cve_data['description']
            event['matchedCveRemediation'] = cve_data['remediation']
            event['matchedCvePublishDate'] = cve_data['publishDate']
            event['matchedCveRisk'] = cve_data['risk']
            event['matchedCveKennaRiskScoreMeter'] = cve_data['kenna']['riskScoreMeter']
            event['matchedCveKennaRemoteCodeExecution'] = cve_data['kenna']['remoteCodeExecution']
            event['matchedCveKennaEasilyExploitable'] = cve_data['kenna']['easilyExploitable']
            event['matchedCveKennaMalwareExploitable'] = cve_data['kenna']['malwareExploitable']
            event['matchedCveKennaActiveInternetBreach'] = cve_data['kenna']['activeInternetBreach']
            event['matchedCveKennaPopularTarget'] = cve_data['kenna']['popularTarget']
            event['matchedCveKennaPredictedExploitable'] = cve_data['kenna']['predictedExploitable']
            return event

        return None

    def _get_cve_details(self, cve_id, application_id):
        data = self._request(uri=f"/controller/argento/api/v2/vulnerabilities/{cve_id}?applicationId={application_id}&order=DESC")
        if not data:
            return {}
        return data

    def get_timestamp(self, string_timestamp):
        for fmt, pattern in self._date_patterns.items():
            if re.match(pattern, string_timestamp):
                try:
                    return datetime.strptime(string_timestamp, fmt).timestamp()
                except ValueError as ve:
                    self.logger.error(f"Unable to parse timestamp {string_timestamp} exception: {ve}")
        self.logger.error(f"Unable to parse timestamp {string_timestamp}")
        return None

    def get_application_security_vulnerabilities(self, application_id):
        table_data = self._request(uri=f"/controller/argento/api/v2/vulnerabilities?applicationId={application_id}&sort=lastSeenAt&order=DESC&max=100")
        if not table_data:
            return []

        data = []

        #this is terrible and inefficient, but it works until something else works
        for item in table_data.get('cveTableData', []):
            timestamp = round(self.get_timestamp(item['lastSeenAt']) * 1000)
            if timestamp > self.timeRangeStart and timestamp < self.timeRangeEnd:
                match = re.search(r'application=(\d+)', item['applicationUrl'])
                if match:
                    item['applicationId'] = match.group(1)
                    item['deepLink'] = f"{self.controller_url}/controller/argento/assets/vulnerabilities/{item['id']}?application={item['applicationId']}"
                item['controller_url'] = self.controller_url
                item['applicationUrl'] = f"{self.controller_url}{item['applicationUrl']}"
                item['tierUrl'] = f"{self.controller_url}{item['tierUrl']}"
                data.append(item)
        return data

    def get_client_id(self):
        return self.auth_handler.get_client_id()

    def get_database_application(self):
        return self.get_all_app_list()["dbMonApplication"]

    def get_databases(self):
        data = self._request(
            method="POST",
            uri="/controller/databasesui/databases/list?maxDataPointsPerMetric=1440",
            json={
                "requestFilter": {},
                "resultColumns": ["ID", "NAME", "TYPE"],
                "offset": 0,
                "limit": -1,
                "searchFilters": [],
                "columnSorts": [{"column": "HEALTH", "direction": "ASC"}],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd
            },
        )

        if not data:
            return []

        return data.get('data', [])

    def get_tiers(self, app_id):
        cached_entry = self._cache_tier_map.get(app_id)
        if cached_entry:
            return cached_entry

        tiers = {}
        data = self._request(uri=f"/controller/rest/applications/{app_id}/tiers?output=json")

        if not data:
            return {}
        for tier in data:
            tiers[tier['name']] = tier['id']
        self._cache_tier_map[app_id] = tiers
        return tiers

    def get_application(self, app_id):
        app_id = int(app_id)
        cached_entry = self._cache_app_map.get(app_id)
        if cached_entry:
            self.logger.debug(f"returning cached lookup of application for app {app_id} - {cached_entry}")
            return cached_entry

        data = self.get_all_app_list()
        for section_key, section_value in data.items():
            if isinstance(section_value, list):  # Ensure that the section is a list of applications
                for app in section_value:
                    if 'id' in app and 'name' in app:  # Ensure that both 'id' and 'name' exist
                        self._cache_app_map[app['id']] = app  # Cache the app
            elif isinstance(section_value, dict) and 'id' in section_value and 'name' in section_value:
                self._cache_app_map[section_value['id']] = section_value  # Cache single application entries

        self.logger.debug(f"returning fresh lookup of application {app_id} - {self._cache_app_map.get(app_id)}")
        return self._cache_app_map.get(app_id)

    def get_application_id_by_name(self, app_name):
        # Check the cache for a matching name
        for app in self._cache_app_map.values():
            if app.get('name') == app_name:
                self.logger.debug(f"returning cached lookup of application id for name '{app_name}' - {app.get('id')}")
                return app.get('id')

        # Refresh the cache if not found
        data = self.get_all_app_list()
        for section_key, section_value in data.items():
            if isinstance(section_value, list):
                for app in section_value:
                    if 'id' in app and 'name' in app:
                        self._cache_app_map[app['id']] = app
            elif isinstance(section_value, dict) and 'id' in section_value and 'name' in section_value:
                self._cache_app_map[section_value['id']] = section_value

        # Second pass: search again after cache is repopulated
        for app in self._cache_app_map.values():
            if app.get('name') == app_name:
                self.logger.debug(f"returning fresh lookup of application id for name '{app_name}' - {app.get('id')}")
                return app.get('id')

        self.logger.debug(f"application name '{app_name}' not found in application list")
        return None

    def get_nodes(self, app_id):
        cached_entry = self._cache_node_map.get(app_id)
        if cached_entry:
            self.logger.debug(f"returning cached lookup of nodes for application {app_id} - {cached_entry}")
            return cached_entry

        nodes = {}
        data = self._request(uri=f"/controller/rest/applications/{app_id}/nodes?output=json")

        if not data:
            return {}
        for node in data:
            nodes[node['id']] = node
        self._cache_node_map[app_id] = nodes
        self.logger.debug(f"returning fresh lookup of nodes for application {app_id} - {nodes}")
        return nodes

    def get_snapshots_by_app(self, app_id, filters):
        arguments = "output=JSON"
        if filters['need_props'] is True:
            arguments += "&need-props=true"
        if filters['need_exit_calls'] is True:
            arguments += "&needs-exit-calls=true"
        if filters['first_in_chain'] is True:
            arguments += "&first-in-chain=true"
        if filters['archived'] is True:
            arguments += "&archived=true"
        if int(filters.get('execution_time_in_milis')) > 0:
            arguments += f"&execution-time-in-milis={filters.get('execution_time_in_milis')}"
        arguments += f"&user-experience={','.join(filters.get('user_experience', []))}"
        data = self._request(uri=f"/controller/rest/applications/{app_id}/request-snapshots?time-range-type=BETWEEN_TIMES&start-time={self.timeRangeStart}&end-time={self.timeRangeEnd}&{arguments}")
        if not data:
            return []
        snapshots = []
        for item in data:
            app_name, tier_name, node_name = self._lookup_names(
                app_id, item["applicationComponentNodeId"], item.get("applicationComponentId")
            )
            item['application_name'] = app_name
            item['tier_name'] = tier_name
            item['node_name'] = node_name
            item['controller_url'] = self.controller_url
            item['deepLink'] = f"{self.controller_url}/controller/#/location=APP_SNAPSHOT_VIEWER&requestGUID={item['requestGUID']}&application={app_id}&businessTransaction={item['businessTransactionId']}&rsdTime=Custom_Time_Range.BETWEEN_TIMES.{self.timeRangeEnd}.{self.timeRangeStart}.{self.duration}&tab=overview&dashboardMode=force"
            snapshots.append(item)

        return snapshots

    def _convert_timestamp(self, timestamp_ms):
        timestamp_sec = timestamp_ms / 1000.0
        dt_local = datetime.fromtimestamp(timestamp_sec).astimezone()
        return dt_local.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + dt_local.strftime('%z')

    def get_audit_logs(self):
        audit_data = self._request(uri=f"/controller/ControllerAuditHistory?startTime={urllib.parse.quote(self._convert_timestamp(self.timeRangeStart))}&endTime={urllib.parse.quote(self._convert_timestamp(self.timeRangeEnd))}")
        if not audit_data:
            return []
        data = []
        for item in audit_data:
            item['controller_url'] = self.controller_url
            data.append(item)

        return data

    def get_account(self):
        data = self._request(uri="/controller/api/accounts/myaccount")
        if not data:
            return []
        return data

    def get_abl_license_usage(self):
        account = self.get_account()
        license_data = self._request(uri=f"/controller/api/accounts/{account['id']}/licensemodules/usages", ignore_errors=True)
        if not license_data:
            return []

        data = {}
        for item in license_data.get('usages', []):
            item['controller_url'] = self.controller_url
            item['account_name'] = account['name']
            item['type'] = "ABL"
            data[item.get('agentType')] = item
        array = []
        for key in data.keys():
            array.append(data[key])
        return array

    def get_ibl_license_usage(self):
        account = self.get_account()
        license_data = self._request(uri=f"/controller/restui/license/accounts/{account['id']}/usages?includeExpiredPackages=true", ignore_errors=True)
        if license_data is None:
            return []

        data = []
        for package in license_data.get('packages', []):
            package_data = self._request(uri=f"/controller/restui/license/accounts/{account['id']}/packages/{package.get('packageName')}/usage?granularityMinutes=5")
            metrics = package_data.get('metrics', {})
            item = {}
            for type in metrics.keys():
                metric = metrics[type].get('agg')
                item[type] = {}
                item[type]['avg'] = metric.get('avg')
                item[type]['count'] = metric.get('count')
                item[type]['max'] = metric.get('max')
                item[type]['min'] = metric.get('min')
                item[type]['timestamp'] = metric.get('timestamp')
            item['controller_url'] = self.controller_url
            item['type'] = "IBL"
            #item['license'] = package
            for key in package.keys():
                item[key] = package[key]
            data.append(item)
        return data

    def get_tier_metrics(self, app, tier_name):
        self.logger.debug(f"get_tier_metrics Getting tier metrics for application: {app} tier: {tier_name}")
        data = {}
        metric_path = f"Overall Application Performance|{tier_name}|*"
        metric_data = self.get_metric_data(app, metric_path)
        for metric in metric_data:
            tierName = metric["metricPath"].split('|')[1]
            if metric["metricPath"].split('|')[2] == 'Average Response Time (ms)':
                data["averageResponseTime"] = metric["metricValues"][0]["current"]
            elif metric["metricPath"].split('|')[2] == 'Calls per Minute':
                data["callsPerMinute"] = metric["metricValues"][0]["current"]
            elif metric["metricPath"].split('|')[2] == 'Errors per Minute':
                data["errorsPerMinute"] = metric["metricValues"][0]["current"]
        return data

    def get_remote_services_status(self, app):
        self.logger.debug(f"get_remote_services_status Getting remote services status for application: {app}")
        list_data = self._request(
            method="POST",
            uri="/controller/restui/backend/list/remoteService",
            json={
                "requestFilter":{
                    "queryParams":{
                        "applicationId": app
                    },
                    "filters":[]
                },
                "resultColumns": ["ID","NAME","TYPE"],
                "offset":0,
                "limit":-1,
                "searchFilters":[],
                "columnSorts":[],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd
            }
        )

        if not list_data:
            return []

        self.logger.debug(f"get_remote_services_status list for application: {app} returns: {list_data}")
        remote_service_ids = []
        for item in list_data['data']:
            remote_service_ids.append(item['id'])

        backend_data = self._request(
            method="POST",
            uri="/controller/restui/backend/list/remoteService/ids",
            json={
                "requestFilter": remote_service_ids,
                "resultColumns": ["TYPE","RESPONSE_TIME","CALLS","CALLS_PER_MIN","ERRORS","ERRORS_PER_MIN"],
                "offset":0,
                "limit":-1,
                "searchFilters":[],
                "columnSorts":[],
                "timeRangeStart": self.timeRangeStart,
                "timeRangeEnd": self.timeRangeEnd
            }
        )

        if not backend_data:
            return []

        data = []
        for item in backend_data['data']:
            backend = {}
            backend['id'] = item['id']
            backend['name'] = item['name']
            backend['type'] = item['exitPointSubtype']
            backend['application_id'] = app
            backend['application_name'] = self.get_application(app)['name']
            backend['averageResponseTime'] = item['performanceStats']['averageResponseTime']['value']
            backend['callsPerMinute'] = item['performanceStats']['callsPerMinute']['value']
            backend['errorsPerMinute'] = item['performanceStats']['errorsPerMinute']['value']
            backend['deepLink'] = f"{self.controller_url}/controller/#/location=APP_BACKEND_DASHBOARD&application={app}&backendDashboard={item['id']}&dashboardMode=force&rsdTime=Custom_Time_Range.BETWEEN_TIMES.{self.timeRangeEnd}.{self.timeRangeStart}.{self.duration}"
            data.append(backend)
        return data