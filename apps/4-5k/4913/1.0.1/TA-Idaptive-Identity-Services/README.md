# About this App

Idaptive Identity Services Add-on for Splunk is aimed at collecting syslog for events of Idaptive Identity Services, for users to do follow-up data analysis. 

* Author - Idaptive Corporation
* Version - 1.0.1
* Build - 1
* Creates Index - False
* Compatible with:
  * Splunk Enterprise version: 6.5.x and 6.6.x
  * OS: Platform independent

# Requirements

* Splunk version 6.5 and above

# Recommended System configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.

# Topology and Setting up Splunk Environment

* This app is an Add-on, which collects syslog for events of Idaptive Identity Services, parses and enriches this data and makes it available for adhoc searching and reporting.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install  Add-on app on a single machine.

     Here single splunk instance would work as both forwarder and indexer.

  2) **Distributed Environment**: Install Add-on app on search head, on forwarder system and on Indexer.
     
     * The Add-on will reside on search head, indexer and forwarder.
     * Execute the following command on forwarder to forward the collected data to the indexer.
       /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk). 
     * All the search time extraction would be done by the add-on placed on search head

# Installation of Add-on

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.

# Configuration of Add-on
    
* Below configuration for Add-on is only needed on Forwarder.
* Copy $SPLUNK_HOME/etc/apps/TA-Idaptive-Identity-Services/default/inputs.conf to $SPLUNK_HOME/etc/apps/TA-Idaptive-Identity-Services/local/inputs.conf (Make sure you have admin rights)
* There are different input stanzas in inputs.conf. This inputs.conf contains entries for various file locations for monitoring syslog depending on OS platform. To enable any stanza based on your OS, change the disabled property of stanza from “disabled = 1” to “disabled = 0”.
* Restart the Splunk.

# Compatibility with Splunk Add-on for *nix

* It is possible that user is already having the Splunk Add-on for *nix installed on the Universal Forwarder and Indexer nodes.
* Since Idaptive logs are already part of the Unix logs, user does not have to install anything additional on this Universal Forwarder, However the add-on need to be installed on indexer, so that Idaptive data is correctly parsed and indexed.
* Note that Data collection stanzas in Idaptive Identity Services Add-on for Splunk will remain disabled because we are not using them to collect data. In this case the Idaptive add-on is mainly used for field extractions and data normalization.

# EULA

* In enclosed file : license-eula.txt

# Support Information
    
    * You can contact developer using following Email.
        Email: vishnu.varma@idaptive.com

# RELEASE NOTES

* Version 1.0.1
  * Functionality to collect and enrich events of Idaptive Identity Services

# Data Collection

**Data collection using Idaptive Identity Services Add-on for Splunk:** 
Data will get indexed to main index and sourcetype will be “iis:events“. 
We are overriding the sourcetype specifically to make sure that no unintentional properties are assigned to the default syslog.

# CIM Compatibility

This app is compatible  with "Authentication" data model of Splunk CIM (Comman information model).

# Test your install

A good test to see that you are receiving all of the data we expect is to run this search after few minutes:

  • Search all Idaptive Identity Services events:
                Search vendor_product="Idaptive_Identity_Services"

  • Search All Idaptive Identity Services logs with tag "authentication":
                Search tag=authentication vendor_product="Idaptive_Identity_Services"

Copyright © 2019 Idaptive Corporation
