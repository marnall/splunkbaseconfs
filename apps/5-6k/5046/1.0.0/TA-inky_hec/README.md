Inky HEC Add-on for Splunk

Add-on Homepage:
Author: Hurricane Labs
Version: 1.0.0

### Description ###
The purpose of this add-on is to provide CIM compliant field extractions for Inky logs via HEC.

+Built for Splunk Enterprise 6.x.x or higher
+CIM Compliant (CIM 4.0.0 or higher)
+Ready for Enterprise Security

### INSTALLATION AND CONFIGURATION
Search Head: Required
Heavy Forwarder: Possibly Required
Indexer: Possibly Required
Universal Forwarder: Not Supported
Light Forwarder: Not Supported

#### Add-on Installation
1. Install on your Search Head and HEC Endpoint.
2. Splunk restart may be required depending on your version of Splunk.

#### Setting up the HEC Token (GUI)
1. Settings > Data Inputs > HTTP Event Collector > New Token.
2. Set a name for the input (up to you) and leave "Enable indexer acknowledgment" unchecked, click next.
3. For "source type" click "select" and choose "inky:email:hec", then at the bottom select the index you want to store the logs in. Review and finish.

#### Setting up HEC Token (CLI)
1. Change the index and token value and set this in inputs.conf on your HEC collection point(s).
    Note: You can run 'uuidgen' to generate a HEC token value from Linux/Mac

[http://inky]
description = Inky Events
disabled = 0
index = <REPLACEME>
indexes = <REPLACEME>
useACK = 0
token = <REPLACEME>
sourcetype = inky:email:hec

#### Validate your installation
1. Search for the data on your Search Head by running this search (smart/verbose mode):
    a. index=REPLACEME sourcetype=inky:email:hec
2. On the left hand side, verify that you see the auto KV json fields (such as data.meta_data.dashboard_url, etc)
3. On the left hand side, verify that you see CIM fields (such as recipient, subject, etc)
    
### New features
+ 1.0.0: Add-on released

### Fixed issues

### Known issues

### DEV SUPPORT
Contact: splunk-app@hurricanelabs.com
