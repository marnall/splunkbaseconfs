# Pensando DSS App for Splunk


## OVERVIEW
The "Pensando DSS App for Splunk" provides several visualizations to view the Pensando DSS logs.

* Author - Pensando
* Version - 1.0.0
* Build - 5
* Prerequisites - This application is dependent on "Pensando Add-on for Splunk" (TA-Pensando)


## COMPATIBILITY MATRIX
* Browser: Chrome, Safari, and Firefox
* OS: Platform Independent
* Splunk Enterprise version: 8.0.X, 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment


## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. **Pensando Add-on for Splunk**, which parses data collected from the Pensando DSS platform.
    2. **Pensando DSS App for Splunk**, which adds dashboards to visualize this data.

* This app can be set up in two ways:

**1) Standalone Mode**:

* Install the "Pensando DSS App for Splunk" and "Pensando Add-on for Splunk" on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
* The "Pensando DSS App for Splunk" uses the data parsed by "Pensando Add-on for Splunk" and builds dashboards on it.

**2) Distributed Environment**:

* Install the "Pensando DSS App for Splunk" and "Pensando Add-on for Splunk" on the search head.
* User needs to manually create an index on the Indexer (No need to install "Pensando DSS App for Splunk" on Indexer).


## INSTALLATION
"Pensando DSS App for Splunk" can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.


## CONFIGURATION

### Configure Index in Macro:
    
If the user has selected a default index (**Note**: *By default, Splunk considers `main` index as default index*) while configuring inputs for Pensando DSS logs, then no need to perform this step. But if the user has given any other index, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "Pensando DSS App for Splunk" in the "App" context dropdown.
3. Click on the `pensando_get_index` macro from the shown table.
4. In the macro definition default value will be `()`. Update the definition with the custom index you used for data collection. For example: `index="<your_index_name>"`.

**NOTE:** Make sure that the data model must not be accelerated otherwise it gives unexpected results in searches.


## MACROS

* pensando_get_index
    * If you are using a custom index in Add-on for data collection then kindly update the "pensando_get_index" macro in the app.
* summariesonly
    * If you want to visualize only accelerated data then change this macro to summariesonly=true.
    * Default value of the macro is summariesonly=false.
  

## DATA MODEL

* The app consists of one data model "Pensando" and one dataset:
    * pensando_dss - Maps Syslog data from the DSS device of the Pensando.
* The acceleration for the data model is disabled by default.
* As all the dashboards are populated using data model queries and real-time search doesn't work with the data model, all the real-time search filters are disabled.
* If you want to improve the performance of dashboards, you must need to enable the acceleration of the data model. Please follow the below steps:
    * On Splunk menu bar, Click on Settings -> Data models
    * Select "Pensando DSS App for Splunk" in the "App" context dropdown.
    * In the "Actions" column, click on Edit and click Edit Acceleration for the "Pensando" Data model. This will display the pop-up menu for Edit Acceleration.
    * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    * If acceleration is enabled, select the summary range to specify the acceleration period. The recommended acceleration period is 7 days. The acceleration period can be changed as per user convenience.
    * To save acceleration changes click on the Save button.
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the Indexer.


## REBUILDING DATA MODEL

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    * On the Splunk menu bar, Click on Settings -> Data models.
    * Select "Pensando DSS App for Splunk" in the "App" context dropdown.
    * From the list for Data models, expand the row by clicking the ">" arrow in the first column of the row for the "Pensando" Data model. This will display extra Data Model information in the "Acceleration" section.
    * From the "Acceleration" section click on the "Rebuild" link.
    * Monitor the status of "Rebuild" in the field "Status" of the "Acceleration" section. Reload the page to get the latest rebuild status.


## TROUBLESHOOTING

* If dashboards are not getting populated or found data discrepancy between the panel search result and drilldown search result:
    * Check whether you have correctly configured the index in the `pensando_get_index` macro. 
    * Also you can verify if the data is there in the index by running the search query: 
        * `index="<your_index_name>"`
    * Try expanding Time Range.

* If you found data discrepancy or unexpected results in the data while execution of searches:
    * Make sure that data model acceleration is disabled.


## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/PensandoDSSAppForSplunk
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance


## KNOWN ISSUES

* In the "DSS Network Connections" dashboard, the view of the Sankey diagram is breaking:
    * We would recommend you to select the "Time Range" filter with less range.
    * This issue happens due to the large scale of Syslog data and there will be lots of Source IP and Destination IP so the Sankey diagram is not able to handle that many values. 

* In the "DSS Network Connections" dashboard, the tooltip of the Sankey diagram is wrapping the values:
    * If the length of the value exceeds the threshold then the tooltip displays the wrapped values to adjust in the tooltip box.

* After data model acceleration data discrepancy is found in the execution of searches:
    * Make sure that the data model must not be accelerated otherwise it gives unexpected results in searches.


## OPEN SOURCE COMPONENTS AND LICENSES
Some of the components included in "Pensando DSS App for Splunk" are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* Splunk Sankey Diagram - Custom Visualization
    * version: 1.6.0
    * URL: https://splunkbase.splunk.com/app/3112/
    * Documentation: https://docs.splunk.com/Documentation/SankeyDiagram/1.6.0/SankeyDiagramViz/SankeyIntro


## SUPPORT
* Support Offered: Yes
* Support Email: splunkapp@pensando.io

### Copyright © 2022 Pensando. All rights reserved.