# File: cyberintpremiumioc_connector.py
#
# Copyright (c) 2025-2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

import json
from datetime import datetime, timedelta, timezone

import phantom.app as phantom
import requests
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

from cyberintpremiumioc_consts import (
    DEFAULT_SEVERITY,
    FEED_ARTIFACT_LABEL,
    FEED_CONTAINER_SDI_PREFIX,
    FEED_FIRST_FETCH_DAYS,
    FEED_STATE_CURSOR_KEY,
    FEED_STATE_OFFSET_KEY,
    IOC_CEF_MAPPING,
    IOC_ENRICHMENT_ENDPOINT,
    IOC_FEED_JSONL_ENDPOINT,
    IOC_FEED_PAGE_SIZE,
    IOC_SEVERITY_MAP,
    IOC_TYPE_DOMAIN,
    IOC_TYPE_IPV4,
    IOC_TYPE_SHA256,
    IOC_TYPE_URL,
    POLL_NOW_ARTIFACT_LIMIT,
    POLL_NOW_LOOKBACK_DAYS,
)


class CyberintpremiumiocConnector(BaseConnector):
    """
    Check Point EM ThreatCloud Intelligence connector.
    """

    def __init__(self):
        super().__init__()
        self._state = None
        self._base_url = None
        self._access_token = None
        self._customer_name = None
        self._verify = True

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

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, json=None, method="get"):
        """
        Helper function to make REST calls for the connector. Authenticates via the
        `access_token` cookie as required by the Check Point EM ThreatCloud APIs.
        """
        try:
            url = f"{self._base_url}{endpoint}"
            self.debug_print(f"Making REST call to: {url}")

            try:
                request_func = getattr(requests, method.lower())
            except AttributeError:
                return action_result.set_status(phantom.APP_ERROR, f"Invalid method: {method}"), None

            all_headers = self._get_custom_headers()
            if headers:
                all_headers.update(headers)

            cookies = {"access_token": self._access_token}

            response = request_func(
                url,
                json=json,
                data=data,
                headers=all_headers,
                params=params,
                cookies=cookies,
                verify=self._verify,
            )

            if hasattr(action_result, "add_debug_data"):
                action_result.add_debug_data({"r_status_code": response.status_code})

            if 200 <= response.status_code < 300:
                content_type = response.headers.get("Content-Type", "")
                if "jsonl" in content_type or endpoint.endswith("/jsonl"):
                    return phantom.APP_SUCCESS, self._parse_jsonl(response.text)
                if not response.text:
                    return phantom.APP_SUCCESS, {}
                try:
                    return phantom.APP_SUCCESS, response.json()
                except ValueError:
                    return phantom.APP_SUCCESS, response.text

            error_message = f"Error from server. Status Code: {response.status_code}"
            if response.text:
                try:
                    resp_json = response.json()
                    detail = resp_json.get("detail") or resp_json.get("error") or resp_json
                    error_message = f"Error from server. Status Code: {response.status_code}. Error: {detail}"
                except ValueError:
                    error_message = f"Error from server. Status Code: {response.status_code}. Error: {response.text}"

            return action_result.set_status(phantom.APP_ERROR, error_message), None

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, f"Error making REST call: {e!s}"), None

    @staticmethod
    def _parse_jsonl(text):
        """Parse a JSON Lines payload into a list of dicts. Skips blank lines."""
        items = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except ValueError:
                continue
        return items

    def _enrich_indicator(self, action_result, indicator_type, indicator_value):
        """Call the premium enrichment endpoint for a single IOC."""
        body = {"type": indicator_type, "value": indicator_value}
        return self._make_rest_call(IOC_ENRICHMENT_ENDPOINT, action_result, json=body, method="post")

    def _handle_test_connectivity(self, param):
        """
        Validate the asset configuration for connectivity using supplied credentials.
        """
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to instance...")

        ret_val, _ = self._enrich_indicator(action_result, IOC_TYPE_DOMAIN, "cyberint.com")
        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        self.save_progress("Test Connectivity Passed.")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_enrichment(self, param, indicator_type, param_key):
        """Run one enrichment action and attach the enriched indicator as data."""
        action_result = self.add_action_result(ActionResult(dict(param)))

        indicator_value = (param.get(param_key) or "").strip()
        if not indicator_value:
            return action_result.set_status(phantom.APP_ERROR, f"Parameter '{param_key}' is required")

        ret_val, response = self._enrich_indicator(action_result, indicator_type, indicator_value)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # The endpoint returns a single EnrichedIOC object; anything else is
        # wrapped so playbooks always see a dict at action_result.data.0.
        action_result.add_data(response if isinstance(response, dict) else {"response": response})
        action_result.update_summary({"total_objects": 1, "total_objects_successful": 1})
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_enrich_sha256(self, param):
        return self._handle_enrichment(param, IOC_TYPE_SHA256, "Hash")

    def _handle_enrich_ipv4(self, param):
        return self._handle_enrichment(param, IOC_TYPE_IPV4, "IP")

    def _handle_enrich_url(self, param):
        return self._handle_enrichment(param, IOC_TYPE_URL, "URL")

    def _handle_enrich_domain(self, param):
        return self._handle_enrichment(param, IOC_TYPE_DOMAIN, "Domain")

    def _find_container_id(self, sdi):
        """Look up an existing container id by its source_data_identifier."""
        url = f"{self.get_phantom_base_url()}/rest/container?_filter_source_data_identifier='{sdi}'"
        try:
            r = self._get_requests_session().get(url, verify=False)
            r.raise_for_status()
            data = r.json()
            if data.get("count", 0) > 0:
                return data["data"][0]["id"]
        except Exception as e:
            self.debug_print(f"Failed to look up container for '{sdi}': {e}")
        return None

    def _get_daily_container(self, date_str, cache):
        """
        Return the container id for a given UTC day, creating it if needed.
        Container ids are cached per-run so IOCs spanning multiple days each land
        in the correct daily container without redundant lookups.
        """
        if date_str in cache:
            return cache[date_str]

        sdi = f"{FEED_CONTAINER_SDI_PREFIX}{date_str}"
        container = {
            "name": f"Check Point EM ThreatCloud Daily IOC Feed - {date_str}",
            "source_data_identifier": sdi,
            "description": f"Indicators added to the Check Point EM ThreatCloud intelligence feed on {date_str} (UTC).",
            "label": self.get_config().get("ingest", {}).get("container_label"),
            "severity": DEFAULT_SEVERITY,
            "tags": ["cyberint", "threatcloud", "ioc_feed"],
        }
        status, message, container_id = self.save_container(container)
        if phantom.is_fail(status):
            self.debug_print(f"Could not create container (likely already exists): {message}")
        if not container_id:
            container_id = self._find_container_id(sdi)

        cache[date_str] = container_id
        return container_id

    @staticmethod
    def _ioc_feed_date(ioc, default_date_str):
        """Return the UTC date (yyyy-MM-dd) an IOC was added to the feed."""
        ts = ioc.get("added_to_feed")
        if not ts:
            return default_date_str
        try:
            parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            return default_date_str

    @staticmethod
    def _build_artifact(ioc, container_id):
        """
        Map a feed indicator onto a SOAR artifact.

        The indicator lands in the standard CEF field for its type (with the
        matching ``cef_types`` contains, so SOAR can recommend actions on it) and
        the remaining feed attributes are surfaced alongside it for triage and
        playbook filtering. Returns ``None`` for indicators that are missing a
        value or carry an IOC type this app does not know how to map.
        """
        indicator_type = str(ioc.get("indicator_type") or "").strip().lower()
        indicator_value = ioc.get("indicator_value")
        mapping = IOC_CEF_MAPPING.get(indicator_type)
        if not indicator_value or not mapping:
            return None

        cef_field, contains, artifact_type = mapping
        activity = ioc.get("activity", "")

        cef = {
            cef_field: indicator_value,
            "indicatorType": indicator_type,
            "indicatorValue": indicator_value,
        }
        # Only carry through the attributes the feed actually populated, so
        # artifacts stay free of empty CEF keys.
        optional_fields = {
            "activity": activity,
            "malicious": ioc.get("malicious"),
            "confidence": ioc.get("confidence"),
            "severity": ioc.get("severity"),
            "killChainStage": ioc.get("kill_chain_stage"),
            "firstSeen": ioc.get("first_seen"),
            "lastSeen": ioc.get("last_seen"),
            "addedToFeed": ioc.get("added_to_feed"),
            "validUntil": ioc.get("valid_until"),
            "isBlocking": ioc.get("is_blocking"),
            "isUnique": ioc.get("is_unique"),
            "malwareTypes": ioc.get("malware_types"),
            "hasCve": ioc.get("has_cve"),
            "hasCampaign": ioc.get("has_campaign"),
        }
        cef.update({key: value for key, value in optional_fields.items() if value not in (None, "", [])})

        return {
            "name": f"{indicator_type} - {indicator_value}",
            "label": FEED_ARTIFACT_LABEL,
            "type": artifact_type,
            "severity": IOC_SEVERITY_MAP.get(ioc.get("severity"), DEFAULT_SEVERITY),
            "cef": cef,
            "cef_types": {cef_field: contains},
            "container_id": container_id,
            "source_data_identifier": f"{indicator_value}|{activity}",
            "data": ioc,
        }

    def _handle_on_poll(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        now = datetime.now(timezone.utc)
        added_before = now.isoformat()

        # Determine the ingestion window start. Scheduled polls resume from the
        # checkpoint saved in the state file; a manual "poll now" uses a fixed
        # lookback and never advances the checkpoint.
        poll_now = self.is_poll_now()
        resume_offset = 0
        if poll_now:
            added_after = (now - timedelta(days=POLL_NOW_LOOKBACK_DAYS)).isoformat()
            self.save_progress(f"POLL NOW: ingesting the last {POLL_NOW_LOOKBACK_DAYS} day(s); checkpoint will not advance")
        elif self._state.get(FEED_STATE_CURSOR_KEY):
            added_after = self._state[FEED_STATE_CURSOR_KEY]
            resume_offset = self._as_positive_int(self._state.get(FEED_STATE_OFFSET_KEY)) or 0
            self.save_progress(f"Resuming ingestion from checkpoint: {added_after} (offset {resume_offset})")
        else:
            added_after = (now - timedelta(days=FEED_FIRST_FETCH_DAYS)).isoformat()
            self.save_progress(f"First run: ingesting the last {FEED_FIRST_FETCH_DAYS} days")

        # Ingestion ceilings. SOAR supplies these for "poll now"; a scheduled poll
        # only receives them when the asset defines them. max_containers bounds the
        # number of daily buckets a single run may open.
        max_artifacts = self._as_positive_int(param.get("artifact_count"))
        if max_artifacts is None and poll_now:
            max_artifacts = POLL_NOW_ARTIFACT_LIMIT
        max_containers = self._as_positive_int(param.get("container_count"))
        if max_artifacts:
            self.save_progress(f"Ingestion capped at {max_artifacts} IOC artifact(s)")
        if max_containers:
            self.save_progress(f"Ingestion capped at {max_containers} daily container(s)")

        container_cache = {}
        default_date_str = now.strftime("%Y-%m-%d")

        offset = resume_offset
        total_iocs = 0
        skipped_iocs = 0
        truncated = False
        # Offset of the first record this run did not handle. Results are sorted
        # ascending and `added_before` only ever grows, so an offset stays stable
        # across runs and a truncated pass can resume exactly where it stopped.
        next_offset = offset

        while not truncated:
            limit = IOC_FEED_PAGE_SIZE
            if max_artifacts:
                limit = min(limit, max_artifacts - total_iocs)
                if limit <= 0:
                    truncated = True
                    break

            self.save_progress(f"Fetching IOCs, offset: {offset}")
            body = {
                "filters": {
                    "added_to_feed_after": added_after,
                    "added_to_feed_before": added_before,
                },
                "pagination": {"limit": limit, "offset": offset},
                "sort": {"field": "added_to_feed", "direction": "asc"},
            }
            ret_val, iocs = self._make_rest_call(IOC_FEED_JSONL_ENDPOINT, action_result, json=body, method="post")
            if phantom.is_fail(ret_val):
                return action_result.get_status()

            if not iocs:
                break

            page_start = offset
            for index, ioc in enumerate(iocs):
                date_str = self._ioc_feed_date(ioc, default_date_str)
                if max_containers and date_str not in container_cache and len(container_cache) >= max_containers:
                    # This record was not handled; resume from it next time.
                    next_offset = page_start + index
                    truncated = True
                    break

                container_id = self._get_daily_container(date_str, container_cache)
                if not container_id:
                    return action_result.set_status(phantom.APP_ERROR, "Failed to create or find container for IOC feed")

                artifact = self._build_artifact(ioc, container_id)
                if artifact:
                    self.save_artifact(artifact)
                    total_iocs += 1
                else:
                    skipped_iocs += 1
                    self.debug_print(f"Skipping unsupported or incomplete IOC: {ioc.get('indicator_type')}")

                next_offset = page_start + index + 1

                if max_artifacts and total_iocs >= max_artifacts:
                    truncated = True
                    break

            if len(iocs) < limit:
                break
            offset += limit

        if truncated:
            self.save_progress("Ingestion limit reached; remaining IOCs will be picked up by the next poll")

        # Advance the checkpoint only after a full successful scheduled pass. A run
        # cut short by a limit keeps the same window start and records how far into
        # it it got, so the next poll resumes there without re-reading or skipping.
        if not poll_now:
            if truncated:
                self._state[FEED_STATE_CURSOR_KEY] = added_after
                self._state[FEED_STATE_OFFSET_KEY] = next_offset
            else:
                self._state[FEED_STATE_CURSOR_KEY] = added_before
                self._state.pop(FEED_STATE_OFFSET_KEY, None)

        action_result.update_summary(
            {
                "iocs_ingested": total_iocs,
                "iocs_skipped": skipped_iocs,
                "containers_created": len(container_cache),
                "limit_reached": truncated,
            }
        )
        return action_result.set_status(phantom.APP_SUCCESS)

    @staticmethod
    def _as_positive_int(value):
        """Coerce a SOAR poll parameter to a positive int, or None if unusable."""
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def initialize(self):
        """
        Initialize the connector.
        """
        self.debug_print("Initializing connector")
        self._state = self.load_state()
        config = self.get_config()

        self._base_url = config.get("base_url")
        self._access_token = config.get("access_token")
        self._customer_name = config.get("customer_name")
        self._verify = config.get("verify_server_cert", True)

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """
        Dispatcher for actions.
        """
        if hasattr(self, "_get_requests_session"):
            self._requests_session = self._get_requests_session()

        action_id = self.get_action_identifier()
        self.debug_print("action_id", action_id)

        action_mapping = {
            "test_connectivity": self._handle_test_connectivity,
            "enrich_sha256": self._handle_enrich_sha256,
            "enrich_ipv4": self._handle_enrich_ipv4,
            "enrich_url": self._handle_enrich_url,
            "enrich_domain": self._handle_enrich_domain,
            "on_poll": self._handle_on_poll,
        }

        ret_val = phantom.APP_SUCCESS
        if action_id in action_mapping:
            ret_val = action_mapping[action_id](param)
        return ret_val


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("input_test_json", help="Input Test JSON file")
    args = parser.parse_args()

    with open(args.input_test_json) as f:
        in_json = json.load(f)

    connector = CyberintpremiumiocConnector()
    connector.print_progress_message = True

    connector._base_url = in_json["config"].get("base_url")
    connector._access_token = in_json["config"].get("access_token")
    connector._customer_name = in_json["config"].get("customer_name")

    connector._action_identifier = in_json.get("action")

    ret_val = connector.handle_action(in_json.get("parameters", [{}])[0])
    print(ret_val)

    sys.exit(0)
