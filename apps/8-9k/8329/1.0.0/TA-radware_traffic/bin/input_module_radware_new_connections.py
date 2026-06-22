# encoding = utf-8

import os
import sys
import time
import datetime

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # vrm_host = definition.parameters.get('vrm_host', None)
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # lookback_minutes = definition.parameters.get('lookback_minutes', None)
    pass


def collect_events(helper, ew):
    import requests
    import time as _time
    import json
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ========= 1. Read parameters from the input =========
    primary_vrm_host = helper.get_arg("primary_vrm_host")
    username = helper.get_arg("username")
    password = helper.get_arg("password")
    lookback_minutes = int(helper.get_arg("lookback_minutes"))
    index_num = helper.get_arg("index_num")
    
    # Optional: Secondary VRM host for failover
    try:
        secondary_vrm_host = helper.get_arg("secondary_vrm_host")
        if secondary_vrm_host is None or secondary_vrm_host.strip() == "":
            secondary_vrm_host = None
    except:
        secondary_vrm_host = None

    # Let Splunk use the index configured on the input stanza
    index = index_num
    
    if secondary_vrm_host:
        helper.log_info(f"[VRM-CPS] Starting with primary: {primary_vrm_host}, secondary: {secondary_vrm_host}")
    else:
        helper.log_info(f"[VRM-CPS] Starting with primary: {primary_vrm_host} (no secondary configured)")

    # ========= 2. Define VRMClient class (CPS-per-DP logic) =========
    class VRMClient:
        def __init__(self, primary_host, secondary_host, username, password):
            self.primary_host = primary_host
            self.secondary_host = secondary_host
            self.active_host = primary_host
            self.username = username
            self.password = password
            self.session = requests.Session()
            self.logged_in = False
            self.last_login_time = 0
            self.primary_failed = False

        @property
        def base_url(self):
            return f"https://{self.active_host}".rstrip("/")

        def switch_to_secondary(self):
            """Switch to secondary VRM host if available"""
            if self.secondary_host and not self.primary_failed:
                helper.log_warning(f"[VRM-CPS] Primary VRM ({self.primary_host}) failed, switching to secondary ({self.secondary_host})")
                self.active_host = self.secondary_host
                self.primary_failed = True
                self.logged_in = False
                return True
            return False

        def login(self):
            url = f"{self.base_url}/mgmt/system/user/login"
            payload = {"username": self.username, "password": self.password}
            
            try:
                r = self.session.post(url, json=payload, verify=False, timeout=10)
                r.raise_for_status()
                self.logged_in = True
                self.last_login_time = _time.time()
                helper.log_info(f"[VRM-CPS] Login OK to {self.active_host}")
            except Exception as e:
                helper.log_error(f"[VRM-CPS] Login failed to {self.active_host}: {e}")
                # Try secondary if primary fails
                if self.switch_to_secondary():
                    url = f"{self.base_url}/mgmt/system/user/login"
                    r = self.session.post(url, json=payload, verify=False, timeout=10)
                    r.raise_for_status()
                    self.logged_in = True
                    self.last_login_time = _time.time()
                    helper.log_info(f"[VRM-CPS] Login OK to {self.active_host} (secondary)")
                else:
                    raise

        def login_if_needed(self, force=False):
            current_time = _time.time()
            time_since_login = current_time - self.last_login_time
            
            if force or not self.logged_in or time_since_login > 600:
                helper.log_info(f"[VRM-CPS] Re-authenticating to {self.active_host} (time since last login: {time_since_login:.0f}s)")
                try:
                    self.login()
                except Exception as e:
                    helper.log_error(f"[VRM-CPS] Re-authentication failed: {e}")
                    raise

        def logout(self):
            url = f"{self.base_url}/mgmt/system/user/logout"
            try:
                r = self.session.post(url, json={}, verify=False, timeout=10)
                r.raise_for_status()
                helper.log_info(f"[VRM-CPS] Logout OK from {self.active_host}")
            except Exception as e:
                helper.log_warning(f"[VRM-CPS] Logout failed from {self.active_host}: {e}")

        def get_mitigation_groups(self):
            """
            Get mitigation devices with their groups.
            Returns: list of dicts:
                {
                  "dp_name": "<device-name>",
                  "ip_address": "<ip>",
                  "mg_groups": ["group1","group2",...]
                }
            """
            self.login_if_needed()
            result = []
            try:
                url = f"{self.base_url}/mgmt/v2/device/df/restv2/configure/mitigation-devices"
                r = self.session.get(url, verify=False, timeout=10)
                
                if r.status_code == 401 or r.status_code == 403:
                    helper.log_warning("[VRM-CPS] Authentication failed, attempting re-login")
                    self.login_if_needed(force=True)
                    r = self.session.get(url, verify=False, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    for dev in data:
                        device = dev.get("name", "")
                        groups_names = dev.get("groups", [])
                        ip_address = dev.get("address", "")
                        result.append(
                            {
                                "dp_name": device,
                                "ip_address": ip_address,
                                "mg_groups": groups_names,
                            }
                        )
                    return result
                else:
                    helper.log_error(
                        f"[VRM-CPS] get_mitigation_groups: status={r.status_code}"
                    )
                    return []
            except Exception as e:
                helper.log_error(f"[VRM-CPS] Exception in get_mitigation_groups: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    return self.get_mitigation_groups()
                return []

        def get_mg_devices(self):
            """Not used right now, but kept for completeness."""
            mitigation_group = []
            try:
                url = f"{self.base_url}/mgmt/device/df/config/MitigationDevicesGroups?count=100"
                r = self.session.get(url, verify=False, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    for group in data.get("MitigationDevicesGroups", []):
                        group_name = group.get("name", "")
                        devices = group.get("devices", [])
                        device_names = [d.get("name") for d in devices]
                        mitigation_group.append(
                            {"group_name": group_name, "devices": device_names}
                        )
                    return mitigation_group
                else:
                    helper.log_error(
                        f"[VRM-CPS] get_mg_devices: status={r.status_code}"
                    )
                    return []
            except Exception as e:
                helper.log_error(f"[VRM-CPS] Exception in get_mg_devices: {e}")
                return []

        def _build_cps_payload(self, lookback_minutes, selected_devices):
            """
            Build CPS payload per your example, per DP:
                - selectedDevices: [{deviceId: "<ip>", networkPolicies: [], ports: []}]
                - protocols: ["UDP","TCP"]
                - scopeType: "device"
                - include: "ACTIVE_ONLY"
                - originatedByDF: false
                - timeInterval.from = now - lookback_minutes
            """
            now_ms = int(_time.time() * 1000)
            from_ms = now_ms - lookback_minutes * 60 * 1000

            return {
                "selectedDevices": selected_devices,
                "filterString": "",
                "include": "ACTIVE_ONLY",
                "originatedByDF": False,
                "protectedObjectNames": [],
                "protocols": ["UDP", "TCP"],
                "scopeType": "device",
                "timeInterval": {
                    "from": from_ms,
                    "to": None
                }
            }

        def get_dp_cps(self, dp_ip, lookback_minutes=5):
            """
            Get CPS stats for a single DefensePro (by IP).
            Uses the CPS API:
               /cyber-controller/api/vrm/v1/traffic/defensepro/cps
            with per-DP selectedDevices payload.
            """
            self.login_if_needed()
            url = f"{self.base_url}/cyber-controller/api/vrm/v1/traffic/defensepro/cps"
            selected = [{"deviceId": dp_ip, "networkPolicies": [], "ports": []}]
            payload = self._build_cps_payload(lookback_minutes, selected)

            try:
                r = self.session.post(
                    url, json=payload, verify=False, timeout=20
                )
                
                if r.status_code == 401 or r.status_code == 403:
                    helper.log_warning("[VRM-CPS] Authentication failed on CPS call, attempting re-login")
                    self.login_if_needed(force=True)
                    r = self.session.post(
                        url, json=payload, verify=False, timeout=20
                    )
                
                r.raise_for_status()
                return r.json()
            except Exception as e:
                helper.log_error(f"[VRM-CPS] Failed to get CPS from {self.active_host}: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    self.login_if_needed(force=True)
                    url = f"{self.base_url}/cyber-controller/api/vrm/v1/traffic/defensepro/cps"
                    r = self.session.post(
                        url, json=payload, verify=False, timeout=20
                    )
                    r.raise_for_status()
                    return r.json()
                raise

        def get_all_dp_cps_from_mg(self, lookback_minutes=5):
            """
            For every DefensePro returned by get_mitigation_groups(),
            call CPS API and return a list of:
                {
                  "dp_name": ...,
                  "ip_address": ...,
                  "mg_groups": [...],
                  "stats": <raw json from CPS API>
                }
            """
            devices = self.get_mitigation_groups()
            results = []

            for dev in devices:
                ip = dev.get("ip_address")
                if not ip:
                    continue

                try:
                    stats = self.get_dp_cps(ip, lookback_minutes)
                    results.append(
                        {
                            "dp_name": dev.get("dp_name"),
                            "ip_address": ip,
                            "mg_groups": dev.get("mg_groups", []),
                            "stats": stats,
                        }
                    )
                    helper.log_info(
                        f"[VRM-CPS] Collected CPS for {ip} ({dev.get('dp_name')})"
                    )
                except Exception as e:
                    helper.log_error(f"[VRM-CPS] Failed CPS query for {ip}: {e}")

            return results

    # ========= 3. Use the client and write events to Splunk =========
    client = VRMClient(primary_vrm_host, secondary_vrm_host, username, password)

    try:
        client.login()
    except Exception as e:
        helper.log_error(f"[VRM-CPS] Login failed: {e}")
        return

    all_stats = client.get_all_dp_cps_from_mg(lookback_minutes)

    event_count = 0

    for item in all_stats:
        dp_name = item["dp_name"]
        ip = item["ip_address"]
        mg_groups = item["mg_groups"]
        stats = item["stats"]

        # rows are under stats["data"], each with a "row" dict like:
        # { "timeStamp": "1764056355000", "TCP": "211.0", "UDP": "215.0" }
        for entry in stats.get("data", []):
            row = entry.get("row", {})

            # parse timestamp in ms
            device_ts_ms_raw = row.get("timeStamp", 0.0)
            try:
                device_ts_ms = float(device_ts_ms_raw)
            except (TypeError, ValueError):
                device_ts_ms = 0.0

            event_body = {
                "dp_name": dp_name,
                "dp_ip": ip,
                "mg_groups": mg_groups,
                "device_timestamp_ms": device_ts_ms,
            }

            # Add CPS values per protocol: TCP, UDP, etc.
            for key, val in row.items():
                if key == "timeStamp":
                    continue
                # store as <protocol>_CPS
                try:
                    event_body[f"{key}_CPS"] = float(val)
                except (TypeError, ValueError):
                    helper.log_debug(f"[VRM-CPS] Non-numeric CPS value for {key}: {val}")
                    event_body[f"{key}_CPS"] = val

            # Use device timestamp as event time if present
            event_time = None
            if device_ts_ms:
                event_time = device_ts_ms / 1000.0

            event_obj = helper.new_event(
                data=json.dumps(event_body),
                index=index,  # use the configured index
                sourcetype="radware:new:conn",
                source=f"radware_vrm://{ip}/cps",
                time=event_time,
            )
            ew.write_event(event_obj)
            event_count += 1

    helper.log_info(f"[VRM-CPS] Finished collection. Wrote {event_count} events.")

    # ========= 4. Logout =========
    try:
        client.logout()
    except Exception as e:
        helper.log_error(f"[VRM-CPS] Logout failed: {e}")
    finally:
        client.session.close()
