# Google Threat Intelligence App for Splunk

## Overview

Google Threat Intelligence automatically enriches your Splunk logs with curated and crowdsourced threat intelligence data. It allows you to contextualize IoCs (files/hashes, domains, IP addresses, URLs) and confirm malicious intent/discard false positives. The context added includes: Gogle Threat Intelligence score, security industry reputation, severity, threat categories and labels, associated campaigns and threat actors, etc.

## Compatibility Matrix

* Unix OS
* Splunk version: 9.4.x, 9.3.x ,9.2.x, 9.1.x, 9.0.x
* Python version: Python3
* Enterprise security: > 8.0.0

## Installation

GTI app can be installed through UI as is shown below:

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `TA-gti-app` installation file.
4. Click on `Upload`.
5. Restart Splunk.

By the limitations of Splunk at the time of reading the API key from indexers **GTI app will always run on the Search Head** so the add-on it only needs to be installed on the Search Head as usual, not on the indexers nor in the forwarders.

## Configuration

Configuring GTI:

### Proxy

Configure proxy settings:

||||
|---|---|---|
| Enable Proxy   | Optional  | To enable or disable the proxy |
| Proxy Host     | Mandatory | Host or IP of the proxy server |
| Proxy Port     | Mandatory | Port for proxy server          |
| Proxy Username | Optional  | Username of the proxy server   |
| Proxy Password | Optional  | Password of the proxy server   |

### Logging

Configure the Logging level:

1. Navigate to the `Configuration` tab.
2. Click on the `Logging` tab.
2. Select the log level click on `Save`.

### General Settings

Configure basic values for the correct operation of the app:

* `GTI API Key`:
Your API key can be found at https://www.virustotal.com/gui/my-apikey (sign in required). As a premium user you can also generate service accounts in your group profile.

To test the connection you can execute this Splunk query after save the API key
```
| makeresults
| eval testip="8.8.8.8"
| gti ip=testip
```

* `Lookup table expiration (days)`:
Elements stored in the lookup tables (iocs, campaigns, actors) will be removed when the last time they are seen in the events exceeds this value.

### Correlation Settings

Configure values which will affect to the automatic correlation and the data shown in the dashboards:

* `Enable automatic correlation`:
Enable this to automatically correlate IoCs found in your events with Google Threat Intelligence context. GTI enrichment will be scheduled every 30 minutes and findings will be summarized in the dashboards.

* `Data freshness (days)`:
Optimizes your Google Threat Intelligence API quota. IoC enrichment will be retrieved from the local cache, instead of performing an API call, whenever the cached analysis' age is lower than this value.

* `Names for indexes`:
Automatic correlation and dashboards will use this list of indexes to perform the search of the events in your catalog.

* `Fields names [Hash, URL, Domain, IP]`:
Saved searches will perform automatic correlation using these field names to find IoCs in your events. Empty field disables that automatic correlation specifically.

## Commands

The app provides a main command `gti` to correlate IoCs found in your events with the Google Threat Intelligence information, also provides other commands to keep up-to-date the enrichment dataset:

* `gti`:

Adding the command to a SPL query will enrich events which contains the fieldname passed as argument, adding new fields to the event in search time with the prefix `gti_`, the command admits the following parameters:

| Parameter | Optional | Description |
| --- | --- | --- |
| hash \| domain \| url \| ip | No | event fieldname |
| nocache | Yes | Boolean lowercase value [true \| false] |

Query examples:

```
sourcetype=access_* status=400 method=POST
| gti ip=clientip
```
Correlate `clientip` field of access log events.

```
sourcetype=access_* status=400 method=POST
| gti ip=clientip nocache=true
```
Forcing to get the enrichment data from Google Threat Intelligence instead of the lookup tables.

```
sourcetype=access_* status=400 method=POST
| gti ip=clientip nocache=true
| search gti_detections > 10
```
Get correlated events where detections are more than ten.

### Additional commands

The following additional commands are executed periodically by the saved searches, it rarely will be necessary to execute manually.

* `gtideleteiocs`:

Delete IoCs older than 30 days by default. It can be also executed manually given a table with `gti_id` field as input and/or with some parameter to perform a more selective delete:

| Parameter | Optional | Description |
| --- | --- | --- |
| lookups | Yes | delete iocs of specific types (hash, domain, ip, url) |
| ttl | Yes | delete iocs older than this value (days) |

Query examples:

```
| makeresults | gtideleteiocs
```
Delete all IoCs.

```
| makeresults | gtideleteiocs ttl=30
```
Delete all IoCs older than 30 days.

```
| inputlookup gti_url_cache | search gti_detections < 10 | gtideleteiocs lookups=url ttl=5
```
Delete URLs with less than 10 detections and older than 5 days.

```
| inputlookup gti_file_cache | search gti_tags=*cve-* | gtideleteiocs lookups=hash
```
Delete hashes with CVE tags.

* `gtiadversaryupdate`:

Keep up-to-date campaigns and threat actors.

* `gtimitreupdate`:

Extract MITRE information of each hash and keep up-to-date the dashboard.

## Saved Searches

The app provides tool for creating and managing saved searches that will correlate your events and will keep the data up-to-date in an unmanaged way.

The saved searches are in charge of the automatic correlation, they will inspect new events in the last 15 minutes contained only in the indexes configured in the **Correlation Settings**.

* `GTI Clean Lookups`

This saved search will remove IoCs from the lookup tables older than the value configured in the **Correlation Settings**, by default 30 days.

* `GTI Keep Adversary Lookups Updated`
* `GTI Keep MITRE Lookup Updated`

The above saved searches keep up-to-date the data shown in the Vulnerability, Adversary and MITRE dashboards.

## Lookup tables

The app creates several lookup tables to store the enrichment data and to feed the dashboards:

* `gti_file_cache`: store the Google Threat Intelligence enrichment data for files
* `gti_domain_cache`: store the Google Threat Intelligence enrichment data for domains
* `gti_url_cache`: store the Google Threat Intelligence enrichment data for urls
* `gti_ip_cache`: store the Google Threat Intelligence enrichment data for ips
* `gti_collection_cache`: store the Google Threat Intelligence collections for flagged iocs (Campaigns and malware toolkits)
* `gti_mitre_cache`: store the MITRE information for files
* `gti_ignore_cache`: store the IoCs to be ignored in the dashboards

All of the above tables can be inspected running a search query like this: `| inputlookup gti_file_cache`.

### Ignoring specific IoCs

IoCs can be ignored adding them to a specific lookup table, preventing them from appearing in the dashboards, this can be useful if you have a well-known or false positives IoCs.

You can manage those IoCs with these queries:
* To add a single IoC:
```
| makeresults | eval gti_id="eed999fcf63eaa5dd73fac49a7d49d64fe19b945eb30730da4ab026d78746559", gti_type="hash"
| outputlookup append=true gti_ignore_cache
```
* To add multiple IoCs:
```
| makeresults format=csv data="gti_id, gti_type
eed999fcf63eaa5dd73fac49a7d49d64fe19b945eb30730da4ab026d78746559,hash
google.com,domain
https://www.google.com,url
127.0.0.1,ip"
| outputlookup append=true gti_ignore_cache
```
* To remove duplicate IoCs:
```
| inputlookup gti_ignore_cache | dedup gti_id gti_type | outputlookup gti_ignore_cache
```

## Troubleshooting

### Empty dashboards

* Saved searches only correlate events created in the last 30 minutes, if you want to do a backfill to start showing data perform a search adding the command **gti** as described above.

* Check lookup tables have information, if not try to execute the `gti` command manually over a search of events.

* Check the index names in the **Correlation Settings**.

### Configuration tab is not loading

* Some specific versions of Splunk may have some problems reading the passwords.conf file, leading to Configuration tab not loading. To solve this you have to delete the passwords.conf file and try again, you can found it accessing to your Splunk instance in the following path `$SPLUNK_HOME/etc/apps/TA-gti-app/local/passwords.conf`.

### I cannot see the correlations settings.

The correlations settings is now on its own page, click on the Configuration menu and select the Correlations menu entry.

**Attention Splunk 9.3 users**. This version has an acknowledged bug by which the add-on navigation bar does not refresh after an add-on upgrade. To overcome this, please, open the browser developer tools, locate the local storage (In Chrome: Application tab -> Local Storage left menu) filter by `TA-gti-app`, remove the `splunk-appnav:TA-gti-app` entry and refresh the page.

### Check that inputs are ingesting

You can run the following searches to see if inputs are working correctly.

**IoCStream:**
```
index="_internal" source=*ta_gti_app_ioc_stream* Ingested
```
**Threat Lists:**
```
index="_internal" source=*ta_gti_app_threat_lists* Ingested
```
**CVEs:**
```
index="_internal" source=*ta_gti_app_cve* Ingested
```

This will return log entries with the following format:
```
Collection finished.Total time: 5 seconds. Ingested: 21.
```

## Support

* Email [contact@virustotal.com](contact@virustotal.com)

* When contacting to support, please indicate your Google Threat Intelligence version, Splunk version, if Enterprise or Cloud, and some screenshots and logs by executing:
```
index=_internal | search source="*ta_gti_app*"
```
To get all logs stored by GTI.

```
index=_internal log_level=ERROR
```
To get all error logs.

### Migration from VT4Splunk

This add-on has been designed to mimic the behavior of VT4Splunk as closely as possible to facilitate migration from it.

* The main enrichment command is called `gti` (former vt4splunk).
* The commands `vtdeleteiocs`, `vtadversaryupdate`, `vtvulnerabilitiesupdate`, `vtmitreupdate` are now called `gtideleteiocs`, `gtiadversaryupdate`, `gtivulnerabilitiesupdate`, `gtimitreupdate`.

**Copyright (c) 2024 Google. All rights reserved.**
