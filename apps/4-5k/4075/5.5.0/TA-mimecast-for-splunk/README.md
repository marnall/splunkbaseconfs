# Mimecast for Splunk

## OVERVIEW
*  This app provides an easy way to add Mimecast gateway and audit events into your Splunk Enterprise environment, as well as a number of predefined dashboards to give you valuable, actionable insights into your organization's email security.
* Author - Mimecast
* Version - 5.5.0

## COMPATIBILITY MATRIX
* Splunk version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Python version: Python3
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome, Firefox

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-on can be set up in two ways:

1. Standalone Mode
    * Install the Mimecast for Splunk.
    * Follow all the steps mentioned in `Add-on Setup` section to configure the Add-on.
2. Distributed Environment
    * Add-on resides on Search Head machine need not require any configuration here.
    * Add-on needs to be installed and configured on the Heavy Forwarder system.
    * Execute the following command on Heavy Forwarder to forward the collected data to the indexer. `/opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997`
    * On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * Add-on needs to be installed on Search Head for CIM mapping.

> **NOTE** : For the distributed environment, only indexes of the Forwarder would be shown in the input configuration page.

## RELEASE NOTES

### Version 5.5.0
* Reused OAuth tokens until expiration to minimize API calls.

### Version 5.4.0
* Migrated Add-On for Splunk with AOB version 4.5.0
* Updated regex in search queries for dashboard panels to accommodate current data format.

### Version 5.3.0
* Migrated Add-On for Splunk with AOB version 4.3.0
* Updated Python SDK version to 2.1.0
* Updated data ingestion logic for "actions" field for TTP URL data.
* Fixed auto datetime parsing issue
* Fixed extractions issue to support special characters in the data

### Version 5.2.0
* Added compatibility with Splunk 9.3

### Version 5.1.0
* Added a new input "Mimecast Awareness Training".
* Added new dashboard "Awareness Training".

### Version 5.0.0
* Updated the endpoints to API v2.
* Updated the Input and Account page.
    * Moved 'Account Code' and 'Base URL' from Input page to Account Page.
    * Removed 'Application ID', 'Access Key' and 'Secret Key' fields from Account page.
    * Added 'Client ID' and 'Client Secret' fields for API v2 on the Account page.
* Added a new input "Mimecast SIEM - Cloud Integrated".
* Added new dashboard "Email Activity Summary - Cloud Integrated" in Email Activity.
* Resolved parsing issue for events with equal sign and new line characters.

### Version 4.2.0
* Migrated Add-On for Splunk with AOB version 4.1.4


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

## General Upgrade Steps:
* Log in to Splunk Web and navigate to Apps -> Manage Apps.
* Click Install app from file.
* Click Choose file and select the Mimecast for Splunk Add-on installation file.
* Check the Upgrade checkbox.
* Click on Upload.
* Restart Splunk.

### Upgrade to V5.5.0 from V5.4.0
- Follow General Upgrade steps.

### Upgrade to V5.4.0 from V5.3.0
- Follow General Upgrade steps.

### Upgrade to V5.3.0 from V5.2.0
- Follow General Upgrade steps.

### Upgrade to V5.2.0 from V5.0.1
- Follow General Upgrade steps.

### Upgrade to V5.1.0 from V5.0.0
- Follow General Upgrade steps.

### Upgrade to V5.0.0 from V4.2.0
- Remove/Uninstall the existing app.
- Follow General Upgrade steps.


## CONFIGURATION

### Add-on Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` or `Caching` in their respective sections.

### Account
* Navigate to the `Mimecast for Splunk` -> `Configuration` -> `Account` tab, fill in the details asked and click "Save". Field descriptions are as below:.

| Mimecast Account parameters    | Description                                 |
| ----------------------------   | ------------------------------------------- |
| Account Name\*                 | Name of the account |
| Account Code\*                 | Mimecast account code |
| Base URL\*                     | Mimecast API base url with scheme (http:// or https://) |
| Client ID\*                    | Mimecast API Client ID |
| Client Secret\*                | Mimecast API Client Secret |

**Note**: `*` denotes required fields

### Proxy (Optional)
* Navigate to `Mimecast for Splunk -> Configuration -> Proxy` tab, fill in the details asked and click "Save". Field descriptions are as below:

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
* Navigate to `Mimecast for Splunk -> Configuration -> Logging` tab, select the prefered "Log level" value from the dropdown and click "Save".

### Caching
* Navigate to `Mimecast for Splunk -> Configuration -> Caching` tab, enable or disable "Enable full caching" by checkbox and set "Custom event cache size" if required else leave it empty to make it disable.

### Create Data Input
* Navigate to `Mimecast for Splunk -> Inputs`. Click on "Create New Input", one dropdown will open with options:
    * Mimecast SIEM - Cloud Gateway
    * Mimecast SIEM - Cloud Integrated
    * Mimecast Audit - Cloud Gateway
    * Mimecast Service Health - Cloud Gateway
    * Mimecast TTP URL - Cloud Gateway
    * Mimecast TTP Impersonation Protect - Cloud Gateway
    * Mimecast TTP Attachment Protect - Cloud Gateway
    * Mimecast Data Leak Prevention - Cloud Gateway
    * Mimecast Threat Intel Feed Regional - Cloud Gateway
    * Mimecast Threat Intel Feed Targeted - Cloud Gateway
    * Mimecast Awareness Training

* Select an option and the pop-up will open accordingly.
* Provide the required information related to input and click on `Add` to configure the input. Field descriptions are as below:

**Common fields**

*  For all inputs.

    | Field Name           | Field Description                                                               |
    | -------------------  | ------------------------------------------------------------------------------- |
    | Name\*               | Unique name for the data input                                                  |
    | Interval\*           | Time interval of input in seconds                                               |
    | Index\*              | Index where data will be stored                                                 |
    | Credentials\*        | Account that you have configured in "Configuration" tab                         |

**Additional Field for below inputs**

* "Mimecast TTP URL - Cloud Gateway", "Mimecast TTP Impersonation Protect - Cloud Gateway" and "Mimecast TTP Attachment Protect - Cloud Gateway"

    | Field Name           | Field Description                                                               |
    | -------------------  | ------------------------------------------------------------------------------- |
    | Logs to fetch\*      | Log types to filter the data                                                    |


* Mimecast Data Leak Prevention - Cloud Gateway

    | Field Name           | Field Description                                                               |
    | -------------------  | ------------------------------------------------------------------------------- |
    | Actions\*            | Actions to filter the data                                                      |

**Note**: `*` denotes required fields

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-mimecast-for-splunk
* Remove $SPLUNK_HOME/var/log/Splunk/ta_mimecast_for_splunk*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## TROUBLESHOOTING
### General Checks
* To troubleshoot Mimecast for Splunk, check $SPLUNK_HOME/var/log/Splunk/ta_mimecast_for_splunk*.log or user can search `index="_internal" source=*ta_mimecast_for_splunk*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_mimecast_for_splunk*.log ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this Add-on will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* Add-on icons are not showing up: The Add-on does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.

### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled).
* Check `ta_mimecast_for_splunk_<input_name>.log` file for any relevant error messages.

## Binary file declaration

* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder.

## END USER LICENSE AGREEMENT
* http://www.apache.org/licenses/LICENSE-2.0
## SUPPORT
* <https://community.mimecast.com/s/contactsupport>

## Copyright (c) 2003 - 2026 Mimecast Services Limited.