# Cisco SD-WAN App for Splunk


## OVERVIEW
The "Cisco SD-WAN App for Splunk"  presents several dashboards for different types of Cisco Logs and NetFlow Data visualization, analysis, and representation. The App uses the data collected by the "Cisco SD-WAN Add-on for Splunk".

* Author - Cisco Systems, Inc
* Version - 3.1.1
* Build - 1
* Prerequisites - This application is dependent on the "Cisco SDWAN Add-on for Splunk" (ta-cisco-sdwan) and "Cisco SD-WAN HSL Add-on for Splunk" (splunk_app_stream_ipfix_cisco_hsl)


## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox & Safari
* OS: Linux, macOS, Windows
* Splunk Enterprise Version: Splunk 9.4.x, Splunk 9.3.x, Splunk 9.2.x & Splunk 9.1.x
* Supported Splunk Deployment: Standalone, Distributed & Cluster

## RELEASE NOTES

### Version 3.1.1
* Updated Splunk SDK to v2.1.0.

### Version 3.1.0
* Added additional search filters in ZBFW panels on SOC Overview Dashboard.

### Version 3.0.0
* Added new dashboards "Event Threshold Notification" and "Monitor Critical IPs" to configure custom alerts for monitoring specific keywords and critical IPs.
* Updated existing drill-downs with additional details.
* Enhanced the search queries for better search results.
* Added support for Username in syslog data
* Added extraction for Signature ID field
* Fixed regex for URLs with dash in value


### Version 2.0.0
* Added new dashboard panels of "Dropped ZBFW Flows", "Inspected ZBFW Flows", and "Network Users" on SOC Overview dashboard.
* Added support for HSL NetFlow Logs.
* Added Username column in "Top 10 Policy Hits" drilldown
* Added extraction for Username field

### Version 1.0.0
* Initial Release
* Added CIM mapping for “network” and “communicate” model
* Added field extractions for the dashboards

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer, and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. **Cisco SD-WAN Add-on for Splunk**, which parses collected Syslog and NetFlow data.
    2. **Cisco SD-WAN App for Splunk**, which adds dashboards to visualize Syslog and NetFlow data.

* This app can be set up in two ways:

**1) Standalone Mode**:

* Install the "Cisco SD-WAN App for Splunk" and "Cisco SD-WAN Add-on for Splunk" on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
* The "Cisco SD-WAN App for Splunk" uses the data parsed by the "Cisco SD-WAN Add-on for Splunk" and builds dashboards on it.

**2) Distributed Environment**:

* Install the "Cisco SD-WAN App for Splunk" and "Cisco SD-WAN Add-on for Splunk" on the search head.
* User needs to manually create an index on the Indexer (No need to install "Cisco SD-WAN App for Splunk" on Indexer).

## INSTALLATION
 Cisco SD-WAN App For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/ folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install the app from file`.
3. Click `Choose file` and select the `cisco-sdwan-app` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted. (In case of Adding .tar or .spl extracted files to directly into $SPLUNK_HOME/etc/apps/ folder, restart is required)

## OPEN SOURCE COMPONENTS AND LICENSES

* Some of the components included in the Cisco SD-WAN App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* jQuery
    * version: 3.5.0
    * URL: https://jquery.com
    * LICENSE: https://github.com/jquery/jquery/blob/main/LICENSE.txt

* Underscore JS
    * version: 1.6.0
    * URL: http://underscorejs.org
    * LICENSE: https://github.com/jashkenas/underscore/blob/master/LICENSE

* JQuery-ui
    * version: 1.12.1
    * URL: https://jqueryui.com
    * LICENSE:  https://github.com/jquery/jquery-ui/blob/main/LICENSE.txt

* MSelectDialogBox
    * URL: https://github.com/eugenegantz
    * URL: https://github.com/eugenegantz/MSelectDialogBox
    * LICENSE: This jQuery plugin is developed by eugenegantz under MIT License. 
  
* Splunk Sankey Diagram - Custom Visualization
    * version: 1.6.0
    * URL: https://splunkbase.splunk.com/app/3112/
    * Documentation: https://docs.splunk.com/Documentation/SankeyDiagram/1.6.0/SankeyDiagramViz/SankeyIntro

## CONFIGURATION

### Configure Index Macro:
    
If the user has selected a default index  (**Note**: *By default, Splunk considers the `main` index as the default index*) while configuring inputs for Syslog and NetFlow data, then no need to perform this step. But if the user has given any other index, then perform the following steps:

1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "Cisco SD-WAN for Splunk" in the "App" context dropdown.
3. Click on the `cisco_sdwan_index` macro from the shown table.
4. In the macro definition default value will be `()`. Update the definition with the custom index you used for data collection. For example: `index="<your_index_name>"`.

## MACROS

* cisco_sdwan_index
    * If you are using a custom index in Add-on for data collection then kindly update the "cisco_sdwan_index" macro in the app.
* summariesonly
    * If you want to visualize only accelerated data then change this macro to summariesonly=true.
    * Default value of the macro is summariesonly=false.
## DATA MODEL

* The app consists of Two data models "Cisco SDWAN" for Syslog data and "Cisco SDWAN Netflow" for NetFlow data :
    * Cisco_SDWAN - Maps Syslog data based on different log types.
    * Cisco_SDWAN_NETFLOW - Maps NetFlow data from Cisco SDWAN  
* The acceleration for the data model is disabled by default.
* As all the dashboards are populated using data model queries and real-time search doesn't work with the data model, all the real-time search filters are disabled.
* If you want to improve the performance of dashboards, you just need to enable the acceleration of the data model. Please follow the below steps:
    * On the Splunk menu bar, Click on Settings -> Data models
    * Select "Cisco SDWAN App for Splunk" in the "App" context dropdown.
    * In the "Actions" column, click on Edit and click Edit Acceleration for the "Cisco SDWAN" Data model. This will display the pop-up menu for Edit Acceleration.
    * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    * If acceleration is enabled, select the summary range to specify the acceleration period. The recommended acceleration period is 7 days. The acceleration period can be changed as per user convenience.
    * To save acceleration changes click on the Save button.
    * Follow the Similar Steps to Enable/Disable Acceleration Cisco_SDWAN_Netflow Data model
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the Indexer.


## REBUILDING DATA MODEL

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    * On the Splunk menu bar, Click on Settings -> Data models.
    * Select "Cisco SD-WAN App for Splunk" in the "App" context dropdown.
    * From the list of Data models, expand the row by clicking the ">" arrow in the first column of the row for the "Cisco SDWAN" Data model or "Cisco SDWAN Netflow" data model. This will display extra Data Model information in the "Acceleration" section.
    * From the "Acceleration" section click on the "Rebuild" link.
    * Monitor the status of "Rebuild" in the field "Status" of the "Acceleration" section. Reload the page to get the latest rebuild status.
## CUSTOM COMMANDS
* This application contains the following custom commands
    * aggregatebyflow - This command provides the Total Bytes passed between the Source IP and Destination IP based on query passed having Source IP and Destination with bytes passed between them
    * NOTE: Non-admin Users can not run the custom command.

## SAVEDSEARCHES
This application contains the following saved searches

* **cisco_sdwan_netflow** - Update the lookup cisco_sdwan_app_mapping from configured index that maps the app with app_tag for Netflow data.
* **cisco_sdwan_policy** - Update the lookup cisco_sdwan_policy_mapping from configured index that maps policy with policy_rule for Netflow data.
* **cisco_sdwan_action** - Update the lookup cisco_sdwan_action_mapping from configured index that maps action with action_rule for Netflow data.
* **cisco_sdwan_username** - Update the lookup cisco_sdwan_username_mapping from configured index that maps src_ip with FW_Username for Netflow data.

## LOOKUPS
* `cisco_sdwan_app_mapping`: This lookup contains the mapping between the app and app_tag for Netflow data.
* `cisco_sdwan_policy_mapping`: This lookup contains the mapping between the policy and policy_rule for Netflow data.
* `cisco_sdwan_action_mapping`: This lookup contains the mapping between the action and action_rule for Netflow data.
* `cisco_sdwan_username_mapping`: This lookup contains the mapping between the src_ip and FW_Username for Netflow data.



## TROUBLESHOOTING

* If dashboards are not getting populated or found data discrepancy between the panel search result and drilldown search result:
    * Check whether you have correctly configured the index in the `cisco_sdwan_index` macro. 
    * Also you can verify if the data is there in the index by running the search query: 
        * `index="<your_index_name>"`
    * Try expanding Time Range.

* If in SOC Dashboard "Top 10 Applications" Panel is not getting populated run the savesearch as per the given steps:
    * Go to Settings -> Searches, reports, and alerts
    * Select "Cisco SD-WAN for Splunk" in the "App" context dropdown and "All" in the "Owner" dropdown.
    * Run the "cisco_sdwan_netflow" savedsearch with "All time" time range.  

* If in SOC Dashboard "Top 10 Policy Hits" Panel is not getting populated run the savesearch as per the given steps:
    * Go to Settings -> Searches, reports, and alerts
    * Select "Cisco SD-WAN for Splunk" in the "App" context dropdown and "All" in the "Owner" dropdown.
    * Run the "cisco_sdwan_action" and "cisco_sdwan_policy" savedsearches with "All time" time range.

## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/cisco-sdwan-app
* To reflect the cleanup changes in UI, Restart the Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Email: tac@cisco.com

### Copyright (c) 2025 Cisco Systems, Inc. All rights reserved.