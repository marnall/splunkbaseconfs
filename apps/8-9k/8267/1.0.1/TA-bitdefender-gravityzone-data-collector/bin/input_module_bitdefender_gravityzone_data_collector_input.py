# encoding = utf-8

import os
import sys
import time
from datetime import datetime, timedelta, timezone
import json
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass
from time import sleep
from urllib.parse import urlparse

'''
        // sort
        if ($sort == null) {
            $this->sort('created', self::SORT_DESCENDING);
        }

        optimization idea: assume that logs are sorted by created date and stop early without processing all items
'''

USER_ACTIVITY_ACTION_NAMES = {
    0x01: "login",
    0x30: "login_idp",
    0x02: "login_failed",
    0x03: "logout",
    0x04: "create",
    0x05: "edit",
    0x06: "delete",
    0x07: "restore",
    0x08: "download",
    0x09: "assign_policy",
    0x0A: "moved",
    0x0B: "update",
    0x0C: "upload",
    0x0D: "suspend",
    0x0E: "activate",
    0x10: "rename",
    0x11: "push_sync",
    0x12: "license",
    0x13: "cancel",
    0x14: "stop",
    0x15: "save",
    0x16: "publish",
    0x18: "publish_fast",
    0x19: "set_default_policy",
    0x1A: "retrieve_recovery_key",
    0x1B: "set_ad_integrator",
    0x1C: "remove_ad_integrator",
    0x1D: "remove_ad_integration",
    0x1E: "add_file",
    0x1F: "add_to_block_list",
    0x20: "remove_from_block_list",
    0x21: "update_incident_status",
    0x22: "update_incident_note_old",
    0x34: "action_password_recovery",
    0x73: "action_create_incident_note",
    0x74: "action_update_incident_note",
    0x75: "action_delete_incident_note",
    0x77: "action_assign_incident",
    0x78: "action_unassign_incident",
    0x79: "action_change_incident_priority",
    0x23: "resync",
    0x24: "assign_custom_fields_values",
    0x25: "import_data_custom_fields",
    0x26: "action_provision",
    0x27: "start_gathering_logs",
    0x28: "begin_debug_session",
    0x29: "end_debug_session",
    0x2A: "login_with_bearer",
    0x40: "quarantine_remove_all",
    0x50: "unassign",
    0x51: "import_exclusions",
    0x52: "collect_investigation_package",
    0x53: "delete_investigation_package",
    0x54: "cancel_investigation_package",
    0x55: "download_investigation_package",
    0x60: "action_remote_shell_session_started",
    0x61: "action_remote_shell_session_ended",
    0x62: "disconnect_all_users",
    0x63: "delete_email_0365",
    0x64: "isolate_endpoint",
    0x65: "disable_user_o365",
    0x66: "enable_user_o365",
    0x67: "disable_user_ad",
    0x68: "enable_user_ad",
    0x69: "reset_credentials_ad",
    0x70: "reset_credentials_o365",
    0x71: "restore_endpoint",
    0x72: "confirm_compromised_user_o365",
    0x80: "action_live_search_query",
    0x81: "action_type_im_configure_default_rule",
    0x82: "action_type_im_assign_rules",
    0x83: "action_type_im_correct_rules",
    0x84: "action_assign_gz_tags",
    0x85: "action_unassign_gz_tags",
    0x86: "deactivate_user_aws",
    0x90: "restart",
    145: "action_send_mobile_activation_email",
    146: "action_failed_mobile_activation_email",
    147: "restore_original",
    150: "delete_email_google",
    148: "disable_user_google",
    149: "enable_user_google",
    151: "action_provision_failed",
    152: "download_quarantine_file",
    153: "delete_quarantine_file",
    154: "retrieve_quarantine_file",
    155: "start_trial_features",
    156: "end_trial_features",
    157: "action_modify_msp_ipt_rights",
    158: "action_modify_msp_ipt_visibility",
    159: "patch_install",
    160: "add_to_quarantine",
    161: "restore_from_quarantine",
    162: "delete_endpoint_item",
    163: "disinfect",
    164: "kill_process",
    165: "add_to_sandbox",
    166: "submit_to_labs",
    167: "update_scan_configuration",
    168: "include_assets",
    169: "exclude_assets",
    170: "on_demand_scan",
    171: "malware_scan",
    172: "risk_scan",
    173: "assign_staging_version",
    174: "unassign_staging_version",
    175: "disable_user_atlassian",
    176: "reset_credentials_atlassian",
    177: "ignore_applications",
    178: "restore_applications",
    179: "ignore_human_risks",
    180: "restore_human_risks",
    181: "ignore_devices",
    182: "restore_devices",
    183: "ignore_users",
    184: "restore_users",
    185: "add_to_watchlist",
    186: "remove_from_watchlist",
    187: "ignore_misconfigurations",
    188: "restore_misconfigurations",
}
USER_ACTIVITY_MODEL_NAMES = {
    0x00: "auth",
    0x01: "user",
    0x02: "protected_entity",
    0x03: "policy",
    0x04: "quarantine",
    0x05: "reports",
    0x06: "task",
    0x07: "settings",
    0x08: "virtualization_server",
    0x09: "package",
    0x0A: "credentials",
    0x0B: "update_server",
    0x0C: "product_update",
    0x0D: "active_directory",
    0x0E: "certificate",
    0x0F: "license",
    0x10: "portlet",
    0x11: "company",
    0x12: "quarantine_exchange",
    0x13: "integrations_config",
    0x14: "aws_subscriptions",
    0x15: "mail_server_settings",
    0x16: "proxy_settings",
    0x29: "auth_settings",
    0x17: "backup_settings",
    0x18: "policy_rules",
    0x19: "endpoint_update",
    0x1A: "endpoint_kit",
    0x1B: "auto_update_settings",
    0x1C: "application_inventory",
    0x1D: "encryption",
    0x20: "incident",
    0x21: "blocked_file",
    0x22: "security_group_rule",
    0x23: "ntsa",
    0x24: "security_provider",
    0x25: "network_cleanup_rules",
    0x26: "custom_fields",
    0x27: "email_security",
    0x28: "troubleshooting",
    0x30: "custom_rules_exclusions",
    0x31: "edr_custom_rules_detections",
    0x32: "auth_by_token",
    0x33: "model_api_key",
    0x34: "mobile_security",
    0x56: "cws",
    0x50: "exclusion_items",
    0x51: "exclusion_list",
    0x60: "remote_shell",
    0x61: "disconnect_all_users",
    0x52: "model_maintenance_window",
    0x53: "collect_investigation_package",
    0x71: "model_security_servers_global_settings",
    0x72: "model_sensors_management",
    0x73: "model_live_search_query",
    0x74: "model_integrity_monitor_rules",
    0x75: "model_integrity_monitor_rule_set",
    0x76: "model_gz_tags",
    0x77: "model_integrity_monitor_events",
    120: "model_mobile_security",
    121: "model_web_access_control_schedules",
    122: "model_cloud_workload_security",
    123: "model_easm",
    124: "model_update_staging",
    125: "model_live_search_s3_account_settings",
    126: "model_support_tool_s3_bucket_settings",
    127: "model_aws_settings",
    128: "model_risk_management_actions",
}

''' TODO research this mode
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def unix_ts_to_iso(timestamp: float) -> str:
    dt = datetime.fromtimestamp(timestamp, tz=timezone(timedelta(hours=2)))
    return dt.isoformat()


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # bitdefender_api_key = definition.parameters.get('bitdefender_api_key', None)
    pass


def collect_events(helper, event_writer):
    # get configuration parameters
    bitdefender_api_key = helper.get_global_setting("gravityzone_api_key")
    bitdefender_api_url = helper.get_global_setting("gravityzone_api_url")
    gz_company_id = helper.get_arg("gravityzone_company_id")

    # get proxy configuration
    proxy_enabled = helper.get_global_setting("enable_proxy")
    proxy_url = helper.get_global_setting("proxy_url")
    proxy_port = helper.get_global_setting("proxy_port")
    proxy_username = helper.get_global_setting("proxy_username")
    proxy_password = helper.get_global_setting("proxy_password")

    # Convert proxy_enabled to boolean if it's a string
    if isinstance(proxy_enabled, str):
        proxy_enabled = proxy_enabled.lower() in ('true', '1', 'yes', 'on')

    gz_api_client = GravityZoneApiClient(
        bitdefender_api_url,
        bitdefender_api_key,
        proxy_enabled=proxy_enabled,
        proxy_url=proxy_url,
        proxy_port=proxy_port,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
    )

    fetch_all_activity_logs(
        helper,
        event_writer,
        gz_api_client,
        gz_company_id,
        logs_per_page=100,
        period='lastWeek'
    )

    fetch_all_incidents(
        helper,
        event_writer,
        gz_api_client,
        gz_company_id
    )


@dataclass
class LogsFetchConfig:
    logs_per_page: int = 100
    period: str = 'lastWeek'
    ingestion_interval_days: int = 365
    checkpoint_cleanup_interval_days: int = 400
    max_retries: int = 3
    retry_backoff_factor: int = 2

    def __post_init__(self):
        if self.checkpoint_cleanup_interval_days < self.ingestion_interval_days:
            raise Exception(
                '[ActivityLogs] checkpoint_cleanup_interval_days cannot be less than ingestion_interval_days')


@dataclass
class IncidentsFetchConfig:
    incidents_per_page: int = 10
    ingestion_interval_days = 365
    checkpoint_cleanup_interval_days = 400
    max_retries: int = 3
    retry_backoff_factor: int = 2

    def __post_init__(self):
        if self.checkpoint_cleanup_interval_days < self.ingestion_interval_days:
            raise Exception('[Incidents] checkpoint_cleanup_interval_days cannot be less than ingestion_interval_days')


class GravityZoneApiClient:
    def __init__(self, api_url: str, api_key: str, proxy_enabled: bool = False, proxy_url: str = None,
                 proxy_port: int = None, proxy_username: str = None, proxy_password: str = None):
        """
        Initialize the GravityZone API client

        Args:
            api_url (str): Base API URL
            api_key (str): API authentication key
            proxy_enabled (bool): Whether to use proxy
            proxy_url (str): Proxy server URL (e.g., http://proxy.example.com)
            proxy_port (int): Proxy server port
            proxy_username (str): Proxy authentication username (optional)
            proxy_password (str): Proxy authentication password (optional)
        """
        self.api_url = api_url
        self.api_key = api_key
        self.api_url_internal = f"{api_url}/v1.0/jsonrpc/internal"
        self.api_url_incidents_v12 = f"{api_url}/v1.2/jsonrpc/incidents"

        # Configure proxy settings
        self.proxies = None

        if proxy_enabled and proxy_url:

            # Construct the proxy URL with authentication if provided
            if proxy_username and proxy_password:
                # Parse the provided proxy URL to extract components
                parsed_proxy = urlparse(proxy_url)
                proxy_url_str = f"{parsed_proxy.scheme}://{proxy_username}:{proxy_password}@{parsed_proxy.netloc}:{proxy_port}"
            else:
                proxy_url_str = f"{proxy_url}:{proxy_port}"

            # The 'requests' library expects a dictionary mapping protocol to the proxy URL
            self.proxies = {
                'http': proxy_url_str,
                'https': proxy_url_str
            }

    def get_activity_logs_for_company(
            self,
            company_id: str,
            period: str,
            page: int,
            per_page: int
    ) -> requests.Response:
        """
        Fetch activity logs for a company using the Bitdefender API

        Args:
            company_id (str): Company identifier
            period (str): Time period for logs
            page (int): The page number
            per_page (int): How many items per page

        Returns:
            requests.Response: API response object
        """
        json_payload = {
            "jsonrpc": "2.0",
            "method": "getActivityLogsForCompany",
            "params": {
                "companyId": company_id,
                "filters": {
                    "period": period
                },
                "page": page,
                "perPage": per_page
            },
            "id": "x"
        }

        return requests.post(
            self.api_url_internal,
            auth=(self.api_key, ''),
            headers={'Content-Type': 'application/json'},
            json=json_payload,
            verify=True,
            proxies=self.proxies
        )

    def get_incidents_list_for_company_v12(
            self,
            company_id: str,
            start_date: datetime,
            end_date: datetime,
            page: int,
            per_page: int
    ) -> requests.Response:
        """
        Fetch incidents for a company using the Bitdefender API

        Args:
            company_id (str): Company identifier
            start_date (datetime): Start date for incidents
            end_date (datetime): End date for incidents
            page (int): The page number
            per_page (int): How many items per page

        Returns:
            requests.Response: API response object
        """
        json_payload = {
            "jsonrpc": "2.0",
            "method": "getIncidentsList",
            "params": {
                "filters": {
                    "companyId": company_id,
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat()
                },
                "page": page,
                "perPage": per_page
            },
            "id": "x"
        }

        return requests.post(
            self.api_url_incidents_v12,
            auth=(self.api_key, ''),
            headers={'Content-Type': 'application/json'},
            json=json_payload,
            verify=True,
            proxies=self.proxies
        )


def fetch_all_activity_logs(helper, event_writer, gz_api_client, gz_company_id, **kwargs):
    config = LogsFetchConfig(**kwargs)
    fetcher = ActivityLogsFetcher(helper, event_writer, gz_api_client, gz_company_id, config)
    fetcher.fetch_all()


def fetch_all_incidents(helper, event_writer, gz_api_client, gz_company_id, **kwargs):
    config = IncidentsFetchConfig(**kwargs)
    fetcher = IncidentsFetcher(helper, event_writer, gz_api_client, gz_company_id, config)
    fetcher.fetch_all()


class ActivityLogsFetcher:
    _checkpoint_name = 'bitdefender-gravityzone-user-activity-checkpoint-v2'

    def __init__(self, helper, event_writer, gz_api_client: GravityZoneApiClient, company_id: str,
                 config: Optional[LogsFetchConfig] = None):
        self.helper = helper
        self.event_writer = event_writer
        self.gz_api_client = gz_api_client
        self.company_id = company_id
        self.config = config or LogsFetchConfig()

        self.ingestion_time = datetime.now()
        self.ingested_logs_map: dict = json.loads(helper.get_check_point(self._checkpoint_name) or '{}')
        self.ingested_logs_map_update_needed = False
        # self.helper.log_debug(f"[UserActivity] Got ingested logs map: {json.dumps(self.ingested_logs_map)}")

    def fetch_all(self) -> None:
        """Fetches and processes all activity logs with pagination."""
        try:
            current_page = 1
            while True:
                result = self._fetch_page(current_page)
                # time.sleep(2)
                items = result.get('result', {}).get('items', [])

                if not items:
                    break

                self._process_items(items)

                total_pages = result.get('result', {}).get('pagesCount', 0)
                self.helper.log_debug(f"[UserActivity] Processed page {current_page} of {total_pages}")

                if current_page >= total_pages:
                    break

                current_page += 1

        except Exception as e:
            self.helper.log_error(f"[UserActivity] Error in fetch_all: {str(e)}")
            raise

        finally:
            self.save_checkpoint()

    def _fetch_page(self, page: int) -> Dict[str, Any]:
        max_retries = self.config.max_retries

        for attempt in range(max_retries):
            try:
                response = self.gz_api_client.get_activity_logs_for_company(
                    self.company_id,
                    self.config.period,
                    page,
                    self.config.logs_per_page
                )
                response.raise_for_status()

                response_payload = response.json()

                if response_payload.get('error') is not None:
                    raise RuntimeError(
                        f"[[UserActivity] api method getActivityLogsForCompany returned error. Page: {page}. Error: {json.dumps(response_payload['error'])}")

                return response_payload
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"[UserActivity] Failed to fetch page {page} after {max_retries} attempts") from e
                # test error is logged correctly
                self.helper.log_warning(
                    f"[UserActivity] Retry {attempt + 1} (of {max_retries}) for page {page}. Got error: {str(e)}")
                sleep(self.config.retry_backoff_factor ** (attempt + 1))  # exponential backoff

    def _process_items(self, items: list) -> None:
        for item in items:
            log_id = item['_id']
            log_unix_timestamp = datetime.fromisoformat(item['created']).timestamp()

            # compare with logs saved in checkpoint
            if self.ingested_logs_map.get(log_id):
                # skip item if already ingested in splunk
                self.helper.log_debug(f"[UserActivity] Skipping activity log #{log_id}")
                continue

            self.ingested_logs_map[log_id] = self.ingestion_time.timestamp()
            self.ingested_logs_map_update_needed = True

            # Add computed fields before creating event
            item['model_name'] = USER_ACTIVITY_MODEL_NAMES.get(item.get('model', -1), 'Unknown')
            item['action_name'] = USER_ACTIVITY_ACTION_NAMES.get(item.get('action', -1), 'Unknown')

            event = self.helper.new_event(
                data=json.dumps(item),
                time=log_unix_timestamp,
                source=self.helper.get_input_type(),
                index=self.helper.get_output_index(),
                sourcetype=self.helper.get_sourcetype()
            )

            self.event_writer.write_event(event)

    def save_checkpoint(self):
        try:
            # remove from map logs ingested more than config.checkpoint_cleanup_interval_days ago
            # this is necessary to avoid checkpoint data getting too large
            now_ts = datetime.now().timestamp()
            cleanup_interval_seconds = timedelta(self.config.checkpoint_cleanup_interval_days).total_seconds()
            logs_to_remove = []
            for log_id, ingestion_time_ts in self.ingested_logs_map.items():
                if now_ts - ingestion_time_ts > cleanup_interval_seconds:
                    logs_to_remove.append(log_id)

            if len(logs_to_remove) > 0:
                # remove logs
                self.ingested_logs_map = {k: v for k, v in self.ingested_logs_map.items() if k not in logs_to_remove}
                self.ingested_logs_map_update_needed = True

            if self.ingested_logs_map_update_needed:
                checkpoint_value = json.dumps(self.ingested_logs_map)
                self.helper.save_check_point(self._checkpoint_name, checkpoint_value)
                self.helper.log_debug(f"[UserActivity] Saving checkpoint: {checkpoint_value}")

        except Exception as e:
            self.helper.log_warning(f"[UserActivity] Error while saving checkpoint: {str(e)}")


class IncidentsFetcher:
    _checkpoint_name = 'bitdefender-gravityzone-incidents-checkpoint'

    def __init__(self, helper, event_writer, gz_api_client: GravityZoneApiClient, company_id: str,
                 config: Optional[IncidentsFetchConfig] = None):
        self.helper = helper
        self.event_writer = event_writer
        self.gz_api_client = gz_api_client
        self.company_id = company_id
        self.config = config or IncidentsFetchConfig()

        self.ingestion_time = datetime.now()
        self.ingested_incidents_map: dict = json.loads(helper.get_check_point(self._checkpoint_name) or '{}')
        self.ingested_incidents_map_update_needed = False
        # self.helper.log_debug(f"[Incidents] Got ingested incidents map: {json.dumps(self.ingested_incidents_map)}")

    def fetch_all(self) -> None:
        """Fetches and processes all activity logs with pagination."""
        try:
            current_page = 1
            while True:
                result = self._fetch_page(current_page)
                # time.sleep(2)
                items = result.get('result', {}).get('items', [])

                if not items:
                    break

                self._process_items(items)

                total_pages = result.get('result', {}).get('pagesCount', 0)
                self.helper.log_debug(f"[Incidents] Processed page {current_page} of {total_pages}")

                if current_page >= total_pages:
                    break

                current_page += 1

        except Exception as e:
            self.helper.log_error(f"[Incidents] Error in fetch_all: {str(e)}")
            raise

        finally:
            self.save_checkpoint()

    def _fetch_page(self, page: int) -> Dict[str, Any]:
        max_retries = self.config.max_retries
        start_date = self.ingestion_time - timedelta(days=self.config.ingestion_interval_days)
        end_date = datetime.now() + timedelta(days=1)

        for attempt in range(max_retries):
            try:
                response = self.gz_api_client.get_incidents_list_for_company_v12(
                    self.company_id,
                    start_date,
                    end_date,
                    page,
                    self.config.incidents_per_page
                )
                response.raise_for_status()

                response_payload = response.json()

                if response_payload.get('error') is not None:
                    raise RuntimeError(
                        f"[Incidents] Api method getIncidentsList returned error. Page: {page}. Error: {json.dumps(response_payload['error'])}")

                return response_payload
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"[Incidents] Failed to fetch page {page} after {max_retries} attempts") from e
                # test error is logged correctly
                self.helper.log_debug(
                    f"[Incidents] Retry {attempt + 1} (of {max_retries}) for page {page}. Got error: {str(e)}")
                sleep(self.config.retry_backoff_factor ** (attempt + 1))  # exponential backoff

    def _process_items(self, items: list) -> None:
        for item in items:

            # compare with timestamp saved in checkpoint
            if self.ingested_incidents_map.get(item['incidentId']):
                # skip item if already ingested in splunk
                self.helper.log_debug(f"[Incidents] Skipping incident #{item['incidentNumber']} - {item['incidentId']}")
                continue

            self.ingested_incidents_map[item['incidentId']] = self.ingestion_time.timestamp()
            self.ingested_incidents_map_update_needed = True

            event = self.helper.new_event(
                data=json.dumps(item),
                time=datetime.fromisoformat(item['created']).timestamp(),
                source=self.helper.get_input_type(),
                index=self.helper.get_output_index(),
                sourcetype=self.helper.get_sourcetype()
            )
            self.helper.log_debug(f"Writing incident #{item['incidentNumber']} - {item['incidentId']}. Incident: {item}")
            self.event_writer.write_event(event)

    def save_checkpoint(self):
        try:
            # remove from map incidents ingested more than config.checkpoint_cleanup_interval_days ago
            # this is necessary to avoid checkpoint data getting too large
            now_ts = datetime.now().timestamp()
            cleanup_interval_seconds = timedelta(self.config.checkpoint_cleanup_interval_days).total_seconds()
            incidents_to_remove = []
            for incident_id, ingestion_time_ts in self.ingested_incidents_map.items():
                if now_ts - ingestion_time_ts > cleanup_interval_seconds:
                    incidents_to_remove.append(incident_id)

            if len(incidents_to_remove) > 0:
                # remove incidents
                self.ingested_incidents_map = {k: v for k, v in self.ingested_incidents_map.items() if
                                               k not in incidents_to_remove}
                self.ingested_incidents_map_update_needed = True

            if self.ingested_incidents_map_update_needed:
                checkpoint_value = json.dumps(self.ingested_incidents_map)
                self.helper.save_check_point(self._checkpoint_name, checkpoint_value)
                self.helper.log_debug(f"[Incidents] Saving checkpoint: {checkpoint_value}")

        except Exception as e:
            self.helper.log_warning(f"[Incidents] Error while saving checkpoint: {str(e)}")

