import requests
import sys
import os
import json
import gzip
import logging

# Add bin/ to path for shared helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splunk_helpers import get_session_key, get_session_key_from_payload, read_conf

LOG_FORMAT = "%(asctime)s %(levelname)s [diagnostics] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("diagnostics")

FALLBACK_URL = "https://data0001.avertpoint.com/splunk/essential/diagnostics"


def get_api_url(session_key=None):
    """Read the diagnostics API URL from avert.conf via REST, with fallback."""
    if session_key:
        try:
            conf = read_conf(session_key, 'avert', 'config')
            diag_url = conf.get('diagnostics', '').strip('"').rstrip('/%s')
            if diag_url:
                return diag_url
        except Exception:
            pass
    return FALLBACK_URL


def send_to_api(payload, session_key=None):
    url = get_api_url(session_key)
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info("Alert sent successfully: %s", response.status_code)
    except requests.RequestException as e:
        logger.error("Error sending alert to %s: %s", url, e)


def read_payload():
    raw_payload = sys.stdin.read()
    if not raw_payload:
        logger.warning("Empty payload received on stdin")
        return {}

    # Try plain JSON first
    try:
        return json.loads(raw_payload)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try gzip-compressed JSON
    try:
        decompressed = gzip.decompress(raw_payload.encode("latin-1"))
        return json.loads(decompressed)
    except Exception:
        pass

    logger.error("Failed to parse payload (%d bytes): %s", len(raw_payload), raw_payload[:200])
    return {}


def main():
    payload = read_payload()

    # For alert actions, session_key is in the payload (both Cloud and on-prem)
    session_key = get_session_key_from_payload(payload) if payload else ''
    if not session_key:
        session_key = get_session_key()

    if not payload:
        logger.warning("Sending empty payload -- check alert action configuration")
    send_to_api(payload, session_key)


if __name__ == "__main__":
    main()
