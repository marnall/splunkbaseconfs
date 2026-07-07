# Splunk Technology Add-on for RiskIQ PassiveTotal

## This is an add-on powered by the Splunk Add-on Builder

## OVERVIEW

* RiskIQ PassiveTotal Add-on for Splunk brings the power of datasets collected from Internet scanning directly to your Splunk instance. This application leverages your existing PassiveTotal account and our API to bring in data for live investigation and also to do Bulk Enrichment of various datasets.
* The RiskIQ PassiveTotal Add-on for Splunk will provide the below functionalities:
  * Collect data from RiskIQ PassiveTotal API, do Bulk Enrichment of various data sets and store it into Splunk indexes with categorizing the data in different sourcetypes.
  * Provide custom commands for each tab provided in Community UI (<https://community.riskiq.com>). It will bring live data through API calls and will show in tabular form under the statistics tab in Search Dashboard.

* Author - RiskIQ Intelligence
* Version - 1.5.0
* Build - 1
* Prerequisites - RiskIQ PassiveTotal Account (Username and API Key).

## COMPATIBILITY MATRIX

* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform Independent
* Splunk Enterprise version: 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES

### Version 1.5.0

* Upgraded AOB from v3.0.1 to v4.0.0
* Upgraded croniter library from v0.3.31 to v.1.1.0

### Version 1.3.0

* Added data collection for `Articles`.
* Added custom command `rptreputation`.

### Version 1.2.0

* Removed API Limit error message feature across dashboards.
* Added data collection for `HostAttribute Cookies`.and `Services`.
* Added custom command `rptcookies`. and `rptservices`.

### Version 1.1.0

* Added `rptpullindicators` custom command.

### Version 1.0.0

* Added feature of Bulk Enrichment of Indicators directly into the Splunk Instance.
* Added new Custom Commands as listed above.
* Migrated existing Custom Commands from App to Add-on.
* Migrated Account & Proxy Configuration UI from App to Add-on.
* Updated Account & Proxy Configuration UI.
* Added Logging Configuration UI.
* Added compatibility for Add-on to Python 2 & 3.

## END USER LICENSE AGREEMENT

https://www.riskiq.com/msa/

## OPEN SOURCE COMPONENTS AND LICENSES

Some of the components included in RiskIQ PassiveTotal Add-on for Splunk are licensed under free or open-source licenses. We wish to thank the contributors to those projects.

* [passivetotal](https://pypi.org/project/passivetotal/) version 1.0.31 [LICENSE](https://github.com/passivetotal/python_api/blob/master/LICENSE)
* [croniter](https://pypi.org/project/croniter/) version 1.1.0  [LICENSE](https://github.com/kiorky/croniter/blob/master/docs/LICENSE)
* [PySocks](https://pypi.org/project/PySocks/) version 1.7.1 [LICENSE](https://github.com/Anorov/PySocks/blob/master/LICENSE)

## RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1. Standalone Mode: Install the Add-on on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install Add-on on search head and Heavy forwarder (for REST API).

* Configure Add-on on Search Head Deployer and then push it on Search Head Cluster. This step is required only for Live Investigation Dashboard and Search History Dashboard in App.
* Add-on needs to be installed and configured on the Heavy forwarder system.
* Execute the following command on Heavy forwarder to forward the collected data to the indexer.
  /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on search head for CIM mapping

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the PassiveTotal Add-on from `Splunkbase`.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the Add-on package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

Note: Dependencies have been packaged inside of the Add-on.

## CONFIGURATION

Follow the below steps for configuring RiskIQ PassiveTotal Add-on for Splunk.

* From the Splunk Home Page, click on RiskIQ PassiveTotal Add-on for Splunk and navigate to the Configuration section.
* In the PassiveTotal Account tab, enter the required details like Username/Email, RiskIQ PassiveTotal API Key, and click on Save to save the configuration.
* To use a proxy as part of the connection to RiskIQ PassiveTotal, go to the Proxy tab and provide the required details. Don't forget to check the Enable option.
* To configure the Log Level, go to the Logging tab.
* Once the configuration is done, you can use Bulk Enrichment and Custom command functionality.

## UPGRADATION

### Upgrade to v1.5.0
* No additional steps are required.
### Upgrade to v1.3.0
* No additional steps are required.

### Upgrade to v1.2.0

* Download the PassiveTotal Add-on from `Splunkbase`.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File`, then select the Add-on package and check the `Upgrade` checkbox.
* Select `Upload` and follow the prompts.
* Navigate to `$SPLUNK_HOME/etc/apps/TA-riskiq-passivetotal/local/ta_riskiq_passivetotal_settings.conf` if present.
* Remove the stanza `[api_errors]` alongwith the parameter `api_limit_exceeded` and save the file.
* Restart Splunk.

## Bulk Enrichment

Sample CSV Format

```
Indicators
abc.com
1.x.x.1
pqr.com
2.x.x.2
```

* To upload Indicators, go to the Upload Indicators section. Click Choose File and select CSV file from the local system. Click on Upload, It will save the file and will automatically create modular input in disabled mode with the same name as CSV File.
* User can enable/disable/edit/delete Modular Input by selecting specific Action on Inputs Section.
* After successfully uploading the CSV file, go to the Inputs section and click on Action -> Edit. It will open up an Edit Dialog box where you can change Interval (Bulk enrichment will be done/updated at this interval), Index (Splunk Index, where enriched data will be ingested), and Dataset (Type of enrichment that will be performed on ingested Indicators like Certificates, Host Pairs, etc.). Once done with editing, click on Update and go to Action -> Enable to enable bulk enrichment input for provided indicators.

Note: Bulk Enrichment can be done for Passive DNS, Whois, Certificates, Subdomains, Trackers, Components, Hostpairs, OSINT, Hashes, and Tags.

## Custom Commands

* To use custom commands, open Search & Reporting App, enter any provided custom commands with its parameters. It will fetch live data using PassiveTotal API and show search results in tabular form under the statistics tab.

## Available Custom Commands

The following commands can be used outside the context of the PassiveTotal Add-on to populate the "statistics" tab on search results:

### Below commands will return the same fields shown in [Community UI](https://community.riskiq.com) under a respective tab.

- Resolutions: ```| rptresolutions query=<IPAddress/Hostname>```
- Whois: ```| rptwhois query=<IPAddress/Hostname>```
- Certificates: ```| rptcertificates query=<IPAddress/Hostname> field=<Field on which query value will be searched - (default:name)>```
- Subdomains: ```| rptsubdomains query=<IPAddress/Hostname>```
- Trackers: ```| rpttrackers query=<IPAddress/Hostname>```
- Components: ```| rptcomponents query=<IPAddress/Hostname>```
- Host Pairs: ```| rpthostpairs query=<IPAddress/Hostname> direction=<pairs/children/parents - (default:pairs)>```
- Cookies: ```| rptcookies query=<IPAddress/Hostname>```
- Services: ```| rptservices query=<IPAddress>```
- OSINT: ```| rptosint query=<IPAddress/Hostname>```
- Hashes: ```| rpthashes query=<IPAddress/Hostname>```
- DNS: ```| rptdns query=<IPAddress/Hostname>```

### Other custom commands

- Account History: ```| rpthistory``` 
- Team History: ```| rptteamstream```
- Whois Search: ```| rptwhoissearch query=<IPAddress/Hostname> field=<Field on which query value will be searched>```
- Trackers Search: ```| rpttrackerssearch query=<IPAddress/Hostname> type=<Type of trackers to retrive>```
- Pull Indicators: ```<Base search> | rptpullindicators field="field1,field2" type="passivedns"```
- Host Attributes Cookies: ``` | rptcookies query=<IPAddress/Hostname> ```
- Reputation: ```| rptreputation query=<IPAddress/Hostname>```
- Mass Reputation: ```| <SPL for searching events having field which contains IPAddress/Hostname> | rptreputation query_field=<Field Name which contains IPAddress/Hostname>```

### Below commands are migrated from App to Add-On and kept for backward compatibility

- **ptenrich_command.py**: Perform enrichment on the supplied "query" to get tags, metadata, and user classifications.
- **pthistory_command.py**: Get the historic searches associated with the API key organization. (*requires PassiveTotal enterprise*)
- **ptpdns_command.py**: Get the passive DNS information associated with the supplied "query" value.
- **ptssl_command.py**: Get the passive SSL information associated with the supplied "query" value.
- **pttrackers_command.py**: Get the tracking code information associated with the supplied "query" value.
- **ptupdns_command.py**: Get the unique resolutions based on passive DNS associated with the supplied "query" value.
- **ptwhois_command.py**: Get the WHOIS information associated with the supplied "query" value.
- **pthostpairs_command.py**: Get host pairs associated with the supplied query value.
- **ptcomponents_command.py**: Get the trackers associated with the supplied query value.

## DATA RETENTION POLICY

* To control the amount of data in particular index, use the below settings in $SPLUNK_HOME/etc/apps/TA-riskiq-passivetotal/local/indexes.conf for your index.

```
frozenTimePeriodInSecs = Time in seconds for which data should remain in index
maxDataSize = 750
maxHotBuckets = 1
```

* Ex. Use the below settings for keeping 1 day data in index `my_test_index`

```
[my_test_index]
frozenTimePeriodInSecs = 86400
maxDataSize = 750
maxHotBuckets = 1
```

## TROUBLESHOOTING

### Common Issues

* Custom commands or Bulk Enrichment will not produce any results if configured PassiveTotal Account's API exceeded per day quota so It will start working the next day once the API quota gets reset. A proper message regarding this can be seen in a log file and Splunk's standard messages section. If you want to increase API quota, contact support for details on enterprise plans.

### Splunk search showing empty results (blank events)

* The number of events displayed in the Splunk search timeline is configurable by a parameter called `max_events_per_bucket`.
* Setting this parameter to a higher value, will show more events in the timeline. The default value is 1000.
* To change this parameter follow the below steps:
  * Open/Create limits.conf under `$SPLUNK_HOME/etc/system/local/` folder.
  * Create a stanza `[search]` if not already present.
  * Add `max_events_per_bucket=<some higher number>` in `[search]` stanza.
  * Save the file and restart Splunk.

### The input or configuration page is not loading.

* Check log file for possible errors/warnings: $SPLUNK_HOME/var/log/splunk/splunkd.log

### Data is not getting collected in Splunk for Bulk Enrichment

* Verify that such events exist on the RiskIQ PassiveTotal platform.
* Check the log file related to Bulk Enrichment that is generated under `$SPLUNK_HOME/var/log/splunk/ta_riskiq_passivetotal_indicators.log`.
* To get the detailed logs, in the Splunk UI, navigate to RiskIQ PassiveTotal Add-on For Splunk. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
* Check the logs. They will be more verbose and will give the user insights on data collection.
* Disable/Enable the input to restart the enrichment process.

### Custom command is not generating any results or showing error

* Verify that such events exist on the RiskIQ PassiveTotal platform.
* If any error occurs during execution, a basic error message will be shown below the search input box.
* Check the log file related to custom commands that is generated under `$SPLUNK_HOME/var/log/splunk/ta_riskiq_passivetotal_custom_commands.log`
* To get the detailed logs, in the Splunk UI, navigate to RiskIQ PassiveTotal Add-on For Splunk. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
* Check the logs. They will be more verbose and will give the user insights on the actual issue.

#### Splunk Monitoring Console

* Check the Monitoring Console (>=v6.5) for errors.

### If the Splunk Instance is behind a proxy, Configure Proxy settings by navigating to RiskIQ PassiveTotal Add-on for Splunk -> Configuration -> Proxy

## UNINSTALL & CLEANUP STEPS


* Remove $SPLUNK_HOME/etc/apps/TA-riskiq-passivetotal
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_passivetotal_indicators.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_passivetotal_custom_commands.log**
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## SUPPORT

### Questions and Answers

* Access questions and answers specific to RiskIQ PassiveTotal Add-on For Splunk at https://answers.splunk.com. Be sure to tag your question with the Add-on.

### Support

* Support Offered: Yes 
* Support Email: splunk@riskiq.com 

Send any support related questions to splunk@riskiq.com

### Copyright 2016 - 2022 RiskIQ