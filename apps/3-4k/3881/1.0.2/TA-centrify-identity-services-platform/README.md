# ABOUT THIS APP

Centrify Add-on for Splunk aimed at collecting data from Centrify Identity Platform environment for users to do follow-up data analysis. 

* Author - Centrify Corporation
* Version - 1.0.2
* Build - 2
* Creates Index - False
* Compatible with:
  * Splunk Enterprise version: 6.4.x, 6.5.x , 6.6.x , 7.x and 8.x
  * OS: Platform independent

# REQUIREMENTS

* Splunk version 6.2 and above

# Recommended System configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.

# Topology and Setting up Splunk Environment

* This app is an Add-on, which runs collector scripts and gathers data from Centrify Identity Platform environment, parses and enriches this data and makes it available for adhoc searching and reporting.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install  Add-on app on a single machine.

     Here single splunk instance would work as both forwarder and indexer.

  2) **Distributed Environment**: Install Add-on app on search head, on forwarder system and on Indexer.
     
     * The Add-on will reside on search head, indexer and forwarder.
     * Execute the following command on forwarder to forward the collected data to the indexer.
       /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk). 
     * All the search time extraction would be done by TA placed on search head

# Installation of Add-on

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.

# Configuration of Add-on
    
* Below configuration for Add-on is only needed on Forwarder.
* Copy $SPLUNK_HOME/etc/apps/TA-centrify-identity-services-platform/default/inputs.conf to $SPLUNK_HOME/etc/apps/TA-centrify-identity-services-platform/local/inputs.conf (Make sure you have admin rights)
* There are different input stanzas in inputs.conf. This inputs.conf contains entries for various file locations for monitoring syslog depending on OS platform. To enable any stanza based on your OS, change the disabled property of stanza from “disabled = 1” to “diabled = 0”.
* Restart the Splunk.

# Compatibility with Splunk Add-on for *nix

* It is possible that user is already having the Splunk Add-on for *nix installed on his Universal Forwarder and Indexer nodes.
* Since Centrify logs are already part of the Unix logs, user does not have to install anything additional on his Universal Forwarder, However the add-on need to be installed on indexer, so that Centrify data is correctly parsed and indexed.
* Note that Data collection stanzas in Centrify Add-on for Splunk will remain disabled because we are not using them to collect data. In this case Centrify Add-on for Splunk is mainly used for field extractions and data normalization.

# EULA

* Please check End User's License Agreement at https://www.centrify.com/eula-siem

# Support Information
    
    * You can contact developer using following Email.
        Email: fabrice.viguier@centrify.com

# RELEASE NOTES

* Version 1.0.2
  * Tested Compatiblity with Splunk 8.0.x
  
* Version 1.0.1
  * Functionality to collect and enrich events of Centrify Identity Platform Services
  
# Data Collection

**Data collection using Centrify Add-on for Splunk:** 
Data will get indexed to main index and sourcetype will be “centrify_cisp_syslog“. We are overriding the sourcetype specifically to make sure that no unintentional properties are assigned to the default syslog.

# CIM Compatiblity

This app is compatible  with "Authentication" datamodel of Splunk CIM (Comman information model).

# TEST YOUR INSTALL

A good test to see that you are receiving all of the data we expect is to run this search after few minutes:

  • Search all Centrify Identity Platform logs:
                Search centrify_vendor_product="Centrify_Cloud"

  • Search All Centrify Identity Platform logs with tag "authentication":
                Search tag=authentication centrify_vendor_product="Centrify_Cloud"

Copyright © 2020 Centrify Corporation
