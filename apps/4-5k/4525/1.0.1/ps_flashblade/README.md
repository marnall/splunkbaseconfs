# OVERVIEW
 
* PureStorage FlashBlade App will help users to provide visualization dashboards for data collected using Technology Add-on for PureStorage FlashBlade.
* For Data collection, please install the Technology Add-on for PureStorage FlashBlade available at https://splunkbase.splunk.com

* Author - PureStorage Inc
* Version - 1.0.1
* Supported Splunk versions are 7.0, 7.1 and 7.2

# RELEASE NOTES

  * Version - 1.0.1
    * Updated Logo.

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

    1) Add-on app, which fetches the data from FlashBlade REST API.
    
    2) The main app for visualizing data.

* This App can be set up in two ways:

  1) __Standalone Mode__:
  
Install the main app and Add-on app.

* Here both the app resides on a single machine.
* The main app uses the data collected by Add-on app and builds dashboards on it

  2) __Distributed Environment__: 

* Search head
    * Install main app and Add-on both.
    * No need to configure Add-on here.

* Indexer
    * If you are using custom index define it here.

* Forwarder
    * Install and Configure Add-on.

# INSTALLATION IN SPLUNK CLOUD

* Same as on-premise setup.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or from the command line using the following command:
    ```sh
    $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/ps_flashblade.spl/
    ```
* User can directly extract SPL file  into $SPLUNK_HOME/etc/apps/ folder.

# Macros

* get_ps_flashblade_index
    * If you are using a custom index in Add-on for data collection then kindly update "get_ps_flashblade_index" macro in the app.
* summariesonly
    * If you want to visualize only accelerated data then change this macro to summariesonly=true.
    * Default value of the macro is summariesonly=false.

# Alerts

* PureStorage FlashBlade Email Alert
    * This alert will be triggered when the alert with 'Critical' severity occurs in FlashBlade Server.
    * By default, alert will be disabled.
  
# Alerts Configuration

* PureStorage FlashBlade Email Alert
    * Enable Alert
      * Go to `Alerts` under `Notification` on navigation bar.
      * Click on Edit for `PureStorage FlashBlade Email Alert`
      * In the dropdown click on `Enable`

    * Email ID on which the mail is intended should be set in the App, to do that follow the steps
      * Go to `Alerts` under `Notification` on navigation bar.
      * Click on Edit for `PureStorage FlashBlade Email Alert`
      * In the dropdown click on `Edit Alert`
      * Under 'Trigger Action' section write your Email ID in `To` field
      * Click on Save
  
# DATA MODEL

* The app consist of one data model "PureStorage FlashBlade". The acceleration for the data model is disabled by default. Please enable the data model acceleration for the dashboards to work. 
* The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.
* As all the dashboard are populated using data model queries and real-time search doesn't work with data model, all the real-time search filters are disabled.

# DATA MODEL CONFIGURATION

* The Data Model used in this application is not accelerated. Admin should manually accelerate the Data Model.
* The recommended acceleration period is 7 days. Admin can enable/disable acceleration or change the acceleration period by the following steps:
    * On Splunk menu bar, Click on Settings -> Data models
    * From the list for Data models, click Edit in the "Action" column of the row for the "PureStorage FlashBlade" Data model.
    * From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    * If acceleration is enabled, select the summary range to specify acceleration period.
    * To save acceleration changes click on save button.

# REBUILDING DATA MODEL

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    * On Splunk menu bar, Click on Settings -> Data models.
    * From the list for Data models, expand the row by clicking ">" arrow in the first column of the row for the "PureStorage FlashBlade" Data model. This will display an extra Data Model information in "Acceleration" section.
    * From the "Acceleration" section click on "Rebuild" link.
    * Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get the latest rebuild status.


# TROUBLESHOOTING

* If dashboards are not getting populated:
    * Check "get_ps_flashblade_index" macro is updated if you are using the custom index.
    * Check either data model is accelerated or "summariesonly" macro is updated with summariesonly=true.
    * Make sure you have data in given time range.
    * To check data is collected or not, run "`get_ps_flashblade_index` | stats count by sourcetype" query in the search.
    * Try expanding TimeRange.

# SUPPORT

* Access questions and answers specific to PureStorage FlashBlade App at https://answers.splunk.com.
* Support Offered: yes
* Support Email: support@purestorage.com
* Please visit https://answers.splunk.com, and ask your question regarding PureStorage FlashBlade App. Please tag your question with the correct App Tag, and your question will be attended to.

### Copyright (c) 2019 Pure Storage, Inc. All Rights Reserved