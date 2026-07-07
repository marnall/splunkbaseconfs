## Microsoft Cloud App Security Add-on for Splunk

* Add-on Homepage: https://apps.splunk.com/apps/id/TA-ms_cloud_app_security
* Author: Hurricane Labs
* Version: 1.0.0

## Description
The purpose of this add-on is to provide value to your Microsoft Cloud App Security syslog from Alerts and Activities. This is done by making the logs CIM compliant, adding tagging for Enterprise Security data models, and other knowledge objects to make searching and visualizing this data easy.

This add-on assumes you are onboarding the data either using a syslog collector that outputs to a file or using the built-in Splunk TCP/UDP listener (I would highly recommend the former)--the knowledge objects will work for any ingestion method if you use the correct sourcetype. Regardless of ingestion method, you may need to adjust some of the props.conf settings for proper line breaking and timestamp parsing.

* Built for Splunk Enterprise 6.x.x or higher
* CIM Compliant (CIM 4.0.0 or higher)
* Ready for Enterprise Security

## Constraints
1. This add-on requires that you use the sourcetype "ms:cas:syslog" when ingesting the data.
2. This add-on must be installed on your parsing (HF/IDX) tier and Search Head(s).
3. This add-on requires that you choose "Generic CEF" as the Format when configuring CAS.

## Microsoft Cloud App Security Instructions
1. Follow the steps as outlined by Microsoft here:
    * https://docs.microsoft.com/en-us/cloud-app-security/siem

## SPLUNK INSTALLATION AND CONFIGURATION
* Search Head: Add-on Always Required (Knowledge Objects)
* Heavy Forwarder: Add-on Possibly Required (Event Parsing)
* Indexer: Possibly Add-on Required (Event Parsing)
* SH & Indexer Clustering: Supported


### Add-on Installation Instructions
1. This add-on needs to be installed on your Search Head(s) and on the FIRST Splunk Enterprise system(s) that handles the data, traditionally that would be a Heavy Forwarder or an Indexer. This add-on should not be deployed to a Universal Forwarder as it won't do anything.
    * Make sure you have read and understood the "Constraints" section to properly configure your inputs.conf.
2. A Splunk Restart may be required, you may also attempt a debug refresh.
3. Verify data is coming in and you are seeing the proper field extractions & sourcetype transforms by searching the data.
    * Example Search: index=cas sourcetype=ms:cas:*
    * Note: If you see 'ms:cas:syslog' as a sourcetype, the sourcetype transform isn't working. This likely means you did not install the TA according to step 1 above.
4. (Optional, recommended) On your Search Head(s) edit the "ms_cas_activities" and "ms_cas_alerts" Event Types to include the index you're storing this sourcetype in.

### Example Inputs.conf
How you choose to bring the syslog data into Splunk is completely up to you. Here are a couple examples of how you might bring on this data:

#### Built-in Splunk Listener Example
[tcp://9514]
connection_host = dns
sourcetype = ms:cas:syslog
index = cas

#### File Monitor For Syslog-ng Output Example
[monitor:///var/log/network/ms_cloud_app_security/*/syslog.log]
sourcetype = ms:cas:syslog
index = cas
disabled = 0
host_segment = 5

### New features
* 1.0.0: Add-on Released

### Fixed issues

### Known issues

### Third-party software attributions

### DEV SUPPORT
Contact: splunk-app@hurricanelabs.com
