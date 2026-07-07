# Cyware Intel Exchange

## OVERVIEW
* The Cyware Intel Exchange pulls Indicators from the Cyware Threat Intelligence eXchange platform. The integration does correlation and provides dashboards for visualization.


## REQUIREMENTS

* Splunk Common Information Model (CIM datamodels) (To match the indicators with the datamodel events)(https://splunkbase.splunk.com/app/1621).
* Enterprise Security (To generate and see the notable events of correlated data)(https://splunkbase.splunk.com/app/263).


## COMPATIBILITY MATRIX
* Splunk version: 10.2.x, 10.0.x, 9.4.x, 9.3.x
* Python version: Python3.7+
* OS Support: Independent
* Browser Support: Independent


## RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## RELEASE NOTES

### Version 4.0.2

* Updated Indicator Overview dashboard time-based panels and timeline charts to use `splunk_ingest_time`.
* Added `cyware_index` macro to centrally manage the indices used by the Add-on.
* Adding SSL configuration support from conf file.

### Version 4.0.0

* Added multi-account support for managing multiple Cyware instances.
* Implemented KV Store-based data collection as mandatory; index ingestion is now optional.
* Added field-based correlation feature to find sightings in Splunk events.
* Added lookback days parameter in Input configuration.
* Added fetching of enriched data for indicators.
* Added workflow actions for creating new indicators, updating indicator status, managing allowlists, tags,tasks and notes for indicators to the Cyware platform.
* Added bulk indicator ingestion from Splunk indexes, data models, and lookups with automation support.
* Added automatic deletion of expired indicators from KVStore lookups.
* Added Indicator Overview and Correlation Overview dashboards.
* Added automated data migration (index to KV Store) for existing data.
* Added new alert actions for Splunk Enterprise Security (adaptive response).
* Improved error handling, proxy configuration, and data collection reliability.

## INSTALLATION
Cyware Intel Exchange can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `Cyware Intel Exchange` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## UPGRADE
### General upgrade steps:

1. Log in to Splunk Web and navigate to Cyware Intel Exchange > Inputs.
2. Here disable all configured Inputs.
3. Navigate to Apps -> Manage Apps on Splunk menu bar.
4. Click Install app from file.
5. Click Choose file and select the `Cyware Intel Exchange` installation file.
6. Check the Upgrade checkbox.
7. Click on Upload.
8. Restart Splunk.

### Upgrade to v4.0.0

> **IMPORTANT**: In-place upgrade from versions prior to 4.0.0 is **not supported** due to significant architectural changes. A fresh install is required.

1. **Uninstall the Previous Version**
   - Remove the existing Cyware add-on from your Splunk instance.

2. **Perform a Fresh Install**
   - Follow the steps in the [Installation](#installation) section to install v4.0.0.
   - Configure your account, inputs, and correlation settings from scratch.

3. **Automatic Data Migration**
   - If you have indicator data ingested into Splunk indexes by the older version, the add-on includes a built-in saved search (`cyware_index_to_kvstore_migration`) that **runs automatically** every 10 minutes.
   - This search migrates indicator data from your indexes into the new indicator-type-wise KVStore lookups (e.g., `cyware_ti_ipv4_addr`, `cyware_ti_domain_name`, etc.).
   - The saved search **automatically disables itself** after successful migration. No manual intervention is required.
   - **Note**: Do not modify or manually execute this saved search.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-on can be set up in two ways:

1. Standalone Mode
    * Install the Cyware Intel Exchange.
    * Follow all the steps mentioned in `Configuration` section to configure the Add-on.
2. Distributed Environment
    * Install the Cyware Intel Exchange on the Search Head and Heavy Forwarder.
    * Follow the steps #1, #2 , #3 and #4 from `Configuration` section on Heavy Forwarder.
    * Follow the step #5 from `Configuration` section on Search Head.
    * In case of Search Head Clustering, make sure that steps #4 and #5 from `Configuration` are configured only on single search head. In such cases, the configuration will not be visible on other search heads. This is recommended approach.
    * Follow the step #5 from `Configuration` section on Search Head. Following these steps will replicate the configuration on all search heads.
3. Cloud Environment
    * Install the Cyware Intel Exchange on Search Head.
    * Install the Cyware Intel Exchange on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the Cyware Intel Exchange on the On-Premise Heavy Forwarder.

## CONFIGURATION
Configure Cyware Intel Exchange

### App Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.
3. Configure the settings related to Splunk KVStore and Correlation in `Splunk KVStore Rest` and `Correlation Settings` section respectively. 
4. After the configuration of `Splunk KVStore Rest` and `Correlation Settings`, users can configure the inputs by specifying the required parameters.
5. Configure the settings related to correlation searches in `Correlation Settings` section.


### Account
To configure the Account,

1. Navigate to the `Configuration`.
2. Provide your Cyware Intel Exchange API credentials and Account Name and click on `Add`.

| Account parameters            | Mandatory or Optional | Description                                 |
| ----------------------------  | --------------------- | ------------------------------------------- |
| Name                          | Mandatory        | Enter a unique name for this account. |
| Base URL                      | Mandatory        | Base URL of the Cyware Intel Exchange. (Only Secure, HTTPS Based, connections are allowed. Example: https://test.com/ctixapi/) |
| Access ID                     | Mandatory        | Access ID used to integrate with Cyware Threat Intel Platform. |
| Secret Key                    | Mandatory        | Secret Key used to integrate with Cyware Threat Intel Platform. |

### Proxy
To configure the Proxy,

1. Navigate to the `Configuration`.
2. Click on the `Proxy` tab. 
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy     |
|    Proxy Type            |     Optional            |  Type of the Proxy. Available options are http, socks4 and socks5. Default is http.|
|    Host            |     Optional            |  Host or IP of the proxy server                                                        |
|    Port            |     Optional            |  Port for proxy server                                                                 |
|  Username          |     Optional             |  Username of the proxy server |
|  Password          |     Optional             |  Password of the proxy server |
|  Remote DNS resolution |  Optional             |  Enable remote DNS resolution for the proxy |

### Logging
To configure the Logging,

1. Navigate to the `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`. By default the log level is set to 'INFO'.

| Logging Parameters       | Mandatory or Optional | Description                                                  |
|------------------------|----------|-----------------------------------------------------------------------------|
| Log level   | Mandatory   | Select the log level. Available options are DEBUG, INFO, WARNING, ERROR, CRITICAL. Default is INFO. |
| Enable Debug Log Ingestion | Optional | Add request details and response received to the Index along with updating the lookup table. If 'Ingest to Index' is disabled, debug logs will be ingested in the 'Default' index. |

### Splunk KVStore Rest
To configure the Splunk KVStore,

1. Navigate to the `Configuration`.
2. Click on the `Splunk KVStore Rest` tab.
3. Provide the required values and click on Save.

| KVStore Parameters       | Mandatory or Optional | Description                                                  |
|------------------------|----------|-----------------------------------------------------------------------------|
| Splunk Username | Optional | Enter the username for Splunk instance. Not required if Splunk Rest Host URL is localhost or 127.0.0.1. Configured user should have at least power role capabilities. |
| Splunk Password | Optional | Enter the password for Splunk account. Not required if Splunk Rest Host URL is localhost or 127.0.0.1. |
| Splunk Rest Host URL | Optional | Enter the Splunk rest host or localhost (without http(s) scheme) to collect data. (Default: localhost) |
| Port | Optional | Enter the management port of the Splunk. (Default: 8089) |

> **NOTE** : If using Cluster environment then make sure that all fields are configured and splunkd port 8089 of Splunk Management is open for storing lookups.

### Correlation Settings
To configure the Correlation Settings,

1. Navigate to the `Configuration`.
2. Click on the `Correlation Settings` tab.
3. Provide the required values and click on Save.

| Correlation Parameters       | Mandatory or Optional | Description                                                  |
|------------------------|----------|-----------------------------------------------------------------------------|
| Enabled Indicator Types | Optional      | Select the indicator types you want to enable correlation for. Available options are Autonomous System, Domain, Email, File, IPv4, IPv6, Network Traffic, URL, and Windows Registry Key. |
| Search Matching Algorithm       | Optional       | Select the method for correlating indicators. Available options are Raw Search and Datamodel Search. |
| Select Datamodels  | Optional      | Select the data models from the list. Available options are Network Traffic, Malware, Intrusion Detection, Authentication, Certificates, Endpoint, Email, Inventory, Network Resolution (DNS), Updates, and Web. |
| Autonomous System: Target Query | Optional | Splunk query to get events for correlation with Autonomous System Indicators. |
| Autonomous System: Target Fields | Optional | Comma separated list of fields to be used in correlation. |
| Domain Name: Target Query | Optional | Splunk query to get events for correlation with Domain Name Indicators. |
| Domain Name: Target Fields | Optional | Comma separated list of fields to be used in correlation. |
| Email: Target Query | Optional | Splunk query to get events for correlation with Email Indicators. |
| Email: Target Fields | Optional | Comma separated list of fields to be used in correlation. |
| File: Target Query | Optional | Splunk query to get events for correlation with File Indicators. |
| File: Target Fields | Optional | Comma separated list of fields to be used in correlation. |
| IPv4: Target Query    | Optional       | Splunk query to get events for correlation with IPv4 Indicators. |
| IPv4: Target Fields  | Optional      | Comma separated list of fields to be used in correlation. |
| IPv6: Target Query    | Optional       | Splunk query to get events for correlation with IPv6 Indicators. |
| IPv6: Target Fields  | Optional      | Comma separated list of fields to be used in correlation. |
| Network Traffic: Target Query | Optional | Splunk query to get events for correlation with Network Traffic Indicators. |
| Network Traffic: Target Fields | Optional | Comma separated list of fields to be used in correlation. |
| URL: Target Query | Optional | Splunk query to get events for correlation with URL Indicators. |
| URL: Target Fields | Optional | Comma separated list of fields to be used in correlation. |
| Windows Registry Key: Target Query | Optional | Splunk query to get events for correlation with Windows Registry Key Indicators. |
| Windows Registry Key: Target Fields | Optional | Comma separated list of fields to be used in correlation. |


### Inputs
To configure the Inputs,

1. Navigate to the `Inputs`.
2. Click on `Create New Input`.
3. Provide the required information related to input and click on `Add` to configure the input.

| Input Parameter |  Mandatory or Optional | Description                                                  |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | A name to uniquely identify the input.                        |
| Interval        | Mandatory              | Time interval of input in minutes. Must be greater than 5 minutes. |
| Account         | Mandatory              | Select the account from where data will be fetched.             |
| Ingest to Index | Optional               | Select the checkbox to enable the data collection in index. |
| Index           | Optional               | Select the index in which data should be collected. Only required if "Ingest to Index" is enabled. |
| Lookback Days   | Optional               | Specify the number of past days to collect indicators from Cyware. This setting is only used during the initial data fetch (default: 30 days). |
| Saved Result Set Tag | Mandatory         | Provide comma separated tags added to "Saved Result Set" Rule Action in Cyware Threat Intel. |
| Fetch Enriched Data  | Optional          | Select the checkbox to enable the fetching of enriched data. |

### Dashboards

1. Indicator Overview:
    * This dashboard provides an overview of the indicator data in your Splunk instance.
    * Indicator Overview Dashboard Panels:
        1. Total Indicators
        2. Total Matched Indicators Count
        3. Indicators: Last 24 hours
        4. Indicators: Last 7 days
        5. Indicators: Last 30 days
        6. Allowed Indicators Count
        7. Deprecated Indicators Count
        8. False Positive Indicators Count
        9. Revoked Indicators Count
        10. Marked for Review Indicators Count
        11. Actioned Indicators Count
        12. Timeline Distribution of Indicators
        13. Top 10 Indicators Distribution by Source
        14. Source based Timeline Chart
        15. IOC Type based Timeline Chart
        16. Indicators Distribution by IOC Type
        17. Indicators Distribution by Risk Score
        18. Indicators Distribution by Top 10 Tags
        19. Indicators Count by Geo Location (Country)
        20. Indicators with Relations
        21. Indicators with Threat Actors
        22. Top 10 Indicators Distribution by Threat Actors
        23. Indicators by Threat Actors
        24. Indicators with Attack Patterns
        25. Top 10 Indicators Distribution by Attack Patterns
        26. Indicators by Attack Patterns
        27. Indicators with Malware
        28. Top 10 Indicators Distribution by Malware
        29. Indicators by Malware
        30. Indicators with Campaigns
        31. Top 10 Indicators Distribution by Campaigns
        32. Indicators by Campaigns
        33. Indicators with Tools
        34. Top 10 Indicators Distribution by Tools
        35. Indicators by Tools
        36. Indicators with Custom Attributes
        37. Top 10 Indicators with Custom Attributes by IOC Types
        38. List of Indicators with Custom Attributes
        39. Indicators with Enrichment Data
        40. Top 10 Indicators with Enrichment Data by IOC Type
        41. List of Indicators with Enrichment Data
        42. Indicators with Vulnerabilities
        43. Top 10 Indicators Distribution by Vulnerabilities
        44. Indicators by Vulnerability Reports

2. Correlation Overview:
    * This dashboard provides visualization of matched indicators of Cyware Intel Exchange Indicators data with Splunk events.
    * Correlation Overview Dashboard Panels:
        1. Total Matched Indicators
        2. Matched Indicators: Last 24 hours
        3. Matched Indicators: Last 7 days
        4. Matched Indicators: Last 30 days
        5. Allowed Matched Indicators Count
        6. Deprecated Matched Indicators Count
        7. False Positive Matched Indicators Count
        8. Revoked Matched Indicators Count
        9. Marked for Review Matched Indicators Count
        10. Actioned Matched Indicators Count
        11. Timeline Distribution of Matched Indicators
        12. Top 10 Matched Indicators Distribution by Source
        13. Matched Indicators Distribution by IOC Type
        14. Matched Indicators Distribution by Risk Score
        15. Matched Indicators Count by Geo Location (Country)
        16. Matched Indicators Distribution by Top 10 Tags
        17. Matched Indicators with Threat Actors
        18. Top 10 Matched Indicators Distribution by Threat Actors
        19. Matched Indicators by Threat Actors
        20. Matched Indicators with Malware
        21. Top 10 Matched Indicators Distribution by Malware
        22. Matched Indicators by Malware
        23. Matched Indicators with Vulnerabilities
        24. Top 10 Matched Indicators Distribution by Vulnerabilities
        25. Matched Indicators by Vulnerability Reports
        26. Matched Indicators with Attack Patterns
        27. Top 10 Matched Indicators Distribution by Attack Patterns
        28. Matched Indicators by Attack Patterns
        29. Matched Indicators with Campaigns
        30. Top 10 Matched Indicators Distribution by Campaigns
        31. Matched Indicators by Campaigns

3. Add New Indicator:
    * This dashboard allows adding a single indicator to Intel Exchange with custom metadata and classification.

4. Add Indicator to Allowlist:
    * This dashboard allows adding indicators to the Intel Exchange allowlist to prevent them from being flagged.

5. Get/Update Allowed Indicators:
    *  This dashboard is used to view and remove indicators from the Intel Exchange allowlist.

6. Add Indicators in Bulk from Data Source:
    * This dashboard allows ingesting multiple indicators from Splunk indexes, data models, or lookup files and creating and managing automation.

7. Add/Remove Tags from Indicator:
    * This dashboard allows managing tags for Cyware Intel Exchange indicators.

8. Add Note in Intel Exchange:
    * This dashboard allows adding notes to Cyware Intel Exchange indicators.

9. Update Indicator Status:
    * This dashboard allows updating the status of Intel Exchange indicators.

10. Create Task in Intel Exchange:
    * This dashboard allows creating tasks for Cyware Intel Exchange indicators for collaboration and tracking.

## LOOKUPS
* `cyware_ti_file`: This lookup contains enrichment data for file indicators.
* `cyware_ti_url`: This lookup contains enrichment data for URL indicators.
* `cyware_ti_domain_name`: This lookup contains enrichment data for domain indicators.
* `cyware_ti_ipv4_addr`: This lookup contains enrichment data for IPv4 indicators.
* `cyware_ti_ipv6_addr`: This lookup contains enrichment data for IPv6 indicators.
* `cyware_ti_windows_registry_key`: This lookup contains enrichment data for Windows registry key indicators.
* `cyware_ti_email_addr`: This lookup contains enrichment data for email address indicators.
* `cyware_ti_autonomous_system`: This lookup contains enrichment data for autonomous system indicators.
* `cyware_ti_network_traffic`: This lookup contains enrichment data for network traffic indicators.
* `cyware_matched_indicators_file`: This lookup contains the matched indicator data for file indicators.
* `cyware_matched_indicators_url`: This lookup contains the matched indicator data for URL indicators.
* `cyware_matched_indicators_domain_name`: This lookup contains the matched indicator data for domain indicators.
* `cyware_matched_indicators_ipv4_addr`: This lookup contains the matched indicator data for IPv4 indicators.
* `cyware_matched_indicators_ipv6_addr`: This lookup contains the matched indicator data for IPv6 indicators.
* `cyware_matched_indicators_windows_registry_key`: This lookup contains the matched indicator data for Windows registry key indicators.
* `cyware_matched_indicators_email_addr`: This lookup contains the matched indicator data for email indicators.
* `cyware_matched_indicators_autonomous_system`: This lookup contains the matched indicator data for AS indicators.
* `cyware_matched_indicators_network_traffic`: This lookup contains the matched indicator data for network traffic indicators.
* `ctix_bulk_indicator_sources`: This lookup manages bulk data source configurations.

User can check data in lookup by running following SPL query in Splunk search: `| inputlookup <NAME OF LOOKUP>`

## MACROS
This application contains the following search macros (defined in `macros.conf`). Update them as needed to match your environment.

* **cyware_index**
    * Description: Definition for the indices used by the Add-on. Update this macro to restrict searches to the specific indices where Cyware data is stored (e.g., `index IN (my_cyware_index)`).
    * Default Definition: `index IN (*)`

## SAVEDSEARCHES
This application contains the following saved searches:

**Correlation - Raw Search:**
* **cyware_correlate_file_indicators** - Match Indicators of type File from the master lookup against Splunk events using raw search.
* **cyware_correlate_ipv4_addr_indicators** - Match Indicators of type IPv4 from the master lookup against Splunk events using raw search.
* **cyware_correlate_ipv6_addr_indicators** - Match Indicators of type IPv6 from the master lookup against Splunk events using raw search.
* **cyware_correlate_url_indicators** - Match Indicators of type URL from the master lookup against Splunk events using raw search.
* **cyware_correlate_domain_name_indicators** - Match Indicators of type Domain from the master lookup against Splunk events using raw search.
* **cyware_correlate_windows_registry_key_indicators** - Match Indicators of type Windows Registry Key from the master lookup against Splunk events using raw search.
* **cyware_correlate_email_addr_indicators** - Match Indicators of type Email from the master lookup against Splunk events using raw search.
* **cyware_correlate_autonomous_system_indicators** - Match Indicators of type Autonomous System from the master lookup against Splunk events using raw search.
* **cyware_correlate_network_traffic_indicators** - Match Indicators of type Network Traffic from the master lookup against Splunk events using raw search.

**Correlation - Datamodel Search:**

For each indicator type (file, ipv4_addr, ipv6_addr, url, domain_name, windows_registry_key, email_addr, autonomous_system, network_traffic), the following datamodel-based saved searches are available:
* **cyware_correlate_\<indicator_type\>_indicators_network_traffic** - Match indicators against Network_Traffic events.
* **cyware_correlate_\<indicator_type\>_indicators_malware** - Match indicators against Malware events.
* **cyware_correlate_\<indicator_type\>_indicators_intrusion_detection** - Match indicators against Intrusion_Detection events.
* **cyware_correlate_\<indicator_type\>_indicators_authentication** - Match indicators against Authentication events.
* **cyware_correlate_\<indicator_type\>_indicators_certificates** - Match indicators against Certificates events.
* **cyware_correlate_\<indicator_type\>_indicators_email** - Match indicators against Email events.
* **cyware_correlate_\<indicator_type\>_indicators_compute_inventory** - Match indicators against Compute_Inventory events.
* **cyware_correlate_\<indicator_type\>_indicators_network_resolution** - Match indicators against Network_Resolution events.
* **cyware_correlate_\<indicator_type\>_indicators_updates** - Match indicators against Updates events.
* **cyware_correlate_\<indicator_type\>_indicators_web** - Match indicators against Web events.
* **cyware_correlate_\<indicator_type\>_indicators_endpoint_filesystem** - Match indicators against Endpoint (Filesystem dataset) events.
* **cyware_correlate_\<indicator_type\>_indicators_endpoint_services** - Match indicators against Endpoint (Services dataset) events.
* **cyware_correlate_\<indicator_type\>_indicators_endpoint_processes** - Match indicators against Endpoint (Processes dataset) events.

**Other Saved Searches:**
* **Threat - CTIX - Generating hourly indicator matches by IP - Rule** - Enterprise Security correlation rule for generating notable events from IP indicator matches.
* **CTIX - Bulk Indicator Ingestion Engine** - Scheduled search engine for bulk indicator ingestion.
* **Delete Expired Indicators from All Lookups** - Delete expired indicators from all KVStore lookups.
* **cyware_index_to_kvstore_migration** - Migrate indicator data from indexes to KVStore.

## Custom Commands
This application contains the following custom commands:

* **cywarematchindicators**
    * Description : This command performs the correlation between Cyware Intel Exchange indicators and provided Splunk events.
    * Parameters :
        * indicator_type (required) : The type of indicator to be matched.

* **ctixaddindicator**
    * Description : This command adds a new indicator to Cyware Intel Exchange platform.
    * Parameters :
        * indicator_type : Type of indicator (default: ipv4-addr).
        * value : Indicator value to add.
        * title : Title for the indicator (default: "Added from Splunk").
        * description : Description of the indicator.
        * confidence : Confidence level of the indicator (default: 100).
        * tlp : TLP marking (default: AMBER).
        * tags : Comma separated tags.
        * valid_until : Deprecation period in days.
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixupdateindicatorstatus**
    * Description : This command updates the status of indicators in Cyware platform.
    * Parameters :
        * status_type : Status type to update (default: is_reviewed).
        * value : Indicator ID.
        * splunk_account : Configured Cyware Intel Exchange Account Name.
        * undeprecate_until : Undeprecate until period in days.

* **ctixgetallowlist**
    * Description : This command retrieves allowlist indicators from Cyware platform.
    * Parameters :
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixupdateallowlist**
    * Description : This command adds or removes indicators from the Cyware allowlist.
    * Parameters :
        * indicator_value : Indicator value.
        * indicator_type : Type of indicator.
        * reason : Reason for adding to allowlist.
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixmanagetags**
    * Description : This command manages tags for Cyware indicators.
    * Parameters :
        * ctix_id : Cyware indicator ID.
        * action : Action to perform (default: add_tags).
        * tag_ids : Comma separated tag IDs.
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixgettags**
    * Description : This command retrieves all tags from Cyware platform.
    * Parameters :
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixgetusers**
    * Description : This command retrieves all users from Cyware platform for task assignment.
    * Parameters :
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixgetindicatortags**
    * Description : This command retrieves tags for a specific Cyware indicator.
    * Parameters :
        * ctix_id : Cyware indicator ID.
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixaddnote**
    * Description : This command adds notes to Cyware platform indicators.
    * Parameters :
        * ctix_id : Cyware indicator ID.
        * note_content : Content of the note.
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixaddtask**
    * Description : This command creates tasks for Cyware Intel Exchange indicators.
    * Parameters :
        * object_id (required) : Cyware indicator ID (UUID).
        * text (required) : Task description/text.
        * priority : Task priority (default: medium). Options: low, medium, high.
        * status : Task status (default: not_started). Options: not_started, in_progress, completed.
        * type : Type of task (default: indicator). Options: indicator, threatdata.
        * deadline : Task deadline in days (default: 10).
        * assignee : User ID to assign task to.
        * splunk_account (required) : Configured Cyware Intel Exchange Account Name.

* **ctixaddbulkindicators**
    * Description : This command adds bulk indicators to Cyware platform from Splunk data sources.
    * Parameters :
        * source_type : Source type (index, cim, custom_datamodel, lookup). Default: index.
        * index_name : Index name for source type "index".
        * sourcetype : Sourcetype filter.
        * cim_datamodel_name : CIM data model name.
        * cim_field_name : CIM field name.
        * datamodel_name : Custom datamodel name.
        * lookup_name : Lookup name for source type "lookup".
        * field_name : Field containing indicator values.
        * field_name_custom_datamodel : Field name for custom datamodel.
        * source_name : Source name metadata (default: Splunk).
        * description : Description of the bulk source.
        * tlp : TLP marking (default: AMBER).
        * confidence_score : Confidence score (default: 100).
        * tags : Comma separated tags.
        * splunk_account (required) : Configured Cyware Intel Exchange Account Name.
        * collection_name : Collection name (default: Splunk Collection).
        * enable_automation : Enable automation.
        * automation_source_name : Automation source name.

* **ctixmanagebulksources**
    * Description : This command manages bulk indicator sources in KV Store.
    * Parameters :
        * action (required) : Action to perform (list, add, update, delete).
        * key : Key of the bulk source record.
        * source_name : Name of the bulk source.
        * source_type : Type of the bulk source.
        * index_name : Index name.
        * sourcetype : Sourcetype.
        * cim_datamodel_name : CIM data model name.
        * cim_field_name : CIM field name.
        * datamodel_name : Datamodel name.
        * lookup_name : Lookup name.
        * field_name : Field name.
        * source_name_metadata : Source name metadata (default: Splunk).
        * tlp : TLP marking (default: AMBER).
        * confidence : Confidence score (default: 100).
        * tags : Comma separated tags.
        * description : Description.
        * collection_name : Collection name.
        * splunk_account : Configured Cyware Intel Exchange Account Name.

* **ctixbulkingestionengine**
    * Description : Scheduled search engine for Cyware bulk indicator ingestion.

* **cywareindextokvstoremigration**
    * Description : This command migrates indicator data from indexes to KV Store.
    * Parameters :
        * saved_search_name : Name of the saved search to disable after successful migration.

* **cywaredeleteindicators**
    * Description : This command deletes expired indicators from all KVStore lookups.

## ALERT ACTIONS
This application provides the following adaptive response actions for use with Splunk Enterprise Security (ES). They support both ad-hoc execution and cloud deployments.

> **NOTE**: These alert actions require Splunk Enterprise Security to be installed for full functionality. A configured Cyware account is required for all actions.

* **Cyware: Add New Indicator**
    * Description: Add an indicator to Cyware with custom metadata and classification.
    * Parameters:
        * Title - Title for the indicator (default: "Added from Splunk ES").
        * Indicator Type (required) - Type of indicator (e.g., ipv4-addr, domain, file, url, email, sha256, etc.).
        * Indicator Value (required) - The indicator value to add.
        * Confidence - Confidence level (default: 100).
        * TLP - Traffic Light Protocol marking. Options: CLEAR, GREEN, AMBER, AMBER+STRICT, RED (default: AMBER).
        * Tags (comma separated) - Tags to associate with the indicator.
        * Deprecates after (in days) - Auto-deprecation period (default: 180).
        * Cyware Account (required) - Select the configured Cyware account.

* **Cyware: Update Indicator Status**
    * Description: Update the status of Cyware indicators.
    * Parameters:
        * Cyware Indicator ID (required) - The Cyware indicator ID to update.
        * Indicator Status (required) - Status to set. Options: Deprecate, Undeprecate, Mark False Positive, Unmark False Positive, Manual Review, Manually Reviewed.
        * Undeprecate until Days - Number of days to undeprecate the indicator. Only applicable when undeprecating.
        * Cyware Account (required) - Select the configured Cyware account.

* **Cyware: Add to Allowlist**
    * Description: Add indicators to the Cyware allowlist to prevent them from being flagged.
    * Parameters:
        * Indicator Value (required) - The indicator value to allowlist.
        * Indicator Type (required) - Type of indicator (e.g., ipv4-addr, domain, file, url, email, sha256, etc.).
        * Reason for Adding to Allowlist - Reason for allowlisting (default: "Added from Splunk").
        * Cyware Account (required) - Select the configured Cyware account.

* **Cyware: Add Note in Intel Exchange in Cyware**
    * Description: Add a note to a Cyware indicator.
    * Parameters:
        * Cyware Indicator ID (required) - The Cyware indicator ID to add the note to.
        * Note Content (required) - Content of the note.
        * Cyware Account (required) - Select the configured Cyware account.

* **Cyware: Create Task in Intel Exchange**
    * Description: Create a task for a Cyware indicator for collaboration and tracking.
    * Parameters:
        * Object ID (Indicator UUID) (required) - The Cyware indicator ID to create the task for.
        * Task Description (required) - Description of the task (max 2000 characters).
        * Priority - Task priority. Options: Low, Medium, High (default: Medium).
        * Status - Initial task status. Options: Not Started, In Progress, Completed (default: Not Started).
        * Deadline (in days) (required) - Task deadline in days (default: 10).
        * Assignee - User to assign the task to (selected from dropdown).
        * Cyware Account (required) - Select the configured Cyware account.

* **Cyware: Get enriched data**
    * Description: Fetch enriched data for a provided indicator value.
    * Parameters:
        * Indicator Value (required) - The indicator value to enrich.
        * Cyware Account (required) - Select the configured Cyware account.

## WORKFLOW ACTIONS
This application provides the following workflow actions accessible from the field action menu in Splunk search results:

* **Cyware Intel Exchange: Update Indicator Status** - Opens the Update Indicator Status dashboard with the selected field value.
* **Cyware Intel Exchange: Add New Indicator** - Opens the Add New Indicator dashboard with the selected field value.
* **Cyware Intel Exchange: Add Indicators in Bulk** - Opens the Add Indicators in Bulk dashboard with the selected field value.
* **Cyware Intel Exchange: Get/Update Allowed Indicators** - Opens the Get/Update Allowed Indicators dashboard.
* **Cyware Intel Exchange: Add to Allowlist** - Opens the Add to Allowlist dashboard with the selected field value.
* **Cyware Intel Exchange: Add/Remove Tags from Indicator** - Opens the Add/Remove Tags from Indicator dashboard with the selected field value.
* **Cyware Intel Exchange: Add Note in Intel Exchange** - Opens the Add Note in Intel Exchange dashboard with the selected field value.
* **Cyware Intel Exchange: Create Task in Intel Exchange** - Opens the Create Task in Intel Exchange dashboard with the selected field value.

## SEARCHES
* To see ingested data for Cyware Intel Exchange, select the `Search` tab. Search `` `cyware_indicator_indices` sourcetype=ctix``.

## TROUBLESHOOTING

### General Checks
* To troubleshoot Cyware Intel Exchange, check `$SPLUNK_HOME/var/log/Splunk/ta_cyware_*.log` or user can search `index="_internal" source=*ta_cyware_*.log*` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_cyware_*.log* ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this Add-on will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* Add-on icons are not showing up: The Add-on does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.

### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled) and also ensure that the kvstore is enabled.
* Check `ta_cyware*.log*` file for Cyware Intel Exchange data collection for any relevant error messages.

### Correlation
* Note that correlation is field based and it will only match to those Splunk events having value exactly same as values in configured fields on Correlation Page.
* Check `ta_cyware_correlation_command.log` file for further analysis.

#### Master Lookup
* If it seems that all the data of indicators is not available in `cyware_ti_<indicator_type>` lookup, ensure that the input is enabled and has completed at least one data collection cycle. You can also run `| inputlookup cyware_ti_<indicator_type>` to verify the lookup contents.

#### Custom Commands

* cywarematchindicators
    * Check that `cyware_matched_indicators_<indicator_type>` lookup is not empty and also ensure that `cyware_correlate_<indicator_type>_indicators` savedsearch is enabled.
    * Check `ta_cyware_correlation_command.log` file for further analysis.
* ctixaddindicator
    * Check `ta_cyware_add_indicator_custom_command.log` file for further analysis.
* ctixupdateindicatorstatus
    * Check `ta_cyware_update_indicator_status.log` file for further analysis.
* ctixgetallowlist
    * Check `ta_cyware_get_allowlist.log` file for further analysis.
* ctixupdateallowlist
    * Check `ta_cyware_add_allowlist.log` file for further analysis.
* ctixmanagetags
    * Check `ta_cyware_manage_tags.log` file for further analysis.
* ctixaddnote
    * Check `ta_cyware_add_note.log` file for further analysis.
* ctixaddtask
    * Check `ta_cyware_create_task.log` file for further analysis.
* ctixaddbulkindicators
    * Check `ta_cyware_add_bulk_indicators.log` file for further analysis.
* ctixmanagebulksources
    * Check `ta_cyware_bulk_sources_custom_command.log` file for further analysis.
* ctixbulkingestionengine
    * Check `ta_cyware_bulk_ingestion_engine.log` file for further analysis.
* cywareindextokvstoremigration
    * Check `ta_cyware_migration_custom_command.log` file for further analysis.
* cywaredeleteindicators
    * Check `ta_cyware_delete_indicators.log` file for further analysis.

### SSL Configuration
1. By default, the API calls from the Cyware Add-on for Splunk would be verified by SSL. The configurations are present in $SPLUNK_HOME/etc/apps/TA-cyware-ctix/default/ta_cyware_ctix_settings.conf file:
    ```
    [verify_ssl]
    ssl_validation = true
    ```
2. In order to make unverified calls, change the SSL verification to False. To do that, navigate to $SPLUNK_HOME/etc/apps/TA-cyware-ctix/local/ta_cyware_ctix_settings.conf file and change the verify_ssl parameter value to False under additional_parameters stanza. Create a stanza if its not present already.
3. Restart the Splunk in order for the changes to take effect.

### Dashboards
* Panel not populating:

1. Indicator Overview:
    * If dashboard panels are not populating data, it is possible that the Add-on's data collection has not yet completed. Ensure that the input is enabled and has run at least once.

2. Correlation Overview:
    * If the data is not populated in the above listed panels, then ensure that Indicator data is collected in Splunk and the `cyware_matched_indicators_<indicator_type>` lookup is filled with the latest data.
    * Also please ensure that savedsearches `cyware_correlate_<indicator_type>_indicators` or `cyware_correlate_<indicator_type>_indicators_<datamodel>` savedsearches are enabled.
    * If dashboard panels are not populating data, it is possible that Add-on's Saved Searches have not yet encountered newly ingested data on their previous execution. Please check Next Schedule Time in Settings -> Searches, reports and alerts. Most likely the panels will be populated once all saved searches complete their next execution.


## BINARY FILE DECLARATION

* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with PyYAML module and source code for the same can be found at https://pypi.org/project/PyYAML/
* _speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with MarkupSafe module and source code for the same can be found at https://pypi.org/project/MarkupSafe/

## SUPPORT
* Support Offered: Yes
* Support Details:
    * Email: support@cyware.com

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-cyware-ctix
* Remove $SPLUNK_HOME/var/log/Splunk/ta_cyware_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

#### Copyright (C) 2026 Cyware Intel Exchange. All rights reserved.
