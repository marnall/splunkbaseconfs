CrowdStrike App for Splunk
======================================================================

OVERVIEW
------------------------------
The CrowdStrike App for Splunk allows users to upload IOCs on falcon platform, run searches on indexed data and build dashboards using it.

* Author - CrowdStrike
* Version - 1.0.4
* Build - 1
* Creates Index - False
* Compatible with:
    - Splunk Enterprise version: 6.4.x, 6.5.x, 6.6.x and 7.0.x
    - OS: Platform independent
* Prerequisites: Installed and configured CrowdStrike Falcon Intelligence Add-on OR CrowdStrike Add-on.


RELEASE NOTES
------------------------------
* Version 1.0.4
  - Fixed issue of not able to upload IOC.

* Version 1.0.3
  - Modified drilldown query of 'Indicators over Time' panel of Falcon Intelligence Dashboard.
  
* Version 1.0.2
  - Modified Audit Dashboard to consider events of all authentication types.

* Version 1.0.1
  - Removed dependancy of Technology Addon and added requests module in main APP to do API call
  
* Version 1.0.0
  - Audit Dashboard
  - Indicator Summary Dashboard
  - Asset Details Dashboard
  - Detection Details Dashboard
  - Falcon Intelligence Indicator Details Dashboard
  - Upload IOC to Falcon
 

RECOMMENDED SYSTEM CONFIGURATION
----------------------------------------------------------
* Standard Splunk configuration of Search Head.


TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
-----------------------------------------------------------
* This app has been distributed in two parts.

    1) Add-on app, which listens for data from CrowdStrike Falcon platform using REST API Calls.
    
    2) The main app for allowing user to upload IOCs on Falcon Platform and visualizing CrowdStrike data.

* This App can be set up in two ways:

  1) __Standalone Mode__: Install the main app and Add-on app.

  * Here both the app reside on a single machine.
  * The main app uses the data collected by Add-on app and builds dashboard on it

  2) __Distributed Environment__: Install the main app and Add-on app on search head. Add-on app on forwarder.

  * Configure Account and Input settings of Add-on on forwarder.
  * Configure Account settings of TA-crowdstrike on search head.
  * Configure Data Inputs of Add-on only on forwarder.
  * The main app on search head uses the collected data and builds dashboards on it.
  * By default, all the data is indexed in "main" index. If custom Index is defined, Add index on Indexer.


INSTALLATION
------------------------------
* This app can be installed through UI using "Manage Apps" or from the command line using the following command:
    ```sh
    $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/CrowdStrike.spl/
    ```
* User can directly extract SPL file into $SPLUNK_HOME/etc/apps/ folder.


INSTALLATION IN SPLUNK CLOUD
-------------------------------
* Install and configure TA on heavy forwarder and forward data to cloud instance.


DATA MODEL CONFIGURATION
------------------------------
Data models for Intelligence TA must be accelerated to improve performance. To accelerate Data models, follow below steps:
    1. Go to "Settings" -> "Data Models"
    2. Select "CrowdStrike App for Splunk" app in the filter.
    3. Click on "Edit" action for the data model you want to accelerate.
    4. Click on "Edit Acceleration".
    5. Check the "Accelerate" checkbox and select "Summary Range" ("1 Day" is recommended).
    6. Click on "Save".
    

REBUILDING DATA MODEL
------------------------------
* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:

    1. On Splunk’s menu bar, Click on Settings -> Data models.
    2. From the list for Data models, expand the row by clicking “>" arrow in the first column of the row for the Data model for which acceleration needs to be rebuild. This will display an extra Data Model information in "Acceleration" section.
    3. From the "Acceleration" section click on "Rebuild" link.
    4. Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get latest rebuild status.
    

TROUBLESHOOTING
------------------------------

The main app dashboard can take some time before the data is returned which will populate some of the panels. A good test to see that you are receiving all of the data we expect is to run below searches after several minutes:

* Execute below search in case TA-crowdstrike_falcon_intel Addon has been installed and configured.
    search `cs_get_intelligence_index` | stats count by sourcetype

In particular, you should see below sourcetype:
* crowdstrike:falcon:intelligence

* Execute below search in case TA-crowdstrike Addon has been installed and configured.
    search `cs_get_index` | stats count by sourcetype

In particular, you should see below sourcetype:
* crowdstrike:falconhost:json
* crowdstrike:falconhost:query:json

* To troubleshoot Crowdstrike application, check specific log files under location $SPLUNK_HOME/var/log/crowdstrike/ .

REFERENCES
-----------------------------
* We have used external library requests(version: 2.11.0) to make https requests.
  https://pypi.python.org/pypi/requests/2.11.0

SUPPORT
------------------------------
* Support Offered: Yes
* Support Email: integrations@crowdstrike.com

Copyright (C) by CrowdStrike. All Rights Reserved.