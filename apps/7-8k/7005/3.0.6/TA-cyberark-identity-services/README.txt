# CyberArk Identity Services Add-on for Splunk

# About this App

This Add-on retrieves events using REST APIs from CyberArk Identity Services. It parses and enriches these events to make it available for adhoc searching and reporting in Splunk.

* Author - CyberArk Software, Inc.
* Version - 3.0.0
* Build - 4 
* Creates Index - False
* Compatible with:
  * Splunk Enterprise version: 8.2.0
  * OS: Platform independent

# Requirements

* Splunk version 8.2.0 and above

# Topology and Setting up Splunk Environment

* This app is an Add-on, which retrieves events of CyberArk Identity Services, parses and enriches this data, and makes it available for adhoc searching and reporting.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install the Add-on app on a single machine.

  2) **Distributed Environment**: Install the add-on either on heavy forwarder or on an Indexer. Also install the add-on on search head.
     
     * In case of an indexer cluster, just install the addon on a Heavy forwarder to avoid duplicate events collection. 
     * The addon will also need to be installed on search head, as it has various search time extractions.

# Installation of Add-on

* This app can be installed through UI using "Manage Apps" or extract the tgz file directly into /opt/splunk/etc/apps/ folder.

# Configuration of Add-on
    
* Install Addon and it will prompt you to restart the Splunk. 
* Create input in UI for Idaptive Identity Services Tenant 

# EULA

* In enclosed file : license-eula.txt

# RELEASE NOTES

* Version 3.0.0
  * Functionality is to collect, parse and enrich events of Idaptive Identity Services

# Data Collection

**Data collection using CyberArk Identity Services Add-on for Splunk:** 
Data will get indexed in the specified index, and sourcetype will be “iis:events“. 

# CIM Compatibility

This app is compatible  with "Authentication" data model of Splunk CIM (Common information model).

# Test your install

A good test to see that you are receiving all of the data we expect is to run this search after few minutes of adding an input:

  • Search all CyberArk Identity Services events:
                Search sourcetype="iis:events"

  • Search All CyberArk Identity Services logs with tag "authentication":
                Search tag=authentication sourcetype="iis:events"

Copyright © 2023 CyberArk Software, Ltd.
