Technology Add-on for CrowdStrike
======================================================================

OVERVIEW
------------------------------
Technology Add-on for CrowdStrike use to fetch data from Falcon Indicator and indexes it in Splunk for further analysis.

* Author - CrowdStrike
* Version - 1.0.7
* Build - 1
* Creates Index - False
* Compatible with:
    - Splunk Enterprise version: 6.4.x, 6.5.x, 6.6.x and 7.0.x
    - OS: Platform independent
 

APPLICATION SETUP
------------------------------
* On Splunk Forwarder:
    * Install the TA bundle on Splunk Forwarder as mentioned under installation section.
    * Navigate to Technology Add-on for CrowdStrike, click on "Configuration" and add "Account" with authorized credentials.
    * Click on "Input" and fill the "Account", "Interval" and "Starting Date" fields, using which REST API Calls will be called.
    * In case needed index name can also be updated here to drive data into specific index name.
    * Splunk Indexer’s IP address needs to be given in outputs.conf to send data to specific Splunk Indexer.
    * Restart the instance once and that should start pushing data onto the Splunk Indexer.

* On Splunk Indexer Nodes:
    * On Splunk Indexer, No TA configurations are needed. In case of custom Index, the custom Index should be created.

* On Splunk Search Head:
    * On Splunk Search head, Install TA and configure user account only(No need to configure "Input").

** Note: By default, all data is indexed to the main index. If you want to use a custom index then kindly update "cs_get_index" macro in Technology Add-on for CrowdStrike.

SAMPLE EVENT GENERATOR
------------------------------

* The TA-crowdstrike, comes with sample data files, which can be used to generate sample data for testing. In order to generate sample data it requires SA-Eventgen application. The TA will generate sample data of rest API calls at an interval of 2 hours. You can update this configuration from eventgen.conf file available under $SPLUNK_HOME/etc/apps/default/.

TROUBLESHOOTING
------------------------------

A good test to see that you are receiving all of the data we expect is to run below searches after several minutes:

* Execute below search in case TA-crowdstrike Addon has been installed and configured.
    search `cs_get_index` | stats count by sourcetype

In particular, you should see below sourcetype:
* crowdstrike:falconhost:json
* crowdstrike:falconhost:query:json

* To troubleshoot any modular input issues of Crowdstrike Addon, check $SPLUNK_HOME/var/log/splunk/ta-crowdstrike_falcon_host_api.log and $SPLUNK_HOME/var/log/splunk/ta-crowdstrike_ucc_lib.log files.
* To troubleshoot any Workflow action and custom command related issues, check specific log file under location $SPLUNK_HOME/var/log/crowdstrike/

SUPPORT
------------------------------
* Support Offered: Yes
* Support Email: integrations@crowdstrike.com

Copyright (C) by CrowdStrike. All Rights Reserved.
