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
    # Example access (uncomment if you want to validate):
    # vrm_host        = definition.parameters.get('vrm_host', None)
    # username        = definition.parameters.get('username', None)
    # password        = definition.parameters.get('password', None)
    # lookback_minutes = definition.parameters.get('lookback_minutes', None)
    #
    # You could, for example, check that lookback_minutes is a positive int.
    pass


def collect_events(helper, ew):
    import requests
    import json
    import time as _time
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ========= 1. Read parameters from this input =========
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

    # Let Splunk use the index configured in the input stanza.
    index = index_num
    
    if secondary_vrm_host:
        helper.log_info(f"[VRM-NETFLOW] Starting with primary: {primary_vrm_host}, secondary: {secondary_vrm_host}")
    else:
        helper.log_info(f"[VRM-NETFLOW] Starting with primary: {primary_vrm_host} (no secondary configured)")

    # ========= 2. VRM client for NetFlow endpoint =========
    class VRMNetflowClient:
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
                helper.log_warning(f"[VRM-NETFLOW] Primary VRM ({self.primary_host}) failed, switching to secondary ({self.secondary_host})")
                self.active_host = self.secondary_host
                self.primary_failed = True
                self.logged_in = False
                return True
            return False

        # -------- login --------
        def login(self):
            url = f"{self.base_url}/mgmt/system/user/login"
            payload = {
                "username": self.username,
                "password": self.password
            }
            
            try:
                r = self.session.post(url, json=payload, verify=False, timeout=10)
                r.raise_for_status()
                self.logged_in = True
                self.last_login_time = _time.time()
                helper.log_info(f"[VRM-NETFLOW] Login OK to {self.active_host}")
            except Exception as e:
                helper.log_error(f"[VRM-NETFLOW] Login failed to {self.active_host}: {e}")
                # Try secondary if primary fails
                if self.switch_to_secondary():
                    url = f"{self.base_url}/mgmt/system/user/login"
                    r = self.session.post(url, json=payload, verify=False, timeout=10)
                    r.raise_for_status()
                    self.logged_in = True
                    self.last_login_time = _time.time()
                    helper.log_info(f"[VRM-NETFLOW] Login OK to {self.active_host} (secondary)")
                else:
                    raise

        def login_if_needed(self, force=False):
            current_time = _time.time()
            time_since_login = current_time - self.last_login_time
            
            if force or not self.logged_in or time_since_login > 600:
                helper.log_info(f"[VRM-NETFLOW] Re-authenticating to {self.active_host} (time since last login: {time_since_login:.0f}s)")
                try:
                    self.login()
                except Exception as e:
                    helper.log_error(f"[VRM-NETFLOW] Re-authentication failed: {e}")
                    raise

        def logout(self):
            url = f"{self.base_url}/mgmt/system/user/logout"
            payload = {
                "username": self.username,
                "password": self.password
            }
            try:
                r = self.session.post(url, json=payload, verify=False, timeout=10)
                r.raise_for_status()
                helper.log_info(f"[VRM-NETFLOW] Logout OK from {self.active_host}")
            except Exception as e:
                helper.log_warning(f"[VRM-NETFLOW] Logout failed from {self.active_host}: {e}")

        # -------- build payload for netflow stats --------
        def _build_payload(self, lookback_minutes, unit="bps", monitoring_protocol="all"):
            now_ms = int(_time.time() * 1000)
            from_ms = now_ms - lookback_minutes * 60 * 1000

            return {
                "direction": "Inbound",
                "monitoringProtocol": monitoring_protocol,
                "selectedDevices": [],          # empty -> all devices
                "timeInterval": {
                    "from": from_ms,
                    "to": None
                },
                "unit": unit,
                "filterString": "",
                "protectedObjectNames": [],
                "enforce": "minDPDeviceVersion=8.21"
            }

        # -------- call netflow API --------
        def get_netflow_stats(self, lookback_minutes, unit="bps", monitoring_protocol="all"):
            self.login_if_needed()
            url = f"{self.base_url}/cyber-controller/api/vrm/v1/traffic/flowdetector/netflow"
            payload = self._build_payload(lookback_minutes, unit, monitoring_protocol)

            try:
                r = self.session.post(url, json=payload, verify=False, timeout=20)
                
                if r.status_code == 401 or r.status_code == 403:
                    helper.log_warning("[VRM-NETFLOW] Authentication failed on netflow call, attempting re-login")
                    self.login_if_needed(force=True)
                    r = self.session.post(url, json=payload, verify=False, timeout=20)
                
                r.raise_for_status()
                return r.json()
            except Exception as e:
                helper.log_error(f"[VRM-NETFLOW] Failed to get netflow stats from {self.active_host}: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    self.login_if_needed(force=True)
                    url = f"{self.base_url}/cyber-controller/api/vrm/v1/traffic/flowdetector/netflow"
                    r = self.session.post(url, json=payload, verify=False, timeout=20)
                    r.raise_for_status()
                    return r.json()
                raise
        
        # -------- get netflow stats for both bps and pps --------
        def get_all_netflow_stats(self, lookback_minutes):
            """
            Collect netflow stats in both bps and pps for all monitoring protocols.
            Returns list of dicts with unit, monitoring_protocol, and stats.
            """
            results = []
            
            # Define protocol options - "all" is the main one, others are for protocol breakdown
            protocols = ["all", "icmp", "other", "udp", "tcp"]
            
            # For each protocol, collect in both bps and pps
            for protocol in protocols:
                # Collect in bps
                try:
                    helper.log_info(f"[VRM-NETFLOW] Collecting netflow stats (bps, {protocol})...")
                    stats_bps = self.get_netflow_stats(lookback_minutes, unit="bps", monitoring_protocol=protocol)
                    results.append({
                        "unit": "bps",
                        "monitoring_protocol": protocol,
                        "stats": stats_bps
                    })
                    helper.log_info(f"[VRM-NETFLOW] Collected {len(stats_bps.get('data', []))} data points (bps, {protocol})")
                except Exception as e:
                    helper.log_error(f"[VRM-NETFLOW] Failed to get netflow stats (bps, {protocol}): {e}")
                
                # Collect in pps
                try:
                    helper.log_info(f"[VRM-NETFLOW] Collecting netflow stats (pps, {protocol})...")
                    stats_pps = self.get_netflow_stats(lookback_minutes, unit="pps", monitoring_protocol=protocol)
                    results.append({
                        "unit": "pps",
                        "monitoring_protocol": protocol,
                        "stats": stats_pps
                    })
                    helper.log_info(f"[VRM-NETFLOW] Collected {len(stats_pps.get('data', []))} data points (pps, {protocol})")
                except Exception as e:
                    helper.log_error(f"[VRM-NETFLOW] Failed to get netflow stats (pps, {protocol}): {e}")
            
            return results

    # ========= 3. Use client & write events to Splunk =========
    client = VRMNetflowClient(primary_vrm_host, secondary_vrm_host, username, password)

    try:
        # login
        try:
            client.login()
        except Exception as e:
            helper.log_error(f"[VRM-NETFLOW] Login failed: {e}")
            return

        # fetch data for both bps and pps
        try:
            all_netflow_data = client.get_all_netflow_stats(lookback_minutes)
        except Exception as e:
            helper.log_error(f"[VRM-NETFLOW] Failed to get netflow stats: {e}")
            return

        sourcetype = "radware:fnm:traffic"
        source = f"radware_vrm://{primary_vrm_host}/netflow"

        events_written = 0

        # Process each unit's data (bps and pps)
        for dataset in all_netflow_data:
            unit = dataset["unit"]
            monitoring_protocol = dataset["monitoring_protocol"]
            netflow_data = dataset["stats"]
            
            # ---- per-row events from "data" ----
            for item in netflow_data.get("data", []):
                row = item.get("row", {})

                device_ts_ms = float(row.get("timeStamp", 0.0))
                
                # Multiply values by 1000 if unit is bps
                multiplier = 1000 if unit == "bps" else 1
                
                event_body = {
                    "device_timestamp_ms": device_ts_ms,
                    "ceDropped":        float(row.get("ceDropped", 0.0)) * multiplier,
                    "ceDroppedOut":     float(row.get("ceDroppedOut", 0.0)) * multiplier,
                    "ceDiverted":       float(row.get("ceDiverted", 0.0)) * multiplier,
                    "ceFragmented":     float(row.get("ceFragmented", 0.0)) * multiplier,
                    "ceOutbound":       float(row.get("ceOutbound", 0.0)) * multiplier,
                    "ceInbound":        float(row.get("ceInbound", 0.0)) * multiplier,
                    "ceDiscarded":      float(row.get("ceDiscarded", 0.0)) * multiplier,
                    "ceFragmentedOut":  float(row.get("ceFragmentedOut", 0.0)) * multiplier,
                    "docCount":         float(row.get("docCount", 0.0)),
                    "unit":             unit,  # Add unit to distinguish bps vs pps
                    "monitoring_protocol": monitoring_protocol,  # fragmented, icmp, other, udp, tcp, all
                }

                # Use device timestamp as event time if present
                event_time = None
                if device_ts_ms:
                    event_time = device_ts_ms / 1000.0

                event_obj = helper.new_event(
                    data=json.dumps(event_body),
                    time=event_time,
                    index=index,
                    sourcetype=sourcetype,
                    source=source,
                )
                ew.write_event(event_obj)
                events_written += 1

            # ---- optional summary event from "dataMap" ----
            data_map = netflow_data.get("dataMap", {})
            if data_map:
                try:
                    # Add unit and monitoring_protocol to summary as well
                    summary_data = dict(data_map)
                    summary_data["unit"] = unit
                    summary_data["monitoring_protocol"] = monitoring_protocol
                    
                    summary_event = helper.new_event(
                        data=json.dumps(summary_data),
                        time=_time.time(),
                        index=index,
                        sourcetype=f"{sourcetype}:summary",
                        source=source,
                    )
                    ew.write_event(summary_event)
                    events_written += 1
                except Exception as e:
                    helper.log_error(f"[VRM-NETFLOW] Failed to write summary event ({unit}): {e}")

        helper.log_info(f"[VRM-NETFLOW] Finished collection, wrote {events_written} events.")

        # ========= 4. Logout =========
        try:
            client.logout()
        except Exception as e:
            helper.log_error(f"[VRM-NETFLOW] Logout failed: {e}")
    finally:
        client.session.close()
