# stg_Xage

**Splunk App** for Xage Fabric: Zero Trust dashboards and optional Enterprise Security correlation searches.

Requires the technical add-on **`stg_Xage_TA`** on the same search head (and on indexers/HFs for parse-time).

POC: Ron Conant, STG Splunk Consultant, ronald.h.conant@saic.com  
Author: **SAIC STG Cyber Engineering Service Delivery - 2026**

## Install order

1. `stg_Xage_TA.spl` — search heads **and** indexers / heavy forwarders  
2. `stg_Xage.spl` — search heads only (this package)  
3. Restart Splunk Web  

Use the `.spl` (gzip tar). Splunk rejects a `.zip` with “not a valid tar file.” Check **Upgrade app** when replacing.

**Dashboards require this app AND the TA on the same search head.** Panel searches use `` `xage` `` defined in *this* app (1.3.9+). Pin an index in `stg_Xage/local/macros.conf` (not only the TA):

```
[xage_index]
definition = index=<your_index> `xage_sources`
```


## Dashboards

In-app titles are short so Splunk’s letter avatars are unique.

- **Overview** (O)
- **Authentication** (A) — CIM Authentication
- **Privileged** (P) — unveils, rotations, write-enable
- **Devices** (D)
- **Security alerts** (S) — CIM Alerts
- **Inspector** (I) — vendor vs CIM
- **ES detections** (E) — correlation-search inventory

Chrome: [README/dashboards.md](README/dashboards.md).

## Optional Enterprise Security detections

Nine correlation searches ship **`disabled = 1`**. They create intermediate **risk** events and/or **notables**. Enable individually in ES Content Management.

Thresholds are macros in this app (`xage_cs_fail_count`, etc.). Tune in `local/macros.conf`.

Details: [README/detections.md](README/detections.md).

```
| rest splunk_server=local /servicesNS/-/stg_Xage/saved/searches
| search action.correlationsearch.enabled=1
| table title, disabled, action.notable, action.risk
```

## Layout

```
stg_Xage/
  default/app.conf macros.conf savedsearches.conf analyticstories.conf
          data/ui/nav/default.xml
          data/ui/views/*.xml
  appserver/static/          dashboard.css/js, brand_banner.png
  static/                    appIcon, appLogo
  metadata/default.meta
```
