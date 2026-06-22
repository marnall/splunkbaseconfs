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
                helper.log_warning(f"[VRM-PO] Invalid traffic_direction '{traffic_direction}', defaulting to 'both'")
                traffic_direction = "both"
    except:
        traffic_direction = "both"
    
    index = index_num
    
    # Get checkpoint for PO data collection - use primary host for checkpoint key
    checkpoint_key = f"{primary_vrm_host}_po_last_collection"
    last_po_collection_time = helper.get_check_point(checkpoint_key)
    
    # Calculate the from_time for PO collection
    now_ms = int(time.time() * 1000)
    po_from_time_ms = None
    
    if last_po_collection_time:
        try:
            last_timestamp_ms = int(float(last_po_collection_time))
            fallback_time_ms = now_ms - (lookback_minutes * 60 * 1000)
            po_from_time_ms = max(last_timestamp_ms, fallback_time_ms)
            helper.log_info(f"[VRM-PO] Last checkpoint: {last_timestamp_ms}, using from_time: {po_from_time_ms}")
        except Exception as e:
            helper.log_warning(f"[VRM-PO] Invalid checkpoint time ({e}), using lookback_minutes")
            po_from_time_ms = now_ms - (lookback_minutes * 60 * 1000)
    else:
        helper.log_info("[VRM-PO] No checkpoint found, using lookback_minutes for initial collection")
        po_from_time_ms = now_ms - (lookback_minutes * 60 * 1000)
    
    if secondary_vrm_host:
        helper.log_info(f"[VRM-PO] Starting with primary: {primary_vrm_host}, secondary: {secondary_vrm_host}")
    else:
        helper.log_info(f"[VRM-PO] Starting with primary: {primary_vrm_host} (no secondary configured)")
    
    helper.log_info(f"[VRM-PO] Parameters - from_time: {po_from_time_ms}, Direction: {traffic_direction}")

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
                helper.log_warning(f"[VRM-PO] Primary VRM ({self.primary_host}) failed, switching to secondary ({self.secondary_host})")
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
                helper.log_info(f"[VRM-PO] Login OK to {self.active_host}")
            except Exception as e:
                helper.log_error(f"[VRM-PO] Login failed to {self.active_host}: {e}")
                # Try secondary if primary fails
                if self.switch_to_secondary():
                    url = f"{self.base_url}/mgmt/system/user/login"
                    r = self.session.post(url, json=payload, verify=False, timeout=10)
                    r.raise_for_status()
                    self.logged_in = True
                    self.last_login_time = time.time()
                    helper.log_info(f"[VRM-PO] Login OK to {self.active_host} (secondary)")
                else:
                    raise

        def login_if_needed(self, force=False):
            current_time = time.time()
            time_since_login = current_time - self.last_login_time
            
            if force or not self.logged_in or time_since_login > 600:
                helper.log_info(f"[VRM-PO] Re-authenticating to {self.active_host} (time since last login: {time_since_login:.0f}s)")
                try:
                    self.login()
                except Exception as e:
                    helper.log_error(f"[VRM-PO] Re-authentication failed: {e}")
                    raise

        def logout(self):
            url = f"{self.base_url}/mgmt/system/user/logout"
            try:
                r = self.session.post(url, verify=False, timeout=10)
                r.raise_for_status()
                helper.log_info(f"[VRM-PO] Logout OK from {self.active_host}")
            except Exception as e:
                helper.log_warning(f"[VRM-PO] Logout failed from {self.active_host}: {e}")

        def get_protected_objects(self):
            url = f"{self.base_url}/cyber-controller/api/dfc/v1/protected-objects/search"
            payload = {"names": []}
            
            try:
                helper.log_info(f"[VRM-PO] Fetching protected objects from {self.active_host}")
                helper.log_info(f"[VRM-PO] Calling PO API: {url}")
                r = self.session.post(url, json=payload, verify=False, timeout=10)
                
                helper.log_info(f"[VRM-PO] PO API status code: {r.status_code}")
                
                if r.status_code == 401 or r.status_code == 403:
                    helper.log_warning("[VRM-PO] Authentication failed on PO call, attempting re-login")
                    self.login()
                    r = self.session.post(url, json=payload, verify=False, timeout=10)
                    helper.log_info(f"[VRM-PO] After re-login, PO API status code: {r.status_code}")
                
                if r.status_code != 200:
                    helper.log_error(f"[VRM-PO] PO API returned status {r.status_code}: {r.text[:500]}")
                    return []
                
                data = r.json()
                helper.log_info(f"[VRM-PO] Raw API response type: {type(data)}")
                helper.log_info(f"[VRM-PO] PO API response length: {len(data)} objects")
                
                # Log all POs for debugging
                if len(data) > 0:
                    helper.log_info(f"[VRM-PO] First PO sample: {data[0]}")
                
                po_names = []
                for idx, po in enumerate(data):
                    po_name = po.get("name")
                    if po_name:
                        po_names.append(po_name)
                        helper.log_info(f"[VRM-PO] Processing PO {idx + 1}/{len(data)}: {po_name}")
                
                helper.log_info(f"[VRM-PO] Successfully found {len(po_names)} protected objects: {po_names}")
                return po_names
            except Exception as e:
                helper.log_error(f"[VRM-PO] Failed to get protected objects from {self.active_host}: {str(e)}")
                import traceback
                helper.log_error(f"[VRM-PO] Traceback: {traceback.format_exc()}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    try:
                        self.login()
                        url = f"{self.base_url}/cyber-controller/api/dfc/v1/protected-objects/search"
                        helper.log_info(f"[VRM-PO] Retrying PO API from secondary {self.active_host}")
                        r = self.session.post(url, json=payload, verify=False, timeout=10)
                        if r.status_code == 200:
                            data = r.json()
                            helper.log_info(f"[VRM-PO] Received {len(data)} POs from secondary")
                            po_names = [po.get("name") for po in data if po.get("name")]
                            return po_names
                    except Exception as e2:
                        helper.log_error(f"[VRM-PO] Failed to get POs from secondary: {str(e2)}")
                return []

        def _build_stats_payload(self, lookback_minutes, unit="bps", protected_object_names=None, monitoring_protocol="all", from_time_ms=None, direction="Inbound"):
            now_ms = int(time.time() * 1000)
            
            if from_time_ms is not None:
                from_ms = from_time_ms
            else:
                from_ms = now_ms - lookback_minutes * 60 * 1000

            payload = {
                "direction": direction,
                "monitoringProtocol": monitoring_protocol,
                "selectedDevices": [],  # Empty for PO traffic
                "enforce": "minDPDeviceVersion=8.21",
                "filterString": "",
                "protectedObjectNames": protected_object_names or [],
                "timeInterval": {"from": from_ms, "to": None},
                "unit": unit,
            }
            
            return payload

        def get_po_traffic(self, po_name, lookback_minutes=5, unit="bps", monitoring_protocol="all", from_time_ms=None, direction="Inbound"):
            url = f"{self.base_url}/mgmt/vrm/dp-traffic/statistic"
            
            payload = self._build_stats_payload(lookback_minutes, unit, [po_name], monitoring_protocol, from_time_ms, direction)

            try:
                r = self.session.post(url, json=payload, verify=False, timeout=20)
                
                if r.status_code == 401 or r.status_code == 403:
                    helper.log_warning("[VRM-PO] Authentication failed on po_traffic call, attempting re-login")
                    self.login()
                    r = self.session.post(url, json=payload, verify=False, timeout=20)
                
                # Handle 500 errors gracefully - likely means PO doesn't support this protocol
                if r.status_code == 500:
                    helper.log_warning(f"[VRM-PO] API returned 500 for PO '{po_name}' with protocol '{monitoring_protocol}' - skipping")
                    return {"data": []}
                
                r.raise_for_status()
                return r.json()
            except requests.exceptions.HTTPError as e:
                # Only failover for connection/network errors, not for 500 errors
                if hasattr(e.response, 'status_code') and e.response.status_code == 500:
                    helper.log_warning(f"[VRM-PO] Server error (500) for PO '{po_name}' - continuing with next query")
                    return {"data": []}
                helper.log_error(f"[VRM-PO] Failed to get po_traffic from {self.active_host}: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    self.login()
                    url = f"{self.base_url}/mgmt/vrm/dp-traffic/statistic"
                    r = self.session.post(url, json=payload, verify=False, timeout=20)
                    r.raise_for_status()
                    return r.json()
                raise
            except Exception as e:
                helper.log_error(f"[VRM-PO] Failed to get po_traffic from {self.active_host}: {e}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    self.login()
                    url = f"{self.base_url}/mgmt/vrm/dp-traffic/statistic"
                    r = self.session.post(url, json=payload, verify=False, timeout=20)
                    r.raise_for_status()
                    return r.json()
                raise

        def get_all_po_traffic(self, lookback_minutes=5, from_time_ms=None, traffic_direction="both"):
            po_names = self.get_protected_objects()
            results = []
            
            if not po_names:
                helper.log_info("[VRM-PO] No protected objects found, skipping PO traffic collection")
                return results
            
            protocols = ["all", "icmp", "other", "udp", "tcp"]
            
            if traffic_direction == "both":
                directions = ["Inbound", "Outbound"]
            elif traffic_direction == "inbound":
                directions = ["Inbound"]
            elif traffic_direction == "outbound":
                directions = ["Outbound"]
            else:
                directions = ["Inbound"]
            
            for po_name in po_names:
                for direction in directions:
                    for protocol in protocols:
                        # Collect PO traffic in bps
                        try:
                            helper.log_info(f"[VRM-PO] Querying PO traffic ({direction}, bps, {protocol}) for {po_name}...")
                            stats_bps = self.get_po_traffic(po_name, lookback_minutes, unit="bps", monitoring_protocol=protocol, from_time_ms=from_time_ms, direction=direction)
                            
                            data_points = len(stats_bps.get("data", []))
                            helper.log_info(f"[VRM-PO] PO {po_name} ({direction}, bps, {protocol}): received {data_points} data points")
                            
                            if data_points > 0:
                                results.append({
                                    "stats": stats_bps,
                                    "unit": "bps",
                                    "po_name": po_name,
                                    "monitoring_protocol": protocol,
                                    "direction": direction,
                                })
                                helper.log_info(f"[VRM-PO] ✓ Collected PO traffic ({direction}, bps, {protocol}) for {po_name}")
                            else:
                                helper.log_info(f"[VRM-PO] ⚠ No traffic data for PO {po_name} ({direction}, bps, {protocol})")
                                
                        except Exception as e:
                            helper.log_error(f"[VRM-PO] Failed PO traffic ({direction}, bps, {protocol}) for {po_name}: {e}")
                            import traceback
                            helper.log_error(f"[VRM-PO] Traceback: {traceback.format_exc()}")
                        
                        # Collect PO traffic in pps
                        try:
                            helper.log_info(f"[VRM-PO] Querying PO traffic ({direction}, pps, {protocol}) for {po_name}...")
                            stats_pps = self.get_po_traffic(po_name, lookback_minutes, unit="pps", monitoring_protocol=protocol, from_time_ms=from_time_ms, direction=direction)
                            
                            data_points = len(stats_pps.get("data", []))
                            helper.log_info(f"[VRM-PO] PO {po_name} ({direction}, pps, {protocol}): received {data_points} data points")
                            
                            if data_points > 0:
                                results.append({
                                    "stats": stats_pps,
                                    "unit": "pps",
                                    "po_name": po_name,
                                    "monitoring_protocol": protocol,
                                    "direction": direction,
                                })
                                helper.log_info(f"[VRM-PO] ✓ Collected PO traffic ({direction}, pps, {protocol}) for {po_name}")
                            else:
                                helper.log_info(f"[VRM-PO] ⚠ No traffic data for PO {po_name} ({direction}, pps, {protocol})")
                                
                        except Exception as e:
                            helper.log_error(f"[VRM-PO] Failed PO traffic ({direction}, pps, {protocol}) for {po_name}: {e}")
                            import traceback
                            helper.log_error(f"[VRM-PO] Traceback: {traceback.format_exc()}")
            
            return results

    # ========= 3. Use the client and write events to Splunk =========
    client = VRMClient(primary_vrm_host, secondary_vrm_host, username, password)

    try:
        # login
        try:
            client.login()
        except Exception as e:
            helper.log_error(f"[VRM-PO] Login failed: {e}")
            return

        # Collect protected object traffic only
        helper.log_info("[VRM-PO] Starting protected object traffic collection")
        po_stats = client.get_all_po_traffic(lookback_minutes, from_time_ms=po_from_time_ms, traffic_direction=traffic_direction)
        helper.log_info(f"[VRM-PO] Collected {len(po_stats)} PO stat sets")

        event_count = 0
        latest_po_timestamp = 0

        for item in po_stats:
            stats = item["stats"]
            unit = item["unit"]
            po_name = item.get("po_name")
            monitoring_protocol = item.get("monitoring_protocol", "all")
            direction = item.get("direction", "Inbound")

            for entry in stats.get("data", []):
                row = entry.get("row", {})
                
                # Track latest timestamp for checkpoint
                timestamp_ms = float(row.get("timeStamp", 0))
                if timestamp_ms > latest_po_timestamp:
                    latest_po_timestamp = timestamp_ms
                
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
                    "device_timestamp_ms": timestamp_ms,
                    "trafficValue": traffic_value,
                    "discards": discards,
                    "excluded": excluded,
                    "challengeIng": challenge_ing,
                    "unit": unit,
                    "scope": "protectedObject",
                    "monitoring_protocol": monitoring_protocol,
                    "direction": direction,
                    "po_name": po_name,
                }

                # Create Splunk event
                event_obj = helper.new_event(
                    data=json.dumps(event_body),
                    index=index,
                    sourcetype="radware:dp:po_traffic",
                    source=f"radware_vrm://po/{po_name}",
                )
                ew.write_event(event_obj)
                event_count += 1

        # Save checkpoint for next PO collection
        if latest_po_timestamp > 0:
            helper.save_check_point(checkpoint_key, str(int(latest_po_timestamp)))
            helper.log_info(f"[VRM-PO] Saved checkpoint: {int(latest_po_timestamp)}")
        else:
            # If no events were collected, save current time
            helper.save_check_point(checkpoint_key, str(now_ms))
            helper.log_info(f"[VRM-PO] No events collected, saving current time as checkpoint: {now_ms}")

        helper.log_info(f"[VRM-PO] Finished collection. Wrote {event_count} events.")

        # ========= 4. Logout =========
        try:
            client.logout()
        except Exception as e:
            helper.log_error(f"[VRM-PO] Logout failed: {e}")
    finally:
        client.session.close()
