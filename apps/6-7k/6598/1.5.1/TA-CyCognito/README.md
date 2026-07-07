# CyCognito Add-on for Splunk


## This is an add-on powered by the Splunk Add-on builder

## OVERVIEW

CyCognito Add-on for Splunk is a Splunk Addon which collects assets and issues from the CyCognito platform.

- Author - CyCognito, Ltd.

- Version - 1.5.1

- Build - 1

## Compatibility Matrix for CyCognito
* Browser: Google Chrome, Mozilla Firefox
* OS: Platform independent
* Splunk Enterprise version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Supported Splunk ES version: 7.0.x
* Supported CyCognito Platform: CyCognito Platform Release Date: 2023-07-06 
* Supported Splunk Deployment: Cloud, Standalone, and Distributed Deployment 

## RELEASE NOTES

### Version 1.5.1
* Bumped the minimum required Python version to 3.13 as per Splunk standards.

### Version 1.5.0
* Migrated to Splunk add-on builder v4.5.1

### Version 1.4.0
* Migrated to Splunk add-on builder v4.2.0

### Version 1.3.0
* Added support for collecting 'Resolved issues' and 'Removed assets' data.
* Migrated to Splunk add-on builder v4.1.4

### Version 1.2.0
* Modified field extractions.

### Version 1.1.0
* Migrated to Splunk add-on builder v4.1.3

### Version 1.0.0
* Added support for data collection of CyCognito Issues and Assets.
* Added Risk based Alerting correlation searches to identify risky events of CyCognito Issues and Assets.


## Recommended System Configuration

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-On can be set up in two ways:


1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Forwarder for this setup.

2) Distributed Environment: Install Add-on on search head and Forwarder (for REST API).

* Add-on resides on search head machine need not require any configuration here.

* Add-on needs to be installed and configured on the Forwarder system and search head.

* Execute the following command on Heavy forwarder to forward the collected data to the indexer.
  /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
  
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).

* Add-on needs to be installed on search head for CIM mapping.

## INSTALLATION
 
This TA can be installed through UI using the following steps.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click the `Install app from file`.
3. Click `Choose File` and select the `TA-CyCognito` installation file.
4. Click on `Upload`.
5. Once the installation is complete, restart Splunk. 

as after Splunkbase upload this will also work.
* Directly from the Find More Apps section provided in Splunk Home Dashboard.


## UPGRADE

### GENERAL UPGRADE STEPS:
* Log in to Splunk Web and navigate to Apps -> Manage Apps.
* Click `Install app from file`.
* Click `Choose File` and select the `TA-CyCognito` for Splunk installation file.
* Check the Upgrade checkbox.
* Click on `Upload`.
* Restart Splunk.

### Upgrade to V1.5.1
Follow the below steps to upgrade the Add-on to v1.5.1

* Disable the existing inputs.
* Follow the General upgrade steps section.
* Navigate to the CyCognito Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

### Upgrade to V1.5.0
Follow the below steps to upgrade the Add-on to v1.5.0

* Disable the existing inputs.
* Follow the General upgrade steps section.
* Navigate to the CyCognito Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.


## APPLICATION SETUP

### Configuration 

Configure the CyCognito Add-on through the UI. These configurations will be used while collecting data from the CyCognito platform. Configuration should be divided into three components:

- CyCognito Account Page

- Proxy Page

- Logging Page

#### CyCognito Account Page

After Installing 

1. Click on the `Configuration` tab next to the `Inputs` tab.
2. Enter your CyCognito Account details and click on `Save`.


| Input Parameter                | Mandatory or Optional | Description                                                                                                                                                                                                       |
| -------------------------------| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Account Name                   | Mandatory             | Enter a unique name for this account.                                                                                                                                                                              |
| Platform URL                   | Mandatory             | Enter the CyCognito server address. E.g. "api.platform.cycognito.com".                                                                                                                                                            |
| API Token                      | Mandatory             | Enter the API token.                              


#### Proxy Page

1. If you want to add proxy settings, select the `Proxy` tab next to the `CyCognito Account`.
2. Enter your proxy credentials and click `Save`. 

| Proxy Parameter       | Mandatory or Optional | Description                                                                                     |
| --------------------- | --------------------- | ----------------------------------------------------------------------------------------------- |
| Enable                | Optional              | Checkbox to enable or disable proxy support.                                                     |
| Proxy Type            | Mandatory only if Proxy is Enabled. | Select the proxy type that you want to use from the dropdown. The TA supports the `http` `socks4` & `sock5`proxy.                       |
| Host                  | Mandatory only if Proxy is Enabled. | Host or IP of the proxy server. Mandatory if `Proxy` is Enabled.                    |
| Port                  | Mandatory only if Proxy is Enabled. | Port for proxy server. Mandatory if `Proxy` is Enabled.                             |
| Username              | Mandatory in the case when the user has entered `Password` and Proxy is Enabled. | Username of the proxy server.                              |
| Password              | Mandatory in the case when the user has entered `Username` and Proxy is Enabled. | Password of the proxy server.                              |

#### Logging

1. To Configure logging, Select `Logging`.
2. Select the desired log level from the dropdown and click on `Save`.
                                   
### Inputs

1. Go to the apps list and open CyCognito Add-on for Splunk. From the inputs screen, click on `Create New Input`.
2. If you want to add Assets input then click on `CyCognito Assets Input`.


| Input Parameter             | Mandatory or Optional | Description                                                                                                                                                                                                                                                                                               |
| --------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                        | Mandatory             | Enter a unique name for the data input.                                                                                                                                                                                                                                                              |
| CyCognito Account           | Mandatory             | Select the CyCognito account among the list.                                                                                                                                                                                                                                                                        |
| Asset Types                 | Mandatory             | Multiselect options. Select the asset types(“Web Application, ”IP Range”, “IP Address, ”Domain”, “Certificate")                                                                                                                                                                                                                   |
| Interval                    | Mandatory             | Time interval of input in seconds and must be greater than or equal to 86400.                                                                                                                                                                                                                       |
| Index                       | Mandatory             | Index to which you want to send data. It refers to the index name in indexes.conf.                                                                                                                                                                                                                        |

3. If you want to add Issues input then click on `CyCognito Issues Input`

| Input Parameter             | Mandatory or Optional | Description                                                                                                                                                                                                                                                                                               |
| --------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                        | Mandatory             | Enter a unique name for the data input.                                                                                                                                                                                                                                                             |
| CyCognito Account           | Mandatory             | Select your account among the list.                                                                                                                                                                                                                                                                        |
| Interval                    | Mandatory             | Time interval of input in seconds and must be greater than or equal to 86400(1 Day).                                                                                                                                                                                                                       |
| Index                       | Mandatory             | Index to which you want to send data. It refers to the index name in indexes.conf.                                                                                                                                                                                                                        |

## Search

To see data logged by `CyCognito`, select the `Search` tab and click on `Data Summary`. Follow the given sourcetypes for data searching.

| Sourcetype                            | Data Type | Description                                                                                                                                                                                                                                                                                               |
| --------------------------------------| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| cycognito:issues                      | issues             | Collect data for CyCognito Issues                                                                                                                                                                                                                                                            |
| cycognito:assets:webapp      | webapp             | Collect data for CyCognito Web Application Assets                                                                                                                                                                                                                                                                      |
| cycognito:assets:iprange             | iprange             | Collect data for CyCognito IP Range Assets                                                                                                                                                                                                                       |
| cycognito:assets:ip           | ip             | Collect data for CyCognito IP Address Assets                                                                                                                                                                                                                       |
| cycognito:assets:domain               | domain             | Collect data for CyCognito Domain Assets                                                                                                                                                                                                                                                                        |
| cycognito:assets:cert          | cert             | Collect data for CyCognito Certificate Assets                                                                                                                                                                                                                       |

You can also enter search parameters in the search box to filter events.

## Macros

### `get_cycognito_index`

- It is used for searching CyCognito events from the index.
- By default, it will search from `main` index
- To improve the performance of searches using this macro, update this macro to only search in indices where CyCognito data is collected. Follow the below steps for updating macro.
If the user has selected a default index (Note: By default, Splunk considers only IN (main) index as default index) in the "Data Input" configuration during CyCognito Add-on for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in the "Data Input" configuration, then perform the following steps:
	1. Go to "Settings" > "Advanced search" > "Search macros".
	2. Select "CyCognito Add-on for Splunk" in the "App" context dropdown.
	3. Click on get_cycognito_index macro from the shown table.
	4. In the macro definition default value will be index IN (main). Update the definition with the index you used for data collection and save the configurations. For example: index="<your_index_name>".

## Risk Based Analysis - Correlation Savedsearch Configuration
This application contains the following Correlation savedsearches

* **Threat - CyCognito Assets Risk Alert - Rule** - This correlation search is used to generate risky events for those assets which are having D or F security grade. This search will run every 24 hours and will collect the risky events in the `risk` index.

* **Threat - CyCognito Issues Risk Alert - Rule** - This correlation search is used to generate risky events for those issues which are having high or critical severity. This search will run every 24 hours and will collect the risky events in the `risk` index.

Note - This correlation searches are using `get_cycognito_index` macro. Make sure that macro is configured properly.

### To change the configuration of Correlation Savedsearch

1. Open `Enterprise Security App`
2. Go to `Configure` -> `Content` -> `Content Management Dashboard`
3. Select `CyCognito Add-on for Splunk` in the `App` dropdown and Correlation Search in the Type.
4. To `Enable/Disable` the Correlation savedsearches, Click on the respective button in the `Actions` column of the table.
5. To change the detailed configuration of a specific correlation search, click on the name of the Savedsearch for which you want to change the configuration
6. In edit form, the `Time Range` section
	* Updating `Cron Schedule` changes how frequently saved search should run.
    * Updating `Earliest Time` changes how far to look for events in the past for matching.
7. In edit form, the `Throttling` section
	* Updating `Window duration` will prevent creating risky events in provided window duration if the same type of event matches. This will help in changing the suppression feature.
8. In the Adaptive Response Actions,  Risk Modifiers and Threat Objects can be added by clicking on the Add Risk Modifier and Add Threat Object respectively.

Note:-

* `Earliest Time` should have a larger time range than the `Cron Schedule` interval to avoid missing any Splunk events.
* Any update to correlation savedsearch will clear the suppression data for existing risk alerts so risk alerts can be duplicated for provided `Earliest Time`.
* `Threat - CyCognito Assets Risk Alert - Rule` and `Threat - CyCognito Issues Risk Alert - Rule` Correlation Searches are part of Add-on

## Risk Analysis Dashboard

1. Navigate to Splunk `Enterprise Security App`> Security Intelligence dropdown
2. Select `Risk Analysis` dashboard.
3. Select the relevant Source, Risk Object Type and Risk Object and Submit it.
4. Select the relevant time range from the Time filter and Submit it.
5. In the bottom portion, all the panels will be displayed.


## TROUBLESHOOTING

### General Checks

* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.
* Check `$SPLUNK_HOME/var/log/splunk/splunkd.log` and `$SPLUNK_HOME/var/log/splunk/ta_cycognito_*.log` log files.
* Check $SPLUNK_HOME/var/log/Splunk/<ta-log-name-prefix>*.log or user can search `index="_internal" source=*ta_cycognito_*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_cycognito_*.log ERROR` query to see ERROR logs in the Splunk UI.
* To get the detailed logs, in the Splunk UI, navigate to `CyCognito Add-on for Splunk`. Click on `Configuration` and go to the `Logging` tab. Select the Log level to DEBUG.
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled).
* Make sure if you are using the custom index, then check that `get_cycognito_index` macro needs to be updated.

### If data is not getting collected in Splunk Index:

* Data collection logs for particular assets are in `ta_cycognito_<asset_name>.log`. 
* Data collection logs for particular issues are in `ta_cycognito_<issues_name>.log`.
* Check that you have selected correct sourcetype.
* Make sure that API Token which you have entered while configuring Account is not expired.
* Make sure that splunk restart or disabling of input action should not be performed while input (data collection) is running. Error occur when data collection, is in progress and Splunk is restarted, Input disabled, or in case of any kind of error from API.
* Try increase truncate size for larger events from $SPLUNK_HOME/etc/apps/TA-CyCognito/local/props.conf file
	* Update TRUNCATE = <integer\>
	* Default: 9999999
* If an event is not getting extracted properly, then we need to add $SPLUNK_HOME/etc/apps/TA-CyCognito/local/limits.conf
* The content of limits.conf should be
	* [kv] limit = <integer\> maxchars = <integer\>
* By default, maxchars = <integer\>
	* Truncate _raw to this size and then do auto KV.
	* Default: 10240 characters

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-CyCognito
* Remove $SPLUNK_HOME/var/log/splunk/ta_cycognito_*.log.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance.

## END USER LICENSE AGREEMENT
https://www.cycognito.com/terms-of-service

## CONTACT

Contact Information: https://www.cycognito.com/contact

## BINARY FILE DECLARATION
* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML. https://pypi.org/project/MarkupSafe/

## COPYRIGHT

- (c) CyCognito, Ltd. 2026

