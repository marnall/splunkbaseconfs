## JupiterOne App for Splunk

## OVERVIEW

* The JupiterOne App uses the data that are indexed in Splunk via add-on for Data Visualization. The JupiterOne App for Splunk will provide the below dashboard:
    * J1 Alerts
* Author - JupiterOne, Inc.
* Version - 1.2.0

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Platform independent
* Splunk Enterprise version: 8.0.X, 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone and Distributed Deployment

## RELEASE NOTES
### Version 1.2.0
* Updated the App logo.

### Version 1.1.0
* Added drilldown to "Count" field of "Active Alert Details" panel of "J1 Alerts" dashboard which displays the raw events of alert related entities if alert related entities are collected.

### Version 1.0.0
* Added "J1 Alerts" dashboard.

## RECOMMENDED SYSTEM CONFIGURATION
* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    * JupiterOne Add-on for Splunk: It collects data from JupiterOne platform.
    * JupiterOne App for Splunk: It is used for visualizing JupiterOne data.
* This app can be set up in two ways:
    * Standalone Mode:
        * Install the JupiterOne App for Splunk and JupiterOne Add-on for Splunk.
        * The JupiterOne App for Splunk uses the data collected by JupiterOne Add-on for Splunk and builds the dashboard on it.
    * Distributed Environment:
        * Install the JupiterOne App for Splunk and JupiterOne Add-on for Splunk on the search head. The user only needs to configure an account in JupiterOne Add-on for Splunk but should not create data input.
        * User needs to manually create an index on the indexer (No need to install JupiterOne App for Splunk or JupiterOne Add-on for Splunk on indexer).

## INSTALLATION
Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## CONFIGURATION
* The App does not require any specific configuration to make but in case of customized configuration of the JupiterOne Add-on for Splunk, the configuration of App has to be changed.

## UPGRADE
### From v1.1.0 to v1.2.0
* No special steps are required to upgrade the JupiterOne App for Splunk from version 1.1.0 to version 1.2.0

### From v1.0.0 to v1.1.0
* No special steps are required to upgrade the JupiterOne App for Splunk from version 1.0.0 to version 1.1.0

## Configure Macros:
* If the user has selected a default index (**Note**: *By default, Splunk considers only `main` index as default index*) in "Data Input" configuration during JupiterOne Add-on for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in "Data Input" configuration, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "JupiterOne App for Splunk" in "App" context dropdown.
3. Click on `jupiterone_get_index` macro from the shown table.
4. In the macro definition default value will be `index="main"`. Update the definition with the index you used for data collection and save the configurations. For example: `index="<your_index_name>"`.


## DASHBOARD INFORMATION
* J1 Alerts dashboard :
    * It has following panels:
        * Active Alerts : This panel gives single value count of alerts that are currently active.
        * Dismissed Alerts : This panel gives single value count of alerts that are dismissed. 
        * Active Alerts By Severity : This panel provides the bifurcation of alerts according to the severity.
        * Alerts Updated Over Time : This panel provides the count of active/dismissed alerts that were updated with relative to time period. 
        * Active Alert Details :  This panel provides the detailed information of the alerts that are currently active.

## TROUBLESHOOTING
* If dashboards are not getting populated:
    * Make sure if you are using the custom index, then check that `jupiterone_get_index` macro needs to be updated.
    * Make sure you have data in given time range.
    * To check whether is data collected or not, run "`jupiterone_get_index` | stats count by sourcetype" query in the search.
    * Try expanding TimeRange.

## UNINSTALL APP
- To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the JupiterOneAppforSplunk folder from apps directory -> Restart Splunk

# OPEN SOURCE COMPONENTS AND LICENSES
* Some of the components included in JupiterOne App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* Underscore JS
    * version: 1.6.0
    * URL: http://underscorejs.org
    * LICENSE: https://github.com/jashkenas/underscore/blob/master/LICENSE

## END USER LICENSE AGREEMENT
https://jupiterone.com/terms/

## SUPPORT
* Support Offered: Yes
* Support Email: <support@jupiterone.com>

### Copyright 2021 JupiterOne, Inc.
