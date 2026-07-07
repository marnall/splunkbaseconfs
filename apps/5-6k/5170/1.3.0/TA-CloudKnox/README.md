CloudKnox Add-on for Splunk
==========================

This is an add-on powered by the Splunk Add-on Builder.

# OVERVIEW
The CloudKnox Add-on for Splunk is used to get CloudKnox Privilege Analytics Report data, CloudKnox alerts, and CloudKnox platform audit logs from the CloudKnox platform. To visualize the CloudKnox data in Splunk dashboards, please install CloudKnox App for Splunk.

* Author - CloudKnox, Inc.
* Version - 1.3.0
* Build - 17
* Creates Index - False
* Prerequisites - This application requires appropriate credentials for collecting data from CloudKnox platform. For Details refer to Configuration > Add CloudKnox Credentials section.
* Compatible with:
    * Splunk Enterprise version: 8.0.x ,8.1.x and 8.2.x
    * CloudKnox API v2 for audit,alert endpoints and v3 for PAR endpoint
    * OS: Platform independent
    * Browser: Safari, Chrome and Firefox

# Release Notes Version 1.3.0
* Migrated Cloudknox Add-on for Splunk with AOB version 4.0.0

# Release Notes Version 1.2.0
* Provided API v3 support. Not backward compatible with API v2.
* Added support for different CloudKnox alerts types

# Release Notes Version 1.1.0
* Added support for CloudKnox platform audit logs
* Added support for CloudKnox alerts

# Upgrade Steps
## Version 1.2.0. to Version 1.3.0
No manual steps are required to upgrade the Cloudknox Add-on for Splunk from version 1.2.0 to version 1.3.0.
An upgradation script upgrade_existing_inputs.py exists that will handle the Add-on upgrade from 1.1.0 to 1.3.0 on restart after installation.

## Version 1.1.0. to Version 1.2.0
No manual steps are required to upgrade the Cloudknox Add-on for Splunk from version 1.1.0 to version 1.2.0.
An upgradation script upgrade_existing_inputs.py exists that will upgrade the Add-on on restart after installation.

To confirm if the upgradation is complete, check that `Updated ta_cloudknox_settings.conf file, setting has_upgraded key to 1.` log message is present in `$SPLUNK_HOME/var/log/TA-CloudKnox/cloudknox_upgrade_utility.log` log file.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

## Version 1.0.0. to Version 1.1.0
No special steps are required to upgrade the CloudKnox Add-on for Splunk from version 1.0.0 to version 1.1.0.

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. CloudKnox Add-on for Splunk, which collects data from CloudKnox using REST API calls.
    2. CloudKnox App for Splunk, which adds dashboards to visualize the CloudKnox data

* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the CloudKnox App for Splunk and CloudKnox Add-on for Splunk.
        * The CloudKnox App for Splunk uses the data collected by CloudKnox Add-on for Splunk and builds dashboards on it.
    2. **Distributed Environment**:
        * Install the CloudKnox App for Splunk and CloudKnox Add-on for Splunk on the search head. User does not need to configure an account or create an input in CloudKnox Add-on for Splunk on search head.
        * Install only CloudKnox Add-on for Splunk on the heavy forwarder. User needs to configure account and needs to create data input to collect data from CloudKnox platform.
        * User needs to manually create an index on the indexer (No need to install CloudKnox App for Splunk or CloudKnox Add-on for Splunk on indexer).

# INSTALLATION
CloudKnox Add-on for Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## 1. Add CloudKnox Credentials
To generate the required keys, open CloudKnox console and navigate to "Integration" page. Thereafter, select "Splunk" and click on "Integration" tab to generate new key. Thereafter, on Splunk instance, navigate to CloudKnox Add-on for Splunk, click on "Configuration", go to "CloudKnox Credentials" tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name           | Field Description                 |
| -------------------  | --------------------------------- |
| CloudKnox URL\*      | CloudKnox server URL              |
| Service Account ID\* | CloudKnox service account ID      |
| Access Key\*         | Service account access key        |
| Secret Key\*         | Service account secret key        |

**Note**: `*` denotes required fields

## 2. Configure Proxy (Optional)
Navigate to CloudKnox Add-on for Splunk, click on "Configuration", go to "Proxy" tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name          | Field Description                                                              |
| ------------------- | ------------------------------------------------------------------------------ |
| Enable              | Enable/Disable proxy                                                           |
| Proxy Type\*        | Type of proxy                                                                  |
| Host\*              | Hostname/IP Address of the proxy                                               |
| Port\*              | Port of proxy                                                                  |
| Username            | Username for proxy authentication (Username and Password are inclusive fields) |
| Password            | Password for proxy authentication (Username and Password are inclusive fields) |

**Note**: `*` denotes required fields

After enabling proxy, re-visit "CloudKnox Credentials" tab, fill in the details and click on "Save" to verify if proxy is in working state.

## 3. Configure Logging (Optional)
Navigate to CloudKnox Add-on for Splunk, click on "Configuration", go to "Logging" tab, select the prefered "Log level" value from the dropdown and click "Save".

## 4. Create Data Input
Navigate to CloudKnox Add-on for Splunk, click on "Inputs", click on "Create New Input" and select the type of input that you want to create. Fill in the details asked and click "Add". Field descriptions are as below:

**CloudKnox PAR Input**

| Field Name           | Field Description                         |
| -------------------  | ----------------------------------------- |
| Name\*               | Unique name for the data input            |
| Interval\*           | Time interval of input in seconds         |
| Index\*              | Index where data will be stored           |
| Auth System Type\*   | Auth system type to collect data from     |
| Auth Systems\*       | List of auth systems to collect data from |

**CloudKnox Audit Log Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Start Date           | Date in UTC from when to start collecting data. Default will be last 24 hours.  |

**CloudKnox Alerts Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| Alert Type\*         | Alert Type for the alerts to be collected.                                 |      
| Start Date           | Date in UTC from when to start collecting data. Default will be last 24 hours.  |

**Note**: `*` denotes required fields

## 5. Configure Event Types:
    
If the user has selected a default index (**Note**: *By default, Splunk considers only `main` index as default index*) in "Data Input" configuration during CloudKnox Add-on for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in "Data Input" configuration, then perform the following steps:

1. Navigate to Settings > Event types.
2. Select "CloudKnox Add-on for Splunk" from the App dropdown.
3. Click on cloudknox_index.
4. Update “index=main” with “index=<your_configured_index>” in the existing definition to use your configured index.
5. Click Save.


# OPEN SOURCE COMPONENTS AND LICENSES
Some of the components included in "CloudKnox Add-on for Splunk" are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* filelock version 3.0.12 https://pypi.org/project/filelock/ (LICENSE https://github.com/benediktschmitt/py-filelock/blob/master/LICENSE)
* requests version 2.22.0 https://pypi.org/project/requests (LICENSE https://github.com/requests/requests/blob/master/LICENSE)

# TROUBLESHOOTING
* To troubleshoot CloudKnox Add-on for Splunk please check `$SPLUNK_HOME/var/log/TA-CloudKnox/*.log` and `$SPLUNK_HOME/var/log/splunk/ta_cloudknox.log` log files.
* To check the data collected by modinput in index use query like "index=<your_index_name> source=cloudknox"
* If data for a particular auth system is not collected in PAR input, check if that particular auth system is not OFFLINE. If the auth system is offline, then data for that particular auth system will not be collected in the current invocation. The list of offline auth systems for the current invocation will be logged in `$SPLUNK_HOME/var/log/TA-CloudKnox/cloudknox_mod_input.log`

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-CloudKnox/
* Remove $SPLUNK_HOME/var/log/TA-CloudKnox/
* Remove $SPLUNK_HOME/var/log/splunk/**ta_cloudknox.log**
* To reflect the cleanup changes in UI, restart Splunk instance. Refer https://docs.splunk.com/Documentation/Splunk/8.0.6/Admin/StartSplunk documentation to get information on how to restart Splunk.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# BINARY FILE DECLARATION
* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML. https://pypi.org/project/MarkupSafe/

# SUPPORT
* Support Offered: Yes
* Support Email: support@cloudknox.io

### Copyright (c) 2021 CloudKnox, Inc.