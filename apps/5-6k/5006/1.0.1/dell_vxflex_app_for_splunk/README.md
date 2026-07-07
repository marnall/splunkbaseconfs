# Dell EMC VxFlex integrated rack App for Splunk #

## Overview

Splunk App uses the data that are collected by one or more Add-ons and uses those data to visualize data in Splunk dashboards. The Dell EMC VxFlex integrated rack App for Splunk provides rich dashboards to visualize the VxFlex systems. It also provides dashboard to visualize historical performance of the VxFlex systems.

* Author - Crest Data Systems
* Version - 1.0.1
* Build - 75
* Dependant on: Dell EMC VxFlex integrated rack Add-on for Splunk
* Creates Index - False
* Uses Sourcetype: 1) vxflex:instance:<vxlfex_instance_name> 2) vxflex:statistics:<vxlfex_instance_name> 3) vxflex:alerts
* Uses KV Store - True. This App uses Splunk KV Store for storing some of the lookup files
* App has some savedsearches to fill lookups
* Compatible with:
    * Splunk Enterprise version: 7.2, 7.3 and 8.0
    * OS: CentOS, Windows
    * Browser: Google Chrome, Mozilla Firefox

## Recommended System Configuration

Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

## Installation

This App is supported on both Distributed and Standalone Splunk deployment. The following table provides the reference for installing the App on Distributed Splunk deployment:


| Splunk instance type  | Supported  | Required | Comments |
| --------------------- | ---------- | --------- | -------- |
| Search Heads          | Yes | Yes | This App is required on Search Heads as it has dashboards and searches.|
| Indexers              | Yes | No | This App is not required on the indexers.|
| Heavy Forwarders      | Yes | No | This App is not required on the heavy forwarders.| 

To install the App based on your deployment, refer the following links:

* [Single-instance Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Singleserverinstall)
* [Distributed Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Distributedinstall)
* [Splunk Cloud](https://docs.splunk.com/Documentation/AddOns/latest/Overview/SplunkCloudinstall)


## Configuration

The App does not require any specific configuration to make but in case of customized configuration of the Dell EMC VxFlex integrated rack Add-on for Splunk, the configuration of App has to be changed.


### Update Index Macro Configuration

By default, the index name is main in Splunk Enterprise. You can modify the default index name, by updating vxflex_data macro.
1. Log in as administrator and select Settings > Advance search > Search Macros. 
2. By default, Dell EMC VxFlex integrated rack App for Splunk (dell_vxflex_app_for_Splunk) is selected in App drop-down. A list of available macros is displayed. 
3. Select and edit vxflex_data macro and change the definition of macros with new index name. 


### Update Time Range and Execution Period of Savedsearches

If you have changed the data collection interval for any instance type of input in the Add-on configuration page, then you have to change the cron schedule and earliest/latest time of the savedsearches. For example, if you have changed volume instance data collection interval from default 2 minutes to 20 minutes then you have to change the savedsearch execution to cron schedule to run after every 20 minutes and search data for last 40 minutes. If you have configured multiple systems, consider the minimal interval to configure the time range of savedsearches. 
Use the following steps to configure the time range of a savedsearch.
1. On Splunk web go to `Settings > Searches, reports, and Alerts`.
2. Select `Dell EMC VxFlex integrated rack App for Splunk` in `App`.
3. Search for `lookupfill_volume` and click on it to edit.
4. To edit time range, edit `Earliest time` to `-40m@m` for this example.
5. Click on `Save`.
6. Click on `Edit > Edit Schedule`.
7. Change `Cron Expression` to `*/20 * * * *`. To learn more about cron schedule visit https://crontab.guru/.
8. Click on `Save`.

Follow the same steps for other searches.


### Update Critical Alert Definition in the Macro

All alerts with critical severity which affects the MDM cluster are set as the default definition of critical events. If you want to change the critical alert definition, follow the below mentioned steps.
1. On Splunk web go to `Settings > Advanced search > Search macros`.
2. Select `Dell EMC VxFlex integrated rack App for Splunk` in `App`. Change `Visible in the App` to `Created in the App`.
3. Search for macro name `vxflex_critical_alerts` and click on it to edit.
4. Change definition of macro with the list of critical alerts.
  * Ex. `("MDM_NOT_CLUSTERED", "MDM_FAILS_OVER_FREQUENTLY")`
5. Click on `Save`.


## List of Savedsearches

* lookupfill_system
* lookupfill_faultset
* lookupfill_pd
* lookupfill_sp
* lookupfill_volume
* lookupfill_sds
* lookupfill_sdc
* lookupfill_device
* autorun_lookupfill_system
* autorun_lookupfill_faultset
* autorun_lookupfill_pd
* autorun_lookupfill_sp
* autorun_lookupfill_volume
* autorun_lookupfill_sds
* autorun_lookupfill_sdc
* autorun_lookupfill_device


## List of Lookups

* vxflex_lookup_system
* vxflex_lookup_faultset
* vxflex_lookup_pd
* vxflex_lookup_sp
* vxflex_lookup_volume
* vxflex_lookup_sds
* vxflex_lookup_sdc
* vxflex_lookup_device


## Release Notes

### V1.0.1

* Removed deprecated parameter refresh.auto.interval from the Overview dashboard.


### V1.0.0

* Created following dashboards. 1) Overview 2) Protection Domain 3) Storage Pool 4) Volumes 5) SDS 6) SDC 7) Devices 8) Alerts 9) Historical Performance dashboards
* Created lookups and savedsearches to fill these lookups from data
* Added troubleshooting dashboard.


## Troubleshooting
See, Troubleshooting section in Dell EMC VxFlex integrated rack Add-on and App for Splunk User Guide. For complete information, see Dell EMC VxFlex integrated rack Add-on and App for Splunk User Guide in https://infohub.delltechnologies.com/t/vxflex/ .

## Support

* Support Offered: Yes
* Support Email: dell-support@crestdatasys.com


### Copyright (C) 2020 Dell Technologies Inc. All Rights Reserved.

## Open Source Components And Licenses
Some of the components included in Dell EMC VxFlex integrated rack App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

| Component name | Version | Source | License |
|----------------|---------|--------|---------|
| Font Awesome   | 5.12.0  | https://fontawesome.com/icons | https://fontawesome.com/license/free |
