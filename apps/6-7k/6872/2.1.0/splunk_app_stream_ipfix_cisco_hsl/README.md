# Cisco Catalyst Enhanced Netflow Add-on for Splunk


## OVERVIEW
The "Cisco Catalyst Enhanced Netflow Add-on for Splunk" provides Netflow element mapping for the Cisco Netflow data

* Author - Cisco Systems, Inc
* Version - 2.1.0
* Build - 1


## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox & Safari
* OS: Linux, macOS, Windows
* Splunk Enterprise Version: Splunk 9.0.x & Splunk 8.2.x
* Supported Splunk Deployment: Standalone, Distributed & Cluster

## RELEASE NOTES

### Version 2.1.0
* Updated the name to Cisco Catalyst Enhanced Netflow Add-on for Splunk.

### Version 2.0.0
* Added extractions for additional fields.

### Version 1.0.0
* Added support for HSL NetFlow Logs.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app can be set up in two ways:

**1) Standalone Mode**:

* Install the "Cisco Catalyst Enhanced Netflow Add-on for Splunk" on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
* The "Cisco Catalyst Enhanced Netflow Add-on for Splunk" parses the NetFlow data collected by the "Cisco Catalyst Add-on for Splunk".

**2) Distributed Environment**:

* Install the "Cisco Catalyst Enhanced Netflow Add-on for Splunk" on the Heavy Forwader.

## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/splunk_app_stream_ipfix_cisco_hsl
* To reflect the cleanup changes in UI, Restart the Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Email: ciscosdwan-splunk-support@external.cisco.com

### Copyright (c) 2024 Cisco Systems, Inc. All rights reserved.