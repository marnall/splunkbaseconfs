# Technitium DNS Add-on

## I. Introduction

This technology add-on ("this app") provides source typing and field extraction for [Technitium DNS](https://technitium.com/dns/) (TDNS) servers running on Linux. It also comes with a dashboard that summarizes the TDNS environment metrics gathered from logs.

## II. Prerequisites

There are several requirements listed below for this app. These instructions assume the Splunk administrator is familiar with Splunk app installation and configuration. The installation of TDNS is not described here and these instructions assume that TDNS is up and running.

### II.A. Basic requirements

1. The TDNS instances you wish to monitor must be installed on Linux.
1. If not already, the TDNS instances you wish to monitor will have logging to a file enabled in the TDNS UI.

### II.B. Dashboard requirements

If not already,

1. The Technitium DNS *Log Exporter* app will be installed.
1. The [*Splunk Common Information Model*](https://splunkbase.splunk.com/app/1621) app will be installed on your search heads.
1. The Network Resolution (DNS) data model will be accelerated.

## III. Architecture

### III.A. TDNS hosts

This app was written to support TDNS on a Linux host. (It has not been tested with container implementations.) These instructions assume that:

- TDNS is configured to log to a file in the default location, i.e. `/var/log/technitium/dns/`.
- If used, the LogExporter app is configured to write DNS query logs to `/var/log/technitium/dns/dns.json`.
- A Splunk Universal Forwarder is installed on the TDNS host and configured to send events to indexers as appropriate.

### III.B. Splunk forwarder

This app must be deployed to the Universal Forwarder, either manually or through a deployment server.

This app configures inputs on the TDNS host that collect TDNS logs and forwards them with the appropriate metadata to indexers.

### III.C. Splunk indexers

This app must be installed on indexers or heavy forwarders that receive TDNS events from Universal Forwarders.

This app parses the log events and types them based on content.

### III.D. Splunk search heads

This TA must be installed on search heads for field extraction, model acceleration, and the dashboard. It can be deployed to search head clusters from a deployer.

A scheduled search updates a lookup containing authoritative zones to support the dashboard.

## IV. Installation

### IV.A. Prepare the TDNS host

#### IV.A.1. Enable logging to a file

Login to your TDNS server's UI as an administrator. Go to the *Settings* tab. (On a TDNS cluster, make sure that *Cluster* is not selected, but rather one of the nodes.)

Within *Settings*, select the *Logging* tab. For the *Enable Logging To* section, select *File*. For the *Logging Options* section, you can leave *Log All Queries* off if you install the *Log Exporter* in the next step to provide JSON query logs. Otherwise, select *Log All Queries* if you want to send queries to the plain TDNS log file. (The built-in query logging provides less information than JSON logging.) 

==If you want this app's dashboard to work, you must enable JSON logging in the next step.== Having both *Log All Queries* and JSON logging enabled will produce duplicate query events.

Make sure that *Log Folder Path* is set to `/var/log/technitium/dns`.

Click *Save Settings* at the bottom of the page.

Repeat this for each TDNS instance. On a cluster, the configuration can be done for each node from one UI by selecting each host from the drop-down list in turn. The drop-down value *Cluster* does not have a *Logging* config page -- each host must be configured independently.

#### IV.A.2. Install and configure the *Log Exporter* app

Login to your TDNS server's UI as an administrator. Go to the *Apps* tab and click on the *App Store*. Find *Log Exporter* in the list of apps and select *Install*. (If you do not find it in the list, it may already be installed.)

Now in the list of installed apps, find *Log Exporter*. Click on its *Config* button on the right side. Edit the `dnsApp.config` file such that:

```
    "enableEdnsLogging": true,
```
and the file section looks like this:

```
    "file": {
        "path": "/var/log/technitium/dns/dns.json",
        "enabled": true
    },
```
Click on *Save* when complete. TDNS should immediately begin writing JSON query logs.

If you installed on a cluster member, the entire cluster should now have the *Log Exporter* app installed and configured.

### IV.B. Splunk servers

Various Splunk components must be configured to provide TDNS log handling.

This app can be installed from Splunkbase directly, by downloading the package from Splunkbase and installing from the package file, or by extracting the app files from the package and copying the `TA_technitium_dns` directory to the appropriate location.

#### IV.B.1. Stand-alone Splunk

If you have a single Splunk Enterprise instance, install this app on that server.

#### IV.B.2. Distributed Splunk

If you have a distributed Splunk environment, you must install this app on multiple Splunk components, including indexers and search heads. See the following sections for details.

##### IV.B.2.a. Indexers

If you have stand-alone indexers, install this app on each one that will receive TDNS logs.

If you have clustered indexers, unpack and copy this app to the cluster manager's `$SPLUNK_HOME/etc/manager-apps` directory and apply the cluster bundle. This will install this app to all indexers in the cluster.

##### IV.B.2.b. Search heads

Make sure the [*Splunk Common Information Model*](https://splunkbase.splunk.com/app/1621) app is installed on each search head. This is required for the dashboard to function.

If you have stand-alone search heads, install this app on each search head.

If you have clustered search heads, unpack and copy this app to the cluster deployer's `$SPLUNK_HOME/etc/shcluster/apps` directory. Apply the bundle to distribute this app to the search heads in the cluster.

#### IV.B.3. Create an index (optional)

Your TDNS events will go into the default index (usually `main`) unless you specify otherwise in the forwarder configuration. If you want to create an index specifically for TDNS events, configure it on your indexer tier before you install this app on forwarders.

#### IV.B.4 Data model acceleration (optional, recommended)

After this app is installed on the search heads and the index preferred for TDNS events exists, override the `cim_Network_Resolution_indexes` macro (provided by the *Splunk Common Information Model*) to include the TDNS events index. By default it is "`()`"; set it to "`(index=tdns)`" or whatever your chosen index is. This is done in Splunk *Settings*, *KNOWLEDGE*, *Advanced Search*, and *Search macros*.

When the macro is set, go to Splunk *Settings*. Under *KNOWLEDGE*, select *Data models*. Go to the *Network Resolution (DNS)* data model, select *Edit*, then *Edit Acceleration*. Make sure the *Accelerate* checkbox is checked. You can adjust the *Summary Range* for as long as you wish the dashboard to be functional for historical data.

The dashboard will not work unless the data model is accelerated.

This app's dashboard uses the macro `technitium_dns_indexes` to find its events. This macro is set to `cim_Network_Resolution_indexes` by default. You do not have to change it; once you set the `cim_Network_Resolution_indexes` macro, searches in this app will work. If you have multiple indexes that contain DNS events, you can optimize the dashboard searches by overriding the `technitium_dns_indexes` macro to point to the TDNS event index(es) exclusively.

### IV.C. Forwarders

#### IV.C.1. Install this app to TDNS hosts

Each TDNS host must have a [forwarder installed](https://help.splunk.com/en/?resourceId=Forwarder_Forwarder_Installanixuniversalforwarder) and you must install this app on the forwarder on all TDNS hosts.

If you have a Splunk [deployment server](https://help.splunk.com/en/?resourceId=Splunk_Updating_Updateconfigurations), unpack and copy this app to the `$SPLUNK_HOME/etc/deployment-apps` directory. Configure a *server class* on your deployment server associated with your TDNS hosts. Add this app to the class's application list. Set this application to restart the forwarder upon update. This will install the app on each TDNS host.

If you have some other way of installing apps to forwarders (e.g. Ansible, manually, etc.), use that method.

If you created an index specifically for TDNS events, override the default index for the TDNS inputs before you deploy your app. Create a `./local/inputs.conf` and change the index values. For example:

```
    [monitor:///var/log/technitium/dns/dns.json*]
    index = tdns

    [monitor:///var/log/technitium/dns/*.log]
    index = tdns
```

#### IV.C.2. Configure `logrotate` on each TDNS host

The JSON logs written by the *Log Exporter* app are not rotated -- they merely accumulate in one file. In order to manage them, configure the Linux utility `logrotate` on each TDNS host.

There is a `logrotate` configuration file in this app at `./package/logrotate/technitium-dns`. Copy this file to your `logrotate` configuration directory on each TDNS host, e.g.:

> `sudo cp /opt/splunkforwarder/etc/apps/TA_technitium_dns/package/logrotate/technitium-dns /etc/logrotate.d/`

The provided configuration will rotate the file daily and compress the previous day's logs. The configuration file is set to keep fifteen days of logs. You can change these settings to match your preferences.

Note that the *copytruncate* method does not work for TDNS *Log Exporter*, so `logrotate` renames the existing file and creates a new `dns.json` file. For logging to continue, `logrotate` restarts TDNS.

## V. Use Cases

### V.A. Show all TDNS events

> ``` `technitium_dns_indexes` sourcetype=technitium:dns:* ```

>> Returns all TDNS events.

### V.B. List DNS queries

> ``` `technitium_dns_indexes` sourcetype=technitium:dns:json | table _time src dest query_type query answer ```

>> Returns a table of queries using JSON events. (JSON-based queries require that you turned on JSON logging with the TDNS *Log Exporter* app.) The output includes the client IP and the TDNS server queried.

### V.C. List DNS queries for a specific domain

> ``` `technitium_dns_indexes` sourcetype=technitium:dns:json query IN (google.com, *.google.com) | table _time src query```

>> Returns a table of queries matching the domain `google.com`.

### V.D. List DNS clients by usage

> ``` `technitium_dns_indexes` sourcetype=technitium:dns:json | stats count BY src | lookup dnslookup clientip AS src OUTPUT clienthost as hostname```

>> Returns a table of DNS clients in descending order by query count, with a reverse DNS lookup of the client IP that adds the hostname.

## VI. Upgrade Instructions

A new version can be installed over the previous version unless otherwise documented below.

### VI.A. v0.1.0

The initial release.

### VI.B. v0.1.1

A log ingestion fix and a dashboard update.

- The *initCrcLength* for the file inputs was increased from the default to 2048 bytes. Sometimes Splunk
reported "File will not be read, seekptr checksum did not match (file=/var/log/technitium/dns/dns.json).
Last time we saw this initcrc, filename was different." **This change will re-ingest all your DNS logs
if you have v0.1.0 installed.** To avoid this, move ingested files out of the log directory before you push
this update.

- Some dashboard searches did not have automatic refresh turned on. These have been updated. Updates 
intervals have also been changed to a minimum of 2 minutes.

## VII. Reference

The following is a summary of items and knowledge objects defined in this app.

### VII.A. Inputs

There are two input stanzas in `./default/inputs.conf`:

> `[monitor:///var/log/technitium/dns/dns.json*]`
>> Ingests the JSON query logs generated by the TDNS *Log Exporter* app.

> `[monitor:///var/log/technitium/dns/*.log]`
>> Ingests the normal text logs generated by TDNS.

### VII.B. Source types

> `technitium:dns:json`

>> Assigned to events ingested from the JSON input. These are exclusively DNS query events.

> `technitium:dns`

>> Assigned to plain-text logs before differentiation by `TRANSFORMS`. Events with this source type are assigned a more specific source type, as detailed in the following sections. You should not see this source type in the index. (If you do, please report the events to the [author](mailto:fwayne@frankwayne.com).)

> `technitium:dns:query`

>> Assigned to DNS query events found in plain-text logs. If you enable JSON logging with the *Log Exporter* app, you should turn off DNS query logging in TDNS and thus you will not find these logs in the index. These logs do not contain as much information about queries as do the JSON events.

>> `[2026-07-20 18:06:04 UTC] [192.168.0.49:62421] [UDP] QNAME: clients4.google.com; QTYPE: A; QCLASS: IN; RCODE: NoError; ANSWER: [clients.l.google.com., 142.251.41.78]`

> `technitium:dns:zone`

>> Assigned to DNS query events found in plain-text logs *for zone operations*. These are formatted differently from other query events. If you enable JSON logging with the *Log Exporter* app, you should turn off DNS query logging in TDNS and thus you will not find these logs in the index. These logs do not contain as much information about queries as do the JSON events.

>> `[2026-07-20 18:03:55 UTC] [192.168.0.66:47758] [TCP] QNAME: cluster-catalog.tdns.example.org; QTYPE: IXFR; QCLASS: IN; TSIG KeyName: cluster-catalog.tdns.example.org; TSIG Algo: hmac-sha256; TSIG Error: NoError; RCODE: NoError; ANSWER: [invalid. invalid. 11 300 60 604800 900]`

> `technitium:dns:zonefile`

>> Assigned to zone file saves for authoritative zones.

>> `[2026-07-29 14:41:29 UTC] Saved zone file for domain: 0.168.192.in-addr.arpa`

> `technitium:dns:server`

>> Assigned to server events like zone transfers, refreshes, and updates.

>> `[2026-07-29 14:42:40 UTC] DNS Server successfully checked for '_msdcs.example.org' Secondary zone update from: 192.168.0.9`

> `technitium:dns:admin`

>> Assigned to TDNS cluster events like logins, and configuration requests, synchronizations, and transfers.

>> `[2026-07-29 05:53:16 UTC] [192.168.0.65:58524] [admin] Secondary node 'tdns1.tdns.example.org (192.168.0.65)' details were updated successfully.`

### VII.C. Lookups

> `technitium_dns_authoritative_zones`

>> A lookup table containing all authoritative zones discovered in the last day, based on zone file log activity. This is used by the dashboard.

### VII.D. Saved searches

> `technitium_dns_authoritative_zones_update`

>> A scheduled report that updates the `technitium_dns_authoritative_zones` lookup. It runs every hour.

### VII.E. Macros

> `technitium_dns_indexes`

>> A macro used by the dashboard. This is set to `cim_Network_Resolution_indexes` by default, but can be set to a more specific list of indexes to improve dashboard search performance.

### VII.F. Dashboards

> `technitium_dns_dashboard`

>> A dashboard that displays TDNS statistics.
