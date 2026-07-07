# Spur Enrichment For Splunk
Enhance your Splunk experience with the Spur Enrichment for Splunk App. This application integrates with Spur products, providing you with enriched data and insights right in your Splunk environment. Generate events based on IP inputs, enrich existing events with data from the Spur Context API, and insert feed data into a Splunk index with our modular input feature.

The Spur Splunk App requires an active Spur subscription and specific user privileges for installation. 

Once installed, you can utilize our search commands and modular input features to generate and enrich your data. 

Get the most out of your data with the Spur Splunk App. Download today and start exploring your data in new ways.

## Pre-requisites
1. An active [Spur](https://spur.us/) subscription. Your subscription determines which products you can use:
   - **Context API** — powers the `spurcontextapi` and `spurcontextapigen` search commands.
   - **Feeds** — powers the `spurfeedingest` modular input and the `spuriplocation` command (via the ipgeo MMDB).
   These subscriptions are separate. You can use Context API commands without ingesting feeds, and you can ingest feeds without calling the Context API.
2. A Spur API token — you will enter this during the app setup.
3. Splunk capability requirements:
   - The user installing the app needs `admin_all_objects` (standard for Splunkbase installs).
   - Users running the search commands need only the `search` capability. The app reads its secrets through a privileged REST handler, so `list_storage_passwords` is NOT required of search users.

## Installation

### From Splunkbase (recommended)
1. In Splunk Web, go to **Apps → Find more apps online**.
2. Search for **Spur**, click **Install**, and accept the license.
3. Complete the app setup and enter your Spur API token.

### Manual upload from a `.tar.gz`
1. Download the app tarball from [Splunkbase](https://splunkbase.splunk.com/app/7126).
2. In Splunk Web, go to **Apps → Manage Apps → Install app from file**.
3. Upload the tarball and complete the app setup.

## Search Head Cluster (SHC) setup note

If you are running a Search Head Cluster, complete the app setup on **one** SH member. The app includes SHC conf-replication for its secrets, API config, and `is_configured` flag, so the setup propagates to the other members automatically — but there are two separate timing layers to be aware of:

1. **File replication** is fast (seconds). The `is_configured = 1` flag and the stored token land on every SH member's disk shortly after you complete setup.
2. **In-memory manifest refresh** can lag. Each SH's Splunk Web caches app metadata at process startup and only re-reads it on specific triggers. Until that re-read happens, other SH members may still redirect users to the setup page even though the config is already in place.

If you hit the setup page on a different SH right after configuring, you have three options in ascending order of disruption:

- Wait a few minutes — Splunk Web will re-read app state on its own.
- Force an immediate refresh on a single member: `curl -sk -u admin:<pw> -X POST "https://<that-member>:8089/servicesNS/nobody/system/apps/local/spur-enrichment-for-splunk/_reload"`
- Rolling-restart the SHC from the captain: `splunk rolling-restart shcluster-members`

End users (non-admin roles) do not need to re-run setup on each member — only the one-time admin setup matters.

## Configure your index

The app does not create a Splunk index. Before running the `spurfeedingest` modular input, pick (or create) the index you want feed events stored in. The shipped dashboards and example searches reference a macro named `spur_index` rather than hard-coding an index name, so you can retarget everything in one place.

To edit the macro:

1. In Splunk Web, go to **Settings → Advanced search → Search macros**.
2. Select app **Spur Enrichment for Splunk**.
3. Edit `spur_index`. The default is `index=spur`. Change it to match your deployment (for example `index=spur_threat` or `index=main`).

## Overview dashboard

On install the app lands on **Overview**, which provides copy-pasteable examples for each search command, a feed-ingest status table, and live breakdowns of top infrastructure types and top anonymous tunnel operators from the feed. This is the fastest way to confirm the app is wired up correctly.

## Right-click enrichment

Fields named `src_ip`, `src`, `clientip`, `dest_ip`, `ip`, `ipaddress`, `src_addr`, `source_ip`, or `dst_ip` get two Spur actions in the field-value menu:

- **Enrich _field_ with Spur Context API** — calls `spurcontextapigen` for the clicked IP.
- **Locate _field_ with Spur IP Geo** — calls `spuriplocation` for the clicked IP.

Both open a new search window with the enrichment result.

## Macros

The app ships three macros you can reference from your own searches (Settings → Advanced search → Search macros):

- `` `spur_index` `` — the index the `spurfeedingest` modular input writes to. Default `index=spur`. Edit this one macro to retarget every shipped dashboard/search to your chosen index.
- `` `spur_enrich(<field>)` `` — shorthand for `spurcontextapi ip_field="<field>"`. Example: `... | \`spur_enrich(clientip)\``.
- `` `spur_anonymous` `` — filter for enriched events with at least one anonymous tunnel (`spur_tunnels_anonymous="True"`). Note: anonymity is a per-tunnel boolean in the Spur API and is NOT the same as `spur_infrastructure` being `VPN`/`TOR`/`PROXY` — a corporate VPN has `infrastructure=VPN` but is not anonymous.

## Search Commands
### Generating command
This command generates events from input IPs. It uses the Spur Context API so you must have an active Context API subscription. The command takes one argument, `ip`, which is the IP (or comma-separated list of IPs) that will be passed to the Context API.

#### Examples
Single IP:
```
| spurcontextapigen ip="1.1.1.1"
```

Multiple IPs (quote the whole list — SPL's parser will otherwise split on the first comma):
```
| spurcontextapigen ip="1.1.1.1,8.8.8.8,9.9.9.9"
```

### Streaming command
This command enriches existing events with data from the Spur Context API. It uses the Spur Context API so you must have an active Spur subscription. The command takes 1 argument 'ip_field' which is the field that contains the ip that will be passed to the context api.

#### Examples
NOTE: This assumes you have uploaded the splunk tutorial data: https://docs.splunk.com/Documentation/Splunk/9.1.1/SearchTutorial/GetthetutorialdataintoSplunk

Simple example:
```
| makeresults
| eval ip = "1.1.1.1"
| spurcontextapi ip_field="ip"
```

Basic IP Query:
```
clientip="223.205.219.67" | spurcontextapi ip_field="clientip"
```

Enrich a list of distinct IPs:
```
clientip=* | head 1000 | stats values(clientip) as "ip" | mvexpand ip | spurcontextapi ip_field="ip"
```

## Modular Input (Feed integration)
The `spurfeedingest` modular input ingests Spur feed data into a Splunk index. It requires an active Spur Feeds subscription for whichever feed type you configure.

Supported `feed_type` values:

- `anonymous` — daily IPv4 anonymous-traffic feed
- `anonymous-ipv6` — daily IPv6 anonymous-traffic feed
- `anonymous-residential` — daily IPv4 anonymous + residential feed
- `anonymous-residential-ipv6` — daily IPv6 anonymous + residential feed
- `anonymous-residential/realtime` — realtime feed (no checkpointing)
- `ipgeo` — daily IP geolocation MMDB (downloaded to a local file, not indexed as events)

The modular input takes three arguments:

- **Feed Type** — one of the values above.
- **Enable Checkpoint Files** — resume an interrupted feed from the last successful offset instead of re-ingesting. Recommended for large daily feeds with an interval configured; ignored for realtime.
- **Enable Pre-download** — download the feed to a temp file before indexing, rather than streaming it directly. Useful on slow or flaky network paths; doubles local disk usage during ingest.

During setup you can also override the target index and the ingest interval.

### Setup
1. Go to **Settings → Data inputs** **on the indexer** (in a distributed or SHC deployment the modular input only surfaces on the indexer, not on the search heads).
2. Select **Spur Feed** and click **New**.
3. Give the input a name and set the Feed Type.
4. Enable checkpointing if you want resume-on-crash behavior. Ignored for realtime feeds.
5. Enable pre-download if your connection to `feeds.spur.us` is flaky.
6. Under **More Settings**, set the target index (match your `spur_index` macro) and the ingest interval.
7. Click **Next**. Ingest starts on the next interval tick; large feeds may take several minutes to fully land.

NOTE: Monitor ingest progress in `$SPLUNK_HOME/var/log/splunk/spur.log`. You can tail the file directly or add it as a Splunk data input for searchable logs.

The modular input must be able to read the Spur API token via `storage/passwords` on the indexer. SHC password replication does NOT reach indexers, so if you configured the token only through the setup page on a search head, you will also need to configure it once on each indexer that runs the modular input.

### Examples
```
`spur_index` sourcetype=spur_feed earliest=@d | head 1000
```

## IP Geo

### Using Spur IP Geo with built in 'iplocation' command

You can enhance Splunk's built-in `iplocation` command by replacing the default IP geolocation database with Spur's more accurate and comprehensive IP geolocation data. This allows you to leverage Spur's superior IP intelligence while using Splunk's native `iplocation` command syntax.

#### Setup

1. **Download the Spur IP Geo database**: Download the latest version of the Spur IP geolocation database from:
   ```
   https://feeds.spur.us/v2/ipgeo/latest.mmdb
   ```

2. **Replace the default database using Splunk Web Interface** (Recommended):
   - Navigate to **Settings > Lookups > GeoIP lookups file**
   - Click **Choose File** and select the downloaded Spur `.mmdb` file
   - Click **Save** to upload and replace the existing GeoIP database
   - Splunk will automatically restart the necessary services

   **Alternative - Manual file replacement**:
   - Copy the downloaded `.mmdb` file to your Splunk installation directory:
     - Default location: `$SPLUNK_HOME/share/GeoLite2-City.mmdb`
     - Or configure a custom path using the `db_path` setting in `limits.conf`
   - Restart your Splunk instance to load the new database file

#### Configuration Options

To use a custom file path or name, add the following to your `limits.conf` file:

```
[iplocation]
db_path = /path/to/your/spur-ipgeo.mmdb
```

For distributed deployments, ensure the `.mmdb` file is deployed to all indexers as it's not automatically included in the knowledge bundle.

#### Example Usage

Test the enhanced IP geolocation with a simple example:

```
| makeresults 
| eval ip="8.8.8.8" 
| iplocation ip
```

This will return enhanced location data powered by Spur's IP intelligence, including more accurate city, country, region, latitude, and longitude information.

### Spur IP Geo modular input (optional)

You can also schedule the `spurfeedingest` modular input with `feed_type = ipgeo` to keep a local copy of the MMDB fresh for the `spuriplocation` command. The feed is regenerated daily, so an interval of a few hours is plenty.

#### Setup
1. Go to **Settings → Data inputs** on the indexer.
2. Select **Spur Feed** and click **New**.
3. Give the input a name and set Feed Type to `ipgeo`.
4. Under **More Settings**, set the ingest interval (a few hours is sufficient for a daily-regenerated feed).
5. Click **Next**.

The `spuriplocation` command will auto-refresh the MMDB on demand if it is older than 24 hours, so scheduling this input is optional — it just lets the refresh happen during a quiet cron window instead of on the first search of the day.

### Spur IP Location Command

The app includes a `spuriplocation` command that enriches events with comprehensive IP geolocation data from the Spur IP Geo MMDB. This command can be used as an enhanced replacement for Splunk's built-in `iplocation` command, providing more detailed geographic and network information.

**MMDB management**: the command auto-refreshes the local MMDB on demand when it is missing or older than 24 hours (matches the daily upstream feed regeneration cadence). The refresh is performed by a privileged REST handler under system auth, so non-admin users can trigger it without holding `list_storage_passwords`. You do not need to configure the ipgeo modular input for `spuriplocation` to work — it is only useful for pre-warming the MMDB on a schedule.

#### Basic Usage

```
| makeresults 
| eval ip="1.1.1.1" 
| spuriplocation ip_field=ip
```

#### Options

- `ip_field` (required): The field containing the IP address to look up
- `fields` (optional): Comma-separated list of fields to include in the output. If not specified, all fields are included.

#### Available Fields

The `spuriplocation` command supports the following fields. You can use either the short field names or full field names when specifying the `fields` option:

| Short Name | Full Field Name | Description |
|------------|-----------------|-------------|
| `country` | `spur_location_country` | Country name (English) |
| `country_iso` | `spur_location_country_iso` | ISO country code (e.g., "US") |
| `country_geoname_id` | `spur_location_country_geoname_id` | GeoNames database ID for country |
| `subdivision` | `spur_location_subdivision` | State/province name (English) |
| `subdivision_geoname_id` | `spur_location_subdivision_geoname_id` | GeoNames database ID for subdivision |
| `city` | `spur_location_city` | City name (English) |
| `city_geoname_id` | `spur_location_city_geoname_id` | GeoNames database ID for city |
| `continent` | `spur_location_continent` | Continent name (English) |
| `continent_code` | `spur_location_continent_code` | Continent code (e.g., "NA") |
| `continent_geoname_id` | `spur_location_continent_geoname_id` | GeoNames database ID for continent |
| `registered_country` | `spur_location_registered_country` | Registered country name (English) |
| `registered_country_iso` | `spur_location_registered_country_iso` | Registered country ISO code |
| `registered_country_geoname_id` | `spur_location_registered_country_geoname_id` | GeoNames ID for registered country |
| `latitude` | `spur_location_latitude` | Latitude coordinate |
| `longitude` | `spur_location_longitude` | Longitude coordinate |
| `accuracy_radius` | `spur_location_accuracy_radius` | Accuracy radius in kilometers |
| `timezone` | `spur_location_timezone` | Timezone (e.g., "America/Chicago") |
| `as_number` | `spur_as_number` | Autonomous System number |
| `as_organization` | `spur_as_organization` | Autonomous System organization name |
| `error` | `spur_error` | Error message (if any) |

#### Usage Examples

**Basic IP lookup with all fields:**
```
| makeresults 
| eval ip="8.8.8.8" 
| spuriplocation ip_field=ip
```

**Get only basic location information:**
```
| makeresults 
| eval ip="8.8.8.8" 
| spuriplocation ip_field=ip fields="country,subdivision,city"
```

**Get coordinates only:**
```
| makeresults 
| eval ip="8.8.8.8" 
| spuriplocation ip_field=ip fields="latitude,longitude"
```

**Get network information:**
```
| makeresults 
| eval ip="8.8.8.8" 
| spuriplocation ip_field=ip fields="as_number,as_organization"
```

**Enrich existing log data:**
```
index=web_logs 
| head 1000 
| spuriplocation ip_field=client_ip fields="country,city,latitude,longitude"
```

**Get detailed country information with IDs:**
```
| makeresults 
| eval ip="8.8.8.8" 
| spuriplocation ip_field=ip fields="country,country_iso,country_geoname_id"
```

**Mixed field specification (short and full names):**
```
| makeresults 
| eval ip="8.8.8.8" 
| spuriplocation ip_field=ip fields="country,spur_location_latitude,as_number"
```

## Schema

### Search Commands
The following fields are returned from the Context API and added to enriched events by `spurcontextapi` / `spurcontextapigen`:
```
"spur_ip"
"spur_as_number"
"spur_as_organization"
"spur_organization"
"spur_infrastructure"
"spur_client_behaviors"
"spur_client_concentration_country"
"spur_client_concentration_city"
"spur_client_concentration_geohash"
"spur_client_concentration_density"
"spur_client_concentration_skew"
"spur_client_countries"
"spur_client_spread"
"spur_client_proxies"
"spur_client_count"
"spur_client_types"
"spur_location_country"
"spur_location_state"
"spur_location_city"
"spur_services"
"spur_tunnels_type"
"spur_tunnels_anonymous"
"spur_tunnels_operator"
"spur_risks"
"spur_error"
```

### Feed
Feed events carry the upstream Spur JSON schema (shown below) with three fields stamped on by the modular input: `feed_identifier` (the feed-file generation ID), `feed_date` (YYYYMMDD), and `feed_type` (one of the `feed_type` values from the Modular Input section).

Events are indexed under sourcetype `spur_feed`. Splunk's event `_time` is derived from `feed_date` (via `TIME_PREFIX`/`TIME_FORMAT` in `props.conf`), so historical replays land on the correct day rather than on ingest wall-clock time.

The following fields are extracted as **indexed fields** at ingest time — meaning `| tstats count where sourcetype=spur_feed by <field>` reads directly from the TSIDX and is sub-second regardless of feed size:

- `ip`
- `feed_type`
- `infrastructure`
- `tunnel_operator` (multi-valued — one entry per tunnel)
- `anonymous_tunnel_operator` (multi-valued — only operators from tunnels with `anonymous: true`)

Every other field in the feed JSON (including the nested `client`, `location`, `as`, `tunnels`, `risks`, etc.) is available via search-time JSON extraction (`KV_MODE = json`).

The underlying Spur JSON schema:

```
{
  "type": "object",
  "description": "IP Context Object",
  "additionalProperties": false,
  "properties": {
    "ip": {
      "type": "string"
    },
    "as": {
      "type": "object",
      "properties": {
        "number": {
          "type": "integer"
        },
        "organization": {
          "type": "string"
        }
      }
    },
    "organization": {
      "type": "string"
    },
    "infrastructure": {
      "type": "string"
    },
    "client": {
      "type": "object",
      "properties": {
        "behaviors": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string"
          }
        },
        "concentration": {
          "type": "object",
          "properties": {
            "country": {
              "type": "string"
            },
            "state": {
              "type": "string"
            },
            "city": {
              "type": "string"
            },
            "geohash": {
              "type": "string"
            },
            "density": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "skew": {
              "type": "integer"
            }
          }
        },
        "countries": {
          "type": "integer"
        },
        "spread": {
          "type": "integer"
        },
        "proxies": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string"
          }
        },
        "count": {
          "type": "integer"
        },
        "types": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "type": "string"
          }
        }
      }
    },
    "location": {
      "type": "object",
      "properties": {
        "country": {
          "type": "string"
        },
        "state": {
          "type": "string"
        },
        "city": {
          "type": "string"
        }
      }
    },
    "services": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "tunnels": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "anonymous": {
            "type": "boolean"
          },
          "entries": {
            "type": "array",
            "uniqueItems": true,
            "items": {
              "type": "string"
            }
          },
          "operator": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "exits": {
            "type": "array",
            "uniqueItems": true,
            "items": {
              "type": "string"
            }
          }
        },
        "required": ["type"]
      }
    },
    "risks": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string"
      }
    }
  },
  "required": ["ip"]
}
```
