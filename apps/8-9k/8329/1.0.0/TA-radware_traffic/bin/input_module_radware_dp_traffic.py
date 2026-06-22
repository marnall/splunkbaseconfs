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
    
    # Optional: Traffic direction (defaults to "both" if not specified)
    try:
        traffic_direction = helper.get_arg("traffic_direction")
        if traffic_direction is None or traffic_direction == "":
            traffic_direction = "both"
        else:
            traffic_direction = str(traffic_direction).lower()
            if traffic_direction not in ["inbound", "outbound", "both"]:
                helper.log_warning(f"[VRM-DEVICE] Invalid traffic_direction '{traffic_direction}', defaulting to 'both'")
                traffic_direction = "both"
    except:
        traffic_direction = "both"
    
    index = index_num
    
    if secondary_vrm_host:
        helper.log_info(f"[VRM-DEVICE] Starting with primary: {primary_vrm_host}, secondary: {secondary_vrm_host}")
    else:
        helper.log_info(f"[VRM-DEVICE] Starting with primary: {primary_vrm_host} (no secondary configured)")
    
    helper.log_info(f"[VRM-DEVICE] Parameters - Lookback: {lookback_minutes}min, Direction: {traffic_direction}")

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
                helper.log_warning(f"[VRM-DEVICE] Primary VRM ({self.primary_host}) failed, switching to secondary ({self.secondary_host})")
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
                self.last_login_time = time.time()
                helper.log_info(f"[VRM-DEVICE] Login OK to {self.active_host}")
            except Exception as e:
                helper.log_error(f"[VRM-DEVICE] Login failed to {self.active_host}: {e}")
                # Try secondary if primary fails
                if self.switch_to_secondary():
                    url = f"{self.base_url}/mgmt/system/user/login"
                    r = self.session.post(url, json=payload, verify=False, timeout=10)
                    r.raise_for_status()
                    self.logged_in = True
                    self.last_login_time = time.time()
                    helper.log_info(f"[VRM-DEVICE] Login OK to {self.active_host} (secondary)")
                else:
                    raise

        def login_if_needed(self, force=False):
            current_time = time.time()
            time_since_login = current_time - self.last_login_time
            
            if force or not self.logged_in or time_since_login > 600:
                helper.log_info(f"[VRM-DEVICE] Re-authenticating to {self.active_host} (time since last login: {time_since_login:.0f}s)")
                try:
                    self.login()
                except Exception as e:
                    helper.log_error(f"[VRM-DEVICE] Re-authentication failed: {e}")
                    raise

        def logout(self):
            url = f"{self.base_url}/mgmt/system/user/logout"
            try:
                r = self.session.post(url, verify=False, timeout=10)
                r.raise_for_status()
                helper.log_info(f"[VRM-DEVICE] Logout OK from {self.active_host}")
            except Exception as e:
                helper.log_warning(f"[VRM-DEVICE] Logout failed from {self.active_host}: {e}")

        def get_mitigation_groups(self):
            result = []
            try:
                url = f"{self.base_url}/mgmt/v2/device/df/restv2/configure/mitigation-devices"
                helper.log_info(f"[VRM-DEVICE] Fetching mitigation groups from {self.active_host}")
                helper.log_info(f"[VRM-DEVICE] Request URL: {url}")
                r = self.session.get(url, verify=False, timeout=10)
                
                helper.log_info(f"[VRM-DEVICE] Response status: {r.status_code}")
                
                if r.status_code == 401 or r.status_code == 403:
                    helper.log_warning("[VRM-DEVICE] Authentication failed, attempting re-login")
                    self.login()
                    r = self.session.get(url, verify=False, timeout=10)
                    helper.log_info(f"[VRM-DEVICE] After re-login, response status: {r.status_code}")
                
                if r.status_code == 200:
                    data = r.json()
                    helper.log_info(f"[VRM-DEVICE] Raw API response type: {type(data)}")
                    helper.log_info(f"[VRM-DEVICE] Received {len(data)} devices from API")
                    
                    # Log the first device for debugging
                    if len(data) > 0:
                        helper.log_info(f"[VRM-DEVICE] First device sample: {data[0]}")
                    
                    for idx, dev in enumerate(data):
                        device = dev.get("name", "")
                        groups_names = dev.get("groups", [])
                        ip_address = dev.get("address", "")
                        helper.log_info(f"[VRM-DEVICE] Processing device {idx + 1}/{len(data)}: name={device}, ip={ip_address}")
                        result.append({
                            "dp_name": device,
                            "ip_address": ip_address,
                            "mg_groups": groups_names,
                        })
                    helper.log_info(f"[VRM-DEVICE] Successfully parsed {len(result)} devices")
                    return result
                else:
                    helper.log_error(f"[VRM-DEVICE] get_mitigation_groups: status={r.status_code}, response={r.text[:500]}")
                    return []
            except Exception as e:
                helper.log_error(f"[VRM-DEVICE] Exception in get_mitigation_groups from {self.active_host}: {e}")
                import traceback
                helper.log_error(f"[VRM-DEVICE] Traceback: {traceback.format_exc()}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    try:
                        self.login()
                        url = f"{self.base_url}/mgmt/v2/device/df/restv2/configure/mitigation-devices"
                        helper.log_info(f"[VRM-DEVICE] Retrying mitigation groups from secondary {self.active_host}")
                        r = self.session.get(url, verify=False, timeout=10)
                        if r.status_code == 200:
                            data = r.json()
                            helper.log_info(f"[VRM-DEVICE] Received {len(data)} devices from secondary")
                            for dev in data:
                                device = dev.get("name", "")
                                groups_names = dev.get("groups", [])
                                ip_address = dev.get("address", "")
                                result.append({
                                    "dp_name": device,
                                    "ip_address": ip_address,
                                    "mg_groups": groups_names,
                                })
                            return result
                    except Exception as e2:
                        helper.log_error(f"[VRM-DEVICE] Exception in get_mitigation_groups from secondary: {e2}")
                return []

        def _build_stats_payload(self, lookback_minutes, selected_devices, unit="bps", monitoring_protocol="all", direction="Inbound"):
            now_ms = int(time.time() * 1000)
            from_ms = now_ms - lookback_minutes * 60 * 1000

            payload = {
                "direction": direction,
                "monitoringProtocol": monitoring_protocol,
                "selectedDevices": selected_devices,
                "enforce": "minDPDeviceVersion=8.21",
                "filterString": "",
                "protectedObjectNames": [],
                "timeInterval": {"from": from_ms, "to": None},
                "unit": unit,
                "scopeType": "device",
                "include": "ACTIVE_ONLY"
            }
            
            return payload

        def get_dp_traffic(self, dp_ip, lookback_minutes=5, unit="bps", monitoring_protocol="all", direction="Inbound"):
            url = f"{self.base_url}/mgmt/vrm/dp-traffic/statistic"
            
            selected = [{"deviceId": dp_ip, "networkPolicies": [], "ports": []}]
            payload = self._build_stats_payload(lookback_minutes, selected, unit, monitoring_protocol, direction)

            try:
                r = self.session.post(url, json=payload, verify=False, timeout=20)
                
                if r.status_code == 401 or r.status_code == 403:
                    helper.log_warning("[VRM-DEVICE] Authentication failed on dp_traffic call, attempting re-login")
                    self.login()
                    r = self.session.post(url, json=payload, verify=False, timeout=20)
                
                r.raise_for_status()
                return r.json()
            except Exception as e:
                helper.log_error(f"[VRM-DEVICE] Failed to get dp_traffic from {self.active_host}: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    self.login()
                    url = f"{self.base_url}/mgmt/vrm/dp-traffic/statistic"
                    r = self.session.post(url, json=payload, verify=False, timeout=20)
                    r.raise_for_status()
                    return r.json()
                raise

        def get_all_dp_traffic_from_mg(self, lookback_minutes=5, traffic_direction="both"):
            devices = self.get_mitigation_groups()
            results = []
            
            protocols = ["all", "icmp", "other", "udp", "tcp"]
            
            if traffic_direction == "both":
                directions = ["Inbound", "Outbound"]
            elif traffic_direction == "inbound":
                directions = ["Inbound"]
            elif traffic_direction == "outbound":
                directions = ["Outbound"]
            else:
                directions = ["Inbound"]

            for dev in devices:
                ip = dev.get("ip_address")
                if not ip:
                    continue

                for direction in directions:
                    for protocol in protocols:
                        # Collect device-level traffic in bps
                        try:
                            stats_bps = self.get_dp_traffic(ip, lookback_minutes, unit="bps", monitoring_protocol=protocol, direction=direction)
                            results.append({
                                "dp_name": dev.get("dp_name"),
                                "ip_address": ip,
                                "mg_groups": dev.get("mg_groups", []),
                                "stats": stats_bps,
                                "unit": "bps",
                                "monitoring_protocol": protocol,
                                "direction": direction,
                            })
                            helper.log_info(f"[VRM-DEVICE] Collected device traffic ({direction}, bps, {protocol}) for {ip} ({dev.get('dp_name')})")
                        except Exception as e:
                            helper.log_error(f"[VRM-DEVICE] Failed device traffic ({direction}, bps, {protocol}) query for {ip}: {e}")

                        # Collect device-level traffic in pps
                        try:
                            stats_pps = self.get_dp_traffic(ip, lookback_minutes, unit="pps", monitoring_protocol=protocol, direction=direction)
                            results.append({
                                "dp_name": dev.get("dp_name"),
                                "ip_address": ip,
                                "mg_groups": dev.get("mg_groups", []),
                                "stats": stats_pps,
                                "unit": "pps",
                                "monitoring_protocol": protocol,
                                "direction": direction,
                            })
                            helper.log_info(f"[VRM-DEVICE] Collected device traffic ({direction}, pps, {protocol}) for {ip} ({dev.get('dp_name')})")
                        except Exception as e:
                            helper.log_error(f"[VRM-DEVICE] Failed device traffic ({direction}, pps, {protocol}) query for {ip}: {e}")

            return results

    # ========= 3. Use the client and write events to Splunk =========
    client = VRMClient(primary_vrm_host, secondary_vrm_host, username, password)

    try:
        # login
        try:
            client.login()
        except Exception as e:
            helper.log_error(f"[VRM-DEVICE] Login failed: {e}")
            return

        # Collect device-level traffic only
        helper.log_info("[VRM-DEVICE] Starting device-level traffic collection")
        device_stats = client.get_all_dp_traffic_from_mg(lookback_minutes, traffic_direction)
        helper.log_info(f"[VRM-DEVICE] Collected {len(device_stats)} device-level stat sets")

        event_count = 0

        for item in device_stats:
            dp_name = item["dp_name"]
            ip = item["ip_address"]
            mg_groups = item["mg_groups"]
            stats = item["stats"]
            unit = item["unit"]
            monitoring_protocol = item.get("monitoring_protocol", "all")
            direction = item.get("direction", "Inbound")

            for entry in stats.get("data", []):
                row = entry.get("row", {})
                
                # Multiply traffic value by 1000 if unit is bps
                # Handle None values by using 0 as default
                traffic_value = float(row.get("trafficValue") or 0)
                excluded = float(row.get("excluded") or 0)
                challenge_ing = float(row.get("challengeIng") or 0)
                discards = float(row.get("discards") or 0)
                if unit == "bps":
                    traffic_value = traffic_value * 1000
                    excluded = excluded * 1000
                    challenge_ing = challenge_ing * 1000
                    discards = discards * 1000
                    
                event_body = {
                    "device_timestamp_ms": float(row.get("timeStamp", 0)),
                    "trafficValue": traffic_value,
                    "discards": discards,
                    "excluded": excluded,
                    "challengeIng": challenge_ing,
                    "unit": unit,
                    "scope": "device",
                    "monitoring_protocol": monitoring_protocol,
                    "direction": direction,
                    "dp_name": dp_name,
                    "dp_ip": ip,
                    "mg_groups": mg_groups,
                }

                # Create Splunk event
                event_obj = helper.new_event(
                    data=json.dumps(event_body),
                    index=index,
                    sourcetype="radware:dp:traffic",
                    source=f"radware_vrm://{ip}",
                )
                ew.write_event(event_obj)
                event_count += 1

        helper.log_info(f"[VRM-DEVICE] Finished collection. Wrote {event_count} events.")

        # ========= 4. Logout =========
        try:
            client.logout()
        except Exception as e:
            helper.log_error(f"[VRM-DEVICE] Logout failed: {e}")
    finally:
        client.session.close()
