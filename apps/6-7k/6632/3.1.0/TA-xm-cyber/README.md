# XM Cyber

## SUMMARY

The XM Cyber Splunk Integration collects and analyzes entities, critical assets, scenarios, overall security scores, Vulnerability Risk Management data and the attack techniques that attackers might use to compromise the configured cloud environments. Integrated with Splunk, it provides visibility into potential attack paths, critical vulnerabilities, misconfigurations etc to proactively prevent breaches. The Integration also offers pre-built dashboards for easy analysis. This helps operational teams monitor and troubleshoot issues.

Author - XM Cyber
Version - 3.1.0

## REQUIREMENTS

* Splunk version 9.3.x, 9.4.x, 10.0.x, 10.2.x and 10.4.x.
* OS Support: Linux (Centos, Ubuntu) and Windows  
* Browser Support: Chrome and Firefox  
* [Splunk Common Information Model (CIM)](https://splunkbase.splunk.com/app/1621): 6.0.0  
* XM Cyber account credentials

## RELEASE NOTES

### Version: 3.1.0

* Migrated the Scenarios input and Scenarios Overview dashboard to the latest v2 endpoint.
* Migrated the Security Score input and Security Score dashboard to the latest v2 endpoint.
* Added compatibility support for Python 3.13.

### Version: 3.0.2

* Removed Base URL validation from account configuration.
* Updated Tenant field extraction to include the full Base URL instead of a partial value.

### Version: 3.0.1

* Fixed issue with entity type mapping.
* Enhanced entity data collection with additional fields: inboundTechniques, outboundTechniques, xmLabels, remoteAddress, lastCompromised, and affectedCriticalAssetsCount.
* Added support for Splunk version 10.2.x.

### Version: 3.0.0

* Removed support for Basic authentication.
* Added VRM Data input for collecting Vulnerability Risk Management data.  
* Added following dashboards to visualize VRM data: 
   * VRM Details
   * VRM Stats
   * VRM Time Chart
* Updated Dashboard and panel names for some of the dashbaords.
* Enhanced Entities Overview dashboard with Compromised vs Non-Compromised Entities panel.
* Enhanced Scenario Exposure Findings dashboard with Mitre Tactics panel.

### Version: 2.0.0

* Provided configuration page to add Account with Basic and OAuth support.  
* Provided Input page to provide data collection configurations for following Data Inputs: 
   * Audit Trail
   * All Entities
   * Sensors
   * Findings & Exposures
   * Security Score
   * Scenario
* Provided following dashboards to visualize collected data: 
   * Entity Details
   * Audit Trails Details
   * Scenarios Findings and Exposures
   * Scenarios Dashboard
   * Sensors Dashboard
   * Risk Score

## RECOMMENDED SYSTEM CONFIGURATION

* Refer to the Splunk Enterprise system requirements: [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements)

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1) Standalone Mode: Install the Add-on on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.  
2) Distributed Environment: Install Add-on on search head and Heavy forwarder (for REST API).

* Add-on resides needs to be installed on search head and should configure Macros.
* Add-on needs to be installed and configured on the Heavy forwarder system for data collection.
* Execute the following command on Heavy Forwarder to forward the collected data to the indexer.
  $SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on the search head for CIM mapping.

**NOTE:** Here $SPLUNK_HOME is the absolute path where Splunk is installed.

## INSTALLATION OF Add-on

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR 

* Directly install from the `Find More Apps` section provided in Splunk Home Dashboard.

OR 
 
* Download and extract .spl file directly into $SPLUNK\_HOME/etc/apps/ folder.
**Note**: This step is only possible with on-prem instances having backend access to Splunk.

## UPGRADATION OF Add-on

### General upgrade steps

Follow the below steps to upgrade the Add-on.

* Download the required version Add-on package.
* From UI Navigate to Apps \> Manage Apps.
* Select the `Install app from file` in the top right corner.  
* Click on `Choose File` and select the Add-on Package.  
* Check the `Upgrade app` checkbox and click on `Upload`.  
* Restart the Splunk instance if prompted.

### Upgrading to version 3.1.0

* Follow the **General upgrade steps**

### Upgrading to version 3.0.2

* Follow the **General upgrade steps**

### Upgrading to version 3.0.1

* Follow the **General upgrade steps**

### Upgrading to version 3.0.0

* Create a new account using an OAuth API key. To obtain an OAuth API key, contact your XM Cyber account administrator.
* Delete the existing account configured with Basic authentication.
* Update all existing inputs to use the new OAuth account instead of the Basic authentication account.
* Follow the **General upgrade steps**

### Upgrading to version 2.0.0

* Delete the Existing XM Cyber Add-on
* Follow the **General upgrade steps**

# CONFIGURATION OF Add-on

To Configure XM Cyber Add-on:

* Login to Splunk Web UI.  
* Navigate to Apps \> XM Cyber

## ACCOUNTS

1. Navigate to Configuration \> Accounts
2. Click on `Add` button on the right corner.  
3. Fill in the details as described in the below table.
4. Click on Add button to save the account.

| XM Cyber Account parameters | Mandatory or Optional | Description |
| :---- | :---- | :---- |
| Account Name | Mandatory | Unique Name for the account that is configured |
| BASE URL | Mandatory | The Base URL/domain name of the tenant. Example: test.xmcyber.com |
| API key | Mandatory | The API key for OAuth authentication and tenant |

## Proxy

To configure the Proxy

1. Navigate to the Configuration \> Proxy.
2. Provide your Proxy details as described in the below table.
3. Click on `Save`.

| Proxy Parameters | Mandatory or Optional | Description |
| :---- | :---- | :---- |
| Enable | Optional | To enable the proxy |
| Proxy Host | Mandatory when enabled| Host or IP of the proxy server |
| Proxy Port | Mandatory when enabled| Port for proxy server |
| Proxy Username | Optional| Username of the proxy |
| Proxy Password | Optional| Password of the proxy  |

## Logging

To configure the Logging

1. Navigate to the Configuration \> Logging.  
2. Select the Log level required.
3. Click on `Save`.

## Inputs

To configure the Inputs

1. Navigate to the Inputs page.
2. Click on `Create New Input` in the top right corner, a dropdown will be open with options:  
   * `Audit Trail`  
   * `All Entities`  
   * `Sensors`  
   * `Findings & Exposures`  
   * `Security Score`  
   * `Scenario`
   * `VRM Data`

3. Select the Input that you want to configure and a pop-up will open accordingly.  
4. Provide the Input configuration details as described in below tables.
5. Click on `Add` to save the Input configured and start the data collection.

**Audit Trail** 

Fetches audit records from the selected account in configured time intervals.

To configure Audit Trail Input, Field descriptions are as below:

| Input Parameter | Mandatory or Optional | Desciption |
| :---- | :---- | :---- |
| Name | Mandatory | Unique name to identify Input |
| Account | Mandatory | Account to collect audit records from |
| Start Date | Mandatory | Data time to collect data from |
| Interval | Mandatory | Interval to fetch the data from API |
| Index | Mandatory | Index to ingest data into |

**All Entities** 

Collect Entities report from the selected account in configured time interval.

To configure All Entites Input, Field descriptions are as below:

| Input Parameter | Mandatory or Optional | Desciption |
| :---- | :---- | :---- |
| Name | Mandatory | Unique name to identify Input |
| Account | Mandatory | Account to collect data from |
| Ingest ChokePoint Stats | Optional | Enable ChokePoint stats collection |
| Interval | Mandatory | Interval to fetch the data from API. |
| Index | Mandatory | Index to ingest data into |

**Sensors**

Collect sensor details from the selected account in the configured time interval.

To configure Sensors Input, Field descriptions are as below:

| Input Parameter | Mandatory or Optional | Desciption |
| :---- | :---- | :---- |
| Name | Mandatory | Unique name to identify Input |
| Account | Mandatory | Account to collect data from |
| Interval | Mandatory | Interval to fetch the data from API. |
| Index | Mandatory | Index to ingest data into |

**Findings & Exposures** 

Collect Findings & Exposures data from the selected account in configured time interval.

To configure Findings & Exposures Input, Field descriptions are as below:

| Input Parameter | Mandatory or Optional | Desciption |
| :---- | :---- | :---- |
| Name | Mandatory | Unique name to identify Input. |
| Account | Mandatory | Account to collect data from |
| Interval | Mandatory | Interval to fetch the data from API. |
| Index | Mandatory | Index to ingest data into. |

**Security Score** 

Collect Security risk score from the selected selected account in configured time interval.

To configure Security Score Input, Field descriptions are as below:

| Input Parameter | Mandatory or Optional | Desciption |
| :---- | :---- | :---- |
| Name | Mandatory | Unique name to identify Input. |
| Account | Mandatory | Account to collect data from |
| Time Id | Mandatory | Time Range of the report. |
| Ingest scenarios | Optional | Ingest Risk score data for all scenarios individually.|
| Interval | Mandatory | Interval to fetch the data from API. |
| Index | Mandatory | Index to ingest data into. |

**Scenario** 

Collect scenario data from the selected account in configured time interval.

To configure Scenario Input, Field descriptions are as below:

| Input Parameter | Mandatory or Optional | Desciption |
| :---- | :---- | :---- |
| Name | Mandatory | Unique name to identify Input. |
| Account | Mandatory | Account to collect data from |
| Interval | Mandatory | Interval to fetch the data from API. |
| Index | Mandatory | Index to ingest data into. |

**VRM Data** 

Collect VRM (Vulnerability Risk Management) data (Devices, Products and Vulnerabilities)from the selected account in configured time interval.

To configure VRM Data Input, Field descriptions are as below:

| Input Parameter | Mandatory or Optional | Desciption |
| :---- | :---- | :---- |
| Name | Mandatory | Unique name to identify Input. |
| Account | Mandatory | Account to collect data from |
| Interval | Mandatory | Interval to fetch the data from API. |
| Index | Mandatory | Index to ingest data into. |

## MACROS

The Add-on contains the following macros

1. **xmcyber_summariesonly**: If you want to visualize only accelerated data on the dashboards, then change this macro to summariesonly=true. Default value: summariesonly=false.
2. **xmcyber_index**: Kindly update the specific indexes in which XM Cyber data is collected. Default value: index=main.  
Example: 
* `index=main OR index=test`
* `index IN (main, test)`

To update Macros,

1. Navigate to Settings \> Advanced Search \> Search Macros  
2. In the App dropdown filter select XM Cyber  
3. click on the macro in the Name column.  
4. Update the Definition as required.  
5. click `save`.

## DATA MODEL

* The Add-on consists of XM Cyber datamodel.
* The acceleration for these data models is disabled by default.
* Please enable the data model acceleration for better performance of the dashboards .
* The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.
* Major portion of the dashboard panels are populated using data model queries and real-time searches don't work with the data model, all the real-time search filters are disabled.

### DATA MODEL CONFIGURATION

* The Data Model used in this application is not accelerated.
* Admin should manually accelerate the Data Model.
* The recommended acceleration period is 7 days. Admin can enable/disable acceleration or change the acceleration period by the following steps.
   * On Splunk menu bar, Click on Settings \> Data models
   * From the list for Data models, click Edit in the "Action" column of the row for the XM Cyber Data model.
   * From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
   * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
   * If acceleration is enabled, select the summary range to specify the acceleration period.
   * To save acceleration changes click on the Save button.

### REBUILDING DATA MODEL

In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:

* On the Splunk menu bar, Click on Settings \> Data models.
* From the list for Data models, expand the row by clicking the ">" arrow in the first column of the row for the XM Cyber Data model. This will display extra Data Model information in the "Acceleration" section.
* From the "Acceleration" section click on the "Rebuild" link.
* Monitor the status of the "Rebuild" in the field "Status" of the "Acceleration" section. Reload the page to get the latest rebuild status.

## DASHBOARDS

The Add-on contains the following dashboards

1. **Entities Overview**: Provides Entities overview per tenant. It conatins following panels:
   * Agentless Entities count
   * Agentless Entities Percentage
   * Total Entities
   * Total Critical Assets
   * Total choke points
   * Critical assets by severity
   * Entities distribution by Compromised status
   * Most impacted entities
   * Entity Details
2. **Audit Trail**: Provides Audit trail overview per tenant. It conatins following panels:It consist panels:
   * Most active users
   * User activity distribution
   * 2FA setup trend
   * Most active IP addresses
   * Audit details
3. **Scenario Exposure Findings**: Provides Finding & Exposures overview per tenant. It conatins following panels:
   * Exposures with most risk to critical assets
   * Exposures with most risk to choke points
   * Exposures with most risk to all entities
   * Mitre Tactics
   * Technique Overview
   * Exposure profile
4. **Scenarios Overview**: Provides Scenarios overview per tenant. It conatins following panels:
   * Scenarios by Risk Grade
   * Inactive Scenarios
   * Lowest scoring scenarios
   * Scenario Details  
5. **Sensors Overview**: Provides Sensors overview per tenant. It conatins following panels:
   * Sensors by OS Type
   * Sensors by Cloud Provider
   * Failed sensors by reason
   * Sensors requiring Updates
   * Sensor Version Distribution
   * Recent Status Changes
   * Sensor details
6. **Security Score**:  Provides Security score trend per tenant. It conatins following panel:
 * Security score trend
7. **VRM Details**: Provides VRM (Vulnerability Risk Management) details per tenant. It conatins following panels:
   * Vulnerabilities
   * Devices
   * Products
8. **VRM Stats**: Provides VRM statistics overview per tenant. It conatins following panels:
   * Vulnerabilities by severity
   * Vulnerabilities distribution by age
   * Vulnerabilities funnel by catalog and XM Enrichment
9. **VRM Time Chart**: Provides VRM trends over time per tenant. It conatins following panels:
   * Vulnerability severity trend
   * New vs Remediated vulnerabilities

# BINARY FILE DECLARATION

* lib/charset_normalizer/md__mypyc.cpython-312-x86_64-linux-gnu.so \- This binary file is provided by UCC  
* lib/charset_normalizer/md.cpython-312-x86_64-linux-gnu.so \- This binary file is provided by UCC

## TROUBLESHOOTING

To Troubleshoot XM Cyber

* Check $SPLUNK\_HOME/var/log/splunk/TA_xm_cyber\*.log or user can search `index="_internal" sourcetype="xmcyber:log"` query to see all the logs on UI. Also, user can use `index="_internal" source="*TA_xm_cyber*.log" ERROR` query to see ERROR logs on the Splunk UI.  
* Note that all log files of this Add-on will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.  
* If data collection is not working then ensure that the internet is active where a proxy is configured and also ensure that the kvstore is enabled. You can check current kvstore status by running following command `splunk show kvstore-status` from $SPLUNK\_HOME/bin. The output should not report any errors and status should be Ready.Alternatively, you should not receive any KVstore related error in the messages section in Splunk menu bar.

## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK\_HOME/etc/apps/TA-xm-cyber 
* Remove $SPLUNK\_HOME/var/log/splunk/*TA_xm_cyber.log*\*.  
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## SUPPORT 
* Support Email : sup-ops@xmcyber.com
* Support Offered: Email 

## COPYRIGHT INFORMATION

© 2026 XM Cyber All Rights Reserved
