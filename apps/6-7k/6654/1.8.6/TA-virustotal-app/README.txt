# VT4Splunk, official VirusTotal app for Splunk

## Overview

VT4Splunk automatically enriches your Splunk logs with threat intelligence coming from VirusTotal. It allows you to contextualize IoCs (files/hashes, domains, IP addresses, URLs) and confirm malicious intent/discard false positives. The context added includes: security industry reputation, severity, threat categories and labels, associated campaigns and threat actors, etc.

## Compatibility Matrix

* Unix OS
* Splunk version: 9.4.x, 9.3.x, 9.2.x, 9.1.x, 9.0.x
* Python version: Python3

## Installation

VT4Splunk app can be installed through UI as is shown below:

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `TA-virustotal-app` installation file.
4. Click on `Upload`.
5. Restart Splunk.

By the limitations of Splunk at the time of reading VT API key from indexers **VT4Splunk app will always run on the Search Head** so the add-on it only needs to be installed on the Search Head as usual, not on the indexers nor in the forwarders.

## Configuration

Configuring VT4Splunk:

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

* `VirusTotal API Key`:
Your API key can be found at https://www.virustotal.com/gui/my-apikey (sign in required). As a premium user you can also generate service accounts in your group profile.

To test the connection you can execute this Splunk query after save the API key
```
| makeresults
| eval testip="8.8.8.8"
| vt4splunk ip=testip
```

* `Lookup table expiration (days)`:
Elements stored in the lookup tables (iocs, campaigns, actors) will be removed when the last time they are seen in the events exceeds this value.

### Correlation Settings

Configure values which will affect to the automatic correlation and the data shown in the dashboards:

* `Enable automatic correlation`:
Enable this to automatically correlate IoCs found in your events with VirusTotal context. VirusTotal enrichment will be scheduled every 30 minutes and findings will be summarized in the dashboards.

* `Data freshness (days)`:
Optimizes your VirusTotal API quota. IoC enrichment will be retrieved from the local cache, instead of performing an API call, whenever the cached analysis' age is lower than this value.

* `Names for indexes`:
Automatic correlation and dashboards will use this list of indexes to perform the search of the events in your catalog.

* `Fields names [Hash, URL, Domain, IP]`:
Saved searches will perform automatic correlation using these field names to find IoCs in your events. Empty field disables that automatic correlation specifically.

## Commands

The app provides a main command `vt4splunk` to correlate IoCs found in your events with the VirusTotal information, also provides other commands to keep up-to-date the enrichment dataset:

* `vt4splunk`:

Adding the command to a SPL query will enrich events which contains the fieldname passed as argument, adding new fields to the event in search time with the prefix `vt_`, the command admits the following parameters:

| Parameter | Optional | Description |
| --- | --- | --- |
| hash \| domain \| url \| ip | No | event fieldname |
| nocache | Yes | Boolean lowercase value [true \| false] |

Query examples:

```
sourcetype=access_* status=400 method=POST
| vt4splunk ip=clientip
```
Correlate `clientip` field of access log events.

```
sourcetype=access_* status=400 method=POST
| vt4splunk ip=clientip nocache=true
```
Forcing to get the enrichment data from VirusTotal instead of the lookup tables.

```
sourcetype=access_* status=400 method=POST
| vt4splunk ip=clientip nocache=true
| search vt_detections > 10
```
Get correlated events where detections are more than ten.

### Additional commands

The following additional commands are executed periodically by the saved searches, it rarely will be necessary to execute manually.

* `vtdeleteiocs`:

Delete IoCs older than 30 days by default. It can be also executed manually given a table with `vt_id` field as input and/or with some parameter to perform a more selective delete:

| Parameter | Optional | Description |
| --- | --- | --- |
| lookups | Yes | delete iocs of specific types (hash, domain, ip, url) |
| ttl | Yes | delete iocs older than this value (days) |

Query examples:

```
| makeresults | vtdeleteiocs
```
Delete all IoCs.

```
| makeresults | vtdeleteiocs ttl=30
```
Delete all IoCs older than 30 days.

```
| inputlookup vt_url_cache | search vt_detections < 10 | vtdeleteiocs lookups=url ttl=5
```
Delete URLs with less than 10 detections and older than 5 days.

```
| inputlookup vt_file_cache | search vt_tags=*cve-* | vtdeleteiocs lookups=hash
```
Delete hashes with CVE tags.

* `vtadversaryupdate`:

Keep up-to-date campaigns and threat actors.

* `vtvulnerabilitiesupdate`:

Keep up-to-date CVEs.

* `vtmitreupdate`:

Extract MITRE information of each hash and keep up-to-date the dashboard.

## Saved Searches

The app provides tool for creating and managing saved searches that will correlate your events and will keep the data up-to-date in an unmanaged way.

The saved searches are in charge of the automatic correlation, they will inspect new events in the last 15 minutes contained only in the indexes configured in the **Correlation Settings**.

* `VirusTotal Clean Lookups`

This saved search will remove IoCs from the lookup tables older than the value configured in the **Correlation Settings**, by default 30 days.

* `VirusTotal Keep Adversary Lookups Updated`
* `VirusTotal Keep CVE Lookup Updated`
* `VirusTotal Keep MITRE Lookup Updated`

The above saved searches keep up-to-date the data shown in the Vulnerability, Adversary and MITRE dashboards.

## Lookup tables

The app creates several lookup tables to store the enrichment data and to feed the dashboards:

* `vt_file_cache`: store the VirusTotal enrichment data for files
* `vt_domain_cache`: store the VirusTotal enrichment data for domains
* `vt_url_cache`: store the VirusTotal enrichment data for urls
* `vt_ip_cache`: store the VirusTotal enrichment data for ips
* `vt_collection_cache`: store the VirusTotal collections for flagged iocs (Campaigns and malware toolkits)
* `vt_threat_actor_cache`: store the VirusTotal threat actors for flagged iocs
* `vt_cve_cache`: store the CVEs extracted from file enrichment data
* `vt_mitre_cache`: store the MITRE information for files
* `vt_ignore_cache`: store the IoCs to be ignored in the dashboards

All of the above tables can be inspected running a search query like this: `| inputlookup vt_file_cache`.

### Ignoring specific IoCs

IoCs can be ignored adding them to a specific lookup table, preventing them from appearing in the dashboards, this can be useful if you have a well-known or false positives IoCs.

You can manage those IoCs with these queries:
* To add a single IoC:
```
| makeresults | eval vt_id="eed999fcf63eaa5dd73fac49a7d49d64fe19b945eb30730da4ab026d78746559", vt_type="hash"
| outputlookup append=true vt_ignore_cache
```
* To add multiple IoCs:
```
| makeresults format=csv data="vt_id, vt_type
eed999fcf63eaa5dd73fac49a7d49d64fe19b945eb30730da4ab026d78746559,hash
google.com,domain
https://www.google.com,url
127.0.0.1,ip"
| outputlookup append=true vt_ignore_cache
```
* To remove duplicate IoCs:
```
| inputlookup vt_ignore_cache | dedup vt_id vt_type | outputlookup vt_ignore_cache
```

## Troubleshooting

### Empty dashboards

* Saved searches only correlate events created in the last 30 minutes, if you want to do a backfill to start showing data perform a search adding the command **vt4splunk** as described above.

* Check lookup tables have information, if not try to execute the `vt4splunk` command manually over a search of events.

* Check the index names in the **Correlation Settings**.

### I cannot see the correlations settings.

The correlations settings is now on its own page, click on the Configuration menu and select the Correlations menu entry.

**Attention Splunk 9.3 users**. This version has an acknowledged bug by which the add-on navigation bar does not refresh after an add-on upgrade. To overcome this, please, open the browser developer tools, locate the local storage (In Chrome: Application tab -> Local Storage left menu) filter by `TA-virustotal-app`, remove the `splunk-appnav:TA-virustotal-app` entry and refresh the page.

## Support

* Email [contact@virustotal.com](contact@virustotal.com)

* When contacting to support, please indicate your VT4Splunk version, Splunk version, if Enterprise or Cloud, and some screenshots and logs by executing:
```
index="_internal" | search source="*ta_virustotal_app*"
```
To get all logs stored by VT4Splunk.

```
index="_internal" | search "virustotal" "ERROR"
```
To get all logs stored by Splunk about VT4splunk.

**Copyright (c) 2024 Google. All rights reserved.**


# Binary File Declaration
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/aiohttp/_websocket.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/aiohttp/_helpers.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/aiohttp/_http_parser.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/aiohttp/_http_writer.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/frozenlist/_frozenlist.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/charset_normalizer/md__mypyc.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/charset_normalizer/md.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/multidict/_multidict.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/lib/yarl/_quoting_c.cpython-39-darwin.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/cli.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/gui.exe: this file does not require any source code
/Applications/Splunk/var/data/tabuilder/package/TA-virustotal-app/bin/ta_virustotal_app/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
