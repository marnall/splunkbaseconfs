# Mandiant Advantage App For Splunk

## Overview

The Mandiant Advantage App For Splunk pulls Mandiant Threat Intelligence, Security Validation Job telemetry, DTM alerts, and Attack Surface Management data from the Mandiant platform. The app performs correlation between Indicators of Compromise and security event data using Splunk CIM data models and provides dashboards to visualize data and alerts.

## Compatibility

* Splunk version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Python version: Python3
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome, Firefox and Safari

## Prerequisites

* [Splunk Common Information Model (CIM)](https://splunkbase.splunk.com/app/1621/) - required to support the **Indicator | Event Matching** feature

## Installation

**Installing from Splunkbase**

1. Log in to the Splunk Web UI and navigate to **Apps | Find More Apps**.
2. Search for Mandiant
3. Click `Install`
4. If prompted, enter your Splunkbase username and password and click `Agree and Install`
5. The app is installed

**Installing from file**

1. Log in to the Splunk Web UI and navigate to **Apps | Manage Apps**.
2. Click `Install app from file`.
3. Click `Choose file` and select the `TA-mandiant-advantage` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

**Distributed environments:** The app should be installed on both a heavy forwarder and a search head. 

### Upgrading from earlier versions

In some cases the app's Settings page does not load after an upgrade and returns an error. This is caused by caching of the app's `globalConfig.json` file in the local browser. To resolve this issue, perform a hard reload and empty cache on this page.

## Configuration

The app provides a number of modular features. Unless specifically noted, features function independently from each other.

### Enable Indicator of Compromise data collection

Enabling this feature will collect indicators of compromise from the Mandiant API and write an event for each indicator to a Splunk index. A saved search will periodically read these events and populate the `mandiant_master_lookup` KV store.

The index is intended to be used for a historical view of indicators and for threat hunting use cases. The KV Store is intended to be used for correlation searches that can trigger alerts or provide context.

**Create a Mandiant Advantage account**

NOTE: In distributed environments this step should be completed on a Splunk Heavy Forwarder

1. Log in to the Splunk Web UI, open the Mandiant Advantage App and navigate to **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Click `Add`
3. Enter an `Account Name`
4. Select `Mandiant Advantage` as the type of Account to add
5. Complete the form with the required settings as described in the table below
6. Click `Add`
7. Connectivity and authentication to the Mandiant API is verified and the account is created

| Mandiant Account parameters | Mandatory or Optional | Description                                                                                 |
| --------------------------- | --------------------- | ------------------------------------------------------------------------------------------- |
| Account name                | Mandatory             | Name of the account                                                                         |
| Mandiant Advantage Account  | Mandatory             | The account type |
| API Key Public              | Mandatory             | The Mandiant Public API Key |
| API Key Secret              | Mandatory             | The Mandiant Secret API Key  |
| Enable Proxy                | Optional              | Enable or disable proxy settings for connectivity to Mandiant |
| Proxy Type                  | Mandatory             | The proxy type that you want to use (supports HTTP/SOCK4/SOCK5) |
| Proxy Host                  | Mandatory             | Host or IP of the proxy server                                                              |
| Proxy Port                  | Mandatory             | The port that the proxy server accepts connections on |
| Proxy Username              | Optional              | Username for the proxy server                                                                |
| Proxy Password              | Optional              | Password for the proxy server                                                                |

**Create a Threat Intelligence Input**

NOTE: In distributed environments this step should be completed on a Splunk Heavy Forwarder

1. Log in to the Splunk Web UI, open the Mandiant Advantage App and navigate to the **Setup | Inputs** page
2. Select **Create New Input**, select Mandiant Threat Intelligence from the dropdown menu
3. Complete the form and click **Add** to create the input. Field descriptions are described below

| Input Parameter                 | Mandatory or Optional | Description                                                                                 |
| ------------------------------- | --------------------- | ------------------------------------------------------------------------------------------- |
| Name                            | Mandatory             | A name to uniquely identify the input                                                       |
| Interval                        | Mandatory             | Interval in seconds                                                                         |
| Index                           | Mandatory             | Index in which to store the data                                                            |
| Mandiant Advantage Account      | Mandatory             | The Mandiant Account to be used                                                             |
| Indicator Time Window           | Mandatory             | Define the age of indicators included in the `mandiant_master_lookup` lookup table. WARNING: increasing this setting will result in higher volumes of indicators in the lookup table and possible false positive alerts |
| Minimum IC Score                | Mandatory             | Indicators that have an IC score greater than or equal to the given value will be collected |
| Include Open Source Indicators  | Mandatory             | Optionally include indicators from open source intelligence sources. WARNING: enabling this setting will significantly increase the volume of indicators ingested |
| Include Threat Rating (Preview) | Mandatory             | Preview. Add Mandiant Threat Rating context to ingested indicators                          |

**Additional steps for distributed environments**

1. Disable the `mandiant_master_lookup` saved search on the Heavy Forwarder. This search creates a lookup table that is only required on the search head
2. Ensure the app is installed on a Search Head and that the `mandiant_master_lookup` saved search is enabled.

The `mandiant_master_lookup` saved search sets the index, IC Score value and time period of the query using macros. These macros have default values:

```
[mandiant_indicator_index]
definition = main

[mandiant_indicator_time_window]
definition = 30

[mandiant_min_ic_score]
definition = 80
```

These values are set when the Threat Intelligence Modular Input is saved. As the Threat Intelligence modular input is not configured on the search head it is possible to overide the defaults using config files. To do this:

1. Create a file named `macros.conf` in the `$SPLUNK_HOME/etc/apps/TA-mandiant-advantage/local` directory on the search head where the Mandiant app is installed and the `mandiant_master_lookup` saved search is enabled
2. Copy / paste the default values described above into the file
3. Edit the definition key of each macro to the desired value
4. Save the file

### Enable Indicator | Event Matching

NOTE: In distributed environments this step should be completed on a Splunk Search Head

Threat Intelligence Event Matching uses the Splunk Common Information Model data models to match indicators against Threat Intelligence from Mandiant. When a match is discovered an entry is added to the `mandiant_matched_events` lookup table for later use in dashboards and to generate notable alerts.

Before using this feature, ensure that you have successfully enabled the Indicator of Compromise Data Collection feature.

> Notable Alerts requires Splunk Enterprise Security

To enable this feature:

1. Navigate to the **Indicator | Event Matching** tab on the  **Setup | Configuration** page
2. Complete the form and click `Save`. The form fields are described below:

| Correlation parameters     | Mandatory or Optional | Description |
| -------------------------- | --------------------- | ----------- |
| Enable Event Matching         | Mandatory             | Selecting this checkbox will enable saved searches for Indicator - Event matching |
| Data Models To Match              | Mandatory             | Saved searches corresponding to the selected Splunk CIM data models to be used for event matching. |
| Enable Notable Alerts         | Optional              | Check this box to enable the creation of Notable Alerts. Notable alerts are created from Mandiant Threat Intelligence Correlation matches |
| Exclude Unattributed | Optional | Select if Correlation matches without attribution to a Malware Family or Threat Actor should be considered for notable alert creation |
| Minimum Confidence Score | Optional | The lowest score of an indicator to be considered a match when creating a notable alert |
| Exclude Actions | Optional | A comma separated list of action field values that should cause a match to be excluded from creating a notable alert, for example, if alerts should not be created for events that have an action of blocked |
| Exclude Categories | Optional | The threat categories that should cause a match to be excluded from creating a notable alert, for example, if alerts for an event matching an indicator categorized as Spam should not be created |
| Severity Definition | Optional | Selecting Mandiant IC Score calculates severity based on Mandiant's Indicator Confidence Score. NOTE: Confidence is not always reflective of Severity or Urgency |

### Enable Vulnerability Correlation

This feature correlates events containing CVE values with intelligence from Mandiant in order to inform analysts about hosts in the environment that represent a security risk. The correlation also provides the analyst with a risk rating and any known mitigations.

NOTE: This feature requires access to both the Splunk indexes and the Mandiant API. In distributed environments these steps should be completed on a Search Head with internet access. This feature is not supported in Splunk environments where the Search head cannot access the Mandiant API (https://api.intelligence.mandiant.com).

**Create a Mandiant Advantage account**

This is the same account that is used for Indicator of Compromise data collection.

**Configure Vulnerability Correlation**

1. Navigate to the **Vulnerability Correlation Settings** tab on the  **Setup | Configuration** page
2. Complete the form and click **Save**. Field descriptions can be found in the table below

| Correlation parameters     | Description |
| -------------------------- | ----------- |
| Enable Vuln Correlation    | Enables the Vulnerability Correlation saved searches    |
| Mandiant Advantage Account  | The Mandiant Advantage Account to use for correlation |
| Vuln Indices                | The index that contains the data with CVE values     |
| Vuln Sourcetypes            | The sourcetype of the data that contains CVE values |
| Vuln Fields                 | The field that contains CVE values     |
| Vuln Time Window            | The number of days correlated vulnerability data will be kept in the `mandiant_vuln_matched_lookup` lookup |

### Enable Attack Surface Management data collection

**Create an Attack Surface Management account**

NOTE: In distributed environments this step should be completed on a Splunk Heavy Forwarder

1. Log in to the Splunk Web UI, open the Mandiant Advantage App and navigate to **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Click `Add`
3. Enter an `Account Name`
4. Select `Mandiant Attack Surface Management` as the type of Account to add
5. Complete the form with the required settings as described in the table below
6. Click `Add`. Connectivity to Mandiant Account and API and authentication is verified and the account is created

| Mandiant Account parameters | Mandatory or Optional | Description                                                                                                                      |
| --------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Account name                | Mandatory             | Name of the account                                                                                                              |
| Mandiant Advantage Account  | Mandatory             | The type of account |
| Endpoint URL                | Mandatory             | The Endpoint URL for the Mandiant Attack Surface Management API (asm-api.advantage.mandiant.com) without `http://` or `https://` |
| Access Key                  | Mandatory             | The Attack Surface Management API Access Key                                                                                     |
| Secret Key                  | Mandatory             | The Attack Surface Management API Secret Key                                                                                     |
| Verify SSL Certificate      | Optional              | Specify whether API calls should be validated with certificates or not                                                           |
| Enable Proxy                | Optional              | Enable or disable proxy settings for connectivity to Mandiant |
| Proxy Type                  | Mandatory             | The proxy type that you want to use (supports HTTP/SOCK4/SOCK5) |
| Proxy Host                  | Mandatory             | Host or IP of the proxy server                                                              |
| Proxy Port                  | Mandatory             | The port that the proxy server accepts connections on |
| Proxy Username              | Optional              | Username for the proxy server                                                                |
| Proxy Password              | Optional              | Password for the proxy server                                                                |

**Create Attack Surface Management Inputs**

NOTE: In distributed environments this step should be completed on a Splunk Heavy Forwarder

1. Log in to the Splunk Web UI, open the Mandiant Advantage App and navigate to the **Setup | Inputs** page
2. Select **Create New Input**, select `Mandiant Attack Surface Management Issues` or `Mandiant Attack Surface Management Entities` from the dropdown menu
3. Complete the form and click **Add** to create the input. Field descriptions are described below


**Mandiant Attack Surface Management Issues Input**

| Input Parameter            | Mandatory or Optional | Description                                                                                |
| -------------------------- | --------------------- | ------------------------------------------------------------------------------------------ |
| Name                       | Mandatory             | A name to uniquely identify the input.                                                     |
| Interval                   | Mandatory             | Interval in seconds                                                                        |
| Index                      | Mandatory             | Index in which to store the data                                                           |
| Mandiant Advantage Account | Mandatory             | The Mandiant Account to be used, must be of type ASM                                       |
| Alerts Time Window         | Optional              | The number of days in the past to start the collection of Issue data from. Default 30 days |
| ASM Project and Collection | Mandatory             | The ASM Collection to collect issues from, this list is dynamically populated              |
| Issue Severity             | Mandatory             | The minimum issue severity to collect                                                      |

**Mandiant Attack Surface Management Entities Input**

| Input Parameter            | Mandatory or Optional | Description                                                                                 |
| -------------------------- | --------------------- | ------------------------------------------------------------------------------------------- |
| Name                       | Mandatory             | A name to uniquely identify the input.                                                      |
| Interval                   | Mandatory             | Interval in seconds                                                                         |
| Index                      | Mandatory             | Index in which to store the data                                                            |
| Mandiant Advantage Account | Mandatory             | The Mandiant Account to be used, must be of type ASM                                        |
| Alerts Time Window         | Optional              | The number of days in the past to start the collection of Entity data from. Default 30 days |
| ASM Project and Collection | Mandatory             | The ASM Collection to collect entities from, this list is dynamically populated             |
| Query                      | Optional              | A text string to further refine which entities are collected from ASM                       |


**Configure Dashboard Settings**

NOTE: In distributed environments this step should be completed on a Splunk Search Head

1. Navigate to `Dashboard Settings` tab on the **Setup | Configuration** page
2. Enter the name of the indices where the Attack Surface Management Modular Inputs were configured to write events to in the `ASM Issues Indices` setting
3. Click Save

### Enable Security Validation data collection

**Create a Mandiant Validation account**

NOTE: In distributed environments this step should be completed on a Splunk Heavy Forwarder

1. Log in to the Splunk Web UI, open the Mandiant Advantage App and navigate to **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Click **Add**
3. Enter an **Account Name**
4. Select **Mandiant Validation** as the type of Account to add
5. Complete the form with the required settings as described in the table below
6. Click **Add**. Connectivity to Mandiant Account and API and authentication is verified and the account is created

**Mandiant Validation Account**

| Mandiant Account parameters | Mandatory or Optional | Description                                                                                 |
| --------------------------- | --------------------- | ------------------------------------------------------------------------------------------- |
| Account name                | Mandatory             | Name of the account                                                                         |
| Mandiant Advantage Account  | Mandatory             | Type of the account for two different inputs:  1. Mandiant Advantage 2. Mandiant Validation |
| Endpoint URL                | Mandatory             | The Endpoint URL of your Security Validation instance without `http://` or `https://`       |
| API Token                   | Mandatory             | The Security Validation API Token                                                           |
| API Version                 | Mandatory             | The Security Validation API version                                                         |
| Verify SSL Certificate      | Optional              | Specify whether API calls should be validated with certificates or not                      |
| Enable Proxy                | Optional              | Enable or disable proxy settings for connectivity to Mandiant |
| Proxy Type                  | Mandatory             | The proxy type that you want to use (supports HTTP/SOCK4/SOCK5) |
| Proxy Host                  | Mandatory             | Host or IP of the proxy server                                                              |
| Proxy Port                  | Mandatory             | The port that the proxy server accepts connections on |
| Proxy Username              | Optional              | Username for the proxy server                                                                |
| Proxy Password              | Optional              | Password for the proxy server                                                                |

**Create a Mandiant Validation Input**

NOTE: In distributed environments this step should be completed on a Splunk Heavy Forwarder

1. Log in to the Splunk Web UI, open the Mandiant Advantage App and navigate to the **Setup | Inputs** page
2. Select **Create New Input**, select `Mandiant Validation` from the dropdown menu
3. Complete the form and click **Add** to create the input. Field descriptions are described below:

**Mandiant Security Validation Reporting Input**

| Input Parameter            | Mandatory or Optional | Description                                                                                       |
| -------------------------- | --------------------- | ------------------------------------------------------------------------------------------------- |
| Name                       | Mandatory             | A name to uniquely identify the input                                                             |
| Interval                   | Mandatory             | Interval in seconds                                                                               |
| Index                      | Mandatory             | Index in which to store the data                                                                  |
| Mandiant Advantage Account | Mandatory             | The Mandiant Account to be used                                                                   |
| Delay (In Minutes)         | Mandatory             | The amount of time to wait for Security Validation to retrieve correlation and integration events |

**Configure Dashboard Settings**

NOTE: In distributed environments this step should be completed on a Splunk Search Head

1. Navigate to `Dashboard Settings` tab on the **Setup | Configuration** page
2. Enter the name of the indices where the Mandiant Validation Modular Inputs were configured to write events to in the `Validation Indices` setting
3. Click Save

### Enable Digital Threat Monitoring data collection

**Create a Mandiant Advantage account**

This is the same account that is used for Indicator of Compromise data collection.

**Create a Digital Threat Monitoring Alerts Input**

NOTE: In distributed environments this step should be completed on a Splunk Heavy Forwarder

1. Log in to the Splunk Web UI, open the Mandiant Advantage App and navigate to the **Setup | Inputs** page
2. Select **Create New Input**, select `Digital Threat Monitoring Alerts` from the dropdown menu
3. Complete the form and click **Add** to create the input. Field descriptions are described below

**Mandiant Digital Threat Monitoring Alerts Input**

| Input Parameter            | Mandatory or Optional | Description                                                                      |
| -------------------------- | --------------------- | -------------------------------------------------------------------------------- |
| Name                       | Mandatory             | A name to uniquely identify the input.                                           |
| Interval                   | Mandatory             | Interval in seconds                                                              |
| Index                      | Mandatory             | Index in which to store the data                                                 |
| Mandiant Advantage Account | Mandatory             | The Mandiant Account to be used                                                  |
| Lookback Days              | Optional              | The number of days in the past to start the collection of Alerts. Default 7 days |


**Configure Dashboard Settings**

1. Navigate to `Dashboard Settings` tab on the **Setup | Configuration** page
2. Enter the name of the indices where the DTM Alerts Modular Inputs were configured to write events to in the `DTM Alert Indices` setting
3. Click Save

## Release Notes

### Version 1.7.4

* Fixed checkpoint save failure in Mandiant Security Validation input.

### Version 1.7.3

* Fixed an issue with Mandiant Security Validation Input

### Version 1.7.2

* Bumped the minimum required Python version to 3.13 as per Splunk standards.

### Version 1.7.1

* Handled unexpected response in ASM Entity Modular Input.

### Version 1.7.0

* Migrated the App to UCC Framework.

### Version 1.6.1

**Fixes**

* Fixes an issue where the matched events dashboard would not show results in the table view when the matched events were not attributed to a Threat Actor or Malware Family
* The Attack Surface Management Issues Modular Input now ingests events where the issue status changes between syncs but the last seen after date did not

**Improvements**

* Removed validator on ASM Entities Modular Input settings to allow for a query to actually be set
* Improved error handling and logging in ASM Entity Modular Input
* Improved logging and error handling in mandiantmatchedvulns custom command
* Added a new Vuln Host Field setting to the Vulnerability Correlation feature to allow for an event field to be used as the host impacted by the CVE
* Updated the Mandiant Threat Intel Client to version 0.1.18
* Ensure verify ssl is always True for MSV and ASM accounts when running in Splunk Cloud

**New features**

* Added a new setting to optionally include / exclude open source indicators from data ingestion
* Added support for indicator data collection in distributed Splunk environments where the search head does not have access to the internet
* Added new saved search `mandiant_master_lookup` to populate the `mandiant_master_lookup` kv store
* Added new Matched Events Summary dashboard
* Added support for the indicator threat score, severity level and severity reason as returned by the Mandiant API, this is a preview feature

### Version 1.5.1

* Updated Mandiant Intel Client to v0.1.12 to reduce API calls made when collecting indicators and improve modular input performance

### Version 1.5.0

**Fixes**

* Fixes an issue where the ASM Input Config only displays collections from 1 project / organization
* Fixes an issue where Threat Intelligence Indicator data collection would fail if the system clock was ahead of Internet time

**Improvements**

* Added support for associated campaigns and Threat Intelligence reports for ingested indicators
* Reduced dependency on Saved Searches to improve overall system performance

**New features**

* New Mandiant Indicator | Event matching feature with support to tune Notable Alert creation (the Threat Intelligence Correlation feature is now deprecated)
* Added additional context to Notable Alerts created by the app
* New Threat Intelligence Overview dashboard provides more context about the data set
* New Mandiant Matched Events dashboard provides more context to potential threats in the environment

### Version: 1.4.3
* Fixes an issue in the Attack Surface Management Modular Inputs where the second page of results would not be collected

## Troubleshooting

## Uninstall and Cleanup

* Remove $SPLUNK_HOME/etc/apps/TA-mandiant-advantage
* Remove $SPLUNK_HOME/var/log/Splunk/ta_mandiant_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

### Data is not displaying in the Threat Intelligence Overview dashboard

**Step 1: Validate Mandiant Advantage Account Configuration**

1. Open the **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Verify that an account of type **Mandiant Advantage** has been added

**Step 2: Validate Mandiant Threat Intelligence Input Configuration** 

1. Open the **Setup | Inputs** page
2. Verify that a **Mandiant Threat Intelligence** Input has been added

**Step 3: Check logs for more information**

For Splunk on-premises customers:

1. Open a terminal on your Splunk server
2. Search the log file for errors using this command: `cat $SPLUNK_HOME/var/log/splunk/ta_mandiant_advantage_mandiant_advantage_indicators.log | grep -A 10 ERROR`
3. If the `ERROR` log does not help you resolve the issue, please contact Mandiant customer support and provide the complete contents of the `ta_mandiant_advantage_mandiant_advantage_indicators.log` log file.

For Splunk Cloud customers:

Check logs via Splunk search as you do not have access to the terminal of your Splunk instance. Use this query:

`index=_internal source=*ta_mandiant_advantage_mandiant_advantage_indicators.log`

**Step 4: Verify that the `mandiant_master_lookup` saved search is enabled and running successfully**

1. In the Splunk Web UI navigate to **Settings | Searches, reports, and alerts**
2. Verify that the `mandiant_master_lookup` is enabled
3. Click **View Recent** to see what happened the last time the search ran

---

### Not seeing any data in the Threat Intelligence | Matched Events dashboard

**Step 1: Validate the the Splunk CIM app is installed**

1. Open the **Settings | Data models** page in the Splunk Web UI
2. Verify that there are data models listed with app value **Splunk_SA_CIM**

**Step 2: Validate data is displaying in Threat Intelligence Overview dashboard**

See steps above to validate this step.

**Step 3: Validate that Event Matching is enabled**

1. Open the **Indicator | Event Matching** tab on the **Setup | Configuration** page
2. Verify that the **Enable Event Matching** setting is checked
3. Verify that at least 1 data model is selected in the **Data Models To Match** setting

**Step 4: Validate that Splunk Saved Searches are enabled**

1. Open the **Settings | Searches, reports, and alerts** page in the Splunk Web UI
2. Filter the page on **App: Mandiant Advantage App for Splunk** and **Owner: nobody**
3. Verify that the Saved Searches selected in the **Data Models To Match** Mandiant app setting are enabled

**Step 4: Validate that data model queries return results**

1. Open the **Settings | Searches, reports, and alerts** page in the Splunk Web UI
2. Filter the page on **App: Mandiant Advantage App for Splunk** and **Owner: nobody**
3. For one of the enabled saved searches, click **Run**
4. Verify that the search returns results
5. If the search does not return results, trying expanding the time range used for the search
6. If the search still does not return results, verify that there are data sources writing to the Splunk instance that are compatible with the data model you are troubleshooting

**Step 5: Check logs for more information**

For Splunk on-premises customers:

1. Open a terminal on your Splunk server
2. Search the log file for errors using this command: `cat $SPLUNK_HOME/var/log/splunk/ta_mandiant_advantage_command_mandiant_match_events.log | grep -A 10 ERROR`
3. If the `ERROR` log does not help you resolve the issue, please contact Mandiant customer support and provide the complete contents of the `ta_mandiant_advantage_command_mandiant_match_events.log` log file.

For Splunk Cloud customers:

Check logs via Splunk search as you do not have access to the terminal of your Splunk instance. Use this query:

`index=_internal source=*ta_mandiant_advantage_command_mandiant_match_events.log`

---

### Data is not displaying in the Security Validation dashboards

**Step 1: Validate Mandiant Validation Account Configuration**

1. Open the **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Verify that an account of type **Mandiant Validation** has been added

**Step 2: Validate Mandiant Security Validation Input Configuration** 

1. Open the **Setup | Inputs** page
2. Verify that a **Mandiant Security Validation** Input has been added

**Step 3: Validate Validation Job Indices**

1. Open the **Dashboard Settings** tab on the **Setup | Configuration** page
2. Verify that the correct Index / Indices have been entered in the **Validation Jobs Indices** setting

**Step 4: Check logs for more information**

For Splunk on-premises customers:

1. Open a terminal on your Splunk server
2. Search the log file for errors using this command: `cat $SPLUNK_HOME/var/log/splunk/ta_mandiant_advantage_mandiant_security_validation_reporting.log | grep -A 10 ERROR`
3. If the `ERROR` log does not help you resolve the issue, please contact Mandiant customer support and provide the complete contents of the `ta_mandiant_advantage_mandiant_security_validation_reporting.log` log file.

For Splunk Cloud customers:

Check logs via Splunk search as you do not have access to the terminal of your Splunk instance. Use this query:

`index=_internal source=*ta_mandiant_advantage_mandiant_security_validation_reporting.log`

---

### Data is not displaying in the Attack Surface Management | ASM Issues dashboard

**Step 1: Validate Mandiant Attack Surface Management Account Configuration**

1. Open the **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Verify that an account of type **Attack Surface Management** has been added

**Step 2: Validate Mandiant Attack Surface Management Issues Input Configuration** 

1. Open the **Setup | Inputs** page
2. Verify that an **Attack Surface Management Issues** Input has been added

**Step 3: Validate ASM Issues Indices**

1. Open the **Dashboard Settings** tab on the **Setup | Configuration** page
2. Verify that the correct Index / Indices have been entered in the **ASM Issues Indices** setting

**Step 4: Check logs for more information**

For Splunk on-premises customers:

1. Open a terminal on your Splunk server
2. Search the log file for errors using this command: `cat $SPLUNK_HOME/var/log/splunk/ta_mandiant_advantage_TA_mandiant_advantage_rh_mandiant_advantage_asm_issues.log | grep -A 10 ERROR`
3. If the `ERROR` log does not help you resolve the issue, please contact Mandiant customer support and provide the complete contents of the `ta_mandiant_advantage_TA_mandiant_advantage_rh_mandiant_advantage_asm_issues.log` log file.

For Splunk Cloud customers:

Check logs via Splunk search as you do not have access to the terminal of your Splunk instance. Use this query:

`index=_internal source=*ta_mandiant_advantage_TA_mandiant_advantage_rh_mandiant_advantage_asm_issues.log`

---

### Data is not displaying in the Attack Surface Management | ASM Entities dashboard

**Step 1: Validate Mandiant Attack Surface Management Account Configuration**

1. Open the **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Verify that an account of type **Attack Surface Management** has been added

**Step 2: Validate Mandiant Attack Surface Management Entities Input Configuration** 

1. Open the **Setup | Inputs** page
2. Verify that an **Attack Surface Management Entities** Input has been added

**Step 3: Validate ASM Entities Indices**

1. Open the **Dashboard Settings** tab on the **Setup | Configuration** page
2. Verify that the correct Index / Indices have been entered in the **ASM Entities Indices** setting

**Step 4: Check logs for more information**

For Splunk on-premises customers:

1. Open a terminal on your Splunk server
2. Search the log file for errors using this command: `cat $SPLUNK_HOME/var/log/splunk/ta_mandiant_advantage_TA_mandiant_advantage_rh_mandiant_advantage_asm_entities.log | grep -A 10 ERROR`
3. If the `ERROR` log does not help you resolve the issue, please contact Mandiant customer support and provide the complete contents of the `ta_mandiant_advantage_TA_mandiant_advantage_rh_mandiant_advantage_asm_entities.log` log file.

For Splunk Cloud customers:

Check logs via Splunk search as you do not have access to the terminal of your Splunk instance. Use this query:

`index=_internal source=*ta_mandiant_advantage_TA_mandiant_advantage_rh_mandiant_advantage_asm_entities.log`

---

### Data is not displaying in the DTM Alerts dashboard

**Step 1: Validate Mandiant Advantage Account Configuration**

1. Open the **Mandiant Advantage Configuration** tab on the **Setup | Configuration** page
2. Verify that an account of type **Mandiant Advantage** has been added

**Step 2: Validate Mandiant Digital Threat Monitoring Alerts Input Configuration** 

1. Open the **Setup | Inputs** page
2. Verify that an **Mandiant Digital Threat Monitoring Alerts** Input has been added

**Step 3: Validate DTM Alerts Indices**

1. Open the **Dashboard Settings** tab on the **Setup | Configuration** page
2. Verify that the correct Index / Indices have been entered in the **DTM Alerts Indices** setting

**Step 4: Check logs for more information**

For Splunk on-premises customers:

1. Open a terminal on your Splunk server
2. Search the log file for errors using this command: `cat $SPLUNK_HOME/var/log/splunk/ta_mandiant_advantage_mandiant_advantage_monitoring_alerts.log | grep -A 10 ERROR`
3. If the `ERROR` log does not help you resolve the issue, please contact Mandiant customer support and provide the complete contents of the `ta_mandiant_advantage_mandiant_advantage_monitoring_alerts.log` log file.

For Splunk Cloud customers:

Check logs via Splunk search as you do not have access to the terminal of your Splunk instance. Use this query:

`index=_internal source=*ta_mandiant_advantage_mandiant_advantage_monitoring_alerts.log`

---

## Reference

### Saved Searches

This application contains the following saved searches:

> All saved searches are disabled by default and enabled via the app's Settings options

**mandiant_master_lookup** - Populate the mandiant_master_lookup KV Store with Mandiant indicators

**mandiant_match_vulnerabilities** - Match Vulnerabilities from the selected indices and sourcetypes

**mandiant_retire_vulnerabilities** - Delete mandiant vulnerabilities that are older than configured days.

**mandiant_match_events_authentication** - Queries the Authentication CIM Data Model and uses the `mandiantmatchevents` command to correlate the `src` or `dest` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store. 

**mandiant_match_events_endpoint_process** - Queries the Endpoint Services CIM Data Model and uses the `mandiantmatchevents` command to correlate the `file_hash` or `dest` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store. 

**mandiant_match_events_endpoint_filesystem** - Queries the Endpoint Filesystem CIM Data Model and uses the `mandiantmatchevents` command to correlate the `file_hash` or `dest` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store. 

**mandiant_match_events_intrusion_detection** - Queries the Intrusion Detection CIM Data Model and uses the `mandiantmatchevents` command to correlate the `file_hash`, `src` or `dest` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store.

**mandiant_match_events_malware_attacks** - Queries the Malware Attacks CIM Data Model and uses the `mandiantmatchevents` command to correlate the `file_hash`, `src`, `dest` or `url` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store.

**mandiant_match_events_network_resolution** - Queries the Network Resolution CIM Data Model and uses the `mandiantmatchevents` command to correlate the `src`, `dest`, or `domain` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store.

**mandiant_match_events_network_traffic** - Queries the Network Traffic CIM Data Model and uses the `mandiantmatchevents` command to correlate the `src_ip`, `dest_ip`, `src` or `dest` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store.

**mandiant_match_events_web** - Queries the Web CIM Data Model and uses the `mandiantmatchevents` command to correlate the `src`, `dest`, `url` or `domain` fields with Mandiant indicators in the `mandiant_master_lookup`. Results of matched events are added to the `mandiant_matched_events` KV Store.

**mandiant_create_notables** - Queries the `mandiant_matched_events` KV Store for events and uses the `mandiantnotables` command to create a Splunk Notable Alert for each result found

### Lookups

The app creates the following Splunk KV Store Lookup Tables:

**mandiant_master_lookup**: populated by the Mandiant Threat Intelligence Modular Input and contains Mandiant indicator data. The indicator value is used as the primary key for the lookup.

Example queries:

Get all indicators:

`| inputlookup mandiant_master_lookup | eval indicator_value=_key`

Use the lookup:

`<base search> | lookup mandiant_master_lookup _key AS <field>`

Where:

* `<base_search>` is your Splunk search
* `<field>` is the field you want to match to an indicator value

**mandiant_matched_events**: contains data about events that were matched against Mandiant indicators as a result of the Indicator | Event Matching feature

Example query:

`| inputlookup mandiant_matched_events`

**mandiant_vuln_matched_lookup**: contains the matched vulnerabilities data

Example query: 

`| inputlookup mandiant_vuln_matched_lookup`

### Search

* To see ingested data for Mandiant Threat Intelligence, select the `Search` tab. Search `` `mandiant_indicator_indices` sourcetype="mandiant:advantage:indicators"``.
* To see ingested data for Security Validation, select the `Search` tab. Search `` `mandiant_validation_indices` sourcetype="mandiant:advantage:reporting_data"``.
* To see ingested data for Digital Threat Monitoring, select the `Search` tab. Search `` `mandiant_dtm_alert_indices` sourcetype="mandiant:advantage:dtm:alerts"``.
* To see ingested data for Attack Surface Management Issues, select the `Search` tab. Search `` `mandiant_asm_issues_indices` sourcetype="mandiant:advantage:asm:issues"``.
* To see ingested data for Attack Surface Management Entities, select the `Search` tab. Search `` `mandiant_asm_entities_indices` sourcetype="mandiant:advantage:asm:entities"``.

### Open Source Components and Licenses

Some of the components included in "Mandiant Advantage App For Splunk" are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* dateutil version 2.8.2 https://pypi.org/project/python-dateutil (LICENSE https://github.com/dateutil/dateutil/blob/master/LICENSE)
* pytz version 2022.7.1 https://pypi.org/project/pytz/ (LICENSE MIT License (MIT))
* tenacity version 8.2.2 https://pypi.org/project/tenacity/ (LICENSE Apache Software License (Apache 2.0))


## Support
* Email: customersupport@mandiant.com

**Copyright (c) 2026 Mandiant. All rights reserved.**

# Binary File Declaration
/usr/local/google/home/adamhlevy/splunk/splunk/var/data/tabuilder/package/TA-mandiant-advantage/bin/ta_mandiant_advantage/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
