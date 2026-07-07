# Netskope App For Splunk

## OVERVIEW

* The App delivers a user experience designed to make Splunk immediately useful and relevant for typical tasks and roles. The Netskope App for Splunk will provide the below functionalities:  
  * Dashboards to visualize the Netskope data.
  * The App uses data collected by the Netskope Add-on to present the above dashboards.

* Author - Netskope, Inc.
* Version - 2.4.1
* Build - 1
* Prerequisites - Netskope Add-on for Splunk
* Compatible with:  
  * Splunk Enterprise version: 10.0.x, 9.4.x, 9.3.x, 9.2.x
  * OS: Platform independent

## END USER LICENSE AGREEMENT

https://www.netskope.com/software-eula

## DOWNLOAD

* Download Netskope Add-on For Splunk at https://splunkbase.splunk.com/app/3808/.
* Download Netskope App For Splunk at https://splunkbase.splunk.com/app/3414/.

## RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This App can be set up in two ways:

1) Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup  
2) Distributed Environment: Install app on search head.

* App resides on search head machine to visualize the data coming from forwarders.

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

### DATA MODEL

* The app consist of one data model "Netskope". The datamodel has all required fields used in the dashboard of Web Transactions.
* The acceleration for the data model is disabled by default. Please enable the data model acceleration for the dashboards to work.
* The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.


### DATA MODEL CONFIGURATION

* Admin can enable/disable acceleration or change the acceleration period by following the below steps:
On Splunk's menu bar, Click on Settings -> Data models
*From the list of Data models, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
* From the list of actions select Edit Acceleration. This will display pop-up menu for Edit Acceleration.
Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
* If acceleration is enabled, select a summary range to specify acceleration period.
* To save acceleration changes click on save button.

### CUSTOM INDEX CONFIGURATION FOR DATA MODEL

* If you are ingesting Netskope web transaction data in a custom index then follow the below steps to update the index in the data model:
1. On Splunk's menu bar, Click on Settings -> Data models
2. From the list of Data models, click "Edit" in the "Action" column of the row for the "Netskope" Data model.
3. Click on "Edit Datasets" and edit the index by clicking on the "Edit" button visible at index raw.
4. Click on the save button.

### SUMMARIESONLY MACRO

*  In the tstats query search summariesonly referes to a macro which indicates (summariesonly=true) meaning only search data that has been summarized by the data model acceleration. Summarized data will be available once you've enabled data model acceleration for the data model Netskope.
* By default it has been set to false.

## UPGRADE

### v2.x.x to v2.4.1
* No additional steps are required.

### Upgradation is not supported from the older version to v2.0.0

## TROUBLESHOOTING

### Not showing any data in Web transaction dashboard despite having data in custom index

* In this case please do the steps given in "CUSTOM INDEX CONFIGURATION FOR DATA MODEL".

## UNINSTALL APP

To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the NetSkopeAppForSplunk folder from apps directory -> Restart Splunk

## SUPPORT

### Questions and Answers

* Access questions and answers specific to Netskope App/Add-on For Splunk at https://answers.splunk.com. Be sure to tag your question with the App.

### Support

* Support Email: support@netskope.com
* Support Offered: Email  
Support is available via email at support@netskope.com. Responses vary on working days between working hours.

## COPYRIGHT INFORMATION

Copyright (C) 2025 Netskope, Inc. All rights reserved.

## RELEASE NOTES

### Version 2.4.1

* Bumped the App version.

### Version 2.4.0

* Removed About page.
* Fixed "Web transaction" data model not working with custom index.
* Fixed "Network Detail" dashboard console errors

### Version 2.3.0

* Updated query for latency panel in Web Transaction V2 dashboard.
* Addded panels in "Application Usage" dashboard for ingested data.

### Version 2.2.0

* Added support for Netskope Webtransactions V2 data in the existing Web Transactions dashboard.
* Added DataModel support for Netskope Web Transactions data in the existing Web Transactions dashboard.

### Version 2.1.0

* Added information of newly added data collection of network event type and changes of clients data collection.
* Added "Network Event Overview" and "Network Detail" Dashboards

### Version 2.0.0

* Removed all the Data Collection part from App and moved it to Add-on
* Added Web Transactions Dashboard
* Added "Latest Execution Statistics for Web Transactions" and "Statistics for Last Web Transaction data collection" panels in Application Health Overview
* Fixed issues in Alert Actions and Moved it to Add-On
* Migrated the App & Add-on to make it Python 2 & 3 compatible.
* Removed dashboard from App which was named as - "Application Configuration"
