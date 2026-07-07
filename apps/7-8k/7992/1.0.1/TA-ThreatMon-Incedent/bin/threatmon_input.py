#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import time
import traceback
from typing import Optional
from datetime import datetime

import urllib3
from splunklib.modularinput import Script, Scheme, Argument, Event, EventWriter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

THREATMON_PAGE_SIZE = 10

class ThreatmonInput(Script):
    def get_scheme(self):
        scheme = Scheme("threatmon_incidents")
        scheme.description = "Pull Threatmon incidents into Splunk"
        scheme.use_external_validation = True
        scheme.use_single_instance = True  # Aynı anda birden fazla çekme işlemini engeller

        scheme.add_argument(Argument("api_url", title="API Base URL", required_on_create=True))
        scheme.add_argument(Argument("api_key", title="API Key", required_on_create=True, data_type=Argument.data_type_password))
        scheme.add_argument(Argument("index", title="Index", required_on_create=True))
        scheme.add_argument(Argument("interval", title="Interval (sec)", required_on_create=True))
        scheme.add_argument(Argument("sourcetype", title="Sourcetype", required_on_create=False, default_value="threatmon:incident"))
        return scheme

    def validate_input(self, definition):
        api_url = definition.parameters.get("api_url")
        api_key = definition.parameters.get("api_key")
        if not api_url.startswith("http"):
            raise ValueError("api_url must start with http/https")
        if not api_key:
            raise ValueError("api_key is required")

    def stream_events(self, inputs, ew: EventWriter):
        for input_name, input_item in inputs.inputs.items():
            params = input_item
            api_url = params.get("api_url")
            api_key = params.get("api_key")
            index = params.get("index")
            sourcetype = params.get("sourcetype", "threatmon:incident")

            checkpoint_key = f"{input_name}::last_incident_id"
            last_incident_id = self._get_checkpoint(checkpoint_key)
            last_incident_id_int: Optional[int] = int(last_incident_id) if last_incident_id else None

            http = urllib3.PoolManager()
            headers = {"X-COMPANY-API-KEY": api_key, "accept": "application/json"}

            page = 0
            total_events = 0

            try:
                while True:
                    url = f"{api_url}/vulnerabilities/{page}"
                    if last_incident_id_int:
                        url += f"?afterAlarmCode={last_incident_id_int}"

                    resp = http.request("GET", url, headers=headers)
                    if resp.status != 200:
                        raise RuntimeError(f"API Error {resp.status}: {resp.data.decode('utf-8', 'ignore')}")

                    data = json.loads(resp.data.decode("utf-8"))
                    alerts = data.get("data", [])
                    total_records = data.get("totalRecords", 0)
                    if not alerts:
                        break

                    for alert in alerts:
                        incident_id = alert.get("alarmCode")
                        title = alert.get("title", "Unknown Threat")
                        description = alert.get("description", "No description available")
                        severity = alert.get("severity", "Low")
                        status = alert.get("status", "New")
                        alarm_date = alert.get("alarmDate") or datetime.utcnow().isoformat()

                        event = Event(
                            data=json.dumps(alert),
                            time=self._to_epoch(alarm_date),
                            index=index,
                            sourcetype=sourcetype,
                            source="threatmon_api"
                        )
                        ew.write_event(event)
                        total_events += 1

                        if isinstance(incident_id, int):
                            if (last_incident_id_int is None) or (incident_id > last_incident_id_int):
                                last_incident_id_int = incident_id

                    if len(alerts) < THREATMON_PAGE_SIZE or (total_records and total_events >= total_records):
                        break

                    page += 1
                    time.sleep(1)

            except Exception as e:
                ew.log(EventWriter.ERROR, f"Threatmon input failure: {e}\n{traceback.format_exc()}")
            finally:
                if last_incident_id_int is not None:
                    self._save_checkpoint(checkpoint_key, str(last_incident_id_int))
                ew.log(EventWriter.INFO, f"Threatmon input: indexed={total_events} last_incident_id={last_incident_id_int}")

    # --- helpers ---
    def _get_checkpoint(self, key: str) -> Optional[str]:
        try:
            return self.service.storage_passwords.get(key).clear_password
        except Exception:
            return self._read_ckpt_file(key)

    def _save_checkpoint(self, key: str, value: str) -> None:
        try:
            import os
            from pathlib import Path
            ckptdir = Path(self._input_definition.metadata.get("checkpoint_dir", self._input_definition.metadata.get("checkpoint_dir" , "")))
            if not ckptdir:
                ckptdir = Path(self._input_definition.metadata["checkpoint_dir"])
            ckptdir.mkdir(parents=True, exist_ok=True)
            with open(ckptdir / (key.replace("::", "_") + ".ckpt"), "w", encoding="utf-8") as f:
                f.write(value)
        except Exception:
            pass

    def _read_ckpt_file(self, key: str) -> Optional[str]:
        try:
            import os
            from pathlib import Path
            ckptdir = Path(self._input_definition.metadata.get("checkpoint_dir", ""))
            path = ckptdir / (key.replace("::", "_") + ".ckpt")
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            return None
        return None

    @staticmethod
    def _to_epoch(iso_dt: str) -> float:
        try:
            dt = datetime.fromisoformat(iso_dt.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return time.time()

if __name__ == "__main__":
    ThreatmonInput().run(sys.argv)

    def stream_events(self, inputs, ew: EventWriter):
        for input_name, input_item in inputs.inputs.items():
            params = input_item
            api_url = params.get("api_url")
            api_key = params.get("api_key")
            index = params.get("index")
            sourcetype = params.get("sourcetype", "threatmon:incident")

            checkpoint_key = f"{input_name}::last_incident_id"
            last_incident_id = self._get_checkpoint(checkpoint_key)  # returns None or int-as-str
            last_incident_id_int: Optional[int] = int(last_incident_id) if last_incident_id else None

            http = urllib3.PoolManager()
            headers = {"X-COMPANY-API-KEY": api_key, "accept": "application/json"}

            page = 0
            total_events = 0

            try:
                while True:
                    url = f"{api_url}/vulnerabilities/{page}"
                    if last_incident_id_int:
                        q = urlencode({"afterAlarmCode": last_incident_id_int})
                        url = f"{url}?{q}"

                    resp = http.request("GET", url, headers=headers)
                    if resp.status != 200:
                        raise RuntimeError(f"API Error {resp.status}: {resp.data.decode('utf-8', 'ignore')}")

                    data = json.loads(resp.data.decode("utf-8"))
                    alerts = data.get("data", [])
                    if not alerts:
                        break

                    for alert in alerts:
                        incident_id = alert.get("alarmCode")
                        alarm_date = alert.get("alarmDate") or datetime.utcnow().isoformat()
                        event = Event(
                            data=json.dumps(alert),
                            time=self._to_epoch(alarm_date),
                            index=index,
                            sourcetype=sourcetype,
                            source="threatmon_api"
                        )
                        ew.write_event(event)
                        total_events += 1

                        # advance checkpoint conservatively to the max seen
                        if isinstance(incident_id, int):
                            if (last_incident_id_int is None) or (incident_id > last_incident_id_int):
                                last_incident_id_int = incident_id

                    # pagination break condition
                    if len(alerts) < THREATMON_PAGE_SIZE:
                        break

                    page += 1
                    time.sleep(0.5)

            except Exception as e:
                ew.log(EventWriter.ERROR, f"Threatmon input failure: {e}\n{traceback.format_exc()}")
            finally:
                if last_incident_id_int is not None:
                    self._save_checkpoint(checkpoint_key, str(last_incident_id_int))
                ew.log(EventWriter.INFO, f"Threatmon input: indexed={total_events} last_incident_id={last_incident_id_int}")

    # --- helpers ---
    def _get_checkpoint(self, key: str) -> Optional[str]:
        try:
            return self.service.storage_passwords.get(key).clear_password  # not ideal for FIPS/Cloud; fallback below
        except Exception:
            # use file-based checkpoint in $SPLUNK_DB/modinputs/
            return self._read_ckpt_file(key)

    def _save_checkpoint(self, key: str, value: str) -> None:
        try:
            # best-effort: write to file in var/lib/splunk/modinputs
            import os
            from pathlib import Path
            ckptdir = Path(self._input_definition.metadata.get("checkpoint_dir", self._input_definition.metadata.get("checkpoint_dir" , "")))
            if not ckptdir:
                ckptdir = Path(self._input_definition.metadata["checkpoint_dir"])  # may exist depending on Splunk version
            ckptdir.mkdir(parents=True, exist_ok=True)
            with open(ckptdir / (key.replace("::", "_") + ".ckpt"), "w", encoding="utf-8") as f:
                f.write(value)
        except Exception:
            pass

    def _read_ckpt_file(self, key: str) -> Optional[str]:
        try:
            import os
            from pathlib import Path
            ckptdir = Path(self._input_definition.metadata.get("checkpoint_dir", ""))
            path = ckptdir / (key.replace("::", "_") + ".ckpt")
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except Exception:
            return None
        return None

    @staticmethod
    def _to_epoch(iso_dt: str) -> float:
        try:
            dt = datetime.fromisoformat(iso_dt.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return time.time()

if __name__ == "__main__":
    ThreatmonInput().run(sys.argv)