# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#!/usr/bin/python
# -----------------------------------------
# Phantom App Connector python file
# -----------------------------------------

import json
from datetime import UTC, datetime, timedelta

import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from cyberintalerts_consts import (
    ALERTS_ENDPOINT,
    ALERTS_STATUS_ENDPOINT,
    CREDENTIALS_BY_DOMAIN_ENDPOINT,
    CREDENTIALS_BY_EMAIL_ENDPOINT,
    CVE_GET_BY_ID_ENDPOINT,
    IOC_DOMAIN_ENDPOINT,
    IOC_FILE_SHA256_ENDPOINT,
    IOC_IPV4_ENDPOINT,
    IOC_URL_ENDPOINT,
    TAKEDOWN_REQUEST_ENDPOINT,
    TAKEDOWN_SUBMIT_ENDPOINT,
    ClosureReason,
    Status,
    TakedownReason,
)


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


def map_severity(severity_str):
    """Maps Cyberint severity to Splunk SOAR severity."""
    if not severity_str:
        return "low"
    sev_lower = severity_str.lower()
    if sev_lower == "very_high":
        return "high"
    if sev_lower in ["high", "medium", "low"]:
        return sev_lower
    return "low"


class CyberintAlertsConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._max_fetch = None
        self._include_csv = None
        self._start_time = None
        self._fetch_type = None
        self._fetch_environment = None
        self._fetch_status = None
        self._fetch_severity = None
        self._state = None
        self._base_url = None
        self._access_token = None
        self._customer_id = None
        self._customer_name = None

    def _get_custom_headers(self):
        app_json = self.get_app_json()
        config = self.get_config()
        return {
            "X-Integration-Type": "Splunk SOAR",
            "X-Integration-Instance-Name": config.get("asset_name"),
            "X-Integration-Instance-Id": str(self.get_asset_id()),
            "X-Integration-Customer-Name": self._customer_name,
            "X-Integration-Version": app_json.get("app_version"),
        }

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        self._base_url = config.get("base_url")
        self._access_token = config.get("access_token")
        self._customer_name = config.get("customer_name")
        self._fetch_severity = config.get("fetch_severity")
        self._fetch_status = config.get("fetch_status")
        self._fetch_environment = config.get("fetch_environment")
        self._fetch_type = config.get("fetch_type")
        self._start_time = config.get("start_time", "Last 24 Hours")
        self._max_fetch = config.get("max_fetch", 10)
        self._include_csv = config.get("include_csv", False)
        return phantom.APP_SUCCESS

    @staticmethod
    def _parse_start_time(start_time):
        deltas = {
            "Last 1 Hour": timedelta(hours=1),
            "Last 24 Hours": timedelta(hours=24),
            "Last 7 Days": timedelta(days=7),
            "Last 30 Days": timedelta(days=30),
            "Last 90 Days": timedelta(days=90),
        }
        delta = deltas.get(start_time, timedelta(hours=24))
        now = datetime.now(UTC)
        return (now - delta).strftime("%Y-%m-%dT%H:%M:%SZ"), now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _build_alerts_request_body(self):
        body = {"page": 1}
        filters = {}
        if self._fetch_severity:
            filters["severity"] = [s.strip() for s in self._fetch_severity.split(",") if s.strip()]
        if self._fetch_status:
            filters["status"] = [s.strip() for s in self._fetch_status.split(",") if s.strip()]
        if self._fetch_environment:
            filters["environments"] = [s.strip() for s in self._fetch_environment.split(",") if s.strip()]
        if self._fetch_type:
            filters["type"] = [s.strip() for s in self._fetch_type.split(",") if s.strip()]
        if self._start_time:
            date_from, date_to = self._parse_start_time(self._start_time)
            filters["created_date"] = {"from": date_from, "to": date_to}
        if filters:
            body["filters"] = filters
        if self._max_fetch:
            body["size"] = int(self._max_fetch)
        if self._include_csv:
            body["include_csv_attachments_as_json_content"] = True
        return body

    def _process_response(self, r, action_result):
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        if "json" in r.headers.get("Content-Type", ""):
            try:
                resp_json = r.json()
            except Exception as e:
                return RetVal(
                    action_result.set_status(phantom.APP_ERROR, f"Unable to parse JSON response. Error: {e}"),
                    None,
                )
            if 200 <= r.status_code < 399:
                return RetVal(phantom.APP_SUCCESS, resp_json)
            message = f"Error from server. Status Code: {r.status_code} Data from server: {r.text}"
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

        if "html" in r.headers.get("Content-Type", ""):
            try:
                soup = BeautifulSoup(r.text, "html.parser")
                error_text = "\n".join([x.strip() for x in soup.text.split("\n") if x.strip()])
            except Exception:
                error_text = "Cannot parse error details"
            message = f"Status Code: {r.status_code}. Data from server:\n{error_text}\n"
            return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

        if not r.text:
            if r.status_code == 200:
                return RetVal(phantom.APP_SUCCESS, {})
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
                None,
            )

        message = f"Can't process response from server. Status Code: {r.status_code} Data from server: {r.text}"
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, method="get", **kwargs):
        config = self.get_config()
        cookies = {"access_token": self._access_token}
        kwargs["cookies"] = cookies

        headers = self._get_custom_headers()
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"),
                None,
            )

        url = self._base_url + endpoint
        try:
            r = request_func(url, verify=config.get("verify_server_cert", False), **kwargs)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Error Connecting to server. Details: {e}"),
                None,
            )

        return self._process_response(r, action_result)

    def _get_full_alert_from_ref_id(self, ref_ids: list[str], action_result):
        full_alerts = []
        for ref_id in ref_ids:
            ret_val, response = self._make_rest_call(f"{ALERTS_ENDPOINT}/{ref_id}", action_result)
            if phantom.is_fail(ret_val):
                return ret_val, None
            full_alerts.append(response["alert"])
        return phantom.APP_SUCCESS, full_alerts

    def _enrich_alert_indicators(self, alerts: list[dict], action_result):
        for alert in alerts:
            ref_id = alert.get("ref_id")
            for idx, indicator in enumerate(alert["indicators"]):
                ret_val, response = self._make_rest_call(
                    f"{ALERTS_ENDPOINT}/{ref_id}/indicators/{indicator['id']}",
                    action_result,
                )
                if phantom.is_fail(ret_val):
                    return ret_val, None
                alert["indicators"][idx] = response
        return phantom.APP_SUCCESS, alerts

    def _handle_get_enriched_alerts(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.debug_print(f"Fetching alerts from {ALERTS_ENDPOINT}")
        ret_val, response = self._make_rest_call(ALERTS_ENDPOINT, action_result, method="post", json=self._build_alerts_request_body())
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.debug_print(f"Initial API response: {response}")

        alerts = response.get("alerts", [])
        self.debug_print(f"Found {len(alerts)} alerts in initial response.")

        ref_ids = [alert["ref_id"] for alert in alerts]
        self.debug_print(f"Enriching ref_ids: {ref_ids}")

        ret_val, full_alerts = self._get_full_alert_from_ref_id(ref_ids, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, enriched_alerts = self._enrich_alert_indicators(full_alerts, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        for alert in enriched_alerts:
            action_result.add_data(alert)
        action_result.update_summary({"alerts_enriched": len(enriched_alerts)})
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_update_alert_status(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        alert_ref_ids = [x.strip() for x in param["Alert_Ref_IDs"].split(",")]

        status = param["Status"]
        if status not in [member.value for member in Status]:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid status value: {status}")

        closure_reason = param.get("Closure_Reason")
        if closure_reason and closure_reason not in [member.value for member in ClosureReason]:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid closure_reason value: {closure_reason}")

        body = {
            "alert_ref_ids": alert_ref_ids,
            "data": {
                "status": status,
                "closure_reason": closure_reason,
                "closure_reason_description": param.get("Reason_Description"),
            },
        }
        ret_val, response = self._make_rest_call(ALERTS_STATUS_ENDPOINT, action_result, method="put", json=body)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_submit_takedown(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        reason = param["Reason"]
        if reason not in [member.value for member in TakedownReason]:
            return action_result.set_status(phantom.APP_ERROR, f"Invalid takedown reason value: {reason}")

        takedown = {
            "customer": param["Customer_ID"],
            "reason": reason,
            "url": param["URL"],
            "brand": param["Brand"],
            "original_url": param.get("Original_URL"),
            "alert_id": param.get("Alert_ID"),
            "note": param.get("Note"),
        }
        ret_val, response = self._make_rest_call(TAKEDOWN_SUBMIT_ENDPOINT, action_result, method="post", json=takedown)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_retrieve_takedowns(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        customer_id = param.get("Customer_ID")
        if not customer_id:
            return action_result.set_status(phantom.APP_ERROR, "Customer_ID is a required parameter.")

        body = {"customer_id": customer_id, "filters": {}}
        ret_val, response = self._make_rest_call(TAKEDOWN_REQUEST_ENDPOINT, action_result, method="post", json=body)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        for takedown in response.get("requests", []):
            action_result.add_data(takedown)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint...")
        ret_val, response = self._make_rest_call(ALERTS_ENDPOINT, action_result, method="post", json=self._build_alerts_request_body())
        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()
        self.save_progress("Test Connectivity Passed.")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ingest_alerts(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Starting alert ingestion...")

        self.debug_print("Fetching raw alerts...")
        ret_val, response = self._make_rest_call(ALERTS_ENDPOINT, action_result, method="post", json=self._build_alerts_request_body())
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        alerts = response.get("alerts", [])
        self.save_progress(f"Found {len(alerts)} alerts to process.")
        if not alerts:
            return action_result.set_status(phantom.APP_SUCCESS, "No new alerts found.")

        ref_ids = [alert["ref_id"] for alert in alerts]
        self.debug_print(f"Enriching {len(ref_ids)} alerts: {ref_ids}")

        ret_val, enriched_alerts = self._get_full_alert_from_ref_id(ref_ids, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ret_val, enriched_alerts = self._enrich_alert_indicators(enriched_alerts, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        self.save_progress("Enrichment complete. Saving to Splunk SOAR...")
        for alert in enriched_alerts:
            self.save_progress(f"Full Alert Object: {json.dumps(alert, indent=2)}")
            self.save_progress(f"Processing alert {alert.get('ref_id')}")

            # 1. Direct Mapping for Key Fields
            container = {
                "name": alert.get("title", "Cyberint Alert"),
                "description": alert.get("description", ""),
                "source_data_identifier": alert.get("ref_id"),
                "severity": map_severity(alert.get("severity")),
                "tags": alert.get("tags", []),
            }
            status, message, container_id = self.save_container(container)
            if phantom.is_fail(status):
                self.debug_print(f"Failed to save container for alert {alert.get('ref_id')}: {message}")
                continue

            self.debug_print(f"Successfully created container {container_id} for alert {alert.get('ref_id')}")

            # 2. "Catch-All" Artifact for remaining details
            alert_details = alert.copy()
            alert_details.pop("title", None)
            alert_details.pop("description", None)
            alert_details.pop("severity", None)
            alert_details.pop("tags", None)
            alert_details.pop("ref_id", None)
            alert_details.pop("indicators", None)  # We handle these separately below

            details_artifact = {
                "name": "Alert Details",
                "container_id": container_id,
                "source_data_identifier": f"{alert.get('ref_id')}",
                "cef": alert_details,
            }
            self.save_artifact(details_artifact)

            # 3. Process and save indicators
            for indicator in alert.get("indicators", []):
                self.save_progress(f"Full Indicator Object: {json.dumps(indicator, indent=2)}")
                self.debug_print(f"Adding indicator {indicator.get('value')} to container {container_id}")
                artifact = {
                    "name": indicator.get("value"),
                    "cef": {
                        "type": indicator.get("type"),
                        "value": indicator.get("value"),
                        "confidence": indicator.get("confidence"),
                        "source_category": indicator.get("source_category"),
                    },
                    "container_id": container_id,
                    "source_data_identifier": indicator.get("id"),
                }
                self.save_artifact(artifact)

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_file_reputation(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        sha256 = param["SHA256"]
        ret_val, response = self._make_rest_call(IOC_FILE_SHA256_ENDPOINT, action_result, params={"value": sha256})
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response.get("data", {}))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_domain_reputation(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        domain = param["Domain"]
        ret_val, response = self._make_rest_call(IOC_DOMAIN_ENDPOINT, action_result, params={"value": domain})
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response.get("data", {}))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_ip_reputation(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        ip = param["IP"]
        ret_val, response = self._make_rest_call(IOC_IPV4_ENDPOINT, action_result, params={"value": ip})
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response.get("data", {}))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_url_reputation(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        url = param["URL"]
        ret_val, response = self._make_rest_call(IOC_URL_ENDPOINT, action_result, params={"value": url})
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response.get("data", {}))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_get_cve_intelligence(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        cve_id = param["CVE_ID"]
        endpoint = CVE_GET_BY_ID_ENDPOINT.format(cve_id=cve_id)
        ret_val, response = self._make_rest_call(endpoint, action_result)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response.get("data", {}))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_credentials_by_domain(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        domain = param["Domain"]
        body = {"domain": domain}
        ret_val, response = self._make_rest_call(CREDENTIALS_BY_DOMAIN_ENDPOINT, action_result, method="post", json=body)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response.get("data", {}))
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_lookup_credentials_by_email(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        emails = [e.strip() for e in param["Email"].split(",") if e.strip()]
        mask_password = param.get("Mask_Password", True)
        body = {"email": emails, "mask_password": mask_password}
        ret_val, response = self._make_rest_call(CREDENTIALS_BY_EMAIL_ENDPOINT, action_result, method="post", json=body)
        if phantom.is_fail(ret_val):
            return action_result.get_status()
        action_result.add_data(response.get("data", {}))
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        if hasattr(self, "_get_requests_session"):
            self._requests_session = self._get_requests_session()
        ret_val = phantom.APP_SUCCESS
        action_id = self.get_action_identifier()
        self.debug_print("action_id", action_id)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)
        elif action_id == "get_enriched_alerts":
            ret_val = self._handle_get_enriched_alerts(param)
        elif action_id == "update_alert_status":
            ret_val = self._handle_update_alert_status(param)
        elif action_id == "submit_takedown":
            ret_val = self._handle_submit_takedown(param)
        elif action_id == "retrieve_takedowns":
            ret_val = self._handle_retrieve_takedowns(param)
        elif action_id == "on_poll":
            ret_val = self._handle_ingest_alerts(param)
        elif action_id == "get_file_reputation":
            ret_val = self._handle_get_file_reputation(param)
        elif action_id == "get_domain_reputation":
            ret_val = self._handle_get_domain_reputation(param)
        elif action_id == "get_ip_reputation":
            ret_val = self._handle_get_ip_reputation(param)
        elif action_id == "get_url_reputation":
            ret_val = self._handle_get_url_reputation(param)
        elif action_id == "get_cve_intelligence":
            ret_val = self._handle_get_cve_intelligence(param)
        elif action_id == "lookup_credentials_by_domain":
            ret_val = self._handle_lookup_credentials_by_domain(param)
        elif action_id == "lookup_credentials_by_email":
            ret_val = self._handle_lookup_credentials_by_email(param)

        return ret_val

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("input_test_json", help="Input Test JSON file")
    args = parser.parse_args()

    with open(args.input_test_json) as f:
        in_json = json.load(f)

    connector = CyberintAlertsConnector()
    connector.print_progress_message = True

    # Mock the config for local testing
    connector._base_url = in_json["config"].get("base_url")
    connector._access_token = in_json["config"].get("access_token")
    connector._customer_id = in_json["config"].get("customer_id")

    # Mock get_action_identifier
    connector._action_identifier = in_json.get("action")

    ret_val = connector.handle_action(in_json.get("parameters", [{}])[0])
    print(ret_val)

    sys.exit(0)
