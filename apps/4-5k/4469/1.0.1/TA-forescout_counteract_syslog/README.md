ForeScout CounterACT Syslog Add-on for Splunk

Add-on Homepage: https://apps.splunk.com/apps/id/TA-forescout_counteract_syslog
Author: Hurricane Labs
Version: 1.0.1

### Description ###
The purpose of this add-on is to provide value to your ForeScout CounterACT syslog logs (ONLY SYSLOG!). This is done by making the logs CIM compliant, adding tagging for Enterprise Security data models, and other knowledge objects to make searching and visualizing this data easy.

This add-on assumes you are onboarding the data either using a syslog collector that outputs to a file or using the built-in Splunk TCP/UDP listener (I would highly recommend the former)--the knowledge objects will work for any ingestion method if you use the correct sourcetype. Regardless of ingestion method, you may need to adjust some of the props.conf settings for proper line breaking and timestamp parsing.

+Built for Splunk Enterprise 6.x.x or higher
+CIM Compliant (CIM 4.0.0 or higher)
+Ready for Enterprise Security
+Built based on ForeScout CounterACT Syslog Plugin 3.2.0 Documentation
++https://www.forescout.com/wp-content/uploads/2018/04/CounterACT_Syslog_Messages_Technical_Note.pdf
+++Supports logs from "NAC Events", "Threat Protection", and "System Log and Events" sections.
+++Does not support logs from "User Operation" or "Operating System Messages" sections (too much variance between systems).
+If you are looking to use the ForeScout CounterACT API, please use this add-on: https://splunkbase.splunk.com/app/3382/

### Constraints ###
1. This add-on is assuming you are using the timestamp which is configured in default/props.conf. If your timestamp is different, you MUST alter several settings in local/props.conf of this add-on under the "forescout:counteract:syslog" sourcetype stanza. You may also need to set 'TZ' if Splunk is picking the wrong timezone for your events.
2. This add-on requires that you initially bring on the data with the sourcetype "forescout:counteract:syslog". There are sourcetype transforms in place that will ultimately change the initial sourcetype to one of three other sourcetypes (forescout:counteract:nac, forescout:counteract:threat, and forescout:counteract:system).

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
  4a. Example Search: index=forescout sourcetype=forescout:counteract:* | dedup sourcetype
  4b. Note: You should have zero results for index=forescout sourcetype=forescout:counteract:syslog

#### Indexer For Data Collection ####
1. Install the add-on on the Indexer and Search Head.
  1a. Make sure you have read and understood the "Constraints" section.
2. Configure the inputs.conf in the local directory of this add-on.
3. A Splunk Restart may be required, you may also attempt a debug refresh.
4. Verify data is coming in and you are seeing the proper field extractions & sourcetype transforms by searching the data.
  4a. Example Search: index=forescout sourcetype=forescout:counteract:* | dedup sourcetype
  4b. Note: You should have zero results for index=forescout sourcetype=forescout:counteract:syslog

#### Universal Forwarder For Data Collection ####
1. Install the add-on on the Search Head and on the first Splunk Enterprise system that the Universal Forwarder forwards to (check your outputs.conf on the UF).
  1a. Make sure you have read and understood the "Constraints" section.
2. A Splunk Restart may be required, you may also attempt a debug refresh. Make sure this is done before continuing.
3. Configure inputs.conf on the UF (typically done through a deployment server).
4. Verify data is coming in and you are seeing the proper field extractions & sourcetype transforms by searching the data.
  4a. Example Search: index=forescout sourcetype=forescout:counteract:* | dedup sourcetype
  4b. Note: You should have zero results for index=forescout sourcetype=forescout:counteract:syslog

#### Example Inputs.conf ####
How you choose to bring the data into Splunk is completely up to you. Here are a couple examples of how you might bring on this data:

##### Built-in Splunk Listener Example #####
[tcp://9514]
connection_host = dns
sourcetype = forescout:counteract:syslog
index = forescout

##### File Monitor For Syslog Output Example #####
[monitor:///var/log/network/forescout_counteract/*/syslog.log]
sourcetype = forescout:counteract:syslog
index = forescout
disabled = 0
host_segment = 5


### New features
+ 1.0.1: Changed capture groups in transforms.conf to non-capture groups to meet AppInspect requirements.

### Fixed issues
+ 1.0.1: Changed capture groups in transforms.conf to non-capture groups to meet AppInspect requirements.

### Known issues

### Third-party software attributions

### DEV SUPPORT
Contact: splunk@hurricanelabs.com
