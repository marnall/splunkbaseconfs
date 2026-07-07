# Vectra SaaS Add-on for Splunk

## OVERVIEW
*  The Vectra SaaS Add-on for Splunk pulls account scoring and account detection data from the Vectra SaaS platform, does CIM mapping and maps the account scoring and account detection event fields to corresponding Vectra Syslog event fields.
* Author - Vectra AI
* Version - 1.1.0

## COMPATIBILITY MATRIX
* Splunk version: 9.1.x and 9.0.x
* Python version: Python3
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome, Firefox

## RELEASE NOTES
### Version: 1.1.0
* Updated add-on builder version to 4.1.4.

### Version: 1.0.0
* Added data collection for Vectra SaaS account scoring events.
* Added data collection for Vectra SaaS account detection events.
* Added CIM mapping for account detection events.
* Mapped fields of Vectra SaaS API account scoring and account detection events to corresponding Vectra syslog event fields.

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-on can be set up in two ways:

1. Standalone Mode
    * Install the Vectra SaaS Add-on for Splunk.
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
* Log in to Splunk Web and navigate to Apps -> Manage Apps.
* Click Install app from file.
* Click Choose file and select the Databricks Add-on installation file.
* Check the Upgrade checkbox.
* Click on Upload.
* Restart Splunk.

## Upgrade from Vectra SaaS Add-On for Splunk v1.0.0 to v1.1.0
* Follow the General upgrade steps section.
* No additional steps are required.

## CONFIGURATION

### Add-on Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.

### Account
* Navigate to the `Vectra SaaS Add-on for Splunk`-> `Configuration` -> `Account` tab, fill in the details asked and click "Save". Field descriptions are as below:.

| Vectra SaaS Account parameters | Description                                 |
| ----------------------------   | ------------------------------------------- |
| Account name\*                 | Name of the account |
| Host Name\*                    | Vectra SaaS API client portal url without scheme (http:// or https://) |
| Client ID\*                    | Vectra SaaS API client id |
| Client Secret Key\*            | Vectra SaaS API client secret key |

**Note**: `*` denotes required fields

### Proxy (Optional)
* Navigate to `Vectra SaaS Add-on for Splunk -> Configuration -> Proxy` tab, fill in the details asked and click "Save". Field descriptions are as below:

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
* Navigate to `Vectra SaaS Add-on for Splunk -> Configuration -> Logging` tab, select the prefered "Log level" value from the dropdown and click "Save".

### Create Data Input
* Navigate to `Vectra SaaS Add-on for Splunk -> Inputs`. Click on "Create New Input", one dropdown will open with options:
    * `Account Scoring Input`
    * `Account Detection Input`
* Select an option and the pop-up will open accordingly.
* Provide the required information related to input and click on `Add` to configure the input. Field descriptions are as below:

**Account Scoring Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Vectra SaaS Account\* | Account that you have configured in "Configuration" tab                        |
| Historical Data      | Checkbox to pull historical data                                                 |    

**Note**: `*` denotes required fields

**Account Detection Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Vectra SaaS Account\* | Account that you have configured in "Configuration" tab                        |
| Historical Data      | Checkbox to pull historical data                                                 |    

**Note**: `*` denotes required fields

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-Vectra-SaaS
* Remove $SPLUNK_HOME/var/log/Splunk/ta_vectra_saas_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## TROUBLESHOOTING
### General Checks
* To troubleshoot Vectra SaaS Add-on for Splunk, check $SPLUNK_HOME/var/log/Splunk/ta_vectra_saas*.log or user can search `index="_internal" source=*ta_vectra_saas*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_vectra_saas*.log ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this Add-on will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* Add-on icons are not showing up: The Add-on does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.

### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled).
* Check `ta_vectra_saas_account_scoring_input_<input_name>.log` file for account scoring events, `ta_vectra_saas_account_detection_input_<input_name>.log` file for account detection events for any relevant error messages.

## END USER LICENSE AGREEMENT
* http://www.apache.org/licenses/LICENSE-2.0

## SUPPORT
* Email: <support@vectra.ai>

## Copyright: (c) 2023 Vectra AI, Inc. All rights reserved.
