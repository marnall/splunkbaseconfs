# Farsight Security DNSDB for Splunk


## Table of Contents

### OVERVIEW

- About Farsight Security DNSDB for Splunk
- Release notes
- Performance benchmarks
- Support and resources

### INSTALLATION

- Hardware and software requirements
- Installation steps

### USER GUIDE

- Key concepts
- Usage (command/lookup documentation)
- Configuration
- Troubleshooting

---
### OVERVIEW

#### About Farsight Security DNSDB for Splunk

| Author | Farsight Security, Inc. |
| --- | --- |
| App Version | 2.0.0 |
| Vendor Products | Farsight Security DNSDB |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

Farsight Security DNSDB for Splunk allows a Splunk® Enterprise administrator to run DNSDB queries from an included dashboard, as well as through search commands.

##### Scripts and binaries

* dnsdb_query.py
  * Common python module for performing DNSDB queries.
* dnsdb_command.py
  * Splunk custom command for performing DNSDB queries on hostnames/IP addresses.
* dnsdb_ratelimit.py
  * Splunk custom command which retrieves query limit information.
* dnsdb_lookup.py
  * Custom command for querying a set of targets against DNSDB. **Note: please see the section titled "dnsdb lookup" before using this.**
* dnsdb_validateip.py
  * Internal script used by dashboard to validate IP addresses.
* dnsdb_flushcache.py
  * Internal script used by a daily scheduled search to remove outdated responses from the KV store.

#### Release notes

##### About this release

Version 2.0.6 of Farsight Security DNSDB for Splunk is compatible with:

| Splunk Enterprise versions | 9.x, 8.x                |
| --- |-------------------------|
| CIM | N/A                     |
| Platforms | Platform independent    |
| Vendor Products | Farsight Security DNSDB |
| Lookup file changes | N/A                     |

##### Features

Version 2.0.6 Released: 2023-July-01 
 * Update README documentation

Version 2.0.5 Released: 2022-May-24 
 * Upgraded dependencies to latest versions to maintain Splunk Cloud compatibility

Version 2.0.0 Released: 2021-March-21
 * Converted app to DNSDB API version 2.
 * Added "raw" lookup type for dnsdb command.
 * Added "dnsdbflex" command for performing searches using the Flex API.
 * Added a DNSDB adaptive response action. 

Version 1.1.1 Released: 2020-July-15
 * Added Python 3 support.
 * API key now stored in the encrypted credential store.

Version 1.0.6 Released: 2018-Mar-2
 * Corrected issue where Time First in rrset results was always N/A

Version 1.0.4 Released: 2017-Mar-22

 * Exclude .pyc from build package.

Version 1.0.3 Released: 2017-Sept-24

 * Make proxy values configuration options.
 * Make KV URL a configuration option.
 * Converts scripted lookup to a streaming command.


#### Performance benchmarks

In general performance impact of this app should be minimal. Individual queries will almost always take less than a second to complete. The following is a few queries listed next to the time spent executing them:

| Command                                       | Execution Time  |
| --------------------------------------------- | --------------- |
| dnsdb target="example.com" type="rrset"       | 0.175707101822s |
| dnsdb target="198.51.100.1" type="rdata"      | 0.183328151703s |
| dnsdb target="google.com" type="rrset"        | 0.723739147186s |

Google.com can be seen as an extreme example, as it returns the maximum amount of results (10,000).

Results from queries made by the custom command are also cached (using the Splunk KV store). Performing a query that has already been run once within the past 24 hours will be much faster, as the data is simply taken from the KV Store.

##### dnsdb lookup
The one performance issue to be aware of is the included dnsdblookup command. Every event that is passed to it will generate a query to DNSDB, so a search over a few thousand events could easily take minutes longer if passed to the lookup. Furthermore, **every event passed to the lookup will count as a query towards your daily maximum**. Please be wary when using the lookup as to not accidentally reach your maximum query limit.

##### Support and resources

Support for this app is provided by Farsight Security. Please send questions to support@farsightsecurity.com

* Hours: 9AM-5PM Monday-Frday
* Observed Holidays: Major US Holidays

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

This app has no hardware requirements.

#### Software requirements

Farsight Security DNSDB for Splunk can run on either Windows or Linux.

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download Farsight Security DNSDB for Splunk  at <link to app location>.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Download app from Splunkbase
2. Place [app.tar.gz] somewhere on your Search Head
3. Install using splunk command:
_splunk install app /path/to/app.tar.gz_
4. Set API key. This can be done in Splunkweb by clicking "Setup" in the app's navigation bar.



## USER GUIDE

### Usage

Once configured, the easiest way to use this app is through the built-in DNSDB dashboard. Choose a time range, type an IP address or hostname into the target field and press enter.

Farsight Security DNSDB for Splunk also comes with two commands and a lookup so that you can incorporate DNSDB queries into your own searches and dashboards. Below is usage documentation for all three of them.

### Adaptive response action

If you use Splunk's Enterprise Security product, this app includes an adaptive response action which can be used from the Incident Review view. Select any notable event you wish to run a DNSDB query against, select "Run Adaptive Response Actions" and then "DNSDB Lookup". Fill in the name of the field containing the value you wish to look up (eg. dest), the type of the target (ip, hostname, raw rdata) and any other inputs needed. Click "Run", and then refresh the adaptive responses panel of that notable events. Clicking "DNSDB Lokup" in that panel will send you to a search containing the output of your lookup. 

### dnsdb command

Runs a DNSDB query on the given target. If target is an IP address, query is RDATA. Otherwise, query is RRSET. "before" and "after" fields can be supplied optionally to limit the time range of the query.

**Syntax**

_dnsdb target=**ip/hostname** type=**rdata/rrset/raw** [rrtype=**A/MX/CNAME/etc] [earliest=**time**] [latest=**latest**]_


**Examples**

_| dnsdb target=203.0.113.0/24_
_| dnsdb target="example.com" latest=1446000216_

### dnsdblimit command

Returns the DNSDB API query limit, number of queries remaining, as well as the time the remaining queries will reset.

**Syntax**

_dnsdblimit_


**Example**

_| dnsdblimit_

### dnsdblookup command

Runs dnsdb command on a set of targets.

**Syntax**

_ ... | dnsdblookup input_field=hostname _

**Example**

_... | dnsdblookup input_field=src_ip_

### dnsdbflex command

Perform searches using the Flex API.

**Syntax**

_ | dnsdbflex query_type=<rdata|rrnames> match_type=<glob|regex> query=<glob or regex pattern> [rrtype=**A/MX/CNAME/etc] [bailiwick=bailiwick] [time_first_before=time] [time_first_after=time] [time_last_before=time] [time_last_after=time]

**Example**

_ |dnsdbflex query_type=rdata match_type=regex query="farsight" time_last_after=2020-01-01T00:00:00Z

### Configure Farsight Security DNSDB for Splunk

The only configuration needed for this app is setting an API key. This can be done in Splunkweb by clicking "Set up" on the "Manage apps" page, or through commandline by editing dnsdb.conf.

### Troubleshooting

***Problem***
App returns error "Authorization failed. Check API key".
***Cause***
API Key is missing or incorrect.
***Resolution***
Check that your API key is entered correctly.

***Problem***
App returns error "Query limit reached".
***Cause***
You have reached your query limit. 
***Resolution***
Wait until your limit reset (probably daily at midnight) until making more queries.
