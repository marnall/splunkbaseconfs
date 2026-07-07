# encoding = utf-8
"""Alerts Dashboard API Client for Cisco Cloud Security Splunk App."""

import sys
import json
import urllib.parse
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from exceptions import ReportingAPIClientException
from enums import AlertingAPIEndpoints, ALERT_SEVERITY_LABEL_MAP, ALERT_STATUS_LABEL_MAP
from reporting_api_client import ReportingAPIClient
from global_org_client import GlobalOrgClient


@dataclass
class AlertsSearchFilters:
    """
    Data class for Alerts search filter validation.
    Validates query parameters according to Cisco Cloud Security API specification.
    
    API Reference: https://developer.cisco.com/docs/cloud-security/list-alerts/
    """
    severity: Optional[str] = None
    status: Optional[str] = None
    alert_name: Optional[str] = None
    modified_at: Optional[str] = None
    
    # Validation constants
    SEVERITY_MAP = {
        'high': 1,
        'medium': 2,
        'low': 3,
        'info': 4
    }
    
    STATUS_MAP = {
        'active': 1,
        'dismissed': 2,
        'resolved': 3,
        'archived': 4
    }
    
    def __post_init__(self):
        """Validate all fields after initialization."""
        self._validate_all()
    
    def _validate_all(self):
        """Validate all search filter fields."""
        if self.severity is not None:
            self.severity = self._validate_severity(self.severity)
        if self.status is not None:
            self.status = self._validate_status(self.status)
        if self.modified_at is not None:
            self.modified_at = self._validate_modified_at(self.modified_at)
    
    def _validate_severity(self, value: str) -> int:
        """
        Validate severity filter.
        
        Allowed values: 1 (High), 2 (Medium), 3 (Low), 4 (Info)
        Also accepts: 'high', 'medium', 'low', 'info' (case-insensitive)
        
        Raises:
            Exception: If invalid severity value
        """
        normalized = str(value).lower().strip()
        if normalized not in self.SEVERITY_MAP:
            raise Exception(
                "Invalid 'severity' filter. Allowed values: High, Medium, Low, Info"
            )
        return self.SEVERITY_MAP[normalized]
    
    def _validate_status(self, value: str) -> int:
        """
        Validate status filter.
        
        Allowed values: 1 (Active), 2 (Dismissed), 3 (Resolved), 4 (Archived)
        Also accepts: 'active', 'dismissed', 'resolved', 'archived' (case-insensitive)
        
        Raises:
            Exception: If invalid status value
        """
        normalized = str(value).lower().strip()
        if normalized not in self.STATUS_MAP:
            raise Exception(
                "Invalid 'status' filter. Allowed values: Active, Dismissed, Resolved, Archived"
            )
        return self.STATUS_MAP[normalized]
    
    def _validate_modified_at(self, value: str) -> str:
        """
        Validate modified_at filter.
        
        Must be ISO 8601 format: YYYY-MM-DD HH:MM:SS
        
        Raises:
            Exception: If invalid datetime format
        """
        value = str(value).strip()
        try:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise Exception(
                "Invalid 'modified_at' filter. Must be in format: YYYY-MM-DD HH:MM:SS (e.g., 2026-02-20 00:00:00)"
            )
        return value


class AlertsDashboardAPIClient(PersistentServerConnectionApplication):
    """API Client for Alerts Dashboard - handles alerts listing, filtering, and status updates."""

    def __init__(self, command_line, command_arg):
        """Initialize API client instance variables."""
        PersistentServerConnectionApplication.__init__(self)
        self.reporting_api_client_inst = None
        self.session_token = None
        self.global_org_client = None
        self._logger = Logger()

    def _calculate_total_from_severity(self, severity_counts):
        """Calculate total alerts from severity counts dict."""
        return (
            severity_counts.get('high', severity_counts.get('1', 0)) +
            severity_counts.get('medium', severity_counts.get('2', 0)) +
            severity_counts.get('low', severity_counts.get('3', 0)) +
            severity_counts.get('info', severity_counts.get('4', 0))
        )

    def _build_filters(self, from_date=None, to_date=None, severity=None, status=None, alert_name=None, modified_at=None):
        """Build filters dict for API request."""
        filters = {}
        if from_date and to_date:
            filters['time_range'] = {'start_time': from_date, 'end_time': to_date}
        if severity:
            filters['severity'] = severity
        if status:
            filters['status'] = status
        if alert_name:
            filters['alert_name'] = alert_name
        if modified_at:
            filters['modified_at'] = modified_at
        return filters

    def _append_filters_to_path(self, path, filters):
        """Append filters JSON to API path if filters exist."""
        if filters:
            filters_json = json.dumps(filters)
            path += "&filters={}".format(urllib.parse.quote(filters_json))
        return path

    def fetch_result(self, query, limit=20, offset=0, from_date=None, to_date=None, severity=None,
                     status=None, alert_name=None, entity_ids=None,
                     new_status=None, modified_at=None):
        """Fetch result for alerts API based on query type."""
        org_id = self.global_org_client.global_org
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'
        }

        if query == 'listAlerts':
            path = AlertingAPIEndpoints.LIST_ALERTS.value.format(org_id, limit, offset)
            filters = self._build_filters(from_date, to_date, severity, status, alert_name, modified_at)
            path = self._append_filters_to_path(path, filters)

            rsp = self.send_request(path, headers)
            rsp_json = rsp.json()
            
            response = []
            alerts = rsp_json.get('alerts', [])
            for alert in alerts:
                response.append(self._transform_alert(alert))
            
            severity_counts = rsp_json.get('severityCounts', {})
            total_from_severity = self._calculate_total_from_severity(severity_counts)
            api_total = total_from_severity if total_from_severity > 0 else len(alerts)
            
            return {
                "alerts": response,
                "total": api_total,
                "severityCounts": severity_counts,
                "limit": limit,
                "offset": offset
            }

        elif query == 'getAlertCount':
            path = AlertingAPIEndpoints.GET_ALERT_COUNT.value.format(org_id)
            filters = self._build_filters(from_date, to_date)
            path = self._append_filters_to_path(path, filters)

            rsp = self.send_request(path, headers)
            rsp_json = rsp.json()
            
            severity_counts = rsp_json.get('severityCounts', {})
            api_total = self._calculate_total_from_severity(severity_counts)
            
            return {
                "total": api_total,
                "activeCount": rsp_json.get('activeAlertsCount', rsp_json.get('total', 0))
            }

        elif query == 'getSeverityCounts':
            path = AlertingAPIEndpoints.LIST_ALERTS.value.format(org_id, 1, 0)
            filters = self._build_filters(from_date, to_date)
            path = self._append_filters_to_path(path, filters)

            rsp = self.send_request(path, headers)
            rsp_json = rsp.json()

            severity_counts = rsp_json.get('severityCounts', {})
            total_active_count = rsp_json.get('total', 0)
            
            high_count = severity_counts.get('high', severity_counts.get('1', 0))
            medium_count = severity_counts.get('medium', severity_counts.get('2', 0))
            low_count = severity_counts.get('low', severity_counts.get('3', 0))
            info_count = severity_counts.get('info', severity_counts.get('4', 0))
            
            total =  self._calculate_total_from_severity(severity_counts)
            
            return {
                "total": total,
                "total_active_count": total_active_count,
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
                "info": info_count
            }

        elif query == 'updateAlertStatus':
            if not entity_ids or not new_status:
                raise Exception("entity_ids and new_status are required for updateAlertStatus")
            
            path = AlertingAPIEndpoints.UPDATE_ALERTS_STATUS.value.format(org_id)
            payload = {
                "status": int(new_status),
                "entity_ids": entity_ids
            }
            
            rsp = self.send_put_request(path, headers, payload)
            return rsp.json()

        else:
            raise Exception(
                'Invalid query! Expected one of ["listAlerts", "getAlertCount", '
                '"getSeverityCounts", "updateAlertStatus"].'
            )

    def _transform_alert(self, alert):
        """Transform alert response to UI-friendly format."""
        return {
            "alertId": alert.get('alertId', ''),
            "name": alert.get('name', ''),
            "severity": alert.get('severity', 4),
            "severityLabel": self._get_severity_label(alert.get('severity', 4)),
            "status": alert.get('status', 1),
            "statusLabel": self._get_status_label(alert.get('status', 1)),
            "ruleId": alert.get('rule_id', ''),
            "ruleTypeId": alert.get('rule_type_id', ''),
            "organizationId": alert.get('organization_id', ''),
            "createdAt": alert.get('created_at', ''),
            "modifiedAt": alert.get('modified_at', ''),
            "description": alert.get('description', '')
        }

    def _get_severity_label(self, severity_code):
        """Convert severity code to label."""
        return ALERT_SEVERITY_LABEL_MAP.get(severity_code, 'Unknown')

    def _get_status_label(self, status_code):
        """Convert status code to label."""
        return ALERT_STATUS_LABEL_MAP.get(status_code, 'Unknown')

    def send_request(self, path, headers):
        """Send GET request via reporting API client."""
        try:
            response = self.reporting_api_client_inst.send_request(path, 'get', headers=headers)
            return response
        except Exception as e:
            self._logger.error("alerts_dashboard_api_client send_request error: {0}".format(str(e)))
            raise

    def send_put_request(self, path, headers, payload):
        """Send PUT request via reporting API client."""
        try:
            response = self.reporting_api_client_inst.send_request(
                path, 'put', headers=headers, payload=json.dumps(payload)
            )
            return response
        except Exception as e:
            self._logger.error("alerts_dashboard_api_client send_put_request error: {0}".format(str(e)))
            raise

    def _validate_limit(self, value, default=20):
        """Validate limit parameter - must be a positive integer."""
        if value is None:
            return default
        try:
            limit = int(value)
            if limit <= 0:
                raise ValueError("limit must be a positive integer")
            if limit > 100:
                limit = 100
            return limit
        except ValueError:
            raise Exception("Invalid 'limit' parameter - must be a positive integer (1-100)")

    def _validate_offset(self, value, default=0):
        """Validate offset parameter - must be a non-negative integer."""
        if value is None:
            return default
        try:
            offset = int(value)
            if offset < 0:
                raise ValueError("offset must be non-negative")
            return offset
        except ValueError:
            raise Exception("Invalid 'offset' parameter - must be a non-negative integer")

    def _get_date_range(self, params):
        """Extract date range strings from params (format: YYYY-MM-DD HH:MM:SS)."""
        from_date = params["query"].get('from', None)
        to_date = params["query"].get('to', None)
        if from_date:
            from_date = str(from_date).strip()
            try:
                datetime.strptime(from_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise Exception("Invalid 'from' parameter - must be in format: YYYY-MM-DD HH:MM:SS")
        if to_date:
            to_date = str(to_date).strip()
            try:
                datetime.strptime(to_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise Exception("Invalid 'to' parameter - must be in format: YYYY-MM-DD HH:MM:SS")
        if (from_date and not to_date) or (to_date and not from_date):
            raise Exception("Both 'from' and 'to' parameters must be provided together")
        return from_date, to_date

    def handle(self, in_string):
        """Process incoming request and route to appropriate query handler."""
        try:
            response = []
            params = Common().parse_in_string(in_string)
            self.session_token = params['session']['authtoken']
            self.reporting_api_client_inst = ReportingAPIClient(self.session_token)
            self.global_org_client = GlobalOrgClient(self.session_token)

            query = params["query"].get('query', '')

            if query == "listAlerts":
                limit = self._validate_limit(params["query"].get('limit'))
                offset = self._validate_offset(params["query"].get('offset'))
                from_date, to_date = self._get_date_range(params)

                search_filters = AlertsSearchFilters(
                    severity=params["query"].get('severity', None),
                    status=params["query"].get('status', None),
                    alert_name=params["query"].get('alert_name', None),
                    modified_at=params["query"].get('modified_at', None)
                )

                response = self.fetch_result(
                    query,
                    limit=limit,
                    offset=offset,
                    from_date=from_date,
                    to_date=to_date,
                    severity=search_filters.severity,
                    status=search_filters.status,
                    alert_name=search_filters.alert_name,
                    modified_at=search_filters.modified_at
                )

            elif query == "getAlertCount":
                from_date, to_date = self._get_date_range(params)
                response = self.fetch_result(query, from_date=from_date, to_date=to_date)

            elif query == "getSeverityCounts":
                from_date, to_date = self._get_date_range(params)
                response = self.fetch_result(query, from_date=from_date, to_date=to_date)

            elif query == "updateAlertStatus":
                put_body = json.loads(params.get('payload', '{}'))
                entity_ids_param = put_body.get('entity_ids', [])
                new_status = put_body.get('new_status', None)
                
                if isinstance(entity_ids_param, str):
                    if entity_ids_param.startswith('['):
                        entity_ids = json.loads(entity_ids_param)
                    else:
                        entity_ids = [entity_ids_param]
                elif isinstance(entity_ids_param, list):
                    entity_ids = entity_ids_param
                else:
                    entity_ids = []
                
                if not entity_ids:
                    raise Exception("entity_ids is required")
                if not new_status:
                    raise Exception("new_status is required")

                response = self.fetch_result(
                    query,
                    entity_ids=entity_ids,
                    new_status=new_status
                )

            else:
                raise Exception(
                    'Invalid query! Expected one of ["listAlerts", "getAlertCount", '
                    '"getSeverityCounts", "updateAlertStatus"].'
                )

            return {"payload": response, "status": 200}

        except ReportingAPIClientException as e:
            self._logger.error("API: alerts_dashboard_api_client, ReportingAPIClientException: {0}".format(str(e)))
            return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
        except Exception as e:
            self._logger.error("API: alerts_dashboard_api_client, Exception: {0}".format(str(e)))
            return {"payload": {"error_msg": str(e)}, "status": 500}
