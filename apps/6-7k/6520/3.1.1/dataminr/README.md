# Dataminr Pulse App for Splunk

## OVERVIEW
The Dataminr Pulse App for Splunk fetches Alerts from Dataminr Pulse platform, does Alerting and provides dashboards for visualization.

## REQUIREMENTS
* Splunk version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome and Firefox
* [Splunk Common Information Model (CIM)](https://splunkbase.splunk.com/app/1621)
* Dataminr Pulse account credentials

## RELEASE NOTES

### Version 3.1.1
* Refactored content generation for several dashboards to address possible injection vulnerabilities.

### Version 3.1.0
* Enhanced the ReGenAI modal for URL and IP data.

### Version 3.0.1
* Updated the App logo.
* Enhanced the ReGenAI modal.
* Updated the extraction of eventSource field to exclude the trailing period (".").

### Version: 3.0.0
* Added new input for v4 API.
* Added Malware Intelligence dashboard.
* Added Monitored Alerts dashboard.
* Enhanced CIM mapping.
* Updated the Digital and Third Party Risk dashboard into two separate dashboards: Digital Risk and Third Party Risk.
* Added Sector and Threat Actor Country filter in the dashboards.
* Added ReGenAI modal in 'Dataminr Alert Overview', 'Cyber Threat Overview', 'Malware Intelligence', 'Digital Risk', 'Third Party Risk', 'Vulnerability Intel', 'Malware Intelligence', 'Cyber-Physical Risk Intel' and 'Monitored Alerts' dashboards.

### Version: 2.1.3
* Updated multiline savedsearch.
* Updated HEC url creation for splunk cloud (victoria instance).

### Version: 2.1.2
* Enhanced Vulnerability Intelligence dashboard to accomodate the variations for Event Source : GreyNoise and Greynoise.

### Version: 2.1.1
* Fixed cloud failure by upgrading Splunk SDK version to 2.0.2.
* Updated internal logs.

### Version 2.1.0
* Fixed the Alerts in Close Proximity panel in Cyber-Physical Risk Intel dashboard to show location pin colours as per the alert severity and show the count of distinct Alerts for each alert severity on hovering.
* Updated the IOC Overview dashboard panels.
* Updated the saved search dataminr_alert_vulnerable_ips to accept ipv6 values.

### Version 2.0.0
* Rebuilt the app using Splunk UCC framework.
* Refactored the code for Splunk UCC.
* Added Support for Data collection via Dataminr webhooks.
* Added Digital and Third Party Risk and Vulnerability Intel dashboards.
* Added new filters to existing dashboards.
* Added CIM Mapping.
* Added searches to update Threat Intelligence and create Notable Events in Splunk Enterprise Security.

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of Search Head and Forwarder.

## INSTALLATION OF APP
Dataminr Pulse App for Splunk can be installed through UI as mentioned below or extract .spl file directly into $SPLUNK_HOME/etc/apps/ folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.  
2. Click `Install app from file`.  
3. Click `Choose file` and select the Dataminr Pulse App for Splunk installation file.  
4. Click on `Upload`.
5. Restart the Splunk instance if prompted.

    **OR** 

1. Log in to Splunk Web and navigate to Apps > Manage Apps.  
2. Click `Browse more apps`. The Splunk App Browser opens.
3. Search for `Dataminr Pulse for Splunk Enterprise and Splunk Cloud` and click `install`.
4. Enter your credentials as prompted
5. click `Agree and install`. This confirms that you accept the app license terms and installs the app on your deployment.
6. Restart the Splunk instance if prompted.


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This app can be set up in two ways:

1. Standalone Mode
    * Install the Dataminr Pulse App for Splunk.
    * Configure an account and create modular input.
2. Distributed Environment
    * Install the Dataminr Pulse App for Splunk on the Search Head and On-Premise IDM/Heavy Forwarder.
    * Configure the modular Inputs only on the Forwarder .
    * Configure macros, savedsearches only on the Search Head.

Note that for the distributed environment, only indexes of the Forwarder would be shown in the input configuration page.

## INSTALLATION IN SPLUNK CLOUD

* Same as an on-premise setup.

## UPGRADATION OF APP

Follow the below steps to upgrade the app.

1. Download the required version from Splunkbase and can upload it into Splunk manually.
    * Navigate to Apps > Manage Apps and click on the **Install app from file**.
    * Click on **Choose File** and select the Dataminr Pulse App for Splunk installation file.
    * Check the Upgrade app checkbox and click on Upload.
    * Restart the Splunk instance if prompted.

    **OR**

2. Upgrade the app using Splunk's web UI.
    * Navigate to Apps > Manage Apps.
    * In the list, locate **Dataminr Pulse**. In the **Version** column, you will see the option to **Update to <latest_version>**.
    * Click on **Update to <latest_version>**.
    * Agree to the terms and conditions and click on **Accept and continue**.
    * Enter your credentials as prompted.
    * Restart the Splunk instance if prompted.

## Upgrading to version 3.0.2 from 3.1.0

* To Upgrade follow the steps mentioned in **UPGRADATION OF APP** section.
* After that no additional steps are required.

## Upgrading to version 3.0.1 from 3.0.0

* To Upgrade follow the steps mentioned in **UPGRADATION OF APP** section.
* After that no additional steps are required.

## Upgrading to version 3.0.0 from 2.1.3

* To Upgrade follow the steps mentioned in **UPGRADATION OF APP** section.
* After upgrading to v3.0.0, you need to Rebuild the Datamodels. Follow steps from **REBUILDING DATA MODEL** section.
* If you have made local changes in a previous version, please ensure your event types are updated as described below. To verify or update your event types: Go to Settings > Event Types in Splunk. Search for each of the event types listed below.
If your data is stored in a different index, update the dataminr_index event type with the correct index name(s).
* Required Event Types and Their Definitions:

    - dataminr_index: index=main
    - dataminr_alerts: eventtype=dataminr_index source IN ("dataminr", "dataminr_v4")
    - dataminr_cyber_alerts: eventtype=dataminr_index source IN ("dataminr", "dataminr_v4") lists_subtype="CYBER"
    - dataminr_malware_data: eventtype=dataminr_index source IN ("dataminr", "dataminr_v4") metadata.cyber.malwares{}="*"
    - dataminr_vulnerabilities_data: eventtype=dataminr_index source IN ("dataminr", "dataminr_v4") metadata.cyber.vulnerabilities{}.id="*"
    - dataminr_intelAgent_malware_data: eventtype=dataminr_index source="dataminr_v4" "intelAgents{}.discoveredEntities{}.type"=malware
    - dataminr_intelAgent_vulnerability_data: eventtype=dataminr_index source="dataminr_v4" "intelAgents{}.discoveredEntities{}.type"=vulnerability
    - dataminr_intelAgent_threatActor_data: eventtype=dataminr_index source="dataminr_v4" "intelAgents{}.discoveredEntities{}.type"=threatActor

Note: If you use a different index, make sure to replace main in the dataminr_index event type with your actual index name(s).

## Upgrading to version 2.1.3 from 2.1.2

* To Upgrade follow the steps mentioned in **UPGRADATION OF APP** section.
* After upgrading to v2.1.0, you need to Rebuild the Datamodels. Follow steps from **REBUILDING DATA MODEL** section.

## Upgrading to version 2.1.2 from 2.1.1

* To Upgrade follow the steps mentioned in **UPGRADATION OF APP** section.
* After that no additional steps required.

## Upgrading to version 2.1.1 from 2.1.0

* To Upgrade follow the steps mentioned in **UPGRADATION OF APP** section.
* After that no additional steps required.

## Upgrading to version 2.1.0 from 2.0.0

* To Upgrade follow the steps mentioned in **UPGRADATION OF APP** section.
* After upgrading to v2.1.0, you need to Rebuild the Datamodels. Follow steps from **REBUILDING DATA MODEL** section.

## Upgrading to version 2.0.0 from 1.2.3

* Before upgrading the app, Log in to Splunk Web UI and Navigate to Settings > Data Inputs > Dataminr Splunk Connector 
* Delete each of the configured Dataminr Splunk Connector Inputs.
* Navigate to Apps > Dataminr Pulse > Setup > Dataminr Secrets and Delete all the Dataminr account client secrets configured.
* Now, follow the steps mentioned in **UPGRADATION OF APP** section.
* After upgrading to v2.0.0, Re-configure the Accounts and Modular Inputs. Follow steps from **CONFIGURATION OF APP** section.
* Also, you need to Rebuild Datamodel after upgrading the app. Follow steps from **REBUILDING DATA MODEL** section.


## CONFIGURATION OF APP
Configure Dataminr Pulse App for Splunk:

* Login to Splunk Web UI.
* Navigate to Apps > Dataminr Pulse

### Account
To configure the Account

1. Navigate to the `Setup`> `Account`.
2. Click on the `Account` tab.
3. Click on `Add` button on the right corner.
3. Provide your Dataminr Pulse credentials and Click on `Save`.

| Dataminr Pulse Account parameters  | Mandatory or Optional | Description                                     |
| ---------------------------------- | --------------------- | ----------------------------------------------- |
| Account Name                       | Mandatory             | Unique Name for the credentials being configured|
| API Version                        | Mandatory             | API Version of Dataminr Pulse             |
| Client ID                          | Mandatory             | Client Id of Dataminr Pulse Account             |
| Client Secret                      | Mandatory             | Client Secret of the Dataminr Pulse account     |

### Proxy
To configure the Proxy

1. Navigate to the `Setup`> `Account`.
2. Click on the `Proxy` tab.
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters         |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy                                                      |
|    Proxy Type            |     Mandatory            |  Select proxy type that you want to use from the dropdown (supports HTTP proxy only)|
|    Proxy Host            |     Mandatory            |  Host or IP of the proxy server                                                        |
|    Proxy Port            |     Mandatory            |  Port for proxy server                                                                 |
|  Proxy Username          |     Optional             |  Username of the proxy server |
|  Proxy Password          |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging

1. Navigate to the `Setup`> `Account`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`.

### Inputs
To configure the Inputs

1. Navigate to the `Setup`> `Inputs`.
2. Click on `Create New Input`, one dropdown will open with options:
    * `Dataminr API v4`
    * `Dataminr API v3`
    * `Dataminr Webhook`
3. Select a option and pop-up will open accordingly.
4. Provide the input related information and click on `Add` to start the data collection.

**Dataminr API v4**

Field descriptions are as below:

| Input Parameter           |  Mandatory or Optional | Desciption                                                   |
| --------------------------| ---------------------- | ------------------------------------------------------------ |
| Name                      | Mandatory              | Unique name identify Input                                   |
| Interval                  | Mandatory              | Time interval of input in minutes. Default: 5 mins           |
| Index                     | Mandatory              | Index in which you want to store your data                   |
| Dataminr Account          | Mandatory              | Dataminr Account configured to use for data collection       |
| Alert Type                | Mandatory              | Alert Types to collect. Default: All                         |
| WatchLists                | Mandatory              | Watchlists from which to collect Alerts. Default: All                      |

**Dataminr API v3**

Field descriptions are as below:

| Input Parameter           |  Mandatory or Optional | Desciption                                                   |
| --------------------------| ---------------------- | ------------------------------------------------------------ |
| Name                      | Mandatory              | Unique name identify Input                                   |
| Interval                  | Mandatory              | Time interval of input in minutes. Default: 5 mins           |
| Index                     | Mandatory              | Index in which you want to store your data                   |
| Dataminr Account          | Mandatory              | Dataminr Account configured to use for data collection       |
| Alert Type                | Mandatory              | Alert Types to collect. Default: All                         |
| WatchLists                | Mandatory              | Watchlists from which to collect Alerts. Default: All                      |

**Dataminr Webhook**

Before configuring the Dataminr Webhook, you need to configure a HTTP event Collector(HEC) to collect the data received via the Dataminr Webhook.
To Configure HEC

1. Navigate to `Settings` > `Data inputs` > `HTTP Event Collector`
2. Click on `New Token` button.
3. In the Token configuration page, provide the following details and click `Next`

| Input Parameter           |  Mandatory or Optional | Desciption                                                   |
| --------------------------| ---------------------- | ------------------------------------------------------------ |
| Name                      | Mandatory              | Unique name identify the HEC token created                   |
| Source name override?     | Mandatory              | Add the value "dataminr" to specify the source of data       |
| Description               | Optional               | Text to provide description for this HEC token              |

4. In the Input settings page, select the Source type option "Select".
5. In the `Select Source Type` dropdown that appears below, select "json"
6. In the `Index` section click on the index to collect data from the Select Allowed Indexes sub-section. Note that the same index is set as the `Default Index` too.
7. Click on `Review`
8. Verify the configured HEC details and click `Submit.`
9. From the Token Successfully created page, copy the Token Value.

To configure Dataminr Webhook, Field descriptions are as below:

| Input Parameter           |  Mandatory or Optional | Desciption                                                   |
| --------------------------| ---------------------- | ------------------------------------------------------------ |
| Name                      | Mandatory              | Unique name identify Input                                   |
| Dataminr Account          | Mandatory              | Dataminr Account configured to use for data collection       |
| Alert Type                | Mandatory              | Alert Types to collect. Default: All                         |
| WatchLists                | Mandatory              | Watchlists from which to collect Alerts. Default: All                      |
| HEC Token                 | Mandatory              | HEC Token created for Webhook URL                            |

### Dashboards Configuration

**1. IOC Dashboard**  

* The `dataminr_customer_domains.csv` lookup is used in the IOC dashboard. Although it is optional, It contains important customer domains and urls which can be used in determining the Affected URLs/Domains.

* This lookup can be populated by using a Splunk query to list the intended customer URL domains and corresponding customer URLs under the headers "url_domain" and "url," respectively.

**2. Cyber-Physical Risk Dashboard**

* `dataminr_asset_close_proximity_alerting.csv` lookup is used in Cyber-Physical risk  Dashboard. It contains important Customer Asset locations which is mandatory.

* This lookup can be populated using Splunk query to list the intended Customer Asset Name, Asset Type, Asset Description, Asset Latitude, Asset Longitude , Alerting radius under the headers "asset_name","asset_type","asset_description","asset_lat","asset_long","alerting_distance_miles" respectively.

Examples of these csv lookup files can be found in `lookups_bak` folder in the app package.

User can update the lookup table file manually [here](https://docs.splunk.com/Documentation/Splunk/9.3.1/Knowledge/Usefieldlookupstoaddinformationtoyourevents#Upload_the_lookup_table_file) or download the [Splunk Lookup Editor app](https://splunkbase.splunk.com/app/1724) to modify it.


## SEARCH
* To see ingested data for Dataminr API, select the `Search` tab. Search 
    - For v3: ``index=<data_collection_index> source=dataminr sourcetype=json host=dataminr``.
    - For v4: ``index=<data_collection_index> source=dataminr_v4 sourcetype=json host=dataminr``.
* To see ingested data for Dataminr Webhook, select the `Search` tab. Search ``index=<data_collection_index> source=dataminr sourcetype=json host!=dataminr``.

## EVENT TYPES
The app has the following event types:

1. **dataminr_index**: Indexes for Dataminr data
2. **dataminr_alerts**: Contains All Dataminr Alerts collected
3. **dataminr_cyber_alerts:** Contains All Dataminr cyber Alerts
4. **dataminr_malware_data**: Contains All Dataminr malwares Alerts
5. **dataminr_vulnerabilities_data**: Contains All Dataminr Vulnerabilities Alerts
6. **dataminr_intelAgent_malware_data**: Contains All Dataminr IntelAgent malwares Alerts
7. **dataminr_intelAgent_vulnerability_data**: Contains All Dataminr IntelAgent vulnerabilities Alerts
8. **dataminr_intelAgent_threatActor_data**: Contains All Dataminr IntelAgent threatActors Alerts

## EVENT TYPES CONFIGURATION
To configure Event Types

1. Navigate to `Settings` > `Event Types`.
2. Search for following event types :
    1. dataminr_index
    2. dataminr_alerts
    3. dataminr_cyber_alerts
    4. dataminr_malware_data
    5. dataminr_vulnerabilities_data
    6. dataminr_intelAgent_malware_data
    7. dataminr_intelAgent_vulnerability_data
    8. dataminr_intelAgent_threatActor_data
3. Click on each of the above event types to update it.
4. To update the indexes, modify the `dataminr_index` event type with something like `index IN ("index1", "index2")`, then click on Save. This is the index setup for the Dataminr inputs

## DATA MODEL
* The app consists of two data models `Dataminr` and `DataminrVulnerabilities`.
* The acceleration for these data models is disabled by default.
* Please enable the data model acceleration for the dashboards to work.
* The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.
* Major portion of the dashboard panels are populated using data model queries and real-time search doesn't work with the data model, all the real-time search filters are disabled.

## DATA MODEL CONFIGURATION
* The Data Model used in this application is not accelerated.
* Admin should manually accelerate the Data Model.
* The recommended acceleration period is 1 Month. Admin can enable/disable acceleration or change the acceleration period by the following steps.
    1. On Splunk menu bar, Click on Settings > Data models
    2. From the list for Data models, click Edit in the "Action" column of the row for the **Dataminr** or **DataminrVulnerabilities** Data model.
    3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    5. If acceleration is enabled, select the summary range to specify the acceleration period.
    6. To save acceleration changes click on the Save button.

## REBUILDING DATA MODEL
In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:

1. On the Splunk menu bar, Click on Settings > Data models.
2. From the list for Data models, expand the row by clicking the ">" arrow in the first column of the row for the **Dataminr** and/or **DataminrVulnerabilities** Data model. This will display extra Data Model information in the "Acceleration" section.
3. From the "Acceleration" section click on the "Rebuild" link.
4. Monitor the status of the "Rebuild" in the field "Status" of the "Acceleration" section. Reload the page to get the latest rebuild status.


## MACROS
The app has the following macros:

1. **dataminr_dm_summariesonly**: Specifies if only the search data summarized by Dataminr datamodel will be used in the queries in dashboards. Default: true
2. **dataminr_vulnerabilities_dm_summariesonly**: Specifies if only the search data summarized by DataminrVulnerabilities datamodel will be used in the queries in dashboards. Default: true
3. **customer_dm_summariesonly**: Specifies if only the search data summarized by datamodel from other sources(not Dataminr Pulse App for Splunk) will be used in the queries in Dashboards. This is used to populate the `Affected  Ips`, `Affected Hashes`, `Affected Domains`, `Affected Malwares` panels of `IOC Overview` dashboard
4. **important_location_csv_lookup**: Lookup table name storing important customer locations and thresholds distance.
5. **customer_domains_csv_lookup**: Lookup table name storing customers domain details.


## MACROS CONFIGURATION
To configure macros

1. Navigate to `Settings` > `Advanced Search` > `Search macro`
2. Search for `customer_dm_summariesonly`
3. In the form that opens Update the "summariesonly=false" to "summariesonly=true" if required.

## SAVEDSEARCHES
This application contains the following saved searches

* **dataminr_alert_vulnerable_ips** - Finds vulnerable IP found in last 60 minutes and merge the list with 30day master list
* **dataminr_alert_vulnerable_hashes** - Finds vulnerable Hashes found in last 60 minutes and merge the list with 30day master list
* **datamin_alert_vulnerable_domains** - Finds vulnerable domains found in last 60 minutes and merge the list with 30day master list
* **dataminr_alert_vulnerable_malwares** - Finds Vulnerable Malwares found in last 60 minutes and merge the list with 30day master list

## ALERTS  
This application contains the following alerts

* **Dataminr_matched_vulnerable_ip_address_with_DMA** - Matches IP addresses from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and appropriate data models accelerated. Default: Disabled
* **Dataminr_matched_vulnerable_hashes_with_DMA** - Matches Hashes from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and appropriate data models accelerated. Default: Disabled
* **Dataminr_matched_vulnerable_domains_with_DMA** - Matches domains from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and appropriate data models accelerated. Default: Disabled
* **Dataminr_matched_vulnerable_malware_with_DMA** - Matches malware from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and appropriate data models accelerated. Default: Disabled
* **Dataminr_matched_vulnerable_ip_address** - Matches IP addresses from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and works with non-accelerated data. Default: Disabled
* **Dataminr_matched_vulnerable_hashes** - Matches hashes from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and works with non-accelerated data. Default: Disabled
* **Dataminr_matched_vulnerable_domains** - Matches domains from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and works with non-accelerated data. Default: Disabled
* **Dataminr_matched_vulnerable_malware** - Matches malware from Dataminr alerts to Customer data and sends alerts when a match is found. Requires Customer Data to be CIM compliant and works with non-accelerated data. Default: Disabled
* **Dataminr_close_proximity_alerts** - Dataminr alerts within threshold miles from important customer locations.
* **Threat - Dataminr File Threat Intel update - Rule** - Update the Splunk Enterprise Security File Threat intelligence with Datamir data from past 30 days. Default: Disabled 
* **Threat - Dataminr Domain Threat Intel update - Rule** - Update the Splunk Enterprise Security Domain Threat intelligence with Datamir data from past 30 days Default: Disabled 
* **Threat - Dataminr IP Threat Intel update - Rule** - Update the Splunk Enterprise Security Ip Threat intelligence with Datamir data from past 30 days. Default: Disabled 
* **Threat - Dataminr remove old IP and Domain Intel - Rule** - Remove IPs and Domains older than 30 days from source Dataminr from Splunk Enterprise Security IP Threat Intel. Default: Disabled 
* **Threat - Dataminr remove old File Intel - Rule** - Remove File Hashes older than 30 days from source Dataminr from Splunk Enterprise Security File Threat Intel. Default: Disabled 
* **Network - Dataminr Domain based Notable events - Rule** - Generate Notable Events for new Domain sightings for customer data with Dataminr. Requires Customer Data to be CIM compliant. Default: Disabled
* **Network - Dataminr IP based Notable events - Rule** - Generate Notable Events for new IP sightings for customer data with Dataminr. Default: Disabled
* **Endpoint - Dataminr File based Notable events - Rule** - Generate Notable Events for new File Hash sightings for customer data with Dataminr. Default: Disabled

## ALERTS CONFIGURATION
To enable the required alerts

1. Navigate to `Settings` > `Searches, reports, and alerts` 
2. From the list of Alerts, identify the required Alert.
3. Click corresponding `Edit` > `Enable` option in the `Actions` column.
4. Click `Enable` button in the pop-up to confirm.

To edit Correlation searches generating Notable events

1. Navigate to `Settings` > `Searches, reports, and alerts` 
2. Search for `Network - Dataminr Domain based Notable events - Rule`, `Network - Dataminr IP based Notable events - Rule`, `Dataminr File based Notable events - Rule`
3. Click the search name.
4. In the form update the Search as required and click on `Save`.

**Note** 

1. If Splunk Enterprise Security is installed, you can enable following Alerts to Enrich the Enterprise Security Threat Intelligence with Dataminr Data.
    1. Threat - Dataminr File Threat Intel update - Rule
    2. Threat - Dataminr IP Threat Intel update - Rule
    3. Threat - Dataminr Domain Threat Intel update - Rule
    4. Threat - Dataminr remove old IP and Domain Intel - Rule
    5. Threat - Dataminr remove old File Intel - Rule

2. You can also edit the following Correlation searches to generate Notable Events on Splunk Enterprise Security.
    1. Network - Dataminr Domain based Notable events - Rule
    2. Network - Dataminr IP based Notable events - Rule
    3. Endpoint - Dataminr File based Notable events - Rule

## DASHBOARDS
The app contains the following dashboards

1. **Dataminr Alert Overview**: Overview of alerts from your Dataminr Pulse watchlists.
2. **Cyber Threat Overview**: Overview of cyber-related Dataminr alerts by category.
3. **IOC Overview**: Shows other events in Splunk matching Dataminr IOCs (IPs, file hashes, domains, and malware).
4. **Malware Intelligence**: Overview of Malware related Dataminr alerts.
5. **Dataminr Alerts Drilldown**: An overview of your Dataminr alerts stored in Splunk.
6. **Digital Risk**: Overview of Dataminr alerts about digital risk.
7. **Third Party Risk**: Overview of Dataminr alerts about third party risk.
8. **Vulnerability Intel**: Overview of Dataminr alerts about vulnerabilities.
9. **Cyber-Physical Risk Intel**: Shows Dataminr alerts in close proximity of customer-defined important locations.
10. **Monitored Alerts**: Overview of Dataminr alerts that are being monitored.

### ReGenAI Modal
- The ReGenAI modal provides a comprehensive view of the alert, including its summary, key entities and assessments, impacted assets, metadata, related media, locations, timeline details, in-depth threat intelligence.
    * Users can open the modal by clicking on a row marked with the ✨ icon.
    * Inside the modal, there’s a Monitor button to start monitoring that alert.
    * Once monitored, the alert will appear in the Monitored Alerts dashboard.
    * Users can stop monitoring at any time by clicking the Stop Monitor button in the Monitored Alerts dashboard.

## Binary File Declaration

* lib/charset_normalizer/md.cpython-37m-x86_64-linux-gnu.soin this integration is required for charset_normalizer library. It is added by the splunk-add-on-ucc-framework used for creating the integration. Repository Link: https://github.com/Ousret/charset_normalizer

## TROUBLESHOOTING
* To troubleshoot Dataminr Pulse App for Splunk, check $SPLUNK_HOME/var/log/splunk/dataminr*.log or user can search `index="_internal" source=*dataminr*.log` query to see all the logs on UI. Also, user can use `index="_internal" source=*dataminr*.log ERROR` query to see ERROR logs on the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/splunk/` directory. 
* If data collection is not working then ensure that the internet is active where a proxy is configured and also ensure that the kvstore is enabled.
* When creating Dataminr Webhook input, If error occurs, ensure that the Splunk server name value under `Settings` > `Server Settings` > `General Settings` is set to `Hostname / Ip` value that is publically reachable & accessible. Also make sure that the certificates used by the Splunk HEC utilises the above mentioned server name.
* If Dataminr Webhook Input is still not working, Navigate to `Settings` > `HTTP Event Collector`. Ensure that the token used to configure the Dataminr Webhook input is Enabled. If not, click on the corresponding `Enable` option in the Actions Column. If the Enable/Disable button is disabled, Click on Global Settings and select All Tokens to Enable.

## Known Issues
* If any configured account details are updated, it is recommended to create a new input using the updated account instead of editing the existing input.
* When you load the "Vulnerability Intel" dashboard for the first time, you may encounter error: "Search was not dispatched. To adjust search displatch settings, edit the Dashboard XML". If you encounter the above error , reloading the page will remove the error.
* For large events if all the fields from data are not getting extracted, create limits.conf and add following stanza to the limits.conf under $SPLUNK_HOME/etc/apps/dataminr/default
```
[kv]
limit = <max number of key - value pairs that can be extracted from data> 
maxchars = <max length of alert>
[spath]
extraction_cutoff = <max size of the alert>
```
where the default system values are 
* extraction_cutoff = 5000
* limit = 100
* maxchars = 10240

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/Dataminr
* Remove $SPLUNK_HOME/var/log/splunk/dataminr*.log*
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Details:
    - Email: support@dataminr.com

## COPYRIGHT
* (c) 2026 Dataminr. All rights reserved