#!/usr/bin/env python3
"""
Custom search command to update Cyberint Argos alert status.

Usage in SPL:
    | cyberintupdatestatus account="..." instance_domain="..." client_name="..."
      ref_id="ARG-123" status="acknowledged"
"""
import datetime
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import import_declare_test  # noqa: E402, F401
import utils  # noqa: E402
from argos_client import CyberintClient  # noqa: E402

import requests as http_requests  # noqa: E402
import urllib3  # noqa: E402
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SPLUNKD_BASE = "https://localhost:8089"


@Configuration()
class UpdateCyberintStatusCommand(GeneratingCommand):
    account = Option(require=True)
    instance_domain = Option(require=True)
    client_name = Option(require=True)
    ref_id = Option(require=True)
    status = Option(require=True)
    closure_reason = Option(require=False, default="-")
    closure_reason_description = Option(require=False, default="-")

    def generate(self):
        session_key = self._metadata.searchinfo.session_key

        # Enforce field requirements based on status:
        # - only "closed" requires closure_reason
        # - only closure_reason="other" requires closure_reason_description
        if self.status == "closed":
            closure_reason = self.closure_reason if self.closure_reason not in ("-", "", None) else None
            if closure_reason == "other":
                closure_reason_desc = self.closure_reason_description if self.closure_reason_description not in ("-", "", None) else None
            else:
                closure_reason_desc = None
        else:
            closure_reason = None
            closure_reason_desc = None

        logger = utils.logger_for_input("cyberint_update_status_command")

        try:
            api_key = utils.get_account_api_key(session_key, self.account)
            proxies = utils.get_proxy_settings(session_key)
            app_version = utils.get_version(session_key)

            client = CyberintClient(
                version=app_version,
                client_name=self.client_name,
                instance_domain=self.instance_domain,
                access_token=api_key,
                input_name="cyberint_update_status_command",
                proxies=proxies or {},
            )

            client.update_alerts_status(
                alert_ref_ids=[self.ref_id],
                status=self.status,
                closure_reason=closure_reason,
                closure_reason_description=closure_reason_desc,
            )

            logger.info("Successfully updated alert %s to status '%s'", self.ref_id, self.status)

            # Write a synthetic event to Splunk so the dashboard reflects
            # the updated status immediately (before the next scheduled sync).
            self._write_synthetic_event(session_key, logger)

            yield {"Result": f"Status update for {self.ref_id} to '{self.status}' has been submitted."}

        except Exception as e:
            logger.error("Failed to update alert %s: %s", self.ref_id, e)
            yield {"Result": f"Error updating {self.ref_id}: {self._parse_error(str(e))}"}

    @staticmethod
    def _parse_error(error_str):
        """Try to extract a human-readable message from the API error JSON."""
        try:
            # Find the JSON payload in the error string
            json_match = re.search(r'\{.*\}', error_str)
            if json_match:
                # The "message" field contains a Python-repr list; extract 'msg' from it
                error_body = json.loads(json_match.group())
                message_str = error_body.get("message", "")
                msg_match = re.search(r"'msg':\s*'([^']+)'", message_str)
                if msg_match:
                    status_code = error_body.get("status", "")
                    prefix = f"Status {status_code}: " if status_code else ""
                    return f"{prefix}{msg_match.group(1)}"
        except Exception:
            pass
        return error_str

    def _splunkd_headers(self, session_key):
        return {"Authorization": f"Splunk {session_key}"}

    def _write_synthetic_event(self, session_key, logger):
        """Query the latest Splunk event for this ref_id, update its status, and re-index it."""
        headers = self._splunkd_headers(session_key)

        # Step 1: Find the target index from the input configuration
        index_name = self._lookup_index(headers, logger)
        if not index_name:
            logger.warning("Could not determine target index; skipping synthetic event write.")
            return

        # Step 2: Query the latest event for this ref_id
        search_query = (
            f'search index=* sourcetype="{utils.ADDON_NAME}" ref_id="{self.ref_id}"'
            f" | head 1"
        )
        try:
            search_resp = http_requests.post(
                f"{SPLUNKD_BASE}/services/search/jobs/export",
                data={"search": search_query, "output_mode": "json"},
                headers=headers,
                verify=False,
            )
            search_resp.raise_for_status()
        except Exception as e:
            logger.error("Failed to query existing event for ref_id=%s: %s", self.ref_id, e)
            return

        # Parse streaming JSON (one JSON object per line)
        event_data = None
        for line in search_resp.text.strip().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                raw_json = row.get("result", {}).get("_raw")
                if raw_json:
                    event_data = json.loads(raw_json)
                    break
            except (json.JSONDecodeError, KeyError):
                continue

        if not event_data:
            logger.warning("No existing event found for ref_id=%s; skipping synthetic event.", self.ref_id)
            return

        # Step 3: Override status and update_date
        event_data["status"] = self.status
        event_data["update_date"] = datetime.datetime.utcnow().strftime(utils.ALERTS_DATE_FORMAT)

        # Step 4: Write the updated event to the index
        try:
            write_resp = http_requests.post(
                f"{SPLUNKD_BASE}/services/receivers/simple",
                params={
                    "index": index_name,
                    "sourcetype": utils.ADDON_NAME,
                    "source": "cyberint_update_status_command",
                },
                data=json.dumps(event_data, ensure_ascii=False, default=str).encode("utf-8"),
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                verify=False,
            )
            write_resp.raise_for_status()
            logger.info("Synthetic event written to index=%s for ref_id=%s", index_name, self.ref_id)
        except Exception as e:
            logger.error("Failed to write synthetic event for ref_id=%s: %s", self.ref_id, e)

    def _lookup_index(self, headers, logger):
        """Look up the Splunk index from the TA input configuration."""
        try:
            resp = http_requests.get(
                f"{SPLUNKD_BASE}/servicesNS/-/-/data/inputs/{utils.ADDON_NAME}",
                params={"output_mode": "json"},
                headers=headers,
                verify=False,
            )
            resp.raise_for_status()
            body = resp.json()
            for entry in body.get("entry", []):
                content = entry.get("content", {})
                if content.get("client_name") == self.client_name:
                    return content.get("index", "main")
        except Exception as e:
            logger.error("Failed to look up input configuration: %s", e)

        return None


dispatch(UpdateCyberintStatusCommand, sys.argv, sys.stdin, sys.stdout, __name__)
