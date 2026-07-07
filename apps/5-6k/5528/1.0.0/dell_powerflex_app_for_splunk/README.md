# Dell EMC PowerFlex App for Splunk #

## Overview

Splunk App uses the data that are collected by one or more Add-ons and uses those data to visualize data in Splunk dashboards. The Dell EMC PowerFlex App for Splunk provides rich dashboards to visualize the PowerFlex systems. It also provides dashboard to visualize historical performance of the PowerFlex systems.

* Author - Crest Data Systems
* Version - 1.0.0
* Build - 1
* Dependant on: Dell EMC PowerFlex Add-on for Splunk
* Creates Index - False
* Uses Sourcetype: 1) powerflex:instance:<powerlfex_instance_name> 2) powerflex:statistics:<powerlfex_instance_name> 3) powerflex:alerts
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

The App does not require any specific configuration to make but in case of customized configuration of the Dell EMC PowerFlex Add-on for Splunk, the configuration of App has to be changed.


### Update Index Macro Configuration

By default, the index name is main in Splunk Enterprise. You can modify the default index name, by updating Powerflex_data macro.
1. Log in as administrator and select Settings > Advance search > Search Macros. 
2. By default, Dell EMC PowerFlex App for Splunk (dell_powerflex_app_for_Splunk) is selected in App drop-down. A list of available macros is displayed. 
3. Select and edit powerflex_data macro and change the definition of macros with new index name. 


### Update Time Range and Execution Period of Savedsearches

If you have changed the data collection interval for any instance type of input in the Add-on configuration page, then you have to change the cron schedule and earliest/latest time of the savedsearches. For example, if you have changed volume instance data collection interval from default 2 minutes to 20 minutes then you have to change the savedsearch execution to cron schedule to run after every 20 minutes and search data for last 40 minutes. If you have configured multiple systems, consider the minimal interval to configure the time range of savedsearches. 
Use the following steps to configure the time range of a savedsearch.
1. On Splunk web go to `Settings > Searches, reports, and Alerts`.
2. Select `Dell EMC PowerFlex App for Splunk` in `App`.
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
2. Select `Dell EMC PowerFlex App for Splunk` in `App`. Change `Visible in the App` to `Created in the App`.
3. Search for macro name `powerflex_critical_alerts` and click on it to edit.
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
* lookupfill_rpl_stats
* lookupfill_systems_in_rpl
* lookupfill_rcg_overview
* lookupfill_volume_details
* autorun_lookupfill_system
* autorun_lookupfill_faultset
* autorun_lookupfill_pd
* autorun_lookupfill_sp
* autorun_lookupfill_volume
* autorun_lookupfill_sds
* autorun_lookupfill_sdc
* autorun_lookupfill_device
* autorun_lookupfill_rpl_stats
* autorun_lookupfill_systems_in_rpl
* autorun_lookupfill_rcg_overview
* autorun_lookupfill_volume_details


## List of Lookups

* powerflex_lookup_system
* powerflex_lookup_faultset
* powerflex_lookup_pd
* powerflex_lookup_sp
* powerflex_lookup_volume
* powerflex_lookup_sds
* powerflex_lookup_sdc
* powerflex_lookup_device
* powerflex_lookup_rpl_stats
* powerflex_lookup_systems_in_rpl
* powerflex_lookup_rcg_overview
* powerflex_lookup_volume_details

## Troubleshooting
See, Troubleshooting section in Dell EMC PowerFlex Add-on and App for Splunk User Guide. For complete information, see Dell EMC PowerFlex Add-on and App for Splunk User Guide in https://infohub.delltechnologies.com/t/powerflex/ .

## Uninstall App
To uninstall an app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps ($SPLUNK_HOME/etc/apps) -> Remove the dell_powerflex_app_for_splunk folder from apps directory -> Restart Splunk

## Support

* Support Offered: Yes
* Support Email: dell-support@crestdatasys.com


### Copyright (C) 2020 Dell Technologies Inc. All Rights Reserved.

## Open Source Components And Licenses
Some of the components included in Dell EMC PowerFlex App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

| Component name | Version | Source | License |
|----------------|---------|--------|---------|
| Font Awesome   | 5.12.0  | https://fontawesome.com/icons | https://fontawesome.com/license/free |
| Network Diagram Viz | 1.8.0   | https://splunkbase.splunk.com/app/4438/ | https://opensource.org/licenses/MIT |


## Release Notes
Added following dashboards under Replication:
* Overview
* Peer MDM
* SDR
* Replication Consistency Group
* Replication Pair
* Historical Performance > Replication Performance
* Alerts > Replication Alerts

Added following lookups:
* powerflex_lookup_rpl_stats
* powerflex_lookup_systems_in_rpl
* powerflex_lookup_rcg_overview
* powerflex_lookup_volume_details

Added following savedsearches:
* lookupfill_rpl_stats
* lookupfill_systems_in_rpl
* lookupfill_rcg_overview
* lookupfill_volume_details
* autorun_lookupfill_rpl_stats
* autorun_lookupfill_systems_in_rpl
* autorun_lookupfill_rcg_overview
* autorun_lookupfill_volume_details