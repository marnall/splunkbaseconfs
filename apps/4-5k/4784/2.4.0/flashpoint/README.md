# Flashpoint App for Splunk

## OVERVIEW

Flashpoint App for Splunk allows you to leverage the Flashpoint platform's Indicators, Compromised Credentials, Ransomware, Alerts, Reports, and CVEs(including Exploits and Mentions) within your Splunk instance.

- Author - Flashpoint
- Version - 2.4.0
- Build - 1

## Compatibility Matrix
* Splunk version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Python version: Python3
* Browser Support: Chrome and Firefox

## Recommended System Configuration

- Standard Splunk configuration of Search Head, Indexer, and Forwarder.
- The Flashpoint Add-on for Splunk should be installed on the heavy forwarder and Search Head and the Flashpoint App for Splunk should be installed on the Search Head.

## Installation

This App can be installed through UI using the following steps.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click the `install app from file`.
3. Click `Choose File` and select the flashpoint App installation file.
4. Click on `Upload`.

Install from the command line using the following command:
`sh $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/flashpoint-<version>.spl/`

## Release Notes

### Version: 2.4.0
- Enhanced the Matching Configurations tab to support multiple IOC types, each with its own configuration.
- Introduced a new workflow action for on-demand Alert investigation to retrieve and view Alert details dynamically.

### Version: 2.3.0
- Enhanced performance of Indicators v2 dashboard by migrating indicator data to datamodel.
- Removed the Indicators (Deprecated) dashboard.
- Renamed the CVEs dashboard to Vulnerabilities.

### Version: 2.2.0
- Added new dashboard for Indicators input type v2.
- The original indicators dashboard is now labeled "Indicators (Deprecated)."

### Version: 2.1.0
- Fixed bugs in "Matching Configuration" dashboard.
- Updated the Splunk SDK version.

### Version: 2.0.0
- Updated the dashboards to use Ignite fields.
- Removed 'Exploits' and 'Ransomware' dashboards.

### Version: 1.3.0
- Upgraded Splunk SDK to v1.7.3

### Version: 1.2.0
- Added new dashboards named "Compromised Credentials", "Ransomware" and "Alerts"
- Added new panels in the "Overview" Dashboard.
- Added Indicator Matching correlation search.

## Upgradation

### Upgrading to version 2.4.0

Before upgrading please follow below steps.

1. Navigate to Settings → Searches, Reports, and Alerts.
2. Search for `perform_matching` in the Name column and click Edit.
3. If the saved search is enabled, disable it first.
4. After the update, you will need to reconfigure the Matching Configurations.

### Upgrading to version 2.3.0

- No additional steps are required after the upgrade.

### Upgrading to version 2.2.0

- No additional steps are required after the upgrade.

### Upgrading to version 2.1.0

- No additional steps are required after the upgrade.

### Upgrading to version 2.0.0

- No additional steps are required after the upgrade.

### Upgrading to version 1.3.0

- No additional steps are required after the upgrade.

### Upgrading to version 1.2.0

- No additional steps are required after the upgrade.

### Upgrading to version 1.1.1

Follow the below steps to upgrade the App to 1.1.1

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click the `install app from file`.
3. Click the `Choose File` button and select the flashpoint App installation file and checked the `Upgrade app` checkbox.
4. Click on `Upload`.

Once the installation is complete, restart Splunk. Now go to the matching configuration page to set up the indexes and the time range from which the matching of the IOCs should execute. Note that if this setup is not done, then the app will start the matching of events from the last 1 hour by default.

## Application Setup

- In the Matching Configuration page, configure the following fields.

1.  Index: It is a multi-select field. The user can select multiple indexes from which they want to match the IOCs. The default value is ' All ' i.e. search in all the indexes.
    - To improve the performance of matching logic, reduce the scope of the search by adding only indices where you want to search to avoid searching in all indices by default.
2.  Start Time: It is a Time-Range filter. The user can select the time from which they want to start the matching of the IOCs. The default value is the last 7 days. Note that this Start Time means from which date/time does the user wants to start matching the events, hence, this will be applicable on the first time of the configuration i.e. when the user saves the configuration for the first time, the app will start matching the events since the Start Time till the current time. Once this matching is completed, then the next subsequent matching logic will be invoked every hour automatically by the saved search and it will match the events from the last 1 hour.

## Saved Searches

- This Application contains the following Saved Searches.

| Saved Searches Name                            | Description                                                                                 | Interval                              | Default Status |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------- | -------------- |
| `populate_lookup`                              | Populate list_iocs lookup                                                                   | 24 hours                              | Enabled        |
| `perform_matching`                             | Perform matching and populate matched_lookup based on matching                              | 1 hour(mathces data for last 60 mins) | Enabled        |
| `flashpoint_populate_domain_intel`             | Get domains from list_iocs lookup and populate data in flashpoint_domain_intel lookup       | 30 mins                               | Disabled       |
| `flashpoint_populate_email_intel`              | Get emails from list_iocs lookup and populate data in flashpoint_email_intel lookup         | 30 mins                               | Disabled       |
| `flashpoint_populate_file_intel`               | Get file hash from list_iocs lookup and populate data in flashpoint_file_intel lookup       | 30 mins                               | Disabled       |
| `flashpoint_populate_http_intel`               | Get URLs from list_iocs lookup and populate data in flashpoint_http_intel lookup            | 30 mins                               | Disabled       |
| `flashpoint_populate_ip_intel`                 | Get IPs from list_iocs lookup and populate data in flashpoint_ip_intel lookup               | 30 mins                               | Disabled       |
| `flashpoint_populate_registry_intel`           | Get registry from list_iocs lookup and populate data in flashpoint_registry_intel lookup    | 30 mins                               | Disabled       |
| `flashpoint_populate_service_intel`            | Get service hash from list_iocs lookup and populate data in flashpoint_service_intel lookup | 30 mins                               | Disabled       |
| `Threat - Flashpoint Matched Indicator - Rule` | Generate Notable Events for new sightings from Flashpoint Matched Indicators data in Splunk | 30 mins                               | Disabled       |

## Workflow Action

 This Application contains the following Workflow Actions

### Flashpoint - Get addition alert information
#### Steps to Use the Flashpoint - Get addition alert information Workflow action

1. Search for alert data in your Splunk instance.
   - Ex: `index=flashpoint_index sourcetype="flashpoint_intelligence:alerts`
2. Expand the alert event you want to investigate by clicking the `>` icon on the left-hand side.
3. Locate the `resource.id` field, click the `∨` dropdown, and select
`Flashpoint – Get Additional Alert Information`.
4. This will redirect you to `Alert Investigation` Dashboard where you need to select the Source and Account filters and a panel will get populated with Alert informations.

## Custom Command

- This Application contains the following custom commands

1. `matchiocs`: This custom command is used to match flashpoint IOCs with Splunk's selected indexes.
2. `mentiondetail`: This custom command is used to generate a mention details table.
3. `flashpointadhoc`: This custom command is used to retrieve and generate alert information for the on-demand dashboard.

## Lookups

- This Application contains the following lookups

| Lookup Name                 | Description                       |
| --------------------------- | --------------------------------- |
| `list_iocs`                 | Stores the list of unique IOCs    |
| `matched_lookup`            | Stores the list of matched events |
| `flashpoint_domain_intel`   | Stores the list of domain IOCs    |
| `flashpoint_email_intel`    | Stores the list of email IOCs     |
| `flashpoint_file_intel`     | Stores the list of file hash IOCs |
| `flashpoint_http_intel`     | Stores the list of URL IOCs       |
| `flashpoint_ip_intel`       | Stores the list of IP IOCs        |
| `flashpoint_registry_intel` | Stores the list of registry IOCs  |
| `flashpoint_service_intel`  | Stores the list of service IOCs   |

## Macros

### `flashpoint_index`

- It is used for searching flashpoint events from the index.
- By default, it will search from all index
- To improve the performance of searches using this macro, update this macro to only search in indices where flashpoint data is collected.

| Macro Name                           | Description                                                         |
| ------------------------------------ | ------------------------------------------------------------------- |
| `flashpoint_indicators`              | Splunk query for retriving Flashpoint Indicator Events              |
| `flashpoint_reports`                 | Splunk query for retriving Flashpoint Report Events                 |
| `flashpoint_cves`                    | Splunk query for retriving Flashpoint CVE Events                    |
| `flashpoint_cve_mentions`            | Splunk query for retriving Flashpoint Mention Events                |
| `flashpoint_compromised_credentials` | Splunk query for retriving Flashpoint Compromised Credential Events |
| `flashpoint_alerts`                  | Splunk query for retriving Flashpoint Alert Events                  |
| `flashpoint_ransomware`              | Splunk query for retriving Flashpoint Ransomware Events             |

### Steps to update the macro

1. Go to `Settings` -> `Advanced Searches` -> `Search macros`
2. Select `Flashpoint App for Splunk` in `App`, `Any` in `Owner`, and `Created in App` in the last dropdown
3. Click on the macro which you want to edit
4. Update macro search and click on save

## Search

To see data logged by `Flashpoint`, select the `Search` tab and click on `Data Summary`. Follow the given source types for data fetching.

| Data Type               | Sourcetype                                        |
| ----------------------- | ------------------------------------------------- |
| Indicators              | `flashpoint_intelligence`                         |
| Reports                 | `flashpoint_intelligence:reports`                 |
| CVEs                    | `flashpoint_intelligence:cve`                     |
| Mentions                | `flashpoint_intelligence:mentions`                |
| Alerts                  | `flashpoint_intelligence:alerts`                  |
| Ransomware              | `flashpoint_intelligence:ransomware`              |
| Compromised Credentials | `flashpoint_intelligence:compromised_credentials` |

You can also enter search parameters in the search box to filter events.

## Splunk ES - Threat Intelligence

To integrate the Flashpoint App with Enterprise Security, follow the below mentions steps.

1. Login into Splunk Web and navigate to Apps > Flashpoint App for Splunk.
2. Click on the `Settings` dropdown and select the `Searches, reports, and alerts` option.
3. Select the saved search for which you want to download thread intelligence data.
4. Click on the `Edit` dropdown from the `Actions` column.
5. Select the `Enable` option from the list to enable the saved search.
6. Now, Navigate to Apps > Enterprise Security in the navigation bar.
7. In the Enterprise Security app, click on the `Configure` tab.
8. Navigate to `Data Enrichment` > `Intelligence Downloads`.
9. Click on the `New` Button.
10. Fill out all the mandatory fields in the form.
11. For the URL field, select the appropriate URL name from the given table.

| URL Name                           | Purpose                                                                              |
| ---------------------------------- | ------------------------------------------------------------------------------------ |
| lookup://flashpoint_domain_intel   | Integrate Flashpoint Intelligence's domain data with Enterprise Security App         |
| lookup://flashpoint_email_intel    | Integrate Flashpoint Intelligence's email data with Enterprise Security App          |
| lookup://flashpoint_file_intel     | Integrate Flashpoint Intelligence's file intel data with Enterprise Security App     |
| lookup://flashpoint_http_intel     | Integrate Flashpoint Intelligence's http intel data with Enterprise Security App     |
| lookup://flashpoint_ip_intel       | Integrate Flashpoint Intelligence's ip intel data with Enterprise Security App       |
| lookup://flashpoint_registry_intel | Integrate Flashpoint Intelligence's registry intel data with Enterprise Security App |
| lookup://flashpoint_service_intel  | Integrate Flashpoint Intelligence's service intel data with Enterprise Security App  |

> Note: To populate the data in Enterprise Security, relevant saved search must be enabled in the app.

For more info, visit:

https://docs.splunk.com/Documentation/ES/5.3.0/Admin/Downloadthreatfeed

## Enterprise Security - Correction Savedsearch Configuration

### To change the configuration of Correction Savedsearch

1. Open `Enterprise Security` App
2. Go to `Configure` -> `Content` -> `Content Management` Dashboard
3. Select `Flashpoint App for Splunk` in the `App` dropdown.
4. To Enable/Disable the Correlation savedsearches, Click on the respective button in the `Actions` column of the table.
5. To change the detailed configuration of a specific correlation search, click on the name of the Savesearch for which you want to change the configuration
6. In edit form, the `Time Range` section
   - Updating `Cron Schedule` changes how frequently saved search should run.
   - Updating `Earliest Time` changes how far to look for events in past for matching.
7. In edit form, the `Throttling` section
   - Updating `Window duration` will prevent creating notable again in provided window duration, if the same type of event matches. This will help in changing the suppression feature.

Note:
- `Earliest Time` should have a larger time range than the `Cron Schedule` interval to avoid missing any Splunk events.
- Any update to correlation savedsearch will clear the suppression data for existing notables so notables can be duplicated for provided `Earliest Time`.

### To add new fields in the `Additional Fields` section when a Notable event is expanded in the `Incident Review` Dashboard of ES

Steps:
1. Open Splunk ES, click Configure -> Incident Management -> Incident Review Settings
2. Scroll down and go to section `Incident Review - Event Attributes`
3. Click on the `Add new entry` button at the end.
4. Form will pop up with fields `Label` and `Field`. The value of `Field` can be any field coming in a notable event that you want to show in the `Additional Fields` section.
5. Click on `Done`. The added field will start showing in the `Additional Fields` section of notables in the `Incident Review` dashboard, which has the given field.

#### Recommended Fields that can be added in `Additional Fields`

* Threat - Flashpoint Matched Indicator - Rule

| Label               | Field      |
| ------------------- | ---------- |
| IOC Value           | value      |
| IOC Type            | type       |
| Matched Event Time  | event_time |
| Matched Event Index | orig_index |
| Matched Event       | event      |

Note: To avoid conflict with the existing index field (with the value "notable"), Splunk converts the given "index" field to "orig_index" when creating a notable event

For more details, refer to the Splunk blog post https://www.splunk.com/en_us/blog/security/modifying-the-incident-review-page.html

## Troubleshooting

- If you do not see any results in panels Try to increase the Time Range filter provided in the top left corner.

- Sometimes in panels' drill down, event count can have a mismatch due to Splunk taking a specific time range in drill down compared to the original search in the panel.

- If you are facing a performance issue in indicator matching logic, then reduce the matching scope by updating matching indices as specified in the `Matching Configuration Page Guide` section.

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/flashpoint
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## Contact

Contact Information: https://www.flashpoint-intel.com/contact-us

## Copyright

- (c) Flashpoint 2026
