Dtex App for Splunk
======================================================================

# Overview

Dtex Splunk app is to analyze Dtex’s unique endpoint data to find both known and unusual user activity that could be insider threat.

* Author - Dtex Systems
* Version - 3.1.1
* Build - 1
* Creates Index - False
* Compatible with:
    - Splunk: 8.x, 9.1, 9.2, 9.3, 9.4
    - Browser: Chrome, Firefox, Safari
    - OS: Linux, Windows, Mac
    - Common Information Model: 4.16.0
* Prerequisites: Installed and configured Dtex Add-on for Splunk.

# Release Notes
* Version - 3.1.1
    - Updated compatible versions, reformat readme

* Version 3.1.0:
    - Updated jQuery to v3.5.0 in the app package. This version of jQuery has security fixes and will be used by the app independently.

* Version 3.0.0:
    - Made app Python 2 and 3 compatible to support Splunk 8.0.
    - Updated dashboards as per new category IDs.
    - Added and improved dashboard drilldowns.
    - Updated 'Alerts' dashboard for better user experience.
    - Fixed minor bugs.

* Version 1.0.0:
    - Overview Dashboard
    - Incident Reports Dashboards
    - Statistics Dashboards
    - Alerts Dashboards
    - Custom Alert Actions
    - Sample Saved Searches (Disabled)

# Recommended System Configuration

* Standard Splunk configuration

# Topology and Setting Up Splunk Environment

* This app has been distributed in two parts.

    1. Dtex Add-on for Splunk, which collects data from Splunk Forwarder.
    2. Dtex App for Splunk, which adds dashboards to visualize the Dtex data.

* This app can be set up in two ways:
    
    1. **Standalone Mode**:

        * In case of deploying this App on Stand-alone Splunk Deployment, user would have to install TA on Splunk Forwarder which ideally should be on the same server as Dtex Server and do the configuration for TA as per steps mentioned in the 'Application Setup' section of Readme file of TA.
        * Post that, user can install Dtex App on Splunk instance by performing the steps mentioned in 'INSTALLATION' section below.

    2. **Distributed Environment**:

        * In case of deploying Dtex App for Splunk on distributed setup, following are the changes needed on each type of node.
        * Splunk Universal/Heavy Forwarder:
            - On Splunk Universal forwarder, install & configure TA-dtexubi and configure necessary directories as per given in 'Application Setup' section of TA's Readme file.
        * On Indexer:
            - On Splunk Indexer, user would have to install TA-dtexubi.
        * On Search-Head:
            - On Splunk Search Head, user would install the TA and App and configure only Dtex App for Splunk.

# Installation

* This app can be installed either through UI from "Manage Apps" or by extracting the compressed file into $SPLUNK_HOME/etc/apps folder.
* Restart Splunk after installation.

# Configuration

* Configure Macro:
    
  * If you have used the index "dtex" in your batch input stanzas in inputs.conf while configuring Dtex Add-on for Splunk, then no need to perform this step.
    But if a user has given any other index during configuration in Dtex Add-on for Splunk, then perform the following steps.
    * Go to Settings > Advanced search > Search macros
    * Select "Dtex App for Splunk(dtexubi)" in App context
    * Click on "dtexubi_index" macro and update definition to index=INDEX_NAME, Where INDEX_NAME should be the same index name where Dtex activities and alerts data is collected and then click Save.

# Upgrade

Follow the below steps when upgrading from the older version of App.

* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.

# Data Model Configuration

* The Data Models used in this application are not accelerated by default. Their default acceleration period is 1 month. Admin can enable/disable acceleration or change the acceleration period by the following steps:
    - On Splunk’s menu bar, Click on Settings -> Data models
	- From the list for Data models, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
	 - From the list of actions select Edit Acceleration. This will display a pop-up menu for Edit Acceleration.
	  - Check or uncheck Accelerate check box to "Enable" or "Disable" data model acceleration respectively.
	  - If acceleration is enabled, select the summary range to specify acceleration period.
	  - To save acceleration changes click on the save button.
	  

# Rebuilding Data Model

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:

    1. On Splunk’s menu bar, Click on Settings -> Data models.
    2. From the list for Data models, expand the row by clicking the ">" arrow in the first column of the row for the Data model for which acceleration needs to be rebuilt. This will display an extra Data Model information in the "Acceleration" section.
    3. From the "Acceleration" section click on the "Rebuild" link.
    4. Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get the latest rebuild status.


# Log Files

* Application setup logs are written in $SPLUNK_HOME/var/log/dtexubi/dtexubi.log
* Logs for Alert Actions are written in $SPLUNK_HOME/var/log/splunk/dtexubi_custom_modalert.log


# Savedsearches and Reports

This application contains savedsearches.conf which contains search queries used in Visualization Dashboards.

There are few sample saved searches embedded into the App, which gives understanding on how users can create different Alerts based on different scenarios and how to write specific saved searches associated with those scenarios.
All the saved searches are by default in disabled mode and would need the user to enable to get the Alerts generated using these saved searches.

The following saved searches are present in the App:

* get_zscore_alert - This saved search is used to get count of the events from Activity_Type="FileCopied" group by User, Time. The count's standard deviation and zscore is calculated and if the value of zscore is greater than configured zscore and standard deviation is greater than 0, the alert is generated.
The Alert is scheduled to run every hour.
The Alert gets the result for the last 24 hours generated data.

* get_unusual_network_transfers - This saved search is used to get the calculated bytesIN and bytesOUT in MB and then the value's Standard Deviation is calculated from that value for users. If the MB count is greater than 3, the Alert is generated.
The Alert is scheduled to run every hour.
The Alert gets the result for the last 24 hours generated data.

* get_domain_alerts - This saved search is used to get the count of the Website_Domain for specific Website_Domain group by User and Time. If the count is greater than the 50, the alert is generated. It states if the user has visited the website more than 50 times, the alert is generated. 
The Alert is scheduled to run every hour.
The Alert gets the result for the last 24 hours generated data.

* get_rare_hash_alerts - This saved search is used to get count of the events from Activity_Type="ProcessStarted" group by User, Time and Process_Checksum_SHA256. For unique Process_Checksum_SHA256, alert is generated.
The Alert is scheduled to run every hour.
The Alert gets the result for the last 24 hours generated data.

* get_threshold_alerts - This saved search is used to get the count of the Website_Domain for specific Website_Domain group by User and Time. If the count is greater than the threshold value, the alert is generated. 
The Alert is scheduled to run every hour.
The Alert gets the result for the last hour's generated data.

The following Report is also present in the App:

* Dtex_Count_Summary - This Report is used in 'User and Device Summary' dashboard. By default it is accelerated. 
Its 'Summary Range' is set to 'All Time' and its scheduled to run at every ten minutes.

# Custom Alert

* Following are the steps to create alerts:
    - Create a search. Search must contain Time and User_Name field.
    Eg: index=dtex sourcetype = dtex_st_activities	Activity_Type=ProcessStarted | stats  count by Activity_Time  User_Name | sort - count | where count > 2

    - Click on the `Save As` link on the right side corner, under that link click on Alerts.

* A pop-up window will open, in that fill the specified fields.
Reference URL:
http://docs.splunk.com/Documentation/SplunkCloud/6.6.0/Alert/Definescheduledalerts

* Click on `Add Action` drop-down.

* From the Drop-down select the `Dtex Create Custom Alerts` Action
* The Alert form will open with default values filled in the fields
* Following are the description of Fields:
    - Time : define the Time field name used to set created_time of Alert
    - Trigger Time : get the time when the alert triggered and use this as occured_time  of Alert
    - Category : select the category type of the search from drop down
    - Risk-Score : define the risk-score of the category
    - Severity : select the severity of events
    - User Name : define the User Name field name used to set User Name of Alert
* Change the value with required field names and Save.

* User can check the schedule after which the Saved searches are running. In case events get qualified under this specific search, Events can be seen in Alerts Dashboard with specific severity and Risk Category selected.

Note: By default, the events generated by the Custom Alert Action are stored at $SPLUNK_HOME/etc/apps/dtexubi/local/dtex_custom_alerts_response/ and are only indexed once user configures batch input stanza for the specified path. For example of the batch input stanza, please look at the inputs.conf.example file in Dtex Add-on for Splunk.

# Known Issues

* There is a known limitation in Splunk where App Icon doesn’t get visible before restarting Splunk. Hence, it’s recommended to restart post installation of the App to load the App Icon.
* It’s recommended to update the Alert Details, In case the sample saved searches are enabled.
* Default Splunk setting will not export PDFs in proper format in the existing App Dashboard.
* It’s recommended to update the Splunk Export settings as per following URL: https://answers.splunk.com/answers/45286/formatting-of-pdf-report.html
* As the `Dtex Create Custom Alerts` - custom alert action included in the app stores the response events in App's local folder on the machine where it is triggered and requires batch input stanza to index them, the user will not be able to index those responses on a search head cluster or distributed environment.

# Uninstall and Cleanup Steps

* Remove $SPLUNK_HOME/etc/apps/dtexubi
* Remove $SPLUNK_HOME/var/log/dtexubi
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# Troubleshooting

* If you do not see any results in search then check whether you have correctly configured index in the `dtexubi_index` macro. Also you can verify if the data is there in the index by running the search query `index="<your_index_name>"`.
* If the Custom Alerts have not generated the results, you can check the logs for it which are stored at $SPLUNK_HOME/var/log/splunk/dtexubi_custom_modalert.log
* If 'Configurations' dashboard is not loaded with default values or the values are not getting saved, you can check the logs for it which are stored at $SPLUNK_HOME/var/log/dtexubi/dtexubi.log

# EULA

Please check End User's License Agreement at https://dtexsystems.com/dtex-splunk-app-eula/

# Support

* Support Offered: Yes
* Support Email: support@dtexsystems.com

(c) Copyright Dtex Systems Inc 2025