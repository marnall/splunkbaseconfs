# IMS Connect Extensions : Splunk app containing sample dashboards for the IMS Connect transaction analysis

This repository contains a [Splunk](http://www.splunk.com) app for IMS Connect transaction analysis.

The app contains sample dashboards that presents visualization of the IMS Connect transaction analysis.

## Requirements

* Install Splunk 7.2, or later
* The IMS Connect transaction analysis app requires the Splunk Built ["Sankey Diagram - Custom Visualization"](https://splunkbase.splunk.com/app/3112/) app
* To receive IMS Connect transaction performance data into Splunk, install and run the [IMS Connect Extensions feed](https://www.ibm.com/support/knowledgecenter/en/SSAVHV_3.1.0/cexu-ca20.html)
* If you want to use ODBM data field and z/OS Connect token field, please apply the PTFs, UI93456 and UIxxxxx, respectively.

## Installation

This folder *is* the Splunk `IMS Connect transaction analysis` app.

To install the app, clone this Git repository to a new `cexca20` subdirectory under `Splunk/etc/apps` in your Splunk installation.

After cloning, check that the directory structure contains the following path:

`Splunk/etc/apps/cexca20/local`

There should be no intervening directory between `cexca20` and `local`.

For complete installation instructions, see [forwarding-a-live-feed-of-ims-connect-events-to-splunk](https://community.ibm.com/community/user/ibmz-and-linuxone/viewdocument/forwarding-a-live-feed-of-ims-conne?CommunityKey=eba3ada3-db89-4dca-9154-328195f5e560&tab=librarydocuments/)

## Splunk configuration files
* `inputs.conf`

  Defines a TCP data input, including the port number on which Splunk listens for incoming data. Sets the default index to `cex` and sourcetype to `ims-ca20`.

* `props.conf`

  Defines the incoming data as JSON Lines; configures timestamp recognition.

## Setting which indexes the app searches

By default, the app (more specifically, *each of the search commands in the app*) searches for data in an index named `ims-ca20`.

It's easy to change which index, or indexes, the app searches.
Rather than specifying index names directly in search commands, which would mean you would have to search and replace many index names in definitions across multiple files, the app uses macros.

The macros are defined in the file `local/macros.conf`.

## Dashboards

### Overview

Shows the top 10 values by transaction count of the selected IMS Connect transaction identifier.
How to use:
* Select time period
* Select an IMS Connect transaction identifier to group transactions

### Workload distribution

Shows the distribution of transactions from a selected IMS Connect transaction identifier to IMS Connect systems, Target IMS data store and Tmember.
How to use:
* Select time period
* Select an IMS Connect transaction identifier to group transactions
* Select transactions groups to show it's distribution

### Workload mapping

Shows the relationship between IMS Connect transaction identifiers.
How to use:
* Select time period
* Select two IMS Connect transaction identifiers

### Performance comparison

Compare IMS Connect transaction performance grouped by your choice of identifier.
How to use:
* Select time period
* Select an IMS Connect transaction identifier to group transactions
* Select all or specific groups for comparison

### Elapsed time components
View transaction transit data of events grouped by a chosen criteria.
How to use:
* Select time period
* Select an IMS Connect transaction identifier to group transactions
* Select a specific group

## Javascript files

* `control.js`
Updates the time of all graphs in the dashboard to the selected time range.

## CSS files

* `right_align.css`
Set text-align property of a target table cell to "right".
