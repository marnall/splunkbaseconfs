# PAVO Authentication App for Splunk Documentation

Dashboards and reports on Authentication events in Splunk.

## About PAVO Authentication App for Splunk

|                            |                                 |
|----------------------------|---------------------------------|
| Author                     | Aplura, LLC                     |
| App Version                | 1.3.5                           |
| App Build                  | 188                             |
| Creates an index           | False                           |
| Implements summarization   | No                              |
| Summary Indexing           | False                           |
| Data Model Acceleration    | If Enabled                      |
| Data Model                 | Authentication                  |
| Report Acceleration        | False                           |
| Splunk Enterprise versions | 10.0, 9.X, 8.X                  |
| Platforms                  | Splunk Enterprise, Splunk Cloud |

# Scripts and binaries

This App provides the following scripts:

- `Diag.py`

  - For use with the `diag` command.

- `version.py`

  - For use with keeping track of the version number within Python scripts.

- `app_properties.py`

  - Provides app properties for python files.

# Overview

Most sourcetypes contain authentication events of some sort. This app provides Splunk dashboards, forms, and reports which can be used to explore your authentication events across your different sourcetypes.

To do this, the app relies on the Splunk Common Information Model (CIM) for authentication events. This means that the app can report on any authentication data, as long as it has been on-boarded properly, and is available through the [Authentication data model](http://docs.splunk.com/Documentation/CIM/latest/User/Authentication).

# A note on Splunk Data Model Acceleration and Disk Space

This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on [data model acceleration, how it uses disk space, and how to plan for it](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

# A note on the Splunk Common Information Model

As mentioned above, the app uses the CIM for authentication events. The CIM allows you to take events from a number of sources or products, and report on them in one cohesive manner, using a common set of names for fields and event types.

# Available Dashboards

## Authentication Overview

Provides a starting point for exploring your authentication events. Most panels will drill-down to other pages in the application.

## User Profile

A view based on a single users authentication activity.

## Source Profile

Authentication events which appear to come from a single source.

## Destination Profile

Authentication events where users are authenticating against the same destination.

## App Profile

Panels which focus on events which all are from the same application (win:local, ssh, vpn, etc).

## Action Profile

A view based in the action (`success`, `failure`, `unknown`) from the authentication event.

## Default Authentication

Reports on default authentication occurring in the environment. See the Customization section of this document for more information about how this dashboard can be customized for your deployment.

## Privileged Authentication

Reports on privileged authentication occurring in the environment. See the Customization section of this document for more information about how this dashboard can be customized for your deployment.

## Authentication Search (Advanced)

A form for finding events based on various field values.

## Authentication Geography (Advanced)

Where in the World are authentications originating? View that here.

## Sourcetypes (Advanced)

Information about the sourcetypes which are present in the accelerated data.

## About

A simple HTML version of this document.

# User Guide

Configure PAVO Authentication App for Splunk

- Install the App according to your environment

## Lookups

PAVO Authentication App for Splunk contains the following lookup files.

- apl_aut_default_users.csv

- apl_aut_priv_users.csv

## Event Generator

PAVO Authentication App for Splunk does not include an event generator.

## Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: If Enabled

3.  Report Acceleration: No

# Installation and Configuration

## Prerequisites

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

This app depends on data models included in the Splunk Common Information Model Add-on, specifically the Authentication data model. Please review the information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model).

The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/).

This app has been tested with versions 4.8 of the CIM add-on.

In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the Authentication data model must be accelerated. Information on how to enable acceleration for the Authentication data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

The `Breakdown of Sourcetypes in Indexes in Dataset panel` on the `Data Transparency Overview` dashboard will only be seen if the `Sankey Diagram visualization` is installed.

The Sankey Diagram Visualization can be downloaded from [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/).

## Lookups

PAVO Authentication App for Splunk contains the following default lookup files.

- apl_aut_default_users.csv

- apl_aut_priv_users.csv

We strongly suggest that if you want to use customized versions of the lookups, you create new configurations for additional lookups, rather than editing the .csv files included in the app. Splunk lookup files are not upgrade safe, so future versions of the app may contain lookup files which may overwrite your customizations.

## Macros

There are two macros which may be customized to help this app fit into your environment, and make use of other lookups (possibly the ones from the Splunk App for Enterprise Security). In both of these cases, the result is that the search in the macro should output a user field which contains the users appropriate for your environment.

### apl_aut_default_users_lookup

Used for the `Default Authentication` dashboard. By default, uses the `apl_aut_default_users.csv` file. This list was put together from multiple sources, and may not contain all the default users which may be available in your environment.

### apl_aut_priv_users_lookup

Used for the `Privileged Authentication` dashboard. By default, uses the `apl_aut_priv_users.csv` file. This list was put together from multiple sources, and may not contain all the privileged users which may be available in your environment.

## References and Downloads

- [Splunk Common Information Model Add-on Docs](http://docs.splunk.com/Documentation/CIM/latest/User/Overview)

- [Splunk Common Information Model add-on Authentication data model](http://http//docs.splunk.com/documentation/cim/latest/user/Authentication)

- [Splunk Common Information Model Add-on](https://apps.splunk.com/app/1621/)

- [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/)

# Installation and Configuration

Reminder: This app should be installed on a search head where the Authentication data model has been accelerated. More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

## Download

Download PAVO Authentication App for Splunk at <https://splunkbase.splunk.com/app/4227>.

### Installation Process Overview

- Make sure the field extractions and tags on your authentication events are correct.

- Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).

- Install the Authentication App for Splunk.

- Enable accelerations on the Authentication data model (skip if you are installing on an ES search head).

- Wait for the accelerations to start. After the acceleration searches have run, you should start seeing the dashboards populate.

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any App, and restart Splunk.

2.  Configure.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation.

### Deploy to a Distributed Environment

1.  For each Search Head in the environment, deploy a copy of the App.

# Support and resources

## Questions and answers

Access questions and answers specific to PAVO Authentication App for Splunk at <https://answers.splunk.com/app/questions/4227.html>. Be sure to tag your question with the App.

## Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

## Known Issues

Version 1.3.5 of PAVO Authentication App for Splunk has the following known issues:

- None

# Release notes

## Version 1.3.5

- Reviewed and Certified Splunk 10 and Splunk Cloud compatibility.

## Version 1.3.3

- Improvement

  - Added Data Transparency Overview dashboard under advanced menu

  - Added PAVO Banner Service

## Version 1.3.2

- Bug

  - \[AAAFS-12\] - Searches Need to Have Quotes Around The app Field

  - \[AAAFS-13\] - Change Titles and Correct Capitalization of Sourcetypes dashboard

  - \[APL029-418\] - Authentication App Bugs

- Improvement

  - \[AAAFS-3\] - Suggestion - Add a Filter For Success/Failure on the Source Profile Dashboard

  - \[AAAFS-14\] - Added Data Transparency Overview dashboard under advanced menu

## Version 1.3.1

- Bug

  - \[AAAFS-6\] - Docs issues

- Task

  - \[AAAFS-5\] - Rename app

## Version 1.3.0

- Initial Upload

# Third Party Notices

Version 1.3.5 of

PAVO Authentication App for Splunk incorporates the following Third-party software or third-party services.

- None
