# CyCognito App for Splunk

## OVERVIEW

* The CyCognito App uses the data that are indexed in Splunk via add-on for Data Visualization. 
The CyCognito App for Splunk will present dashboards for
    * Attack Surface Overview
    * Assets
    * Issues
* Author - CyCognito, Ltd.
* Version - 1.1.1
* Build - 1
* Pre-requisites - CyCognito Add-on for Splunk
* Creates Index - False

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Platform independent
* Splunk Enterprise version: 9.2.x, 9.1.x and 9.0.x
* Supported Splunk ES version: 7.0.x
* Supported CyCognito Platform: CyCognito Platform Release Date: 2022-06-06
* Supported Splunk Deployment: Cloud, Standalone, and Distributed Deployment 

## RELEASE NOTES

### Version 1.1.1
* Bumped the version to maintain compatibility with Splunk.

### Version 1.1.0
* Dashboard enhancements.

### Version 1.0.0
* Added "Attack Surface Overview" dashboard.
* Added "Assets" dashboard.
* Added "Issues" dashboard.

## RECOMMENDED SYSTEM CONFIGURATION
* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This integration has been distributed in two parts
    * CyCognito Add-on for Splunk: It collects data from CyCognito platform.
    * CyCognito App for Splunk: It is used for visualizing CyCognito data.
* This app can be set up in two ways:
    * Standalone Mode:
        * Install the CyCognito App for Splunk and CyCognito Add-on for Splunk.
        * The CyCognito App for Splunk uses the data collected by CyCognito Add-on for Splunk and builds the dashboard on it.
    * Distributed Environment:
        * Install the CyCognito App for Splunk and CyCognito Add-on for Splunk on the search head. The user only needs to configure an account in CyCognito Add-on for Splunk but should not create data input.
        * User needs to manually create an index on the indexer (No need to install CyCognito App for Splunk or CyCognito Add-on for Splunk on indexer).

## INSTALLATION
Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard or go to the Manage Apps in the Splunk Dashboard then click on `Browse more apps`

## UPGRADE

### From v1.1.0 to v1.1.1
Upgrade App from v1.1.0 to v1.1.1 by following the steps mentioned below:

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the 'CyCognito App for Splunk' installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

### From v1.0.0 to v1.1.0
Upgrade App from v1.0.0 to v1.1.0 by following the steps mentioned below:

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the 'CyCognito App for Splunk' installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

## CONFIGURATION
* The App does not require any specific configuration to make but in case of customized configuration of the CyCognito Add-on for Splunk, the configuration of App has to be changed.

## Configure Macros:

`get_cycognito_index`

* If the user has selected a default index (**Note**: *By default, Splunk considers only `IN (main)` index as default index*) in "Data Input" configuration during CyCognito Add-on for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in "Data Input" configuration, then perform the following steps:
    * Go to "Settings" > "Advanced search" > "Search macros".
    * Select "CyCognito App for Splunk" in "App" context dropdown.
    * Click on `get_cycognito_index` macro from the shown table.
    * In the macro definition default value will be `index IN (main)`. Update the definition with the index you used for data collection and save the configurations. For example: `index="<your_index_name>"`.

`summariesonly`

* Search data that the data model acceleration has summarized.
* Summarized data will be available once you've enabled data model acceleration for the data model. 
* By default (summariesonly=f)
* Check either the data model is accelerated or "summariesonly" macro is updated with summariesonly=true
* Make sure you have data in the given time range.


## DATA MODELS
* The CyCognito app for Splunk consist of two data models. 
    1. CyCognito_Assets
    2. CyCognito_Issues
* The acceleration for the data models are disabled by default. You can also enable the acceleration of the data model.
* Steps to enable/disable acceleration or change the acceleration period of data model:
    1. On Splunk's menu bar, click on `Settings` > `Data models`.
    2. From the list of the data model search for the "CyCognito_Assets" or "CyCognito_Issues" data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
    3. From the list of actions select `Edit Acceleration`. This will display the pop-up menu for edit Acceleration.
    4. Check or uncheck Acceleration checkbox to "Enable" or "Disable" data model acceleration period.
    5. If acceleration is enabled, select the summary range to specify the acceleration period.
    6. To save acceleration changes click on the `Save` button.
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer 

## DASHBOARD INFORMATION

* Attack Surface Overview:
    * Overview
        * Total Assets : This panel displays single value count of total number of assets in your environment.
        * Total Asset at Risk : This panel displays single value count of assets that have "security_grade" as "D" or "F" 
        * Total Active Issues : This panel displays single value count of total number of open issues.
        * Total Severe Issues :  This panel displays single value count of total number of issues that have "security_grade" as "D" or "F"
    * Risk Distribution
        * Asset Types by Grade : This panel displays the count of Assets based on Asset Type by Grade.
        * Assets by Hosting Type : This panel displays the count of Assets based on Hosting Type by Grade.
        * Assets with Severe Issues by Location : This panel displays the count of IP geolocations according to their number of assets with high and critical severity assets.
    * Risk and Remediation History
        * Issue Severity over Time : This panel displays the monthly count of issues according to their severity.
        * Asset Grades over Time : This panel displays the monthly count of assets according to their grades.


* Assets Dashboard :
    * Assets Overview : 
        * Assets by Grade : This panel displays the distribution of assets according to their security grade.
        * Assets by Status : This panel displays the distribution of assets according to their status.
        * Assets by Type : This panel displays the distribution of assets according to their type.
        * Assets by Grade over Time : This panel displays the monthly count of assets according to their grades.
        * Assets by Status over Time : This panel displays the monthly count of assets according to their status.
        * Assets by Tag : This panel displays assets by tag.
    * Vulnerability : 
        * Most Common Issue Type: This panel displays issue type that affects the largest number of assets.
    * Risk Distribution : 
        * Riskiest Locations : This panel displays the distribution of assets according to their IP geolocation and their security grades.
        * Top 1000 Assets : This pannel displays list for Top 1000 Assets


* Issues Dashboard :
    * Issues Overview 
        * Total Severe Issues: This panel displays single value count of total number of issues with high or critical severity.
        * Issues Under Investigation : This panel displays single value count of the number of issues being investigated.
        * Issues by Severity Over Time : This panel displays monthly count of issues according to their severity.
        * Issues by Status over Time : This Panel displays the monthly count of issues according to their status.
        * Issues by Severity : This Panel displays the distribution of issues according to their severity.
        * Issues by Status : This Panel displays the distribution of issues according to their status.
    * Prevalent Issues 
        * Prevalent Issue Types : This panel displays the most commonly detected types of issues in your environment.
        * Prevalent Issue Types over time : This panel displays the most frequently detected types of issues in your environment per month.
        * Issues by Tag : This panel displays issues by tag such as (Critical, High, Low, Medium)
    * Issue Distribution
        * Riskiest Locations by Issues : This panel displays Ranks IP geolocations according to the prevalence of their high-severity and critical-severity issues.
        * Top 1000 Issues : This panel displays list for Top 1000 Issues.

## TROUBLESHOOTING

* If dashboards are not getting populated:
    * Disable and Re-enable the input to recollect the data. Check the logs, it will be more verbose and will give the insights on data collection.
    * If you are using custom index, make sure that `get_cycognito_index` has been updated accordingly.
    * If you don't see data in the given time range, try expanding it.
    * To check whether is data collected or not, run "`get_cycognito_index` | stats count by sourcetype" query in the search.
* If you are still having problems, follow the steps mentioned in [LINK](https://docs.splunk.com/Documentation/Splunk/8.2.6/Troubleshooting/Generateadiag) to generate diag and send to CyCognito support 

## Known Issues

* `Riskiest Locations` panel on Assets dashboard, `Issues by Tag` and `Riskiest Locations by Issues` panel on Issues dashboard - For this panels the count of values on the panel and count of values on the drilldown may not match due to mutiple locations and tags values linked to the same asset or issue.

## UNINSTALL APP
- To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the CyCognitoAppforSplunk folder from apps directory -> Restart Splunk

# OPEN SOURCE COMPONENTS AND LICENSES
* Some of the components included in CyCognito App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* Underscore JS
    * version: 1.6.0
    * URL: http://underscorejs.org
    * LICENSE: https://github.com/jashkenas/underscore/blob/master/LICENSE

## END USER LICENSE AGREEMENT
https://www.cycognito.com/terms-of-service

## CONTACT

Contact Information: https://www.cycognito.com/contact

## COPYRIGHT

- (c) CyCognito, Ltd. 2026

