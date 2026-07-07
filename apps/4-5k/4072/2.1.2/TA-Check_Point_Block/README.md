# Check Point Block Alert Action For Splunk
**December 2023**


## Table of Contents

### OVERVIEW

- About CheckPoint Block Alert Action For Splunk
- Release notes
- Prerequisites and requirements
- Support and resources

### INSTALLATION

- Hardware and OS requirements
- Installation steps
- Deployment

### USER GUIDE

- Workflow Action
    * Known Issue


---
### OVERVIEW

#### About CheckPoint Block Alert Action For Splunk

| Author | Hurricane Labs |
| --- | --- |
| App Version | 2.1.2 |
| Vendor Products | Check Point |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

The CheckPoint Block Alert Action for Splunk allows organizations to easily block suspicious IPs on their CheckPoint systems. The app includes an adaptive response action and a workflow action.

#### Release notes

Version 2.1.2 is the seventh release. It contains updates and fixes to the setup page. Version 2.0.0 contains a bug fix to the alert action. This update is only compatible with Splunk 8+/Python 3. Version 1.0.2 contains an update to the README file. Version 1.0.1 contains minor edits to version 1.0.0. SSL verification of the API call to the management server is disabled because most servers either have self signed or non-existant certificates. You will also need to have a configured Check Point firewall for this app to function (it's in the name, so you're probably aware of this already).

##### About this release

Version 2.1.2 of the Check Point Block Alert Action For Splunk is compatible with:

| Splunk Enterprise versions | 8.0, 8.1, 8.2, 9.0, 9.1 |
| --- | --- |
| Platforms | Platform independent |
| Vendor Products | Check Point Management API, Check Point R80, R80.10 |
| Lookup file changes | None |

##### Prerequisites and Requirements

This app requires that the CheckPoint management server controlling gateways be running a version which supports the R80.x and R81.x web API. Standalone gateways are supported in addition to management servers handling multiple gateways. Gateways do not necessarily need to be running a version running the API if they are centrally managed by a management server which supports the API. By default, the app will issue a block command to all managed gateways. 

The Check Point API must be configured to allow remote connections in order for this to operate; the management API doesn’t allow remote access by default. To enable API access, open SmartConsole and navigate to Manage and Settings -> Blades -> Management API -> Advanced Settings. If this setting is changed, you will need to restart the API by SSHing into the management server and running the api restart command.


##### Support

**Support**

Support for this app is provided by Hurricane Labs. Please send questions to splunk-app@hurricanelabs.com
For a more detailed walkthrough of the app's setup and features, please see [the Hurricane Labs website](https://www.hurricanelabs.com/splunk-apps/check-point-block-alert-action-for-splunk)
Note that we will make our best effort to assist you, but as this app relies on an external product we cannot guarantee we will be able to fix problems that may occur.

* Hours: 9AM-5PM EDT Monday-Friday
* Observed Holidays: Major US Holidays


## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

Check Point Block Alert Action For Splunk supports the following server platforms in the versions supported by Splunk Enterprise:

- Linux (Tested on Ubuntu 16.04)

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Installation steps

### Single-instance
**Install to search head**

1. Install the app.
2. Click on 'Apps' in the top left corner of the Splunk UI. Then click 'Manage Apps' and search for the app. Click on 'Set up' under the 'Actions' column. Enter the appropriate information and then click Save.

### Distributed
**Install to search head**

1. Install the app.
2. Click on 'Apps' in the top left corner of the Splunk UI. Then click 'Manage Apps' and search for the app. Click on 'Set up' under the 'Actions' column. Enter the appropriate information and then click Save.

### Adaptive Response

This app contains compatibility with the Enterprise Security feature Adaptive Response. Responders can block IP addresses of suspicious traffic on the Check Point management servers configured during setup.


## User Guide

### Workflow Action
- The workflow action will show up as "(Non-IR) Issue a block command of IP: (selected IP here) to configured Check Point system"
- The included workflow action allows you to block specific IPs returned when you run a search.
- These are global and are therefore available across all apps.
- The following workflows are available. Wildcards are used to match any field containing a specific term such as *domain*:
  - execute_check_point_block
- The user should check their management server to view blocks executed with the workflow action

#### Known Issue
- The workflow action cannot be used in ES Incident Review. The (Non-IR) appearing before the action is meant to bring this greater visibility. 
- Unfortunately, there is no way to disable the action from appearing in Incident Review. 
