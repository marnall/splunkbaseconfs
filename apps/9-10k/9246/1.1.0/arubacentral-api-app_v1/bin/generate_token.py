import os
import json
import requests
from datetime import datetime, timedelta, timezone
from splunk_secret_helper import get_secret, set_secret

APP_CONF = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "etc", "apps", "arubacentral-api-app_v1", "local", "arubacentral_settings.json"
)

def load_settings():
    with open(APP_CONF, "r", encoding="utf-8") as f:
        return json.load(f)

def refresh_access_token(session_key):
    settings = load_settings()
    client_id = get_secret(session_key, "client_id")
    client_secret = get_secret(session_key, "client_secret")

    r = requests.post(
        f"{settings['hpe_base_url']}{settings['token_url']}",
        headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        },
        verify=True,
        timeout=30
    )
    r.raise_for_status()
    payload = r.json()

    access_token = payload["access_token"]
    expires_in = int(payload.get("expires_in", 7200))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    set_secret(session_key, "access_token", access_token)
    set_secret(session_key, "expires_at", expires_at.isoformat())

    return {"access_token": access_token, "expires_at": expires_at.isoformat()}