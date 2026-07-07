# Dragos OT Add-On for Splunk

## Overview:
The Dragos OT Add-On bridges the IT/OT divide by bringing OT cybersecurity
data from the Dragos Platform and Dragos WorldView into Splunk Enterprise Security
This integration brings a set of Dragos capabilities into Splunk, enhancing visibility
of OT environments by providing complete asset discovery, threat detection, and
vulnerability management as well as enabling effective incident response. This
provides users in-depth and context rich ICS/OT asset visibility that analyzes
multiple data sources including protocols, network traffic, data historians,
host logs, asset characterizations, and anomalies to provide unmatched
visibility of your ICS/OT environment. In addition to the Add-On's ability
to provide visibility into your OT environment, it can also connect to
Dragos WorldView to download Indicators of Compromise (IOCs) and integrate
them into Splunk Enterprise Security's Threat Intelligence framework for
streamlined threat intelligence.

## How it Works
The Dragos OT Add-On can be installed and configured to connect to both
Dragos Platform and Dragos WorldView to ingest data into Splunk.
You can then use the raw data to build queries and dashboards that provide
value for your organization. 

To take full advantage of Splunk's OT and Threat Intelligence capabilities
it's recommended that you install both Splunk Enterprise Security and the Splunk OT
Add-On. You can then follow the Splunk OT Add-On and Dragos OT Add-On configuration
instructions to get access Dragos data inside these additional applications. This provides
integration with Splunk's Asset and Threat Intelligence Frameworks, advanced
pre-built dashboards, and security alerting.  This improved visibility, detection,
and response capability gives security teams a blended IT/OT view allowing teams
to appropriately prioritize analysis and response activities.

## How to Access
To use the basic Dragos OT Add-On functionality, you need a Dragos Platform license
if connecting to a Dragos Platform Instance for OT data and/or a Dragos WorldView
Subscription if connecting to Dragos WorldView for IOCs. To utilize advanced features
within Splunk Enterprise and the Splunk OT Add-On a Splunk Enterprise Security
license is required.

## Additional Documentation

Additional documentation for this application is available to Dragos customers.
Please reach out to your Dragos point of contact for additional information.

## Version History

### 1.1.7
- Updating application to to utilize Splunk Add-On Builder v4.5.1. This ensures
  compliance with latest security updates.
- Add support for HTTP/1.1 when proxying API requests.
- Fix Dragos notification source field so that it doesn't conflict with Splunk's
  built in source field.
- Fix Dragos notification handling around query responses with 0 results.
- Parsing out source and destination IP addresses, MACs, hostnames, and domains from raw
  data to make it easier to identify the directionality of assets involved in notifications.


### 1.1.6
- Updated application to ensure compliance with latest Splunk Cloud Vetting
  standards
- Updated notifications input to use checkpointing. This reduces duplication of
  data if there is an error in the middle of pulling down a large batch of notifications.

### 1.1.5
- Added support for Dragos Platform 2.2.1, 2.3, and 2.4
- Added support for using a proxy server when communicating with a SiteStore
- Removed toggle for TLS certificate validation
- Added ability to map sensorID to sensor_name
- Fixed various minor bugs

### 1.1.1
- Fixed timestamp parsing bug with in Dragos Notifications data that could lead
  to inaccurate event timestamps in Splunk
- Fixed bug that could have led to duplicate Dragos Notifications if notification
  fell on query time boundary
- Switched Dragos Notifications to query based off creation time instead of
  previously used updated time. This reduces the likelihood that a notification
  could be imported twice but cloud also result in data that differs slightly
  from the Dragos Sitestore
- Modified Dragos Sitestore query batch size to improve compatibility across
  multiple sitestore versions
- Updated to support Sitestore versions 2.2 and newer
- Added saved search that can be used to search for asynchronous errors
  when downloading data from the Dragos WorldView or Sitestore APIs

### 1.1.0
- Adding support for WorldView IOCs
- Modifying Asset Data saved search to de-duplicate by Dragos asset_id

### 1.0.0
- Initial release

# Binary File Declaration
* bin/ta_dragos_ot_add_on/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: This file
  is included as a dependency of Splunk's Add-On Builder. Source code for can be found
  inside the pyrsistent Python project: https://github.com/tobgu/pyrsistent/tree/master/pyrsistent
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA_dragos_ot_add_on/bin/ta_dragos_ot_add_on/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA_dragos_ot_add_on/bin/ta_dragos_ot_add_on/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA_dragos_ot_add_on/bin/ta_dragos_ot_add_on/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA_dragos_ot_add_on/bin/ta_dragos_ot_add_on/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA_dragos_ot_add_on/bin/ta_dragos_ot_add_on/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA_dragos_ot_add_on/bin/ta_dragos_ot_add_on/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA_dragos_ot_add_on/bin/ta_dragos_ot_add_on/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
