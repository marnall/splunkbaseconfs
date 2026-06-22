#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import json
import time
import traceback
import os
from typing import Optional
from datetime import datetime
from urllib.parse import urlencode
import splunklib.modularinput as mi
from types import SimpleNamespace
from splunklib.modularinput import Scheme, Argument, Event, EventWriter

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _HAS_URLLIB3 = True
except Exception:
    urllib3 = None
    _HAS_URLLIB3 = False

THREATMON_PAGE_SIZE = 10

class ThreatmonInput(mi.Script): 
    def get_scheme(self):
        scheme = Scheme("threatmon_incidents")
        scheme.description = "Pull Threatmon incidents into Splunk"
        scheme.use_external_validation = True
        scheme.use_single_instance = False  # Bu satırı ekledim

        scheme.add_argument(Argument("api_url", title="API Base URL", required_on_create=True))
        scheme.add_argument(Argument("api_key", title="API Key", required_on_create=True))
        
        return scheme

    def validate_input(self, definition):
        api_url = definition.parameters.get("api_url")
        api_key = definition.parameters.get("api_key")

        if not api_url or not api_url.startswith("http"):
            raise ValueError("api_url must start with http or https")
        if not api_key or api_key.strip() == "":
            raise ValueError("api_key is required")

    def stream_events(self, inputs, ew: EventWriter):
        ew.log(EventWriter.INFO, f"=== STREAM_EVENTS CALLED ===")
        ew.log(EventWriter.INFO, f"Number of inputs: {len(inputs.inputs)}")
        ew.log(EventWriter.INFO, f"Input names: {list(inputs.inputs.keys())}")
        
        if not inputs.inputs:
            ew.log(EventWriter.WARNING, "No inputs found! Check your inputs.conf configuration")
            return
        
        for input_name, input_item in inputs.inputs.items():
            ew.log(EventWriter.INFO, f"Processing input: {input_name}")
            
            # Parametreleri düzgün şekilde al
            params = input_item
            
            api_url = params.get("api_url")
            api_key = params.get("api_key")
            index = params.get("index", "main")
            sourcetype = params.get("sourcetype", "threatmon:incident")

            # Validasyon
            if not api_url:
                ew.log(EventWriter.ERROR, f"API URL is missing! Available parameters: {list(params.keys())}")
                continue
                
            if not api_key or api_key == "$encrypted$":
                ew.log(EventWriter.ERROR, f"API key is missing or encrypted! Please provide actual API key")
                continue
            
            # API key'i log'da gizle
            masked_api_key = api_key[:8] + "***" if api_key and len(api_key) > 8 else "***"
            ew.log(EventWriter.INFO, f"Configuration - API URL: {api_url}, Index: {index}, Sourcetype: {sourcetype}, API Key: {masked_api_key}")

            # Checkpoint sistemi - basitleştirilmiş
            checkpoint_key = f"threatmon_incidents_{input_name}_last_id"
            last_incident_id = self._get_checkpoint(checkpoint_key)
            last_incident_id_int: Optional[int] = int(last_incident_id) if last_incident_id and last_incident_id.isdigit() else None
            
            ew.log(EventWriter.INFO, f"Checkpoint loaded - Last incident ID: {last_incident_id_int}")

            headers = {"X-COMPANY-API-KEY": api_key, "accept": "application/json"}

            page = 0
            total_events = 0
            start_time = time.time()

            try:
                ew.log(EventWriter.INFO, "Starting to fetch data from Threatmon API")
                
                while True:
                    url = f"{api_url}/vulnerabilities/{page}"
                    if last_incident_id_int:
                        q = urlencode({"afterAlarmCode": last_incident_id_int})
                        url = f"{url}?{q}"

                    ew.log(EventWriter.DEBUG, f"Making API request to: {url}")
                    
                    try:
                        resp = self._http_get(url, headers=headers, timeout=30)
                        ew.log(EventWriter.DEBUG, f"API Response - Status: {resp.status}")
                    except Exception as req_error:
                        ew.log(EventWriter.ERROR, f"Request failed: {req_error}")
                        break
                    
                    if resp.status != 200:
                        error_msg = f"API Error {resp.status}: {resp.data.decode('utf-8', 'ignore') if resp.data else 'No response body'}"
                        ew.log(EventWriter.ERROR, error_msg)
                        break  # API hatası durumunda devam etmeyi dene

                    try:
                        data = json.loads(resp.data.decode("utf-8"))
                        ew.log(EventWriter.DEBUG, f"JSON parsed successfully")
                    except json.JSONDecodeError as e:
                        ew.log(EventWriter.ERROR, f"Failed to parse JSON response: {e}")
                        break

                    alerts = data.get("data", [])
                    total_records = data.get("totalRecords", 0)
                    
                    ew.log(EventWriter.INFO, f"Page {page} - Retrieved {len(alerts)} alerts, Total records available: {total_records}")
                    
                    if not alerts:
                        ew.log(EventWriter.INFO, f"No more alerts found on page {page}, stopping pagination")
                        break

                    processed_on_page = 0
                    for alert in alerts:
                        incident_id = alert.get("alarmCode")
                        title = alert.get("title", "Unknown Threat")
                        severity = alert.get("severity", "Low")
                        status = alert.get("status", "New")
                        alarm_date = alert.get("alarmDate") or datetime.utcnow().isoformat()

                        ew.log(EventWriter.DEBUG, f"Processing alert - ID: {incident_id}, Title: {title[:50] if title else 'N/A'}..., Severity: {severity}, Status: {status}")

                        try:
                            event = Event(
                                data=json.dumps(alert),
                                time=self._to_epoch(alarm_date),
                                index=index,
                                sourcetype=sourcetype,
                                source="threatmon_api"
                            )
                            ew.write_event(event)
                            total_events += 1
                            processed_on_page += 1
                            
                            ew.log(EventWriter.DEBUG, f"Event written successfully for incident {incident_id}")

                            # Update checkpoint
                            if isinstance(incident_id, int):
                                if (last_incident_id_int is None) or (incident_id > last_incident_id_int):
                                    old_id = last_incident_id_int
                                    last_incident_id_int = incident_id
                                    ew.log(EventWriter.DEBUG, f"Checkpoint updated from {old_id} to {last_incident_id_int}")
                                    
                        except Exception as event_error:
                            ew.log(EventWriter.ERROR, f"Failed to process alert {incident_id}: {event_error}")
                            continue

                    ew.log(EventWriter.INFO, f"Page {page} completed - Processed {processed_on_page} events successfully")

                    # Pagination break conditions
                    if len(alerts) < THREATMON_PAGE_SIZE:
                        ew.log(EventWriter.INFO, f"Retrieved fewer alerts than page size ({len(alerts)} < {THREATMON_PAGE_SIZE}), reached end of data")
                        break
                        
                    if total_records and total_events >= total_records:
                        ew.log(EventWriter.INFO, f"Retrieved all available records ({total_events} >= {total_records})")
                        break

                    page += 1
                    ew.log(EventWriter.DEBUG, f"Moving to next page: {page}")
                    time.sleep(1)  # Rate limiting

                elapsed_time = time.time() - start_time
                ew.log(EventWriter.INFO, f"Data fetching completed - Total time: {elapsed_time:.2f}s, Total events: {total_events}")

            except Exception as e:
                error_msg = f"Threatmon input failure: {e}"
                ew.log(EventWriter.ERROR, f"{error_msg}\n{traceback.format_exc()}")
                
            finally:
                # Save checkpoint
                if last_incident_id_int is not None:
                    try:
                        self._save_checkpoint(checkpoint_key, str(last_incident_id_int))
                        ew.log(EventWriter.INFO, f"Checkpoint saved successfully: {last_incident_id_int}")
                    except Exception as ckpt_error:
                        ew.log(EventWriter.ERROR, f"Failed to save checkpoint: {ckpt_error}")
                
                final_msg = f"Threatmon input completed - Input: {input_name}, Indexed: {total_events}, Last incident ID: {last_incident_id_int}"
                ew.log(EventWriter.INFO, final_msg)

        ew.log(EventWriter.INFO, "All Threatmon inputs processed")

    # --- helpers ---
    def _get_checkpoint(self, key: str) -> Optional[str]:
        """Get checkpoint value from file system"""
        return self._read_ckpt_file(key)

    def _save_checkpoint(self, key: str, value: str) -> None:
        """Save checkpoint to file system - basitleştirilmiş versiyon"""
        try:
            # Splunk'un varsayılan checkpoint dizinini kullan
            splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
            ckptdir = os.path.join(splunk_home, "var", "lib", "splunk", "modinputs", "threatmon_incidents")
            
            os.makedirs(ckptdir, exist_ok=True)
            
            # Dosya adını güvenli hale getir
            safe_key = key.replace("::", "_").replace("/", "_").replace("\\", "_")
            checkpoint_file = os.path.join(ckptdir, f"{safe_key}.ckpt")
            
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                f.write(value)
                
        except Exception as e:
            # Log the error but don't fail the entire process
            print(f"Warning: Failed to save checkpoint {key}: {e}", file=sys.stderr)

    def _read_ckpt_file(self, key: str) -> Optional[str]:
        """Read checkpoint from file system - basitleştirilmiş versiyon"""
        try:
            splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
            ckptdir = os.path.join(splunk_home, "var", "lib", "splunk", "modinputs", "threatmon_incidents")
            
            # Dosya adını güvenli hale getir
            safe_key = key.replace("::", "_").replace("/", "_").replace("\\", "_")
            checkpoint_file = os.path.join(ckptdir, f"{safe_key}.ckpt")
            
            if os.path.exists(checkpoint_file):
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return content if content else None
        except Exception as e:
            print(f"Warning: Failed to read checkpoint {key}: {e}", file=sys.stderr)
            return None
        return None

    def _http_get(self, url: str, headers: dict, timeout: int):
        """HTTP GET with urllib3 if available, otherwise stdlib urllib.request."""
        if _HAS_URLLIB3:
            http = urllib3.PoolManager()
            return http.request("GET", url, headers=headers, timeout=timeout)

        import urllib.request

        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return SimpleNamespace(status=resp.status, data=resp.read())

    @staticmethod
    def _to_epoch(iso_dt: str) -> float:
        """Convert ISO datetime string to epoch timestamp"""
        try:
            # Handle various ISO formats
            iso_dt = iso_dt.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_dt)
            return dt.timestamp()
        except Exception:
            # Fallback to current time
            return time.time()

if __name__ == "__main__":
    sys.exit(ThreatmonInput().run(sys.argv))
