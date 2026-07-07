# Table of Contents

### OVERVIEW

- About Slack App for Splunk
- Release notes
- Support and resources

### INSTALLATION AND CONFIGURATION

- Hardware and software requirements
- Installation
- Configuration

### OVERVIEW

- About the TA for Slack
- Scripts and binaries
- Release notes
- Support and resources

### INSTALLATION AND CONFIGURATION

- Hardware and software requirements
- Installation 
- Deploy to single server instance
- Deploy to distributed deployment

### USER GUIDE

- Data types
- Configure TA for Slack


### OVERVIEW

### About Slack App for Splunk

| Author | Function1 |
| --- | --- |
| App Version | 1.2.3 |
| Vendor Products | Slack |
| Has index-time operations | False, need not install on indexers |
| Create an index | False |
| Implements summarization | False |

The Slack for Splunk app allows a Splunk® Enterprise administrator to access Slack logging and message events from within Splunk by utilizing Slacks API.


### Release notes

#### About this release

Version 1.2.2 of the Slack for Splunk is compatible with:

| Splunk Enterprise versions | 6.4+ |
| --- | --- |
| Platforms | Platform Independent |
| Vendor Products | Slack |

#### Changes

Version 1.2.3 includes the following changes:
- Minor dashboard updates for version and cloud compatibility

Version 1.2.2 includes the following changes:
- Dashboard Search Performance Improvements

Version 1.2.0 includes the following changes:
- Python 3 Compatibility
- Updating of Slack Libraries
- Updating Message Attachment Panels for new Slack API 

### Support and resources

#### Questions and answers ####

Direct questions specific to the Splunk app for Slack to support@function1.com.

#### Support ####

Details of app support resources, instructions, and contact information.

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

Slack App for Splunk supports the following server platforms in the versions supported by Splunk Enterprise:

- Linux
- Windows
- Solaris

#### Software requirements

To function properly, Slack App for Splunk requires the following software:

- TA for Slack installed and bringing data into the indexers

#### Splunk Enterprise system requirements

Because this app runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

### Installation Steps ###

#### Download ####

Download the Slack App for Splunk at [https://splunkbase.splunk.com/app/3542/](https://splunkbase.splunk.com/app/3542/).

To install this app on your supported platform, follow these steps:

#### Use Web Interface ####
1. On Splunk Home page, click on the gear next to Apps. 
2. Click on Install App From File
3. Chose downloaded file and click upload

#### Use Configuration Files ####
1. Untar the downloaded app
2. Copy or move the Slack folder to the server and put into $SPLUNK_HOME/etc/apps directory
3. Restart Splunk

### Configuration Steps ###

In order for the dashboards to properly populate with the correct data, the macro “slack_index” must be correctly set. This macro is used to designate which indexes the slack data is being indexed. By default the value is set to index=main. 

#### Manually configure slack index ####
1. Open macros.conf file in the Slack App for Splunk local </local> folder 
(located at $SPLUNK_HOME/etc/apps/slack_app_for_splunk/local)
2. Modify the macros.conf file to correlate to the proper indexes that contain Slack data. For example:

    `
      [slack_index]
      definition= index=<SLACK INDEX HERE>
    `
  
3. Save the changes made to file
4. Restart Splunk 

---

## OVERVIEW

### About the TA for Slack

| Author | Function1 |
| --- | --- |
| App Version | 1.0.0 |
| Vendor Products | Slack |
| Has index-time operations | True, this add-on must be placed on indexers |
| Create an index | False |

The TA for Slack allows a Splunk® Enterprise administrator to consume, analyze, and report on Slack logging events using modular inputs. 

### Scripts and binaries

- slack_logins.py - Slack Access Logs Modular Input
- slack_messages.py - Slack Messages Modular Input
- checkpointer.py - Stores information on last ran inputs

### Release notes

#### About this release

Version 1.0.0 of the TA for Slack is compatible with:

| Splunk Enterprise versions | 6.4+ |
| --- | --- |
| Platforms | Platform Independent |
| Vendor Products | Slack |

#### New features

TA for Slack includes the following new features:

- Gathers Slack's messages and puts into Splunk
- Gathers Slack's access logs and puts into Splunk

#### Third-party software attributions

Version 1.0.0 of the TA for Splunk incorporates the following third-party software or libraries.

- Dateutil 2.4.0, [https://pypi.python.org/pypi/python-dateutil](https://pypi.python.org/pypi/python-dateutil)
- Pytz 2014.0, [https://pypi.python.org/pypi/pytz/](https://pypi.python.org/pypi/pytz/)
- Websocket-Client 0.31.0, [https://pypi.python.org/pypi/websocket-client/](https://pypi.python.org/pypi/websocket-client/)
- SlackClient 1.0.2, [https://pypi.python.org/pypi/slackclient](https://pypi.python.org/pypi/slackclient)

### Support and resources

#### Questions and answers

Direct questions specific to the TA for Slack to support@function1.com.

#### Support 

Details of app support resources, instructions, and contact information.

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

TA for Slack supports the following server platforms in the versions supported by Splunk Enterprise:

- Linux
- Windows
- Solaris

#### Software requirements ####

To function properly, TA for Slack requires the following software:

- Slack

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.


### Installation Steps ###

To install and configure this app on your supported platform, follow these steps:

#### Download ####

Download the TA for Slack for Splunk at [https://splunkbase.splunk.com/app/3542/](https://splunkbase.splunk.com/app/3542/). See the TA-Slack folder in the app download. 

#### Web Interface ####
1. Click on the gear next to Apps
2. Click on Install App From File
3. Chose downloaded file and click upload

#### Configuration Files ####
1. Untar the downloaded app
2. Copy or move the slack folder to the server and put into $SPLUNK_HOME/etc/apps directory
3. Restart Splunk

### Deploy to single server instance ### 

To install the add-on to a single server instance of Splunk Enterprise choose one of the methods above.

### Deploy to distributed deployment ###

**Install to search head**

TA for Slack doesn't need to be installed on search heads for distributed deployments.

**Install to indexers**

To install the add-on to a indexer choose one of the methods above.

**Install to forwarders**

To install the add-on to a forwarder choose one of the methods above.

### Configuration Steps ###

#### Modular Inputs ####

For both Slack Access Logs and Slack messages, a Slack API token is needed. This token can be found [here](https://api.slack.com/docs/oauth-test-tokens)

Slack Access Logs - token must have admin privileges. 

Slack Messages - token must have channels:history privileges. 

#### Use setup screen to configure inputs ####

1. On Splunk Home Page, click on Slack App for Splunk
2. Click the setup button that appears to setup the app 

At any time afterwards you can access this setup page by navigation to Manager > Apps and then clicking the Setup link for the Slack App for Splunk 

#### Manually configure inputs ####
1. Open the inputs.conf file in the TA slack local</local> folder located at $SPLUNK_HOME/etc/apps/TA_slack/local. If you do not find an inputs.conf file there, create one. 
2. Modify the inputs.conf to include a stanza for each of the following 
   - name - Name of the input 
   - token - Slack API token
   - max days - Number of days to look back during first. Default interval for this input is 10

  For example: 
  ```
  
  [slack_logins://<Name of Your Input>]
   token = <Your Slack API Token Here>
   max_days = 10
  
  [slack_messages://< Name of Your Input >]
   token =  <Your Slack API Token Here>
   max_days = 10

 ```

3. Save the changes made to file
4. Restart Splunk

## USER GUIDE

### Data types

This app provides the index-time and search-time knowledge for the following types of data from Slack:

#### Data type ####

Description and example

- slack:logins - Slack access logs information
- slack:messages - Slack messages information


