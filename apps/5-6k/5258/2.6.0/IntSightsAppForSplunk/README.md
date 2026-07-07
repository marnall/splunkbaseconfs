# IntSights App for Splunk

## OVERVIEW
The IntSights App for Splunk pulls IOCs, Alerts and Vulnerabilities from the IntSights platform, does correlation and provides dashboards for visualization.

This is an app powered by the Splunk Add-on Builder.

## REQUIREMENTS
* Splunk version 9.4.x, 9.3.x, 9.2.x or 9.1.x
* Python version 3.7 and python3.9
* OS Support: Linux and Windows
* Browser Support: Chrome and Firefox

## RELEASE NOTES

### Version 2.6.0
* Migrated the App using Add-On Builder version 4.4.1
* Updated the retirement logic to handle Splunk limits

### Version 2.5.1
* Added configuration option to display specific correlation details count per selected Actions, correlationIndices instead of the overall count for last day and week.
* Updated the Correlation details dashboard to display the counts per selected action, index filters for last day and last 7 days as per selected filters.

### Version 2.5.0
* Migrated the App using Add-On Builder version 4.2.0

### Version 2.4.0
* Added Macros Configuration page in UI to update the macros.
* Added "IOC Status" filter in IOCs input configuration page to collect IOC data according to selected IOC status.
* Added an IOC search filter and First Match Time column in the Correlation Details dashboard.
* Updated IOCs retirement logic to consider iocLastSeen field for retirement.
* Removed Verify SSL Certificate checkbox.
* Updated retirement policy of IOCs for IOC type IP, Email and Hash.
* Added default value for the index field while creating the input.
* Made Start date and Report date un-editable while editing the input.
* Enhanced the log messages.
* Few minor enhancements.

### Version 2.3.0
* Provided an option of collecting All or Non-whitelisted IOCs on the input configuration page.
* Replaced the V1 whitelist endpoint with the V2 whitelist endpoint.
* Updated the Correlation Details dashboard to reflect the result count in the panel.

### Version: 2.2.1
* Added co-dependency on correlated time for the filters on Correlation Details Dashboard.

### Version: 2.2.0
* Modified the limit value for Intsights IOCs v2 route to 1000
* Added co-dependecy for the filters in Correlation Details Dashboard.
* Enhanced the IOC correlation logic to improve performance.
* Added support of "PendingEnrichment" severity type for IOCs.

### Version: 2.1.0
* Modified the IOCs route to v2
* Modified the IOCs lookup, correlation savedsearches, Correlation Details and Correlation Overview dashboards to use tags{} instead of systemTags{} as systemTags are deprecated in v2
* Fixed some minor bugs.

### Version: 2.0.0
* Added support for associated action field values to be added to the intsights_matched_iocs IOCs.
* Modified the IOCs correlation savedsearches to use stats command instead of table command.
* Migrated the App using Add-On Builder version 4.1.0
* Modified correlation searches to create Notable Events with additional fields and title with context in Splunk enterprise for Indicators, Alerts and Vulnerabilities.

### Version: 1.3.0
* Modified the intsightsmatchiocs and intsightsmatchvulns custom commands to combine the events obtained in chunks for better performance 
* Added 3 more savedsearches which will help to deal the large amount of target indices data and by default it will be disabled.
* Added correlation searches to create Notable Events in Splunk enterprise for Indicators, Alerts and Vulnerabilities.
* Added Splunk alerts for newly founded Vulnerabilities and Alerts.

### Version: 1.2.0
* Added IntSights Alerts and IntSights Vulnerabilities data collection.
* Added support to configure the Input policy for IOCs, Alerts and Vulnerabilities on the same Input page.
* Added "Alert Overview" dashboard.
* Added "Alert Details" dashboard with navigation to the Intsights platform and to the related IOCs.
* Added Alert images to be shown in "Alert Details" dashboard.
* Added "Vulnerability Overview" dashboard.
* Added "Vulnerability Correlation Overview" dashboard.
* Added "Vulnerability Correlation Details" dashboard with navigation to the Intsights platform.
* Introducing retention policy for alerts and vulnerabilties.
* Adding macro to disable the outgoing calls to Tags and Comments API.
* Fixed some minor bugs.

### Version: 1.1.0
* Removing the Whitelisted IOCs from the lookup tables.
* Converting the Retired IOCs savedsearch to the scripted input.
* Introduced some filters on Correlation Overview and Correlation Details dashboards.
* Presenting some additional data in lookups.
* Introducing the button to navigate to the Intsights platform to get more information of matched IOCs.
* Fixed some minor bugs.

### Version: 1.0.2
* Fixed the time range issue on IOC drilldown in Correlation Details dashboard.
* Fixed the proxy related issue.

### Version: 1.0.1
* Fixed the dashboards loading time
* Added IOCs retirement feature

### Version: 1.0.0
* Added IOC data collection.
* Added field-based correlation feature to find sightings.
* Added the Splunk alert for newly founded indicators.
* Added Setup, IOC Overview, Correlation Overview and Correlation Details Dashboards.
* Added investigation feature for IOCs that matched an indicator in the Splunk environment.
* Added Workflow action to mark IOC as whitelist.

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of Search Head, Indexer and Forwarder.

## INSTALLATION OF APP
IntSights App for Splunk can be installed through UI as shown below or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.  
2. Click `Install app from file`.  
3. Click `Choose file` and select the IntSights App installation file.  
4. Click on `Upload`.
5. Restart Splunk.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This app can be set up in two ways:

1. Standalone Mode
    * Install the IntSights App for Splunk.
    * Configure an account and create modular input.
2. Distributed Environment
    * Install the IntSights App for Splunk on the Search Head, Indexer and On-Premise/IDM/UF/HF.
    * Configure an account on both Forwarder and Search Head.
    * Create modular input only on Forwarder.
    * Configure macros, savedsearches and alerts only on the Search Head.
3. Cloud Environment
    * Install the IntSights App for Splunk on Searchhead.
    * Install the IntSights App for Splunk on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the IntSights App for Splunk on the On-Premise Heavy Forwarder.

Note that for the distributed environment, only indexes of the Forwarder would be shown in the input configuration page.

## UPGRADATION OF APP
Follow the below steps to upgrade the App

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the IntSightsAppForSplunk installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

## Upgrading to version 2.6.0 from 2.5.1
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 2.5.1 from 2.5.0
* Follow the `UPGRADATION OF APP` section.
* After upgrading to version 2.5.1 follow the below steps:
    * Navigate to IntsightsAppForSplunk > Setup > Configuration > Macros Configuration
    * For Input Type IOC, check the check box `Enable maintaining correlation per IOC, correlation index and actions` if instead of overall count of correlated IOCs, you want to get specific counts as per selected actions, correlatedIndices filters.

## Upgrading to version 2.5.0 from 2.4.0
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 2.4.0 from 2.3.0
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 2.3.0 from 2.2.1
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Common Steps for Upgradation to version 2.2.0 from 2.1.0

* To configure the macros,  Go to Settings -> Advanced search -> Search macros. Here configure the following macros :

    * The below macros indicate the target indices to obtain Splunk events which need to be correlated for the specific type.

            intsights_ips_target_indices
            intsights_domains_target_indices
            intsights_emails_target_indices
            intsights_urls_target_indices
            intsights_hashes_target_indices
        For example the Intsights_ips_target_indices macro will be used to indicate the target indices which will contain Splunk events with ip fields that can be correlated

    * The below macros indicate the target sourcetypes to obtain Splunk events which need to be correlated for the specific type

            intsights_ips_target_sourcetypes
            intsights_emails_target_sourcetypes
            intsights_domains_target_sourcetypes
            intsights_hashes_target_sourcetypes
            intsights_urls_target_sourcetypes
        For example the Intsights_ips_target_sourcetypes macro will be used to indicate the target sourcetypes which will contain splunk events with ip fields that can be correlated

    * The below macros indicate the comma-separated target indicator fields to obtain from Splunk events which need to be correlated with the specific type.

            intsights_ips_target_indicator_fields
            intsights_domains_target_indicator_fields
            intsights_emails_target_indicator_fields
            intsights_urls_target_indicator_fields
            intsights_hashes_target_indicator_fields
        For example the Intsights_ips_target_indicator_fields macro will be used to indicate the target fields which will contain fields from  splunk events with ip values that can be correlated

    * The below macros indicate the comma-separated target action fields to obtain from Splunk events for correlation with specific type of IOC.

            intsights_ips_target_indicator_action_fields
            intsights_domains_target_indicator_action_fields
            intsights_emails_target_indicator_action_fields
            intsights_urls_target_indicator_action_fields
            intsights_hashes_target_indicator_action_fields
        For example the Intsights_ips_target_indicator_fields macro will be used to indicate the target action fields which will contain actions values from  splunk events which are correlated with IP type of IOCs

## Upgrading to version 2.2.1 from 2.2.0
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 2.2.0 from 2.1.0

#### Upgrade steps to version 2.2.0 when facing performance issues with IOC correlation searches
**Follow the upgradation steps under this section only when observing some IOC correlation related performance issue in previous versions of the app.** For example : The correlation savedsearches are not getting completed in 30 minutes as expected.
Then follow the below mentioned steps for upgrade to version 2.2.0.

1. Before upgrading to new version, Go to Inputs tabs and disable all the configured inputs.
2. Go to Searches, reports and alerts and make note of Next Scheduled Time for `intsights_correlate_unmatched_iocs`.
3. Follow the `UPGRADATION OF APP` section.
4. Once the app is installed and Splunk is restarted, Go to Settings -> Searches, reports and alerts . Select Intsights App for Splunk in the App Filter and Owner filter as ALL

    Now disable the following saved searches by clicking on Edit -> Disable in the Actions column.

        * intsights_correlate_IpAddressess_iocs
        * intsights_correlate_Emails_iocs
        * intsights_correlate_Urls_iocs
        * intsights_correlate_Hashes_iocs
        * intsights_correlate_Domains_iocs

5. Follow the `Common Steps for Upgradation to version 2.2.0 from 2.1.0`.
6. Go to Settings - > Searches, reports and alerts. Here Enable and schedule  `intsights_backup_master_lookup` savedsearch to run in about 2 mins from current time
    * To Enable the savedsearch add this `intsights_backup_master_lookup` in the filter.
    * Select Edit -> Enable option under Actions for this particular savedsearch.
    * To schedule savedsearch select Edit -> Edit Schedule. In the dialogue box that opens enter Cron expression to schedule it about 2 mins from the current time. The format of Cron Schedule is `<Minutes> <Hours> <Day of Month> <Month> <Day of week>`
        * For example if you are editing the Cron Schedule at 14:00 Hours use the following Cron schedule : `02 14 * * *` in the Edit Schedule dialogue box and Save.
7. Now wait for the above search to get completed. To check the status of the above search click on  `View Recent` under the Actions coulmn after the Scheduled time, this will navigate to a new Tab where you need to verify that the Status coulmn shows status as `Done`. To check the updated status refresh the page.
8. Once the above savedsearch is done running successfully, disable this (intsights_backup_master_lookup) saved search by clicking on the Edit -> Disable in Searches, Reports and Alerts Page for this particular savedsearch.
9. Once the above savedsearch is done running successfully, Enable and schedule `intsights_accelarate_master_lookup` savedsearch  to run in about 2 mins from current time.
    * To Enable the savedsearch add this `intsights_accelarate_master_lookup` in the filter.
    * Select Edit -> Enable option under Actions for this particular savedsearch.
    * To schedule savedsearch select Edit -> Edit Schedule. In the dialogue box that opens enter Cron expression to schedule it about 2 mins from the current time. The format of Cron Schedule is `<Minutes> <Hours> <Day of Month> <Month> <Day of week>`
        * For example if you are editing the Cron Schedule at 14:00 Hours use the following Cron schedule : `02 14 * * *` in the Edit Schedule dialogue box and Save.
10. Now wait for the above search to get completed. To check the status of the above search click on  `View Recent` under the Actions column after the Scheduled time, this will navigate to a new Tab where you need to verify that the Status coulmn shows status as `Done`. To check the updated status refresh the page.
11. Once the above savedsearch is done running successfully, disable this (intsights_accelarate_master_lookup) saved search by clicking on the Edit -> Disable in Searches, Reports and Alerts Page for this particular savedsearch.
12. Now Go to the Inputs tab and Enable all the configured Inputs.
13. Now navigate to Settings -> Searches, reports and alerts, Select Edit -> Edit Schedule in the Actions column. In the dialogue box that opens Select `Enable and Schedule Report` checkbox. Now in the `Time Range` filter, calculate the difference between the current time and time noted in Step 2 as the `Earliest` field. You can select the desired unit of time from the assocaiated dropdown and provide the `Earliest` field value and don't change the end time for the following savedsearches:
    * intsights_correlate_IpAddressess_iocs
    * intsights_correlate_Emails_iocs
    * intsights_correlate_Urls_iocs
    * intsights_correlate_Hashes_iocs
    * intsights_correlate_Domains_iocs
14. Once the above searches complete their execution, Go to Settings -> Searches, reports and alerts, Select Edit -> Edit Schedule and provide `Last 1 hour` in the `Time Range` filter and click on Save.

**Note** : After upgradation to version 2.2.0 of the app, the IOC correlation savedsearches are expected to complete execution within 1 hour from whenever it was scheduled.

#### Upgrade steps to version 2.2.0 when no performance issues is observed with IOC correlation searches
If no issue was observed in IOC correlation performance in previous versions of the app.
Then follow the below mentioned steps for upgrade to version 2.2.0.

1. Follow the `UPGRADATION OF APP` section.
2. Once the app is installed and Splunk is restarted, Follow the `Common Steps for Upgradation to version 2.2.0 from 2.1.0`.
3. Ensure that the following savedsearches are enabled:
    * intsights_correlate_IpAddressess_iocs
    * intsights_correlate_Emails_iocs
    * intsights_correlate_Urls_iocs
    * intsights_correlate_Hashes_iocs
    * intsights_correlate_Domains_iocs

**Note** : The same steps can be used to Upgrade the App from version 2.0.0 to 2.2.0

## Upgrading to version 2.1.0 from 2.0.0
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 2.0.0 from 1.3.0
* Follow the `UPGRADATION OF APP` section.
* Update the IOCs correlation saved searches to use stats command instead of table command.
    * From IntsightsAppForSplunk in Splunk , navigate to `Settings` > `Searches, Reports, and Alerts`
    * Select App value as `Intsights App for Splunk` and Owner as `All`
    * Ensure that each of the savedsearches in intsights_correlate_unmatched_iocs, intsights_correlate_unmatched_iocs_2, intsights_correlate_unmatched_iocs_3, intsights_correlate_unmatched_iocs_4, intsights_correlate_matched_iocs, intsights_correlate_matched_iocs_2, intsights_correlate_matched_iocs_3, intsights_correlate_matched_iocs_4 uses stats command as follows : 
        ```| fillnull value="-" `intsights_target_indicator_fields` `intsights_target_indicator_action_fields` | stats count by `intsights_target_indicator_fields` `intsights_target_indicator_action_fields`, index```
    instead of the table command:
        ```| table `intsights_target_indicator_fields`, index ```
    * Example : 
        Old savedsearch intsights_correlate_unmatched_iocs: 
        ``` `intsights_target_indices` `intsights_target_sourcetypes` sourcetype!="intsights:indicator" sourcetype!="intsights:alert" sourcetype!="intsights:vulnerability" | table `intsights_target_indicator_fields`, index | intsightsmatchiocs ```

        Updated savedsearch intsights_correlate_unmatched_iocs: 
        ``` `intsights_target_indices` `intsights_target_sourcetypes` sourcetype!="intsights:indicator" sourcetype!="intsights:alert" sourcetype!="intsights:vulnerability" | fillnull value="-" `intsights_target_indicator_fields` `intsights_target_indicator_action_fields` | stats count by `intsights_target_indicator_fields` `intsights_target_indicator_action_fields`, index | intsightsmatchiocs ```

## Upgrading to version 1.3.0 from 1.2.0
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 1.2.0 from 1.1.0
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 1.1.0 from 1.0.2
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 1.0.2 from 1.0.1
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## Upgrading to version 1.0.1 from 1.0.0
* Follow the `UPGRADATION OF APP` section.
* No additional steps are required.

## CONFIGURATION OF APP
Configure IntSights App for Splunk:

### Account
To configure the Account

1. Navigate to the `Setup`-> `Configuration`.
2. Provide your IntSights credential and Click on `Save`.

| IntSights Account parameters | Mandatory or Optional | Description                                 |
| ---------------------------- | --------------------- | ------------------------------------------- |
| IntSights Portal Address     | Mandatory             | Portal Address of the IntSights (read-only) |
| Account ID                   | Mandatory             | Provide an Account ID of IntSights account  |
| API Key                      | Mandatory             | Provide an API Key of IntSights Account     |

### Proxy
To configure the Proxy

1. Navigate to the `Setup`-> `Configuration`.
2. Click on the `Proxy` tab.
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy                                                      |
|    Proxy Type            |     Mandatory            |  Select proxy type that you want to use from the dropdown (supports HTTP proxy only)|
|    Proxy Host            |     Mandatory            |  Host or IP of the proxy server                                                        |
|    Proxy Port            |     Mandatory            |  Port for proxy server                                                                 |
|  Proxy Username          |     Optional             |  Username of the proxy server |
|  Proxy Password          |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging

1. Navigate to the `Setup`-> `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`.

### Macros Configuration
To configure Macros 

1. Navigate to the `Setup`-> `Configuration`.
2. Click on the `Macros Configuration` tab.
3. Select the input type from the `Input Types` dropdown and provide the values that you want to update.
4. Click on `Save`.

| Field Name | Description | Corresponding Macro |
| ---------- | ----------- | ------------------- |
| Input Types | Type of Input for which you want to configure Macros | N/A |
| IOC Indices | Macro definition of indices in which IOC data will be collected | intsights_ioc_indices |
| Enable Tags Comments API Call | Macro whose definition determines if outgoing calls to tags and comments API will be enabled or disabled | intsights_enable_tags_comments_api_calls |
| Enable maintaining correlation per IOC, correlation index and actions | Macro which determines if correlation per IOC, index and action is maintained for last 7 days | intsights_enable_maintain_corr_indexes_actions |
| IOC Type | Select types of IOCs for which you want to configure Macros | N/A |
| Alert Indices | Macro definition of indices in which Alert data will be collected | intsights_alert_indices |
| Vuln Indices | Macro definition of indices in which Vulnerability data will be collected | intsights_vuln_indices |
| Vuln Target Indices | Macro definition of Splunk indices to match against Vulnerabilities for correlation | intsights_vuln_target_indices |
| Vuln Target Sourcetypes | Macro definition of Splunk sourcetypes to match against Vulnerabilities for correlation | intsights_vuln_target_sourcetypes |
| Vuln Target Indicator Fields | Comma separated list of all fields in Splunk event on which correlation will be performed for Vulnerabilities | intsights_vuln_target_indicator_fields |
| IP's Target Indices | Macro definition of Splunk indices to match against IP's IOCs for correlation | intsights_ips_target_indices |
| IP's Target Sourcetypes | Macro definition of Splunk sourcetypes to match against IP's IOCs for correlation | intsights_ips_target_sourcetypes |
| IP's Target IOC Fields | Comma separated list of all fields in Splunk event on which correlation will be performed for IP's IOCs | intsights_ips_target_indicator_fields |
| IP's Target Action Fields | Comma separated list of all indicator action fields in Splunk event on which correlation will be performed for IP's IOCs | intsights_ips_target_indicator_action_fields |
| Email's Target Indices | Macro definition of Splunk indices to match against Email's IOCs for correlation | intsights_emails_target_indices |
| Email's Target Sourcetypes | Macro definition of Splunk sourcetypes to match against Email's IOCs for correlation | intsights_emails_target_sourcetypes |
| Email's Target IOC Fields | Comma separated list of all fields in Splunk event on which correlation will be performed for Email's IOCs | intsights_emails_target_indicator_fields |
| Email's Target Action Fields | Comma separated list of all indicator action fields in Splunk event on which correlation will be performed for Email's IOCs | intsights_emails_target_indicator_action_fields |
| Domain's Target Indices | Macro definition of Splunk indices to match against Domain's IOCs for correlation | intsights_domains_target_indices |
| Domain's Target Sourcetypes | Macro definition of Splunk sourcetypes to match against Domain's IOCs for correlation | intsights_domains_target_sourcetypes |
| Domain's Target IOC Fields | Comma separated list of all fields in Splunk event on which correlation will be performed for Domain's IOCs | intsights_domains_target_indicator_fields |
| Domain's Target Action Fields | Comma separated list of all indicator action fields in Splunk event on which correlation will be performed for Domain's IOCs | intsights_domains_target_indicator_action_fields |
| URL's Target Indices | Macro definition of Splunk indices to match against URL's IOCs for correlation | intsights_urls_target_indices |
| URL's Target Sourcetypes | Macro definition of Splunk sourcetypes to match against URL's IOCs for correlation | intsights_urls_target_sourcetypes |
| URL's Target IOC Fields | Comma separated list of all fields in Splunk event on which correlation will be performed for URL's IOCs | intsights_urls_target_indicator_fields |
| URL's Target Action Fields | Comma separated list of all indicator action fields in Splunk event on which correlation will be performed for URL's IOCs | intsights_urls_target_indicator_action_fields |
| Hash's Target Indices | Macro definition of Splunk indices to match against Hash's IOCs for correlation | intsights_hashes_target_indices |
| Hash's Target Sourcetypes | Macro defintion of Splunk sourcetypes to match against Hash's IOCs for correlation | intsights_hashes_target_sourcetypes |
| Hash's Target IOC Fields | Comma separated list of all fields in Splunk event on which correlation will be performed for Hash's IOCs | intsights_hashes_target_indicator_fields |
| Hash's Target Action Fields | Comma separated list of all indicator action fields in Splunk event on which correlation will be performed for Hash's IOCs | intsights_hashes_target_indicator_action_fields |

* NOTE: All fields are mandatory
* NOTE: With 2.4.0 and later versions of the app, please use the Macro Configuration page, instead of directly configuring the macros from the settigs. Doing so may lead to some inconsistancies.


### Inputs
To configure the Inputs

1. Navigate to the `Setup`-> `Inputs`.
2. Click on `Create New Input`, one dropdown will be open with options:
    * `Configure IntSights Input Policy for IOCs`
    * `Configure IntSights Input Policy for Alerts`
    * `Configure IntSights Input Policy for Vulnerabilities`
3. Select a option and pop-up will open accordingly.
4. Provide the input related information for and click on `Add` to start the data collection. Field descriptions are as below:

**IntSights Input Policy for IOCs**

| Input Parameter |  Mandatory or Optional | Desciption                                                   |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | Provide a unique name to uniquely identify IOC details       |
| Interval        | Mandatory              | Interval in seconds and more than 3600 seconds               |
| Index           | Mandatory              | Index in which you want to store your data                   |
| Start Date      | Optional               | Provide start date in UTC from which Data Collection will start. Time format is "%Y-%m-%dT%H:%M:%S.%f" |
| IOC Severity    | Mandatory              | Select the severity to filter IOCs                           |
| IOC Type        | Mandatory              | Select the type to filter IOCs                               |
| IOC Status      | Mandatory              | Select the IOC Status to filter IOCs                    |
| Reporting Feeds | Mandatory              | Select the reporting feeds to filter IOCs                    |
| Whitelisted     | Mandatory              | Select the whitelisted status to filter IOCs                 |


**IntSights Input Policy for Alerts**

| Input Parameter |  Mandatory or Optional | Desciption                                                   |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | Provide a unique name to uniquely identify Alert details     |
| Interval        | Mandatory              | Interval in seconds and more than 3600 seconds               |
| Index           | Mandatory              | Index in which you want to store your data                   |
| Report Date     | Mandatory              | Select the report date from which Data Collection will start |
| Alert Severity  | Mandatory              | Select the severity to filter Alerts                         |
| Alert Type      | Mandatory              | Select the type to filter Alerts                             |
| Alert Status    | Mandatory              | Select the status to filter Alerts                           |


**IntSights Input Policy for Vulnerabilties**

| Input Parameter         |  Mandatory or Optional | Desciption                                                           |
| ----------------------- | ---------------------- | -------------------------------------------------------------------- |
| Name                    | Mandatory              | Provide a unique name to uniquely identify Vulnerability details     |
| Interval                | Mandatory              | Interval in seconds and more than 3600 seconds                       |
| Index                   | Mandatory              | Index in which you want to store your data                           |
| Report Date             | Mandatory              | Select the report date from which Data Collection will start         |
| Vulnerability Severity  | Mandatory              | Select the severity to filter Vulnerabilities                        |
| Product & Vendor        | Mandatory              | Select the product and vendor to filter Vulnerabilities              |
| Exploit Availability    | Mandatory              | Select the status of Exploit Availability to filter Vulnerabilities  |

Note that if multiple inputs are created with overlapping configuration, there will be duplicate Events in Splunk.

### Configure Macros
Macros can be configured from `Setup`->`Configuration`->`Macros Configuration`. If you don't find some Macros there then Macros can be configured from Search Macros UI as well.

To configure Macro from Splunk UI Settings,

1. Go to `Settings` -> `Advanced search` -> `Search Macros`.
2. Select "IntSights App for Splunk" in the App context.
3. Configure all Macros as specified below by clicking on `Name` of the Macro, go to `Definition` field and update it as per requirements.
4. Click on the `Save` button.

Note that while configuring the correlation related Macro Definition, Comparison Operators and Logical operators can be used with the combination. For selecting all value of an entity, "*" (asterisk) can be used. Logical operators like "AND", "OR" should be capital when used in Definition.

* If the user has selected a "main" index while configuring data input for IOC, then no need to perform this step as it is a default index specified in Macro. But if the user has given any other index in Input configuration, then do the below steps.
    * In "intsights_ioc_indices" Macro Definition, add all "OR" separated indexes on which data has been collected. Note that the empty value of a Definition will by default consider default index only. Sample Definition is shown below.
        - `(index="main" OR index="sample1" OR index="sample2")`

* For correlation of IOCs, target indices,target sourcetypes and target indicator fields for specific IOC type can be configured using below Macros.

        intsights_<ioc_type>_target_indices
        intsights_<ioc_type>_target_sourcetypes
        intsights_<ioc_type>_target_indicator_fields
        intsights_<ioc_type>_target_indicator_action_fields

    Note : Macros are bifurcated based on IOCs types for correlation. <ioc_type> are "ips", "domains", "emails", "urls", "hashes"
    * In "intsights_<ioc_type>_target_indices" Macro Definition, add all "OR" separated target indices. Note that the empty value of a Definition will by default consider default index only. Sample Definitions are shown below.
        - `(index="main" OR index="sample1")`
        - `(index="*" AND index!="main")`
    
    * In "intsights_<ioc_type>_target_sourcetypes" Macro Definition, add all target sourcetypes. 
    Note that the empty value of a Definition will by default consider all sourcetypes. Sample Definitions are shown below.
        - `(sourcetype="sample1" OR sourcetype="sample2")`
        - `(sourcetype="*" AND sourcetype!="sample1")`
  
    * In "intsights_<ioc_type>_target_indicator_fields" Macro Definition, add all "," (comma) separated target fields of Splunk events on which correlation will be performed. Note that the empty value of a field or empty Macro Definition is not allowed and will result in an error while running correlation savedsearches. Sample Definition will contain below values based on IOC type.
        - `"srcIP", "dstIP"`: For IpAddresses
        - `"email"` : For Emails
        - `"file_hash"` : For Hashes
        - `"domain"` : For Domains
        - `"url"`: For Urls

    * In "intsights_<ioc_type>_target_indicator_fields_calc" Macro Definition, automatically set from UI based on "intsights_<ioc_type>_target_indicator_fields" when  maintaining correlation per IOC, correlation index and actions is enabled. This is used in query to maintain details of correlated events of past 7 days.

    * In "intsights_<ioc_type>_target_indicator_action_fields_calc" Macro Definition, automatically set from UI based on "intsights_<ioc_type>_target_indicator_action_fields" when  maintaining correlation per IOC, correlation index and actions is enabled. This is used in query used to to maintain details of correlated events of past 7 days.

    * In "intsights_<ioc_type>_target_indicator_action_fields" Macro Definition, add all "," (comma) separated target action fields of Splunk events from which actions will be added to intsights_matched_iocs lookup on correlation. Note that an empty Macro Definition is not allowed and will result in an error while running correlation savedsearches. 
        * By default, actions will not be updated in intsights_matched_iocs lookup.
        * If you wish to update the actions in intsights_matched_iocs lookup , update the definition to specify the comma seperated target action fields of Splunk events from which actions will be added to intsights_matched_iocs lookup on correlation. Example : 
            - `first_action, second_action`
        * If you wish not to update the actions in intsights_matched_iocs, update the definition to specify `,` (comma).
    

* Following macros can be configured for retirement of IOCs in provided days (Valid integer number).
    * **intsights_url_ioc_retiring_days** - Retire URL type of IOCs after given days (default is 60 days)
    * **intsights_domain_ioc_retiring_days** - Retire Domain type of IOCs after given days (default is 90 days)
    * **intsights_email_ioc_retiring_days** - Retire Email type of IOCs after given days (default is 60 days)
    * **intsights_hash_ioc_retiring_days** - Retire Hash type of IOCs after given days (default is 365 days)
    * **intsights_ipaddress_ioc_retiring_days** - Retire IP Address type of IOCs after given days (default is 14 days)

* If the user has selected a "main" index while configuring data input for Alert, then no need to perform this step as it is a default index specified in Macro. But if the user has given any other index in Input configuration, then do the below steps.
    * In "intsights_alert_indices" Macro Definition, add all "OR" separated indexes on which data has been collected. Note that the empty value of a Definition will by default consider default index only. Sample Definition is shown below.
        - `(index="main" OR index="sample1" OR index="sample2")`

* The "intsights_alert_retiring_days" macro can be configured for retirement of Alerts in provided days (Valid integer number or "").
    * Default is 180 days
    * If the user wants to remove only the alerts with status "closed", then add "" in the macro definition.

* If the user has selected a "main" index while configuring data input for Vulnerability, then no need to perform this step as it is a default index specified in Macro. But if the user has given any other index in Input configuration, then do the below steps.
    * In "intsights_vuln_indices" Macro Definition, add all "OR" separated indexes on which data has been collected. Note that the empty value of a Definition will by default consider default index only. Sample Definition is shown below.
        - `(index="main" OR index="sample1" OR index="sample2")`

* For correlation of vulnerabilities, target indices, sourcetypes and fields can be configured using below Macros
    * In "intsights_vuln_target_indices" Macro Definition, add all "OR" separated target indices. Note that the empty value of a Definition will by default consider default index only. Sample Definitions are shown below.
        - `(index="main" OR index="sample1")`
        - `(index="*" AND index!="main")`

    * In "intsights_vuln_target_sourcetypes" Macro Definition, add all target indices. Note that the empty value of a Definition will by default consider all sourcetypes. Sample Definitions are shown below.
        - `(sourcetype="sample1" OR sourcetype="sample2")`
        - `(sourcetype="*" AND sourcetype!="sample1")`

    * In "intsights_vuln_target_indicator_fields" Macro Definition, add all "," (comma) separated target fields of Splunk events on which correlation will be performed. Note that the empty value of a field or empty Macro Definition is not allowed and will result in an error while running correlation savedsearches. Sample Definition is shown below.
        - `"signature", "signature_id", "cert", "cve"`

* The "intsights_vuln_retiring_days" macro can be configured for retirement of Vulnerabilities in provided days (Valid integer number or "").
    * Default is 180 days
    * If the user wants to remove only the Vulnerabilities with status "closed", then add "" in the macro definition.

* If the user does not want to disable the outgoing calls to tags and comments API, then no need to perform this step as it is "True" by default in the macro. But if user wants to disbale it, then do the below steps.
    * In "intsights_enable_tags_comments_api_calls" Macro definition, add "false". Sample Definition is shown below.
        - `false`
    * Any value other than any form of `Yes` and `True`, would be considered as false.

* NOTE: With 2.4.0 and later versions of the app, please use the Macro Configuration page, instead of directly configuring the macros from the settigs. Doing so may lead to some inconsistancies.

### Configure Savedsearches
* For configuring `batch_size` in `intsights_correlate_IpAddressess_iocs` , `intsights_correlate_Emails_iocs` , `intsights_correlate_Urls_iocs`, `intsights_correlate_Hashes_iocs` and `intsights_correlate_Domains_iocs` savedsearches, go to `Edit` -> `Edit Search` and edit `Search` field as specified below in `CUSTOM COMMANDS` section.
* For configuring `batch_size` in `intsights_correlate_unmatched_vulnerabilities` and `intsights_correlate_matched_vulnerabilities` savedsearches, go to `Edit` -> `Edit Search` and edit `Search` field as specified below in `CUSTOM COMMANDS` section.

* To configure custom types of alert other than default Splunk triggered alert for new indicator findings,
    - Go to `Settings` -> `Searches, reports and alerts`
    - Select "IntSights App for Splunk" in the App context.
    - In `intsights_alert_for_finding_new_indicators`, click on `Edit` -> `Edit Alert` which will open up Edit Alert pop-up.
    - Various configurations can be done for alert like Scheduling (Cron Expression), Time Range, Expires etc. Make sure to keep Scheduling interval and Time Range in sync. e.g Cron Expression: `*/30 * * * *` - TIme Range: `Last 30 minutes`.
    - Go to Trigger Actions part at the end in Form, click on `+ Add Actions`, select any custom alert action (Send email, Log Event, etc.), fill up if any configurations of that alert action, and then add it.

* To configure and customize alert based on index, reporting feeds and severity,
    - Go to `Settings` -> `Searches, reports and alerts`
    - Select "IntSights App for Splunk" in the App context.
    - In `intsights_alert_for_finding_new_indicators`, click on `Clone`.
    - Provide configuration details like Title, Description, App, Permissions and click on `Clone Alert`.
    - For cloned alert, click on Edit` -> `Edit Alert` which will open up Edit Alert pop-up.
    - Replace the where condition `where like(correlationIndices,"%")` with required filters/conditions.  
      For Example:  
        - To configure alert for index=sample, replace where condition with `where correlationIndices="sample"`  
        - To configure alert for severity=Low(10), replace the where condition with `where severity="Low(10)"`  
        - To configure alert for all the Low severity IOCs without considering the exact score, replace the where condition with `where like(severity, "Low%")`  
        - To configure alert for reportedFeedsName='Cyber Threat Alliance', replace the where condition with `where reportedFeedsName="Cyber Threat Alliance"` 
    - Provide other configuration as per requirements and Save it.
 
Note:
- Do not run correlation related savedsearches manually, it will result in rematch and will increase the match count again.

## CORRELATION LOGIC
* Field based correlation of IOCs and Splunk events will be performed. The fields of Splunk events to use in correlation can be specified in macro as shown in the `Configure Macro` section.
* Field based correlation of Vulnerabilities and Splunk events will be performed. The fields of Splunk events to use in correlation can be specified in macro as shown in the `Configure Macro` section.
* Tag (Splunk Match) and comment (Match Time) will be posted to the IntSights Platform that matched to indicator in Splunk Environment for the first time based on the macro 'intsights_enable_tags_comments_api_calls' defined in `Configure Macro` section.

## INVESTIGATION OF MATCHED IOCS
* By clicking on the `Investigation` button in the `Correlation Details` dashboard, it will redirect to Search Dashboard where it will run `intsightsinvestigateioc` custom command which will fetch investigation details of IOC from the IntSights Platform and will show it in Splunk's Search dashboard.

## RETIREMENT OF OLD IOCS
* Old IOCs (Matched/Unmatched) will get retired based on provided days in respective macros (Refer to `Configure macros` section) and will not be considered further in correlation/dashboard panels.
* "$SPLUNK_HOME/etc/apps/IntSightsAppForSplunk/bin/intsightsretirediocs.py" scripted input will be responsible to remove the retired IOCs. (To navigate: Go to Settings > Data inputs).
* Note that the retired IOCs won't be deleted from the Splunk index.

## RETIREMENT OF OLD ALERTS
* Only Closed alerts will be retired if user has provided blank string("") in the macro (Refer to `Configure macros` section).
* Old Alerts (Open/Close) will get retired based on provided days in respective macros (Refer to `Configure macros` section) and will not be considered further in dashboard panels.
* "$SPLUNK_HOME/etc/apps/IntSightsAppForSplunk/bin/intsightsretiredalerts.py" scripted input will be responsible to remove the retired Alerts. (To navigate: Go to Settings > Data inputs).
* Note that the retired Alerts won't be deleted from the Splunk index.

## RETIREMENT OF OLD VULNERABILITIES
* Only Closed vulnerabilities will be retired if user has provided blank string("") in the macro (Refer to `Configure macros` section).
* Old Vulnerabilities (Open/Close) will get retired based on provided days in respective macros (Refer to `Configure macros` section) and will not be considered further in dashboard panels.
* "$SPLUNK_HOME/etc/apps/IntSightsAppForSplunk/bin/intsightsretiredvulns.py" scripted input will be responsible to remove the retired Vulnerabilities. (To navigate: Go to Settings > Data inputs).
* Note that the retired Vulnerabilities won't be deleted from the Splunk index.

## SAVEDSEARCHES
This application contains the following saved searches

* **intsights_update_master_lookup_from_index** - Update IOCs (aggregated by value) from index to `intsights_master_lookup`.
* **intsights_correlate_IpAddressess_iocs** - Match IOCs of type IpAddressess from the  `intsights_master_lookup` against Splunk events.
* **intsights_correlate_Emails_iocs** - Match IOCs of type Emails from the  `intsights_master_lookup` against Splunk events.
* **intsights_correlate_Urls_iocs** - Match IOCs of type Urls from the  `intsights_master_lookup` against Splunk events.
* **intsights_correlate_Hashes_iocs** - Match IOCs of type Hashes from the  `intsights_master_lookup` against Splunk events.
* **intsights_correlate_Domains_iocs** - Match IOCs of type Domains from the  `intsights_master_lookup` against Splunk events.
* **intsights_backup_master_lookup** - Take backup of the IOCs from the `intsights_master_lookup` to `intsights_master_lookup_backup` for upgrade scenario.
* **intsights_accelarate_master_lookup** - Accelerate the `intsights_master_lookup` from the `intsights_master_lookup_backup` for upgrade scenario.
* **intsights_alert_for_finding_new_indicators** - Generate alert for findings of new indicators in Splunk
* **intsights_delete_whitelisted_iocs** - Remove the whitelisted IOCs from the `intsights_master_lookup` and `intsights_matched_lookup`.
* **intsights_ioc_total_count** - Responsible to populate the "Total IOCs", "Total IOCs by Type", "Total High Severity IOCs", "Total Medium Severity IOCs", "Total Low Severity IOCs" panels in IOC Overview dashboard.
* **intsights_ioc_last_week** - Responsible to populate the "New IOCs in Last Week" panel in IOC Overview dashboard.
* **intsights_ioc_last_day** - Responsible to populate the "New IOCs in Last Day" panel in IOC Overview dashboard.
* **intsights_ioc_timechart_last_day** - Responsible to populate the "Domain IOCs in Last Day", "Email IOCs in Last Day", "Hashes IOCs in Last Day", "IP Address IOCs in Last Day", "URL IOCs in Last Day" panel in IOC Overview dashboard.
* **intsights_matched_ioc_data** - Responsible to populate the Correlation Overview and Correlation Details dashboards.
* **intsights_alert_update_master_lookup_from_index** - Update Alerts (aggregated by _id) from index to intsights_alert_master_lookup.
* **intsights_alert_total_count** - Responsible to populate "Total Alerts", "Total Alerts by Type", "Total High Severity Alerts", "Total Medium Severity Alerts", "Total Low Severity Alerts" panels in Alerts Overview dashboard.
* **intsights_alert_last_month** - Responsible to populate the "New Alerts in Last Month" panel in Alerts Overview dashboard.
* **intsights_alert_last_week** - Responsible to populate the "New Alerts in Last Week" panel in Alerts Overview dashboard.
* **intsights_alert_last_day** - Responsible to populate the "New Alerts in Last Day" panel in Alerts Overview dashboard.
* **intsights_alert_timechart_last_day** - Responsible to populate "Attack Indication Alerts in Last Day", "Attack Indication Alerts in Last Day", "Phishing Alerts in Last Day", "Brand Security Alerts in Last Day", "Exploitable Data Alerts in Last Day", "VIP Alerts in Last Day" panels in Alerts Overview dashboard.
* **intsights_update_vuln_lookup_from_index** - Update Vulnerabilities (aggregated by id) from index to intsights_vuln_master_lookup.
* **intsights_correlate_unmatched_vulnerabilities** - Match Vulnerabilities from the `intsights_vuln_master_lookup` which are not in the `intsights_matched_vulnerabilities` lookup against Splunk events.
* **intsights_correlate_matched_vulnerabilities** - Match Vulnerabilities from the `intsights_matched_vulnerabilities` lookup against Splunk events and update with new matching details.
* **intsights_vuln_total_count** - Responsible to populate the "Total Vulnerabilities", "Vulnerabilities with Exploit", "Total Critical Severity Vulnerabilities", "Total High Severity Vulnerabilities", "Total Medium Severity Vulnerabilities", "Total Low Severity Vulnerabilities" panels in Vulnerability Overview dashboard.
* **intsights_vuln_last_month** - Responsible to populate the "New Vulnerabilities in Last Month" panel in Vulnerability Overview dashboard.
* **intsights_vuln_last_week** - Responsible to populate the "New Vulnerabilities in Last Week" panel in Vulnerability Overview dashboard.
* **intsights_vuln_last_day** - Responsible to populate the "New Vulnerabilities in Last Day" panel in Vulnerability Overview dashboard.
* **intsights_matched_vuln_data** - Responsible to populate the Vulnerability Correlation Overview and Vulnerability Correlation Details dashboards.
* **intsights_alert_for_finding_new_alerts** - Generate alert for findings of new alerts in Splunk.
* **intsights_alert_for_finding_new_cves** - Generate alert for findings of vulnerabilities in Splunk.
* **Threat - intsights_notable_events_for_indicators - Rule** - Generate Notable Events for findings of new indicators in Splunk.
* **Threat - intsights_notable_events_for_alerts - Rule** - Generate Notable Events for findings of new alerts in Splunk.
* **Threat - intsights_notable_events_for_cves - Rule** - Generate Notable Events for findings of new vulnerabilities in Splunk.
* **intsights_correlation_hashes_event_details** - Maitain details of correlated Hashes events from Splunk events.
* **intsights_correlation_urls_event_details** - Maitain details of correlated URL events from Splunk events.
* **intsights_correlation_emails_event_details** - Maitain details of correlated Email events from Splunk events.
* **intsights_correlation_ips_event_details** - Maitain details of correlated IPs events from Splunk events.
* **intsights_correlation_domain_event_details** - Maitain details of correlated Domain events from Splunk events.
* **intsights_remove_old_event_details** - Remove details of events correlated older than 7 days ago.
* **intsights_matched_ioc_event_details** - Responsible to populate the Correlation Details dashboard when user configured to maintain correlation event details.

## WORKFLOW ACTION
* Using workflow action, user can perform an action from Splunk to IntSights portal. Supported action is as below:
    * IntSights: Add to Whitelist - If the user triggers this workflow action then it will mark an IOC as whitelist on the IOC IntSights portal.
    Note: On whichever field user is performing workflow action, that field will be considered as IOC value and workflow action will mark that field value as a whitelist IOC on the IntSights portal.

## CUSTOM COMMANDS
This application contains the following custom commands

* **intsightsmatchiocs**
    - Description
        - Perform correlation of IntSights IOCs against Splunk events. The correlation will be done on fields of events passed to command.
    - Parameters
        - batch_size:
            - description: While performing correlation, Upload new founded indicators as soon as it exceed batch_size instead of at the end.
            - default: 500
            - type: Integer
        - ioc_type:
            - description: The IOC type for which the correlation is being performed.
            - type: String
        - backoff_factor:
            - description: In case of error, IOC fetching process will get backoff based on given factor (backoff_factor * (2^retry - 1)). e.g. 30 seconds, 90 seconds, 210 seconds, 450 seconds ... (upto max_retry times)
            - default: 30
            - type: Integer
        - max_retry:
            - description: In case of error, IOC fetching process will retry upto provided times. 
            - default: 4
            - type: Integer

    - Example
        - `<Main Search> | stats count by <target fields> <actionfields>, index | intsightsmatchiocs batch_size=500 ioc_type="Emails" backoff_factor=30 max_retry=4`

* **intsightsinvestigateioc**
    - Description
        - Fetch investigation of IOC from IntSights Platform and return it to caller.
    - Parameters
        - ioc_value:
            - description: Value of IOC for which investigation details will be fetched from IntSights Platform and will be shown in Splunk's search Dashboard.
            - type: String
    - Example
        - `| intsightsinvestigateioc ioc_value="<IOC Value>"`

* **intsightsdeletewhitelist**
    - Description
        - Remove the whitelisted IOCs from the intsights_master_lookup and intsights_matched_lookup.

* **intsightsmatchvuln**
    - Description
        - Perform correlation of IntSights Vulnerabilities against Splunk events. The correlation will be done on fields of events passed to command.
    - Parameters
        - batch_size:
            - description: While performing correlation, Upload new founded vulnerabilities as soon as it exceed batch_size instead of at the end.
            - default: 500
            - type: Integer
        - is_matched:
            - description: If true, correlation will be done only on Vulnerabilities having match count > 0 and if false, correlation will be done only on Vulnerabilities having match count = 0
            - default: false
            - type: Boolean
        - backoff_factor:
            - description: In case of error, Vulnerability fetching process will get backoff based on given factor (backoff_factor * (2^retry - 1)). e.g. 30 seconds, 90 seconds, 210 seconds, 450 seconds ... (upto max_retry times)
            - default: 30
            - type: Integer
        - max_retry:
            - description: In case of error, Vulnerability fetching process will retry upto provided times.
            - default: 4
            - type: Integer

    - Example
        - `<Main Search> | table <target fields> | intsightsmatchvuln batch_size=500 is_matched=true backoff_factor=30 max_retry=4`

## SEARCH
* To see ingested data for IOCs, select the `Search` tab. Search ``"`intsights_ioc_indices` sourcetype="intsights:indicator"``.
* To see ingested data for Alerts, select the `Search` tab. Search ``"`intsights_alert_indices` sourcetype="intsights:alert"``.
* To see ingested data for Vulnerabilities, select the `Search` tab. Search ``"`intsights_vuln_indices` sourcetype="intsights:vulnerability"``.

## TROUBLESHOOTING

### General Checks
* To troubleshoot IntSights App for Splunk, check $SPLUNK_HOME/var/log/splunk/ta_intsights*.log or user can search `index="_internal" source=*ta_intsights*.log` query to see all the logs on UI. Also, user can use `index="_internal" source=*ta_intsights*.log ERROR` query to see ERROR logs on the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.
* The following functionalities need the `admin_all_objects` capability to work properly. If it's not working properly check the capability of users.
    * Workflow action: `IntSights: Add to Whitelist`
    * Investigate matched IOCs
* If you notice that the correlation related searches are getting delayed then please contact the admin of your Splunk Instance to change the "max_rows_per_query" parameter under "kvstore" stanza in limits.conf from 50000 to 200000. 
* If you notice that in some time range, some IOCs are in the index but not in intsights_master_lookup then run the "intsights_update_master_lookup_from_index" savedsearch in that time range.
* If you notice that in some time range, some Vulnerabilities are in the index but not in intsights_vuln_master_lookup then run the "intsights_update_vuln_master_lookup_from_index" savedsearch in that time range.
* If you are getting this error while configuring Input "Error response received from server: Unexpected error "<class 'ValueError'>" from python handler: "IntSights account is not configured!". See splunkd.log/python.log for more details." then make sure to configure the IntSights account first by Navigating to the `Setup`-> `Configuration`.

### Data Collection Related
* If data collection is not working then ensure that the internet is active where a proxy is configured and also ensure that the kvstore is enabled.
* Check `ta_intsights_intsights_indicators.log` file for IOC,`ta_intsights_intsights_alerts.log` for Alerts and `ta_intsights_intsights_vulnerabilities.log` for Vulnerabilities.
* If data collection is not working and getting 422 error code in the logs then try to re-configure the account to resolve this issue.

### Correlation Related
* Note that if no events found/passed to custom commands in correlation saved searches then no logs will be generated for that run.
* For IOCs:
    * Check that `intsights_<ioc_type>_target_indicator_fields`, `intsights_<ioc_type>_target_indicator_fields`, `intsights_<ioc_type>_target_sourcetypes` and `intsights_<ioc_type>_target_indices`  macros are not empty and are configured as specified above in `Configure Macros` section. Here `<ioc_type>` refers to the IOC type for correlation.

        For example for savedsearch `intsights_correlate_IpAddressess_iocs`.
        Make sure all the following macros are correctly configured and enabled:

            intsights_ips_target_indices
            intsights_ips_target_sourcetypes
            intsights_ips_target_indicator_fields
            intsights_ips_target_indicator_action_fields

        Check `General Checks` of `TROUBLESHOOTING` as specified above.
    
    * Note that correlation is field based and it will only match to those Splunk events having value exactly same as IOC value.
    * Check `ta_intsights_intsightsmatchiocs.log` file for further analysis.
    * If you get any network or socket related internal server error due to heavy load on KV Store, increase the `backoff_factor` and   `max_retry` parameter of `intsightsmatchiocs` custom command that is used in all correlation related saved searches. Refer to `CUSTOM COMMANDS` section.
    * Check `ta_intsights_intsightsmatchiocs.log` file.
        Depending on the savedsearches that you enable and use for correlation of IOCs, ensure that the corresponding macros are configured and enabled.

* For Vulnerabilities:
    * Check that `intsights_vuln_target_indicator_fields` macro is not empty and all other macros are configured as specified above in  `Configure Macros` section. Check `General Checks` of `TROUBLESHOOTING` as specified above.
    * Note that correlation is field based and it will only match to those Splunk events having value exactly same as Vulnerability id.
    * Check `ta_intsights_intsightsmatchvulns.log` file for further analysis.
    * If you get any network or socket related internal server error due to heavy load on KV Store, increase the `backoff_factor` and   `max_retry` parameter of `intsightsmatchvuln` custom command that is used in all correlation related saved searches. Refer to    `CUSTOM COMMANDS` section.
    * Check `ta_intsights_intsightsmatchvulns.log` file.

* NOTE: With 2.4.0 and later versions of the app, please use the Macro Configuration page, instead of directly configuring the macros from the settigs. Doing so may lead to some inconsistancies.

### Dashboard Related
* After installing/upgrading the app, the "IOC Overview" dashboard panels will not populate until the following savedsearches are not run successfully.
    - intsights_ioc_total_count
    - intsights_ioc_last_day
    - intsights_ioc_last_week
    - intsights_ioc_timechart_last_day
    - intsights_matched_ioc_data
* After installing/upgrading the app, the "Actions" dropdown in "IOC > Correlation Details" dashboard will not populate until IOcs correlation savedsearches are run successfully and Macro intsights_target_indicator_action_fields is updated accordingly.
* Since the Action dropdown in "IOC > Correlation Details" is populated using the intsights_matched_iocs lookup, it will show list of all actions in the intsights_matched_iocs lookup instead of only the actions from the action fields defined in "intsights_target_indicator_action_fields" macro.
* After installing/upgrading the app, the "Alert Overview" dashboard panels will not populate until the following savedsearches are not run successfully.
    - intsights_alert_total_count
    - intsights_alert_last_day
    - intsights_alert_last_week
    - intsights_alert_last_month
    - intsights_alert_timechart_last_day
* After installing/upgrading the app, the "Vulnerability Overview" dashboard panels will not populate until the following savedsearches are not run successfully.
    - intsights_vuln_total_count
    - intsights_vuln_last_day
    - intsights_vuln_last_week
    - intsights_vuln_last_month
* If dashboard panels are not populating data, it is possible that App's Saved Searches has not yet encountered newly ingested data on their previous execution. Please check `Next Schedule Time` in `Settings` -> `Searches, reports and alerts`. Most likely the panels will be populated once all saved search completes their next execution.
* If User will restart the splunk and face the "| inputlookup" command or "kvstore" related error on the dashboard then the user has to wait for the successful next invocation of the following savedsearches.
    * For IOCs:
        - intsights_ioc_total_count
        - intsights_ioc_last_day
        - intsights_ioc_last_week
        - intsights_ioc_timechart_last_day
        - intsights_matched_ioc_data
    * For Alerts:
        - intsights_alert_total_count
        - intsights_alert_last_day
        - intsights_alert_last_week
        - intsights_alert_last_month
        - intsights_alert_timechart_last_day
    * For Vulnerabilities:
        - intsights_vuln_total_count
        - intsights_vuln_last_day
        - intsights_vuln_last_week
        - intsights_vuln_last_month
* If the user has a total number of IOCs of more than 5 million then we recommend the following step to avoid scalability and performance issues.
    - Contact the admin of your Splunk instance to change "max_rows_per_query" parameter under "kvstore" stanza in limits.conf from 50000 to 200000.
* `Correlation Indices` filter will contain only those indexes for which IOCs are correlated after upgrading the app to v1.2.0
* `Action` filter on Correlation Details dashboard will contain only those action values for which IOCs are correlated after upgrading the app to v2.0.0

Note: On drilldown of the `IOC` column in `Correlation Details` dashboard, search query will run in `All Time` if the earliest time is not found in any rare case.

Note: On drilldown of the `CVE ID` column in `Vulnerability Correlation Details` dashboard, search query will run in `All Time` if the earliest time is not found in any rare case.

### IOC Retirement Related
* Make sure that all macros related to IOC retirements are configured properly (Retiring Days in valid integer number) as specified in `Configure Macro` section.
* Check that scripted input named `$SPLUNK_HOME/etc/apps/IntSightsAppForSplunk/bin/intsightsretirediocs.py` is enabled and is successfully running without any error.
* Check `ta_intsights_intsightsretirediocs.log` file.

### Alert Retirement Related
* Make sure that all macros related to IOC retirements are configured properly (Retiring Days in valid integer number or "") as specified in `Configure Macro` section.
* Check that scripted input named `$SPLUNK_HOME/etc/apps/IntSightsAppForSplunk/bin/intsightsretiredalerts.py` is enabled and is successfully running without any error.
* Check `ta_intsights_intsightsretiredalerts.log` file.

### Vulnerability Retirement Related
* Make sure that all macros related to Vulnerability retirements are configured properly (Retiring Days in valid integer number or "") as specified in `Configure Macro` section.
* Check that scripted input named `$SPLUNK_HOME/etc/apps/IntSightsAppForSplunk/bin/intsightsretiredvulns.py` is enabled and is successfully running without any error.
* Check `ta_intsights_intsightsretiredvulns.log` file.

### Whitelist Delete Related
* Check `ta_intsights_intsightsdeletewhitelist.log` file.

### Investigation Feature Related
* Check `ta_intsights_intsightsinvestigateioc.log` file.

### Workflow Action Related
* Check `ta_intsights_intsightsaddtowhitelist.log` file.

### Email Alert Related
* If not receiving email alerts, please make sure that configuration under `Settings -> Server settings -> Email settings` are correct.

## Known Issues
* On the IOC Correlation Details dashboard, if one of the filter selected causes other filters to have no results it is observed that clicking on the default "All" option in the filter repopulates the filter with previous list of options in the dropdown.

## BINARY FILE DECLARATION

* bin/ta_intsights/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with MarkupSafe module and source code for the same can be found at https://pypi.org/project/MarkupSafe/
## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/IntSightsAppForSplunk
* Remove $SPLUNK_HOME/var/log/splunk/**ta_intsights_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Details:
    - Email: support@intsights.com
    - Phone: +1.877.744.1790 (Toll-Free)

### Copyright (c) IntSights Cyber Intelligence Ltd. All rights reserved.