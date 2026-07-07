# PAVO DNS App for Splunk Documentation

Dashboards and reports on DNS events in Splunk.

## About PAVO DNS App for Splunk

|                            |                                 |
|----------------------------|---------------------------------|
| Author                     | Aplura, LLC                     |
| App Version                | 1.0.6                           |
| App Build                  | 21                              |
| Creates an index           | False                           |
| Implements summarization   | No                              |
| Summary Indexing           | False                           |
| Data Model Acceleration    | If Enabled                      |
| Data Model                 | Network_Resolution              |
| Report Acceleration        | False                           |
| Splunk Enterprise versions | 10.X, 9.X, 8.X                  |
| Platforms                  | Splunk Enterprise, Splunk Cloud |

# Scripts and binaries

This App provides the following scripts:

|                                                                       |
|-----------------------------------------------------------------------|
| `Diag.py`                                                             |
| For use with the `diag` command.                                      |
| `app_properties.py`                                                   |
| Generated properties for the app for use in potential python scripts. |
| `version.py`                                                          |
| Generated version for use in potential python scripts.                |

# About PAVO DNS App for Splunk

## Overview

Most sourcetypes contain DNS events of some sort. This app provides Splunk dashboards, forms, and reports which can be used to explore your DNS events across your different sourcetypes.

To do this, the app relies on the Splunk Common Information Model (CIM) for network resolution (DNS) events. This means that the app can report on any network resolution(DNS) data, as long as it has been on-boarded properly, and is available through the [Network Resolution (DNS) data model](http://docs.splunk.com/Documentation/CIM/latest/User/NetworkResolutionDNS).

## A note on Splunk Data Model Acceleration and Disk Space

This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on [data model acceleration, how it uses disk space, and how to plan for it](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

## A note on the Splunk Common Information Model

As mentioned above, the app uses the CIM for network resolution (DNS) events. The CIM allows you to take events from a number of sources or products, and report on them in one cohesive manner, using a common set of names for fields and event types.

## Available Dashboards

### DNS Overview

Provides a starting point for exploring your DNS events. Most panels will drill-down to other pages in the application.

### Source Profile

DNS events which appear to come from a single source.

### Destination Profile

DNS events sent to a specific destination.

### Query Profile

DNS query information for specific queries.

### Sourcetypes (Advanced)

Information about the sourcetypes which are present in the accelerated data.

### Data Transparency Overview (Advanced)

This dashboard provides field information from the data models used to retrieve data for this application. Included information includes indexes and sourcetypes found in the data model. This dashboard also shows fields and constraints in the data models.

### About

A simple HTML version of this document.

## Macros

There are no macros that need to be customized to help this app fit into your environment.

## References and Downloads

- [Splunk Common Information Model Add-on Docs](http://docs.splunk.com/Documentation/CIM/latest/User/Overview)

- [SplunkCommon Information Model add-on Network Resolution data model](http://http//docs.splunk.com/documentation/cim/latest/user/NetworkResolutionDNS)

- [Splunk Common Information Model Add-on](https://apps.splunk.com/app/1621/)

- [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/)

## Configure PAVO DNS App for Splunk

- Install the App according to your environment.

- Datamodel acceleration is recommended, for performance.

## Lookups

PAVO DNS App for Splunk contains the following lookup files.

- None

## Event Generator

PAVO DNS App for Splunk does not include an event generator.

## Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: If Enabled

3.  Report Acceleration: No

# Installation and Configuration

## Prerequisites

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

This app depends on data models included in the Splunk Common Information Model Add-on, specifically the Network_Resolution data model. Please review the information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model).

The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/).

This app has been tested with versions 4.15 of the CIM add-on.

In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the Network_Resolution data model must be accelerated. Information on how to enable acceleration for the Network_Resolution data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

The `Breakdown of Sourcetypes in Indexes in Dataset` panel on the `Data Transparency Overview` dashboard will only be seen if the `Sankey Diagram` visualization is installed.

The Sankey Diagram Visualization can be downloaded from [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/).

## Installation and Configuration

Reminder: This app should be installed on a search head where the Network_Resolution(DNS) data model has been accelerated. More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

### Download

Download PAVO DNS App for Splunk at <https://splunkbase.splunk.com/app/5178>.

### Installation Process Overview

- Make sure the field extractions and tags on your DNS events are correct.

- Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).

- Install the PAVO DNS App for Splunk.

- Enable accelerations on the Network_Resolution(DNS) data model (skip if you are installing on an ES search head).

- Wait for the accelerations to start. After the acceleration searches have run, you should start seeing the dashboards populate.

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any App, and restart Splunk.

2.  If not already, install and accelerate the Network_Resolution datamodel.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation.

### Deploy to a Distributed Environment

1.  For each Search Head in the environment, deploy a copy of the App.

# Troubleshooting, support, and resources

## Questions and answers

Access questions and answers specific to PAVO DNS App for Splunk at <https://answers.splunk.com> . Be sure to tag your question with the App.

## Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

## Known Issues

Version 1.0.6 of PAVO DNS App for Splunk has the following known issues:

- None

## Release notes

### Version 1.0.6

- Reviewed and Certified for Splunk 10

### Version 1.0.0

- Initial Upload and Release

# Third Party Notices

Version 1.0.6 of PAVO DNS App for Splunk incorporates the following Third-party software or third-party services.

- None
