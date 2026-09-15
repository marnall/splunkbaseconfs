#!/usr/bin/env python
"""envyofflineverify -- offline license verification (NO network).

For Splunk Cloud and air-gapped on-prem, where a custom command cannot phone
home. Reads envy_license_key from each row; if it's a signed offline token
(contains a "."), verifies the RSA-2048 / PKCS#1 v1.5 / SHA-256 signature
LOCALLY against the public key embedded below, checks expiry, and emits
valid/tier/expires/features. Uses only the Python standard library (base64,
json, hashlib, time) -- no `cryptography`, no `requests`, no outbound socket --
so it passes Splunk Cloud AppInspect vetting.

The app ships only the PUBLIC key, so possessing the app does not let anyone
mint a token. Tokens are time-boxed (default 45 days); "revocation" is expiry +
non-reissue. A blank key or ENVY-FREE resolves to the free tier with no work.

Wired into the "Envyously - License check (offline)" saved search, which pipes
the configured key/token through `| envyofflineverify` and outputlookups
valid/tier/expires/features to envy_license_state.csv (read by `envy_licensed`).
"""
import base64
import hashlib
import json
import time

import splunk.Intersplunk as si

# Envyously license public key (RSA-2048). Private counterpart lives only on the
# Envyously license server; rotating it means shipping an app update.
PUBKEY_N_HEX = (
    "b02796530abe32d7d0bb6942c07033cec4d632a93a8f211ad832f44bb2b7739871983567157f8a13"
    "ca4ccecf416c0a8598c60c5341b9bf6fd22c5087556c36b3effdbc4ddda7d5306950d53aaa1739908"
    "c678421552245fa9e88bd7d7b4ec8914f420d7cb19d3d03ff9e7e068c4d3d965d95e1d127d74e3625"
    "3e5d3cb49c5e670c67d5a1f68156cb33616093d7a91b629cf819e2e9d2b1f5b029505f85a8dfc26bd"
    "866cc8c541b339b9ba56b5e999ca37ca5e2e574f5c0508e9dc61d5acb500f7a1c7b4f7111ae616b55"
    "4fab7cdfb16f1907aaff596ee2548d092b78071e66226d72116378f4bf954f835208e859ef21978fe"
    "b7480a8b00723fb528c8293878f"
)
PUBKEY_N = int(PUBKEY_N_HEX, 16)
PUBKEY_E = 65537
# ASN.1 DigestInfo prefix for SHA-256 (RFC 8017).
_SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")

_FREE = {"valid": "false", "tier": "free", "expires": "", "features": "dashboards"}


def _b64u_dec(s):
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode("ascii"))


def _rsa_verify(payload, sig, n=PUBKEY_N, e=PUBKEY_E):
    k = (n.bit_length() + 7) // 8
    if len(sig) != k:
        return False
    si_int = int.from_bytes(sig, "big")
    if si_int >= n:
        return False
    em = pow(si_int, e, n).to_bytes(k, "big")
    t = _SHA256_PREFIX + hashlib.sha256(payload).digest()
    expected = b"\x00\x01" + b"\xff" * (k - 3 - len(t)) + b"\x00" + t
    return em == expected


def _verify(value):
    value = (value or "").strip()
    if value == "" or value.upper() == "ENVY-FREE" or "." not in value:
        return dict(_FREE)
    try:
        p, s = value.split(".", 1)
        payload = _b64u_dec(p)
        sig = _b64u_dec(s)
    except Exception:
        return dict(_FREE)
    if not _rsa_verify(payload, sig):
        return dict(_FREE)
    try:
        claims = json.loads(payload)
    except Exception:
        return dict(_FREE)
    exp = claims.get("exp")
    if exp and time.time() > float(exp):
        return dict(_FREE)   # expired -> free (fail closed)
    feats = claims.get("features") or []
    if isinstance(feats, list):
        feats = ",".join(str(f) for f in feats)
    return {
        "valid": "true",
        "tier": str(claims.get("tier") or "premium"),
        "expires": time.strftime("%Y-%m-%d", time.gmtime(float(exp))) if exp else "",
        "features": str(feats or ""),
    }


def main():
    results, _dummy, _settings = si.getOrganizedResults()
    if not results:
        results = [{}]
    for row in results:
        row.update(_verify(row.get("envy_license_key", "")))
    si.outputResults(results)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        si.generateErrorResults(str(exc))
