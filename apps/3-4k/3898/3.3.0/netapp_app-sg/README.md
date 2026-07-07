# NetApp StorageGRID App for Splunk

## Overview

The NetApp StorageGRID App for Splunk is used to build dashboards and run ad-hoc searches on top of the data collected and indexed by the NetApp StorageGRID Add-on for Splunk. The NetApp StorageGRID Add-on for Splunk can be downloaded from [here](https://splunkbase.splunk.com/app/3895/)

## Compatibility Matrix

* Splunk version: 9.3.x, 9.2.x, and 9.1.x
* NetApp StorageGRID 11.x.
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome and Firefox

## Recommended System Configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.

## Topology and Setting up Splunk Environment

### Prerequisite

* This app has been distributed in two parts.

  1. Install NetApp StorageGRID Add-on for Splunk, which runs collector scripts and gathers data from StorageGRID, does indexing and parsing on collected data.
  2. Install NetApp StorageGRID App for Splunk, which receives indexed data from NetApp StorageGRID Add-on for Splunk, runs searches on it and builds dashboards.

* This App is supported on the Search head in case of distributed Splunk platform deployment and also on standalone Splunk instance. Below table provides the reference for installing the App on distributed Splunk deployment:

     | Splunk instance type  | Supported  | Required | Comments |
     | --------------------- | ---------- | -------- | -------- |
     | Search Heads          | Yes | Yes | This App is required on Search Heads as it has dashboards and searches.|
     | Indexers              | Yes | No | This App is not required on the indexers.|
     | Heavy Forwarders      | Yes | No | This App is not required on the heavy forwarders.| 

## Installation 

Follow the link mentioned below to install the App based on your deployment:

* [Single-instance Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Singleserverinstall)
* [Distributed Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Distributedinstall)
* [Splunk Cloud](https://docs.splunk.com/Documentation/AddOns/latest/Overview/SplunkCloudinstall)

## Upgrade the App

If there is already older version of app installed in your Splunk instance, then you can upgrade app by following two ways:

1. Using the latest version available on Splunkbase.
     * From the Splunk Web home screen, click the gear icon next to Apps. 
     * There will be option to update the App to the latest version in column name as - "Version".
     * Click on "Update to [version]"
     * Follow the installation steps to update the App.

2. You can download latest version of App from Splunkbase and you can upload it into Splunk by navigating to 
     * From the Splunk Web home screen, click the gear icon next to Apps. 
     * Click on, Install app from file -> Choose File 
     * Choose the location of App's build downloaded and make sure you have checked checkbox of "Upgrade app."
     * And then click on Upload
     * Restart the Splunk

## Configuration

Admin will have to update/replace name of the index in 'get_sg_index' macro if StorageGRID data is being indexed in any index other than main. There is no additional configuration required.  

### Update index in macro

* On Splunk web go to `Settings > Advanced search > Search macros`.
* Select `NetApp StorageGRID App for Splunk` in `App`. Change `Visible in the App` to `Created in the App`.
* Search for macro name `get_sg_index` and click on it to edit.
* Change definition of macro with the new index or indexes configured.
  * Ex. `(index=storagegrid)`
* Click on `Save`.


## Lookups

* sg_account_mapping - This is CSV file based lookup which consists details of tenant accounts having their names and ids.
* sg_hierarchy - This is CSV file based lookup which consists details about hierarchy of configured storageGrid.
* sg_storagenode_mapping - This is CSV file based lookup which consists details of all storage nodes.

## Saved Searches
This app contains the following saved searches, which are used for populating data in the dashboard:

* SG-accountMappingLookup - Used to populate - "sg_account_mapping" lookup and is triggered at an interval of 15 minutes.
* SG-hierarchyLookup - Used to populate - "sg_hierarchy" lookup and is triggered at an interval of 15 minutes.
* SG-storagenodeMappingLookup - Used to populate - "sg_storagenode_mapping" lookup and is triggered at an interval of 15 minutes.

## Release Notes


### V3.3.0

* Added StorageGRID System filter in dashboards

### V3.2.1

* Updated the Copyright information.

### V3.2.0

* Remove JQuery dependency from App.
* Added drilldown to new tab in App.
* Resolved console error.
* Added Drilldown in Average Query Latency Over Time panel in ILM Details Dashboard.

### V3.1.0

* Added table for Alerts data for NetApp StorageGRID v11.4 onwards.
* Drilldown from alarms/alarts will now display whole events instead of table
* Added support for Splunk v8.1.x

### V3.0.1

* Fix for "No. of Sites" and "No. of Nodes" panels' issue with large topology in the Summary dashboard.
* Compatibility with NetApp StorageGRID Add-on v3.0.2.

### V3.0.0

* Added two new dashboards named as - "Load Balancer" and "Platform Services Overview".
* Changed navigation menu for all of the dashboards.
* Removed 7 panels from "Security Audit" dashboard as the required audit logs are deprecated in newer version of the StorageGrid.
* Added 2 new panels in "Security Audit" dashboard to audit the use of management APIs by the grid managers & the tenant accounts.
* Replaced column "No. of Established Connections" with "Active Connections of Storage Nodes" in "Security Audit" dashboard.
* Added 2 new panels in "ILM details" dashboard to monitor the objects dropped.
* Removed 3 panels which were based on audit logs from "S3 details" and " Swift details" dashboards.
* Added panels - "Average duration to perform Operations on S3 Objects" and "Average duration to perform Operations on Swift Objects" in "S3 details" and "Swift details" dashboards respectively.
* Added multi-level drill-downs for the following panels in "S3 details" and "Swift details" dashboards.
     * Average Operation rate over time
     * Average Ingest/Retrieval rate over time

## OPEN SOURCE COMPONENTS AND LICENSES
* Some of the components included in "NetApp StorageGRID App for Splunk" are licensed under free or open source licenses. We wish to thank the contributors to those projects.
* jQuery version 3.6.0 http://jquery.com/ (LICENSE https://github.com/jquery/jquery/blob/master/LICENSE.txt)
* Underscore JS version 1.6.0 http://underscorejs.org (LICENSE https://github.com/jashkenas/underscore/blob/master/LICENSE)

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/netapp_app-sg
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## Troubleshooting

**Test Your Install**

The main app dashboard can take some time to populate the dashboards Once data collection is started by Add-on. A good test to see that you are receiving all of the expected data is to run below given search on Main app search dashboard after several minutes:

    search `get_sg_index` | stats count by sourcetype

In particular, you should see these sourcetypes:

 1. grid:rest:api
 2. grid:auditlog

If you don't see these sourcetypes

1. Verify the macro configurations in the App. Refer to "Configuration > Update index in macro" section for more details.
2. Please check troubleshooting guide for the NetApp StorageGRID Add-on for Splunk.

**If the dashboard filters are not being populated**

1. Make sure all the saved-searches in the App is enabled.
2. Try restarting Splunk search head. In standalone restart Splunk.

## Support

* Support Information: Community Supported

### Copyright (c) 2022 NetApp, Inc., All Rights Reserved
