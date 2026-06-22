# AI Query Assistant for Splunk — v4.0.1 Release Notes

**Release date:** 2026-05-30
**Splunk compatibility:** Enterprise 10.0+ (Python 3.9 fallback) / 10.2+ (Python 3.13 agentic path)
**Type:** Security & licensing hardening (no feature changes)

---

## Summary

v4.0.1 is a **security and licensing hardening** release. There are no changes
to the agentic pipeline, providers, or query behaviour from v4.0.0 — the AI
features are byte-for-byte the same. Every change in this release strengthens
how the app verifies and protects its license.

**Existing licenses keep working.** The verification key is unchanged; any
license issued for v4.0.0 (or earlier 4.x) validates under v4.0.1 without
re-issuance. Customers do not need a new license.

---

## What changed

### Licensing: local signature verification restored

v4.0.1 **verifies the license's RSA-PSS signature locally** as the primary
integrity check. A forged or hand-edited license payload (e.g. an altered
expiry date or tier) is now rejected **offline**, without needing to reach the
license server. The RST License Server still layers activation, heartbeat, and
CRL-based revocation on top.

- The per-app RSA public key ships in `default/app.conf [license]`. It is a
  **public** key — not secret — and is only used to verify signatures.
- Multiple `public_key_pem*` entries are supported for seamless key rotation.

### Hardening fixes

| Ref | Fix |
|-----|-----|
| **C1** | Removed the `mcp.conf [ai] dev_skip_license` config switch that could disable licensing via a single config line. Developer bypass now requires both an environment variable **and** a dev-build marker file that is never present in released packages. |
| **C2** | The activation **session token** is now verified against this host on every check — a license activated on one machine cannot be used on another, even fully offline. |
| **V1** | The session token is bound to its **specific license** — a free/trial license's activation can no longer vouch for a different (paid) license on the same host. |
| **V2** | Offline-grace and revocation state are **scoped per license** — a license cannot ride another license's "recently contacted the server" window to bypass node limits. |

### Hosting note (operators only)

The RST License Server backing this app was hardened in the same cycle
(private status endpoint no longer exposes customer PII, activation node-limit
race fixed, paid-renewal token re-signing, shared rate-limit state across
workers). These are server-side changes and require no action from app users.

---

## Upgrade from 4.0.0

In-place upgrade. No data migration, no license re-issuance.

1. Install the app (Splunkbase or `splunk install app`).
2. Populate runtime dependencies: `python bin/install_deps.py`.
3. Restart Splunk.

After restart, open the app once and confirm your existing license still shows
as active. If you run the app fully air-gapped, ensure the license you pasted
was issued by the RST License Server (its signature is what is now verified
locally).

## Rollback

If needed, reinstall the v4.0.0 package — it shares the same data formats and
license key, so downgrading is safe.

## Known limitations

- Unchanged from v4.0.0: the agentic path requires Python 3.13 (Splunk 10.2+);
  10.0/10.1 fall back to the 3.x-style single-shot translator.
- First-run dependency install pulls ~150 MB of packages.
</content>
