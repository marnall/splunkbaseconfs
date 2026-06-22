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


@Configuration()
class ThreatmonSetStatusCommand(GeneratingCommand):
    alarm_id = Option(require=True)
    status = Option(require=True)
    api_url = Option(require=False, default=None)
    api_key = Option(require=False, default=None)

    def _get_api_config(self):
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

    def _http_request(self, method, url, headers, body=None, timeout=30):
        if _HAS_URLLIB3:
            http = urllib3.PoolManager()
            resp = http.request(method, url, body=body, headers=headers, timeout=timeout)
            return resp.status, resp.data.decode("utf-8", "ignore")
        else:
            import urllib.request
            req = urllib.request.Request(url, data=body.encode() if body else None, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "ignore")

    def _update_kv_store(self, alarm_id, status):
        """Upsert alarmCode→status into the status_overrides KV store."""
        try:
            collection = self.service.kvstore["status_overrides"]
            existing = collection.data.query(query=json.dumps({"alarmCode": str(alarm_id)}))
            record = {"alarmCode": str(alarm_id), "status": status}
            if existing:
                collection.data.update(existing[0]["_key"], json.dumps(record))
            else:
                collection.data.insert(json.dumps(record))
            return None  # success
        except Exception as e:
            return str(e)

    def generate(self):
        allowed_statuses = ["Open", "In Progress", "False Positive", "Ignore", "Resolved"]
        if self.status not in allowed_statuses:
            yield {
                "alarmId": self.alarm_id,
                "status": self.status,
                "result": f"Invalid status. Allowed: {', '.join(allowed_statuses)}",
            }
            return

        api_url, api_key = self._get_api_config()

        if not api_url or not api_key:
            yield {
                "alarmId": self.alarm_id,
                "status": self.status,
                "result": "API URL or API Key not configured. Please run the Setup page first.",
            }
            return

        # --- Step 1: Update status via API ---
        url = f"{api_url}/incident/status"
        headers = {
            "X-COMPANY-API-KEY": api_key,
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        body = json.dumps({"status": self.status, "alarmIds": [self.alarm_id]})

        try:
            status_code, resp_text = self._http_request("PATCH", url, headers, body)

            if status_code != 200:
                yield {"alarmId": self.alarm_id, "status": self.status, "result": f"error {status_code}: {resp_text}"}
                return

            # --- Step 2: Write status override to KV Store ---
            kv_err = self._update_kv_store(self.alarm_id, self.status)

            if kv_err:
                yield {"alarmId": self.alarm_id, "status": self.status, "result": f"status updated successfully (kv sync failed: {kv_err})"}
            else:
                yield {"alarmId": self.alarm_id, "status": self.status, "result": "status updated successfully"}

        except Exception as e:
            yield {"alarmId": self.alarm_id, "status": self.status, "result": f"exception: {e}"}


if __name__ == "__main__":
    dispatch(ThreatmonSetStatusCommand, sys.argv, sys.stdin, sys.stdout, __name__)
