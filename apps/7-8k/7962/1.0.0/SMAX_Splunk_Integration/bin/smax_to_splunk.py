import requests
import json
import os
import logging
from datetime import datetime
from configparser import ConfigParser

# ---------------------- Logging Setup ---------------------- #
log_dir = os.path.join(os.environ.get("SPLUNK_HOME", "."), "var", "log", "splunk")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "smax_splunk_integration.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ---------------------- Config Reader ---------------------- #
def get_config():
    splunk_home = os.environ.get("SPLUNK_HOME")
    app_name = "SMAX_Splunk_Integration"

    if not splunk_home:
        logging.error("SPLUNK_HOME not set.")
        return None

    default_config = os.path.join(splunk_home, "etc", "apps", app_name, "default", "userinputs.conf")
    local_config = os.path.join(splunk_home, "etc", "apps", app_name, "local", "userinputs.conf")

    config = ConfigParser()
    files_read = config.read([default_config, local_config])
    logging.info(f"Read config files: {files_read}")

    if not files_read:
        logging.error("No config files found.")
        return None

    return config

def get_config_value(config, section, option):
    try:
        return config.get(section, option)
    except Exception as e:
        logging.error(f"Missing config [{section}] {option}: {e}")
        return None

# ---------------------- Fetch Configuration ---------------------- #
config = get_config()
if not config:
    exit()

SMAX_BASE_URL = get_config_value(config, "smax_settings", "SMAX_BASE_URL")
SMAX_USERNAME = get_config_value(config, "smax_settings", "SMAX_USERNAME")
SMAX_PASSWORD = get_config_value(config, "smax_settings", "SMAX_PASSWORD")
TENANT_ID     = get_config_value(config, "smax_settings", "TENANT_ID")
SPLUNK_HEC_URL = get_config_value(config, "splunk_settings", "SPLUNK_HEC_URL")
SPLUNK_HEC_TOKEN = get_config_value(config, "splunk_settings", "SPLUNK_HEC_TOKEN")

if not all([SMAX_BASE_URL, SMAX_USERNAME, SMAX_PASSWORD, TENANT_ID, SPLUNK_HEC_URL, SPLUNK_HEC_TOKEN]):
    logging.error("One or more configuration values are missing. Exiting.")
    exit()

# ---------------------- Splunk Header ---------------------- #
splunk_headers = {
    'Authorization': f'Splunk {SPLUNK_HEC_TOKEN}',
    'Content-Type': 'application/json'
}

# ---------------------- Authenticate with SMAX ---------------------- #
def get_smax_token():
    url = f"{SMAX_BASE_URL}/auth/authentication-endpoint/authenticate/login?TENANTID={TENANT_ID}"
    payload = json.dumps({
        "login": SMAX_USERNAME,
        "password": SMAX_PASSWORD
    })
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        token = response.text.strip('"')
        jsessionid = response.cookies.get('JSESSIONID')
        return token, jsessionid
    except Exception as e:
        logging.error(f"Failed to authenticate with SMAX: {e}")
        return None, None

# ---------------------- Send to Splunk ---------------------- #
def send_to_splunk(event_data, sourcetype):
    payload = {
        "event": event_data,
        "sourcetype": sourcetype,
        "source": "SMAX",
        "index": "smaxlogs",
        "time": datetime.utcnow().timestamp()
    }
    try:
        response = requests.post(SPLUNK_HEC_URL, headers=splunk_headers, data=json.dumps(payload))
        if response.status_code != 200:
            logging.error(f"Failed to send {sourcetype} to Splunk: {response.text}")
        else:
            logging.info(f"Sent {sourcetype} event to Splunk.")
    except Exception as e:
        logging.error(f"Exception while sending to Splunk: {e}")

# ---------------------- Fetch and Forward Data ---------------------- #
def fetch_and_send(resource_type, lw_token, jsessionid):
    url = f"{SMAX_BASE_URL}/rest/{TENANT_ID}/ems/{resource_type}?layout=FULL_LAYOUT"
    cookie_header = f'LWSSO_COOKIE_KEY={lw_token}; TENANTID={TENANT_ID}'
    if jsessionid:
        cookie_header += f'; JSESSIONID={jsessionid}'

    headers = {
        'Content-Type': 'application/json',
        'Cookie': cookie_header
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        items = response.json()
        if isinstance(items, dict):
            items = items.get("entities", []) or items.get("members", []) or []

        for item in items:
            send_to_splunk(json.dumps(item), f"smax:{resource_type.lower()}")

        logging.info(f"{resource_type} processed.")
    except Exception as e:
        logging.error(f"Failed to fetch {resource_type}: {e}")

# ---------------------- Main ---------------------- #
if __name__ == "__main__":
    lw_token, jsessionid = get_smax_token()
    if lw_token:
        fetch_and_send("Incident", lw_token, jsessionid)
        fetch_and_send("Request", lw_token, jsessionid)
