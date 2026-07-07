## Table of Contents

### OVERVIEW

- About GoogleAppsForSplunk
- Release notes
- Performance benchmarks
- Support and resources

### INSTALLATION

- Hardware and software requirements
- Installation steps 
- Deploy to single server instance
- Deploy to distributed deployment
- Deploy to distributed deployment with Search Head Clustering
- Deploy to Splunk Cloud 


### USER GUIDE

- Key concepts
- Data types
- Lookups
- Configure GoogleAppsForSplunk
- Troubleshooting
- Upgrade
- Example Use Case-based Scenario

---
### OVERVIEW

#### About GoogleAppsForSplunk

| Author | Kyle Smith |
| --- | --- |
| App Version | 1.1.3 |
| Vendor Products | Google Apps for Work utilizing OAuth2 |
| Has index-time operations | true, The included TA add-on must be placed on indexers|
| Create an index | true |
| Implements summarization | Current, the app does not generate summries | 

GoogleAppsForSplunk allows a Splunk® Enterprise administrator to interface with Google Apps for Work, consuming the usage and administrative logs provided by Google.

##### Scripts and binaries

This App provides the following scripts:

- ga.py
  - This python file controls the ability to interface with the Google APIs.
- ga_authorize.py
  - This Python custom endpoint allows the authorization of the App to Google Apps for Splunk from the command line.

#### Release notes

##### About this release

Version _VERSION of GoogleAppsForSplunk is compatible with:

| Splunk Enterprise versions | 6.2 |
| --- | --- |
| Platforms | Splunk Cloud, Splunk Enterprise |

##### New features

GoogleAppsForSplunk includes the following new features:

- Ability to consume log information using OAuth2 of the Google Apps for Works APIs
- Converted the lookup files to KV Store lookups

##### Known issues

Version 1.1.3 of GoogleAppsForSplunk has the following known issues:

- Google Apps Administration Dashboard
  - The lookup editors do not scale to 100% of their respective panels.

##### Third-party software attributions

Version 1.1.3 of GoogleAppsForSplunk incorporates the following third-party software or libraries.

- Google Apps APIs - https://developers.google.com/google-apps/

##### Support and resources

**Questions and answers**

Access questions and answers specific to GoogleAppsForSplunk at <a href="https://answers.splunk.com">Answers</a>

**Support**

Support is available via email at splunkapps@kyleasmith.info. You can also find the author on IRC (#splunk on efnet.org). Feel free to email or ping, most reponses will be within 1-2 business days.

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Software requirements

#### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download GoogleAppsForSplunk at https://splunkbase.splunk.com/app/2714/.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Install the Core app onto all Search Heads.
1. Install the TA on all Indexers
1. If you are using a Heavy Forwarder to pull external data, install the IA on the heavy forwarder and configure either through the GUI or on the server.


##### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1. Deploy as you would any App, and restart Splunk.

##### Deploy to Splunk Cloud

1. Have your Splunk Cloud Support handle this installation.

## USER GUIDE

### Key concepts for GoogleAppsForSplunk

* You must have enabled the Google Apps APIs at https://console.developers.google.com

### Configure GoogleAppsForSplunk

1. Enable the Google Apps APIs and Authorize Splunk with Google Apps so that the modular input can pull data.
1. EDIT and enable the provided Data Inputs, replacing the domain with your domain information.

### Troubleshoot GoogleAppsForSplunk

***Problem***
Not seeing data?
***Cause***
Probable misconfiguration
***Resolution***
Check to make sure the APIs are enabled, authorized, and available to Splunk.
