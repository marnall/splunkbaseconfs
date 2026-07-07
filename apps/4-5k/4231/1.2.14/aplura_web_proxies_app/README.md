# PAVO Web Proxies App for Splunk Documentation

App for exploring and reporting on Web Proxy events

## About PAVO Web Proxies App for Splunk

|                            |                                 |
|----------------------------|---------------------------------|
| Author                     | Aplura, LLC                     |
| App Version                | 1.2.14                          |
| App Build                  | 12                              |
| Creates an index           | False                           |
| Implements summarization   | No                              |
| Summary Indexing           | False                           |
| Data Model Acceleration    | If Enabled                      |
| Data Model                 | Web                             |
| Report Acceleration        | False                           |
| Splunk Enterprise versions | 10.X, 9.X                       |
| Platforms                  | Splunk Enterprise, Splunk Cloud |

# Scripts and binaries

This App provides the following scripts:

- `Diag.py`

  - For use with the `diag` command.

- `version.py`

  - For use with keeping track of the version number within Python scripts.

# Overview

In many organizations, web proxies separate users from the Web at large. User web activity can often be a good indicator of possible compromise, phishing attempts, abuse, and outdated software. This app provides Splunk dashboards, forms, and reports which can be used to explore your web proxy events, and make sense of what can often be a large volume of data.

To do this, the app relies on the Splunk Common Information Model (CIM) for Web events. This means that the app can report on any web proxy data, as long as it has been on-boarded properly, and is available through the Web data model.

# A note on Splunk Data Model Acceleration and Disk Space

This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on [data model acceleration, how it uses disk space, and how to plan for it](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

# A note on the Splunk Common Information Model

As mentioned above, the app uses the CIM for proxy events. The CIM allows you to take events from a number of sources or products, and report on them in one cohesive manner, using a common set of names for fields and event types.

# Available Dashboards

## Web Proxy Overview

This dashboard serves as a jumping-off point for exploring your web proxy data. It includes panels for traffic over time, categories, top talkers, and users. Clicking on panels in this dashboard will drill down to the appropriate profile page for further exploration.

## User Profile

This form provides panels based on a users activity, including source IP addresses, category history, and destinations. By focusing on a particular user, you can see browsing activity, generate a report for HR, or see where a user may have become infected.

## Source Profile

This form provides panels based on source IP addresses, often the users computer or servers. This includes activity over time, categories, users, user agents, and destinations. Use this form when you need to see what sites a particular IP has been visiting, which is useful if you find an un-authenticated session which is attempting to visit different sites.

## Category Profile

This form provides panels based on a category. This includes requests over time, destinations, users, and sources. If particular categories are of concern for your organization, you can use this form to find users or systems which have visited the category.

## Destination Profile

This form provides panels based on destination, which may be a hostname or IP address. This includes URLs, categories, users, and sources. Using this form allows you to see what users visited a particular site, and which URLs are popular with your users. On sites which are categorized based on different URLs, you can see all the categories for visits to the destination. If you know of a compromised site (such as a watering hole attack), you can use this form to quickly find users and systems which may have visited it.

## Policy Exceptions

This dashboard shows users going to bad categories, showing the categories and user activity. Note that the selection of bad categories, which often changes from organization to organization, can be customized by following the steps in the section titled `Customizing Categories for Policy Exceptions`. Using this dashboard can highlight users which may be violating your organizations usage agreement or systems which may be compromised.

## User Agents

This dashboard provides analysis of the user-agent strings present in the web proxy events. To do this, the dashboard searches use a lookup which parses the user-agent strings. There are other lookups which perform this function, but `TA-user-agents` is used by default. For information on customizing the lookup being used, see the section titled `Customizing user-agent lookups`. Using this dashboard will help you find outdated or unauthorized browsers/software in your environment. Additionally, because some malware either modifies user-agent strings, or have their own, you may find compromised systems on your network.

## Proxy Event Search

This form provides an easy way to search proxy events for particular activity. If you already know what you are looking for, this form makes it easy to generate a search that return the events you need. Don’t forget that you can use the search icon at the bottom of the events panel to open the search in the Splunk search interface.

## Sourcetypes

This dashboard provides panels to compare and contrast the activity of sourcetypes. Use the time-picker to display sourcetype activity over time and to visualize event counts by sourcetype.

## About

A simple HTML version of this document.

## Lookups

PAVO Web Proxies App for Splunk contains the following lookup files.

- apl_web_barracuda_wfa.csv

- apl_web_bluecoat_wfa.csv

- apl_web_checkpoint_wfa.csv

- apl_web_cisco_wsa_wfa.csv

- apl_web_mcafee_wg_wfa.csv

- apl_web_palo_alto_wfa.csv

- apl_web_urlblacklist_wfa.csv

- apl_web_web_proxies_http_methods.csv

- apl_web_websense_wfa.csv

## Event Generator

PAVO Web Proxies App for Splunk does not include an event generator.

## Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: If Enabled

3.  Report Acceleration: No

# Installation and Configuration

## Prerequisites

This app depends on data models included in the Splunk Common Information Model Add-on, specifically the Web data model. Please review the information on [configuring the acceleration on the data model](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Enable_persistent_acceleration_for_a_data_model).

The Splunk Common Information Model Add-on can be downloaded from [Splunkbase](https://apps.splunk.com/app/1621/).

This app has been tested with versions 4.X of the CIM add-on.

In order to make the app respond and load quickly, accelerated data models are used to provide summary data. For this data to be available, the Web data model must be accelerated. Information on how to enable acceleration for the Web data model can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Managedatamodels#Enable_data_model_acceleration). The data model must be accelerated for the length of time for which you would like to see reporting.

The `Breakdown of Sourcetypes in Indexes in Dataset` panel on the `Data Transparency Overview` dashboard will only be seen if the `Sankey Diagram visualization` is installed.

The Sankey Diagram Visualization can be downloaded from [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/).

User-agent strings are very difficult to parse efficiently using regular expressions. To make this easier and faster, an external lookup is used. By default, the `TA-user-agents` is used, as it requires no additional data download or internet access.

`TA-user-agents` can be downloaded from here: <https://splunkbase.splunk.com/app/1843/>

The user-agent lookup being used can be customized. See the section titled `Customizing user-agent lookups` for more information.

Not all organizations are the same, so there is a good chance that the default bad categories will need to be customized to meet the needs and policies of your organization. Additionally, customizations may be required based on the type of web proxy device generating the events.

Different web proxy vendors is different category names, so one list wouldn’t cover all vendors. To enable support for different vendors, a macro named `apl_web_wfa_lookup` is used.

Currently, this app comes pre-configured with lookups for 7 different products:

- Barracuda: `apl_web_barracuda_wfa`

- Bluecoat (default): `apl_web_bluecoat_wfa`

- Cisco WSA: `apl_web_cisco_wsa_wfa`

- McAfee Web Gateway: `apl_web_mcafee_wg_wfa`

- Palo Alto Firewalls: `apl_web_palo_alto_wfa`

- URLBlacklist: `apl_web_urlblacklist_wfa`

- Websense: `apl_web_websense_wfa`

These lookup files can be found in `$SPLUNK_HOME/etc/apps/aplura_web_proxies_app/lookups`.

To configure the app to use the correct lookup for your data, edit the `apl_web_wfa_lookup` macro to match the vendor from the list above. More information on editing Splunk macros can be found in the [Splunk documentation](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Definesearchmacros).

<div class="note">

While Splunk has configuration layering for configuration files, it does not have the same layering for lookup files. This means that if you customize one of these lookup files instead of creating your own, you need to make sure to back it up before upgrading this app, as it may be overwritten.

</div>

Because your organizations policies may differ from what is represented in the provided lookups, or you may be using a product which is not listed above, you may wish to use your own custom lookup for Policy Exceptions. A custom lookup for Policy Exceptions should have two columns, `category` and `wfa`. The category column should match the name of the category produced by your proxy device to which visits from clients are not allowed, or need to be reviewed. The second column, `wfa`, should always have a value of `TRUE`. You can always look at the existing lookups for an example.

Once you have created your lookup, edit the `apl_web_wfa_lookup` macro with the name of the lookup you have created.

The use of wildcards for the lookup file is not configured out of the box, however, it can by copying the `transforms.conf` file from the `/default` directory to the `/local` directory and adjusting the configuration of the `apl_web_wfa_lookup` macro in `macros.conf`.

By default, this app uses an external lookup to provide analytics on user-agent string. The default lookup used is the `TA-user-agents` lookup, however, this can be customized to use another lookup which may be more accurate or provide more fields for customizing the dashboard.

To customize the lookup, download and installed the other lookup. Copy the `macros.conf` file from the `aplura_web_proxies_app/default` directory of the app to a `aplura_web_proxies_app/local` directory (which you may need to create). Edit the `macros.conf` file, and edit the `apl_web_user_agent_lookup` macro to be the name of the custom lookup, and then edit the `apl_web_ua_family_field` to match the high-level product name (for example IE or Firefox). The use of the macros expect that the field being used for the lookup will be the CIM-compliant `http_user_agent`. If the lookup is expecting something else, then the dashboard will need to be customized to match.

## References and Downloads

- [Sankey Diagram Custom Visualization](https://splunkbase.splunk.com/app/3112/)

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## Download

Download PAVO Web Proxies App for Splunk at <https://splunkbase.splunk.com/app/4231>.

## Installation steps

This app should be installed on a search head where the Web data model has been accelerated. More information on installing or upgrading Splunk apps can be found [here](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps).

### Installation Process Overview

- Make sure the field extractions and tags on your proxy events are correct.

- Install the Splunk Common Information Model Add-on (skip if you are installing on an ES search head).

- Install the PAVO Web Proxies App for Splunk for Splunk.

- Enable accelerations on the Web data model (skip if you are installing on an ES search head).

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

Access questions and answers specific to PAVO Web Proxies App for Splunk at <https://answers.splunk.com/app/questions/4231.html>. Be sure to tag your question with the App.

## Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

## Known Issues

Version 1.2.14 of PAVO Web Proxies App for Splunk has the following known issues:

- None

# Release notes

## Version 1.2.14

- Reviewed and Certified Splunk 10 and Splunk Cloud Compatibility

## Version 1.2.11

- Bug

  - \[APL029-419\] - Change traffic over time by action to line chart

  - \[APL029-341\] - Configure checklist.conf

- Improvement

  - \[AWPAFS-20\] - Add data transparency overview

## Version 1.2.10

- Bug

  - \[AWPAFS-18\] - Change Titles and Correct Capitalization of Sourcetypes dashboard

## Version 1.2.9

- Bug

  - \[AWPAFS-10\] - Wrong macros referenced in the documentation

- Task

  - \[AWPAFS-9\] - Rename app

## Version 1.2.8

- Initial Release

# Third Party Notices

Version 1.2.14 of PAVO Web Proxies App for Splunk incorporates the following Third-party software or third-party services.

- None
