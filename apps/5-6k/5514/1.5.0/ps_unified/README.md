# OVERVIEW

* PureStorage Unified App for Splunk provides visualization dashboards for data collected using Purestorage Unified Technology Add-on from your FlashArrays, FlashBlades and Pure1.
* For Data collection, please install the Technology Add-on: PureStorage Unified TA available at https://splunkbase.splunk.com
* Author - PureStorage Inc
* Version - 1.5.0
* Supported Splunk versions are 9.4.x, 9.3.x, 9.2.x and 9.1.x
* Supported OS versions are CentOS and Windows
* Supported Browser versions are Chrome and Firefox

# RELEASE NOTES

* Version - 1.5.0
 * Updated the field value types in collections.conf 

* Version - 1.4.0
 * Added span filter in the following Dashboards:
    * FlashBlade > Analysis
      * Capacity
      * Performance
    * Pure1 > Anaylsis
      * Arrays
      * Volumes
      * Pods
      * File Systems
    * Pure1 > Capacity
    * Pure1 > Inventory > FlashArray > Protection Groups
    * FlashBlade > Storage > File System Details


* Version - 1.3.2
  * Added support for SAN , QoS and Queue Latency in Latency Panels for following dashboards under FlashArray > Analysis
    * Array
    * Volumes
    * Volume Groups
    * Pods

* Version - 1.3.1
  * Bugfix for Pure1 > Capacity > Total Capacity vs Used Space dashboard panel.

* Version - 1.3.0
  * Enhanced dashboard search queries, supporting APIv2
  * Bugfixes

* Version - 1.2.0
  * Added support of mirrored write in below dashboards:
    * FlashArray > Analysis > Array
    * FlashArray > Analysis > Volume
    * FlashArray > Analysis > Pod
    * Pure1 > Analysis > Array

* Version - 1.1.0
    * Added below dashboards for data collected using Pure1.
      * Overview
      * Capacity
      * Inventory
        * FlashArray
            * Volumes
            * Pods
            * File Systems
            * Protection Groups
        * Flashblade
            * Blades
            * Object store
            * File Systems
            * Policies
      * Health
        * Alerts
        * Audits
      * Analysis
        * Arrays
        * Volumes
        * Pods
        * File Systems
    * Updated Home dashboard with Pure1 details.
    * Changed the PureStorage FlashBlade Email Alert to run every hour rather than on Real Time search.
    * Added PureStorage FlashArray Email Alert and PureStorage Pure1 Email Alert for alert events with critical severity.
    * Created a kv-store based lookup to maintain a list of FlashArray AND FlashBlades configured in pure1.
    
* Version - 1.0.0
    * Combined dashboards for FlashBlade and FlashArray in a single app.
    * Added below new dashboards:
      * FlashArray
        * Pod Inventory
        * Volume Group
      * FlashBlade
        * Audits

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.
    1) Add-on app, which fetches the data from FlashBlade and FlashArray.
    2) The main app for visualizing data.

* This App can be set up in two ways:

  1) __Standalone Mode__:

    * Install the main app and Add-on app.
      * Both main app and Add-on reside on a single machine.
      * The main app uses the data collected by the Add-on app and displays them on the prebuilt dashboards

  2) __Distributed Environment__: 

    * Search head
        * Install main app and Add-on both.
        * No need to configure Add-on here.
    * Indexer
        * If you want to use a custom index for this app define it here.
          * No need to install the Add-on here.
    * Heavy Forwarder
        * Install and Configure Add-on.

# INSTALLATION IN SPLUNK CLOUD

* Same as an on-premise setup.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or from the command line using the following command:
    ```sh
    $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/ps_unified.spl/
    ```
* User can directly extract SPL file  into $SPLUNK_HOME/etc/apps/ folder.

# UPGRADATION OF APP
Follow the below steps to upgrade the App

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the PureStorageUnifiedApp installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

## Upgrading to version 1.5.0 from 1.4.0
* User needs to rebuild the Data model after upgrading the app. Follow the REBUILDING DATA MODEL section.

## Upgrading to version 1.4.0 from 1.3.2
* User needs to rebuild the Data model after upgrading the app. Follow the REBUILDING DATA MODEL section.

## Upgrading to version 1.3.2 from 1.3.1
* User needs to rebuild the Data model after upgrading the app. Follow the REBUILDING DATA MODEL section.

## Upgrading to version 1.3.1 from 1.3.0
* User needs to rebuild the Data model after upgrading the app. Follow the REBUILDING DATA MODEL section.

## Upgrading to version 1.3.0 from 1.2.0
* User needs to rebuild the Data model after upgrading the app. Follow the REBUILDING DATA MODEL section.

## Upgrading to version 1.2.0 from 1.1.0
* User needs to rebuild the Data model after upgrading the app. Follow the REBUILDING DATA MODEL section.
## Upgrading to version 1.1.0 from 1.0.0
* Follow the `UPGRADATION OF APP` section.
* After completion of the above upgradation steps, update the "get_ps_flasharray_index" macro if you are using a custom index in Add-on for FlashArray data collection.


# Macros

* get_ps_flashblade_index
    * If you are using a custom index in Add-on for FlashBlade data collection then kindly update "get_ps_flashblade_index" macro in the app.
* get_ps_flasharray_index
    * If you are using a custom index in Add-on for FlashArray data collection then kindly update "get_ps_flasharray_index" macro in the app.
* get_ps_pure1_index
    * If you are using a custom index in Add-on for Pure1 data collection then kindly update "get_ps_pure1_index" macro in the app.
* summariesonly
    * If you want to visualize only accelerated data then change this macro to summariesonly=true.
    * Default value of the macro is summariesonly=false.
* The macros listed below are used internally by the data model and dashboard panel queries:
    * get_ps_flasharray_array
    * get_ps_flasharray_hosts
    * get_ps_flasharray_logs_alerts
    * get_ps_flasharray_logs_audit
    * get_ps_flasharray_logs_login
    * get_ps_flasharray_pgroups
    * get_ps_flasharray_pods
    * get_ps_flasharray_snapshots
    * get_ps_flasharray_vgroups
    * get_ps_flasharray_volumes

# Macros Configuration
  * Go to `Settings` -> `Advanced search` -> `Search Macros`.
  * Select "* PureStorage Unified App for Splunk" in the App context.
  * Click on `get_ps_flashblade_index`, `get_ps_flasharray_index` or `get_ps_pure1_index` macro that you want to configure.
  * Update the `Definition` field as per requirements.
  * Click on the `Save` button.

# Alerts

* PureStorage FlashBlade Email Alert
    * This alert will be triggered every hour for alert events with 'Critical' severity obtained from FlashBlade Server.
    * By default, the alert will be disabled.
* PureStorage FlashArray Email Alert
    * This alert will be triggered every hour for alert events with 'Critical' severity obtained from FlashArray Server.
    * By default, the alert will be disabled.
* PureStorage Pure1 Email Alert
    * This alert will be triggered every hour for alert events with 'Critical' severity obtained from the Pure1 platform.
    * By default, the alert will be disabled.
  
# Alerts Configuration

  * Enable Alerts
    * Go to `Alerts` under `Notification` on the navigation bar.
    * Click on Edit for `PureStorage FlashBlade Email Alert`, `PureStorage FlashArray Email Alert` or `PureStorage Pure1 Email Alert` which you want to enable.
    * In the dropdown click on `Enable`

  * Email ID on which the mail is intended should be set in the App, to do that follow the steps
    * Go to `Alerts` under `Notification` on the navigation bar.
    * Click on Edit for `PureStorage FlashBlade Email Alert`, `PureStorage FlashArray Email Alert` or `PureStorage Pure1 Email Alert` which you want to configure.
    * In the dropdown click on `Edit Alert`
    * Under the 'Trigger Action' section write your Email ID in the `To` field
    * Click on Save

# Savedsearches

  * PureStorage Pure1 Array Mapping
    The savedsearch is used to update lookup pure1_array_mapping_lookup, mapping the array id and array name from the pure1 data collected to its type.
  * The savedsearch is triggered every 5 mins.
  * Disable this savedsearch if you are not collecting data from Pure1 and make sure it is Enabled if you are collecting Pure1 data from the Add-on.
    * Enable/Disable Savedsearch
      * Go to `Searches,reports and alerts` under `settings` on the navigation bar.
      * Select `PureStorage Unified App for Splunk` in the App context.
      * The `Status`  column corresponding to `PureStorage Pure1 Array Mapping` indicates its current status.
      * Click on Edit for `PureStorage Pure1 Array Mapping`
      * In the dropdown click on `Enable` or `Disable` as per requirement.
  
  
# DATA MODEL

* The app consists of three data models PureStorage FlashBlade, PureStorage FlashArray and Purestorage Pure1. 
  * The acceleration for these data models is disabled by default. 
  * Please enable the data model acceleration for the dashboards to work.
  * The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.
* Major portion of the dashboard panels are populated using data model queries and real-time search doesn't work with the data model, all the real-time search filters are disabled.

# DATA MODEL CONFIGURATION

* The Data Model used in this application is not accelerated. 
  * Admin should manually accelerate the Data Model.
* The recommended acceleration period is 7 days. Admin can enable/disable acceleration or change the acceleration period by the following steps for PureStorage FlashBlade, PureStorage FlashArray and Purestorage Pure1 data model:
    * On Splunk menu bar, Click on Settings -> Data models
    * From the list for Data models, click Edit in the "Action" column of the row for the <PureStorage FlashBlade> or <PureStorage FlashArray> or <Purestorage Pure1> Data model.
    * From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    * If acceleration is enabled, select the summary range to specify the acceleration period.
    * To save acceleration changes click on the Save button.

# REBUILDING DATA MODEL

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    * On the Splunk menu bar, Click on Settings -> Data models.
    * From the list for Data models, expand the row by clicking the ">" arrow in the first column of the row for the <PureStorage FlashBlade> or <PureStorage FlashArray> and <Purestorage Pure1> Data model. This will display extra Data Model information in the "Acceleration" section.
    * From the "Acceleration" section click on the "Rebuild" link.
    * Monitor the status of the "Rebuild" in the field "Status" of the "Acceleration" section. Reload the page to get the latest rebuild status.

# Known Issues
* Version - 1.1.0
 * In the Home dashboard under the Pure1 Overview section, the Capacity by FlashArray(s) panel has a File Systems column that displays "-" as the data for this column is not present in the API response. Once this API issue is resolved, these values will be displayed in the column instead of "-".
 * In Capacity dashboard under Pure1 tab when System selected is FlashArray, File Systems panel Shows "No results Found" as the data for this is not present in the API response. Once this API issue is resolved, these values will be displayed in the panel instead of "-".


# TROUBLESHOOTING

* If dashboards are not getting populated:
    * Check "get_ps_flashblade_index", "get_ps_flasharray_index" and "get_ps_pure1_index" macro is updated if you are using the custom index.
    * Check either the data model is accelerated or "summariesonly" macro is updated with summariesonly=true.
    * Make sure you have data in the given time range.
    * To check flashblade, flasharray or Pure1 data is collected or not, run the query "\`get_ps_flashblade_index\` | stats count by sourcetype" for flashblade, "\`get_ps_flasharray_index\` | stats count by sourcetype" for flasharray and "\`get_ps_pure1_index\` | stats count by sourcetype" for Pure1 in the search.
        * In particular, there should be below sourcetypes for FlashBlade:
            * purestorage:flashblade:array
            * purestorage:flashblade:alerts
            * purestorage:flashblade:health
            * purestorage:flashblade:inventory
            * purestorage:flashblade:performance
            * purestorage:flashblade:space
            * purestorage:flashblade:audit
        * In particular, there should be below sourcetypes for FlashArray:
            * purestorage:flasharray:array
            * purestorage:flasharray:hosts
            * purestorage:flasharray:alerts
            * purestorage:flasharray:audit
            * purestorage:flasharray:login
            * purestorage:flasharray:pgroups
            * purestorage:flasharray:pod
            * purestorage:flasharray:snapshots
            * purestorage:flasharray:vgroup
            * purestorage:flasharray:volumes
        * In particular, there should be below sourcetypes for Pure1:
            * purestorage:pure1:alerts
            * purestorage:pure1:audits
            * purestorage:pure1:filesystems
            * purestorage:pure1:filesystems:performance
            * purestorage:pure1:flasharray:array
            * purestorage:pure1:flasharray:performance
            * purestorage:pure1:flasharray:pods
            * purestorage:pure1:flasharray:snapshots
            * purestorage:pure1:flasharray:volumes
            * purestorage:pure1:flashblade:array
            * purestorage:pure1:flashblade:health
            * purestorage:pure1:flashblade:inventory
            * purestorage:pure1:flashblade:performance
            * purestorage:pure1:space
    * Try expanding TimeRange.
* If Arrays input dropdowns are not populated for dashboards:
  * Ensure that `PureStorage Pure1 Array Mapping` Savedsearch is Enabled.
  * Check if pure1_array_mapping_lookup lookup has been populated by running the below search query:
    * `|inputlookup pure1_array_mapping_lookup where array_type="FlashArray"` for FlashArray Arrays
    * `|inputlookup pure1_array_mapping_lookup where array_type="FlashBlade"` for FlashBlade Arrays
  * The above mentioned lookup is updated every 5 minutes, so wait for 5 minutes after data is collected for the lookup to be updated.
  * If you have started data collection for pure1 on the Add-on before installation or upgradation of this App or when the savedsearch `PureStorage Pure1 Array Mapping` was disabled, The `PureStorage Pure1 Array Mapping` savedsearch may be invoked after 5 minutes of Pure1 data collection and the lookup may not be populated on the first invocation of the Pure1 modular input in the Add-on.In this case, you can manually execute Savedsearch `PureStorage Pure1 Array Mapping` in your required time-range filter. To do this, follow the below steps:
    * Go to `Searches,reports and alerts` under `settings` on the navigation bar.
    * Select `PureStorage Unified App for Splunk` in the App context.
    * Click on `Run` in the Actions column against `PureStorage Pure1 Array Mapping` savedsearch. Here update the value of the time range from the Last 6 minutes to your required value (the Time range in which pure1 data is collected).


# UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/ps_unified
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# Known Issues:

* TA will fetch live data for native FlashArray. If the input is disabled for a given time, then data for that duration won't be collected so you may observe a gap for that duration in time charts.
* Mirrored write may not work for Pure1 if the configured FlashArrays return zero values for mirrored write fields.
* Below columns will not be populated because these fields are not coming for FlashArray API v1.
  * FlashArray > Audit > Audit Trials > Origin
  * FlashArray > Audit > Session Activities > End Time
  * FlashArray > Alerts > Alerts > State, Updated

# SUPPORT

* Access questions and answers specific to PureStorage Unified App at https://answers.splunk.com.
* Support Offered: yes
* Support Email: splunk-app@purestorage.com
* Please visit https://answers.splunk.com, and ask your question regarding PureStorage Unified App. Please tag your question with the correct App Tag, and your question will be attended to.

### Copyright (c) 2025 Pure Storage, Inc. All Rights Reserved
