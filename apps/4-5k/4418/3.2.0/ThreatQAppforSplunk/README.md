# ThreatQuotient App for Splunk

# OVERVIEW #
* The ThreatQuotient App for Splunk Provides matching functionalities of the Splunk events with the ThreatQ indicators and also builds a dashboard from data provided by ThreatQuotient Add-on for Splunk.
* Author - ThreatQuotient Inc.
* Version - 3.2.0


# COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Linux (CentOs, Ubuntu) and Windows
* Splunk Enterprise version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

# REQUIREMENTS
* This application should be installed on Search Head.
* Splunk Enterprise Security (For Splunk Enterprise Security specific features).
* Splunk Common Information Model (CIM datamodels) (To match the indicators with the datamodel events). 

# RELEASE NOTES

## Version 3.2.0

* Added support for regex and partial based matching.
* Introduced support for port-based matching.
* Added support for custom data models for matching.
* Added support for maintaining multiple data model matches for the same IOC value.
* Added Match Count (lifetime match count) and Event Count (last-run match count) fields to Sighting events.
* Added a new dashboard panel that displays the count of events matched in the last run, grouped by matched data model.
* Added CAC (Common Access Card) authentication support for account configuration.
* Updated the add-on builder to v4.5.1

## Version 3.1.0

* Added OAuth authentication support for account configuration.
* Added an option to skip the Splunk's port to be posted on ThreatQ server as a part of attribute.

## Version 3.0.2

* Added compatibility for Splunk 10.

## Version 3.0.1

* Removed sort parameter for attributes API call used in threatqconsumeindicatorsnew and threatqconsumeindicators custom command.

## Version 3.0.0

* Fixed Splunk cloud compatibility issues.
* Added support to perform bulk indicator lookup.
* Added support to fetch latest indicators from ThreatQ to Splunk through the App. Configure “Splunk Forwarder" under Configuration section to leverage the feature.
* Added support to send custom fields from Splunk to ThreatQ Portal.
* Added support to send Datamodel name and latest raw event to ThreatQ portal.

## Version 2.8.0

* Fixed connectivity issue by using requests library.

## Version 2.7.0

* Fixed app inspect warnings

## Version 2.6.0

* Added "Configuration" tab for ThreatQ account and "App Settings" to avoid dependency on Add-on in a distributed environment.
* Removed the "Verify SSL Certificate" checkbox from the Configuration page. Navigate to the `$SPLUNK_HOME/etc/apps/ThreatQAppforSplunk/bin/threatq_const.py` and change VERIFY_SSL to False if certifiacte validation is not required.
* Included "Splunk Web URL" field in ThreatQ account's tab.
* Migrated "Alert Actions" and "Workflow Actions" from the Add-on to App.
* Removed "ThreatQ: Add To Whitelist" workflow action.
* Added "ThreatQ: Update Indicator Status" workflow action with options from the lookup.
* Options for the "ThreatQ Update Indicator Status" alert action will now populate from the lookup.
* Added "Indicators Malware Family Distribution" and "Indicators With Sightings Malware Family Distribution" panels in Threat Dashboard.
* NOTE: Non-Admin users won't be able to configure "App Settings". 

## Version: 2.5.0
* Minor bug fixes.
* Bundled jQuery in app package and upgraded its version to v3.5.0

## Version: 2.4.1
* Minor bug fixes.

## Version: 2.4.0
* Provided support of Additional Attributes / Custom fields to store in KVstore master lookup.
* Added option for more filtering for raw matching.
* Added support of chunking option in "threatqfieldmatchiocs" custom command which is used in datamodel saved searches.
* Added support of tstats based query for the datamodel saved searches.

## Version: 2.3.0
* Minor bug fixes. 

## Version: 2.2.0
* Providing option on the setup page for Hostname configuration. (This value will be used as a Source attribute while calling consume endpoint).
* Staggering the savedsearches to avoid the concurrent search limitation.
* Providing Malware Family attribute field in kvstore.
* Providing Partial URL matching support in datamodel searches.
* Combined the datamodel savedsearches.
## Version: 2.1.0
* Made some changes related to the KV store.
* Added some new dashboards.
* Minor bug fixes
## Version: 2.0.0
* Made the app Python2 and Python3 compatible
* Minor bug fixes
## Version: 1.3.0
* Threat Intelligence support for Enterprise Security is now provided using its REST APIs
## Version: 1.2.0
* Adding Splunk as a **Source** and **Splunk Sighting Timestamp** attribute to the indicator object while calling consume endpoint.
* Added option to configure **threatq_match_indices** macro from the Setup Dashboard.
* Added new consume endpoint savedsearch(threatqconsumeindicatorsnew) to create multiple events for each sighted indicator.
* Added Sighting Event Configuration section in the Setup Dashboard to choose between **threatq_consume_indicators** and **threatq_consume_indicators_new** consume endpoint savedsearch.
* Updated matching algorithm to add new fields(last_run_first_seen, last_run_last_seen, last_run_match_count) in the threatq_matched_indicators lookup.
## Version: 1.1.0
* Added savedsearches to match indicators with the datamodel events.
* Added Setup Dashboard to choose the matching algorithm. ("Raw search" option to match indicators with raw events and "Datamodel search" option to match indicators with the datamodel events)
* Provided option(Checkbox) in the Setup Dashboard to Enable Splunk ES specific savedsearches to upload threatq indicators in Splunk ES Threat Intelligence lookup.
* Added macro to configure the number of processes spawned by threatq_matched_indicators and threatq_update_matched_indicators savedsearches.
* Added logic to acquire write lock at the time of writing indicators to threatq_matched_indicators lookup table.
* While calling consume endpoint, only the first 10k indicators will get uploaded to ThreatQ platform. If sightings count is more than 10k, it will sort based on score first and than match count and the first 10k indicators will get uploaded.
* Added functionality in threatqmatchiocs custom command to accept IOC type as arguments of the custom command.
* Updated threatqoutputlookup custom command.

# UPGRADE

### General upgrade steps:
* Log in to Splunk Web and navigate to `Apps -> Manage Apps`.
* Click `Install app from file`.
* Click `Choose file` and select the ThreatQuotient App installation file.
* Check the `Upgrade` checkbox.
* Click on `Upload`.
* Restart Splunk.

## Upgrade to V3.2.0
* Follow the `General upgrade steps` section.
* Follow the `MIGRATION TO COMPOSITE KEY STRUCTURE` section.

## Upgrade to V3.1.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 3.0.2 to version 3.1.0

## Upgrade to V3.0.2
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 3.0.1 to version 3.0.2.

## Upgrade to V3.0.1
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 3.0.0 to version 3.0.1.

## Upgrade to V3.0.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 2.8.0 to version 3.0.0.

## Upgrade to V2.8.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 2.7.0 to version 2.8.0.

## Upgrade to V2.7.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 2.6.0 to version 2.7.0.

## Upgrade to V2.6.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 2.5.0 to version 2.6.0.
* Once the app has been upgraded, navigate to Info > Edit App Configuration > Account and configure the account for the app to perform workflow actions and AR actions. Configure Proxy and Logging if required.
## Upgrade to V2.5.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 2.4.1 to version 2.5.0

## Upgrade to V2.4.1
* Follow the `General upgrade steps` section.
* NOTE: If user will enter space seperated field or attribute while configuring custom attributes/fields in setup dashboard then it will be stored in lookup by replacing that space with underscore.
 eg. test1 test2 will be replaced by test1_test2. 

## Upgrade to V2.4.0
* Follow the `General upgrade steps` section.
* NOTE : For correct working of tstats based query of datamodel saved searches, accelerated datamodels are required to enabled. (until the splunk bug is fixed.)

## Upgrade to V2.3.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade ThreatQuotient App for Splunk from version 2.2.0 to version 2.3.0

## Upgrade to V2.2.0
* Before Upgrading the App, remove the savedsearches.conf and macros.conf from $SPLUNK_HOME/etc/apps/ThreatQAppforSplunk/local folder, becasue we have made some changes in these conf files which won't be reflected if the old savedsearches are present in local folder.
* Go to Apps > Manage Apps and click the install app from file.
* Click Choose file and select the ThreatQAppforSplunk installation file.
* Check the Upgrade app checkbox and click on Upload.
* After a successful restart, go to the apps list and open ThreatQuotient App for Splunk.
Note: If user is receiving the URL type of indicators with scheme from the threatq server then configure the enable_url_partial_match_datamodel macro with trigger_partial_url_match=true parameter for the partial matching in datamodel savedsearches.

## Upgrade to V1.2.0
* If the user has not changed default **threatq_match_indices** macro then the app upgrade will overwrite the macro definition with the default searchable index as a new macro definition.
* To change the **threatq_match_indices** macro definition after the app upgrade, the user has to reconfigure the app. Please, refer to **CONFIGURATION OF APP** section to reconfigure the app.

# MIGRATION TO COMPOSITE KEY STRUCTURE #

## Overview
Starting from version 3.2.0, the `threatq_matched_indicators` lookup uses composite keys (`ioc_value_datamodel_name OR ioc_value_Raw`) instead of single `ioc_value` keys. This enables separate tracking of matches per datamodel, allowing multiple events to be created when the same indicator matches in different datamodels.

## What Changed
* **Composite Keys**: Lookup entries now use keys in the format `{ioc_value}_{datamodel_name}` or `{ioc_value}_Raw` instead of just `{ioc_value}`
* **Separate Events**: When an indicator matches in multiple datamodels, separate events are created for each datamodel
* **Event Count Attribute**: New "Event Count" attribute added to show last run's match count (separate from cumulative "Match Count")

## Migration Steps

### Step 1: Run Migration Query (Create Composite Keys)
1. Open ThreatQuotient App For Splunk > Search
2. Run the following migration query to create/update rows with composite keys:
   ```spl
   | inputlookup threatq_matched_indicators
   | eval key_datamodel_name=if(isnotnull(raw_event) AND (isnull(datamodel_name) OR datamodel_name=""), "Raw", coalesce(datamodel_name, "Unknown"))
   | eval key_dm_safe=replace(key_datamodel_name, "[^A-Za-z0-9_-]", "_")
   | eval _key=ioc_value . "_" . key_dm_safe
   | table ioc_id, ioc_value, _key, match_time, first_seen, last_seen, match_count, score, status, type, updated_at, sources, adversaries, sid, last_run_first_seen, last_run_last_seen, last_run_match_count, malware_family, datamodel_name, raw_event
   | outputlookup threatq_matched_indicators key_field=_key
   ```
3. Wait for the query to complete.

### Step 2: Cleanup Old Keys
Run the following query to keep only rows whose existing `_key` already matches the computed composite key and drop legacy rows with old keys:

```spl
| inputlookup threatq_matched_indicators
| eval key_datamodel_name=if(
    isnotnull(raw_event) AND (isnull(datamodel_name) OR datamodel_name=""),
    "Raw",
    coalesce(datamodel_name, "Unknown")
  )
| eval key_dm_safe=replace(key_datamodel_name, "[^A-Za-z0-9_-]", "_")
| eval composite_key = ioc_value . "_" . key_dm_safe
| eval key = _key
| where key = composite_key
| outputlookup threatq_matched_indicators append=F
```

After this step, only composite-key rows remain in `threatq_matched_indicators` and old-key rows are removed.

### Step 3: Verify Migration
Run the following verification query to ensure all entries have composite keys:
```spl
| inputlookup threatq_matched_indicators
| eval has_composite_key=if(match(_key, "^.+_.+$"), "Yes", "No")
| stats count by has_composite_key
```
**Expected Result**: All entries should show `has_composite_key=Yes`

# RECOMMENDED SYSTEM CONFIGURATION #
* Because this Add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT #
This App can be set up in two ways:

1. Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install App on search head only.

# INSTALLATION OF APP #
* Follow the below-listed steps to install an Add-on from the bundle:
    * Download the App package.
    * From the UI navigate to Apps->Manage Apps.
    * In the top right corner select Install app from file.
    * Select Choose File and select the App package.
    * Select Upload and follow the prompts.

OR

* Directly from the Find More Apps section provided in Splunk Home Dashboard.

# CONFIGURATION OF APP #
* Configure ThreatQuotient App for Splunk:
    * After the installation of the app, the user must configure the app. To configure the app, under the "Info" tab, click on "Edit App Configuration", and configure as per the requirements.
        * Account Settings:
            * Select the Authorization Type
                * This will decide which method to use - Basic, OAuth or CAC.
            * Enter the ThreatQ Server URL
                * This value will be used to make the Post call from Workflow action or Alert action.
            * Enter the username of the ThreatQ server
                * This value will be used to connect to the ThreatQ Server.
            * Enter The password of the ThreatQ server
                * This value will be used to connect to the ThreatQ Server.
            * Enter the client ID of the ThreatQ server
                * This value will be used to connect to the ThreatQ Server.
            * Enter the client secret of the ThreatQ server
                * This value will be used to connect to the ThreatQ Server.
            * Enter the Splunk Web URL 
                * This value will be added in the Attributes of matched Indicator on the ThreatQ portal. User can access the URL to investigate further on Splunk instance.
            * Check/Uncheck the Include Port in Splunk URL
                * If checked, Splunk port will be included in the URL else it will be skipped.
        * App Settings:
            * Enter the unique Splunk Hostname.
                * This value will be used as a Source attribute while calling the consume endpoints.
            * Enter comma-separated Index Name.
                * This will overwrite the __threatq_match_indices__ macro definition to match threatq indicators with the event of selected indexes.
                * Note: Index Name is not mandatory field when Data Model matching algorithm is selected.
            * Sighting Event Configuration
                * Select **Single event for each sighted indicator (Default)** option to create a single event for each sighted indicator while calling consume endpoint. 
                * Select **Multiple events for each sighted indicator** option to create Multiple events for each sighted indicator while calling consume endpoint.
            * Check the checkbox to Enable Splunk ES specific savedsearches to upload threatq indicators in Splunk ES Threat Intelligence lookup.
            * Choose "Raw Search" option
                * This will enable the savedsearches that are used to match indicators with the raw events.
            * Choose "Datamodel Search" option and select required datamodels from the list. (More than Five data model can be selected but it will cause the skipping savedsearches as per the hardware configuration of the machine)
                * This will enable the savedsearches that are used to match indicators with the selected datamodels events.
            * Choose "Datamodel tstats Search" option
                * This will enable the tstats-based savedsearches that are used to match indicators with the accelerated datamodels events.
            * Check the "Enable Regex Matching" checkbox
                * Enables regex-based matching against raw events. Use with caution, as complex or numerous regex patterns may significantly impact search performance.
            * Check the "Enable Partial Matching" checkbox
                * Enables partial matching against raw events, applied only to String type IOC entries. This may increase processing overhead and degrade search performance on large datasets.
            * Check the "Send Raw Event to ThreatQ" checkbox
                * If checked, the latest raw event for the matched indicator will be sent to the ThreatQuotient platform.
            * Check the "Custom Datamodel?" checkbox if you want to use a custom datamodel
                * When enabled, custom datamodel and field selections can be configured for matching.
            * Select Datamodels
                * Select one or more CIM datamodels from the list (for example: Network Traffic, Malware, Incident Management, Intrusion Detection, Authentication, Certificates, Endpoint, Email, Inventory, Network Resolution (DNS), Updates, Web).
            * Select Custom Datamodel
                * Select the custom datamodel to be used for matching (if "Custom Datamodel?" is enabled).
            * Fields for Matching
                * Select the fields from the chosen datamodel(s) that should be considered for matching.
            * Enter comma-seperated field names to collect additional attributes
                * This will collect the data of those fields and store it into master_lookup.
            * ThreatQ Custom Attributes
                * Enter comma separated ThreatQ Attribute names. Values entered here will be treated as case-sensitive.
            * ThreatQ Custom Fields
                * Enter comma separated ThreatQ Field names. Values entered here will be treated as case-insensitive.
            * User can use a clear button to deselect the selected options.

        * Splunk Custom Fields Settings:
            * Search Matching Algorithm - This will be fetched from App Settings page.
            * Selected Datamodels - This will be fetched from App Settings page.
            * Indexes to consider - This will take indexes for which fields will be shown in the 'Splunk Custom Fields' section.t
            * Splunk Custom Fields - Select fields that you want to send to ThreatQ portal if data is available for that field.
            * Note that the only those fields will be available to select if it is present in the last 24 hours for the selected indexes/datamodels.

        * Splunk Forwarder Settings:
            * Splunk Forwarder URL - Enter the Splunk Forwarder URL or localhost (without scheme). (Default: localhost)
            * Splunk Forwarder Mgmt Port - Enter the management port of the Splunk Forwarder instance. (Default: 8089)
            * Splunk Forwarder Username - Enter the username for Splunk Forwarder instance. No need to provide an Username if Splunk Forwarder is localhost or 127.0.0.1
            * Splunk Forwarder Password - Enter the password for Splunk Forwarder instance. No need to provide a Password if Splunk Forwarder is localhost or 127.0.0.1
            * Enable Proxy - This Proxy configuration will be used to establish the connection to your Splunk Forwarder instance
            * Proxy Type - Type of proxy (http, socks4, socks5)
            * Proxy Host - Enter Proxy Host here.
            * Proxy Port - Enter Proxy Port here.
            * Proxy Username - Enter Proxy Username here.
            * Proxy Password - Enter Proxy Password here.

        * ThreatQ Indicator Lookup
            * Select Input Type - Either through search query or entering indicator values manually
            * Enter Search Query - Enter a search query containing one field with table command. eg: index=index1 | table my_field
            * Enter Indicators Manually - Enter comma separated value of indicators. eg: 1.1.1.1, 2.2.2.2
            * Page Size - Number of results per page
            * Send to Master Lookup - Selected entries will be sent to master_lookup.

        * Pull Indicators on-demand
            * Pull Indicators in Splunk by triggering input on Splunk Heavy Forwarder.


* Configure Macro:
    * If the user has selected a default index in "Data Input" configuration, then no need to perform this step. But if the user has given any other index in "Data Input" configuration, then do the below steps.
        * Go to Settings->Advanced search->Search macros
        * Select "ThreatQuotient App for Splunk" in App context
    * To restrict matching against events from specific indices and sourcetypes use threatq_match_indices and threatq_match_sourcetypes macros.
    * To match with the specific fields from raw_events use `threatq_match_fields` macro. eg. user wants to match the fields "field1 and field2" user will have to update macro definition like  "field1 OR field2".
    * To provide more customized filters to the correlation for raw matching use `threatq_match_base_query` macro.
    * To change the number of processes spawn by threatq_matched_indicators and threatq_update_matched_indicators saved searches, use threatq_match_process_count macro. If specified process_count="default" the number of processes spawned will be equal to integer half of the CPU count.
* Configure Savedsearch:
    * If the user wants to change the cron schedule for the new consume endpoint saved search(threatq_consume_indicators_new), then do the below steps.
        * Go to Settings->Searches, reports, and alerts
        * Select "ThreatQuotient App for Splunk" in App context
        * Search for "threatq_consume_indicators_new" saved search
        * Click on Edit->Edit Schedule, Enter a new valid cron schedule, and Save. (The interval of the new cron schedule must not be greater than the interval of threatq_match_indicators* and threatq_update_matched_indicators* saved searches.)
        * Click on Edit->Edit Search, Update the search query to have a new value in place of **-35m**, and Save. (The new value must not be less than the interval of this saved search.)
* In case of Search Head Cluster environment, ThreatQuotient App for Splunk needs to be configured on Splunk Search Head Deployer and then it should be pushed to Splunk Search Head Cluster.

# SAVEDSEARCHES
* This application contains following saved searches
    * threatq_update_matched_indicators_on_master_lookup_change - This saved search is used to update the matched indicators information in `threatq_matched_indicators` lookup.
    * threatq_match_indicators - This saved search is used to populate "threatq_matched_indicators" lookup
    * threatq_update_matched_indicators - This saved search is used to update the match time of indicators in "threatq_matched_indicators" lookup
    * threatq_match_indicators_network_traffic - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Network Traffic data model.
    * threatq_match_indicators_malware - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Malware data model.
    * threatq_match_indicators_incident_management_* - This saved searches are used to populate "threatq_matched_indicators" lookup with respect to Incident Management data model.
    * threatq_match_indicators_intrusion_detection - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Intrusion Detection data model.
    * threatq_match_indicators_authentication - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Authentication data model.
    * threatq_match_indicators_certificates - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Certificates data model.
    * threatq_match_indicators_endpoint_* - This saved searches are used to populate "threatq_matched_indicators" lookup with respect to Endpoint data model.
    * threatq_match_indicators_email - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Email data model.
    * threatq_match_indicators_compute_inventory - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Compute Inventory data model.
    * threatq_match_indicators_network_resolution - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Network Resolution data model.
    * threatq_match_indicators_updates - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Updates data model.
    * threatq_match_indicators_web - This saved search is used to populate "threatq_matched_indicators" lookup with respect to Web data model.
    * threatq_update_retired_indicators - This saved search indicators is used to retrieve the indicators from "master_lookup" and "threatq_matched_indicators".
    * threatq_consume_indicators -
        * This saved search is used to update the indicator object and to create/update sighting events for the sighted indicators on the ThreatQ.
        * It will create new sighting events for the newly sighted indicators and update the existing sighting event for the already sighted indicators.
        * This saved search requires the Account configuration of the ThreatQuotient Add-on for Splunk
    * threatq_consume_indicators_new - 
        * This saved search is used to update the indicator object and to create sighting events for the sighted indicators on the ThreatQ.
        * It will create new sighting events for every sighted indicator.
        *  For example, matching saved search finds three sightings for one indicator within the schedule window, only one event will be created with the match_count=3. Later if matching saved search finds two sightings for the same indicators, it will create a new event with the match_count=2.
    * threatq_cleanup_es_lookups -
        * This saved search is used to cleanup indicators from main (for example: ip_intel) threat intel lookups provided by Splunk Enterprise Security App. Note: This search only cleans up indicators that have threatq_indicator threat_key.

    * threatq_update_threat_intelligence_lookup_email_address - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_email_subject - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_file_name - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_fqdn - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_hash - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_ip - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_registry - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_service - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_certificate_serial - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_certificate_subject - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_url - This saved search is used to add data in Splunk ES lookups
    * threatq_update_threat_intelligence_lookup_user - This saved search is used to add data in Splunk ES lookups
    * threatq_all_indicators_dashboard_drilldown_search - This saved search is used in the drilldown of "All Indicators" dashboard
    * threatq_match_indicators_dashboard_drilldown_search - This saved search is used in the drilldown of "Matched Indicators" dashboard

# CUSTOM COMMANDS
* This application contains following custom commands
    * threatqmatchiocs - This custom command is used in saved searches "threatq_match_indicators" and "threatq_update_matched_indicators" to get the list of matching indicators with Splunk raw events.
    * threatqfieldsmatchiocs - This custom command is used in saved searches to get a list of matching indicators with different data models fields.
        * By appedning "is_update=true" with "pull_both_lookups_iocs=false" parameter, particular datamodel savedsearch will consider only threatq_matched_indicators for the correlation.
        * Using "enable_url_partial_match_datamodel" macro with setting up the "trigger_partial_url_match=true" parameter, particular datamodel savedsearch will strip out the URL scheme from the URL type of indicator in correlation.
        * By appedning only "pull_both_lookups_iocs=false" paramter, particular datamodel savedsearch will only the unmatched indicators from the master_lookup.
    * threatqoutputlookup - This custom command is used to write search results to the KV store collection.
    * threatqconsumeindicators - This custom command is used to post matched indicators to consume endpoint on ThreatQ.
    * threatqconsumeindicatorsnew - This custom command is used to post matched indicators to consume endpoint on ThreatQ. This will create new sighting events for the sighted indicators found in each time slot of matching savedsearch.
    * threatqcleanupeslookups - This custom command is used in a utility savedsearch "threatq_cleanup_es_lookups" which is disabled by default. Running it will allow you to clean up indicators that have threatq_indicator thretq_key in threat_intel lookups of Splunk Enterprise Security App.

# ADAPTIVE RESPONSE ACTION #
* Using Adaptive Response action, user can change the status of indicator to Expired or Whitelisted or Active or Indirect or Review from the Enterprise Security App.
* User can create the notable event on master_lookup data as well using query like "| inputlookup master_lookup | sendalert notable"

# WORKFLOW ACTION #
* Using workflow action, user can perform an action from Splunk to ThreatQuotient. Supported actions are as below:
    * ThreatQ: Add Indicator
    * ThreatQ: Lookup Indicator
    * ThreatQ: Mark as False Positive
    * ThreatQ: Mark as True Positive
    * ThreatQ: Update Indicator Status
* User can perform the workflow action from Splunk to ThreatQuotient without admin capability by performing following steps. 
    1. Navigate to `Settings > Advance search > Search macros`. Apply the app filter to "ThreatQuotient App for Splunk". 
    2. Edit the workflow_action_using_conf macro and set it to "True". 
    3. Go to the backend and create the credentials_storage.conf in local folder. (If local folder is not available then create new folder and name it to "local") 
    4. Now provide the below information in the credentials_storage.conf file. 

        sample of credentials_storage.conf: 

        ```
        [credentials] 
        server_url = <server_url> 
        username = <username> 
        password = <passoword> 
        threatq_splunk_url = <threatq_splunk_url> 
        client_id = <client_id> 
        ```

        ```
        [proxy_credentials] 
        proxy_enabled = <boolean> 
        proxy_password = <proxy_password> 
        proxy_port = <proxy_port> 
        proxy_type = <proxy_type> 
        proxy_url = <proxy_url> 
        proxy_username = <proxy_username>
        ```

    5. Restart the Splunk.

# TROUBLESHOOTING #
* To check the data collected by data collection in index use query like "index=<your_index_name> sourcetype=threatq:indicators".
* To check the data collected by data collection in master_lookup use query like "|inputlookup master_lookup".
* To check the data collected by data collection in threatq_indicator_types and threatq_indicator_status, use queries like "|inputlookup threatq_indicator_types" and "|inputlookup threatq_indicator_status" respectively.
* If more than 5 datamodels are configured then saved searches may be skipped due to its concurrent saved searches limit. So, To monitor any specific saved searches use query like "index=_internal sourcetype=scheduler app=ThreatQAppforSplunk savedsearch_name=<SAVEDSEARCH_NAME>".
* To check the concurrent saved searches limit or skipped saved searches ratio follow the below steps:
    * Navigate to Settings -> Monitoring Console.
    * Click on "Search" dropdown from the Navigation tab and select "Schedular Activity : Instance" dashboard.
* To troubleshoot ThreatQuotient App for Splunk please check $SPLUNK_HOME/var/log/splunk/ta_threatquotient_add_on_\*.log\* file or Navigate to the "Info" tab and click on "Application Logs" Dashboard.
* If the dashboard is not getting populated make sure saved searches are enabled.
* Make sure ThreatQuotient Add-on for Splunk is configured correctly for workflow actions and consume indicators functionality to work.
* If Splunk search URL generated by consume indicators functionality is not working make sure to configure hostname properly on the search head.
* If user want to run any saved search manually, they can click on Run button from Saved Search list. In the case of running search in Search window, user might see some discrepancy in sightings count.
* If user is getting "Not able to authenticate using provided configuration parameters" error, check if the SSL Validation is done properly. If it's not required, update the value for "Verify SSL" from backend at `$SPLUNK_HOME/etc/apps/ThreatQAppforSplunk/bin/threatq_const.py`.
* Running threatqmatchiocs or any other custom command sometimes may result in duplicate log entries in the log file. The reason for this behavior is Splunk SCPv2 based custom commands are called multiple times before its finally executed. This may cause duplicate log entries but data is only provided to the command on the execution call which should not impact anything except causing duplicate log entries. (Reference: https://github.com/splunk/splunk-sdk-python/issues/326, https://github.com/splunk/splunk-sdk-python/issues/161)
* If user has upgraded the app version from 2.1.0 to 2.2.0 then please check that old savedsearches.conf and macros.conf are removed from the local.
* If we are receiving the threatq
* If user is not able to access some of the functionality of threatq then refer the below table of roles and access by threatq functionality.
* 'ThreatQ Indicator Lookup' related logs can be checked in 'threatquotient_app_multiple_indicator_lookup.log file.
* 'Pull Indicators on-demand' related logs can be checked in ta_threatquotient_add_on_trigger_forwarder_input.log file.

| Functionality| Admin  | Power  | Splunk_System_Role | User | can_delete | ess_user | ess_analyst | ess_admin |
|--------------|------------------| ---------------- | ----------------| ----------------------| -------------------- | -------------------------| ------------------------------------ | -------------------------------- |
|Configure Account | create,edit,view,clone,delete | --- | create,edit,view,clone,delete | ---| ---| ---| ---| create,edit,view,clone,delete |
|Configure Input | create,edit,view,clone,delete | --- | create,edit,view,clone,delete | ---| ---| ---| ---| create,edit,view,clone,delete |
|Splunk Forwarder Configuration | can configure | --- | can configure | --- | ---|--- | --- | can configure |
| Pull Indicators on-demand | can execute | can execute | can execute | can execute | ---| can execute | can execute | can execute |
| ThreatQ Indicator Lookup | can execute | can execute | can execute | can execute | ---| can execute | can execute | can execute |
| Data Collection | enable,disable | enable,disable | enable,disable | enable,disable | --- | enable,disable | enable,disable | enable,disable |
| Use of Work Flow Actions | create,edit,view,delete,run | ---| create,edit,view,delete,run | ---| ---| ---| ---| create,edit,view,delete,run |
| Use of Alert Actions | create,edit,view,delete,run | ---| create,edit,view,delete,run | ---| ---| ---| ---| create,edit,view,delete,run |
| Configure Setup Dashboard | edit,view | view | edit,view | view | ---| view | view| edit,view |
| Use of Raw matching saved searches | create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run|
| Use of Data model saved searches | create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run|
| Use of ES related saved searches | create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run|

# LIMITATION #
* The app expects the 'id' field in the data export to be in lowercase only.
* Matching saved search may not work with a large number of events if the user runs saved search manually by clicking on the Run button from the Saved Search list. It is recommended to schedule the saved search to make it work correctly.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/ThreatQAppforSplunk
* Remove $SPLUNK_HOME/var/log/splunk/**threatquotient_setup.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_consume_indicators.log** 
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_consume_indicators_new.log** 
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_threatqcleanupeslookups.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_threatqmatchiocs.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_threatqfieldsmatchiocs.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_threatqoutputlookup.log**
* Remove $SPLUNK_HOME/var/log/splunk/**threatquotient_add_indicator.log**
* Remove $SPLUNK_HOME/var/log/splunk/**threatquotient_app_add_indicator_attribute.log**
* Remove $SPLUNK_HOME/var/log/splunk/**threatquotient_app_lookup_indicator.log**
* Remove $SPLUNK_HOME/var/log/splunk/**threatquotient_update_indicator.log**
* Remove $SPLUNK_HOME/var/log/splunk/**threatq_update_indicator_status_modalert.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_trigger_forwarder_input.log**
* Remove $SPLUNK_HOME/var/log/splunk/**threatquotient_app_multiple_indicator_lookup.log**

* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# Reference
* We took reference from https://github.com/georgestarcher/TA-SyncKVStore to collect the data in kvstore lookup directly.

# SUPPORT #
* Support Offered: Yes
* Support Email: support@threatq.com

### Copyright (c) 2026 ThreatQuotient, Inc.
