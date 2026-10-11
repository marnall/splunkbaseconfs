# stg_Xage_TA

**Technical Add-on** for Xage Fabric syslog audit logs. Knowledge only: parse, CIM-normalize, tag. Dashboards and ES detections are in the companion app **`stg_Xage`**.

POC: Ron Conant, STG Splunk Consultant, ronald.h.conant@saic.com  
Author: **SAIC STG Cyber Engineering Service Delivery - 2026**

## What this package is

| Goes here (TA) | Goes in `stg_Xage` (App) |
|---|---|
| props / transforms / eventtypes / tags / lookups | Dashboards, nav, CSS/JS |
| CIM macros (`` `xage` ``, `` `xage_cim_*` ``) | ES correlation searches + thresholds |
| Example inputs | Reports, analytic story |
| Search heads **and** indexers / HFs | Search heads only |

Install **TA first**, then the App. The TA is hidden from the Apps menu (`is_visible = false`); it still appears under Manage Apps.

## Wire format

```
<134> 2026-09-02T19:11:20Z edgehost01 xage[1]: <134>1 - - xage - auditlog - {"id":"...","message":"user_access_device_fail",...}
```

Covers `source=xage` and production `source=tcp:5514` (`sourcetype=syslog` historically). New matching events reclass to `sourcetype=xage:audit`. No reindex required.

## Install

Use `stg_Xage_TA.spl` (gzip tar). A `.zip` is rejected as “not a valid tar file.”

1. **Apps → Manage Apps → Install app from file** → `stg_Xage_TA.spl` (Upgrade app if replacing).
2. Repeat for `stg_Xage.spl` on **search heads**.
3. Copy this TA to **indexers / heavy forwarders** for index-time `TIME_*`, `LINE_BREAKER`, and sourcetype rewrite.
4. Restart Splunk. Install [Splunk CIM](https://splunkbase.splunk.com/app/1621/) if you will accelerate models.

Optional index pin in `etc/apps/stg_Xage_TA/local/macros.conf`:

```
[xage_index]
definition = index=<your_index> `xage_sources`
```

## CIM models

| Model | When |
|---|---|
| Authentication | `user_access_device_success` / `_fail` |
| Change (account) | AD password rotation |
| Change (endpoint) | device write access enable/disable |
| Change (audit) | `credentials_unveiled` |
| Alerts | `msgLevel=Error` and `*fail*` signatures |

Field map: [README/cim_mapping.md](README/cim_mapping.md).

## Validate

```
`xage` | head 20 | table _time, source, sourcetype, message, user, dest, action, signature, vendor_product
| from datamodel:Authentication | search vendor_product="Xage Fabric"
`xage` | stats count by eventtype, tag, signature
```

## Layout

```
stg_Xage_TA/
  default/app.conf props.conf transforms.conf eventtypes.conf tags.conf
          fields.conf macros.conf inputs.conf
  lookups/xage_message_cim.csv
  metadata/default.meta          export = system
  samples/xage_audit_sample.log
  static/                        appIcon / appLogo (Manage Apps)
```
