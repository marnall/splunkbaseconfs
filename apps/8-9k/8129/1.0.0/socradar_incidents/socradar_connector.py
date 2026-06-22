# -*- coding: utf-8 -*-
"""
Splunk SOAR App: SOCRadar Incidents v4 (Merged Edition) — v1.2.0
------------------------------------------------------------------
PURPOSE
  - Pull incidents from SOCRadar v4 API and create Splunk SOAR containers/artifacts
  - Merges ChatGPT's clean SOCRadar logic with SOAR template's testing utilities
  - Maintains durable state for deduplication and status change detection

HIGH-LEVEL FLOW
  Step 1.0: Load asset configuration and build HTTP session
  Step 2.0: Handle action dispatch ("test connectivity" | "on poll")
  Step 3.0: For "test connectivity": make a minimal API call and report success/failure
  Step 4.0: For "on poll": ingest incidents with pagination, rate limiting, and deduplication

DEDUP STRATEGY
  - Container SDI = alarm_id (one container per alarm)
  - Artifact SDI = f"{alarm_id}-{status}" (one artifact per (alarm_id, status))
  - Durable state maps alarm_id -> last_seen_status

STATE
  - Persistent across runs (PostgreSQL-backed)
  - Structure: {"alarm_status": { "<alarm_id>": "<status>" }, "last_updated": "<iso8601>"}
"""

from __future__ import annotations

import json
import time
import requests
import argparse
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

# Constants
SOCRADAR_API_BASE_URL = "https://platform.socradar.com/api"
API_TIMEOUT_SECONDS = 30
APP_VERSION = "1.0.0"
USER_AGENT = f"SOAR-SOCRadar-Merged/{APP_VERSION}"


class RetVal(tuple):
    """Return value tuple for consistent error handling (from SOAR template)"""
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class SOCRadarConnector(BaseConnector):
    """SOCRadar Incidents v4 Connector for Splunk SOAR"""

    def __init__(self):
        super(SOCRadarConnector, self).__init__()

        # Asset configuration (populated in initialize)
        self.company_id: Optional[str] = None
        self.api_key: Optional[str] = None
        self.lookback_days: int = 1
        self.max_pages_to_fetch: int = 50
        self.max_new_incidents_per_poll: int = 500
        self.verify_ssl_certificates: bool = True

        # HTTP session
        self.http_session: Optional[requests.Session] = None

        # State management
        self._state = None

    # ==================================================================
    # Step 1.0: Load asset configuration and build HTTP session
    # ==================================================================
    def initialize(self):
        """Setup before action execution"""
        # Load state for persistence
        self._state = self.load_state()
        if not self._state:
            self._state = {}

        # Get configuration
        asset_config: Dict[str, Any] = self.get_config() or {}

        self.company_id = asset_config.get("socradar_company_id")
        self.api_key = asset_config.get("socradar_api_key")
        self.lookback_days = int(asset_config.get("lookback_days", 1) or 1)
        self.max_pages_to_fetch = int(asset_config.get("max_pages", 50) or 50)
        self.max_new_incidents_per_poll = int(asset_config.get("max_incidents_per_poll", 500) or 500)
        self.verify_ssl_certificates = bool(asset_config.get("verify_ssl", True))
        self.container_label = asset_config.get("ingest", {}).get("container_label", "events")

        # Build requests session + optional proxies
        self.http_session = requests.Session()
        self.http_session.headers.update({"User-Agent": USER_AGENT})

        http_proxy = asset_config.get("http_proxy")
        https_proxy = asset_config.get("https_proxy")
        if http_proxy or https_proxy:
            proxies: Dict[str, str] = {}
            if http_proxy:
                proxies["http"] = http_proxy
            if https_proxy:
                proxies["https"] = https_proxy
            self.http_session.proxies.update(proxies)

        self.save_progress("Connector initialized successfully")
        return phantom.APP_SUCCESS

    # ==================================================================
    # Step 2.0: Action dispatch
    # ==================================================================
    def handle_action(self, param):
        """Route to action handlers"""
        action_name = self.get_action_identifier()

        self.debug_print(f"action_id: {action_name}")

        if action_name == "test_connectivity":
            return self._handle_test_connectivity(param)

        if action_name == "on_poll":
            return self._handle_on_poll(param)

        return self.set_status(phantom.APP_ERROR, f"Unsupported action: {action_name}")

    # ==================================================================
    # Step 3.0: Test Connectivity
    # ==================================================================
    def _handle_test_connectivity(self, param):
        """Test API connectivity"""
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Step 3.1: Validate required fields
        if not (self.company_id and self.api_key):
            return action_result.set_status(
                phantom.APP_ERROR,
                "Missing company_id or api_key in asset configuration"
            )

        self.save_progress("Testing SOCRadar API connectivity...")

        # Step 3.2: Minimal GET request
        url = f"{SOCRADAR_API_BASE_URL}/company/{self.company_id}/incidents/v4"
        try:
            response = self.http_session.get(
                url,
                params={"key": self.api_key, "limit": 1, "page": 1},
                timeout=API_TIMEOUT_SECONDS,
                verify=self.verify_ssl_certificates,
            )
            status_code = response.status_code

            if status_code == 401:
                self.save_progress("Test Connectivity Failed - Unauthorized")
                return action_result.set_status(
                    phantom.APP_ERROR,
                    "Unauthorized (401). Please check your API key and company ID."
                )

            if status_code not in (200, 204):
                self.save_progress(f"Test Connectivity Failed - HTTP {status_code}")
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"HTTP {status_code}: {response.text[:300]}"
                )

            # Success
            self.save_progress("Test Connectivity Passed")
            return action_result.set_status(
                phantom.APP_SUCCESS,
                "Successfully connected to SOCRadar API"
            )

        except requests.exceptions.Timeout:
            self.save_progress("Test Connectivity Failed - Timeout")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Request timeout after {API_TIMEOUT_SECONDS} seconds"
            )
        except requests.exceptions.ConnectionError as e:
            self.save_progress("Test Connectivity Failed - Connection Error")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Connection error: {str(e)}"
            )
        except Exception as e:
            self.save_progress("Test Connectivity Failed - Unexpected Error")
            return action_result.set_status(
                phantom.APP_ERROR,
                f"Connectivity error: {str(e)}"
            )

    # ==================================================================
    # Step 4.0: on_poll — Main ingest loop
    # ==================================================================
    def _handle_on_poll(self, param):
        """
        Ingest SOCRadar incidents v4 into Splunk SOAR.

        Key properties:
          - Pagination (limit=100 per page)
          - 429 rate-limit backoff (30s, then 60s)
          - Per-poll cap (default 500 incidents)
          - Durable state with alarm_id -> status
          - SDI-based deduplication (container & artifact)
        """
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Validate configuration
        if not (self.company_id and self.api_key):
            return action_result.set_status(
                phantom.APP_ERROR,
                "Missing company_id or api_key in asset configuration"
            )

        # Step 4.1: Load durable state and compute time window
        durable_state: Dict[str, Any] = self._state or {}
        alarm_status_map: Dict[str, Any] = durable_state.get("alarm_status", {})

        now_utc = datetime.now(timezone.utc)
        start_epoch_seconds = int((now_utc - timedelta(days=max(1, self.lookback_days))).timestamp())
        end_epoch_seconds = int(now_utc.timestamp())

        api_endpoint_url = f"{SOCRADAR_API_BASE_URL}/company/{self.company_id}/incidents/v4"
        current_page_number = 1
        new_or_updated_counter = 0
        skipped_same_status_counter = 0
        consecutive_rate_limit_counter = 0

        self.save_progress(f"Starting ingestion for last {self.lookback_days} day(s)")

        # Step 4.2: Iterate paginated results
        while (current_page_number <= self.max_pages_to_fetch and
               new_or_updated_counter < self.max_new_incidents_per_poll):

            request_params = {
                "key": self.api_key,
                "limit": 100,
                "page": current_page_number,
                "start_date": start_epoch_seconds,
                "end_date": end_epoch_seconds,
            }

            # Calculate and show progress
            progress_pct = min(100, int((current_page_number / self.max_pages_to_fetch) * 100))
            self.save_progress(
                f"Fetching page {current_page_number}/{self.max_pages_to_fetch} "
                f"({progress_pct}% complete) - "
                f"{new_or_updated_counter} incidents processed"
            )

            try:
                response = self.http_session.get(
                    api_endpoint_url,
                    params=request_params,
                    timeout=API_TIMEOUT_SECONDS,
                    verify=self.verify_ssl_certificates,
                )
                status_code = response.status_code

                # Step 4.2.1: Handle rate limiting
                response_text_lower = (response.text or "").lower()
                if status_code == 429 or ("rate limit" in response_text_lower):
                    consecutive_rate_limit_counter += 1
                    wait_seconds = 30 if consecutive_rate_limit_counter == 1 else 60
                    self.save_progress(
                        f"Rate limit encountered. Waiting {wait_seconds}s "
                        f"(attempt #{consecutive_rate_limit_counter})"
                    )
                    time.sleep(wait_seconds)
                    continue

                consecutive_rate_limit_counter = 0

                # Step 4.2.2: Handle auth/other errors
                if status_code == 401:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        "Unauthorized (401). Check credentials."
                    )
                if status_code != 200:
                    return action_result.set_status(
                        phantom.APP_ERROR,
                        f"HTTP {status_code}: {response.text[:300]}"
                    )

                # Step 4.2.3: Parse page
                payload = response.json() if response.text else {}
                incident_list = payload.get("data", [])

                # Debug logging
                self.save_progress(f"API Response: HTTP {status_code}, Total records in response: {len(incident_list)}")
                self.debug_print(f"API URL: {api_endpoint_url}")
                self.debug_print(f"API Params: {request_params}")
                self.debug_print(f"Response payload keys: {list(payload.keys()) if payload else 'None'}")

                if not incident_list:
                    self.save_progress(f"No incidents found on page {current_page_number}. Response: {payload}")
                    break

                # Step 4.3: Process each incident
                for incident in incident_list:
                    # Normalize/shorten large fields
                    incident = self._normalize_incident(incident)

                    alarm_id_value = incident.get("alarm_id")
                    current_status_value = incident.get("status", "N/A")

                    if not alarm_id_value:
                        continue

                    alarm_id_str = str(alarm_id_value)

                    # Step 4.3.2: Deduplicate unchanged alarms via durable state
                    previous_status_value = alarm_status_map.get(alarm_id_str)
                    if previous_status_value is not None and previous_status_value == current_status_value:
                        skipped_same_status_counter += 1
                        continue

                    # Step 4.3.3: Mark status change (if any)
                    if previous_status_value is not None and previous_status_value != current_status_value:
                        incident["status_changed"] = True
                        incident["previous_status"] = previous_status_value
                        self.debug_print(f"Status change detected for alarm {alarm_id_str}: "
                                       f"{previous_status_value} -> {current_status_value}")

                    # Step 4.3.4: Build deep link
                    if self.company_id:
                        incident["alarm_link"] = (
                            f"https://platform.socradar.com/app/company/{self.company_id}/"
                            f"alarm-management?tab=approved&alarmId={alarm_id_value}"
                        )

                    # Step 4.3.5: Parse event timestamp
                    event_epoch_seconds = self._parse_incident_timestamp(incident)

                    # Step 4.4: Create/Upsert container (SDI = alarm_id)
                    container_id = self._create_container(incident, alarm_id_str, alarm_id_value)
                    if not container_id:
                        continue

                    # Step 4.5: Create artifact (SDI = alarm_id-status)
                    self._create_artifact(
                        incident, container_id, alarm_id_str,
                        alarm_id_value, current_status_value, event_epoch_seconds
                    )

                    # Step 4.6: Update counters and durable state
                    alarm_status_map[alarm_id_str] = current_status_value
                    new_or_updated_counter += 1

                    if new_or_updated_counter >= self.max_new_incidents_per_poll:
                        break

                # Step 4.2.4: End-of-page checks
                if new_or_updated_counter >= self.max_new_incidents_per_poll:
                    self.save_progress(
                        f"Reached per-poll cap: {self.max_new_incidents_per_poll} incidents"
                    )
                    break

                if len(incident_list) < 100:
                    self.save_progress("Last page reached.")
                    break

                current_page_number += 1
                time.sleep(2)  # Politeness delay between pages

            except Exception as error:
                return action_result.set_status(
                    phantom.APP_ERROR,
                    f"on_poll error on page {current_page_number}: {error}"
                )

        # Step 4.7: Trim and save state, produce summary
        if len(alarm_status_map) > 10000:
            # Keep most recent 10000 alarms
            items = sorted(alarm_status_map.items(), key=lambda item: item[0])
            alarm_status_map = dict(items[-10000:])
            self.debug_print("Trimmed state to 10000 most recent alarms")

        durable_state["alarm_status"] = alarm_status_map
        durable_state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._state = durable_state

        # Summary
        action_result.update_summary({
            "new_or_updated": new_or_updated_counter,
            "skipped_same_status": skipped_same_status_counter,
            "pages_traversed": current_page_number,
            "total_tracked": len(alarm_status_map)
        })

        self.save_progress(
            f"Ingestion complete: {new_or_updated_counter} new/updated, "
            f"{skipped_same_status_counter} skipped"
        )

        return action_result.set_status(phantom.APP_SUCCESS)

    # ==================================================================
    # Helper Methods
    # ==================================================================

    def _normalize_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and truncate large incident fields"""
        def truncate_long_text(value, max_length=5000):
            text = "" if value is None else str(value)
            return text if len(text) <= max_length else (text[:max_length] + "...")

        if isinstance(incident, dict):
            # Truncate large text fields
            if "alarm_text" in incident:
                incident["alarm_text"] = truncate_long_text(incident.get("alarm_text"))
            if "alarm_response" in incident:
                incident["alarm_response"] = truncate_long_text(incident.get("alarm_response"))

            # Process alarm type details
            alarm_type_details = incident.get("alarm_type_details") or {}
            if isinstance(alarm_type_details, dict):
                if "alarm_default_mitigation_plan" in alarm_type_details:
                    alarm_type_details["alarm_default_mitigation_plan"] = truncate_long_text(
                        alarm_type_details.get("alarm_default_mitigation_plan")
                    )
                incident["alarm_main_type"] = alarm_type_details.get("alarm_main_type", "N/A")
                incident["alarm_sub_type"] = alarm_type_details.get("alarm_sub_type", "N/A")
            else:
                incident["alarm_main_type"] = incident.get("alarm_main_type", "N/A")
                incident["alarm_sub_type"] = incident.get("alarm_sub_type", "N/A")

        return incident

    def _parse_incident_timestamp(self, incident: Dict[str, Any]) -> Optional[int]:
        """Parse incident timestamp to epoch seconds"""
        incident_date_string = incident.get("date")  # e.g., "YYYY-MM-DD HH:MM:SS"
        if incident_date_string:
            try:
                return int(
                    datetime.strptime(incident_date_string, "%Y-%m-%d %H:%M:%S")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                )
            except Exception:
                pass
        return None

    def _create_container(self, incident: Dict[str, Any], alarm_id_str: str,
                         alarm_id_value: Any) -> Optional[int]:
        """Create or update SOAR container for incident"""
        container_definition = {
            "name": f"SOCRadar Alarm {alarm_id_value}",
            "description": f"{incident.get('alarm_main_type', 'N/A')}/{incident.get('alarm_sub_type', 'N/A')}",
            "label": self.container_label,
            "severity": self._map_severity(incident),
            "source_data_identifier": alarm_id_str,  # Ensures 1 container per alarm
        }

        ret_val, message, container_id = self.save_container(container_definition)

        if not container_id:
            self.debug_print(f"save_container failed: {message}")
            return None

        return container_id

    def _create_artifact(self, incident: Dict[str, Any], container_id: int,
                        alarm_id_str: str, alarm_id_value: Any,
                        current_status_value: str, event_epoch_seconds: Optional[int]):
        """Create SOAR artifact for incident"""
        # Build CEF payload
        cef_payload = {
            "alarm_id": alarm_id_value,
            "status": current_status_value,
            "alarm_link": incident.get("alarm_link"),
            "alarm_main_type": incident.get("alarm_main_type"),
            "alarm_sub_type": incident.get("alarm_sub_type"),
            "company_id": self.company_id,
        }

        # Add IOC fields if present
        cef_types = {}
        if incident.get("ip"):
            cef_payload["ip"] = incident["ip"]
            cef_types["ip"] = ["ip"]
        if incident.get("url"):
            cef_payload["url"] = incident["url"]
            cef_types["url"] = ["url"]
        if incident.get("hash"):
            cef_payload["hash"] = incident["hash"]
            cef_types["hash"] = ["hash", "sha256"]
        if incident.get("domain"):
            cef_payload["domain"] = incident["domain"]
            cef_types["domain"] = ["domain"]

        artifact_definition = {
            "container_id": container_id,
            "name": f"Alarm {alarm_id_value} artifact",
            "label": "event",
            "cef": cef_payload,
            "cef_types": cef_types,
            # Status is part of SDI, so same status won't create duplicate artifacts:
            "source_data_identifier": f"{alarm_id_str}-{current_status_value}",
            "run_automation": True  # Trigger playbooks
        }

        if event_epoch_seconds:
            artifact_definition["start_time"] = datetime.utcfromtimestamp(event_epoch_seconds).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        ret_val, message, artifact_id = self.save_artifact(artifact_definition)

        if not artifact_id:
            self.debug_print(f"save_artifact failed: {message}")

    def _map_severity(self, incident: Dict[str, Any]) -> str:
        """Map incident severity to SOAR severity levels"""
        severity_value = (incident.get("severity") or "").lower()
        if severity_value in ("critical", "high", "medium", "low"):
            return severity_value

        # Fallback based on status
        status_value = (incident.get("status") or "").lower()
        if status_value in ("critical", "high"):
            return "high"

        return "medium"

    def finalize(self):
        """Save state and cleanup"""
        # Save state
        if self._state:
            self.save_state(self._state)
            self.debug_print(f"State saved with {len(self._state.get('alarm_status', {}))} alarms tracked")

        # Close session
        if self.http_session:
            self.http_session.close()

        return phantom.APP_SUCCESS


# ==================================================================
# Main function for local testing (from SOAR template)
# ==================================================================
def main():
    """Local testing entry point"""
    import argparse
    import sys

    argparser = argparse.ArgumentParser()
    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            print("Authenticating with Phantom/SOAR platform...")
            # This would connect to actual SOAR instance for testing
            # Simplified for this implementation
            session_id = "test_session"
        except Exception as e:
            print(f"Unable to get session id from platform. Error: {str(e)}")
            sys.exit(1)

    # Read test JSON
    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = SOCRadarConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == '__main__':
    main()