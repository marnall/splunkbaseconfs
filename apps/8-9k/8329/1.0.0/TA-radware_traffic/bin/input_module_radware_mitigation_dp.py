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
    pass


def collect_events(helper, ew):
    import requests
    import time
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
        helper.log_info(f"[VRM-MITIGATION-DEVICE] Starting with primary: {primary_vrm_host}, secondary: {secondary_vrm_host}")
    else:
        helper.log_info(f"[VRM-MITIGATION-DEVICE] Starting with primary: {primary_vrm_host} (no secondary configured)")

    # ========= 2. Define VRMClient class =========
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
                helper.log_warning(f"[VRM-MITIGATION-DEVICE] Primary VRM ({self.primary_host}) failed, switching to secondary ({self.secondary_host})")
                self.active_host = self.secondary_host
                self.primary_failed = True
                self.logged_in = False
                return True
            return False
        
        def switch_to_primary(self):
            """Switch back to primary VRM host if secondary fails"""
            if self.primary_failed and self.secondary_host:
                helper.log_warning(f"[VRM-MITIGATION-DEVICE] Secondary VRM ({self.secondary_host}) failed, switching back to primary ({self.primary_host})")
                self.active_host = self.primary_host
                self.primary_failed = False
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
                self.last_login_time = time.time()
                helper.log_info(f"[VRM-MITIGATION-DEVICE] Login OK to {self.active_host}")
            except Exception as e:
                helper.log_error(f"[VRM-MITIGATION-DEVICE] Login failed to {self.active_host}: {e}")
                # Try secondary if primary fails
                if self.switch_to_secondary():
                    url = f"{self.base_url}/mgmt/system/user/login"
                    r = self.session.post(url, json=payload, verify=False, timeout=10)
                    r.raise_for_status()
                    self.logged_in = True
                    self.last_login_time = time.time()
                    helper.log_info(f"[VRM-MITIGATION-DEVICE] Login OK to {self.active_host} (secondary)")
                else:
                    raise
        
        def login_if_needed(self, force=False):
            current_time = time.time()
            time_since_login = current_time - self.last_login_time
            
            if force or not self.logged_in or time_since_login > 600:
                helper.log_info(f"[VRM-MITIGATION-DEVICE] Re-authenticating to {self.active_host} (time since last login: {time_since_login:.0f}s)")
                try:
                    self.login()
                except Exception as e:
                    helper.log_error(f"[VRM-MITIGATION-DEVICE] Re-authentication failed: {e}")
                    raise

        def logout(self):
            url = f"{self.base_url}/mgmt/system/user/logout"
            payload = {"username": self.username, "password": self.password}
            try:
                r = self.session.post(url, json=payload, verify=False, timeout=10)
                r.raise_for_status()
                helper.log_info(f"[VRM-MITIGATION-DEVICE] Logout OK from {self.active_host}")
            except Exception as e:
                helper.log_warning(f"[VRM-MITIGATION-DEVICE] Logout failed from {self.active_host}: {e}")

        def _make_request_with_retry(self, method, url, max_retries=2, **kwargs):
            """
            Make HTTP request with automatic re-authentication on 401/403.
            Only re-authenticates if we get auth errors, not for every call.
            """
            for attempt in range(max_retries + 1):
                try:
                    if method == 'GET':
                        r = self.session.get(url, **kwargs)
                    elif method == 'POST':
                        r = self.session.post(url, **kwargs)
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                    
                    # If we get 401/403, try to re-authenticate once
                    if r.status_code in [401, 403] and attempt < max_retries:
                        helper.log_warning(f"[VRM-MITIGATION-DEVICE] Got {r.status_code}, re-authenticating...")
                        self.login()
                        continue  # Retry the request
                    
                    return r
                    
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                        helper.log_warning(f"[VRM-MITIGATION-DEVICE] Request failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        raise
            
            raise Exception(f"Failed after {max_retries + 1} attempts")

        def get_mitigation_devices(self):
            """
            Get mitigation devices with their groups.
            Returns: list of dicts
            """
            result = []
            try:
                url = f"{self.base_url}/mgmt/v2/device/df/restv2/configure/mitigation-devices"
                r = self._make_request_with_retry('GET', url, verify=False, timeout=10)
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
                        f"[VRM-MITIGATION-DEVICE] get_mitigation_devices: status={r.status_code}"
                    )
                    return []
            except Exception as e:
                helper.log_error(f"[VRM-MITIGATION-DEVICE] Exception in get_mitigation_devices from {self.active_host}: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    try:
                        self.login()
                        url = f"{self.base_url}/mgmt/v2/device/df/restv2/configure/mitigation-devices"
                        r = self._make_request_with_retry('GET', url, verify=False, timeout=10)
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
                    except Exception as e2:
                        helper.log_error(f"[VRM-MITIGATION-DEVICE] Exception in get_mitigation_devices from secondary: {e2}")
                return []

        def _build_mitigation_bandwidth_payload(self, lookback_minutes, selected_devices):
            """
            Build payload for mitigation-bandwidth API (device scope only)
            """
            now_ms = int(time.time() * 1000)
            from_ms = now_ms - lookback_minutes * 60 * 1000

            payload = {
                "defenseFlowScope": {
                    "protectedObjects": [],
                    "activationIds": []
                },
                "filterString": "",
                "protectedObjectNames": [],
                "selectedDevices": selected_devices,
                "timeInterval": {
                    "from": from_ms,
                    "to": None
                },
                "scopeType": "device",
                "include": "ACTIVE_ONLY"
            }
            
            return payload

        def get_mitigation_bandwidth(self, dp_ip, lookback_minutes=5, unit="bps"):
            """
            Get mitigation bandwidth stats for a specific device.
            unit: "bps" or "pps" - determines which API endpoint to use
            """
            # Different endpoints for bps vs pps
            if unit == "pps":
                url = f"{self.base_url}/mgmt/vrm/analytics/attacks/mitigation/rate/periodic/report"
            else:
                url = f"{self.base_url}/cyber-controller/api/vrm/v1/attack/defensepro/mitigation-bandwidth"
            
            selected = [{"deviceId": dp_ip, "networkPolicies": [], "ports": []}]
            payload = self._build_mitigation_bandwidth_payload(lookback_minutes, selected)

            try:
                r = self._make_request_with_retry(
                    'POST', url, json=payload, verify=False, timeout=30
                )
                r.raise_for_status()
                return r.json()
            except Exception as e:
                helper.log_error(f"[VRM-MITIGATION-DEVICE] Failed to get mitigation bandwidth from {self.active_host}: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    self.login()
                    # Rebuild URL with new active host
                    if unit == "pps":
                        url = f"{self.base_url}/mgmt/vrm/analytics/attacks/mitigation/rate/periodic/report"
                    else:
                        url = f"{self.base_url}/cyber-controller/api/vrm/v1/attack/defensepro/mitigation-bandwidth"
                    r = self._make_request_with_retry(
                        'POST', url, json=payload, verify=False, timeout=30
                    )
                    r.raise_for_status()
                    return r.json()
                raise

        def get_all_dp_mitigation_bandwidth(self, lookback_minutes=5):
            """
            For every DefensePro, collect mitigation-bandwidth data in both bps and pps.
            """
            devices = self.get_mitigation_devices()
            results = []

            for dev in devices:
                ip = dev.get("ip_address")
                if not ip:
                    continue

                # Collect in bps
                try:
                    stats_bps = self.get_mitigation_bandwidth(ip, lookback_minutes, unit="bps")
                    results.append(
                        {
                            "dp_name": dev.get("dp_name"),
                            "ip_address": ip,
                            "mg_groups": dev.get("mg_groups", []),
                            "stats": stats_bps,
                            "unit": "bps",
                        }
                    )
                    helper.log_info(
                        f"[VRM-MITIGATION-DEVICE] Collected device mitigation-bandwidth (bps) for {ip} ({dev.get('dp_name')})"
                    )
                except Exception as e:
                    helper.log_error(f"[VRM-MITIGATION-DEVICE] Failed device mitigation-bandwidth (bps) query for {ip}: {e}")

                # Collect in pps
                try:
                    stats_pps = self.get_mitigation_bandwidth(ip, lookback_minutes, unit="pps")
                    results.append(
                        {
                            "dp_name": dev.get("dp_name"),
                            "ip_address": ip,
                            "mg_groups": dev.get("mg_groups", []),
                            "stats": stats_pps,
                            "unit": "pps",
                        }
                    )
                    helper.log_info(
                        f"[VRM-MITIGATION-DEVICE] Collected device mitigation-bandwidth (pps) for {ip} ({dev.get('dp_name')})"
                    )
                except Exception as e:
                    helper.log_error(f"[VRM-MITIGATION-DEVICE] Failed device mitigation-bandwidth (pps) query for {ip}: {e}")

            return results

    # ========= 3. Use the client and write events to Splunk =========
    client = VRMClient(primary_vrm_host, secondary_vrm_host, username, password)

    try:
        # login
        try:
            client.login()
        except Exception as e:
            helper.log_error(f"[VRM-MITIGATION-DEVICE] Login failed: {e}")
            return

        # Collect device-level mitigation bandwidth
        helper.log_info("[VRM-MITIGATION-DEVICE] Starting device-level mitigation-bandwidth collection")
        device_stats = client.get_all_dp_mitigation_bandwidth(lookback_minutes)
        helper.log_info(f"[VRM-MITIGATION-DEVICE] Collected {len(device_stats)} device-level stat sets")

        event_count = 0

        for item in device_stats:
            dp_name = item["dp_name"]
            ip = item["ip_address"]
            mg_groups = item["mg_groups"]
            stats = item["stats"]
            unit = item["unit"]

            # rows are under stats["data"], each with a "row" dict
            for entry in stats.get("data", []):
                row = entry.get("row", {})

                # timeStamp comes as string – convert safely
                try:
                    device_ts = float(row.get("timeStamp", 0))
                except Exception:
                    device_ts = 0.0

                # For bps: "bandwidth" field, for pps: "packetRate" field
                try:
                    if unit == "pps":
                        value = float(row.get("packetRate", 0))
                    else:
                        value = float(row.get("bandwidth", 0)) * 1000
                except Exception:
                    value = 0.0

                category = row.get("category", "")

                event_body = {
                    "device_timestamp_ms": device_ts,
                    "value": value,  # bandwidth for bps, packetRate for pps
                    "category": category,
                    "scope": "device",
                    "unit": unit,  # bps or pps
                    "dp_name": dp_name,
                    "dp_ip": ip,
                    "mg_groups": mg_groups,
                }

                # Create Splunk event
                event_obj = helper.new_event(
                    data=json.dumps(event_body),
                    index=index,
                    sourcetype="radware:mitigation:device",
                    source=f"radware_vrm_mitigation_bw://{ip}",
                )
                ew.write_event(event_obj)
                event_count += 1

        helper.log_info(f"[VRM-MITIGATION-DEVICE] Finished collection. Wrote {event_count} events.")

        # ========= 4. Logout =========
        try:
            client.logout()
        except Exception as e:
            helper.log_error(f"[VRM-MITIGATION-DEVICE] Logout failed: {e}")
    finally:
        client.session.close()
