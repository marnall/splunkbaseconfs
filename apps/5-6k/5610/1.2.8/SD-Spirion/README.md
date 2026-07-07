## Table of Contents

### Overview

- About the TA for Spirion SDP
- Release Notes
- Support and Resources

### Installation and Configuration
- Hardware and Software Requirements
- Installation steps
- Deploy to single server instance
- Deploy to distributed deployment
- Configure Spirion Data API Inputs 

---
### Overview

#### About the TA for Spirion SDP
| Author | Spirion |
| --- | --- |
| App Version | 1.2.4 |
| Has index-time operations | true, this add-on must be placed on indexers |
| Create an index | false |
| Implements summarization | false |

Spirion is the leading provider of sensitive data risk reduction solutions. Spirion's enterprise solution accurately finds all sensitive data, anywhere, anytime and in any format on endpoints, servers, file shares, databases and in the cloud with practically zero false positives. The software eliminates and prevents sensitive data sprawl and the integration with Splunk lets customers understand and manage their risks in the context of all their other information security and business data.

Spirion's integration with Splunk enables customers to share, analyze, and correlate Spirion's sensitive data results with their existing enterprise security systems.  Replacing costly and complex third party development integration and manual data exports, the Spirion integration allows endpoints and locations to be queried by Splunk to show the amount of sensitive data each holds and the amount of data that is currently unprotected. This allows companies to quickly and easily identify where they have data breach exposure.

This product contains the Add-on which integrates Spirion sensitive data events and alerts into Splunk Enterprise. The Add-on is designed for Spirion 10.0 and above. For use with previous versions please contact Spirion.

##### Scripts and Binaries

- spirion_endpoints.py - REST Modular Input
- spirion_locations.py - REST Modular Input

#### Release Notes

Compatibility with SDP product.
##### About this release

Version 1.2.4 of the TA for Spirion SDP is compatible with:

| Splunk Enterprise versions | 7.2 |
| --- | --- |
| Platforms | Platform independent |
| Vendor Products | Spirion 10.0 and above |
| Lookup file changes | None |

##### What's New

Compatibility with SDP product.

##### Third-party software attributions

Version 1.2.4 of the TA for Spirion SDP incorporates the following third-party software or libraries:

- Requests, http://www.apache.org/licenses/LICENSE-2.0

#### Support and resources

Email: splunkinfo@spirion.com

### Installation and Configuration

#### Hardware and Software Requirements

##### Hardware Requirements

TA for Spirion SDP supports the following server platforms in the versions support by Splunk Enterprise:

- Linux
- Windows
- Solaris

##### Software Requirements

To function properly, TA for Spirion SDP requires the following software:

- Spirion Data API

##### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the Splunk Enterprise system requirements apply.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:
Download and Deploy the add-on to either a single Splunk Enterprise server or a distributed deployment
Configure your inputs to get your Spirion API data into Splunk Enterprise

##### Deploying the TA for Spirion SDP

###### Using the Web Interface:

- In Splunk Web, click Apps > Manage Apps
- Click Install app from file
- Locate the downloaded file and click Upload
- Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/TA-spirion

###### Using the configuration files:

- Untar the downloaded app
- Copy or Move the TA-spirion folder to the server and put into the $SPLUNK_HOME/etc/apps directory
- Restart Splunk

#### Deploy to single server instance

Install the TA for Spirion SDP on the single server using one of the methods described above. 

#### Deploy to distributed deployment

In a distributed deployment, the TA for Spirion SDP should be installed on the following:

- Heavy Forwarder: The inputs contained within the TA should be configured on the Heavy Forwarder.
- Indexer: The inputs does not need to be configured on the indexer unless there is only one indexer in the deployment and no Heavy Forwarder. The TA contains index time configurations and should be installed on the Indexer.
- Search Head: The inputs does not need to be configured on the Search Head. The TA does contain search time configurations and should be installed on the Search Heads.

#### Configure Spirion Data API Inputs

There are two ways to configure the inputs for this app:

##### Using the Web Interface:

On your Splunk Enterprise instance, navigate over to Settings  Data Inputs  and select the Spirion Data APIs you want to ingest into Splunk. For each input you want to add, select the input then select new  and fill out the required form.  By default sourcetype for endpoints is spirion_endpoints and sourcetype for locations is spirion_locations. The Splunk App for Spirion by default has dependencies for this sourcetype.

Input Form
The input form requires the following information from users:
name: Unique identifier for the input. 
Must be a legal filename
If name was used in a previously deleted input - Delete the file located on the server at $SPLUNK_HOME/etc/apps/TA-spirion/bin/spirion_(locations|endpoints)/ that matches it name
username: The username for the Spirion Data API 
password: The password for the Spirion Data API
url: The url or ip of the Spirion Data API

##### Using the configuration files:

Add the TA to your Splunk APP directory typically found under: $SPLUNK_HOME/etc/apps.

Create a local directory under $SPLUNK_HOME/etc/apps/TA-spirion and add an inputs.conf file in the local directory. Using the inputs.conf.spec file located in the README directory as a guide, add the username, password, and url of the Spirion API to each input. In addition, there are default time intervals, and indexs set. To override the default of any of these stanzas, create a new entry for each in local directory's copy of inputs.conf.

