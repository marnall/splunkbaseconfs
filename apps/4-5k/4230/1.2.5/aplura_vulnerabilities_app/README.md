# PAVO Vulnerabilities App for Splunk Documentation

App for exploring and reporting on Vulnerability events.

## About PAVO Vulnerabilities App for Splunk

|                            |                                 |
|----------------------------|---------------------------------|
| Author                     | Aplura, LLC                     |
| App Version                | 1.2.5                           |
| App Build                  | 15                              |
| Creates an index           | False                           |
| Implements summarization   | No                              |
| Summary Indexing           | False                           |
| Data Model Acceleration    | If Enabled                      |
| Data Model                 |                                 |
| Report Acceleration        | False                           |
| Splunk Enterprise versions | 10.X, 9.X                       |
| Platforms                  | Splunk Enterprise, Splunk Cloud |

# Scripts and binaries

This App provides the following scripts:

- `Diag.py`

  - For use with the `diag` command.

- `version.py`

  - For use with keeping track of the version number within Python scripts.

## Overview

This app provides Splunk dashboards, forms, and reports which can be used to explore your vulnerability events, and make sense of what can often be a large volume of data.

To do this, the app relies on the Splunk Common Information Model (CIM) for vulnerability events. This means that the app can report on any vulnerability data, as long as it has been on-boarded properly, and is available through the Vulnerabilities data model.

## A note on Splunk Data Model Acceleration and Disk Space

This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on [data model acceleration, how it uses disk space, and how to plan for it](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

## A note on the Splunk Common Information Model

As mentioned above, the app uses the CIM for vulnerability events. The CIM allows you to take events from a number of sources or products, and report on them in one cohesive manner, using a common set of names for fields and event types.

## Available Dashboards

### Vulnerabilities Overview

This dashboard serves as a jumping-off point for exploring your vulnerability data. It includes panels for vulnerabilities over time, severities, destinations, and signatures. Clicking on panels in this dashboard will drill down to the appropriate profile page for further exploration.

### Severity Profile

Form with reports and visualizations built around a set of severities (Critical, High, Medium, Low, Informational, Unknown, or all).

### Dest Profile

Form with reports and visualizations built around a destination (host or IP address, depending on how your CIM information for your vulnerability management events is mapped).

### Signature Profile

Form with reports and visualizations built around a signature, such as Terminal Services Encryption Level is Medium or Low or Buffer overrun in NT kernel message handling. Note that this is different than a CVE number, this is the text description of the vulnerability.

### Vulnerability Search

Form with many input variables. This is a flexible form designed to help generate a knockout list for fixing a set, or particular type of vulnerability.

### Identifier Search

Form for searching based on an identifier for a vulnerability, such as CVE, Cert, MSFT, or other reference number.

### Sourcetypes

This dashboard provides panels to compare and contrast activity by sourcetypes. Use the time-picker to display sourcetype activity over time and to visualize event counts by sourcetype.

### About

A simple HTML version of this document.

### Splunk Common Information Model Add-on

This app depends on data models included in the Splunk Common Information Model Add-on, specifically the `{data_model}` data model. Please review the information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model).

The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/).

This app has been tested with versions 4.9 of the CIM add-on.

### Data model Acceleration on the Vulnerability data model

In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the `{data_model}` data model must be accelerated. Information on how to enable acceleration for the `{data_model}` data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

## Acceleration Information

1.  Summary Indexing: No

2.  Data Model Acceleration: If Enabled

3.  Report Acceleration: No

## Lookups

PAVO Vulnerabilities App for Splunk contains the following lookup files.

- None

## Event Generator

PAVO Vulnerabilities App for Splunk does not include an event generator.

# Installation

## Prerequisites

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

This app depends on data models included in the Splunk Common Information Model Add-on, specifically the `{data_model}` data model. Please review the information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model).

The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/).

This app has been tested with versions 4.9 of the CIM add-on.

In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the `{data_model}` data model must be accelerated. Information on how to enable acceleration for the `{data_model}` data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

The `Breakdown of Sourcetypes in Indexes in Dataset` panel on the `Data Transparency Overview` dashboard will only be seen if the `Sankey Diagram visualization` is installed.

The Sankey Diagram Visualization can be downloaded from [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/).

This app uses the following macros which can be used for customization:

### vuln_show_severity

This macro can be used to make the app use a less strict approach to the CIM. The CIM defines what valid values for severity. If your data does not follow this, you can use this for adding other definitions.

# References

- [Splunk Common Information Model Add-on Docs](https://docs.splunk.com/Documentation/CIM/latest/User/Overview)

- Splunk Common Information Model add-on `{data_model}` data model <https://docs.splunk.com/documentation/CIM/latest/User/Vulnerabilities>

- [Splunk Common Information Model Add-on](https://apps.splunk.com/app/1621/)

- [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/)

# Installation and Configuration

Reminder: This app should be installed on a search head where the `{data_model}` data model has been accelerated. More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

## Download

### Installation Process Overview

- Make sure the field extractions and tags on your vulnerability events are correct.

- Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).

- Install the PAVO Vulnerabilities App for Splunk for Splunk.

- 

- Wait for the accelerations to start. After the acceleration searches have run, you should start seeing the dashboards populate.

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any App, and restart Splunk.

2.  Configure.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation.

### Deploy to a Distributed Environment

1.  For each Search Head in the environment, deploy a copy of the App.

This app should be installed on a search head where the `{data_model}` data model has been accelerated. More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

### Simple Installation Process

- Make sure the field extractions and tags on your vulnerability events are correct.

- Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).

- Install the PAVO Vulnerabilities App for Splunk for Splunk.

- 

- Wait for the accelerations to start. After the acceleration searches have run, you should start seeing the dashboards populate.

In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the `{data_model}` data model must be accelerated. Information on how to enable acceleration for the `{data_model}` data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

### Macros for Configuration

This app uses the following macros which can be used for customization:

#### vuln_show_severity

This macro can be used to make the app use a less strict approach to the CIM. The CIM defines what valid values for severity. If your data does not follow this, you can use this for adding other definitions.

# Support and resources

## Questions and answers

Access questions and answers specific to `{long_name}` at <https://answers.splunk.com/app/questions/4230.html>. Be sure to tag your question with the App.

## Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

## Known Issues

Version 1.2.5 of `{long_name}` has the following known issues:

- Setting the date and time range to real time in any of the views will result in a tstats error. As a work around, do not use the real time option.

# Release notes

## Version 1.2.5

- Reviewed and Certified for Splunk 10

## Version 1.2.2

- Bug

  - \[AVAFS-13\] - Change Titles and Correct Capitalization of Sourcetypes dashboard

- Improvement

  - \[AVAFS-14\] - Added data transparency dashboard

## Version 1.2.1

- Bug

  - \[AVAFS-4\] - No Collections defined for transforms

  - \[AVAFS-7\] - Docs issues

- Task

  - \[AVAFS-6\] - Rename app

## Version 1.2.0

- Initial Release

# Third Party Notices

Version 1.2.5 of

PAVO Vulnerabilities App for Splunk incorporates the following Third-party software or third-party services.

- None
