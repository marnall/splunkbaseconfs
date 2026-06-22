"""Scripted input that emits an expiry-warning event.

Runs on a schedule (see `default/inputs.conf`). Reads the encrypted
license blob from storage/passwords, computes `expires_in_days`, and
emits a single JSON event when the value is <= 30. The saved-search
alert created by the License tab fires on those events.

Output (stdout) is a single JSON object, picked up by Splunk's
scripted-input pipeline with sourcetype `itmip_llm_license`.
"""

import json
import os
import sys
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.rest as rest  # type: ignore  # noqa: E402

from itmip_llm_common import APP_NAME, LLM_PASSWORD_REALM  # noqa: E402
from itmip_llm_guid import get_environment_guid  # noqa: E402
from itmip_llm_license_tier import resolve_tier  # noqa: E402


SECRET_NAME = "license_blob"
WARNING_THRESHOLD_DAYS = 30


def _splunkd_session_key():
    """Splunk scripted inputs receive the session key on stdin as the
    first line. The rest of stdin is unused.
    """
    return sys.stdin.readline().strip() if not sys.stdin.isatty() else ""


def _load_blob(session_key):
    path = (
        "/servicesNS/nobody/{app}/storage/passwords/"
        "{realm}%3A{name}%3A?output_mode=json"
    ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=SECRET_NAME)
    try:
        resp, content = rest.simpleRequest(
            path, sessionKey=session_key, method="GET"
        )
    except Exception:
        return None
    if getattr(resp, "status", 0) != 200:
        return None
    try:
        data = json.loads(content)
        entries = data.get("entry") or []
        if not entries:
            return None
        raw = (entries[0].get("content") or {}).get("clear_password") or ""
        return json.loads(raw) if raw else None
    except Exception:
        return None


def main():
    session_key = _splunkd_session_key()
    blob = _load_blob(session_key) if session_key else None
    if not blob:
        # No license stored — nothing to warn about. Quietly emit
        # nothing rather than a noisy "no license" event every 6h.
        return

    guid = get_environment_guid(session_key) if session_key else {"guid": "UNKNOWN"}
    tier_state = resolve_tier(
        blob.get("licenseKey") or {}, current_guid=guid["guid"]
    )

    if not tier_state.get("is_time_limited"):
        return  # Indefinite license — no expiry to warn on.
    expires_in_days = tier_state.get("expires_in_days")
    if expires_in_days is None:
        return
    if expires_in_days > WARNING_THRESHOLD_DAYS:
        return  # Plenty of runway.

    event = {
        "_time": int(time.time()),
        "expiring_in_days": int(expires_in_days),
        "tier": tier_state["tier"],
        "effective_tier": tier_state["effective_tier"],
        "badge": tier_state["badge"],
        "expires_at": tier_state["expires_at"],
        "key": tier_state["key"],
        "customer_name": tier_state.get("customer_name"),
        "guid": guid.get("guid"),
        "is_expired": tier_state["is_expired"],
    }
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
