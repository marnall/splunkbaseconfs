"""
Offline license-key verification for the Inno Streaming Add-on for AWS S3.

The vendor signs a license payload with a PRIVATE key (see tools/mint_license.py);
this add-on ships only the PUBLIC key (license_pubkey.pem) and verifies the key
offline -- no network. Verification uses pure-Python RSA (the `rsa` package), so
there is no compiled binary and the add-on still passes Splunk Cloud AppInspect.

License key string format:  <b64url(payload_json)>.<b64url(signature)>
  payload_json = {"product","customer","edition","expiry":"YYYY-MM-DD","features":[],"issued"}
  signature    = RSA SHA-256 signature over the exact payload_json bytes

SECURITY NOTE (documented for honesty): because the add-on source is readable
(required by Splunk Cloud), the signed key stops forging/sharing of keys and gives
the EULA legal teeth, but a determined user could patch out the check. Tamper-proof
enforcement would require a server-side backend, which this add-on does not use.
"""

import base64
import datetime
import json
import os
import sys

# make bundled libs (rsa, pyasn1) importable when run standalone
_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import rsa  # noqa: E402

PRODUCT = "TA_s3_lambda_deployer"
_PUBKEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "license_pubkey.pem")


def _b64url_decode(s):
    s = s.encode() if isinstance(s, str) else s
    return base64.urlsafe_b64decode(s + b"=" * (-len(s) % 4))


def b64url_encode(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _normalize_accounts(aws_account):
    """None / 'a,b' / ['a','b'] -> sorted unique list of non-empty strings."""
    if not aws_account:
        return []
    items = aws_account.split(",") if isinstance(aws_account, str) else list(aws_account)
    return sorted({str(a).strip() for a in items if str(a).strip()})


def account_allowed(aws_account_list, account_id):
    """True if account_id is licensed (empty list = unrestricted)."""
    accounts = _normalize_accounts(aws_account_list)
    return (not accounts) or (str(account_id).strip() in accounts)


DEFAULT_GRACE_DAYS = 3
# states that warrant an email; ordered by urgency
NOTIFY_STATES = ("d30", "d14", "d7", "d3", "d1", "grace", "stopped", "invalid")
DAILY_STATES = ("grace", "stopped")  # re-notify every day until resolved


def subscription_state(status, today=None):
    """Map a verify_license() result to a subscription state + days-to-expiry.

    Returns (state, days_remaining). Honors grace_days for the expired window.
      active                  — valid, >30 days left (or perpetual: days=None)
      d30/d14/d7/d3/d1        — valid, expiring within N days
      grace                   — expiry passed but within grace_days (still ingesting)
      stopped                 — past expiry + grace (Lambda stops ingesting)
      invalid                 — bad signature/product/account/format (not an expiry issue)
    """
    today = today or datetime.date.today()
    reason = (status.get("reason") or "").lower()
    if not status.get("valid") and "expired" not in reason:
        return "invalid", status.get("days_remaining")
    expiry = status.get("expiry")
    if not expiry:
        return "active", None  # perpetual
    try:
        exp = datetime.date.fromisoformat(expiry)
    except Exception:
        return "invalid", None
    dr = (exp - today).days
    if dr < 0:
        grace = status.get("grace_days")
        grace = DEFAULT_GRACE_DAYS if grace is None else int(grace)
        if today <= exp + datetime.timedelta(days=grace):
            return "grace", dr
        return "stopped", dr
    for thr, label in ((1, "d1"), (3, "d3"), (7, "d7"), (14, "d14"), (30, "d30")):
        if dr <= thr:
            return label, dr
    return "active", dr


def should_notify(state, last_state, last_date, today=None):
    """De-dupe: notify on entering a notify-state, or daily while grace/stopped."""
    today = (today or datetime.date.today()).isoformat()
    if state not in NOTIFY_STATES:
        return False
    if state != last_state:
        return True
    if state in DAILY_STATES and last_date != today:
        return True
    return False


def _load_pubkey():
    with open(_PUBKEY_PATH, "rb") as f:
        return rsa.PublicKey.load_pkcs1(f.read())


def verify_license(key_str):
    """Return a status dict; never raises.

    {valid: bool, customer, expiry, edition, features: [...], reason: str}
    """
    result = {
        "valid": False,
        "customer": None,
        "expiry": None,
        "edition": None,
        "features": [],
        "aws_account": [],
        "grace_days": None,
        "provisional": False,
        "days_remaining": None,
        "reason": "",
    }

    if not key_str or not str(key_str).strip():
        # FREE EDITION (v1.0.2+): this add-on is distributed free of charge, so a
        # missing/empty key is NOT an error -- it is treated as a valid, perpetual,
        # unrestricted (no node-lock, no expiry) license. This makes the deploy gate,
        # node-lock check, license_status action and the monitor all pass with no key.
        # The signed-key verification below is RETAINED (not deleted): if a customer
        # ever enters a real key it still verifies/enforces normally, so re-enabling
        # paid licensing later is a one-line revert of this branch.
        result["valid"] = True
        result["edition"] = "free"
        result["reason"] = "ok (free edition -- no license key required)"
        return result

    try:
        b64_payload, b64_sig = str(key_str).strip().split(".", 1)
        payload_bytes = _b64url_decode(b64_payload)
        signature = _b64url_decode(b64_sig)
    except Exception:
        result["reason"] = "Malformed license key."
        return result

    try:
        rsa.verify(payload_bytes, signature, _load_pubkey())
    except Exception:
        result["reason"] = "License signature is invalid (key was altered or issued by an unknown source)."
        return result

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        result["reason"] = "License payload is not readable."
        return result

    if payload.get("product") != PRODUCT:
        result["reason"] = "License is for a different product."
        return result

    result["customer"] = payload.get("customer")
    result["expiry"] = payload.get("expiry")
    result["edition"] = payload.get("edition")
    result["features"] = payload.get("features") or []
    result["aws_account"] = _normalize_accounts(payload.get("aws_account"))
    result["grace_days"] = payload.get("grace_days")
    # Refund-window (provisional) key: issued at purchase, expires with the money-back
    # window; the vendor sends the full-term key once the window closes. Surfaced so the
    # UI can explain the short expiry instead of alarming the customer.
    result["provisional"] = bool(payload.get("provisional"))

    expiry = payload.get("expiry")
    if expiry:
        try:
            expiry_date = datetime.date.fromisoformat(expiry)
        except Exception:
            result["reason"] = "License expiry date is invalid."
            return result
        result["days_remaining"] = (expiry_date - datetime.date.today()).days
        if datetime.date.today() > expiry_date:
            result["reason"] = f"License expired on {expiry}."
            return result

    result["valid"] = True
    result["reason"] = "ok"
    return result
