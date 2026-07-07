## Table of Contents

### OVERVIEW

- About the Slack Add-On for Splunk
- Release notes

### INSTALLATION AND CONFIGURATION

- Hardware and software requirements
- Installation steps
- Deploy to single server instance
- Deploy to distributed deployment

### USER GUIDE

- Data types
- Configure Slack Add-On for Splunk

---

### OVERVIEW

#### About the Slack Add-On for Splunk

| Author                    | Function1                                    |
| ------------------------- | -------------------------------------------- |
| App Version               | 1.3.1                                        |
| Vendor Products           | Slack                                        |
| Has index-time operations | True, this add-on must be placed on indexers |
| Create an index           | False                                        |

The Slack Add-On for Splunk allows a Splunk® Enterprise administrator to connect to their Slack instance and to use the Slack API to bring Slack logs into Splunk.

##### Scripts and binaries

- slack_logins.py - Slack Access Logs Modular Input
- slack_messages.py - Slack Messages Modular Input
- checkpointer.py - Stores information on last ran inputs

#### Release notes

##### About this release

Version 1.3.1 of the Slack Add-On for Splunk is compatible with:

| Splunk Enterprise versions | 7.0+                 |
| -------------------------- | -------------------- |
| Platforms                  | Platform Independent |
| Vendor Products            | Slack                |

#### Changes

Version 1.3.0 includes the following changes:

- Updating Message History API Call

##### Third-party software attributions

Version 1.3.0 of the Slack Add-On for Splunk incorporates the following third-party software or libraries.

- Dateutil 2.4.0, [https://pypi.python.org/pypi/python-dateutil](https://pypi.python.org/pypi/python-dateutil)
- SlackClient 1.3.2, [https://pypi.python.org/pypi/slackclient](https://pypi.python.org/pypi/slackclient)

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

Slack Add-On for Splunk supports the following server platforms in the versions supported by Splunk Enterprise:

- Linux
- Windows
- Solaris

#### Software requirements

To function properly, Slack Add-On for Splunk requires the following software:

- Slack

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download the Slack Add-On for Splunk at [https://splunkbase.splunk.com/app/3542/](https://splunkbase.splunk.com/app/3542/). See the TA-Slack folder in the app download.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

##### Web Interface

1. Click on the gear next to Apps
2. Click on Install App From File
3. Chose downloaded file and click upload

##### Configuration files

1. Untar the downloaded app
2. Copy or move the slack folder to the server and put into \$SPLUNK_HOME/etc/apps directory
3. Restart Splunk

##### Deploy to single server instance

To install the add-on to a single server instance of Splunk Enterprise choose one of the methods above.

##### Deploy to distributed deployment

**Install to search head**

Slack Add-On for Splunk doesn't need to be installed on search heads for distributed deployments.

**Install to indexers**

To install the add-on to a indexer choose one of the methods above.

**Install to forwarders**

To install the add-on to a forwarder choose one of the methods above.

## USER GUIDE

### Data types

This app provides the index-time and search-time knowledge for the following types of data from Slack:

**Data type**

Description and example

- slack:logins - Slack access logs information
- slack:messages - Slack messages information

### Configure Slack Add-On for Splunk

#### Modular Inputs

For both Slack Access Logs and Slack messages a Slack API token is needed. This token can be found at [https://api.slack.com/docs/oauth-test-tokens](https://api.slack.com/docs/oauth-test-tokens)

##### Slack Access Logs

In order to create a Slack Access Logs input a Slack API token is needed. This token must have admin privileges. The values needed are:

- name - Name of the input
- token - Slack API token
- max_days - Number of days to look back during first run

##### Slack Messages

In order to create a Slack Messages input a Slack API token is needed. This token must have channels:history privileges. The values needed upon setup are:

- name - Name of the input
- token - Slack API token
- max_days - Number of days to look back during first run

Default interval for this input is set to 10 minutes.
