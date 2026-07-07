# Cisco Nexus Dashboard Insights Add-On for Splunk

## Overview

* The Cisco Nexus Insights for the data center stands out as the first comprehensive technology solution in the industry developed by Cisco for network operators to manage day-2 operations in their networks.
* Cisco Nexus Insights automates troubleshooting and helps rapid root-causing and early remediation. It also helps infrastructure owners comply with SLA requirements for their users.
* The Cisco Nexus Insights for the data center is supported on Cisco ACI and Cisco NX-OS/DCNM–based deployments.
* Cisco Nexus Dashboard Insights Add-On for Splunk collects data of Anomalies & Advisories from the Nexus API and parses the fields. Data is mapped with the CIM datamodels for Enterprise Security Use cases.


* Author - Cisco Systems, Inc

* Version - 1.1.0


## Compatibility Matrix

|                                     |                                                           |
|-------------------------------------|-----------------------------------------------------------|
| Browser                             | Google Chrome, Mozilla Firefox, Safari                    |
| OS                                  | Linux, Windows                                            |
| Splunk Enterprise Version           | 9.3.x, 9.2.x, 9.1.x                                       |
| Supported Splunk Deployment         | Splunk Cloud, Splunk Standalone and Distributed Deployment|
| Nexus Insights version              | 6.3, 6.1                                           |
| Nexus Dashboard version             | 3.3, 2.1, 2.0                                                  |

## RELEASE NOTES
### Version: 1.1.0
* Repackaged the App using Splunk’s Add-on Builder v4.3.0
* Upgraded splunklib to v2.0.2

## Recommended System Configuration

* Splunk search head system should have 16 GB of RAM and an octa-core CPU to run this app smoothly.


## Topology and Setting up Splunk Environment

     Install the main app (Cisco Nexus Dashboard Insights App for Splunk) and add-on app (Cisco Nexus Dashboard Insights Add-On for Splunk) on a single machine.

     * Here both the app resides on a single machine.
     * The main app uses the data collected by the Add-on app and builds dashboards on it.

     Install the main app and add-on app on a distributed clustered environment.
     * Install the App on a Search Head or Search Head Cluster.
     * Install and configure the Add-on on a Heavy forwarder or an Indexer. (Heavy forwarder recommended)


## Installation


Follow the below-listed steps to install an Add-On from the UI:


- Download the add-on package.

- From the UI navigate to  `Apps -> Manage Apps`.

- In the top right corner select `Install the app from file`.

- Select `Choose File` and select the App package.

- Select `Upload` and follow the prompts.

  OR

- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.


## UPGRADE

### General upgrade steps:
* Log in to Splunk Web and navigate to `Cisco Nexus Dashboard Insights Add-On for Splunk -> Inputs`.
* Here disable all configured Inputs.
* Navigate to `Apps -> Manage Apps` on Splunk menu bar.
* Click `Install app from file`.
* Click `Choose file` and select the App package.
* Check the `Upgrade` checkbox.
* Click on `Upload`.
* Restart Splunk.

### Upgrade to v1.1.0

* Follow the `General upgrade steps` section.
* No additional steps are required.


## Uninstallation and Cleanup

  This section provides the steps to uninstall App from a standalone Splunk platform installation.

  * (Optional) If you want to remove data from the Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

  * Delete the app and its directory. The app and its directory are typically located in the folder $SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:
    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>

  * You may need to remove user-specific directories created for your app by deleting any files found here: $SPLUNK_HOME/bin/etc/users/*/<appname>

  * Restart the Splunk platform. You can navigate to Settings -> Server controls and click the restart button in Splunk web UI or use the following Splunk CLI command to restart Splunk:
    * $SPLUNK_HOME/bin/splunk restart


## Account Configuration

For configuring an account for the data collection of API data, follow the below-mentioned steps in Cisco Nexus Dashboard Insights Add-On for Splunk.

- Go to Add-on by clicking on `Cisco Nexus Dashboard Insights Add-On for Splunk` from the left bar.

- Click on the Configuration Tab.

- Click on Add. 

| Input Parameters     | Required | Description                                    | 
|----------------------|----------|------------------------------------------------|
| Account Name         | True     | The unique name to identify an account         |
| Account Type         | True     | Type of account from : Local User Authentication or Remote User Authentication|
| Hostname/IP Address  | True     | Hostname or IP Address of ND (cluster/standalone ND)|
| Username             | True     | Username for ND                                |
| Password             | True     | Password for ND                                |
| Login Domain         | True (when Account Type = Remote User Authentication)| Name of the Login Domain for ND |


## Proxy Setup
For setting up the Proxy for data collection of API data, follow the below-mentioned steps in Cisco Nexus Dashboard Insights Add-On for Splunk.

- Go to Add-on by clicking on `Cisco Nexus Dashboard Insights Add-On for Splunk` from the left bar.

- Click on the `Configuration` tab.

- Click on the `Proxy` tab under the configuration tab.

- Fill in all the necessary details.

- Click on `Save`.

The significance of each field is explained below:
| Input Parameters  | Required | Description                                       |
|-------------------|----------|---------------------------------------------------|
| Enable            | No       | If the Proxy should be enabled or not             |
| Proxy Type        | No       | Type of the Proxy: HTTP (default), socks4 and socks5 |
| Host              | Yes      | Server Address of Proxy Host                      |
| Port              | Yes      | Port to the Proxy Server                          |
| User Name         | No       | Username for the Proxy Server                     |
| Password          | No       | Password for the above Username                   |
| DNS Resolution    | No       | Keep DNS Resolution on or off                     |                   

## Logging Setup

For setting up the logging for data collection of API data, follow the below-mentioned steps in Cisco Nexus Dashboard Insights Add-On for Splunk.

- Go to Add-on by clicking on `Cisco Nexus Dashboard Insights Add-On for Splunk` from the left bar.

- Click on the `Configuration` tab.

- Click on the `Logging` tab under the configuration tab.

- Select the Log level. Available log levels are Debug, Info, Warning, Error, and Critical.

- Click on `Save`.

 
## Input Creation

For creating input and data collection of API data, follow the below-mentioned steps
in Cisco Nexus Dashboard Insights Add-On for Splunk.

- Go to Add-on by clicking on `Cisco Nexus Dashboard Insights Add-On for Splunk` from the left bar.

- Click on the Inputs tab.

- Click on `Create New Input`.

- Select the type of input you want to collect the data.

- Fill in all the necessary details.

- Click on `Save`.


The significance of each field is explained below:
| Input Parameters  | Required | Description                                                                    |
|-------------------|----------|--------------------------------------------------------------------------------|
| Name              | Yes      | The unique name for advisories and anomalies data input                        |
| Interval          | Yes      | Interval time of input in seconds. Minimum is 60, Default is 60               |
| Index             | Yes      | Name of the index in which data will be indexed in Splunk. This index should be present on the Indexer in case of a distributed environment |
| Alert Type        | Yes      | Select the type of the input i.e. Anomalies or Advisories                      |
| Global Account    | Yes      | Select Account from the dropdown which is configured in the configuration page |
| Time range        | Yes      | Time range for last N hours. If 0 is specified, all events (from the start of time) should be collected. Default is 4 hours |

### SSL Configuration:
* The SSL Connection with Nexus Insights is enabled by default. Here the user need to provide SSL certificate in Splunk. To do this follow the below steps:
  * If your script uses python2.7 for data collection:
    * Navigate to folder $SPLUNK_HOME$/etc/apps/TA_cisco-NI/bin/ta_cisco_ni/aob_py2
    * Add your content at the end of the cacert.pem file.

  * If your script uses python3.7 for data collection:
    * Navigate to folder $SPLUNK_HOME$/etc/apps/TA_cisco-NI/bin/ta_cisco_ni/aob_py3
    * Add your content at the end of the cacert.pem file.

* If you want to disable SSL Connection, then follow the below steps:
  * Navigate to folder $SPLUNK_HOME$/etc/apps/TA_cisco-NI/bin
  * Change the value of `VERIFY_SSL` from `True` to `False` in the cisco_ni_constants.py file (Line Number 4).


# DATA GENERATOR
This app is provided with sample data that can be used to generate dummy data. To simulate this sample data, first of all, download the Splunk Event generator, which is available at https://github.com/splunk/eventgen, & needs to be installed at $SPLUNK_HOME/etc/apps/. This app generates the dummy data for the NI environment and populates the dashboards of the main app with the dummy data.

By default eventgen is disabled, you can follow the below steps to enable it:
  * Navigate to folder $SPLUNK_HOME$/etc/apps/TA_cisco-NI/default
  * Change the value of `disabled` from `true` to `false` for both the stanzas.
  * Restart Splunk

## Troubleshooting

* If the error message `SSL certificate verification failed. Please add a valid SSL Certificate or Change the VERIFY_SSL flag to "False"` is faced while configuring the account.
  Please set the value of the `VERIFY_SSL` parameter as `"False"` in file `$SPLUNK_HOME$/etc/apps/TA_cisco-NI/bin/cisco_ni_constants.py` Line Number 4.

* If you get any error messages in the Configuration tab on the UI, have a look at the messages coming on the config screen. You can also check logs for validation by using the below query:

    index=_internal source="*ta_cisco_ni_account_validation.log*"

* The main app dashboard can take some time before the data is returned which will populate some of the panels. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

    index="<your index>" | stats count by source type

* In particular, you should see these source types:
  * cisco:ni:anomalies
  * cisco:ni:advisories

* If you don't see these source types, please check the logs generated in the Add-on log files. Here is a sample search that will show all the logs generated by Add-on:

    index=_internal source="*ta_cisco_ni_cisco_ni*.log*"

## Binary File Declaration
The files having binary code in the addon package, are used and generated by AoB.

## Support Information
Support Offered: Yes
Email: tac@cisco.com

## Copy Right Information

Copyright (c) 2023 Cisco Systems, Inc