RiskIQ Digital Footprint App For Splunk
======================================

OVERVIEW
--------
RiskIQ Digital Footprint App For Splunk helps in visualizing and analyzing data collected by RiskIQ Digital Footprint Add-on For Splunk using global inventory.

* Author - RiskIQ
* Version - 1.3.0
* Build - 1
* Creates Index - False
* Prerequisites - This application is dependent on RiskIQ Digital Footprint Add-on For Splunk

## COMPATIBILITY MATRIX

* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform Independent
* Splunk Enterprise version: 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES

### Version 1.3.0

* Upgraded jQuery to v3.5.0 in the app package. This version of jQuery has security fixes and will be used by the app independently.

### Version 1.2.0

* Added the Multiple Account support by providing a Select Business Org filter on all the dashboards which will help to visualize data for a particular business organization.

## RECOMMENDED SYSTEM CONFIGURATION

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
------------------------------------------

This App can be set up in two ways:

1. Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install App on search head only.


INSTALLATION
------------
* Install the App bundle by:
  * Download the App package.
  * In the UI navigate to: `Apps->Manage Apps`.
  * In the top right corner select `Install app from file`.
  * Select `Choose File` and select the App package.
  * Select `Upload` and follow the prompts.

UPGRADE
------------
* Follow the below steps when upgrading RiskIQGIAppForSplunk from 1.2.0 to 1.3.0

  * From the UI navigate to Apps->Manage Apps.
  * In the top right corner select Install app from file.
  * Select Choose File and select the App package.
  * Check the upgrade option.
  * Select Upload and follow the prompts.
  * Restart Splunk.
  * Once installed follow the REBUILDING DATA MODEL steps to rebuild the data models.

DASHBOARDS
----------
1. Digital Footprint Summary
    1. Digital Footprint Summary
    2. Cloud Insights
    3. Servers & Frameworks Insights
    4. Services, Apps & Devices Insights
    5. SSL Certificate Insights
    6. Vulnerability Insights
    7. At Risk Servers
2. External Threats Dashboards
    1. External Threats Summary
    2. Domain Infringement Insights
    3. Phish Insights
    4. Rogue Mobile App Insights
    5. Social Insights

DATA MODEL CONFIGURATION
------------------------
* The Data Model used in this application is not accelerated. Admin should manually accelerate the Data Model.
* The Data Model used in this application should be accelerated to achieve better performance in loading dashboard panels.
* Admin can enable/disable acceleration or change the acceleration period by the following steps:

  1. On Splunk's menu bar, Click on Settings -> Data models.
  2. From the list for Data models, Search for "RiskIQ-GlobalInventory" and "RiskIQ-Event" data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
  3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
  4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
  5. If acceleration is enabled, select the summary range to specify acceleration period.
  6. To save acceleration changes click on the save button.
* Warning: Acceleration may increase storage and processing costs.

REBUILDING DATA MODEL
---------------------
* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:

  1. On Splunk's menu bar, Click on Settings -> Data models.
  2. From the list for Data models, expand the row by clicking ">" arrow in the first column of the row for the Data model "RiskIQ-GlobalInventory" and "RiskIQ-Event" for which acceleration needs to be rebuild. This will display an extra Data Model information in "Acceleration" section.
  3. From the "Acceleration" section click on "Rebuild" link.
  4. Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get latest rebuild status.

TROUBLESHOOTING
---------------------

* If dashboards are getting populated but with inconsistent data this may be because the field extractions not working / Search stops because of memory limit reached / Events are getting truncated. 

   1. Create a file 'limits.conf' in the following directory $SPLUNK_HOME/etc/RiskIQGIAppForSplunk/local.
   2. Add the following 3 stanzas in the file:

```
      [kv]
      maxcols  = 1024
      limit    = 750
      maxchars = 1000000
      max_extractor_time = 2000
      avg_extractor_time = 1000
```  

```
      [mvexpand]
      max_mem_usage_mb =9000
```  

```  
      [lookup]
      max_memtable_bytes = 20000000
```
   3. Restart Splunk

* For the cluster environment, User needs to deploy limits.conf file on the Heavy forwarder, Indexer and Search Head.

EULA
-------
Custom EULA for RiskIQ. https://www.riskiq.com/msa/

SUPPORT
------------------------------
Contact - support@riskiq.com


### Copyright 2016 - 2022 RiskIQ