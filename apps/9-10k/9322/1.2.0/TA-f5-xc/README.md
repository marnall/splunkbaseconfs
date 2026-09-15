# TA-f5-xc — F5 Distributed Cloud (XC) Add-on

CIM-compliant parsing and field mapping for **F5 Distributed Cloud (XC)** security
and access logs delivered to Splunk via **HTTP Event Collector (HEC)** as
**`sourcetype = f5:xc`**.

It maps F5 XC events to the **Web** and **Intrusion Detection** data models so the
data lights up Enterprise Security (Security Posture, Intrusion Center, Web
dashboards) and any CIM-based content with no per-customer SPL rework.

Covers four F5 XC event classes (discriminated by `sec_event_type`):

| `sec_event_type`          | What it is                              | Data model(s)                |
|---------------------------|-----------------------------------------|------------------------------|
| *(none — access log)*     | HTTP request / access log               | Web                          |
| `waf_sec_event`           | WAF / app-firewall signature & violation | Web + Intrusion Detection    |
| `bot_defense_sec_event`   | Bot Defense verdict                     | Web + Intrusion Detection    |
| `svc_policy_sec_event`    | L7 service-policy enforcement (e.g. geofencing) | Web + Intrusion Detection (when `action="block"`) |

---

## Requirements

- Splunk Enterprise / Cloud **8.x or 9.x**.
- The **Common Information Model add-on** (`Splunk_SA_CIM`) for data-model
  acceleration / ES.
- F5 XC must be configured to ship logs to a Splunk **HEC** endpoint as JSON
  (the F5 XC "Global Log Receiver" / HTTP log sink).

This add-on is **parsing/knowledge only** — it has **no inputs, no scripts, no
credentials, and no external dependencies**. It is safe to share and install
anywhere.

---

## Deployment

1. **Install the add-on**
   - **Splunk Cloud:** install the `.tgz` via the ACS / "Install app from file"
     path (it is AppInspect-clean: no inputs, no binaries).
   - **On-prem:** drop the `TA-f5-xc/` folder into `$SPLUNK_HOME/etc/apps/` on the
     **search head(s)**. For index-time use (the optional transform below) it must
     also reach the **indexer(s)**.

2. **Set the sourcetype to `f5:xc`** on the F5 XC HEC input — this is what the
   add-on keys on. Two ways:
   - **Preferred:** create/point a **dedicated HEC token** for F5 XC and set its
     default **sourcetype = `f5:xc`** (Settings → Data inputs → HTTP Event
     Collector, or via the F5 XC log-receiver config if it sets the sourcetype).
   - **Fallback (shared token only):** if you cannot set the sourcetype on the
     token and the token carries other data too, use the optional index-time
     transform in `default/transforms.conf` (`f5_xc_set_sourcetype`) wired to your
     F5 HEC `source`. See the comments in that file. Index-time transforms must be
     deployed to the indexing tier.

3. **Send to a dedicated index** (recommended, e.g. `f5`) and make sure your roles
   and the Web / Intrusion Detection data models include it.

4. **Verify**

   ```spl
   sourcetype=f5:xc | stats count by sec_event_type
   sourcetype=f5:xc | head 1 | table src, src_port, dest, dest_port, http_method, uri_path, status, action, signature, category, severity
   | datamodel Web Web flat | search sourcetype=f5:xc | stats count by action
   | datamodel Intrusion_Detection IDS_Attacks flat | search sourcetype=f5:xc | stats count by signature, severity
   ```

---

## Key CIM mappings

- **`src`** is forced to the real client IP (`src_ip`). F5's raw `src` is a
  network-zone label (e.g. `N:public`) and is preserved as **`src_zone`**.
- **Web:** `action` (normalized to allowed/blocked), `http_method`,
  `http_user_agent`, `uri_path`, `uri_query`, `url`, `status`, `dest`, `dest_ip`,
  `dest_port`, `site`, `bytes_in`/`bytes_out`/`bytes`, `http_version`,
  `http_referrer`.
- **Intrusion Detection:** `ids_type=application`, `signature`, `signature_id`,
  `category`, `severity` (derived from signature risk / violation rating /
  request risk / bot insight), `vendor_action`, `cve`.
- **TLS / perf:** `ssl_version`, `ssl_cipher`, `response_time`.
- **Geo (client):** `src_country`, `src_city`, `src_region`, `src_lat`,
  `src_long` (F5's `PRIVATE` placeholders are nulled).
- **Identity:** `vendor=F5`, `product=Distributed Cloud`,
  `vendor_product=F5 Distributed Cloud`, `dvc` (site/cluster).

Reference: <https://docs.cloud.f5.com/docs/how-to/app-security/event-logs>

---

## Caveats

- Field coverage depends on what F5 XC actually emits per event class; not every
  field is present in every event (e.g. `ssl_version`/`response_time` only appear
  in `svc_policy_sec_event` access logs in some tenants).
- `severity` is a best-effort normalization from several F5 risk indicators; tune
  the `EVAL-severity` `case()` in `default/props.conf` to your environment if
  needed.
- Add-on is **search-time/parse-time** by default. The only index-time component
  is the **optional** `f5_xc_set_sourcetype` transform, which is disabled unless
  you explicitly wire it up.

---

## Version

**1.2.0** — generic/shareable build. Parsing & CIM mapping for `sourcetype=f5:xc`.
