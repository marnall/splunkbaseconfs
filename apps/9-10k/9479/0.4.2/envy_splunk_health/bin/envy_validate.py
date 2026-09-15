#!/usr/bin/env python
"""envyvalidate -- Envy Splunk Health license validation (outbound-only).

Streaming search command. Reads `envy_license_key` from each input row, POSTs it
to the Envyously license server over HTTPS, and adds valid/tier/expires/features
to the row.

Connectivity model (the whole point): this is an OUTBOUND 443 call to a
Cloudflare-fronted endpoint. The customer opens NO inbound firewall port and
changes nothing on their perimeter -- outbound HTTPS to a single hostname is all
it needs, and only the license key is sent (never customer data). Egress-locked
sites allow one hostname. Fully air-gapped sites use the ENVY-OFFLINE path (a
signed offline key handled server-side) or stay on the free tier.

Fails CLOSED: any error, timeout, non-200, or unreachable server resolves to
free tier (valid="false") rather than silently granting premium. The
`envy_licensed` gate macro then zeroes premium detections until the next
successful validation.

Wired into the "Envyously - License check" saved search (savedsearches.conf),
which pipes the single key row through `| envyvalidate` and outputlookups the
result to envy_license_state.csv.
"""
import json
import sys
import urllib.request

import splunk.Intersplunk as si

# Default endpoint is Cloudflare-fronted; override per-environment with
#   | envyvalidate url="https://..."
# (e.g. a customer's own Cloudflare Tunnel hostname, or api.envyously.com once
# the vanity alias is live). Kept as an option so no code change is needed.
DEFAULT_URL = "https://app.envyously.com/api/envy-license/validate"
# Must match this app's id in default/app.conf. It is sent to the license server as the
# scope for the key, so a wrong value validates against the wrong product and a correctly
# licensed customer silently resolves to free tier.
APP = "envy_splunk_health"
TIMEOUT = 8

_FREE = {"valid": "false", "tier": "free", "expires": "", "features": "dashboards"}


def _validate(key, url):
    key = (key or "").strip()
    if key == "" or key.upper() == "ENVY-FREE":
        return dict(_FREE)
    body = json.dumps({"key": key, "app": APP}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8") or "{}")
    except Exception:
        return dict(_FREE)   # fail closed
    feats = data.get("features") or []
    if isinstance(feats, list):
        feats = ",".join(str(f) for f in feats)
    is_valid = bool(data.get("valid"))
    return {
        "valid": "true" if is_valid else "false",
        "tier": str(data.get("tier") or ("premium" if is_valid else "free")),
        "expires": str(data.get("expires") or ""),
        "features": str(feats or ("" if is_valid else "dashboards")),
    }


def main():
    url = DEFAULT_URL
    for arg in sys.argv[1:]:
        if arg.startswith("url="):
            url = arg.split("=", 1)[1].strip().strip('"').strip("'")
    results, _dummy, _settings = si.getOrganizedResults()
    if not results:
        results = [{}]
    for row in results:
        row.update(_validate(row.get("envy_license_key", ""), url))
    si.outputResults(results)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        si.generateErrorResults(str(exc))
