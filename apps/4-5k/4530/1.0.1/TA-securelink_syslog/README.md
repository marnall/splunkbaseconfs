SecureLink Syslog Add-on for Splunk

Add-on Homepage: https://apps.splunk.com/apps/id/TA-securelink_syslog
Author: Hurricane Labs
Version: 1.0.1

### Description ###
The purpose of this add-on is to provide value to your SecureLink syslog logs. This is done by making the logs CIM compliant, adding tagging for Enterprise Security data models, and other knowledge objects to make searching and visualizing this data easy.

This add-on assumes you are onboarding the data either using a syslog collector that outputs to a file or using the built-in Splunk TCP/UDP listener (I would highly recommend the former)--the knowledge objects will work for any ingestion method if you use the correct sourcetype. Regardless of ingestion method, you may need to adjust some of the props.conf settings for proper line breaking and timestamp parsing.

+Built for Splunk Enterprise 6.x.x or higher
+CIM Compliant (CIM 4.0.0 or higher)
+Ready for Enterprise Security

### Constraints ###
1. This add-on is assuming you are using the timestamp which is configured in default/props.conf. If your timestamp is different, you MUST alter several settings in local/props.conf of this add-on under the "securelink:syslog" sourcetype stanza. You may also need to set 'TZ' in local/props.conf if Splunk is picking the wrong timezone for your events.
2. This add-on requires that you initially bring on the data with the sourcetype "securelink:syslog". There are sourcetype transforms in place that will ultimately change the initial sourcetype to one of two other sourcetypes (securelink:admin or securelink:audit).

### INSTALLATION AND CONFIGURATION ###
Search Head: Add-on Always Required (Knowledge Objects)
Heavy Forwarder: Add-on Possibly Required (Data Collection and/or Event Parsing)
Indexer: Possibly Add-on Required (Data Collection and/or Event Parsing)
Universal Forwarder: Add-on Never Required (Data Collection only)
SH & Indexer Clustering: Supported

This add-on needs to be installed on your Search Head(s) and on the FIRST Splunk Enterprise system(s) that handles the data, traditionally that would be a Heavy Forwarder or Indexer. This add-on should not be deployed to a Universal Forwarder as it won't do anything.

#### Heavy Forwarder For Data Collection ####
1. Install the add-on on the Heavy Forwarder and Search Head.
  1a. Make sure you have read and understood the "Constraints" section.
2. Configure the inputs.conf in the local directory of this add-on.
3. A Splunk Restart may be required, you may also attempt a debug refresh.
4. Verify data is coming in and you are seeing the proper field extractions & sourcetype transforms by searching the data.
  4a. Example Search: index=securelink sourcetype=securelink:* | dedup sourcetype
  4b. Note: You should have zero results for index=securelink sourcetype=securelink:syslog
5. On your Search Head(s) edit the "securelink_auth", "securelink_change_account", and "securelink_change_network" eventtypes to include the index you put this data in (this will improve performance).
  5b. Example: search = index=securelink sourcetype=securelink:admin OR sourcetype=securelink:audit

#### Indexer For Data Collection ####
1. Install the add-on on the Indexer and Search Head.
  1a. Make sure you have read and understood the "Constraints" section.
2. Configure the inputs.conf in the local directory of this add-on.
3. A Splunk Restart may be required, you may also attempt a debug refresh.
4. Verify data is coming in and you are seeing the proper field extractions & sourcetype transforms by searching the data.
  4a. Example Search: index=securelink sourcetype=securelink:* | dedup sourcetype
  4b. Note: You should have zero results for index=securelink sourcetype=securelink:syslog
5. On your Search Head(s) edit the "securelink_auth", "securelink_change_account", and "securelink_change_network" eventtypes to include the index you put this data in (this will improve performance).
  5b. Example: search = index=securelink sourcetype=securelink:admin OR sourcetype=securelink:audit

#### Universal Forwarder For Data Collection ####
1. Install the add-on on the Search Head and on the first Splunk Enterprise system that the Universal Forwarder forwards to (check your outputs.conf on the UF).
  1a. Make sure you have read and understood the "Constraints" section.
2. A Splunk Restart may be required, you may also attempt a debug refresh. Make sure this is done before continuing.
3. Configure inputs.conf on the UF (typically done through a deployment server).
4. Verify data is coming in and you are seeing the proper field extractions & sourcetype transforms by searching the data.
  4a. Example Search: index=securelink sourcetype=securelink:* | dedup sourcetype
  4b. Note: You should have zero results for index=securelink sourcetype=securelink:syslog
5. On your Search Head(s) edit the "securelink_auth", "securelink_change_account", and "securelink_change_network" eventtypes to include the index you put this data in (this will improve performance).
  5b. Example: search = index=securelink sourcetype=securelink:admin OR sourcetype=securelink:audit


#### Example Inputs.conf ####
How you choose to bring the data into Splunk is completely up to you. Here are a couple examples of how you might bring on this data:

##### Built-in Splunk Listener Example #####
[tcp://9514]
connection_host = dns
sourcetype = securelink:syslog
index = securelink

##### File Monitor For Syslog-ng Output Example #####
[monitor:///var/log/network/securelink_syslog/*/syslog.log]
sourcetype = securelink:syslog
index = securelink
disabled = 0
host_segment = 5

### New features
+ 1.0.0: Add-on Released

### Fixed issues
+ 1.0.1: Fixed cloud AppInspect issue

### Known issues

### Third-party software attributions

### DEV SUPPORT
Contact: splunk@hurricanelabs.com
