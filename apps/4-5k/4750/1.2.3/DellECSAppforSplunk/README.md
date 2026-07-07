# Dell ECS App for Splunk

Dell ECS App for Splunk allows you to leverage the ECS platform data within your Splunk Enterprise instance.
* Author - Dell Inc.
* Version - 1.2.3

## Release Notes

* Version 1.2.3
    * Bumped the version to unarchive the app on Splunkbase.

* Version 1.2.2
    * Minor bug fix.

* Version 1.2.1
    * BugFix for Transaction > Transaction Requests Dashboard

* Version 1.2.0
    * Bundled JQuery3.5.0 within app package
    * Updated codebase to adhere to appinspect best practices and to support latest Splunk version
    * Added flux API support for DELL v3.6.

* Version 1.1.0
    * Fixed minor dashboard bugs.
    * Splunk 8 Support

## Topology and Setting up Splunk Environment
This App can be set up in two ways:

1) Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup
2) Distributed Environment: Install app on search head.

   * App resides on search head machine to visualize the data coming from forwarders.

## Requirements

Splunk Enterprise:

* Version 8.1.x, 8.2.x and 9.0.x

Dell ECS Add-on for Splunk with input configuration

* Version 1.2.0

Tested on CentOS, Windows with the latest chrome and firefox browser version.

## Recommended System Configuration

* Standard Splunk Enterprise configuration of Search Head, Indexer, and Forwarder.

## Installation

This App can be installed through UI using the following steps.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click the `install app from file`.
3. Click `Choose File` and select the Dell ECS App installation file.
4. Click on `Upload`.
5. Restart Splunk.

## Application Setup

After Installation  

1. Configure Base value

* Navigate to Apps > Manage Apps.
* Filter `Dell ECS App for Splunk` and click on `Set up` under the Actions.
* Setup the base value and click `save`. For example, If the base value is 2 then 1024 Bytes will be converted to 1 KiB and if the base value is 10 then 1000 Bytes will be converted to 1 KB.

2. Configure Macro

* Navigate to Settings > Advanced search > Search macros.
* Filter `Dell_ECS_index` and click `Dell_ECS_index` under the Name.
* Edit the definition macro definition `(index=<index>)` and click`Save`.


## Search

To see data logged by `Dell ECS Add-on for Splunk`, select the `Search` tab. Search  ``Dell_ECS_index`` macro.

## Troubleshooting

* If dashboards are not getting populated then navigate to settings > Searches, Reports, and Alerts and run `dell_vdc_list` saved search.
* If app logo is not loading after app upgrade, please restart your Splunk instance to resolve it.
* If you are collecting Flux data:
    * For below dashboards, we are collecting data from Flux in a chunk of 5 minutes.
        * Overview
        * Disk Bandwidth
        * Performance
    * For below dashboards, we are collecting data from Flux in a chunk of 2 minutes.
        * Overview
        * Transaction Requests
    * Hence you might observe a delay of up to 5 or 2 minutes respectively in the data. If you observe more delay, reduce the interval time of your input.
    * For Disk Bandwidth dashboard > Disk Bandwidth by Nodes (average for last day in selected period) panel you might observe a delay of up to 1 hour due to a limitation in the number of calls that can be made to the Flux.

## Uninstall & Cleanup steps

* Remove $SPLUNK_HOME/etc/apps/DellECSAppforSplunk
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## Support

* Support Offered: Yes
* Support Email: dell-support@crestdata.ai

## Savedsearches

* `dell_vdc_list` saved search is used to populate dell_vdc_list_lookup lookup.

## Copyright

* Copyright (C) 2025 Dell Technologies Inc. All Rights Reserved.