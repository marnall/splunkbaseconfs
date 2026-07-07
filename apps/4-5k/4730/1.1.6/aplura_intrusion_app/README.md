# PAVO Intrusion App for Splunk Documentation

Dashboards and reports on intrusion Detection and Prevention events in Splunk.

## About PAVO Intrusion App for Splunk

|                            |                                 |
|----------------------------|---------------------------------|
| Author                     | Aplura, LLC                     |
| App Version                | 1.1.6                           |
| App Build                  | 23                              |
| Creates an index           | False                           |
| Implements summarization   | No                              |
| Summary Indexing           | False                           |
| Data Model Acceleration    | If Enabled                      |
| Report Acceleration        | False                           |
| Splunk Enterprise versions | 10.X, 9.X                       |
| Platforms                  | Splunk Enterprise, Splunk Cloud |

## Scripts and binaries

This App provides the following scripts:

- `app_properties.py`

  - For use with the `python` integrations, if applicable.

- `Diag.py`

  - IF included, is used to help generate the diag files for support.

- `version.py`

  - For use with keeping track of the version number within Python scripts.

## Overview

Many organizations is IDS/IPS devices and software as their first line of defense against attackers. This app provides Splunk dashboards, forms, and reports which can be used to explore your IDS events across your different sourcetypes.

To do this, the app relies on the Splunk Common Information Model (CIM) for IDS attack events. This means that the app can report on any intrusion data, as long as it has been on-boarded properly, and is available through thehttp://docs.splunk.com/Documentation/CIM/latest/User/IntrusionDetection\[Intrusion Detection data model\], including network, host, wireless, and application products.

## A note on Splunk Data Model Acceleration and Disk Space

This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on [data model acceleration, how it uses disk space, and how to plan for it](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

## A note on the Splunk Common Information Model

As mentioned above, the app uses the CIM for intrusion events. The CIM allows you to take events from a number of sources or products, and report on them in one cohesive manner, using a common set of names for fields and event types.

## Available Dashboards

### Intrusion Overview

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

### Sourcetypes

Information about the sourcetypes which are present in the accelerated data.

### About

A simple HTML version of this document.

## Lookups

PAVO Intrusion App for Splunk contains the following lookup files.

- None

## Event Generator

PAVO Intrusion App for Splunk does not include an event generator.

## Acceleration

- Summary Indexing: No

- Data Model Acceleration: If Enabled

- Report Acceleration: No

# Installation, Prerequisites, and Configuration

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

Please review the information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model). The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/). This app has been tested with versions 4.9 of the CIM add-on.

The data model must be accelerated for the length of time for which you would like to see reporting.

The `Breakdown of Sourcetypes in Indexes in Dataset` panel on the `Data Transparency Overview` dashboard will only be seen if the `Sankey Diagram visualization` is installed. The Sankey Diagram Visualization can be downloaded from [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/).

# References

- [Splunk Common Information Model Add-on Docs](https://docs.splunk.com/Documentation/CIM/latest/User/Overview)

- 

- [Splunk Common Information Model Add-on](https://apps.splunk.com/app/1621/)

- [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/)

# Installation and Configuration

More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

# Download

# Installation Process Overview

- Make sure the field extractions and tags on your intrusion events are correct.

- Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).

- Install the PAVO Intrusion App for Splunk for Splunk.

- 

- Wait for the accelerations to start. After the acceleration searches have run, you should start seeing the dashboards populate.

# Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

- Deploy as you would any App, and restart Splunk.

- Configure.

# Deploy to Splunk Cloud

- Install via the Apps Browser in Splunk Cloud

- If there are issues, or you need help, have your Splunk Cloud Support handle this installation.

# Deploy to a Distributed Environment

- For each Search Head in the environment, deploy a copy of the App.

# Troubleshooting and Support

## Questions and answers

Access questions and answers specific to PAVO Intrusion App for Splunk at <https://answers.splunk.com/app/questions/4730.html>. Be sure to tag your question with the App.

## Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

## Known Issues

Version 1.1.6 of PAVO Intrusion App for Splunk has the following known issues:

- None

# Release notes

## Version 1.1.6

- Reviewed and Certified for Splunk 10

## Version 1.1.3

- Bug

  - \[AIAFS-15\] - Change Titles and Correct Capitalization of Intrusion Sourcetypes dashboard

- Improvement

  - \[AIAFS-16\] - Add data transparency dashboard

## Version 1.1.2

- Task

  - \[AIAFS-5\] - Rename app

## Version 1.1.0

- Initial Release

# Third Party Notices

Version 1.1.6 of PAVO Intrusion App for Splunk incorporates the following Third-party software or third-party services.

- None
