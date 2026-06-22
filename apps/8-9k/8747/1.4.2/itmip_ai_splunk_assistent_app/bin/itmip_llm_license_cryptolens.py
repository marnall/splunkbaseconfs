"""Cryptolens API client.

This module talks to https://api.cryptolens.io for the AI User
Assistent for Splunk product (ProductId 32681). Two operations:

  - `activate(key, machine_code)` — first-time activation of a license
    key for the current Splunk environment.
  - `validate(key, machine_code)` — re-issues the same call to confirm
    the license is still live (e.g. before lifting a feature gate).

The Cryptolens **access token** is the product's API key and is
embedded in code. It is NOT the customer's license key. Cryptolens
designs this token to be safe to ship with the app — every call is
scoped to ProductId 32681, and the token alone cannot mint new
licenses (Cryptolens admin actions require a different, kept-private
key).

Customers activate via the browser (see `LicensePage.tsx`) when the
Splunk Search Head is air-gapped; the server-side activate() path
exists for installs where the SH does have internet egress.
"""

import json
import urllib.parse
import urllib.request


# Public product API token. Shipping this in code is intended.
CRYPTOLENS_ACCESS_TOKEN = (
    "WyIxMjAxODgyODQiLCIwbGwyM2sweEVFM2RnN0kyTXRTQ1Bza3BOdmM3MXA1YVp4Z0hheVVWIl0="
)
CRYPTOLENS_PRODUCT_ID = "32681"
CRYPTOLENS_BASE = "https://api.cryptolens.io/api/key"
DEFAULT_TIMEOUT_SEC = 20


def activate(key, machine_code, timeout=DEFAULT_TIMEOUT_SEC):
    """Call Cryptolens /Activate.

    Returns the parsed JSON dict on success (which has a `result` key —
    0 = success, 1 = error — and a `licenseKey` object). Raises on
    network failure or non-2xx.
    """
    if not key or not isinstance(key, str):
        raise ValueError("key is required")
    if not machine_code or not isinstance(machine_code, str):
        raise ValueError("machine_code is required")

    params = {
        "token": CRYPTOLENS_ACCESS_TOKEN,
        "ProductId": CRYPTOLENS_PRODUCT_ID,
        "Key": key.strip(),
        "MachineCode": machine_code.strip(),
    }
    url = CRYPTOLENS_BASE + "/Activate?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    try:
        return json.loads(body)
    except Exception as exc:
        raise RuntimeError("Cryptolens returned non-JSON: %s" % exc)


def validate(key, machine_code, timeout=DEFAULT_TIMEOUT_SEC):
    """Re-issue an Activate call to confirm the license is still live.

    Cryptolens has no separate `Validate` endpoint — re-activating is
    idempotent and is the documented way to verify a key. Returns the
    same parsed JSON dict shape as `activate`.
    """
    return activate(key, machine_code, timeout=timeout)
