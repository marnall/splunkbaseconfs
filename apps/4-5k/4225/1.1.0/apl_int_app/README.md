# Aplura Intrusion App for Splunk Documentation

# Overview

## About Aplura Intrusion App for Splunk

|                          |                                                |
| ------------------------ | ---------------------------------------------- |
| Author                   | Aplura, LLC.                                   |
| App Version              | 1.1.0                                          |
| App Build                | 18                                             |
| Creates an index         | false                                          |
| Implements summarization | Currently, the app does not generate summaries |

Dashboards and reports on intrusion Detection and Prevention events in Splunk.

## Scripts and binaries

This App provides the following scripts:

|         |                                  |
| ------- | -------------------------------- |
| Diag.py | For use with the `diag` command. |

# Release notes

## Version 1.1.0

  - Initial Release

## About this release

Version 1.1.0 of Aplura Intrusion App for Splunk is compatible with:

|                            |                   |
| -------------------------- | ----------------- |
| Splunk Enterprise versions | 7.0, 7.1          |
| Platforms                  | Splunk Enterprise |

## Overview

Many organizations is IDS/IPS devices and software as their first line of defense against attackers. This app provides Splunk dashboards, forms, and reports which can be used to explore your IDS events across your different sourcetypes.

To do this, the app relies on the Splunk Common Information Model (CIM) for IDS attack events. This means that the app can report on any intrusion data, as long as it has been on-boarded properly, and is available through the [Intrusion Detection data model](http://docs.splunk.com/Documentation/CIM/latest/User/IntrusionDetection), including network, host, wireless, and application products.

## A note on Splunk Data Model Acceleration and Disk Space

This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on [data model acceleration, how it uses disk space, and how to plan for it](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

## A note on the Splunk Common Information Model

As mentioned above, the app uses the CIM for intrusion events. The CIM allows you to take events from a number of sources or products, and report on them in one cohesive manner, using a common set of names for fields and event types.

## Available Dashboards

### Overview

Provides a starting point for exploring your IDS events. Most panels will drill-down to other pages in the application.

### Attack Source Profile

A view based on the source of IDS events.

### Attack Destination Profile

IDS events where attacks are launched against the same destination.

### Attack Signature Profile

Panels which focus on events which all are from the same identified with the same signature.

### Attack Category Profile

A view focusing on attacks which fall into the same category (as defined in the events).

### Attack Search

A form for finding events based on various field values.

### Sourcetypes (Advanced)

Information about the sourcetypes which are present in the accelerated data.

## Prerequisites

### Splunk Versions

This app has been tested with Splunk versions 7.0 and 7.1. This app should be installed on the same search head on which the `|data_model|` data model has been accelerated.

### Splunk Common Information Model Add-on

This app depends on data models included in the Splunk Common Information Model Add-on, specifically the `|data_model|` data model. Please review the information on [installing and using the Splunk Common Information Model Add-on](http://docs.splunk.com/Documentation/CIM/latest/User/Install) and information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model).

The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/).

This app has been tested with versions 4.9 of the CIM add-on.

### Data model Acceleration on the Intrusion data model

In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the `|data_model|` data model must be accelerated. Information on how to enable acceleration for the `|data_model|` data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

## Installation

This app should be installed on a search head where the `|data_model|` data model has been accelerated. More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

### Simple Installation Process

  - Make sure the field extractions and tags on your intrusion events are correct.
  - Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).
  - Install the Aplura Intrusion App for Splunk for Splunk.
  - Enable accelerations on the `|data_model|` data model (skip if you are installing on an ES search head).
  - Wait for the accelerations to start. After the acceleration searches have run, you should start seeing the dashboards populate.

### References

#### Splunk Common Information Model

  - [Splunk Common Information Model Add-on Docs](http://docs.splunk.com/Documentation/CIM/latest/User/Overview)
  - [Splunk Common Information Model add-on |data_model| data model](http://http//docs.splunk.com/documentation/cim/latest/user/%7Cdata_model%7C)

### Downloads

  - [Splunk Common Information Model Add-on](https://apps.splunk.com/app/1621/)

## Known Issues

Version 1.1.0 of Aplura Intrusion App for Splunk has the following known issues:

  - None

# Support and resources

## Questions and answers

Access questions and answers specific to Aplura Intrusion App for Splunk at [https://answers.splunk.com](https://answers.splunk.com) . Be sure to tag your question with the App.

## Support

  - Support Email: None
  - Support Offered: Splunk Answers

# Installation and Configuration

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## Download

Download Aplura Intrusion App for Splunk at [https://splunkbase.splunk.com](https://splunkbase.splunk.com).

## Installation steps

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any App, and restart Splunk.
2.  Configure.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation.

### Deploy to a Distributed Environment

1.  For each Search Head in the environment, deploy a copy of the App.

# User Guide

## Configure Aplura Intrusion App for Splunk

  - Install the App according to your environment (see steps above)

## Lookups

Aplura Intrusion App for Splunk contains the following lookup files.

  - None

## Event Generator

Aplura Intrusion App for Splunk does not include an event generator.

## Acceleration

1.  Summary Indexing: No
2.  Data Model Acceleration: If Enabled
3.  Report Acceleration: No

# Third Party Notices

Version 1.1.0 of Aplura Intrusion App for Splunk incorporates the following Third-party software or third-party services.

  - None

### Related Topics

  - [Documentation overview](index.html#document-index)

2018, Aplura, LLC. | Powered by [Sphinx 1.6.4](http://sphinx-doc.org/) & [Alabaster 0.7.10](https://github.com/bitprophet/alabaster)
