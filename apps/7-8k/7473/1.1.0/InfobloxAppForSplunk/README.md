# Infoblox App For Splunk

## OVERVIEW
* The Infoblox App For Splunk pulls Threats, Insights and Syslog (DNS, DHCP, Audit, Blocked Traffic) data from the Infoblox platform.

## COMPATIBILITY MATRIX
* Splunk version: 9.4.x, 9.3.x, 9.2.x, 9.1.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent


## RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## RELEASE NOTES

### Version 1.1.0

* Added `Infoblox SOC Insights Details` alert action to collect SOC Insights details data.

### Version 1.0.1

* Updated Splunk SDK version to v2.1.0.

### Version 1.0.0

* Added data collection and dashboards for Threats, Insights and Syslog (DNS, DHCP, Audit, Blocked Traffic, Service) data.

## INSTALLATION
Infoblox App For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `Infoblox App For Splunk` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## UPGRADE

### General upgrade steps:
* Log in to Splunk Web and navigate to `Infoblox App For Splunk` -> Inputs.
* Here disable all configured Inputs.
* Navigate to Apps -> Manage Apps on Splunk menu bar.
* Click Install app from file.
* Click Choose file and select the `Infoblox App For Splunk` installation file.
* Check the Upgrade checkbox.
* Click on Upload.
* Restart Splunk.

### Upgrade to v1.1.0
* Follow the General upgrade steps section.

### Upgrade to v1.0.1
* Follow the General upgrade steps section.


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App can be set up in two ways:

1. Standalone Mode
    * Install the Infoblox App For Splunk.
    * Follow all the steps mentioned in `App Setup` section to configure the App.
2. Distributed Environment
    * Install the Infoblox App For Splunk on the Search Head and Heavy Forwarder.
    * Follow the steps #1, #2, and #3 from  `App Setup` section on Heavy Forwarder.
3. Cloud Environment
    * Install the Infoblox App For Splunk on Search Head.
    * Install the Infoblox App For Splunk on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the Infoblox App For Splunk on the On-Premise Heavy Forwarder.

## CONFIGURATION
Configure Infoblox App For Splunk

## Syslog Configuration
* On Infoblox Portal, Follow the steps provided in this [link](https://docs.infoblox.com/space/BloxOneCloud/35430532/Setting+Up+Splunk) to setup the syslog data collection.
* On Splunk, Follow the steps provided in this [link](https://docs.splunk.com/Documentation/Splunk/9.2.1/Forwarding/Enableareceiver#:~:text=Log%20into%20Splunk%20Web%20as,Select%20%22Configure%20receiving.%22)  to enable the receiving of the Splunk CIM(Syslog) data.


### App Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections. 
3. After the configuration of `Account`, `Proxy` and `Logging`, users can configure the inputs by specifying the required parameters.

### Account
To configure the Account,

1. Navigate to the `Configuration`.
2. Provide your Infoblox API Key and Account Name and click on `Add`.

| Infoblox Account parameters   | Mandatory or Optional | Description                                 |
| ----------------------------  | --------------------- | ------------------------------------------- |
| Account name                  | Mandatory        | Enter a unique name for this account. |
| API Key                       | Mandatory        | Enter the API Key for this account.   |

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

### INPUTS
To configure the Inputs,

1. Navigate to the `Inputs`.
2. Click on `Create New Input`.
3. Select the input of which you want to collect data.
    * SOC Insights
    * Threat Intelligence
3. Provide the required information related to corresponding selected input and click on `Add` to configure the input.

#### SOC Insights

| Input Parameter |  Mandatory or Optional | Description                                                  |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | A name to uniquely identify the input                        |
| Interval        | Mandatory              | Time interval of input in seconds. |
| Index           | Optional              | Select the index in which data should be collected.|
| Infoblox Account| Mandatory      | Select the Infoblox Account for which you want to collect data.             |

#### Threat Intelligence

| Input Parameter |  Mandatory or Optional | Description                                                  |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | A name to uniquely identify the input                        |
| Interval        | Mandatory              | Time interval of input in seconds. |
| Index           | Optional              | Select the index in which data should be collected.|
| Infoblox Account| Mandatory      | Select the Infoblox Account for which you want to collect data.             |
| Threat Level | Optional | Enter the threat level for which you want to collect the data. |
| Confidence Level | Optional | Enter the confidence level for which you want to collect the data. |
| Historical Data | Optional | Select if you want to collect historical data. |
| Start Date Time | Optional | NOTE : Only appears if you click on the Historical Data checkbox. Provide start date time from which data will be collected. Default will last 30 days. eg. 2023-02-23 19:00:00.000 |

**NOTE**: For Threat Intelligence, there is a checkpoint mechanism implemented for both historical as well as latest data collection to avoid data duplication in splunk. Also that checkpoint will be deleted on deleting the corresponding input.


### Dashboards

1. Tools:
    * Sub Dashboards of Tools:
        1. IPAM Lookup: This dashboard provides details of IPAM lookup.
            * IPAM Lookup Panel:
                1. IPAM Lookup details:- This Panel shows complete details of the provided IP.

        2. TIDE Lookup: This dashboard provides details of Density Lookup.
            * TIDE Lookup Panel:
                1. TIDELookup details:- This Panel shows complete details of the provided type and value in table format.

        3. Dossier Lookup: This dashboard provides details of Forward Lookup.
            * Dossier Lookup Panel:
                1. Web Categories:- This Panel shows the information for  Web Categories.
                2. Threat Property:- This Panel shows the information for threat property.
                3. Active Threat Feeds and Status (RPZ Feeds):- This Panel shows the information for Active Threat Feeds and Status (RPZ Feeds).
                4. Inforank Ranking:- This panel shows the information for Inforank Ranking.
                5. VirusTotal:- This Panel shows the information for VirusTotal.
                6. DNS Threat Actor:- This panel shows the information for DNS Threat Actor.
                7. Geo Graphic Details:- This Panel shows the information for GeoGraphic Details.
                8. TLD Reputation:- This Panel shows the information for TLD Reputation.
                9. Nameserver Reputation:- This Panel shows the information for Nameserver Reputation.
                10. Threat Details (ATP):- This Panel shows the information for Threat Details (ATP).
                11. Registered Owner (WHOIS):- This Panel shows the information for Registered Owner (WHOIS).
                12. Current DNS:- This panel shows information for Current DNS.
                13. Domain Name Associated:- This Panel shows the information for Domain Name Associated.

        4. Block/Allow Domain/IP Tool: This dashboard allows user to Block/Allow Domain/IP Address.
            * Block/Allow Domain/IP Tool Panel:
                1. Block/Allow Details:- This shows the information about the added or removed Domain/IP Address for the provided named list

        5. DHCP Lease Lookup: This dashboard provides DHCP lease lookup details.
            * DHCP Lease Lookup Panel:
                1. DHCP Lease Event Panels:- This shows the information about DHCP Lease Event.

2. Syslog:
    * Sub Dashboards of Syslog:
        1. Audit Log Overview: This dashboard provides details on the actions performed by users.
            * Audit Log Overview Dashboard Panel:
                1. Top 10 Actions:- This Pannel provides details of top 10 actions performed.
                2. Top 10 User for Action:- This Pannel provides details of the top 10 users who performed a particular action.
                3. Top 10 SourceIP for User:- This Pannel provides details of the top 10 Source IPs for a particular user performing a specific action.
            4. Audit Logs:- This Pannel provides overview of Audit Logs.
        2. DHCP Overview: This dashboard provides details of Density Lookup.
            * DHCP Overview Dashboard Panel:
                1. Released DHCP Leases (Unique IPs): This panel displays a single value of Released DHCP leases with unique IPs.
                2. Released DHCP Leases: This panel displays a single value of Released DHCP leases without unique IPs.
                3. Updated DHCP Leases (Unique IPs): This panel displays a single value of Updated DHCP leases with unique IPs.
                4. Updated DHCP Leases: This panel displays a single value of Updated DHCP leases without unique IPs.
                5. DHCP Leases over Time: This panel shows a line chart of DHCP leases over time.
                6. Top 10 MAC Address: This panel will show Top 10 mac addresses in sorted order.
                    * Source IPs for MAC: "clicked value"=> This Will open a new search that shows a column chart of Sources IPs for that particular mac address.
                7. Top 10 IP Addresses: This panel will show Top 10 IP addresses in sorted order.
                    * Host for IP: "clicked value"=> This will open a new search with a pie chart of Host for that particular IP.
                8. DHCP Activity Summary: This panel will display a pie chart of Activities.
                9. DHCP Lease Event for "All" Activity(DrillDown from Activity summary, by default ALL): This will show complete details of DHCP leases events for that particular activity.
        3. DNS Overview: This dashboard provides details of DNS Overview.
            * DNS Overview Dashboard Panel:
                1. Most Queried FQDNs: This panel displays the table of all the FQDNs in sorted order.
                    * DrillDown -> Top 10 Devices for Domain: "clicked value" : This Will open a new search that shows the top 10 devices for the selected Domain.
                2. Top 10 Requested Device: This panel displays the Pie chart of the top 10 most requested devices.
                3. DNS Requests Count by Users: This panel displays the table of Most requested users in sorted order.
                    * DrillDown -> Top 10 Requested Domains by User: "clicked value" => This Will open a new search that shows a pie chart of Top 10 Requested Domains by that particular user.
                    * DrillDown -> DNS Requests made by User: "clicked value"=> This Will open a New search that shows complete information of DNS requests made by that particular user.
                        c. DrillDomn -> DNS Requests made by Device: "clicked value"=> This will open a new search that shows a column chart of DNS Requests made by that particular Device.
                4. Overall Queries Per Hour: This panel contains  a column  chart of overall queries per hour.
                    * Overall Queries Per minute: This Will open a new search that shows a column chart of overall queries per minute in that particular hour.
                5. Response Type: This panel displays the Pie chart of Response Types.
                    * DrillDown -> Top 20 Devices for "clicked value" Response Type: This Will open a new search that shows a pie chart of Top 20 Devices for that particular response type.
                    * DrillDown -> "clicked value" DNS Requests: This will open a new search that shows complete information of DNS requests for that particular response type.
                6. Query Type: This panel displays a pie chart of query types.
                7. DNS Requests: This panel shows complete information of DNS requests in table format.
        4. BLocked Traffic Overview: This dashboard provides details on compromised assets and blocked domains.
            *  BLocked Traffic Overview Dashboard Panel:
                1. Top 10 Compromised Users:- This Pannel provides details of the top 10 compromised users.
                2. Top 10 Blocked Domains:- This Pannel provides details of the top 10 domains that have been blocked.
                3. Top 10 RPZ Rules Hit:- This panel provides details of the top 10 RPZ rules that were triggered.
                4. Top 10 Compromised Assets:- This panel provides details of the top 10 compromised assets.
                5. Overall Blocked DNS Request for Asset:- This Pannel provides overview blocked request for assets.
        5. Service Log Overview: This dashboard provides details on the service name and host ID.
            * Service Log Overview Dashboard Panel:
                1. Service Log Data:- This panel provides an overview of service log data, including the service name and host ID.


3. Threat Intelligence Overview:
    * Threat Intelligence Overview Dashboard Panels: 
        1. Indicators Imported into Splunk by Indicator Type and Date: This panel displays a column chart of Indicators Imported into Splunk by Indicator Type and Date.
            * Drilldown-> "clicked value" Information =>This Will open a new search that shows a table that contains full information of that particular indicator.
        2. Total Host: This panel shows the total number of hosts.
        3. Total IPs: This panel shows the total number of IPs.
        4. Total URLs: This panel shows the total number of URLs.
        5. Total Hash: This panel shows the total number of Hash.
        6. Total Emails: This panel shows the total number of Emails.
        7. Indicators Observed: This panel shows a table that contains all indicators observed in sorted order.
        8. Indicators Observed over Time: This panel shows a line chart that contains all indicators observed over time.

4. SOC Insights Overview
    * SOC Insights Overview Panels:
        1. Count by Severity: This panel shows the pie chart of Severity.
        2. Count by Threat Type: This panel shows the column chart of Threat Type.
        3. SOC Insights Details: This panels provides information of insights for selected Severity & Threat Type.
        4. Summary: This Tab provides information for provided insight such as Observed time, queries count, impacted assets, indictors and events.
        5. Assets: This tab provides assets information for provided insight.
            * Drilldown-> Redirect to Block/Allow Domain/IP Tool dashboard with the corresponding Asset.
        6. Indicators: This tab provides indicators information for provided insight.
            * Drilldown-> Redirect to Block/Allow Domain/IP Tool dashboard with the corresponding Indicator.
        7. Events: This tab provides events information for provided insight.
            * Drilldown-> Redirect to Block/Allow Domain/IP Tool dashboard with the corresponding Device IP.
        8. Comments: This tab provides comments information for provided insight.

## LOOKUPS
* `infoblox_tide`: This lookup contains the data for tide lookup which is collected using the dashboard and it will be used as caching for the dashboard. By default, it will remove data from the lookup every 24 hours.
* `infoblox_dossier`: This lookup contains the data for the dossier lookup which is collected using the dashboard and it will be used as caching for the dashboard. By default, it will remove data from the lookup every 24 hours.

User can check data in lookup by running following SPL query in Splunk search: `| inputlookup <NAME OF LOOKUP>`


## SAVEDSEARCHES
This application contains the following saved searches:

* Delete Older TIDE data from `infoblox_tide`: TIDE data older than 24 hours will be deleted from `infoblox_tide`.
* Delete Older Dossier data from `infoblox_dossier`: Dossier data older than 24 hours will be deleted from `infoblox_dossier`.
* Get Infoblox SOC insights details: Collect Infoblox SOC Insights details data from the collected SOC insights. By default, this savedsearch will be disabled.

* **NOTE**: If User want to enable/disable Savedsearches
    1. If User wishes to enable or disable any existing savedsearches follow below steps.
    2. Click on setting > Searches, reports, and alerts
    3. Then select App as ˜Infoblox App For Splunk and type the name in the filter section And User will see that savedsearch.
    4. click on the Edit button, it will display the enable/disable button.
    5. All savedsearches will be disabled by default except index data to ingest to master lookup savedsearches.



## DATA MODEL
* The app consist of one data model "Infoblox". The acceleration for the data model is disabled by default. You can also enable the acceleration of the data model.
* Steps to enable/disable acceleration or change the acceleration period of data model:
    1. On Splunk's menu bar, Click on Settings -> Data models.
    2. From the list for Data models, Search for "Infoblox" data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
    3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    5. If acceleration is enabled, select the summary range to specify the acceleration period.
    6. To save acceleration changes click on the Save button.
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.

## MACROS
* **infoblox_index:**
    * This macro is used in all the infoblox dashboards that are populated on indexed data. Default value is  index IN ("main"). 
    * User can update the macro by following this steps:
        * On Splunk's menu bar, Click on Settings ->"Advanced search" -> "Search Macros".
        * Search "infoblox_index" macro
        * Click on the "infoblox_index" macro and mention the index name in the Definition where data is incoming. Please see the sample below.
            * index IN ("main" , "sample2")
        *   Click on the Save Button.

* **summariesonly:**
    * This macro is used in all the infoblox dashboards that are populated on indexed data. Default value is summariesonly=false. 
    * User can update the macro by following this steps:
        * On Splunk's menu bar, Click on Settings ->"Advanced search" -> "Search Macros".
        * Search "summariesonly" macro
        * Click on the "summariesonly" macro and update the the Definition of summariesonly that you want. Please see the sample below.
            * summariesonly=true
        *   Click on the Save Button.

## Alert Actions
This application contains the following alert actions:

* **infoblox_soc_insights_details**
    * Description : This alert action will collect SOC Insights details data.
    * Parameters :
        * assets: Collect SOC Insights Assets data.
        * indicators: Collect SOC Insights Indicators data.
        * events: Collect SOC Insights Events data.
        * comments: Collect SOC Insights Comments data.
        * index: Select the index in which the data should be collected.
        * global_account: Select the Infoblox account for which you want to collect data.

## CUSTOM COMMANDS
This application contains the following custom commands:

* **infobloxsocinsights**
    * Description : This command fetches the details of assets, indicators, events, and comments for the particular insight. 
    * Parameters :
        * insight_id : The id of insight for which details to be fetched.
        * type : The type of deatils to be fetched. i.e. indicators, assets or events
        * account_name : Provide configured Infoblox Account Name.
* **infobloxsocinsightsdetails**
    * Description : This command retrieves insight details data using the specified type and insight_id from the indexed data if available. If not found, it will fetch the data from the platform via an API call.
    * Parameters :
        * insight_id : The id of insight for which details to be fetched.
        * type : The type of details to be fetched. i.e. indicators, assets or events
        * account_name : Provide configured Infoblox Account Name.
* **infobloxdossierlookup**
    * Description: This command gives results of Dossier.
    * Parameters :
        * type="type"
        * target="target"
        * account_name="accountname"
* **infobloxipamlookup**
    * Description: This command gives results of ipam.
    * Parameters :
        * filter="filter"
        * account_name="accountname"
* **infobloxtidelookup**
    * Description: This command gives results of tide.
    * Parameters:
        * type="type"
        * value="value"
        * account_name="accountname"
* **infobloxnamedlist**
    * Description: This command gives results of named list.
    * Parameters:
        * named_list="Named List"
        * account_name="accountname"
* **infobloxblockallowtool**
    * Description: This command gives results of block allow ip/domain detail
    * Parameters:
        * action="action"
        * named_list="Named List"
        * value="value of IP/Domain"
        * description="Description"
        * account_name="accountname"

**NOTE**: Non-Admin users won't be able to run the custom commands.


## SEARCHES
* To see ingested data for Infoblox App For Splunk of collected data through Inputs tab, select the `Search` tab. Search `` index=* sourcetype=infobox:*``.
* To see Splunk CIM(Syslog) data for Infoblox App For Splunk, select the `Search` tab. Search `` index=* sourcetype=ib:*``.

## TROUBLESHOOTING
### General Checks
* To troubleshoot Infoblox App For Splunk, check `$SPLUNK_HOME/var/log/Splunk/ta_infoblox_*.log` or user can search `index="_internal" source=*ta_infoblox_*.log*` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_infoblox_*.log* ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* App icons are not showing up: The App does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.


### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled).
* Check `ta_infoblox*.log*` file for Infoblox App For Splunk data collection for any relevant error messages.

#### Custom Commands
* **NOTE**: Non-Admin users won't be able to run the custom commands. 

* infobloxsocinsights
    * Check `ta_infoblox_soc_insights_custom_command.log` file for further analysis.
* infobloxsocinsightsdetails
    * Check `ta_infoblox_soc_insights_details_custom_command.log` file for further analysis.
* infobloxipamlookup
    * Check `ta_infoblox_ipam_lookup_custom_command.log` file for further analysis.
* infobloxdossierlookup
    * Check `ta_infoblox_dossier_lookup_custom_command.log` file for further analysis.
* infobloxblockallowtool
    * Check `ta_infoblox_block_allow_tool_custom_command.log` file for further analysis.
* Infobloxnamedlist
    * Check `ta_infoblox_named_list_custom_command.log` file for further analysis.



### Dashboards
* Panel not populating:

1. Tools Dashboards
    * If the data is not populated in TIDE & Dossier Lookup panels, then ensure that the infobox_<NAME_OF_LOOKUP> lookup is filled.
    infobloxtidelookup
    * Check `ta_infoblox_tide_lookup_custom_command.log` file for further analysis.
    infobloxipamlookup
    * Check `ta_infoblox_ipam_lookup_custom_command.log` file for further analysis.
    infobloxdossierlookup
    * Check `ta_infoblox_dossier_lookup_custom_command.log` file for further analysis.
    infobloxblockallowtool
    * Check `ta_infoblox_block_allow_tool_custom_command.log` file for further analysis.
    DHCP Lease Lookup
    * If your panel is not populating, then ensure the index in the macro matches the data present in the index. (To open macro go to setting->Advanced search->Search Macros).
    * Check the percentage of acceleration in the data model. If the percentage is not 100%, not all data will load.  (To open data model go to setting->Data Models->Infoblox)

2.  Syslog Dashboards
    * If your panel is not populating, then ensure the index in the macro matches the data present in the index. (To open macro go to setting->Advanced search->Search Macros).
    * Check the percentage of acceleration in the data model. If the percentage is not 100%, not all data will load.  (To open data model go to setting->Data Models->Infoblox)

3. Threat Intelligence Overview
    * If your panel is not populating, then ensure the index in the macro matches the data present in the index. (To open macro go to setting->Advanced search->Search Macros).
    * Check the percentage of acceleration in the data model. If the percentage is not 100%, not all data will load.  (To open data model go to setting->Data Models->Infoblox)

4. SOC Insights Overview
    * If your panel is not populating, then ensure the index in the macro matches the data present in the index. (To open macro go to setting->Advanced search->Search Macros).
    * Check `ta_infoblox_soc_insights_details_custom_command.log` file for further analysis.
    * Check `ta_infoblox_soc_insights_custom_command.log` file for further analysis.
    * Check `ta_infoblox_named_list_custom_command.log` file for further analysis

## BINARY FILE DECLARATION

* md.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/

## SUPPORT
* Support Offered: Yes
* Support Details:
    * https://support.infoblox.com 

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/InfobloxAppForSplunk
* Remove $SPLUNK_HOME/var/log/Splunk/ta_infoblox_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

#### © 2025 Infoblox. All rights reserved.