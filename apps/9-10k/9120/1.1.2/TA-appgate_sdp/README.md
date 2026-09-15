# TA-appgate_sdp — Splunk Technology Add-on for Appgate SDP

CIM-compliant field extractions, eventtypes, and tags for **Appgate SDP**
(Software Defined Perimeter / Zero Trust Network Access) audit events.

| | |
|---|---|
| Sourcetype | `appgate:sdp` |
| Ingest path | SC4S → HEC (also parses correctly via file monitor / TCP / UF) |
| Event format | Single-line JSON: `{"version","timestamp","hostname","daemon","log":{...}}` |
| CIM version | Mappings verified against CIM **8.5** data model docs (help.splunk.com) |
| Vendor reference | Appgate SDP v6.4 audit log catalog (sdphelp.appgate.com) |
| Contents | props, eventtypes, tags, transforms, lookups |

There is **no official or community Appgate SDP add-on on Splunkbase**
(verified 2026-07 via the Splunkbase API), so this TA defines the site
convention for this sourcetype.

## Installation

* **Search head(s)** — required. All CIM mappings in this TA are search-time
  (`KV_MODE=json`, aliases, calculated fields, lookups, eventtypes, tags).
* **Indexers / heavy forwarders** — recommended. The index-time settings
  (line breaking, timestamp, `TRUNCATE`) only take effect for non-HEC ingest
  paths; SC4S delivers pre-parsed events so they are inert there, but installing
  everywhere keeps behavior consistent if the ingest path ever changes.
* **CIM setup** — if the `cim_<Model>_indexes` macros in Splunk_SA_CIM have been
  constrained to an index allowlist, add the Appgate index (e.g. `appgate`) to the
  macros for: Network Traffic, Authentication, Network Sessions, Certificates,
  and Compute Inventory. With the default (unconstrained) macros no change is needed.

## CIM data model mapping

| event_type | Eventtype | Data model | Tags |
|---|---|---|---|
| `ip_access` | `appgate_sdp_ip_access` | Network Traffic | `network`, `communicate` |
| `authentication_succeeded`, `otp_/password_authentication_succeeded`, `ssh_access_succeeded` | `appgate_sdp_authentication_success` | Authentication | `authentication` |
| `authentication_failed`, `otp_/password_authentication_failed`, `ssh_access_failed` | `appgate_sdp_authentication_failure` | Authentication | `authentication` |
| `session_created`, `session_reconnected` | `appgate_sdp_session_start` | Network Sessions › Session_Start + VPN | `network`, `session`, `start`, `vpn` |
| `session_removed` | `appgate_sdp_session_end` | Network Sessions › Session_End + VPN | `network`, `session`, `end`, `vpn` |
| `vpn_certificate_signed`, `certificate_issued`, `appliance_certificate_renewed`, `issued_certificate_revoked` | `appgate_sdp_certificate` | Certificates › SSL | `certificate`, `ssl` |
| `device_claims_accepted`, `device_on_boarded` | `appgate_sdp_device_inventory` | Compute Inventory › OS + Network | `inventory`, `system`, `version`, `network` |
| `tunnel_established` | `appgate_sdp_tunnel_establish` | Network Sessions › Session_Start + VPN | `network`, `session`, `start`, `vpn` |
| `tunnel_closed` | `appgate_sdp_tunnel_close` | Network Sessions › Session_End + VPN | `network`, `session`, `end`, `vpn` |
| `tunnel_connected` | `appgate_sdp_tunnel_connect` | Network Sessions › VPN (no start — pre-login TLS connect) | `network`, `session`, `vpn` |
| `acl_rules_update` | `appgate_sdp_acl_update` | Network Sessions › VPN (per-session statistics record) | `network`, `session`, `vpn` |
| `entitlement_token_*` | `appgate_sdp_entitlement` | — (no CIM model for policy evaluation) | `policy`, `entitlement` |
| `remedy_*` | `appgate_sdp_remedy` | — (no CIM model for policy evaluation) | `policy`, `remedy` |
| `authorization_*`, `admin_authorization_*` | `appgate_sdp_authorization` | — (see notes) | base tags only |
| all remaining types | `appgate_sdp_claims_token`, `_device_script`, `_license`, `_admin_message`, `_appliance_status`, `_url_access`, `_config_change`, `_audit_drop`, `_account_lockout`, `_alert`, `_blocklist` | — | base tags only |
| **every** appgate:sdp event | `appgate_sdp` (base) | — | `appgate`, `ztna` |

The base-eventtype vendor tags (`appgate`, `ztna`) guarantee that 100% of
appgate:sdp events carry at least one tag — including any future event types —
without pulling anything into a CIM data model (they match no model constraint).

Note on Compute Inventory tags: the CIM 8.5 OS child dataset requires tags
`system` **and** `version` (the OS *field* is named `os`, but there is no `os`
*tag*); the root additionally requires `inventory` plus at least one child tag.
The `network` tag routes the device's IP/MAC claims into the Network child.

### Deliberate scoping choices

* **Tunnels vs. sessions (counting caveat).** Both the broker-session events
  (`session_*`, cz-sessiond) and the per-gateway tunnel events (`tunnel_*`,
  cz-vpnd) are tagged into Network Sessions, and one SDP session opens one
  tunnel *per gateway/site* — so `| tstats count from datamodel=Network_Sessions`
  over Session_Start is **not** a unique-session count. Only
  `tunnel_established` carries the `start` tag (`tunnel_connected` fires at TLS
  connect before login and would double-count); for strict unique-session
  counting filter by eventtype, e.g.
  `tag=session tag=start eventtype=appgate_sdp_session_start | stats dc(session_id)`.
* **`acl_rules_update`** is named misleadingly: per vendor docs it is
  "statistics relating to a user session" — cumulative bytes/packets/RTT/
  duration counters for an active VPN session. It is tagged into Network
  Sessions (root + `vpn`, no start/end) as a session-statistics record, and is
  deliberately excluded from Network Traffic (it is not a flow event).
* **Authorization.** `authorization_succeeded` fires once per sign-in *in
  addition to* `authentication_succeeded`. Tagging both would double-count
  logins in the Authentication data model, so authorization is not CIM-tagged
  (the eventtype still exists, and `action=success/failure` is still populated).
* **Token lifecycle.** For the same reason, `claims_token_not_accepted` /
  `entitlement_token_not_accepted` are *not* tagged as Authentication failures:
  token validations fire repeatedly across a session's lifetime and tagging
  only rejections (with no tagged success counterpart) would skew
  success/failure ratios. `action=failure` is still populated on them for
  ad-hoc searching via `eventtype=appgate_sdp_claims_token action=failure`.
* **`entitlement_token_evaluated`** (~29% of volume) and
  **`remedy_action_triggered`** are policy (re-)evaluation records — no CIM
  data model exists for authorization policy evaluation, so they carry the
  descriptive tags `policy` + `entitlement`/`remedy` instead of CIM tags.
* **Future families** documented by Appgate data are pre-wired: `url_access` (candidate for the Web data model) and
  `entity_created/updated/deleted` (candidates for the Change data model) have
  eventtypes but no CIM tags — add those only once real events can be validated.
* **`audit_drop`** means Appgate dropped audit records before forwarding —
  worth an ES correlation search / alert for ingest completeness.

## Field mappings (search-time)

Source JSON fields are auto-extracted by `KV_MODE=json` with their dotted
names (`log.action`, `log.geoip.city_name`, ...) and remain available as-is.
CIM fields are layered on top:

### All events
| CIM field | Source |
|---|---|
| `dvc` | `hostname` (envelope — the appliance) |
| `event_type`, `signature` | `log.event_type` |
| `user` | `log.distinguished_name_user`, else `log.user_claims.ag.username`, else user CN parsed from `log.user_distinguished_name` |
| `src`, `src_ip` | `log.source_ip` (ip_access), else `log.client_ip`, else `log.system_claims.clientSrcIP` / `.client_src_ip` |
| `src_port` | `log.source_port`, else `log.client_port` |
| `dest` | `log.destination_ip` (ip_access), else `log.device_claims.os.hostname` / `log.client_hostname` (posture events), else `hostname` |
| `vendor`, `product`, `vendor_product` | `Appgate` / `SDP` / `Appgate SDP` |
| `app` | `appgate_sdp` |
| `event_category`, `event_description` | automatic lookup `appgate_sdp_event_lookup` on `event_type` |

### Network Traffic (`ip_access`)
| CIM field | Source |
|---|---|
| `action` | `allow`/`allow_report` → `allowed`; `block`/`block_report`/`drop`/`reject` → `blocked` (CIM 8.5 prescribes only allowed/blocked/teardown). Vendor action preserved in `log.action`; drop detail in `log.drop-reason` |
| `dest_ip`, `dest_port` | `log.destination_ip`, `log.destination_port` |
| `transport` | `log.protocol` normalized to lowercase `tcp`/`udp`/`icmp` (CIM requires lowercase) |
| `direction` | `up` → `inbound` (client → protected endpoint), `down` → `outbound` (vendor-documented semantics) |
| `rule` | `log.rule_name` (rule subnet stays in `log.rule_subnet`) |
| `bytes` | `log.packet_size` (size of the packet that triggered the decision — do **not** aggregate `All_Traffic.bytes` volumetrically for this sourcetype; per-session byte counters live on the `acl_rules_update`/`tunnel_closed` events as `bytes_in/out` in Network Sessions) |
| `icmp_code`, `icmp_type` | `log.icmp_code`, `log.icmp_type` |
| `src_translated_ip/port` | `log.nat_src_ip/port` when present (vendor NAT fields), else `log.client_ip/client_port` (client public address outside the tunnel; only when `log.source_ip` exists) |
| `reason` | `log.drop-reason` (populated on drop/reject: "No matching rule found", ...) |

Vendor `action` semantics (Appgate v6.4): `block_report` fires when a condition
attached to the entitlement failed/expired **or** an ALERT rule matched (an
intentional SIEM tripwire — the most detection-worthy blocks); `drop`/`reject`
are default-deny (no matching rule), with `reject` coming from the web client.

### Authentication (`*authentication_succeeded/_failed`, `ssh_access_*`)
| CIM field | Source |
|---|---|
| `action` | `success` / `failure` by event_type |
| `authentication_service` | `log.user_claims.ag.identityProviderName` |
| `src` / `dest` | `log.client_ip` / controller `hostname` |
| `reason` (informational) | `coalesce(log.reason, log.drop-reason)` — note CIM 8.5 renamed the model field to `reason_id`; this one is kept for analyst convenience |

### Network Sessions (`session_*`, `tunnel_*`, `acl_rules_update`)
CIM 8.5 quirk (verified): this model has **no `src`/`dest`/`session_id`
fields** and defines `dest_ip` as "the internal IP address allocated to the
client" (DHCP-lease semantics). Mapped accordingly:

| CIM field | Source |
|---|---|
| `action` | `started` (session_created/reconnected, tunnel_connected/established) / `ended` (session_removed, tunnel_closed) — model-prescribed values |
| `src_ip` | `log.client_ip` (tunnel/acl events), else `log.system_claims.clientSrcIP` (session events; `session_removed` carries no IP — expected) |
| `dest_ip` | `log.pool_v4_ip` / `log.system_claims.tunIPv4` (the allocated tunnel IP; the vendor sentinel `Unassigned` is filtered out) |
| `user` | `log.distinguished_name_user` |
| `session_id` (non-CIM) | `log.session_id` — kept for pivoting even though the model dropped it (present on cz-sessiond events only; tunnel/acl events from cz-vpnd don't carry it) |
| `duration`, `bytes_in/out`, `packets_in/out` | `log.statistics.*` (cumulative per-session counters, populated on `tunnel_closed` and `acl_rules_update`) |

### Certificates (`vpn_certificate_signed`, `certificate_issued`, `appliance_certificate_renewed`, `issued_certificate_revoked`)
| CIM field | Source |
|---|---|
| `ssl_issuer`, `ssl_subject`, `ssl_serial`, `ssl_version` | `log.certificate.*` |
| `ssl_issuer_common_name`, `ssl_subject_common_name` | first CN parsed from the DNs |
| `ssl_hash` | `log.certificate.fingerprint` (SHA-256; CIM prescribes no algorithm) |
| `ssl_start_time`, `ssl_end_time`, `ssl_validity_window` | `log.certificate.valid_from/valid_to` parsed to epoch (TZ-safe `Z`→`+0000`) |

### Compute Inventory (`device_claims_accepted`, `device_on_boarded`)
| CIM field | Source |
|---|---|
| `dest` | `log.device_claims.os.hostname` / `log.client_hostname` |
| `os` | `log.device_claims.os.name` |
| `family` | `log.device_claims.os.family` |
| `mac` | `log.device_claims.macAddresses{}` normalized to lowercase colon-separated (CIM format) |
| `ip` | `log.device_claims.clientIPs{}` |
| `version` | `log.device_claims.os.version` on inventory events only (a conditional EVAL — the field name collides with the JSON envelope's schema-version, which all other events keep); also copied to `os_version` for convenience |

## Validation searches

```spl
sourcetype=appgate:sdp | stats count by eventtype
```

```spl
| datamodel Network_Traffic All_Traffic search
| search sourcetype=appgate:sdp
| stats count by All_Traffic.action, All_Traffic.transport
```

```spl
| tstats count from datamodel=Authentication by Authentication.action, Authentication.app
| search Authentication.app=appgate_sdp
```

```spl
sourcetype=appgate:sdp tag=network tag=session | stats count by event_type, action
```

```spl
| tstats count from datamodel=Compute_Inventory by All_Inventory.dest, All_Inventory.OS.os
```

## Version history

* **1.1.2** — Minor formatting changes to some comments 
* **1.1.1** — Added the NuHarbor app icon set (`static/appIcon*.png`).
* **1.1.0** — Closed the tag-coverage gap: `tunnel_*` and `acl_rules_update`
  now tagged into Network Sessions (VPN child; only `tunnel_established` is a
  `start`); `entitlement_*`/`remedy_*` carry descriptive `policy` tags; base
  eventtype carries `appgate`+`ztna` so every event has at least one tag.
  Eventtype `appgate_sdp_tunnel_open` was split into `appgate_sdp_tunnel_connect`
  and `appgate_sdp_tunnel_establish`.
* **1.0.0** — Initial release.

## Notes / known limitations

* `log.geoip.*` (client geolocation enriched upstream) is left under its native
  names; ES asset/identity or `iplocation` can re-derive as needed.
* `log.statistics.used-entitlements.<name>` and `log.app_shortcuts.<name>` have
  dynamic key names and cannot be aliased statically.
* Events arrive wrapped (`log{}` envelope) because Appgate wraps audit events
  for all non-LogServer destinations; if a LogServer/OpenSearch export is ever
  ingested instead, the fields arrive flattened at top level and this TA's
  alias layer would need a variant sourcetype.
* An existing eventtype named `err0r` (from another app in the search head
  environment) currently matches ~29% of appgate:sdp events; it is unrelated
  to this TA and worth cleaning up separately.
