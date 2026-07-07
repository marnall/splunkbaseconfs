# TA-bricata

# Overview

## About bricata add-on for Splunk

|                          |                                                |
| ------------------------ | ---------------------------------------------- |
| Author                   | Bricata                                        |
| App Version              | 3.0.0                                          |
| App Build                | 1                                              |
| Creates an index         | false                                          |
| Implements summarization | Currently, the app does not generate summaries |

Field extractions, eventtypes and tags for Bricata Metadata and alerts in Splunk.

## Scripts and binaries

  - None

# Release notes

## Version 3.0.0

  - Upgrade

## About this release

Version 3.0.0 of bricata add-on for Splunk is compatible with:

|                            |                   |
| -------------------------- | ----------------- |
| Splunk Enterprise versions | 7.3.5, 8.x        |
| Platforms                  | Splunk Enterprise |
| CIM Versions               | 4.x               |

## Overview

The bricata add-on for Splunk provides inputs for the collection of data from the Bricata CMC or sensors through collection of JSON data sent to a syslog server or "syslog' data streamed from a sensor to tcp listeners.The add-on provides CIM compatible field extractions to normalize the data.

## Available Dashboards

  - None

### Sourcetypes (Advanced)

    #JSON Data Sourcetypes
    -bricata:{metadata_type}:raw


    #Syslog Sourcetypes
    -bricata:{metadata_type}:syslog


    #Alert Sourcetypes
    - bricata:cylance:raw bricata:suricata:raw bricata:alerts:raw

## Prerequisites

### Splunk Versions

This add-on has been tested with Splunk versions 8.0.2.1. 


### Simple Installation Process

  - Install the bricata add-on for Splunk.

## Known Issues

Version 3.0.0 of bricata add-on for Splunk has the following known issues:

  - None

# Support and resources

## Questions and answers

    -Here

## Support

  - Support Email: support@bricata.com
  - Support Offered: Splunk Answers

# Installation and Configuration

    - If upgrading from a previous bricata add-on, the old add-on should be removed completly.

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## Download

Download Bricata add-on for Splunk at [https://splunkbase.splunk.com](https://splunkbase.splunk.com).

## Installation steps

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any add-on, and restart Splunk.
2.  Configure.

### Deploy to single server instance

Follow these steps to install the add-on in a single server instance of Splunk Enterprise:

1.  Deploy as you would any add-on, and restart Splunk.

###  Distributed installation of this add-on
This table provides a quick reference for installing this add-on to a distributed deployment of Splunk Enterprise.
|                        |                                   |                                              |
| ---------------------- | --------------------------------- | -------------------------------------------- |
|Splunk instance type    |Supported        |Required         |Comments
|Search Heads            |Yes              |Yes              |Install this add-on to all search heads where Infoblox knowledge management is required.
|Indexers                |Yes              |Conditional      |Not required if you use heavy forwarders. Required if you use universal forwarders to monitor json or tcp bricata output.
|Heavy Forwarders        |Yes              |See comments     |This add-on supports forwarders of any type for data collection.
|Universal Forwarders    |Yes              |Conditional      | Only the inputs are required.

###   Distributed deployment compatibility
This table provides a quick reference for the compatibility of this add-on with Splunk distributed deployment features.

|                                   |               |                                                       |
| --------------------------------- | ------------- | ----------------------------------------------------- |
|Distributed deployment feature     |Supported      |Comments
|Search Head Clusters               |Yes            |You can install this add-on on a search head cluster for all search-time functionality. 
|Indexer Clusters                   |Yes            |Before installing this add-on to a cluster, remove the eventgen.conf files and all files in the Samples folder.
|Deployment Server                  |Yes            |Supported for deploying the configured add-on.

# User Guide

## Configure Bricata add-on for Splunk

  - Install the App according to your environment (see steps above)

## Lookups

Bricata add-on for Splunk contains the following lookups.

  - alert_severity.csv
  - bricata_conn_state.csv
  - dns_reply_codes.csv

## Event Generator

bricata add-on for Splunk does not include an event generator.

## Acceleration

1.  Summary Indexing: No
2.  Data Model Acceleration: No
3.  Report Acceleration: No

# Third Party Notices

Version 3.0.0 of bricata add-on for Splunk incorporates the following Third-party software or third-party services.

  - None

### Related Topics

  - [Documentation overview](index.html#document-index)

2020, Bricata
