CrowdStrike Falcon Intelligence Add-on
======================================================================

OVERVIEW
------------------------------
CrowdStrike Falcon Intelligence Add-on use to fetch data from Falcon Intelligence and indexes it in Splunk for further analysis.

* Author - CrowdStrike
* Version - 1.0.1
* Build - 1
* Creates Index - False
* Compatible with:
    - Splunk Enterprise version: 6.4.x, 6.5.x, 6.6.x and 7.0.x
    - OS: Platform independent


RELEASE NOTES
------------------------------
* Version 1.0.1
  - Updated README file.
  
* Version 1.0.0
  - Account setup to fetch data from Falcon Intelligence.


APPLICATION SETUP
------------------------------
* On Splunk Forwarder:
    * Install the TA bundle on Splunk Forwarder as mentioned under installation section.
    * Navigate to CrowdStrike Falcon Intelligence Add-on, click on "Configuration" and add "Account" with authorized credentials.
    * Click on "Input" and fill the "Account", "Interval" and "Starting Date" fields, using which REST API Calls will be called.
    * In case needed index name can also be updated here to drive data into specific index name.
    * Splunk Indexer’s IP address needs to be given in outputs.conf to send data to specific Splunk Indexer.
    * Restart the instance once and that should start pushing data onto the Splunk Indexer.

* On Splunk Indexer Nodes:
    * On Splunk Indexer, No TA configurations are needed. In case of custom Index, the custom Index should be created.

* On Splunk Search Head:
    * On Splunk Search head, Install TA but configurations are not needed.

** Note: By default, all data is indexed to the main index. If you want to use a custom index then kindly update "cs_get_intelligence_index" macro in CrowdStrike Falcon Intelligence Add-on.

TROUBLESHOOTING
------------------------------

A good test to see that you are receiving all of the data we expect is to run below search after several minutes:

* Execute below search in case TA-crowdstrike_falcon_intel Addon has been installed and configured.
    search `cs_get_intelligence_index` | stats count by sourcetype

In particular, you should see below sourcetype:
* crowdstrike:falcon:intelligence

* To troubleshoot Crowdstrike Intel Addon, check $SPLUNK_HOME/var/log/splunk/ta_crowdstrike_falcon_intel_falcon_intelligence_data_input.log file.

SUPPORT
------------------------------
* Support Offered: Yes
* Support Email: integrations@crowdstrike.com

Copyright (C) by CrowdStrike. All Rights Reserved.