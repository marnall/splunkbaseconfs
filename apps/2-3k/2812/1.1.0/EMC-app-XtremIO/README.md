# EMC XtremIO App for Splunk Enterprise

## Overview

* The EMC XtremIO App for Splunk Enterprise allows a Splunk® Enterprise administrator to gain insight of XtremIO Cluster inventory and performance data.
* The EMC XtremIO App for Splunk Enterprise gathers the data from EMC XtremIO cluster and allows the splunk Enterprise administrator to:

    * Monitor the cluster inventory
    * Monitor the cluster performance parameters like bandwidhth, Latency and IOPS.
    * Monitor the critical events generated in a XtremIO cluster.

* Author - Crest Data Systems
* Version - 1.1.0


## Compatibility Matrix

|                                     |                                                           |
|-------------------------------------|-----------------------------------------------------------|
| Browser                             | Google Chrome, Mozilla Firefox, Safari                    |
| OS                                  | Platform independent                                      |
| Splunk Enterprise Version           | 8.2.x, 8.1.x, 8.0.x, 7.3.x                                |
| Supported Splunk Deployment         | Splunk Cloud, Splunk Standalone and Distributed Deployment|
| EMC XtremIO Version                 | 2.4 and later                                             |


## Recommended System Configuration

* Splunk search head system should have 8 GB of RAM and a quad-core CPU to run this app smoothly.


## Topology and Setting up Splunk Environment

* This app has been distributed in two parts.

    1) Add-on app, which runs collector scripts and gathers data from EMC XtremIO cluster, does
    indexing on it and provides indexed data to Main app.

    2) Main app, which receives indexed data from Add-on app, runs searches on it and builds
    dashboard using indexed data.

* This App can be set up in two ways:

    1) Deploy to single server instance

        Standalone Mode: Install main app and Add-on app on a single machine.

       * Here both the app resides on a single machine.
       * Main app uses the data collected by Add on app and builds dashboard on it.

    2) Deploy to distributed deployment

       * Install the main app and Add-on on the search head. User does not need to configure the Add-on on search head.
       * Install only Add-on on the heavy forwarder. User needs to configure setup page to collect data from EMC XtremIO cluster.


## Release Notes

* **Version 1.1.0**

    * Added support of Splunk 8.x


## Installation

Follow the below-listed steps to install an Add-On from the UI:

* Download the add-on package.
* From the UI navigate to  `Apps -> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

  **OR**

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.


## Upgradation

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package. 
* Check `Upgrade App`.
* Select `Upload` and follow the prompts.

  **OR**

* If a newer version is available on splunkbase, then App/Add-on can be updated from UI also.

    * From the UI navigate to `Apps->Manage Apps` OR click on gear icon
    * Search for "EMC XtremIO App for Splunk Enterprise".
    * Click on `'Update to <version>'` under Version Column.


## Uninstallation and Cleanup

This section provides the steps to uninstall App from a standalone Splunk platform installation.

* (Optional) If you want to remove data from the Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.

    * $SPLUNK_HOME/bin/splunk stop
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

* Delete the app and its directory. The app and its directory are typically located in the folder $SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:

    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>

* You may need to remove user-specific directories created for your app by deleting any files found here:

    * $SPLUNK_HOME/bin/etc/users/*/<appname>

* Restart the Splunk platform. You can navigate to Settings -> Server controls and click the restart button in Splunk web UI or use the following Splunk CLI command to restart Splunk:

    * $SPLUNK_HOME/bin/splunk restart


## Configuration of App

* This App doesn't need any configuration steps. Please refer the documentation of "EMC XtremIO Add-on for Splunk Enterprise" to see how to set up the Add-on app.


## Macros

* This App contains following macros.

    * **get_xtremio_index:** If you are using a custom index in Add-on for data collection then kindly update the "get_xtremio_index" macro in the app.
    * **bytes_conversion(<args>):** Used in dashboard queries for bytes conversion.
    * **get_performance_parameters:** Used in dashboard queries to get performance parameters.
    * **get_cluster_performance_parameters:** Used in dashboard queries to get cluster performance parameters.

## Lookups

* This App contains following lookup files.

### XtremIOClusterNameLookup

  * This lookup maintains mapping of XtremIO server node ip and Clsuter Name
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOClusterName.csv
  * **Lookup fields:** "Cluster Name","XtremIO_Server"

### XtremIOClustersLookup

  * This lookup maintains summary and inventory related data for each configured XtremIO Cluster
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOClusters.csv
  * **Lookup fields:** "Cluster Name",Index,"Compression Mode","System State","Target Group Count","Target Count","SSD Count","BBU Count","Volume Count","xEnv Count","Controller Count","xBricks Count","Infiniband Switch Count","Dedup Ratio","Physical Space In Use","Logical Space In Use","System Start Time","License Id","XIOS Version",Health,Bandwidth,Latency,IOPS,"Compression Factor","Overall Efficiency","Thin Provisioning Savings","Total Capacity"

### XtremIOVolumesLookup

  * This lookup maintains summary and inventory related data for each XtremIO Cluster Volume
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOVolumes.csv
  * **Lookup fields:** "Cluster Name","Volume Name",Compressible,"Logical Block Size","Small IO Alerts",Index,"Creation Timestamp","Logical Space Used","Volume Size","Total Snaps","Total Lun Mappings","VAAI TP Alerts",Bandwidth,Latency,IOPS

### XtremIOxBricksLookup

  * This lookup maintains summary and inventory related data for each XtremIO xBrick
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOxBricks.csv
  * **Lookup fields:** "Cluster Name","Brick Name",Index,"Node Count","SSD Count",GUID,State

### XtremIOInitiatorsLookup

  * This lookup maintains summary and inventory related data for each XtremIO Initiator
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOInitiators.csv
  * **Lookup fields:** "Cluster Name","Initiator Name",Index,Bandwidth,Latency,IOPS,"Group Name","Port Address","Port Type","Connection State","Connected Targets"

### XtremIOTargetsLookup

  * This lookup maintains summary and inventory related data for each XtremIO Target
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOTargets.csv
  * **Lookup fields:** "Cluster Name","Target Name",Index,"Jumbo Frame Enabled","Driver Version","Brick Name","Storage Controller",Bandwidth,Latency,IOPS,"Port Address","Port Type","Port State"

### XtremIOSnapshotsLookup

  * This lookup maintains summary and inventory related data for each XtremIO Snapshot
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOSnapshots.csv
  * **Lookup fields:** "Cluster Name","XtremIO_Server"

### XtremIOStorageControllersLookup

  * This lookup maintains summary and inventory related data for each XtremIO storage controller
  * **File location:** $SPLUNK_HOME$/etc/apps/EMC-app-XtremIO/lookups/XtremIOStorageControllers.csv
  * **Lookup fields:** "Cluster Name","Brick Name","Controller Name",Index,"Local Disk Count","PSU Count","SSD Count",Health,"Firmware Version","OS Version","IB1 Address","IB2 Address","IB1 Port State","IB2 Port State","IB1 Port Type","IB2 Port Type","IB1 link health","IB2 link health"


## Savedsearches

* This App contains following saved searches to populate specific lookups (Name of the saved searches match with lookup filename)

    * XtremIOClusterNameLookup
    * XtremIOClustersLookup
    * XtremIOVolumesLookup
    * XtremIOxBricksLookup
    * XtremIOInitiatorsLookup
    * XtremIOTargetsLookup
    * XtremIOSnapshotsLookup
    * XtremIOStorageControllersLookup


# Open source components and licenses

Some of the components included in "EMC XtremIO Add-on for Splunk Enterprise" are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* jQuery version 3.5.0 https://jquery.com (LICENSE https://github.com/jquery/jquery/blob/main/LICENSE.txt)
* Underscore JS version 1.6.0 http://underscorejs.org (LICENSE https://github.com/jashkenas/underscore/blob/master/LICENSE)

## Troubleshooting

* If dashboards are not getting populated:

    * Check "get_xtremio_index" macro is updated if you are using the custom index.
    * Make sure you have data in the given time range.
    * To check data is collected or not, run the below query in the search.
        
        * `get_xtremio_index` | stats count by sourcetype 

    * In particular, you should see these source types:

        * emc:xtremio:rest

    * Try expanding Time Range.

## Support Information

* **Email:** dell-support@crestdatasys.com

## Copyright Information

Copyright (C) 2021 Dell Technologies Inc. All Rights Reserved.