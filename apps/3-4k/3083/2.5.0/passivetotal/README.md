# RiskIQ Passive Total App For Splunk

## OVERVIEW

* The App delivers a user experience designed to make Splunk immediately useful and relevant for typical tasks and roles. The RiskIQ Passive Total App for Splunk will provide the below functionalities:
  * Local Investigation Dashboard to visualize the events, collected through bulk-enrichment by the RiskIQ Passive Total Add-on.
  * Live Investigation Dashboard to visualize the live RiskIQ Passive Total data, similar to the experience that matches the PassiveTotal community UI.
  * Search History Dashboard to visualize the Personal and Team Search History.

* Author - RiskIQ Intelligence
* Version - 2.5.0
* Build - 1
* Prerequisites - RiskIQ PassiveTotal Account (Username and API Key).

## COMPATIBILITY MATRIX

* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform Independent
* Splunk Enterprise version: 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES

### Version 2.5.0
* Bundled jQuery v3.5.0 in the app package. This version of jQuery has security fixes and will be used by the app independently.

### Version 2.4.0
* Fixed rptservices issue

### Version 2.3.0
* Added RiskIQ Research dashboard.
* Added `Articles` tab in Local & Live Investigation Dashboard.
* Added `Reputation` tab in Live Investigation Dashboard.

### Version 2.2.0
* Removed API Limit error message feature across dashboards.
* Added Cookies and Services tab in dashboards.

### Version 2.1.0
* Added Pull Indicators dashboard.

### Version 2.0.0
* Added Local Investigation Dashboard to visualize the events, collected through bulk-enrichment by the RiskIQ Passive Total Add-on.
* Added Live Investigation Dashboard to visualize the live RiskIQ Passive Total data, similar to the experience that matches the PassiveTotal community UI.
* Added Search History Dashboard to visualize the Personal and Team Search History.

## END USER LICENSE AGREEMENT

https://www.riskiq.com/msa/

## OPEN SOURCE COMPONENTS AND LICENSES

Some of the components included in the RiskIQ PassiveTotal App for Splunk are licensed under free or open-source licenses. We wish to thank the contributors to those projects.

- [splunk-dashboard-tabs-example](https://github.com/LukeMurphey/splunk-dashboard-tabs-example): version 1.0.0 [LICENSE](https://github.com/LukeMurphey/splunk-dashboard-tabs-example/blob/master/LICENSE)

## DOWNLOAD

https://splunkbase.splunk.com/app/3083/

## RECOMMENDED SYSTEM CONFIGURATION

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This App can be set up in two ways:

1. Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install an app on the search head.

- App resides on the search head machine to visualize the data coming from forwarders.

## INSTALLATION

Follow the below-listed steps to install an App from the bundle:

- Download the app package.
- From the UI navigate to  `Apps -> Manage Apps`.
- In the top right corner select `Install app from file`.
- Select `Choose File` and select the App package.
- Select `Upload` and follow the prompts.
  OR
- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## UPGRADE

Follow the below steps when upgrading from RiskIQ Passive Total App for Splunk

- From the UI navigate to `Apps -> Manage Apps`.
- In the top right corner select `Install app from file`.
- Select `Choose File` and select the App package.
- Check the upgrade option.
- Select `Upload` and follow the prompts.
- Remove default.xml from splunkhome->etc->apps->passivetotal->local->data->ui->nav if found from backend.
- Restart Splunk.

## Configure Macros:
* If the user has selected a default index (**Note**: *By default, Splunk considers only the `main` index as default index*) in the "Data Input" configuration during RiskIQ PassiveTotal Add-on for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in the "Data Input" configuration, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "RiskIQ PassiveTotal App for Splunk" in "App" context dropdown.
3. Click on the `passivetotal_index` macro from the shown table.
4. In the macro definition default value will be `index IN (main)`. Update the definition with the index you used for data collection and save the configurations. For example: `index IN (<your_index_names>)`.

## TROUBLESHOOTING

* If dashboards are not getting populated:
    * Make sure if you are using the custom index, then check that the `passivetotal_index` macro needs to be updated.
    * Make sure you have data in a given time range.
    * To check whether is data collected or not, run the " \`passivetotal_index\` | stats count by sourcetype" query in the search.
    * Try expanding TimeRange.

## Common Issues

Note: Local Investigation Dashboard will only search events in default indexes.

If you are collecting bulk enrichment data in the custom index, then Local Investigation Dashboard won't show any results, as it only searches in default indexes. To make the custom index a default one, follow the below steps:

1. Go to Splunk's Settings -> Roles (USERS AND AUTHENTICATIONS)
2. Edit the specific role that the user has
3. In Indexes section, add the custom index into default indexes
4. Save it

Note: In a Distributed Environment, if you are using a custom index in Add-on to collect data for Bulk Enrichment, then the same custom index needs to be created on Search Heads as well and then add it into default indexes of Search Heads as shown above. In the case of Search Head Cluster, you can perform this step on one of the Search Heads.

## UNINSTALL APP

To uninstall an app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps ($SPLUNK_HOME/etc/apps) -> Remove the passivetotal folder from apps directory -> Restart Splunk

## Support

### Questions and Answers

- Access questions and answers specific to RiskIQ PassiveTotal App For Splunk at <https://answers.splunk.com>. Be sure to tag your question with the App.
- Support Email: splunk@riskiq.com

Send any support related questions to splunk@riskiq.com

### Copyright 2016 - 2022 RiskIQ