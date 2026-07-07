# Team Cymru Scout App For Splunk
## OVERVIEW
The Team Cymru Scout App For Splunk pulls Indicators from the Team Cymru Scout platform. The integration does correlation and provides dashboards for visualization.

## REQUIREMENTS

* Splunk Common Information Model (CIM datamodels) (To match the indicators with the datamodel events)(https://splunkbase.splunk.com/app/1621). 


## COMPATIBILITY MATRIX
* Splunk version: 10.0.x, 9.4.x, 9.3.x, 9.2.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent


## RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## RELEASE NOTES

### Version 1.1.1

* Added `python.required = 3.9` setting to REST handlers, modular inputs, custom commands, and alert actions to restore Splunk Cloud Platform compatibility with the updated AppInspect vetting (replaces the now-deprecated `python.version` setting).

### Version 1.1.0

* Added support for open_ports, pdns, fingerprints, and x509 fields in the collection of IP details data.
* Added Communications, Open Ports, PDNS, Fingerprints, and X.509 panels in the Live Investigation Dashboard for IP indicator type.

### Version 1.0.2

* Resolved Multiselect filter issue

### Version 1.0.1

* Updated Logos
* Minor Bug Fixes

### Version 1.0.0

* Added data collection for Team Cymru Scout Indicators.
* Added field-based correlation feature to find sightings in Splunk events.
* Added Indicators Overview, Correlation Overview, Account Usage and Live Investigation Dashboards.

## INSTALLATION
Team Cymru Scout App For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `Team Cymru Scout App For Splunk App` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## UPGRADE
General upgrade steps:
1. Log in to Splunk Web and navigate to Team Cymru Scout App For Splunk -> Inputs.
2. Here disable all configured Inputs.
3. Navigate to Apps -> Manage Apps on Splunk menu bar.
4. Click Install app from file.
5. Click Choose file and select the TeamCymruScoutAppForSplunk installation file.
6. Check the Upgrade checkbox.
7. Click on Upload.
8. Restart Splunk.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App can be set up in two ways:

1. Standalone Mode
    * Install the Team Cymru Scout App For Splunk App.
    * Follow all the steps mentioned in `App Setup` section to configure the App.
2. Distributed Environment
    * Install the Team Cymru Scout App For Splunk App on the Search Head and Heavy Forwarder.
    * Follow the steps #1, #2 , #3 and #4 from  `App Setup` section on Heavy Forwarder.
    * Follow the step #5 from  `App Setup` section on Search Head.
    * In case of Search Head Clustering, make sure that steps #4 and #5 from `App Setup `are configured only on single search head. In such cases, the configuration will not be visible on other search heads. This is recommended approach.
    * Follow the step #5 from `App Setup` section on Search Head. Following these steps will replicate the configuration on all search heads.
3. Cloud Environment
    * Install the Team Cymru Scout App For Splunk on Searchhead.
    * Install the Team Cymru Scout App For Splunk on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the Team Cymru Scout App For Splunk on the On-Premise Heavy Forwarder.

## CONFIGURATION
Configure Team Cymru Scout App For Splunk

### App Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.
3. Configure the settings related to Splunk KVStore and Correlation in `KV Lookup Rest` and `Correlation Settings` section respectively. 
4. After the configuration of `KV Lookup Rest` and `Correlation Settings`, users can configure the inputs by specifying the required parameters.
5. Configure the settings related to correlation searches and lookups in `Correlation Settings` section.

> **NOTE** :  There might be some delay for the dashboards to populate, as these dashboards are based on savedsearches.

### Account
To configure the Account,

1. Navigate to the `Configuration`.
2. Provide your Team Cymru Scout App Platform address, credentials and click on `Add`.

| Team Cymru Scout App Account parameters   | Mandatory or Optional | Description                                 |
| ----------------------------  | --------------------- | ------------------------------------------- |
| Account name                  | Mandatory        | Enter a unique name for this account. |
| Authentication Type           | Mandatory             | Select the type of Authentication. Available options are Basic Auth and Api Key |
| Username          | Mandatory (Basic Auth)          | Enter the username for this account. |
| Password          | Mandatory (Basic Auth)      | Enter the password for this account.|
| API Key             | Mandatory (Api Key)       | Enter the API Key for this account.|

### Proxy
To configure the Proxy,

1. Navigate to the `Configuration`.
2. Click on the `Proxy` tab. 
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy     |
|    Proxy Type            |     Optional            |  Type of the Proxy. Available options are http and socks5. Default is http.|
|    Host            |     Optional            |  Host or IP of the proxy server                                                        |
|    Port            |     Optional            |  Port for proxy server                                                                 |
|  Username          |     Optional             |  Username of the proxy server |
|  Password          |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging,

1. Navigate to the `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`. By default the log level is set to 'INFO'.

### KV Lookup Rest
To configure the Splunk KVStore,

1. Navigate to the `Configuration`.
2. Click on the `KV Lookup Rest` tab.
3. Provide the required values and click on Save.

| KVStore Parameters       | Mandatory or Optional | Description                                                  |
|------------------------|----------|-----------------------------------------------------------------------------|
| Collection Type   | Mandatory   | Select mode to create lookups. (Defult: Index)            |
| Indicator Indices       | Mandatory      | Master lookup for indicators will be updated based on the indicators data in the selected indices. |
| Splunk Rest Host URL | Mandatory (lookup) | Enter the Splunk rest host or localhost (without http(s) scheme) to collect data.(Default: localhost) |
| Port | Mandatory (lookup) | Enter the management port of the Splunk.(Default: 8089) |
| Splunk Username | Mandatory (lookup) | Not required if Splunk Rest Host URL is localhost or 127.0.0.1. Configured user should have at least power role capabilities | 
| Splunk Password | Mandatory (lookup) | Enter the password for Splunk account. No need to provide a Password if Splunk Rest Host URL is localhost or 127.0.0.1 |

> **NOTE** : If using Cluster environment then make sure that all fields are configured and splunkd port 8089 of Splunk Management is open for storing lookups.

### Correlation Settings
To configure the Correlation Settings,

1. Navigate to the `Configuration`.
2. Click on the `Correlation Settings` tab.
3. Provide the required values and click on Save.

| Correlation Parameters       | Mandatory or Optional | Description                                                  |
|------------------------|----------|-----------------------------------------------------------------------------|
| Enabled Indicator Types | Optional      | Select the indicator types you want to enable correlation for. Available options are Domain and IP.         |
| Search Matching Algorithm       | Optional       | Select the method for correlating indicators. Available options are Raw search and Datamodel Search  |
| Select Datamodels  | Optional      | Select the data models from the list                   |
| IP: Target Query    | Optional       | Splunk query to get events from target events for correlation with IP Indicators     
| IP: Target Fields  | Optional      | Comma separated list of fields from target events to be used in correlation |
| Domain: Target Query | Optional | Splunk query to get events for correlation with Domain Indicators |
| Domain: Target Fields | Optional | Comma separated list of fields to be used in correlation |



### Upload Indicators
To configure the Upload Indicators,

1. Navigate to the `Upload Indicators`.
2. Provide the required values and click on Save.

| Input Parameter |  Mandatory or Optional | Description                                                  |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| File to upload the indicators            | Mandatory              | Select a csv file to upload the indicators                       |
| File Overwrite  | Optional               | Check this checkbox to overwrite the existing IP/Domain indicators. By default the indicators will be appended to the existing ones   |
| API Type        | Mandatory              | Select the type of API to collect initially selected Foundation | 
| Team Cymru Scout Account | Mandatory     | Select the Team Cymru Scout Account for which you want to collect data. |
| Interval        | Mandatory              | Time interval of input in seconds. Default=86400|
| Index           | Optional               | Select the index in which data should be collected. Only required if "Collection Type" is set to "Index". |

### Inputs
To configure the Inputs,

1. Navigate to the `Inputs`.
2. Click on `Create New Input`.
3. Provide the required information related to input and click on `Add` to configure the input.

| Input Parameter |  Mandatory or Optional | Description                                                  |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | A name to uniquely identify the input                        |
| Interval        | Mandatory              | Time interval of input in seconds. Default=86400               |
| Index           | Mandatory              | Select the index in which data should be collected. Only required if "Collection Type" is set to "Index".       |
| Team Cymru Scout Account| Mandatory      | Select the Team Cymru Scout Account for which you want to collect data.             |
| API Type        | Mandatory              | Select the type of API to collect  |
| Indicator Types | Mandatory              | Select the type of indicators to collect. |
| Indicators      | Mandatory              | Enter the comma seperated indicators. |


## LOOKUPS
* `team_cymru_indicators_foundation_ip`: This lookup contains foundation data for IP .
* `team_cymru_indicators_details_ip`: This lookup contains details data for IP.
* `team_cymru_indicators_details_domain`: This lookup contains details data for Domain .
* `team_cymru_matched_indicators_domain`: This lookup contains the matched indicator data for Domain.
* `team_cymru_matched_indicators_ip`: This lookup contains the matched indicator data for IP.

User can check data in lookup by running following SPL query in Splunk search: `| inputlookup <NAME OF LOOKUP>`

## SAVEDSEARCHES
This application contains the following saved searches:

* **update_team_cymru_foundation_ip_indicator_master_lookup** - Update Foundation IP Indicators from index to `team_cymru_indicators_foundation_ip`
* **update_team_cymru_details_ip_indicator_master_lookup** -Update Details IP Indicators from index to `team_cymru_indicators_details_ip`  
* **update_team_cymru_details_domain_indicator_master_lookup** - Update Details Domain Indicators from index to `team_cymru_indicators_details_domain` .
* **team_cymru_correlate_Domains_indicators** -Match Indicators of type Domains from the master_lookup against Splunk events .
* **team_cymru_correlate_IPs_indicators** - Match Indicators of type IPs from the master_lookup against Splunk events.
* **team_cymru_correlate_IPs_indicators_network_traffic** - Match indicators from the IPs master_lookup against Network_Traffic events.
* **team_cymru_correlate_IPs_indicators_malware** - Match indicators from the IPs master_lookup against Malware events
* **team_cymru_correlate_IPs_indicators_intrusion_detection** - Match indicators from the IPs master_lookup against Intrusion_Detection events
* **team_cymru_correlate_IPs_indicators_authentication** - Match indicators from the IPs master_lookup against Authentication events.
* **team_cymru_correlate_IPs_indicators_certificates** - Match indicators from the IPs master_lookup against Certificates events.
* **team_cymru_correlate_IPs_indicators_endpoint_filesystem** - Match indicators from the IPs master_lookup against Endpoint (Filesystem dataset) events.
* **team_cymru_correlate_IPs_indicators_endpoint_services** -  Match indicators from the IPs master_lookup against Endpoint (Services dataset) events.
* **team_cymru_correlate_IPs_indicators_endpoint_processes** -  Match indicators from the IPs master_lookup against Endpoint (Processes dataset) events.
* **team_cymru_correlate_IPs_indicators_email** -  Match indicators from the IPs master_lookup against Email events.
* **team_cymru_correlate_IPs_indicators_compute_inventory** -  Match indicators from the IPs master_lookup against Compute_Inventory events.
* **team_cymru_correlate_IPs_indicators_network_resolution** - Match indicators from the IPs master_lookup against Network_Resolution events.
* **team_cymru_correlate_IPs_indicators_updates** -  Match indicators from the IPs master_lookup against Updates events.
* **team_cymru_correlate_IPs_indicators_web** -  Match indicators from the IPs master_lookup against Web events.
* **team_cymru_correlate_Domains_indicators_network_traffic** - Match indicators from the Domains master_lookup against Network_Traffic events .
* **team_cymru_correlate_Domains_indicators_malware** - Match indicators from the Domains master_lookup against Malware events .
* **team_cymru_correlate_Domains_indicators_intrusion_detection** - Match indicators from the Domains master_lookup against Intrusion_Detection events .
* **team_cymru_correlate_Domains_indicators_authentication** - Match indicators from the Domains master_lookup against Authentication events .
* **team_cymru_correlate_Domains_indicators_certificates** - Match indicators from the Domains master_lookup against Certificates events.
* **team_cymru_correlate_Domains_indicators_endpoint_filesystem** - Match indicators from the Domains master_lookup against Endpoint (Filesystem dataset) events .
* **team_cymru_correlate_Domains_indicators_endpoint_services** - Match indicators from the Domains master_lookup against Endpoint (Services dataset) events.
* **team_cymru_correlate_Domains_indicators_endpoint_processes** - Match indicators from the Domains master_lookup against Endpoint (Processes dataset) events.
* **team_cymru_correlate_Domains_indicators_email** -Match indicators from the Domains master_lookup against Email events.
* **team_cymru_correlate_Domains_indicators_compute_inventory** - Match indicators from the Domains master_lookup against Compute_Inventory events .
* **team_cymru_correlate_Domains_indicators_network_resolution** -Match indicators from the Domains master_lookup against Network_Resolution events
* **team_cymru_correlate_Domains_indicators_updates** - Match indicators from the Domains master_lookup against Updates events.
* **team_cymru_correlate_Domains_indicators_web** - Match indicators from the Domains master_lookup against Web events.
* **Delete Older IPs from `team_cymru_matched_indicators_ip` and `team_cymru_indicators_foundation_ip`** - IPs older than specified time will be deleted from `team_cymru_indicators_foundation_ip` and `team_cymru_matched_indicators_ip` lookups.
* **Delete Older IPs from `team_cymru_matched_indicators_ip` and `team_cymru_indicators_details_ip`** - IPs older than specified time will be deleted from `team_cymru_indicators_details_ip` and `team_cymru_matched_indicators_ip` lookups.
* **Delete Older Domains from `team_cymru_matched_indicators_domain` and `team_cymru_indicators_details_domain`** - Domains older than specified time will be deleted from `team_cymru_indicators_details_domain` and `team_cymru_matched_indicators_domain` lookups.

## Custom Commands
This application contains the following custom commands:

* **teamcymrumatchindicators**
    * Description : This command performs the correlation between Team Cymru indicator and provided Splunk events. 
    * Parameters :
        * indicator_type : The type of indicator to be matched

* **teamcymruaccountusage**
    * Description : Provide details on query usage, including remaining API calls and the API limit already utilized of the cymru account. 

* **teamcymruscoutsectionsearch**
    * Description : This command is useful to get live investigation dashboard data.

* **teamcymruscoutsearch**
    * Description : This command is useful to get live investigation dashboard data.

## Alert Actions
This application contains the following alert actions:

* **team_cymru_indicators_monitors**
    * Description : To monitor indicators from given search with Team Cymru Scout.
    * Parameters : 
        * field_name: Name of field to be used for monitoring indicators.
        * index: Select the index in which data should be collected.
        * global_account: Select the Team Cymru Scout account for which you want to collect data.
        * api_type: Select the type of API to collect.

## SEARCHES
* To see ingested data for Team Cymru Scout App For Splunk, select the `Search` tab. Search `` `team_cymru_indicator_indices` sourcetype=*team_cymru_*``.

## TROUBLESHOOTING
### General Checks
* To troubleshoot Team Cymru Scout App For Splunk, check `$SPLUNK_HOME/var/log/Splunk/ta_team_cymru_scout*.log` or user can search `index="_internal" source=*ta_team_cymru_scout_*.log*` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_team_cymru_scout*.log* ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* if you are facing a problem related to ip address, then check for the lookup `team_cymru_indicators_details_ip`
* if you are facing a problem related to domain address, then check for the lookup `team_cymru_indicators_details_domain`
*  if you are facing a problem related to foundation ip address, then check for the lookup `team_cymru_indicators_foundation_ip`
* App icons are not showing up: The App does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.


### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled) and also ensure that the kvstore is enabled.
* Check `ta_team_cymru_scout*.log*` file for  Team Cymru Scout App For Splunk data collection for any relevant error messages.

### Correlation
* Note that correlation is field based and it will only match to those Splunk events having value exactly same as Indicator value.
* Check `ta_team_cymru_scout_correlation_command.log` file for further analysis.

#### Master Lookup
* If it seems that all the data of indicators from the Splunk index is not available in `team_cymru_indicators_<indicator_type>` lookup, then execute the savedsearch `update_TeamCymruScoutAppForSplunk_<indicator_type>_indicator_master_lookup` manually over a larger time range to refill the lookup.

#### Custom Commands
* teamcymrumatchindicators
    * Check that indices of the collected Indicators data are stored in `Indicator Indices` parameter of correlation settings.
    * Check that `team_cymru_matched_indicators_<indicator_type>` lookup is not empty and also ensure that `team_cymru_correlate_<indicator_type>` savedsearch is enabled.
    * Check `ta_team_cymru_scout_correlation_command.log` file for further analysis.
* teamcymruaccountusage
    * Check `ta_team_cymru_scout_enrichment_command.log` file for further analysis.
* teamcymruscoutsectionsearch
    * Check `ta_team_cymru_scout_section_search_command.log` file for further analysis.
* teamcymruscoutsearch
    * Check `ta_team_cymru_scout_search_command.log` file for further analysis.

### Dashboards
* Panel not populating:

    1. Live Investigation Dashboard:
        * Live Investigation Dashboard Panels:
            1. Indicator Type
            2. Indicators
            3. Team Team Cymru Scout Scout Account
            4. Identity Details
            5. Insights Information
            6. Open Ports
            7. Most Observed Domains
            8. Certificate Details
            9. Most Observed Fingerprints
            10. Overview > PDNS
            11. Overview > Tags
            12. Overview > Open Ports
            13. Overview > Certificate
            14. Overview > Events
            15. Communications > Protocols for and Its Peers
            16. Services > Top 10 Services for and Its Peers
            17. Tags > Top 10 Tags for and Its Peers
            18. ASNs > Top 10 ASNs for and Its Peers
            19. Countries > Top 10 Countries for and Its Peers
            20. Domain Details
            21. Whois > General
            22. Whois > Admin
            23. Whois > Tech
            24. Whois > Organisation
        * Check `ta_team_cymru_scout_search_command.log` file for further analysis.
        * Check `ta_team_cymru_scout_section_search_command.log` file for further analysis.

    2. Correlation Overview Dashboard:
        * Correlation Overview Dashboard Panels:
            1. Total Matched Indicators
            2. Matched Indicators by Type
            3. Matched Indicators Details
        * If the data is not populated in the above listed panels, then ensure that Indicator data is collected in Splunk and the `team_cymru_matched_indicators_<indicator_type>` lookup is filled with the latest data.
        * Also please ensure that savedsearches `team_cymru_correlate_IPs_indicators_<indicator_type>` savedsearches are enabled.
        * If dashboard panels are not populating data, it is possible that App's Saved Searches have not yet encountered newly ingested data on their previous execution. Please check Next Schedule Time in Settings -> Searches, reports and alerts. Most likely the panels will be populated once all saved searches complete their next execution.
        * In Matched Indicators Details panel there is column `Live investigation` if you click on Live investigation cell it will redirect to Live investigation dashboard with the indicator of that row.
        *  In Matched Indicators Details panel there is column `Local investigation` if you click on Local investigation cell it will redirect to Search page with its ip and index.

    3. Indicators Overview Dashboard:
        * Indicators Overview Dashboard Panels:
            1. Indicator Type
            2. Total Indicators
            3. Indicators Reported in Last Week
            4. Indicators Reported in Last Day
            5. Indicators Ingested Over Time
            6. Indicators
            7. Identity Information by Indicators
            8. Insights Information by Indicators
            9. Indicators Details
         * If the data is not populated in the above listed panels, then ensure that Indicator data is collected in Splunk and the `team_cymru_indicators_details_domain` or `team_cymru_indicators_details_ip` or `team_cymru_indicators_foundation_ip` lookup is filled with the latest data.
        * Also please ensure that savedsearches `update_TeamCymruScoutAppForSplunk_<indicator_type>_indicator_master_lookup` savedsearches are enabled.
        * If dashboard panels are not populating data, it is possible that App's Saved Searches have not yet encountered newly ingested data on their previous execution. Please check Next Schedule Time in Settings -> Searches, reports and alerts. Most likely the panels will be populated once all saved searches complete their next execution.

    4. Account Usage Dashboard:
        * Account Usage Dashboard Panels:
            1. Account Usage Details
        * If dashboard panels are not populating data, it is possible that App's Saved Searches have not yet encountered newly ingested data on their previous execution. Please check Next Schedule Time in Settings -> Searches, reports and alerts. Most likely the panels will be populated once all saved searches complete their next execution.

## BINARY FILE DECLARATION

* md.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TeamCymruScoutAppForSplunk
* Remove $SPLUNK_HOME/var/log/Splunk/ta_team_cymru_scout*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Details:
    * Email: support@cymru.com

#### Copyright © Pure Signal Scout ™ 2007-2025. All rights reserved.
