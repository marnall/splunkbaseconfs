#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import json

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _HAS_URLLIB3 = True
except ImportError:
    _HAS_URLLIB3 = False
    import urllib.request

from splunklib.searchcommands import GeneratingCommand, Option, Configuration, dispatch


TAKEDOWN_ELIGIBLE_TITLES = {
    "Phishing Domain Detected",
    "Rogue Mobile App Detected",
    "Company Data Disclosure Detected",
}


@Configuration()
class ThreatmonTakedownCommand(GeneratingCommand):
    finding_id = Option(require=True)
    finding = Option(require=True)
    title = Option(require=False, default=None)
    # api_url and api_key are optional — read from inputs.conf if omitted
    api_url = Option(require=False, default=None)
    api_key = Option(require=False, default=None)

    def _get_api_config(self):
        """Return (api_url, api_key) from options or stored app configuration."""
        api_url = self.api_url
        api_key = self.api_key

        if not api_url or not api_key:
            try:
                stanza = self.service.confs["inputs"]["threatmon_incidents://default"]
                content = stanza.content
                if not api_url:
                    api_url = content.get("api_url", "")
                if not api_key:
                    api_key = content.get("api_key", "")
            except Exception:
                pass

        return api_url, api_key

    def generate(self):
        if self.title and self.title.strip() not in TAKEDOWN_ELIGIBLE_TITLES:
            yield {
                "findingId": self.finding_id,
                "finding": self.finding,
                "result": f"Not eligible for takedown. Allowed incident types: {', '.join(sorted(TAKEDOWN_ELIGIBLE_TITLES))}",
            }
            return

        try:
            finding_id_int = int(self.finding_id)
        except (ValueError, TypeError):
            yield {
                "findingId": self.finding_id,
                "finding": self.finding,
                "result": f"Invalid findingId: must be an integer, got: {self.finding_id}",
            }
            return

        if not self.finding or not self.finding.strip():
            yield {
                "findingId": self.finding_id,
                "finding": self.finding,
                "result": "finding argument is required and cannot be empty.",
            }
            return

        api_url, api_key = self._get_api_config()

        if not api_url or not api_key:
            yield {
                "findingId": self.finding_id,
                "finding": self.finding,
                "result": "API URL or API Key not configured. Please run the Setup page first.",
            }
            return

        url = f"{api_url}/takedown"
        headers = {
            "X-COMPANY-API-KEY": api_key,
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        body = json.dumps({"findingId": finding_id_int, "finding": self.finding})

        try:
            if _HAS_URLLIB3:
                http = urllib3.PoolManager()
                resp = http.request("POST", url, body=body, headers=headers, timeout=30)
                status_code = resp.status
                resp_text = resp.data.decode("utf-8", "ignore")
            else:
                req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=30) as r:
                    status_code = r.status
                    resp_text = r.read().decode("utf-8", "ignore")

            if status_code == 200:
                yield {"findingId": self.finding_id, "finding": self.finding, "result": "Takedown request submitted successfully"}
            elif status_code == 404:
                yield {"findingId": self.finding_id, "finding": self.finding, "result": f"Finding not found: findingId={self.finding_id}"}
            elif status_code == 409:
                yield {"findingId": self.finding_id, "finding": self.finding, "result": f"A takedown request already exists for findingId={self.finding_id}"}
            elif status_code == 403:
                yield {"findingId": self.finding_id, "finding": self.finding, "result": "Takedown quota exceeded. Please contact ThreatMon."}
            elif status_code == 400:
                yield {"findingId": self.finding_id, "finding": self.finding, "result": "This finding is not eligible for a takedown request."}
            else:
                yield {"findingId": self.finding_id, "finding": self.finding, "result": f"error {status_code}: {resp_text}"}
        except Exception as e:
            yield {"findingId": self.finding_id, "finding": self.finding, "result": f"exception: {e}"}


if __name__ == "__main__":
    dispatch(ThreatmonTakedownCommand, sys.argv, sys.stdin, sys.stdout, __name__)
