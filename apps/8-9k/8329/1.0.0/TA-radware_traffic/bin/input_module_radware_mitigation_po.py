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
        helper.log_info(f"[VRM-MITIGATION-PO] Starting with primary: {primary_vrm_host}, secondary: {secondary_vrm_host}")
    else:
        helper.log_info(f"[VRM-MITIGATION-PO] Starting with primary: {primary_vrm_host} (no secondary configured)")

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
                helper.log_warning(f"[VRM-MITIGATION-PO] Primary VRM ({self.primary_host}) failed, switching to secondary ({self.secondary_host})")
                self.active_host = self.secondary_host
                self.primary_failed = True
                self.logged_in = False
                return True
            return False
        
        def switch_to_primary(self):
            """Switch back to primary VRM host if secondary fails"""
            if self.primary_failed and self.secondary_host:
                helper.log_warning(f"[VRM-MITIGATION-PO] Secondary VRM ({self.secondary_host}) failed, switching back to primary ({self.primary_host})")
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
                helper.log_info(f"[VRM-MITIGATION-PO] Login OK to {self.active_host}")
            except Exception as e:
                helper.log_error(f"[VRM-MITIGATION-PO] Login failed to {self.active_host}: {e}")
                # Try secondary if primary fails
                if self.switch_to_secondary():
                    url = f"{self.base_url}/mgmt/system/user/login"
                    r = self.session.post(url, json=payload, verify=False, timeout=10)
                    r.raise_for_status()
                    self.logged_in = True
                    self.last_login_time = time.time()
                    helper.log_info(f"[VRM-MITIGATION-PO] Login OK to {self.active_host} (secondary)")
                else:
                    raise
        
        def login_if_needed(self, force=False):
            current_time = time.time()
            time_since_login = current_time - self.last_login_time
            
            if force or not self.logged_in or time_since_login > 600:
                helper.log_info(f"[VRM-MITIGATION-PO] Re-authenticating to {self.active_host} (time since last login: {time_since_login:.0f}s)")
                try:
                    self.login()
                except Exception as e:
                    helper.log_error(f"[VRM-MITIGATION-PO] Re-authentication failed: {e}")
                    raise

        def logout(self):
            url = f"{self.base_url}/mgmt/system/user/logout"
            payload = {"username": self.username, "password": self.password}
            try:
                r = self.session.post(url, json=payload, verify=False, timeout=10)
                r.raise_for_status()
                helper.log_info(f"[VRM-MITIGATION-PO] Logout OK from {self.active_host}")
            except Exception as e:
                helper.log_warning(f"[VRM-MITIGATION-PO] Logout failed from {self.active_host}: {e}")

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
                        helper.log_warning(f"[VRM-MITIGATION-PO] Got {r.status_code}, re-authenticating...")
                        self.login()
                        continue  # Retry the request
                    
                    return r
                    
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                        helper.log_warning(f"[VRM-MITIGATION-PO] Request failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        raise
            
            raise Exception(f"Failed after {max_retries + 1} attempts")

        def get_protected_objects(self):
            """
            Get all protected objects from the API.
            Returns list of PO names.
            """
            url = f"{self.base_url}/cyber-controller/api/dfc/v1/protected-objects/search"
            payload = {"names": []}
            
            try:
                helper.log_info(f"[VRM-MITIGATION-PO] Calling PO API: {url}")
                r = self._make_request_with_retry('POST', url, json=payload, verify=False, timeout=10)
                helper.log_info(f"[VRM-MITIGATION-PO] PO API status code: {r.status_code}")
                
                if r.status_code != 200:
                    helper.log_error(f"[VRM-MITIGATION-PO] PO API returned status {r.status_code}: {r.text[:500]}")
                    return []
                
                data = r.json()
                helper.log_info(f"[VRM-MITIGATION-PO] PO API response length: {len(data)} objects")
                
                # Extract only the names from the response
                po_names = [po.get("name") for po in data if po.get("name")]
                helper.log_info(f"[VRM-MITIGATION-PO] Found {len(po_names)} protected objects: {po_names}")
                return po_names
            except Exception as e:
                helper.log_error(f"[VRM-MITIGATION-PO] Failed to get protected objects from {self.active_host}: {str(e)}")
                # Try secondary on failure
                if not self.primary_failed and self.switch_to_secondary():
                    try:
                        self.login()
                        url = f"{self.base_url}/cyber-controller/api/dfc/v1/protected-objects/search"
                        r = self._make_request_with_retry('POST', url, json=payload, verify=False, timeout=10)
                        if r.status_code == 200:
                            data = r.json()
                            po_names = [po.get("name") for po in data if po.get("name")]
                            helper.log_info(f"[VRM-MITIGATION-PO] Found {len(po_names)} protected objects from secondary: {po_names}")
                            return po_names
                    except Exception as e2:
                        helper.log_error(f"[VRM-MITIGATION-PO] Failed to get protected objects from secondary: {str(e2)}")
                return []

        def _build_mitigation_bandwidth_payload(self, lookback_minutes, protected_object_names):
            """
            Build payload for mitigation-bandwidth API (PO scope only)
            """
            now_ms = int(time.time() * 1000)
            from_ms = now_ms - lookback_minutes * 60 * 1000

            payload = {
                "defenseFlowScope": {
                    "protectedObjects": [],
                    "activationIds": []
                },
                "filterString": "",
                "protectedObjectNames": protected_object_names,
                "selectedDevices": [],  # Empty for PO traffic
                "timeInterval": {
                    "from": from_ms,
                    "to": None
                }
            }
            
            return payload

        def get_mitigation_bandwidth(self, po_name, lookback_minutes=5, unit="bps"):
            """
            Get mitigation bandwidth stats for a protected object.
            unit: "bps" or "pps" - determines which API endpoint to use
            """
            # Different endpoints for bps vs pps
            if unit == "pps":
                url = f"{self.base_url}/mgmt/vrm/analytics/attacks/mitigation/rate/periodic/report"
            else:
                url = f"{self.base_url}/cyber-controller/api/vrm/v1/attack/defensepro/mitigation-bandwidth"
            
            payload = self._build_mitigation_bandwidth_payload(lookback_minutes, [po_name])

            try:
                r = self._make_request_with_retry(
                    'POST', url, json=payload, verify=False, timeout=30
                )
                r.raise_for_status()
                return r.json()
            except Exception as e:
                helper.log_error(f"[VRM-MITIGATION-PO] Failed to get mitigation bandwidth from {self.active_host}: {e}")
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
        
        def get_all_po_mitigation_bandwidth(self, lookback_minutes=5):
            """
            Get mitigation bandwidth stats for all protected objects in both bps and pps.
            Note: PO queries have selectedDevices empty.
            """
            po_names = self.get_protected_objects()
            results = []
            
            if not po_names:
                helper.log_info("[VRM-MITIGATION-PO] No protected objects found, skipping PO mitigation-bandwidth collection")
                return results
            
            # For each PO, collect mitigation bandwidth (globally, not per device)
            for po_name in po_names:
                # Collect in bps
                try:
                    helper.log_info(f"[VRM-MITIGATION-PO] Querying PO mitigation-bandwidth (bps) for {po_name}...")
                    stats_bps = self.get_mitigation_bandwidth(po_name, lookback_minutes, unit="bps")
                    
                    # Log how many data points were returned
                    data_points = len(stats_bps.get("data", []))
                    helper.log_info(f"[VRM-MITIGATION-PO] PO {po_name} (bps): received {data_points} data points")
                    
                    if data_points > 0:
                        results.append(
                            {
                                "stats": stats_bps,
                                "po_name": po_name,
                                "unit": "bps",
                            }
                        )
                        helper.log_info(f"[VRM-MITIGATION-PO] ✓ Collected PO mitigation-bandwidth (bps) for {po_name}")
                    else:
                        helper.log_info(f"[VRM-MITIGATION-PO] ⚠ No mitigation-bandwidth data (bps) for PO {po_name}")
                        
                except Exception as e:
                    helper.log_error(f"[VRM-MITIGATION-PO] Failed PO mitigation-bandwidth (bps) for {po_name}: {e}")
                    import traceback
                    helper.log_error(f"[VRM-MITIGATION-PO] Traceback: {traceback.format_exc()}")
                
                # Collect in pps
                try:
                    helper.log_info(f"[VRM-MITIGATION-PO] Querying PO mitigation-bandwidth (pps) for {po_name}...")
                    stats_pps = self.get_mitigation_bandwidth(po_name, lookback_minutes, unit="pps")
                    
                    # Log how many data points were returned
                    data_points = len(stats_pps.get("data", []))
                    helper.log_info(f"[VRM-MITIGATION-PO] PO {po_name} (pps): received {data_points} data points")
                    
                    if data_points > 0:
                        results.append(
                            {
                                "stats": stats_pps,
                                "po_name": po_name,
                                "unit": "pps",
                            }
                        )
                        helper.log_info(f"[VRM-MITIGATION-PO] ✓ Collected PO mitigation-bandwidth (pps) for {po_name}")
                    else:
                        helper.log_info(f"[VRM-MITIGATION-PO] ⚠ No mitigation-bandwidth data (pps) for PO {po_name}")
                        
                except Exception as e:
                    helper.log_error(f"[VRM-MITIGATION-PO] Failed PO mitigation-bandwidth (pps) for {po_name}: {e}")
                    import traceback
                    helper.log_error(f"[VRM-MITIGATION-PO] Traceback: {traceback.format_exc()}")
            
            return results

    # ========= 3. Use the client and write events to Splunk =========
    client = VRMClient(primary_vrm_host, secondary_vrm_host, username, password)

    try:
        # login
        try:
            client.login()
        except Exception as e:
            helper.log_error(f"[VRM-MITIGATION-PO] Login failed: {e}")
            return

        # Collect protected object mitigation bandwidth
        helper.log_info("[VRM-MITIGATION-PO] Starting protected object mitigation-bandwidth collection")
        po_stats = client.get_all_po_mitigation_bandwidth(lookback_minutes)
        helper.log_info(f"[VRM-MITIGATION-PO] Collected {len(po_stats)} PO stat sets")

        event_count = 0

        for item in po_stats:
            stats = item["stats"]
            po_name = item["po_name"]
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
                    "scope": "protectedObject",
                    "unit": unit,  # bps or pps
                    "po_name": po_name,
                }

                # Create Splunk event
                event_obj = helper.new_event(
                    data=json.dumps(event_body),
                    index=index,
                    sourcetype="radware:mitigation:po",
                    source=f"radware_vrm_mitigation_bw://po/{po_name}",
                )
                ew.write_event(event_obj)
                event_count += 1

        helper.log_info(f"[VRM-MITIGATION-PO] Finished collection. Wrote {event_count} events.")

        # ========= 4. Logout =========
        try:
            client.logout()
        except Exception as e:
            helper.log_error(f"[VRM-MITIGATION-PO] Logout failed: {e}")
    finally:
        client.session.close()
