# Vectra XDR Technology Add-on

## OVERVIEW
*  The Vectra XDR Technology Add-on pulls entity scoring data, detection data, audit data, lockdown data and health data from the Vectra platform and does CIM mapping on detection and audit data.
* Author - Vectra AI
* Version - 1.1.2

## COMPATIBILITY MATRIX
* Splunk version: 10.0.x, 9.4.x, 9.3.x and 9.2.x
* Python version: Python3
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome, Firefox

## RELEASE NOTES
### Version: 1.1.2
* Repackaged with Python SDK v2.1.1 and Addon Builder v4.5.1 for supportability.

### Version: 1.1.1
* Migrated detection endpoint to v3.4 to utilise new parameter include_src_dst_groups.

### Version: 1.1.0
* Repackaged with Python SDK v2.1.0 and Addon Builder v4.4.1 for supportability.

### Version: 1.0.3
* Updated ingestion logic to prevent the ingestion of triaged detections.

### Version: 1.0.2
* Repackaged with App Builder v4.1.4 for supportability.

### Version: 1.0.0
* Initial version.
* Added data collection for entity scoring, detection, lockdown, health and audit events.
* Added CIM mapping for detection and audit events.

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-on can be set up in two ways:

1. Standalone Mode
    * Install the Vectra XDR Technology Add-on.
    * Follow all the steps mentioned in `Add-on Setup` section to configure the Add-on.
2. Distributed Environment
    * Add-on resides on Search Head machine need not require any configuration here.
    * Add-on needs to be installed and configured on the Heavy Forwarder system.
    * Execute the following command on Heavy Forwarder to forward the collected data to the indexer. `/opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997`
    * On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * Add-on needs to be installed on Search Head for CIM mapping.

> **NOTE** : For the distributed environment, only indexes of the Forwarder would be shown in the input configuration page.


## INSTALLATION
* Follow the below-listed steps to install the Add-on from the bundle:
    * Download the App package.
    * From the UI navigate to Apps->Manage Apps.
    * In the top right corner select Install app from file.
    * Select Choose File and select the App package.
    * Select Upload and follow the prompts.

    OR

* Directly from the Find More Apps section provided in Splunk Home Dashboard.

    OR

* Download the App package.
* Extract downloaded app package directly into `$SPLUNK_HOME/etc/apps/` folder.

## UPGRADE

### General upgrade steps:
* Log in to Splunk Web and navigate to `Vectra XDR Technology Add-on` -> Inputs.
* Here disable all configured Inputs.
* Navigate to Apps -> Manage Apps on Splunk menu bar.
* Click Install app from file.
* Click Choose file and select the `Vectra XDR Technology Add-on` installation file.
* Check the Upgrade checkbox.
* Click on Upload.
* Restart Splunk.

### Upgrade to v1.1.2
* Follow the General upgrade steps section.

### Upgrade to v1.1.1
* Follow the General upgrade steps section.

### Upgrade to v1.1.0
* Follow the General upgrade steps section.


## CONFIGURATION

### Add-on Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.

### Account
* Navigate to the `Vectra XDR Technology Add-on`-> `Configuration` -> `Account` tab, fill in the details asked and click "Save". Field descriptions are as below:.

| Vectra XDR Account parameters | Description                                 |
| ----------------------------   | ------------------------------------------- |
| Account name\*                 | Name of the account |
| Host Name\*                    | Vectra XDR API client portal url without scheme (http:// or https://) |
| Client ID\*                    | Vectra XDR API client id |
| Client Secret Key\*            | Vectra XDR API client secret key |

**Note**: `*` denotes required fields

### Proxy (Optional)
* Navigate to `Vectra XDR Technology Add-on -> Configuration -> Proxy` tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name          | Field Description                                                              |
| ------------------- | ------------------------------------------------------------------------------ |
| Enable              | Enable/Disable proxy                                                           |
| Proxy Type\*        | Type of proxy                                                                  |
| Host\*              | Hostname/IP Address of the proxy                                               |
| Port\*              | Port of proxy                                                                  |
| Username            | Username for proxy authentication (Username and Password are inclusive fields) |
| Password            | Password for proxy authentication (Username and Password are inclusive fields) |

**Note**: `*` denotes required fields

### Logging
* Navigate to `Vectra XDR Technology Add-on -> Configuration -> Logging` tab, select the prefered "Log level" value from the dropdown and click "Save".

### Create Data Input
* Navigate to `Vectra XDR Technology Add-on -> Inputs`. Click on "Create New Input", one dropdown will open with options:
    * `Entity Scoring Input`
    * `Detection Input`
    * `Audit Input`
    * `Lockdown Input`
    * `Health Input`
* Select an option and the pop-up will open accordingly.
* Provide the required information related to input and click on `Add` to configure the input. Field descriptions are as below:

**Entity Scoring Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Vectra XDR Account\* | Account that you have configured in "Configuration" tab                        |
| Historical Data      | Checkbox to pull historical data                                                 |    

**Note**: `*` denotes required fields

**Detection Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Vectra XDR Account\* | Account that you have configured in "Configuration" tab                        |
| Historical Data      | Checkbox to pull historical data                                                 |    

**Note**: `*` denotes required fields

**Audit Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Vectra XDR Account\* | Account that you have configured in "Configuration" tab                        |
| Historical Data      | Checkbox to pull historical data                                                 |    

**Note**: `*` denotes required fields

**Lockdown Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Vectra XDR Account\* | Account that you have configured in "Configuration" tab                        |

**Health Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Vectra XDR Account\* | Account that you have configured in "Configuration" tab                        | 
**Note**: `*` denotes required fields

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-Vectra-XDR
* Remove $SPLUNK_HOME/var/log/Splunk/ta_vectra_xdr_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## TROUBLESHOOTING
### General Checks
* To troubleshoot Vectra XDR Technology Add-on, check $SPLUNK_HOME/var/log/Splunk/ta_vectra_xdr*.log or user can search `index="_internal" source=*ta_vectra_xdr*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_vectra_xdr*.log ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this Add-on will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* Add-on icons are not showing up: The Add-on does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.

### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled).
* Check `ta_vectra_xdr_entity_scoring_input_<input_name>.log` file for entity scoring events, `ta_vectra_xdr_detections_input_<input_name>.log` file for detection events, `ta_vectra_xdr_audits_input_<input_name>.log` file for audit events, `ta_vectra_xdr_lockdown_input_<input_name>.log` file for lockdown events, `ta_vectra_xdr_health_input_<input_name>.log` file for health events, for any relevant error messages.

## END USER LICENSE AGREEMENT
* http://www.apache.org/licenses/LICENSE-2.0

## SUPPORT
* Email: <support@vectra.ai>

## Copyright: (c) 2025 Vectra AI, Inc. All rights reserved.
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-Vectra-XDR/bin/ta_vectra_xdr/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
