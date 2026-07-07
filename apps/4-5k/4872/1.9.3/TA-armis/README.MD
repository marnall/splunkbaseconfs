## Armis Add-On for Splunk

This is an add-on powered by the Splunk Add-on Builder.

#### OVERVIEW

- Author: Armis
- App Version: 1.9.3
- Vendor Products: Armis Security
- Creates Index: False

 The Technology Add-on for Armis allows a Splunk software administrator to collect data from the Armis portal and monitor the events in near real-time. The add-on can collect the following data :
 - Devices 
 - Application Inventory
 - Alerts
 - Vulnerabilities

These details will be fetched and ingested into Splunk so that Armis analysts can see all the required data in one place.
This add-on provides the inputs and CIM-compatible knowledge to use with other Splunk apps, such as Splunk Enterprise Security.


#### COMPATIBILITY MATRIX

- Browser: Google Chrome, Mozilla Firefox
- OS: Platform independent
- Splunk Enterprise version: 10.0.x, 9.4.x, 9.3.x and 9.2.x
- Supported Splunk Deployment: Splunk Cloud, Splunk Standalone, and Distributed Deployment

#### END USER LICENSE AGREEMENT
https://www.armis.com/legal/general-terms-and-conditions/

#### RELEASE NOTES

### v1.9.3

**Notes:**

- Added a Device Fields option to the Device input, allowing users to configure and include custom device fields.
- Reduced the minimum configurable interval for the Alerts input from 3600 seconds to 60 seconds, enabling more frequent alert polling.

### v1.9.2

**Notes:**

- Removed deprecated parameter from globalconfig file.

### v1.9.1

**Notes:**

- Updated Addon Builder to v4.5.1.
- Updated Splunklib to v2.1.1.

### v1.9.0

**Notes:**

- Optimized the Splunk add-on by switching the API for fetching Application Inventory data, thus, reducing API calls and improving performance.
- Updated the User-Agent header to include the app version.
- Updated Addon Builder to v4.4.1.
- Updated Splunklib to v2.1.0.

### v1.8.5

**Notes:**

- Updated splunklib to version 2.0.2

### v1.8.4

**Notes:**

- Updated CIM mappings for src_ip, src_mac, dest_ip and dest_mac fields of Armis API alerts data.
- Fixed an issue where the code would break due to incomplete JSON events for 'Armis Alert Enrichment' input.

### v1.8.2

**Notes:**

- Updated Add-on builder version to 4.1.4
- Updated CIM mapping for armis:alert and armis:api:alert sourcetype as per newly introduced fields in alerts data.

### v1.8.1

**Notes:**

- Added support for customProperties field in device data.
- Updated CIM mapping for syslog and API alerts data with Alerts CIM.
- Removed below incorrect CIM fields from armis:alert sourcetype.
    - body
    - dest
    - src
    - subject
    - user
    - user_name
    - vendor_account

### v1.8.0

**Notes:**

- Added Enrichment Configuration page with support for both Non-Enterprise Security and Enterprise Security users.
- Enrichment configuration allows user to enrich their third-party data by using the asset information available through the Armis portal.
- Updated Add-on builder version to 4.1.3
- Added workflow action for armis:device & enrichment sourcetypes which will be redirected to the Armis portal based on the MAC address value.

#### v1.7.2

**Notes:**

- Removed limits.conf to resolve the app inspect failures.

#### v1.7.1

**Notes:**

- Added limits.conf to resolve the issue of field extractions.

#### v1.7.0

**Notes:**

- Added Support to provide vulnerability chunk size while creating vulnerability input to create vulnerabilities chunks of that many vulnerabilities, which will be passed in one call of vuln-match API call (this API is returning vulnerabilities and devices associated with the particular vulnerability).


#### PREREQUISITES

Before installing this TA, you must have the following information from your Armis instance:

- Armis Hostname
- API Secret Key
- Configure SIEM Integration in Armis Console. For the host, use the Splunk server that will be ingesting the data (Heavy Forwarder or Input Data Manager). You can pick any open port on that machine and configure that port on the Splunk server in the installation steps.

#### DEPLOYMENT CONSIDERATIONS

This app should be installed on the Heavy Forwarder or Input Data Manager as well as all of the indexers and search heads.

#### RECOMMENDED SYSTEM CONFIGURATION

- Standard Splunk Enterprise configuration of [Search Head, Indexer, and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

#### INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard or go to the `Manage Apps` in the Splunk Dashboard then click on `Browse more apps`.

#### UPGRADE

Follow the below steps to upgrade the App.

* Go to Apps > Manage Apps and click on the "Install app from file". 
* Click on "Choose File" and select the TA-Armis installation file. 
* Check the Upgrade app checkbox and click on Upload. 
* Restart the Splunk instance.

**Note** :  

- Before upgrading disable all the enabled inputs from the UI Inputs Page. Once the upgrade is successful, the user can re-enable the inputs from the UI Inputs Page.
- Need to recollect the data of vulnerability to store vuln-device mappings data into kvstore in case of upgrading TA from a lower version than TA-1.5.x.

#### TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

- This Add-On can be set up in two ways:
1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
2) Distributed Environment: 
    - Asset Enrichment Configuration on SH would be required in order to use Enrichment functionality.
    - Install Add-on on Search Head and Heavy Forwarder (for REST API) and no configuration is required for this on SHs.
    - Add-on needs to be installed and configured on the Heavy Forwarder system.
    - Execute the following command on Heavy Forwarder to forward the collected data to the indexer. /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
    - On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    - Add-on needs to be installed on Search Head for CIM mapping.

#### Upgrading to version 1.8.5 from previous versions
- Follow the UPGRADE section.
- No additional steps are required.

#### CONFIGURATION

- After installation of Armis TA you will be redirected to the Configuration Page.
- From that you can configure the Armis Account.

**Account Configuration** :-

- For creating Armis Account fill in the following fields:-

| Input Parameters | Required | Description|
|------------------------|----------|-----------------------------------------------------------------------------|
| Account Name| Yes| Enter any unique name for the account.|
| Armis Hostname   | Yes| Armis hostname. |
| Armis API Key    | Yes| Armis API Key   | 

- After filling in all the 3 fields click on ADD button to create account.
- Necessary validations are also being added if the user enter's invalid value.


**Splunk KVStore Rest Configuration** (Optional):-

- To configure the Splunk KVStore, Navigate to the Configuration->"Splunk KVStore Rest" tab.
- Provide the required values and click on Save.

The significance of each field is explained below:

| Input Parameters | Required | Description|
|------------------------|----------|-----------------------------------------------------------------------------|
| Splunk Rest Host URL   | Yes| URL of an instance where the Armis App is present.  | 
| Port  | Yes| Management port of Splunk  |
| Splunk Username  | No| Username of Splunk instance|  
| Splunk Password  | No| Password of Splunk instance|
| Verify SSL Certificate | No  | Checkbox for For verifying "SSL Certificate" |

**NOTE** :

- No need to configure anything in this tab if both add-on and app are present in localhost. Just make sure that the "Splunk Rest Host URL" field is by default set as "localhost" and the "Port" field is by default set as "8089".
- If using Cluster environment then make sure that all fields are configured and splunkd port 8089 of Splunk Management is open for storing lookups.

**Proxy Configuration** :- 

- To configure the Proxy, Navigate to the Configuration->Proxy tab.
- Provide your Proxy credentials and click on Save.

The significance of each field is explained below:

| Input Parameters  | Required | Description    |
|-------------------|----------|---------------------------------------------------------------------------------------|
| Enable | No| If the proxy should be enabled or not|
| Proxy Type  | No| Type of the Proxy. Available options are HTTP, socks4, and socks5. The default is http.    |
| Host   | Yes| Server Address of Proxy Host   |
| Port   | Yes| Port to the proxy server  |
| User Name   | No| Username for the Proxy Server  |
| Password    | No| Password for the above Username  |


**Logging Configuration** (Optional):-

- Under the Configuration Page there is a Logging tab from where you can set your log level.
- There will be a dropdown of log levels from which you can select anyone.
- After selecting log level click on the save button.
- By default, the log level is set to 'INFO'.


##### **Input Configuration** :-

- After creating Armis Account you need to create inputs for a particular Armis Account.
- From the Inputs page you will be able to create Inputs.
- There are 4 inputs for Armis:-
    - Armis Alert Enrichment
    - Armis Alerts
    - Armis Devices
    - Armis Vulnerabilities
- For creating particular inputs click on Create New Input dropdown and select the input which you need to create.
- After adding all the fields, click on the Add button to create the input.
- Necessary validations are being handled if the user enters invalid values.

**Armis Alerts Enrichment** :-

- Initial steps for collecting syslog data which is necessary further for armis alerts data collection.
    - Go to Settings -> Data Inputs
    - Click on "+Add New" next to "TCP"
    - Type in the port that you configured in the Armis SIEM Integration and click Next.
    - Under sourcetype click New and type "armis:alert" into the text box. Under index, pick the index from the dropdown that you want the Armis data to go into. Click Review.
    - Verify that the settings are correct and click Submit.
    
- For creating armis alerts enrichment input you need to fill in the following fields:-
 
| Input Parameters | Required | Description|
|------------------------|----------|-----------------------------------------------------------------------------|
| Name  | Yes| Enter any unique name for input.  |
| Interval    | Yes| Positive integer for interval. By default, it is 3600 seconds.    |
| Index | Yes| Index in which you need to collect the data. By default - default/main. |
| Global Account   | Yes| Account for which you need to create input.  |
| Armis Alerts Index | Yes| Index in which you will collect the syslog data initially. This index will be considered as index in which we will look to find both inputs data.  |


**Armis Alerts** :-

- For creating armis device input you need to fill in the following fields:-

| Input Parameters | Required | Description|
|------------------------|----------|-----------------------------------------------------------------------------|
| Name  | Yes| Enter any unique name for input.  | 
| Interval    | Yes| Positive integer for interval. By default, it is 3600 seconds.    |
| Index | Yes| Index in which you need to collect the data. By default - default/main. |
| Global Account   | Yes| Account for which you need to create input.  |
| Lookback Days    | No  | Number of days from which alert events will be fetched. By default, it is 90.|


**Armis Devices** :-

- For creating armis device input you need to fill in the following fields:-

| Input Parameters | Required | Description|
|------------------------|----------|-----------------------------------------------------------------------------|
| Name  | Yes| Enter any unique name for input.  |  
| Interval    | Yes| Positive integer for interval. By default, it is 3600 seconds.    |
| Index | Yes| Index in which you need to collect the data. By default - default/main. |
| Global Account   | Yes| Account for which you need to create input.  |
| Device Query| Yes| AQL query for collecting data. By default value is in:devices visibility:Full timeFrame:"30 days"   |
| Device Fields | No | Fields to fetch for device data. |
| Retrieve With Full Visibility | No| Enable the checkbox for collecting Full visible devices, By default checkbox is enabled  |
| Fetch Application Inventory | No  | Enable this checkbox, if you want to collect application data.    |


**Armis Vulnerabilities** :-

- For creating armis vulnerabilities input you need to fill the following fields:-

| Input Parameters | Required | Description|
|------------------------|----------|-----------------------------------------------------------------------------|
| Name  | Yes| Enter any unique name for input.  | 
| Interval    | Yes| Positive integer for interval. By default, it is 86400 seconds.   |
| Index | Yes| Index in which you need to collect the data. By default - default/main. |
| Global Account   | Yes| Account for which you need to create input.  |
| Index Vuln-Device Mappings | No | Ingest Vulnerability and Device mapping data into the index. |
| Vulnerability Chunk Size | No | Provide chunk size to create vulnerabilities chunks of that many vulnerability_ids. which will be passed in one call of vuln-match API. |

#### ASSET ENRICHMENT CONFIGURATION
- Enrichment related configuration can be done by navigating to `Technology Add-on for Armis` -> `Asset Enrichment Configuration`.
- A Description of each of the fields is given below:

| Field Name  | Description|
|------------------------|-----------------------------------------------------------------------------|
| Configuration Deployment Type| If you have having Enterprise Security app installed then select Enterprise Security else Non - Enterprise Security  |  
| Sourcetypes | These contains the sourcetypes that are saved for Enrichment purpose |
| Enable Savedsearch | This will enable/disable savedsearch that is responsible for storing armis:device data to lookup which will be then used for enrichment purposes |
| Add New Sourcetype | Name of sourcetype for which you want to enrich data with armis:device data|
| MAC Address | Name of the field in your sourcetype corresponding to MAC Address | 
| IPv6 Address | Name of the field in your sourcetype corresponding to IPv6 Address | 
| Serial Number | Name of the field in your sourcetype correspoding to Serial Number |
| IP Address | Name of the field in your sourcetype corresponding to IPv4 Address |
| Device Name | Name of the field in your sourcetype corresponding to Device Name |

- Features of Asset Enrichment Configuration page - 
1. Add any sourcetype for which you want enrichment based on Configuration Deployment Type. 
2. Edit enrichment settings for existing sourcetype. This can be done by selecting that sourcetype from "Sourcetypes" dropdown, do the required changes and click on Save.
3. Delete a sourcetype for enrichment purposes by clicking on the Delete button after selecting a sourcetype from "Sourcetypes" dropdown.

- NOTE -
1. Only one of the "MAC Address", "IPv6 Address", "Serial Number", "IP Address" and "Device Name" is to be provided for a particular sourcetype. This field will be used to match the data from armis:device sourcetype.
2. For the best matching results, prioritize MAC Address,   IPv6 Address or Serial Number for high confidence matching. IP Address and Device Name offer medium confidence matching.

#### SAVEDSEARCHES

- This Application contains the following Saved Searches.

| Saved Searches Name   | Description  | Interval |
| ------------------------------------------------------ | --------------------------------------------------------------------------------- | -------- |
| `ARMIS - Device data for Enrichment` | To populate the lookup table with armis device data for Enrichment purposes. | 1 hour |
| `ARMIS - Device data for Enrichment for ES users` | To populate the lookup table with armis device data for Enrichment purposes for ES Users. | 1 hour |
| `Armis - Armis Notable Events for Alerts - Rule` | Generate Notable Events for alerts from Armis syslog alerts data in Splunk | 30 mins  |
| `ARMIS - Asset Lookup Gen`| savedsearch writes data of devices into 'armis_asset_list' CSV lookup. | 24 hours |

#### WORKFLOW ACTION
- This application contains workflow actions for armis:device data for mac & macAddress fields. When clicked on `Armis - View Asset Details`, it will redirect to the Armis portal based on the MAC address value.
- This application also contains workflow actions for sourcetypes that are configured for enrichment. For Non - Enterprise Security users, the workflow action is applicable on armis_asset_mac_address field in the configured sourcetype, and for Enterprise Security users, the workflow action is applicable on the dvc_mac, src_mac and dest_mac field in the configured sourcetype.

#### TROUBLESHOOTING

- General checks :
    - Note that all log files of this Add-on will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.
    - Check $SPLUNK_HOME/var/log/Splunk/ta_armis_*.log or user can search `index="_internal" source=*ta_armis_*.log` query to see all the logs in UI. Also, the user can use `index="_internal" source=*ta_armis_*.log ERROR` query to see ERROR logs in the Splunk UI.
    - To get the detailed logs, in the Splunk UI, navigate to `Technology Add-on for Armis`. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
    - If the User has marked Verify SSL Certificate as True in the Splunk KVStore Rest tab then the User needs to consider the value of Splunk Rest Host URL while generating an SSL certificate. (e.g.1.<ip_address> provided in Splunk Rest Host URL, then use ip_address while generating SSL Certificate, e.g.2 "localhost" provided then use localhost while generating SSL Certificate)
    - If the User upgrades the `Technology Add-on for Armis` for Splunk or changing the Username, Password, and Port of the Splunk Instance then the data of vulnerability-match will not be added in the KVStore lookup. So, the user needs to reconfigure the Splunk KVStore Rest tab.

- If data is not getting collected :
    - If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled).
    - Check that you have entered a valid hostname
    - Make sure that the API Key that you have entered while configuring the Account is valid and not expired.
    - Make sure that modular inputs are configured to run at different intervals. We suggest the following durations for each modular input respectively
        - 3660 secs
        - 5460 secs
        - 6060 secs
    - Also we suggest not configuring all the modular inputs at the same time. Instead, we must wait for the first modular input to finish the data fetching and after that configure the next modular input.

- If device data is collected in the custom index, then update `armis_index` macro with that custom, which is used in 'ARMIS Asset Lookup Gen' savedsearch. 'ARMIS - Asset Lookup Gen' savedsearch writes data of devices into 'armis_asset_list' CSV lookup.

Note: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

#### UNINSTALL ADD-ON

- To uninstall the add-on, the user can follow the below steps: SSH to the Splunk instance -> Go to folder apps   ($SPLUNK_HOME/etc/apps) -> Remove the TA-Armis folder from the apps directory -> Restart Splunk.

#### CLEAN-UP ADD-ON

- To clean up add-on remove $SPLUNK_HOME>etc>users>your user name>TA-armis>local folder.
- Restart Splunk.

#### SUPPORT

- Support Offered: Yes
- Email: support@armis.com

#### BINARY FILE DECLARATION
- markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML. https://pypi.org/project/MarkupSafe/.


### Copyright (C) 2026 Armis Inc. All Rights Reserved.