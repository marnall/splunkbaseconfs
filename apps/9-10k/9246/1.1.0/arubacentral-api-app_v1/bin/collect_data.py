import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from splunk_secret_helper import get_secret
from generate_token import refresh_access_token

APP_CONF = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "etc", "apps", "arubacentral-api-app_v1", "local", "arubacentral_settings.json"
)

def read_session_key():
    data = sys.stdin.read().strip()
    if not data:
        return None
    return data.splitlines()[0].strip()

def load_settings():
    with open(APP_CONF, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def token_expired(session_key, skew=300):
    token = get_secret(session_key, "access_token")
    expires_at = get_secret(session_key, "expires_at")
    if not token or not expires_at:
        return True
    return datetime.now(timezone.utc) >= (parse_iso(expires_at) - timedelta(seconds=skew))

def main():
    session_key = read_session_key()
    if not session_key:
        raise RuntimeError("No session key received")

    settings = load_settings()

    if token_expired(session_key):
        refresh_access_token(session_key)

    access_token = get_secret(session_key, "access_token")

    r = requests.get(
        f"{settings['base_url']}/network-monitoring/v1/aps",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        verify=True,
        timeout=60
    )

    if r.status_code == 401:
        refresh_access_token(session_key)
        access_token = get_secret(session_key, "access_token")
        r = requests.get(
            f"{settings['aruba_base_url']}/network-monitoring/v1/aps",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            verify=settings.get("verify_tls", True),
            timeout=60
        )

    r.raise_for_status()
    now = datetime.now(timezone.utc).isoformat()
    payload = r.json()

    event = {
        "event_time": now,
        "input": "oauth_api_collector",
        "endpoint": settings["data_endpoint"],
        "data": payload
    }
    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()

if __name__ == "__main__":
    main()