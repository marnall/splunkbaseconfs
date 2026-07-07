# ABOUT THIS APP

Centrify Add-on for Splunk aimed at collecting data from the Centrify environment for the users to do follow-up data analysis. 

* Author - Centrify Corporation
* Version - 2.4.0
* Build - 100
* Creates Index - False
* Compatible with:
  * Splunk Enterprise version: 6.4.x, 6.5.x, 6.6.x, 7.0.x and 8.0.x
  * OS: Platform independent

# REQUIREMENTS

* Splunk version 6.2 and above

# Recommended System Configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.


# Topology and Setting up Splunk Environment

* This app has been distributed in two parts.

  1) Add-on app, which collects data from Centrify data and normalise it.

  2) The main app, which receives indexed data from Add-on app, runs searches on it and builds the dashboard using indexed data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install  Add-on app on a single machine.

     Here single splunk instance would work as both forwarder and indexer.

   2) **Distributed Environment**: Install the main app and Add-on app on search head, Only Add-on on forwarder system and indexes.conf file from Add-on bundle on Indexer.
     
     * Add-on should be installed on Search head and forwarder node.
     * Only Add-on needs to be configured only on forwarder system.
      * Execute the following command on forwarder to forward the collected data to the indexer.
       /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
     * All the search time extraction would be done by TA placed on search head

# Installation of Add-on

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.

# Configuration of Add-on
    
* Copy $SPLUNK_HOME/etc/apps/TA-centrify/default/inputs.conf.example to $SPLUNK_HOME/etc/apps/TA-centrify/local/inputs.conf.exmaple (Make sure you have admin rights)
* Rename inputs.conf.example to inputs.conf.
* There are different input stanzas in inputs.conf. This inputs.conf contains entries for various file locations for monitoring syslog depending on OS platform To enable any stanza based on your OS, change the disabled property of stanza from “disabled = 1” to “diabled = 0”.
* Restart the Splunk.

# Compatibility with Splunk Add-on for Windows and Splunk Add-on for *nix

* It is possible that user is already using Splunk Add-on for Windows and collecting Windows application logs on indexers.
* In this case, he should already have Splunk forwarder along with Splunk Add-on for Windows is installed on his Windows machine.

* Since Centrify logs are already part of the Windows application logs, the user does not have to install anything additional.
* He should be able to see the Centrify data directly on the indexers.
* Similarly if the user is already using Splunk Add-on for Unix and sending specific Unix logs to indexers, he should already have Splunk forwarder along with Splunk Add-on for Unix installed on Unix machine.
* User can modify the inputs.conf and add Centrify specific log directory and start forwarding that data to the indexers.

* Note that Data collection stanzas in Centrify Add-on for Splunk will remain disabled because we are not using them to collect data. In this case, Centrify Add-on for Splunk is mainly used for field extractions and data normalization.

# EULA

* Please check End User's License Agreement at https://www.centrify.com/eula-siem

# Support Information
    
    *  Community supported. You can use following url to ask questions.
         URL: https://answers.splunk.com/app/questions/3272.html 

# RELEASE NOTES

* Version 2.4.0
  * Tested Compatiblity with Splunk 8.0.x

* Version 2.3.0
  * Updated TRANSFORMS identifier in props.conf for Centrify Audit Logs.

* Version 2.2
  * Added workflow action for Session Replay Feature by creating session_uri field.
  * Segregated normal syslog events and Centrify audit events.
  * Added following three event types
    * has_session_uri
    * centrify_license_management
    * centrify_directaudit_advanced_monitoring
 
# Data Collection

**Data collection using Splunk Add-on for Windows and Splunk Add-on for *nix:** 
In this case, data will get indexed to wineventlog and os indexes and sourcetype will be WinEventLog: Application and Syslog depending on the Windows or Unix log. The user will have to add these indexes into default searchable indexes. 

**Data collection using Centrify Add-on for Splunk:** 
In this case, data will get indexed to the main index and sourcetype will be WinEventLog: Application and Syslog depending on the Windows or Unix log. In this cases, we are keeping the same sourcetypes as Splunk Add-on for Windows/*nix so that field extractions could be done using the sourcetype and it will happen regardless of the data collection method being used by the user. 
This is done specifically to make sure that user’s data does not get replicated to multiple indexes regardless of what data collection method is being used and the Centrify data will get extracted collectedly in all the scenarios.

# CIM Compatibility

This app is compatible with "Authentication" data model of Splunk CIM (Common Information Model).

# TEST YOUR INSTALL

The main app dashboard can take some time to populate the dashboards Once data collection is started. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

  • Search all Centrify logs generated on Windows Agents:
                Search eventtype=centrify_windows_audit_trail_logs

  • Search All Audit Analyzer related logs:
                Search eventtype=Centrify_audit_analyzer

  • Search all successful/granted “DirectAuthorize-Windows” logs:
                Search eventtype=centrify_directauthorize_windows eventstatus=GRANTED
                
  • Search all failed/denied “DirectAuthorize-Windows” logs:
                Search eventtype=centrify_directauthorize_windows eventstatus=DENIED


Copyright © 2021 Centrify Corporation