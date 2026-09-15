# NordStellar (TA-nordstellar)

Receives and parses the security events NordStellar forwards into Splunk's HTTP
Event Collector, and provides a setup page that generates the **API URL** and
**API key** you paste into NordStellar — no manual token creation needed.

Full setup guide: <https://docs.nordstellar.com/platform/integrations/siem/splunk>

## What it does

1. **Setup page** (`NordStellar Setup`) — enables the HTTP Event Collector,
   creates a dedicated token with `sourcetype = nordstellar:security:event`, and
   shows you the **API URL + API key** to paste into NordStellar.
2. **Parsing** — every field of the NordStellar JSON event is extracted
   automatically, a set of common fields is promoted to friendly names, and
   events are normalized onto the Splunk Common Information Model (CIM).

## Install

**Splunk Web (recommended):** _Apps → Manage Apps → Install app from file_, upload
the app package (`.tar.gz`/`.spl`), then restart Splunk when prompted.

**Manually:** extract the app into `$SPLUNK_HOME/etc/apps/` (so it lives at
`$SPLUNK_HOME/etc/apps/TA-nordstellar`) and restart Splunk so it loads the
configs, REST handler, and views:

```bash
$SPLUNK_HOME/bin/splunk restart
```

## Connect NordStellar

1. In Splunk Web, open **Apps → NordStellar** (or **Settings → Manage Apps**). On
   first launch you are taken to **NordStellar Setup** automatically.
2. Set the **target index** (default `main`; the index must already exist) and
   click **Generate API key**. You must be logged in as a user with the
   `edit_httpinputs` capability (the `admin` role has it).
3. Copy the **API URL** and **API key** into your NordStellar Splunk integration
   settings. The **sourcetype** is shown for reference only — it is set
   automatically on the token, so you don't enter it in NordStellar.

The API URL is your Splunk collector root and the API key is a HEC token.
NordStellar appends the `/raw` ingest path itself, so paste the URL without a
trailing path.

> **Splunk Cloud** uses a different collector host —
> `https://http-inputs-<stack>.splunkcloud.com:443/services/collector`. Adjust the
> URL shown on the setup page before pasting it into NordStellar.

On an already-configured instance the page shows the existing connection details
directly (the target index is read-only and there is nothing to generate).
Re-running setup reuses the existing `nordstellar` token rather than creating a
duplicate. To rotate the API key or change the index, delete that token under
**Settings → Data inputs → HTTP Event Collector**, reload the page, and
reconfigure NordStellar with the newly generated key.

## Verify

Once you save the integration in NordStellar it sends a test event, and real
events then flow in automatically:

```
index=<your index> sourcetype="nordstellar:security:event"
```

The **test event** carries only a `title` and `description`, so it appears with
`signature` / `body` populated — enough to confirm events are ingested and
parsed. It arrives at the current time, so `Last 15 minutes` will find it. The
promoted fields (`EventType`, `RiskLevel`, `AssetValue`, …) and CIM fields
populate once real NordStellar events arrive, which carry those fields.

## Fields

The full raw event is always searchable, since nothing is dropped during parsing.
The fields below are what the app adds on top. Categorization comes from
NordStellar's own `type` and `module` values.

### Promoted fields

| Splunk field       | source                       | notes                                                                                |
| ------------------ | ---------------------------- | ------------------------------------------------------------------------------------ |
| `EventId`          | `id`                         |                                                                                      |
| `EventType`        | `type`                       |                                                                                      |
| `Module`           | `module`                     |                                                                                      |
| `RiskLevel`        | `risk_level`                 |                                                                                      |
| `AssetType`        | type-aware                   | `DOMAIN_PERMUTATION`→`DOMAIN`; else `asset.type` / `source_type`                     |
| `AssetValue`       | type-aware                   | `DOMAIN_PERMUTATION`→`original_domain`; else `asset.value` / `asset_value` / `query` |
| `Tags`             | `tags[]`                     |                                                                                      |
| `DetectedAt`       | `detected_at` / `date_added` | the finding's own date, ISO-8601 (UTC)                                               |
| `DetectionTime`    | `detected_at` / `date_added` | the same date as epoch seconds, for time math and sorting                            |
| `SquattedDomain`   | `domain`                     | domain squatting only — the suspicious permutation, not your own domain              |
| `ServiceVersion`   | `version`                    | attack surface network service findings — the exposed software version               |
| `DeviceCountry`    | `location.country`           | malware infections — where the infected endpoint was                                 |
| `DeviceCity`       | `location.location_name`     | malware infections                                                                   |
| `DevicePostalCode` | `location.zip_code`          | malware infections                                                                   |
| `DeviceTimeZone`   | `location.time_zone`         | malware infections                                                                   |

`AssetValue` is always the asset **you** own. For domain squatting that is your
legitimate domain, so the suspicious look-alike is in `SquattedDomain` — that is
the value to block or pivot on. Dark web posts have no asset attached, so they
fall back to the monitored term that matched (`query`), which is what ties the
post back to you.

### Event time vs. ingest time

`_time` is the moment Splunk received the event, **not** the moment NordStellar
detected the finding. The detection date is available as `DetectedAt` and
`DetectionTime`.

This is deliberate. NordStellar delivers historical findings — leaked credentials
and stealer logs are frequently dated months or years before you receive them.
Indexing those under their original date would hide freshly delivered findings
from recent-window searches and scheduled alerts, and could place them outside
your index's retention period the moment they arrive. Using ingest time keeps
every delivered finding visible and searchable.

To work with detection dates, filter or sort on `DetectionTime`:

```
index=<your index> sourcetype="nordstellar:security:event"
| eval DaysOld = round((now() - DetectionTime) / 86400)
| eval Detected = strftime(DetectionTime, "%F %T")
| table _time Detected DaysOld EventType RiskLevel AssetValue signature
```

### CIM fields

| NordStellar field                         | CIM field                  |
| ----------------------------------------- | -------------------------- |
| _(constant)_                              | `vendor`, `vendor_product` |
| _(constant)_                              | `dvc`                      |
| `risk_level`                              | `severity`, `severity_id`  |
| `id`                                      | `signature_id`             |
| title fields, falling back to `type`      | `signature`, `subject`     |
| `description`/`content`                   | `body`                     |
| `cve_id`                                  | `cve`                      |
| `cvss3_score`                             | `cvss`                     |
| `cwe_ids[]`                               | `xref`                     |
| `vulnerability_type`                      | `category`                 |
| `network_service_name`                    | `service`                  |
| `protocol`                                | `transport`                |
| `port`                                    | `dest_port`                |
| asset/host (type-aware)                   | `dest`                     |
| `device_info.system_name`                 | `dest_nt_host`             |
| `device_info.os`                          | `os`                       |
| `files{}.path`                            | `file_name`                |
| identity (type-aware)                     | `user`                     |
| `email` / `asset.value` (EMAIL)           | `user_email`               |
| `evidence_url`/`url`/`site_subdomain_url` | `url`                      |

`vendor` is always `Nord Security`, and `vendor_product` and `dvc` are always
`NordStellar`, so you can split CIM dashboards by source.

`signature` always has a value. Where a finding has no title of its own — data
breaches, combo lists, domain squatting — it falls back to the event `type`, so
findings group cleanly in Enterprise Security rather than arriving unnamed.

Note that `product` is **not** a constant: on attack surface network service
findings it holds the exposed software name (for example `OpenSSH`).

`dest` and `user` depend on the event type: for `MALWARE_INFECTION`, `dest` is
the infected endpoint (`device_info.ip`) and `user` is `device_info.user_name`;
for attack surface, `dest` is the scanned `asset_value`.

### CIM data models

Events are tagged for the CIM data models that fit them:

| NordStellar `type`  | CIM tag             | CIM data model  |
| ------------------- | ------------------- | --------------- |
| all events          | `alert`             | Alerts          |
| `ATTACK_SURFACE_*`  | `vulnerability`     | Vulnerabilities |
| `MALWARE_INFECTION` | `malware`, `attack` | Malware         |

Dark web, data breach, combo list, and domain squatting findings have no
matching CIM data model. Those events are field-normalized and carry the generic
`alert` tag rather than being forced into an unrelated model.

### Other fields worth knowing

These are not promoted or normalized, but they are extracted from the JSON like
everything else and are directly searchable:

| Field                                      | notes                                                   |
| ------------------------------------------ | ------------------------------------------------------- |
| `is_resolved`                              | whether NordStellar considers the finding resolved      |
| `official_breach_date`                     | data breaches — when the breach itself happened         |
| `epss_score`, `cvss2_score`, `cvss_vector` | attack surface — scoring detail beyond CVSS 3 base      |
| `permutation_type`                         | domain squatting — e.g. `HOMOGLYPH`                     |
| `dark_web_monitoring_rule_name`            | which of your monitoring rules matched                  |
| `posted_at`, `scraped_at`                  | dark web — when the post appeared and when it was found |
| `infection_date`                           | malware infections and consumer credentials             |

Filtering out resolved findings is the common case:

```
index=<your index> sourcetype="nordstellar:security:event" is_resolved=false
```

## Support

-   Documentation: <https://docs.nordstellar.com/platform/integrations/siem/splunk>
-   Support and general inquiries: <https://nordstellar.com/contact-us/>

NordStellar customers can also reach their dedicated account manager directly.
