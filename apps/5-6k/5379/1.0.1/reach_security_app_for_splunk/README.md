# Reach Security App For Splunk

## This is an app powered by the Splunk Add-on Builder

## OVERVIEW

* This application can be used for the following purposes:
  * To search, anonymize and export specific identity and security event logs from Splunk to Reach.
  * You can choose to send these logs to Reach automatically, once at a time, or download them as a csv zip locally.

* Author - Reach Security, Inc
* Version - 1.0.1
* Build - 32
* Prerequisites - Require data collected from below apps:
  * Active Directory Data: https://docs.splunk.com/Documentation/Splunk/latest/Data/MonitorActiveDirectory
  * Proofpoint TAP Data: https://splunkbase.splunk.com/app/3681
  * Palo Alto Networks PAN-OS Data: https://splunkbase.splunk.com/app/2757
* Compatible with:
  * Splunk Enterprise version: 8.1.x, 8.0.x
  * OS: Platform independent

## END USER LICENSE AGREEMENT

https://drive.google.com/file/d/1tRpFky5UJxmOOpGX1HAPpEgnm4Mo_mbs/view?usp=sharing

## OPEN SOURCE COMPONENTS AND LICENSES

There are no third party component used for this application.

## RELEASE NOTES

* Version 1.0.1
  * Query optimization for updating the macros.

* Version 1.0.0
  * Welcome Dashboard
  * Configuration Screen
  * Export Dashboard
    * This is having execute functionality (for triggering search and anonymize data). User can also download the anonymized zip file from the same screen
  * Troubleshooting

## RECOMMENDED SYSTEM CONFIGURATION

* Splunk system should have 12 GB of RAM and a six-core CPU to run this application smoothly.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This application can be set up in two ways:

1) Standalone Mode: Install the App on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup
2) Distributed Environment: Install App on search head for executing the search functionality.

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

## UPGRADE

Follow the below steps when upgrading from Reach Security App For Splunk

* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.

## CONFIGURATION

Follow the below steps for configuring Reach Security App For Splunk
* Go to Configuration Screen
* You will find three tabs over there
  * App Settings
    * Automatic Search & Export: This will be used if you want to turn on periodical search on specific interval and export automatically
    * Reach URL: Provide endpoint URL for exporting data
    * Reach API Key: Provide API Key For Reach endpoint
    * Interval: Provide the script interval for Automatic search and Export
    * Starts From: Number of days to search the data and export or download csv zip file
    * Products: Products data you want in the csv zip file
    * Anonymize Fields: Toggle button for anonymize fields or not
  * Proxy
    * Enable: Toggle button for Proxy flag
    * Proxy Type: Select Proxy Type
    * Host: Provide Host URL
    * Port: Provide Proxy Port
    * Username: Provide Username of proxy
    * Password: Provide Password of proxy
  * Logging
    * Select Logging level for debugging purpose

If user is using search head cluster environment then user needs to follow extra steps. Steps are mentioned below:
* Go to Search Head deployer. Create server.conf in app local($SPLUNK_HOME/etc/apps/reach_security_app_for_splunk)
* Add below stanza:
    [shclustering]
    conf_replication_include.reach_security_app_for_splunk_settings = true
* Push the bundle

## Dashboards

### Welcome
* This dashboard is having two panels: Welcome Panel, Configured Data Sources (Last 90 days)
  * Welcome Panel: This is having basic informatioon for Reach App and information about supported products.
  * Configured Data Sources (Last 90 days): This will show up the configured sources on the Splunk instace.

### Configuration
* This app is having configuration screen and user have to configure the app mentioned in the Configuration section.

### Export
* This dashboard will be used for one time search and download the csv zip locally. This dashboard will show Last Successful Execution and also it will show the status "In Progress" in case of search is running on the instance.
* User can download the csv zip or they can send it to the Reach endpoint.

### Troubleshooting
* This dashboard will help user to troubleshoot the application and they can see the Error logs.
  * Reach Security App Error Logs in Last 24 hours: This will show the count of errors in last 24 hours
  * Reach Security App Error Logs Trend: This will show the Error trend over time
  * Reach Security App Logs: This will show the raw logs for debugging purpose.



## TROUBLESHOOTING

### The configuration page is not loading

* Check log file for possible errors/warnings: $SPLUNK_HOME/var/log/splunk/splunkd.log

### Download button is not clickable on Export dashboard

* Go to Search tab. Hit the following query `index="_internal" source="*reach*"` and check the results.
* Verify the filters configured during data collection are valid and such events exist on the platform.
* Check the log file related to data collection is generated under `$SPLUNK_HOME/var/log/splunk/reach_single_execution.log` or `$SPLUNK_HOME/var/log/splunk/reach_periodic_execution.log`.
* To get the detailed logs, in the Splunk UI, navigate to Reach Security App For Splunk. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
* Check the logs. There will be more verbose and will give the user insights on search execution.

### If you are not seeing file name on Export dashboard in case of Load balancer

* Click on execute button for re-executing the search for creating csv zip file 

### If the Splunk Instance is behind a proxy, Configure Proxy settings by navigating to Reach Security App For Splunk -> Configuration -> Proxy

## UNINSTALL APP

To uninstall app, user can follow below steps: SSH to the Splunk instance Go to folder apps($SPLUNK_HOME/etc/apps) Remove the reach_security_app_for_splunk folder from apps directory Restart Splunk

Copyright (C) 2020 Reach Security, Inc. All rights reserved.