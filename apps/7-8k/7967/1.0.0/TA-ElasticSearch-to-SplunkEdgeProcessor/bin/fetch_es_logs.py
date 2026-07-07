
#!/usr/bin/env python3

#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta

# === Config from Splunk Modular Input (read from stdin or env vars) ===
# Splunk passes parameters as XML or environment variables in modular inputs.
# Here, we simulate reading from env vars for simplicity.

def get_env_param(param_name, default=None):
    return os.environ.get(param_name.upper(), default)

# Read parameters from environment variables
ELASTICSEARCH_URL = get_env_param("elasticsearch_url")
INDEX_PATTERN = get_env_param("index_pattern", "main*")
USERNAME = get_env_param("username")
PASSWORD = get_env_param("password")
ENVIRONMENT = get_env_param("environment")
HEC_URL = get_env_param("hec_url")
HEC_TOKEN = get_env_param("hec_token")
VERIFY_TLS = get_env_param("verify_tls", "true").lower() == "true"
CA_BUNDLE_PATH = get_env_param("ca_bundle_path")  # Optional path to CA cert bundle
PROXY = get_env_param("proxy")  # Optional proxy URL like "http://proxy:8080"
INTERVAL = int(get_env_param("interval", "60"))

FIELDS_TO_EXTRACT = [
#    "@timestamp", --> You can define the fields if you are specfic from the raw logs
#    "service.name",
#    "service.environment",
#    "level",
#    "message",
#    "log_data",
]

SCROLL_TIMEOUT = "2m"
BATCH_SIZE = 10000

TIMESTAMP_FILE = os.path.expandvars(
    f"$SPLUNK_HOME/var/lib/splunk/fetch_es_logs_{ENVIRONMENT}_last_ts.txt"
)

PROXIES = {"http": PROXY, "https": PROXY} if PROXY else None

# === Helper Functions ===

def load_last_timestamp():
    if os.path.exists(TIMESTAMP_FILE):
        with open(TIMESTAMP_FILE, "r") as f:
            ts = f.read().strip()
            if ts:
                return ts
    # Default: last 1 minute from now (ISO8601)
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=1)
    return start_time.isoformat() + "Z"

def save_last_timestamp(ts):
    with open(TIMESTAMP_FILE, "w") as f:
        f.write(ts)

def build_query(start_time, end_time):
    return {
        "size": BATCH_SIZE,
        "sort": [
            {"@timestamp": {"order": "asc"}},
            {"_doc": {"order": "asc"}}
        ],
        "query": {
            "bool": {
                "must": [
                    #{"match": {"kubernetes.container.name": "APILogs"}} --> If you want specific index or cluster please change it,
                    #{"match": {"service.environment": ENVIRONMENT}},
                    {
                        "range": {
                            "@timestamp": {
                                "gte": start_time,
                                "lte": end_time
                            }
                        }
                    }
                ]
            }
        }
    }

def extract_required_fields(source):
    extracted = {}
    for field in FIELDS_TO_EXTRACT:
        parts = field.split('.')
        value = source
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = None
                break
        if value is not None:
            extracted[field] = value
    return extracted

def send_to_hec(events):
    headers = {
        "Authorization": f"Splunk {HEC_TOKEN}",
        "Content-Type": "application/json"
    }
    for attempt in range(3):
        try:
            response = requests.post(
                HEC_URL,
                headers=headers,
                data="\n".join(events),
                verify=CA_BUNDLE_PATH if CA_BUNDLE_PATH else VERIFY_TLS,
                proxies=PROXIES,
                timeout=30
            )
            if response.status_code in (200, 201, 202):
                return True
            else:
                print(f"HEC post failed: HTTP {response.status_code} - {response.text}", file=sys.stderr)
        except Exception as e:
            print(f"HEC post exception: {e}", file=sys.stderr)
        time.sleep(5)
    return False

# === Main Fetch Loop ===

def fetch_logs():
    last_ts = load_last_timestamp()
    now = datetime.utcnow().isoformat() + "Z"
    query = build_query(last_ts, now)

    try:
        response = requests.post(
            f"{ELASTICSEARCH_URL}/{INDEX_PATTERN}/_search?scroll={SCROLL_TIMEOUT}",
            headers={"Content-Type": "application/json"},
            auth=(USERNAME, PASSWORD),
            data=json.dumps(query),
            verify=CA_BUNDLE_PATH if CA_BUNDLE_PATH else VERIFY_TLS,
            proxies=PROXIES,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        print(f"Failed initial ES search: {e}", file=sys.stderr)
        return

    scroll_id = result.get("_scroll_id")
    hits = result.get("hits", {}).get("hits", [])
    all_logs = hits.copy()

    while hits:
        try:
            response = requests.post(
                f"{ELASTICSEARCH_URL}/_search/scroll",
                headers={"Content-Type": "application/json"},
                auth=(USERNAME, PASSWORD),
                data=json.dumps({"scroll": SCROLL_TIMEOUT, "scroll_id": scroll_id}),
                verify=CA_BUNDLE_PATH if CA_BUNDLE_PATH else VERIFY_TLS,
                proxies=PROXIES,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"Failed ES scroll: {e}", file=sys.stderr)
            break

        scroll_id = result.get("_scroll_id")
        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            break
        all_logs.extend(hits)

    # Clean scroll context
    if scroll_id:
        try:
            requests.delete(
                f"{ELASTICSEARCH_URL}/_search/scroll",
                headers={"Content-Type": "application/json"},
                auth=(USERNAME, PASSWORD),
                data=json.dumps({"scroll_id": [scroll_id]}),
                verify=CA_BUNDLE_PATH if CA_BUNDLE_PATH else VERIFY_TLS,
                proxies=PROXIES,
                timeout=10
            )
        except Exception as e:
            print(f"Warning: scroll cleanup failed: {e}", file=sys.stderr)

    if not all_logs:
        print("No new logs found.")
        return

    # Prepare events for HEC
    events = []
    max_ts = last_ts
    for log in all_logs:
        source = log.get("_source", {})
        extracted = extract_required_fields(source)
        # Construct Splunk event payload
        event = {
            "time": datetime.strptime(extracted.get("@timestamp"), "%Y-%m-%dT%H:%M:%S.%fZ").timestamp() if extracted.get("@timestamp") else time.time(),
            "host": extracted.get("service.name", "unknown"),
            "source": "elasticsearch",
            "sourcetype": "json",
            "event": extracted
        }
        events.append(json.dumps(event))
        # Update max_ts
        if extracted.get("@timestamp") and extracted["@timestamp"] > max_ts:
            max_ts = extracted["@timestamp"]

    # Send to HEC with retry
    if send_to_hec(events):
        save_last_timestamp(max_ts)
        print(f"Successfully sent {len(events)} events to HEC. Updated timestamp to {max_ts}")
    else:
        print("Failed to send events to HEC after retries.", file=sys.stderr)

def main():
    # This script should be called by Splunk modular input scheduler
    fetch_logs()

if __name__ == "__main__":
    main()
