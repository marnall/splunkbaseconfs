### OVERVIEW

#### About the BlueCat DNS Edge Technical Add-on for Splunk

| Author | BlueCat |
| --- | --- |
| App Version | 1.5.3 |
| Vendor Products | BlueCat DNS Edge |
| Has index-time operations | true |
| Create an index | false |
| Implements summarization | false |

The BlueCat DNS Edge Technical Add-on for Splunk is a modular input that integrates data from the BlueCat DNS Edge API with Splunk. This app allows DNS administrators and security professionals to collect, monitor, and alert on policy events from their BlueCat DNS Edge service points.

##### Scripts and binaries

bluecat_dns_edge.py - Script for collecting data from BlueCat DNS Edge API.
credential_manager.py - Script for storing and retrieving credentials securely.
responsehandlers.py - Script for cleaning up data collected from BlueCat DNS Edge API for Splunk ingestion.

#### Release notes

##### About this release

Version 1.5.3 of the BlueCat DNS Edge Technical Add-on for Splunk is compatible with:

| Splunk Enterprise versions | 7.0 & 8.0 & 8.1 & 8.2|
| --- | --- |
| CIM | 4.9.1 |
| Platforms | Platform independent |
| Vendor Products | BlueCat DNS Edge |
| Lookup file changes | None |

##### New features

BlueCat DNS Edge Technical Add-on for Splunk includes the following new features:

- Collect data from BlueCat DNS Edge server API.
- Collect policy events and policy details.

##### Fixed issues

Version 1.5.3 of the BlueCat DNS Edge Technical Add-on for Splunk fixes the following issues:

- Configure correct Splunk timestamp recognition from BlueCat DNS Edge Technical Add-on App

##### Known issues

Version 1.5.3 of the BlueCat DNS Edge Technical Add-on for Splunk has the following known issues:

- N/A initial release

##### Third-party software attributions

Version 1.5.3 of the BlueCat DNS Edge Technical Add-on for Splunk incorporates the following third-party software or libraries.

- Python [requests](http://docs.python-requests.org/) library

##### Support and resources

**Questions and answers**

General Splunk troubleshooting advice can be found on answers.splunk.com

**Support**

Please contact edge-splunk@bluecatnetworks.com for support.

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

BlueCat DNS Edge Technical Add-on for Splunk can be installed on any server that meets the Splunk reference hardware specifications.

#### Software requirements

BlueCat DNS Edge for Splunk does not require any additional software.

#### Splunk Enterprise system requirements

Because this app runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download the BlueCat DNS Edge Technical Add-on for Splunk from [Splunkbase](splunkbase.splunk.com)

#### Installation steps

The BlueCat DNS Edge Technical Add-on for Splunk is intended to be deployed on Splunk Search Heads. Data collection is intended to be configured on a Splunk Heavy Forwarder but can be run on any Splunk Enterprise instance (Search Head, Indexer, All-in-one, etc.)

To install and configure this app on your supported platform, follow these steps:

1. Download the BlueCat DNS Edge Technical Add-on for Splunk from Splunkbase.
2. Login to Splunk with an administrator account (default: admin).
3. Click the "Apps" dropdown in the upper left corner of the screen and select "Manage Apps".
4. Select "Install app from file", click "Choose file", navigate to the app package downloaded in the previous step, and click "Upload".

#### Configure BlueCat DNS Edge Technical Add-on for Splunk

- After successfully installing the app, browse to "Settings" in the upper right corner of the screen, then select "Data Inputs".
- From the left hand column, select "BlueCat DNS Edge Modular Input".
- Click the green "New" button in the upper left hand corner.

##### Configure DNS Query Log Stream collection
- Name the input (e.g. DNS Query Log Stream)
- Enter the hostname of the BlueCat DNS Edge Server (e.g. customer.bluec.at) - DO NOT enter "https" or the trailing "/"
- Select the endpoint "DNS Query Log Stream"
- Enter the SIEM Credentials provided with your BlueCat DNS Edge account. Note that this API is only accessible with an applicable API access key. For more information, contact your BlueCat representative.
- Enter an interval in seconds, less than 300 seconds (DNS Query Log Stream data rotates every 5 minutes)
- Leave the sourcetype bluecat:dns:edge for the default parsing to apply
- Select "More settings" to change "host" and "index" values.
	- host: generally this should be the host data was collected by (the host this input is configured on). This is the default value.
	- index: the default is "main" but most Splunk users would send this to an index containing related data (e.g. "bluecat" or "dns"). See Splunk docs for more on indexes.
- Click "Next" to save these settings.
- A screen with a checkmark will appear indicating your modular input has been created successfully. Click "Start Searching" to begin searching logs in Splunk.
- If a red bar appears with a warning message, there is an error. Review configurations and try again or see the troubleshooting section below.

##### Configure Policy Details collection
- Name the input (e.g. Policy Details)
- Enter the hostname of the BlueCat DNS Edge Server (e.g. customer.bluec.at) - DO NOT enter "https" or the trailing "/"
- Select the endpoint "Policy Details"
- Enter a BlueCat DNS Edge client ID
- Enter the corresponding secret key and confirm
- Enter an interval in seconds. This interval dictates how often policy details are pulled into Splunk and should reflect how often BlueCat DNS Edge policies are likely to change. (e.g. 3600)
- Leave the sourcetype bluecat:dns:edge for the default parsing to apply
- Select "More settings" to change "host" and "index" values.
	- host: generally this should be the host data was collected by (the host this input is configured on). This is the default value.
	- index: the default is "main" but most Splunk users would send this to an index containing related data (e.g. "bluecat" or "dns"). See Splunk docs for more on indexes.
- Click "Next" to save these settings.
- A screen with a checkmark will appear indicating your modular input has been created successfully. Click "Start Searching" to begin searching logs in Splunk.
- If a red bar appears with a warning message, there is an error. Review configurations and try again or see the troubleshooting section below.

##### Additional Configuration Notes
- Searches for BlueCat DNS Edge data rely on a macro called "get_bluecat_dns_edge_index". By default this macro searches index=main. If you changed the index for your BlueCat data, please update this macro with the index name by going to Settings > Advanced Search > Search macros > get_bluecat_dns_edge_index and updating the search to match the index your data is in (e.g. index=bluecat)
- These inputs can be modified at any time by visiting Settings > Data Inputs > BlueCat DNS Edge Modular Input
- To get started with visualizing this data, install the BlueCat DNS Edge App for Splunk

##### Troubleshooting
- Search Splunk internal logs: index=_internal sourcetype=splunkd log_level!=INFO *bluecat_dns_edge.py*
- Verify data collection host has access to BlueCat DNS Edge server on port 443.

## USER GUIDE

### Data types

This app provides the index-time and search-time knowledge for the following types of data from BlueCat DNS Edge:

**Data type**

BlueCat DNS Edge Policy Events. These are DNS requests made to the BlueCat DNS Edge service point that triggered a policy action (monitor, allow, or block)

- bluecat:dns:edge

These data types support the following Common Information Model data models:

- Network Resolution (DNS)
