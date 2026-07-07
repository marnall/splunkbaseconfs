# OVERVIEW
 
* Proofpoint On Demand Email Security App will help users to provide visualization dashboards and reports for data collected using Proofpoint On Demand Email Security Add-on and Proofpoint TAP Modular Input.
* For Data collection, please install the Proofpoint On Demand Email Security Add-on and Proofpoint TAP Modular Input available at https://splunkbase.splunk.com/app/4328/ and https://splunkbase.splunk.com/app/3681/ respectively.

* Author - Proofpoint Inc
* Version - 2.1.2
* Compatible with:
  * Splunk Enterprise version: 9.1.x and 9.2.x 
  * OS Support: Linux (CentOs, Ubuntu) and Windows
  * Browser Support: Chrome, Firefox and Safari 

# Release Notes

### Version - 2.1.2
* Updated dashboards to use corresponding normalized fields.

### Version - 2.1.1
* Bumped the version to stop app archiving.

### Version - 2.1.0
* Upgraded Proofpoint On Demand Email Security App to jQuery version 3.5.0 .

### Version - 2.0.0
* Added Support for Splunk 8 and minor changes. 

# RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This App can be set up in two ways:

1. Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install App on search head only.

# INSTALLATION OF APP
Follow the below-listed steps to install an App from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

# UPGRADE

### General upgrade steps:
* Log in to Splunk Web and navigate to `Apps > Manage Apps`.
* Click `Install app from file`.
* Click `Choose file` and select the Proofpoint On Demand Email Security App installation file.
* Check the `Upgrade` checkbox.
* Click on `Upload`.
* Restart Splunk.

### Upgrade from version 2.1.1 to version 2.1.2
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security App from version 2.1.1 to version 2.1.2.

### Upgrade from version 2.1.0 to version 2.1.1
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security App from version 2.1.0 to version 2.1.1.

### Upgrade from version 2.0.0 to version 2.1.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security App from version 2.0.0 to version 2.1.0.

### Upgrade to version 2.0.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security App to version 2.0.0.

# Macros

* pps_get_index
    * If you are using a custom index(es) in Add-on for data collection then kindly update "pps_get_index" macro in the app.
* summariesonly
    * If you want to visualize accelerated data then change this macro to summariesonly=true.
    * Default value of the macro is summariesonly=false.

## Configure Macros
To configure Macros from Splunk UI,

1. Go to `Settings` -> `Advanced search` -> `Search Macros`.
2. Select "Proofpoint On Demand Email Security App" in the App context.
3. Click on `Name` of the Macro, go to `Definition` field and update it as per requirements.
4. Click on the `Save` button.

# DATA MODEL

* The app consist of one data model "Proofpoint On Demand Email Security". The acceleration for the data model is disabled by default.
* The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.

# DATA MODEL CONFIGURATION

* The Data Model used in this application is not accelerated. Admin should manually accelerate the Data Model.
* The recommended acceleration period is 7 days. Admin can enable/disable acceleration or change the acceleration period by the following steps:
    * On Splunk menu bar, Click on Settings -> Data models
    * From the list for Data models, click Edit in the "Action" column of the row for the "Proofpoint On Demand Email Security" Data model.
    * From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    * If acceleration is enabled, select the summary range to specify acceleration period.
    * To save acceleration changes click on save button.

# REBUILDING DATA MODEL

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    * On Splunk menu bar, Click on Settings -> Data models.
    * From the list for Data models, expand the row by clicking ">" arrow in the first column of the row for the "Proofpoint On Demand Email Security" Data model. This will display an extra Data Model information in "Acceleration" section.
    * From the "Acceleration" section click on "Rebuild" link.
    * Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get the latest rebuild status.

# REPORTS
* This App consists of following reports:

    * Inbound message summary
    * Outbound message summary
    * DLP summary
    * Email Authentication Rule For DKIMV
    * Email Authentication Rule For SPF
    * Email Authentication Rule For DMARC
    * TAP Dashboard Information
    * TAP Dashboard - Sender IP
    * TAP Dashboard Threats & Recipients
    * Email Volume by Recipient Domain Name
    * Email Volume by Sender Domain Name

# TROUBLESHOOTING

* If dashboards are not getting populated:
    * Check "pps_get_index" macro is updated if you are using the custom index(es).
    * Check either data model is accelerated or "summariesonly" macro is updated with summariesonly=false.
    * Make sure you have data in given time range.
    * To check data is collected or not, run "`pps_get_index` | stats count by sourcetype" query in the search.
    * Try expanding TimeRange.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/pps_ondemand
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT

* Access questions and answers specific to Proofpoint On Demand Email Security App at https://answers.splunk.com.
* Support Offered: Yes
* Support Email:
* Please visit https://answers.splunk.com, and ask your question regarding Proofpoint On Demand Email Security App. Please tag your question with the correct App Tag, and your question will be attended to.

**Copyright (c) 2024 by Proofpoint, Inc.  All Rights Reserved.**