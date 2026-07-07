Introduction
=============

The Splunk App for NSS Labs CAWS enables consumers of the CAWS API to simply injest CAWS threat and device efficacy into Splunk and view this data using helpful charts and KPI panels. Users can also integrate CAWS organization statistics and KPIs into custom dashboards using various saved searches.

Features
============
## NSS Labs' CAWS API Data Modular Input

Allows Splunk users to receive threat details and device efficacy notifications from NSS Labs' Cyber Advanced Warning System. Event sourcetypes are caws:threat and caws:bypass.

### Notes About Modular Input Data

- `sourcetype=caws:threat` - Results provide details about threats found in the wild. Please see the full documentation for information on how fields are aliased to the Splunk CIM Malware_Attack model.

- `sourcetype=caws:bypass` - Results provide basic details about threats that bypassed a security product in a CAWS Profile. Data can be joined to caws:threat events using the NSSId field.

### CAWS Metrics/KPI Saved Searches

Allows the querying of an organization’s statistics/KPIs in Splunk using custom search commands and saved searches.  The included Saved Searches are intended to provide an interface to the NSS Labs CAWS Web API in order to allow easy integration of metrics and KPIs available in CAWS with custom dashboards, reports, and alerts.  Save searches are then included to facilitate querying specific KPIs, etc.

#### Custom Search Commands

-  `| overallorgmetrics` - Queries the CAWS Web API for global organization KPIs and other metrics.

-  `| dailyorgmetrics` - Queries the CAWS Web API for organization-wide KPIs and other metrics that are calculated using data partitioned based on date.

#### Saved Searches

- `caws:daily:urls:ttl` - Queries the CAWS Web API for the daily average URL time-to-live of the malicious websites found.

- `caws:daily:exploits` - Queries the CAWS API for the daily exploit count

- `caws:daily:urls:malicious` - Queries the CAWS API for the daily malicious URL count.

- `caws:global:exploits` - Queries the CAWS API for the total count of exploits

- `caws:global:urls` - Queries the CAWS API for the total count of URLs scanned

- `caws:global:urls:malicious` - Queries the CAWS API for the count of malicious URLs scanned

- `caws:global:urls:ttl` - Queries the CAWS API for the average malicious URL time-to-live

- `caws:global:apps` - Queries the CAWS API for the number of applications that have been tested

- `caws:global:apps:compromised` - Queries the CAWS API for the number of the organization's' applications that are known to be compromised

These saved searches are scoped to the Splunk App for CAWS application by default.  


### Dashboards

Splunk for CAWS includes several simple dashboards to provide users with examples of the data provided by the modular inputs, custom search commands, and saved searches.

### Common Information Model Integration

`caws:threat` events are aliased to take advantage of searches against the Splunk ***Malware_Attack*** CIM data model.

Requirements
===============

The application requires access to the CAWS API with integration features enabled.

Gettting Started
================

After installing the app, it can be configured using its setup page. This will configure a default NSS Labs’ CAWS API Data modular input and securely store CAWS API credentials to allow the included custom search commands to authenticate against the CAWS API.

Note: If users chose to manually configure the NSS Labs’ CAWS API Data modular input, the password will be encrypted and masked automatically when events are streamed for the first time.

Support
=================

Please contact techsupport@nsslabs.com with any questions or feedback.

Release Notes
=================

### Version 1.0.0, *Feb. 15, 2017*
- Initial release

### Version 1.1.0, *Oct. 25, 2017*
- Added support for using proxy servers.
- Removed drilldown option from application bypass notifications
- Updated documentation