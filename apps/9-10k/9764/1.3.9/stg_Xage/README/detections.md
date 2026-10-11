# Optional Enterprise Security detections

`stg_Xage` ships **nine correlation searches**, all **`disabled = 1`**. They do nothing until you enable them in Splunk Enterprise Security (Premium). Enabling one starts its 15-minute cron (`enableSched = 1` is already set). CIM tags and `` `xage` `` macros come from **stg_Xage_TA**.

ES finds them because each stanza sets `action.correlationsearch.enabled = 1`.

## Risk vs notable

| Kind | Adaptive response | What the analyst sees |
|---|---|---|
| **Risk only** | `action.risk = 1`, `action.notable = 0` | Intermediate risk events on the user and/or system. Feeds Risk-Based Alerting. No Incident Review ticket. |
| **Notable + risk** | both `1` | A notable in Incident Review **and** risk on the object. |

Do not enable every search on day one. Start with notables, then add risk-only if you use RBA.

## Searches

| Stanza | Kind | Severity | MITRE | Fires when |
|---|---|---|---|---|
| Xage - Multiple Failed Device Access - Rule | notable + risk (50) | high | T1110, T1078 | ≥ `xage_cs_fail_count` (default 3) failures by one user |
| Xage - Device Access Failure - Rule | risk (20/10) | — | T1078, T1110 | Any fail, aggregated user+dest (RBA building block) |
| Xage - Privileged Credential Unveil by Non-System - Rule | notable + risk (60) | high | T1555, T1078 | `credentials_unveiled` where actor ≠ `system` |
| Xage - Credential Unveil Spike - Rule | notable + risk (40) | medium | T1555 | ≥ `xage_cs_unveil_spike` (10) unveils per credential+edge |
| Xage - AD Password Rotation Failure - Rule | notable + risk (45) | high | T1098, T1556 | `user_on_AD_password_rotation_fail` |
| Xage - Device Write Access Enabled - Rule | risk (15/15) | — | T1222, T1021 | JIT write-enable (expected; scores the session) |
| Xage - Failed Then Successful Device Access - Rule | notable + risk (70/30) | high | T1078, T1110 | Fail then success, same user+dest, ≤ 3600s |
| Xage - User Access Across Many Devices - Rule | risk (25) | — | T1078, T1021 | ≥ `xage_cs_multi_dest` (4) dests, successful access |
| Xage - Untrusted Audit Event - Rule | notable + risk (80) | critical | T1562 | `isTrusted=false` |

System `credentials_unveiled` events in the captured sample fire about once a minute (ldap bind). There is **no** per-event notable on those — use **Non-System** (human checkout) and **Spike** (runaway volume).

## Enable

**Content Management (preferred)**  
Enterprise Security → Configure → Content → Content Management → filter `Xage` → Enable the searches you want.

**local override**

```
# local/savedsearches.conf
[Xage - Multiple Failed Device Access - Rule]
disabled = 0
```

Tune thresholds without touching SPL:

```
# local/macros.conf
[xage_cs_fail_count]
definition = 5
```

Schedule window is `-70m@m` to `-10m@m` (60 minutes of data, 10 minute lag) every 15 minutes, with per-object suppression (30m–4h). `realtime_schedule = 0` so a search-head restart does not backfill a storm.

## Analytic story

`analyticstories.conf` defines **Xage Zero Trust Access** so the nine searches group together in ES.

## Validate before enabling

```
# who would notable right now (last 60m)
`xage_cim_authentication` action=failure user=*
| stats count as fail_count values(dest) as dest by user
| where fail_count >= `xage_cs_fail_count`

# correlation searches shipped by this TA
| rest splunk_server=local /servicesNS/-/stg_Xage/saved/searches
| search action.correlationsearch.enabled=1
| table title, disabled, cron_schedule, action.notable, action.risk, action.notable.param.severity
```
