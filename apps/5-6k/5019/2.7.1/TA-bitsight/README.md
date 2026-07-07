## BitSight Add-on for Splunk

## OVERVIEW

* The Add-on typically imports and enriches data from the BitSight platform, creating a rich data set ready for direct analysis or use in an App. The BitSight Add-on for Splunk will provide the below functionalities:
    * Collects data from the REST endpoint of the BitSight platform.
    * Parse the data and extract important fields.

* Author - BitSight Technologies, Inc.
* Version - 2.7.1

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Platform Independent
* Splunk Enterprise version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES

### Version 2.7.1
* Bumped the minimum required Python version to 3.13 as per Splunk standards.

### Version 2.7.0
* Migrated TA from AOB to UCC version 6.0.1.

### Version 2.6.0
* Added support of remediations data collection.

### Version 2.5.0
* Added a checkbox on Input page allowing users to skip the checkpointing.

### Version 2.4.1
* Updated header user agent to include app version and Splunk Version dynamically.
* Migrated Splunk SDK to 2.1.0

### Version 2.4.0
* Migrated to AOB version 4.2.0.

### Version 2.3.0
* Migrated to AOB version 4.1.4.

### Version 2.2.1
* Fixed API limitation.

### Version 2.2.0
* Added new input for benchmarking companies.

### Version 2.1.0
* Migrated AOB version to 4.2.0.
* Added support for 'User Behavior' type of findings.
* Added checkpoint mechanism for 'findings_summary' and 'graph' data.
* Minor bug fixes.

### Version 2.0.0
* Introduced multi-select dropdown of subscribed companies. Now data will be collected for selected companies only.
* Introduced a new field "Start Date" to support historical data collection.
* Moved the "API URL" field to the configuration tab and added account validation.
* Added configuration for WFH custom command. Now WFH data will be ingested in the configured index.
* Enhanced data collection logic to avoid data duplication.
* Separated dashboards from this package and the new app can be downloaded individually from the Splunkbase (BitSight App for Splunk).

### Version 1.0.5
* Updating for compatibility with Splunk's recently released Add-on Builder v4.0.0.

### Version 1.0.4
* The dashboard has been enhanced, including a compromised systems view.
* Changed BitSight API token user input option from Inputs page to Configuration -> Addon-Settings as per cloud app standards.
* "BitSight Work From Home Remote Office" enhancement - if the CIM mapping is in place, the user can use that to grab VPN ips instead of manually entering them.

### Version 1.0.3
* Added macros to avoid searching in all indexes and to increase search performance.
* Modified "My Company Dashboard" queries using base searches.
* Modified "Work From Home" functionality by using the VPN dataset of Network Sessions CIM data model to get IP Addresses rather than user search query to get IP Addresses.

### Version 1.0.2
* BitSight risk vector data has been separately identified using a new End_Point attribute which makes it easy for differentiation of data for SOC engineers.
* In this version, the Add-on is modified to import data from the BitSight API by checking against existing data in Splunk and only indexing data that is new. This will help reduce the duplication of data. The exception is the findings_summary which returns all results.
* Added Proxy Configuration support.
* Modified the Dashboard, Scheduled Alerts Queries & CIM model, and field names for consistency with the new indexing style.
* Added a drill-down option that enables redirection to matched events data upon clicking on individual graph elements in the dashboard.
* Added validation for API-URL to prevent unencrypted network (HTTP) calls if the user enters an HTTP URL. (Credentials are encrypted.)

### Version 1.0.1
* V1 of BitSight Security Performance Management for Splunk Add-On.

### Version 1.0.0
* V1 of the BitSight Security Performance Management for Splunk Add-On.

## RECOMMENDED SYSTEM CONFIGURATION
* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1. Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.  
2.  Distributed Environment:
    1. Configuration on SH would be required in order to run WFH custom command.
    2. Install Add-on on Search Head and Heavy Forwarder (for REST API).

* Add-on resides on Search Head machine need not require any configuration here.
* Add-on needs to be installed and configured on the Heavy Forwarder system.
* Execute the following command on Heavy Forwarder to forward the collected data to the indexer.
  `/opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997`
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on Search Head for CIM mapping.

## INSTALLATION
Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## CONFIGURATION
## 1. Add BitSight Credentials
 On Splunk instance, navigate to BitSight Add-on for Splunk, click on `Configuration -> Authentication` and fill in the details asked, and click "Save". Field descriptions are as below:

| Field Name           | Field Description                 |
| -------------------  | --------------------------------- |
|  BitSight API URL\*  | Provide BitSight API URL          |
| BitSight API Token\* | Provide BitSight API Token         |

**Note**: `*` denotes required fields

## 2. Configure Proxy (Optional)
Navigate to `BitSight Add-on for Splunk -> Configuration -> Proxy` tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name          | Field Description                                                              |
| ------------------- | ------------------------------------------------------------------------------ |
| Enable              | Enable/Disable proxy                                                           |
| Proxy Type\*        | Type of proxy                                                                  |
| Host\*              | Hostname/IP Address of the proxy                                               |
| Port\*              | Port of proxy                                                                  |
| Username            | Username for proxy authentication (Username and Password are inclusive fields) |
| Password            | Password for proxy authentication (Username and Password are inclusive fields) |

**Note**: `*` denotes required fields

## 3. Configure Logging (Optional)
Navigate to `BitSight Add-on for Splunk -> Configuration -> Logging` tab, select the prefered "Log level" value from the dropdown and click "Save".

## 4. Configure Work From Home

|       Field Name         |  Field Description                                        |
|  ----------------------  | --------------------------------------------------------  |
|   Custom Command Index   |  Enter the index in which you want to ingest data from the WFH custom command. Make sure the index exists.|

## 5. Work From Home in Distributed Environment

* Apart from the custom command index the following actions are required to run custom command on the distributed environment:
    * Make sure the entered index exists on the particular search head.
    * The collected data will be available on the configured search head only. To replicate the data on all the search heads, configure the data forwarding.

## 6. Create Data Input
Navigate to `BitSight Add-on for Splunk -> Inputs`. Click on "Create New Input". Select the input type. Fill in the details asked and click "Add". Field descriptions are as below:

**BitSight SPM Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Start Date           | The date (UTC in "YYYY-MM-DD" format) from when to start collecting the data. The default value taken will be 90 days ago. Earliest allowed date is 400 days before today.|                         |
| Companies\*          | Select the companies for which you want to collect data.                        |   
| Skip Checkpoint?\*   | Skip checkpointing mechanism if this checkbox is enabled.                       |

**BitSight Benchmarking Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Start Date           | The date (UTC in "YYYY-MM-DD" format) from when to start collecting the data. The default value taken will be 90 days ago. Earliest allowed date is 400 days before today.|                         |
| Benchmark Companies\*          | Select the benchmarked companies for which you want to collect data.                        | 
| Skip Checkpoint?\*   | Skip checkpointing mechanism if this checkbox is enabled.                       |

**Note**: `*` denotes required fields

## CUSTOM COMMAND
The following command is included as a part of the Add-on:

* wfh
    * Search format: <search_query> | eval src_ip = source_ip | table src_ip | wfh
    * Purpose: Retrieves the data from /ratings/v1/findings/wfh/ and ingests it into Splunk.

**Note**: Non-Admin user are not allowed to run the Custom Command.

## SAVEDSEARCH
* `Work From Home IPs` saved search takes VPN client ips from Network_Session. VPN CIM data model and gets ips related data from BitSight WFH endpoint.

## UPGRADE

### General Upgrade Steps

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the TA-Bitsight installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

Note :

* Before upgrade disable all the enabled inputs from the UI Inputs Page. Once the upgrade is successful, user can re-enable the inputs from the UI Inputs Page.

### From 2.x.x to 2.7.1

* To upgrade BitSight Add-On from v2.x.x to v2.7.1 you need to follow general steps as mentioned above.

### From 2.x.x to 2.7.0

* To upgrade BitSight Add-On from v2.x.x to v2.7.0 you need to follow general steps as mentioned above.

### From 2.x.x to 2.5.0

* To upgrade BitSight Add-On from v2.x.x to v2.5.0 you need to follow general steps as mentioned above.

### From 2.x.x to 2.4.1

* To upgrade BitSight Add-On from v2.x.x to v2.4.1 you need to follow general steps as mentioned above.

### From 2.0.0 to 2.1.0

* To upgrade BitSight Add-On from v2.0.0 to v2.1.0 you need to follow general steps as mentioned above.

### From 1.x.x to 2.x.x

#### Follow the below steps to upgrade the Add-on
Upgrade from BitSight Add-On 1.x.x to 2.x.x is NOT supported. Still one can install 2.x.x of BitSight Add-On by following the steps mentioned below:

* Navigate to Navigate to `BitSight Add-on for Splunk -> Inputs`. Disable all the existing inputs, and delete it.
* Install the BitSight Add-on for Splunk.
* Restart Splunk if required and if prompted by Splunk.
* Navigate to the BitSight Add-on for Splunk.
* Perform configuration as mentioned above.

## BINARY FILE DECLARATION
* pvectorc.cpython-37m-x86_64-linux-gnu.so - This is binary file.

## TROUBLESHOOTING
### If Data is not getting collected in Splunk -
* Check below log files.
    * `$SPLUNK_HOME/var/log/splunk/splunkd.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_bitsight_utils.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_bitsight_bitsight.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_bitsight_bitsight_benchmarking.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_bitsight_company_tree.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_bitsight_benchmarking_company_tree.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_bitsight_wfh.log`
* User can search for ERROR logs in the Splunk using following query.
    * `index="_internal" source=*ta_bitsight*.log ERROR`
    * `index="_internal" sourcetype=tabitsight:log ERROR`
* Check that you have selected the correct sourcetype.
* Make sure that API Key which you have entered while configuring the Account is not expired.
* Make sure that Splunk restarts or disabling of input action should not be performed while input (data collection) is running.

### If any field is not getting extracted -
* By default, Splunk extracts maximum 100 fields at a Search time. Refer Splunk doc [here](https://docs.splunk.com/Documentation/Splunk/latest/Admin/Limitsconf#.5Bkv.5D). To extract all the fields, following change needs to be done -
    * Create limits.conf in local folder of your TA ($SPLUNK_HOME/etc/apps/TA-bitsight/local) with below content.
    ```
    [kv]
    limit=0
    ```
    * Restart Splunk.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

## UNINSTALL ADD-ON
* To uninstall the add-on, the user can follow the below steps.
    * Remove $SPLUNK_HOME/etc/apps/TA-bitsight
    * Remove $SPLUNK_HOME/var/log/Splunk/ta_bitsight_*.log*.
    * To reflect the cleanup changes in UI, Restart Splunk Enterprise instance.

## SUPPORT
* Support Offered: Yes
* Email: splunk@bitsight.com

### Copyright (C) BitSight Technologies, Inc. 2026.  All rights reserved.