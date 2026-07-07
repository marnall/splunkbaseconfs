ExtraHop Add-On for Splunk
==========================

# OVERVIEW

The ExtraHop Add-On for Splunk enables you to export ExtraHop wire data metrics as Splunk events. You can export metrics about any device group, or application from an ExtraHop Discover or Command appliance. After the Splunk platform indexes the events, you can analyze the data through the dashboards in the ExtraHop App for Splunk or by creating your own visualizations.

The ExtraHop Add-On for Splunk collects 30-second metrics through the ExtraHop REST API. Dataset metrics are collected for 5th, 25th, 50th, 75th, and 95th percentiles. All events collected by the ExtraHop Add-On for Splunk are assigned the extrahop source type.

The ExtraHop Add-On for Splunk also enables you to collect the Detections as Splunk events. You can collect the Detections from an ExtraHop Discover or Command appliance.

* Author - ExtraHop Networks
* Version - 2.7.0
* Vendor Products - ExtraHop Discover Appliance, ExtraHop Command Appliance
* Creates Index - False
* Prerequisites - This application requires appropriate credentials of Extrahop. For Details refer to Configuration > Add Account section.
* Compatible with:
    * Splunk Enterprise version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
    * OS: Linux and Windows
    * Browser: Safari, Chrome, and Firefox

# RELEASE NOTES 

## VERSION 2.7.0

* Upgraded Add-on Builder framework version to 4.5.1.
* Bumped the minimum required Python version to 3.13 as per Splunk standards.

## VERSION 2.6.0

* Upgraded Add-on Builder framework version to 4.3.0 and Splunk Python SDK version to 2.1.0.

## VERSION 2.5.0

* Upgraded Add-on Builder framework version to 4.1.3.

## VERSION 2.4.0

* Added the support of multiple Detection Categories in input.

**Note**
* The Extrahop Add-On for Splunk v2.4.0 requires a minimum of v9.3.0 of the Extrahop Appliance to perform the data collection.

## VERSION 2.3.0

* Added the support of Extrahop Appliance v9.1.2.
* Optimized the detections input data collection.

**Note**
* The Extrahop Add-On for Splunk v2.3.0 requires a minimum of v9.1.2 of the Extrahop Appliance to perform the data collection.

## VERSION 2.2.1

* Fixed lookup populating error in cluster environment.
* Added three fields "Environment Type", "Splunk Management Username" and "Splunk Management Password" to "Add-On Settings" page for Splunk Management authenctication.

## VERSION 2.2.0

* Migration to the Addon Builder v4.0.0.
* Migration of the Detections data collection from Syslog to REST API.
* Deprecated collection of Detections via Syslog (sourcetype extrahop-detection)
* Introduced new REST API based Detections input (sourcetype extrahop:detection)
* Deprecated support for Activity Group and Activity Group Summary object types for Metrics input.

## VERSION 2.1.0

* Added support for Extrahop Cloud. User can now configure On-Prem instance as well as Cloud instance from single TA.
* Moved Hostname and API field from Inputs tab to Configuration tab.
* Removed "Validate SSL Certificate" field from UI to make TA cloud compatible. Default value will be True for this field. To change, navigate to `$SPLUNK_HOME/etc/apps/TA-extrahop_addon/local/ta_extrahop_addon_settings.conf` and add `validate_ssl_certificates = 0` under `additional_parameters` stanza.
* Fixed proxy issue as the proxy was not being used while making the network calls.
* Other minor changes to make TA Splunk cloud compatible.

## VERSION 2.0.0

* Code migrated to Python 3
* Removed deprecated oidsearch command.
* Fixed a bug in extrahop-detections transform
* Added support for custom "cyclesize", allowing 5min or 1hr metric rollups
* Added support for network metrics
* Added support for summary metrics for activity groups and device groups; metrics are summed for the group for each metric cycle, instead of per-device for group members
* Added settings for custom Splunk Management API hostname and port

## VERSION 1.2.2

* Added support for ExtraHop timestamp metrics.

## VERSION 1.2.1

* Fixed issue retrieving device group metrics from Command appliances

## VERSION 1.2.0

* Added support for ExtraHop detections

## VERSION 1.1.1

* Object IDs no longer incorrect in 'extrahop' events (since 1.1.0)
* Data for ExtraHop devices and applications now retrieved at ingest time.

(NOTE: This version changes how device data is indexed in Splunk's KV Store.
It may be useful to clean the "TA_extrahop_oiddev" collection,
but it is not necessary. This can be done by running the following command:
$SPLUNK_HOME/bin/splunk clean kvstore -app TA-extrahop_addon -collection TA_extrahop_oiddev
)

## VERSION 1.1.0

* Added the ability to specify device objects in data input definitions
* Metric names are no longer incorrectly converted to lowercase
* Fixed overflow error on Windows systems when calculating time intervals

## VERSION 1.0.9

* Added support for topn_tset metrics

## VERSION 1.0.8

* Fixed issue in 'extrahop' modular input schema

## VERSION 1.0.7

* Fixed issue in ExtraHop App setup handler

## VERSION 1.0.6

* Fixed issue in Retrieve Device Information saved search command 'extrahopoid'

## VERSION 1.0.5

* Added option for SSL certificate validation on data inputs
* Added proxy support for extrahopoid command

## VERSION 1.0.2

* Added Eventgen sample files

## VERSION 1.0.1

* Fixed issue with API key retrieval

## VERSION 1.0.0

* Initial release

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration which can be found here: https://docs.splunk.com/Documentation/Splunk/latest/Capacity/Referencehardware
* The ExtraHop Add-On for Splunk requires the ExtraHop firmware version 7.1.2 or later

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This app can be set up in two ways:
    
1. **Standalone Mode**:
    * Install the ExtraHop Add-On for Splunk.
2. **Distributed Environment**:
    * Install the ExtraHop Add-On for Splunk on the search head. User does not need to configure an account or create an input in ExtraHop Add-On for Splunk on search head.
    * Install only ExtraHop Add-On for Splunk on the heavy forwarder. User needs to configure account and needs to create data input to collect data from Extrahop platform.
    * User needs to manually create an index on the indexer (No need to install ExtraHop Add-On for Splunk on indexer).

# INSTALLATION
ExtraHop Add-On for Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## Configure Account
To configure Extrahop account, navigate to ExtraHop Add-On for Splunk, click on "Configuration", go to "Accounts" tab, click on "Add" button and fill in the details asked and click "Add". Field descriptions are as below:

| Field Name        | Field Description                                          |
| ----------------- | ---------------------------------------------------------- |
| Account Name`*`   | Unique name for your account                               |
| Instance Type `*` | Instance type for data collection                          |
| Hostname`*`       | Hostname of your Extrahop account                          |
| API Key`*`           | API Key corresponding to your Extrahop On-Prem Account     |
| Client ID`*`         | Client ID corresponding to your Extrahop Cloud Account     |
| Client Secret`*`     | Client Secret corresponding to your Extrahop Cloud Account |

## Configure Add-On Settings
To configure Splunk Management settings, navigate to ExtraHop Add-On for Splunk, click on "Configuration", go to "Add-On Settings" tab,  fill in the details asked and click "Save". Field descriptions are as below:

| Field Name                    | Field Description                                                 |
| -----------------             | ----------------------------------------------------------        |
| Environment Type`*`           | Select lookup store environment type
| Splunk Management Host`*`     | Hostname/IP Address of Splunk Management                          |
| Splunk Management Port`*`     | Port of Splunk Management                                         |
| Splunk Management Username`*` | Username for Splunk Management authentication                     |
| Splunk Management Password`*` | Password for Splunk Management authentication                     |

**Notes**:
* If "Local Instance" is selected in Environment Type then other fields are not required (except Splunk Management Port).
* If "Cluster Instance" is selected in Environment Type then make sure that splunkd port 8089 of Splunk Management is open for storing lookups.

## Configure Proxy Settings
Navigate to ExtraHop Add-On for Splunk, click on "Configuration", go to the "Proxy" tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name            | Field Description                                                              |
| -------------------   | ------------------------------------------------------------------------------ |
| Enable                | Enable/Disable proxy                                                           |
| Proxy Type`*`         | Type of proxy                                                                  |
| Host`*`               | Hostname/IP Address of the proxy                                               |
| Port`*`               | Port of proxy                                                                  |
| Username              | Username for proxy authentication (Username and Password are inclusive fields) |
| Password              | Password for proxy authentication (Username and Password are inclusive fields) |
| Remote DNS resolution | Check this box if you want to use Remote DNS resolution                        |

**Note**: `*` denotes required fields

## Install the ExtraHop App for Splunk

After you install the ExtraHop Add-On for Splunk, we recommend that you install the ExtraHop App for Splunk to help you configure the ExtraHop Add-On. The ExtraHop App creates default inputs to collect metrics about HTTP, DNS, and storage activity and builds dashboards to display that information.

For more information about the ExtraHop App for Splunk, see https://splunkbase.splunk.com/app/3939/. 

## Create metric inputs for the ExtraHop Add-On for Splunk
You must create data inputs that collect information from an ExtraHop appliance to retrieve wire data metrics.

1. On the Splunk Web home screen, click the **ExtraHop Add-On for Splunk** icon in the navigation bar to launch the add-on.
2. Click **Inputs**.
3. Click **Create New Input**.
4. Click **Metrics**.
5. In the Add ExtraHop Add-On for Splunk window, specify settings for the input
**Note**: Each input can only collect metrics for a single metric category. If you want to collect metrics for multiple categories, you must create multiple inputs. Also, the Interval value provided in the input should be a multiple of the Metrics Cycle Length.
6. Click **Add**.

For the Metrics input, Field descriptions are as below:

| Field Name        | Field Description                                          |
| ----------------- | ---------------------------------------------------------- |
| Name`*`           | A unique name for the data input.                          |
| Index `*`         | Index to collect the data in Splunk.                       |
| Extrahop Account`*` | Account to be used for data collection.                  |
| Metric Cycle Length`*` | The aggregation period for metrics.                   |
| Interval`*`       | How often Splunk will collect metrics from the ExtraHop appliance, in seconds. This should be a multiple of the Metric Cycle Length.     |
| Object Type`*`    | The type of data you want to collect from the ExtraHop platform |
| Metric Category`*`| The category of metrics for this input. You can find this value under REST API Parameters in the ExtraHop Metric Catalog. |
| Metric Name`*`    | A comma-delimited list of metric names. You can find metric names under metric_specs in the ExtraHop Metric Catalog. |

## Create a data input for Detections
You must create data inputs that collect information from an ExtraHop appliance to retrieve the Detections.

1. On the Splunk Web home screen, click the **ExtraHop Add-On for Splunk** icon in the navigation bar to launch the add-on.
2. Click **Inputs**.
3. Click **Create New Input**.
4. Click **Detections**.
5. In the Add ExtraHop Add-On for Splunk window, specify settings for the input.
6. Click **Add**.

For the Detections input, Field descriptions are as below:

| Field Name        | Field Description                                          |
| ----------------- | ---------------------------------------------------------- |
| Name`*`           | A unique name for the data input.                          |
| Interval`*`       | How often Splunk will collect detections from the ExtraHop appliance (in seconds).|
| Index `*`         | Index to collect the data in Splunk.                       |
| Extrahop Account`*`   | Account to be used for data collection.                |
| Detection Categories | Comma separated categories to fetch the detections. If not provided, sec.attack would be considered as default.|
| Detection Status   | Select the status to fetch the detections. If provided None, the detections will be fetched for all the status.|

## Configure the ExtraHop Detection SIEM Connector
Follow the instructions on the [ExtraHop Detection SIEM Connector bundle page](https://www.extrahop.com/customers/community/bundles/extrahop-created/) to configure your ExtraHop appliance to send detections data to Splunk.

# UPGRADE STEPS
Follow the steps mentioned below in order to upgrade your ExtraHop Add-On for Splunk:

* Disable all the existing inputs.
* Install the ExtraHop Add-On for Splunk v2.7.0.
* Restart the Splunk if prompt.
* Navigate to ExtraHop Add-On for Splunk and Configure the Extrahop Account as mentioned [here](#Configure-Account).
* Edit all the inputs and select the configured account in the Extrahop Account dropdown.
* Enable the inputs.

# USER GUIDE

## Data types

This add-on provides the index-time and search-time knowledge for the following types of data from the ExtraHop system:

**Extrahop wire data metrics**

All ExtraHop wire data metrics have a sourcetype of extrahop.

**Extrahop detections**
All Extrahop detections have a sourcetype of extrahop:detection.

## Lookups

The ExtraHop Add-On for Splunk contains 2 KV store lookups: the **extrahop_deviceoid_lookup** and the **extrahop_appuuid_lookup**.

The **extrahop_deviceoid_lookup** adds display names, MAC addresses, and IP addresses to ExtraHop events to Splunk.

- File location: App KV Store
- Lookup fields: oid,discovery_id,display_name,macaddr,ipaddr4,ipaddr6,otype,hostname
- Lookup contents: Generated from data

The **extrahop_appuuid_lookup** saves ExtraHop appliance UUIDs for the ExtraHop App for Splunk

- File location: App KV Store
- Lookup fields: \_key,uuid
- Lookup contents: Generated from data

## Splunk Event Generator

You can configure the Splunk Event Generator to create sample ExtraHop Metrics events through the ExtraHop Add-On for Splunk. Sample event generation is configured through the eventgen.conf file. Sample events retrieve data from the samples directory of the Splunk Event Generator package. For more information about the Splunk Event Generator, see see the [Eventgen GitHub page](https://github.com/splunk/eventgen/).

# OPEN SOURCE COMPONENTS AND LICENSES
Some of the components included in "ExtraHop Add-On for Splunk" are licensed under free or open source licenses. We wish to thank the contributors to those projects. Version 2.1.0 of the ExtraHop Add-On for Splunk incorporates the following third-party software or libraries:

* Splunk Add-On Builder 3.3.0 (https://docs.splunk.com/Documentation/AddonBuilder/2.2.0/UserGuide/Overview)
* Python requests 2.18.4 (http://docs.python-requests.org/en/master/)

# TROUBLESHOOTING
* Ensure that the KV store is enabled. You can check that by visiting: https://localhost:8089/servicesNS/nobody/TA-extrahop_addon/storage/collections/data/TA_extrahop_addon_checkpointer
* For any other unknown failure, please check the $SPLUNK_HOME/var/log/ta_extrahop_addon_*.log files to get more details on the issue. Same logs can be viewed in Search using `index=_internal sourcetype="taextrahop:log"`
* You can find answers to questions about the ExtraHop App for Splunk at https://forums.extrahop.com/.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-extrahop_addon/
* Remove $SPLUNK_HOME/var/log/ta_extrahop_addon_*.log
* To reflect the cleanup changes in UI, restart Splunk instance. Refer https://docs.splunk.com/Documentation/Splunk/latest/Admin/StartSplunk documentation to get information on how to restart Splunk.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# BINARY FILE DECLARATION

* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML. https://pypi.org/project/MarkupSafe/
* pvectorc.cpython-37m-x86_64-linux-gnu.so - This is an AoB generated file.

# SUPPORT
Contact ExtraHop Support for assistance with this app at https://www.extrahop.com/support/

# COPYRIGHT
(c) 2026 ExtraHop Networks, Inc.