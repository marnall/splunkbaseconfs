# Cisco Cyber Vision Add-On For Splunk

## Overview

* The App delivers a user experience designed to make Splunk immediately useful and relevant for typical tasks and roles. The Cisco Cyber Vision Add-On for Splunk 
Provides functionality to collect the data from Cisco Cyber Vision API.


* Author - Cisco Systems

* Version - 2.1.0


## Compatibility Matrix

|                           |                                 |
|---------------------------|---------------------------------|
| Browser                   | Google Chrome, Mozilla Firefox  |                                    
| OS                        | Linux, Windows                  |                                          
| Splunk Enterprise Version | 9.2.x, 9.1.x, 9.3.x             |                                             
| Splunk Deployment         | Standalone, Distributed, Cluster|                                          
| API Version               | Events:1.0, Components:3.0, Devices:3.0, Activities:3.0, Flows:3.0, vulnerabilities:3.0 |


## Release Notes

### Version 2.1.0
- Updated the Icons.
- Added automatic lookup to populate fields site_id and asset_system using host field.
- Updated CIM mapping.
- Migrated to AOB version 4.3.0.

### Version 2.0.0
- Added new Input for Devices data.
- Components input is now deprecated and will be removed in the newer version. Migrate to the Devices input.
- Added support for custom CA certificate on UI while creating account.

### Version 1.2.0
- Migrated to AOB version 4.2.0.


### Version 1.1.0
- Migrated to AOB version 4.1.1.
- Minor enhancement in vulnerability data collection.


## Recommended System Configuration
- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.


## Installation

Follow the below-listed steps to install an Add-On from the bundle:


- Download the add-on package.

- From the UI navigate to  `Apps -> Manage Apps`.

- In the top right corner select `Install the app from file`.

- Select `Choose File` and select the App package.

- Select `Upload` and follow the prompts.

  OR

- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.


## Configuration

For configuring an account for the data collection of API data, follow the below-mentioned steps in Cisco Cyber Vision Add-On.

- Go to Add-on by clicking on `Cisco Cyber Vision Add-On For Splunk` from the left bar.

- Click on the Configuration Tab.

- Click on Add. 

| Input Parameters  | Required | Description                                    | 
|-------------------|----------|------------------------------------------------|
| Account Name      | True     | The unique name to identify an account.        |
| IP Address        | True     | Address of server                              |
| API Token         | True     | API-Token generated from cisco cyber vision portal|

## Proxy Setup
For setting up the proxy for data collection of API data, follow the below-mentioned steps in Cisco Cyber Vision Add-on.

- Go to Add-on by clicking on `Cisco Cyber Vision Add-On For Splunk` from the left bar.

- Click on the `Configuration` tab.

- Click on the `Proxy` tab under the configuration tab

- Fill in all the necessary details

- Click on `Save`

The significance of each field is explained below:

| Input Parameters  | Required | Description                                       |
|-------------------|----------|---------------------------------------------------|
| Enable            | No       | If the proxy should be enabled or not             |
| Proxy Type        | No       | Type of the Proxy. Available options are HTTP, socks4 and socks5. Default is http. |
| Host              | Yes      | Server Address of Proxy Host                      |
| Port              | Yes      | Port to the proxy server                          |
| User Name         | No       | Username for the Proxy Server                     |
| Password          | No       | Password for the above Username                   |
| DNS Resolution    | No       | Keep DNS Resolution on or off.                    |                   

## Logging Setup

For setting up the logging for data collection of API data, follow the below-mentioned steps in Cisco Cyber Vision Add-on.

- Go to Add-on by clicking on `Cisco Cyber Vision Add-On For Splunk` from the left bar.

- Click on the `Configuration` tab.

- Click on the `Logging` tab under the configuration tab

- Select the Log level. Available log levels are Debug, Info, Warning, Error and Critical.

- Click on `Save`

 
## Input Creation

* For creating input and data collection of API data, follow the below-mentioned steps
in Cisco Cyber Vision Add-on

- Go to Add-on by clicking on `Cisco Cyber Vision Add-On For Splunk` from the left bar.

- Click on the Inputs tab.

- Click on `Create New Input`.

- Select the type of input you want to collect the data.

- Fill in all the necessary details

- Click on `Save`


The significance of each field is explained below:

| Input Parameters  | Required | Description                                       |
|-------------------|----------|---------------------------------------------------|
| Name              | Yes      | The unique name for Cisco Cyber Vision data input. |
| Interval          | Yes      | Interval time of input in seconds. Minimum is 60, Default is 300.|
| Index             | Yes      | Name of the index in which data will be indexed in Splunk. This index should be present on the Indexer in case of a distributed environment.      |
| Global Account    | Yes      | Select Cisco Cyber Vision Account from the dropdown.|
| Start Date        | Yes      | Start Time to fetch data. This field will only be applied for the endpoints which can filter the events based on time.                |


## Upgrade
### General Upgrade Steps
- Download TA-cisco_cybervision
- Go to Apps > Manage Apps and click on the "Install app from file".
- Click on "Choose File" and select the Cisco Cyber Vision Add-On for Splunk installation file.
- Check the Upgrade app checkbox and click on Upload.
- Restart the Splunk instance.

Note:
- Before upgrade disable all the enabled inputs from the UI Inputs Page. Once the upgrade is successful, user can re-enable the inputs from the UI Inputs Page.

### From (v1.0.0 / v1.1.0 / v1.2.0/ v2.0.0) to v2.1.0
- No additional upgrade steps are required. follow the "General Upgrade Steps" section mentioned above.

### From (v1.0.0 / v1.1.0 / v1.2.0) to v2.0.0
- No additional upgrade steps are required. follow the "General Upgrade Steps" section mentioned above.

### From (v1.0.0 / v1.1.0) to v1.2.0
- No additional upgrade steps are required. follow the "General Upgrade Steps" section mentioned above.

### From v1.0.0 to v1.1.0
- No additional upgrade steps are required. follow the "General Upgrade Steps" section mentioned above.


## Troubleshooting

1. If the error message `SSL certificate verification failed. Please add a valid SSL Certificate or Change VERIFY_SSL flag to False` is faced while configuring the account then please set value of the `VERIFY_SSL` parameter as `False` in file `$SPLUNK_HOME$/etc/apps/TA-cisco_cybervision/bin/TA_cisco_cybervision_utils.py` Line Number 7 OR check the path of your certificate - 

- Location for adding your certificate is - 
    - $SPLUNK_HOME/etc/apps/TA-cisco_cybervision/bin/ta_cisco_cybervision/aob_py3/certifi/cacert.pem



2. If data is not getting collected:

- Check log files `ta_cisco_cybervision_*.log` present at `$SPLUNK_HOME/var/log/splunk`.

- Also, user can use `index="_internal" source=*ta_cisco_cybervision_*.log ERROR` query to see ERROR logs in the Splunk UI.

- Try disabling and re-enabling the inputs.

Note:
- $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

## Binary file declaration

* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder.
* _speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder.


## Support Information
Email: cisco-cybervision-splunk@cisco.com


## Copyright Information
Copyright (c) 2013-2024 Cisco Systems, Inc