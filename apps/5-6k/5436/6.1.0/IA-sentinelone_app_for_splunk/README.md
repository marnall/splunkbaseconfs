# SentinelOne Documentation

Allows a SentinelOne administrator or analyst interact with the SentinelOne product.

|                            |                                          |
|----------------------------|------------------------------------------|
| Version                    | 6.1.0                                    |
| Build                      | 20260511                                 |
| Splunk Enterprise Versions | 10.2, 10.1, 10.0, 9.4, 9.3, 9.2          |
| Platforms                  | Splunk Enterprise, Splunk Cloud          |
| Splunkbase Url             | <https://splunkbase.splunk.com/app/5433> |
| Author                     | Aplura, LLC                              |

## License

Apache License, Version 2.0 <https://www.apache.org/licenses/LICENSE-2.0.txt>

Copyright 2020-2024, Sentinel Labs, Inc.

## Initial Application Configuration

SentinelOne is configured from the `Application Configuration` menu option under the `Administration` menu.

### Macros

SentinelOne includes the following macros that control dashboard searches.

- None

### Sourcetype Definitions

|                                                      |                                                   |                                                                                                      |
|------------------------------------------------------|---------------------------------------------------|------------------------------------------------------------------------------------------------------|
| sourcetype                                           | SentinelOne API                                   | Description                                                                                          |
| sentinelone:channel:agents                           | web/api/v2.1/agents                               | S1 Agent information                                                                                 |
| sentinelone:channel:activities                       | web/api/v2.1/activities                           | S1 Console Activities                                                                                |
| sentinelone:channel:threats:event                    | web/api/v2.1/threats/\<threat_id\>/explore/events | Get all threat events                                                                                |
| sentinelone:channel:applications                     | web/api/v2.1/installed-applications               | Get Application Inventory                                                                            |
| sentinelone:channel:threats                          | web/api/v2.1/threats                              | Get the S1 Threats                                                                                   |
| IA-sentinelone_app_for_splunk:error:event               | Internal Error Logging                            | Errors that occur during threat event processing.                                                    |
| IA-sentinelone_app_for_splunk:error                     | Internal Error Logging                            | Errors that occur during processing.                                                                 |
| sentinelone:error                                    | Internal Error Logging                            | Deprecated                                                                                           |
| sentinelone:channel:groups                           | web/api/v2.1/groups                               | Get S1 Groups                                                                                        |
| sentinelone:channel:applications:cve                 | web/api/v2.1/installed-applications/cves          | Get known CVEs for applications that are installed on endpoints with Application Risk-enabled Agents |
| sentinelone:channel:application_management:risks     | web/api/v2.1/application-management/risks         | Get Application risks                                                                                |
| sentinelone:channel:application_management:inventory | web/api/v2.1/application-management/inventory     | Get Application Inventory                                                                            |
| sentinelone:channel:uam_alerts                       | unifiedalerts/graphql                             | Get UAM Alerts via GraphQL API                                                                       |

### Dashboards

SentinelOne includes the following dashboards.
- Application Configuration
  - Allows the Splunk admin to configure the inputs for ingestion.
- Application Health Overview (under the Administration menu option)
  - Use this page to get health and status information about any alerts, events, or API errors. View total_failures, messages, and severity level for each instance.
- Network
  - This dashboard shows Agent information by over time, as well as group information.
- Threats
  - This dashboard gives an overview of threats information in the console.
- Manage Agents Overview
  - This dashboard provides the ability to manage Sentinel agents.
- Manage Threats Overview
  - This dashboard provides the ability to manage incidents/threats.

### Saved Searches

SentinelOne includes the following saved searches. These searches need to be run in order to populate the management host and site name dropdowns on the dashboards. Fields from these lookups are also used in the dashboard panels.

- sentinelone_groups_lookup_generation
  - Search for populating the groups lookup with site id and site name
  - This should be enabled prior to enabling the inputs
  - It may need to be run on a one-time basis over "all time" to do the initial import of groups.

- sentinelone_lookup_generation
  - Search for populating the agents lookup
  - This should be enabled prior to enabling the inputs
  - It may need to be run on a one-time basis over "all time" to do the initial import of agents.

- sentinelone_activity_types_lookup_generation
  - Queries the API for current list of Activity Types.
  - Best guess is made for unknown values.
  - Re-populates the `sentinelone_activity_types` with the latest information.
  - Must be enabled after install.

### SentinelOne Inputs

SentinelOne includes the following channels for the SentinelOne inputs. Make sure the interval schedules are reviewed prior to enablement.

These inputs use `cron schedules`, documentation can be found here: <https://docs.splunk.com/Documentation/Splunk/latest/Admin/Inputsconf>

``` bash
To specify a cron schedule, use the following format:
  * "<minute> <hour> <day of month> <month> <day of week>"
  * Cron special characters are acceptable. You can use combinations of "*",
  ",", "/", and "-" to specify wildcards, separate values, specify ranges
  of values, and step values.
* The cron implementation for data inputs does not currently support names
  of months or days.
```

- Applications
  - Interval : Recommended at no more than once per hour. \`\`0 \* \* \* \* \`\`
- Groups
  - Interval : Recommended at no more than once per day. \`\`0 0 \* \* \*\`\`
- Threats
  - Interval : Environment dependant. Smaller environments may be able to support every 1 minute \`\`\* \* \* \* \*\`\`.
- Agents
  - Interval : Recommended at no more than once per day \`\`0 0 \* \* \*\`\`
- Activities
  - Interval : Environment dependant. Smaller environments may be able to support every 1 minute \`\`\* \* \* \* \*\`\`.
- Risks:
  - Interval : Environment dependant. Smaller environments may be able to support every 1 minute \`\`\* \* \* \* \*\`\`.
- UAM Alerts:
  - Interval : Environment dependant. Smaller environments may be able to support every 1 minute \`\`\* \* \* \* \*\`\`.
  - View Type : Optional filter (ALL, ENDPOINT, IDENTITY, CLOUD, THIRD_PARTY, CUSTOM_ALERTS). Defaults to ALL.

### About Lockfile Usage
The lock files were introduced to address a specific issue in Splunk Cloud environments where modular inputs were not completing before the next execution interval, causing data to never fully process. In multi-process environments like Splunk Cloud, modular inputs could start a new run on a different search head before the previous one finished, leading to duplication of efforts, incomplete data ingestion, and missed checkpoints. The lock file mechanism was added to prevent multiple instances of the same modular input from running simultaneously, ensuring that one input completes and writes out the checkpoint before another starts. This avoids the overload caused by pulling large amounts of data, especially in environments with high volumes of threats or agents.

In case of 'Splunk Victoria', this is the type of environment we would need to have the lock files.

However, in all other environments where our App is NOT installed on a Search Head cluster, the API will continue to pull and complete when finished before reaching out to the API on the next interval without the need of lock files. So decide accordingly while configuring the inputs in the application configuration page. 

Note: If the user enables the lockfile checkbox, they must provide the duration of the lockfile in seconds. The valid range for the lockfile duration is between 300 and 3600 seconds, inclusive. If you need the lockfile but require a custom duration, you can provide any value by updating the configuration. Alternatively, feel free to modify the `inputs.conf` file to change the duration value.

### About Bulk Import Limit
The Bulk Import Limit controls the maximum number of records fetched per run for snapshot channels (Applications, Agents, and Groups). These channels pull the entire dataset on every execution rather than incremental changes. The default minimum is 1,000,000. For non-snapshot channels (Threats, Activities, Risks, UAM Alerts), this setting is ignored and the default (1M) is always used.

The cron interval must allow sufficient time for the configured limit. The rule is  1 hour per 1,000,000 (1M) records (e.g., a limit of 2,000,000 requires at least a 2-hour gap between runs). The UI will block saving if the cron schedule is too aggressive for the configured limit.

Recommendation: Regardless of the configured bulk import limit, it is recommended to schedule snapshot channels (Applications, Agents, Groups) to run once per day (`0 0 * * *`) to ensure complete and consistent data ingestion without placing unnecessary load on the API.


### About Automatic Ingest Restart Usage
This feature was introduced to address an issue in Splunk where, in rare cases, the process ID (PID) of a data input may be terminated unexpectedly. When this happens, the input must be restarted manually. By enabling the newly introduced checkbox in the configuration, the system will automatically restart the input if it becomes stuck for more than 25 hours, preventing the need for manual intervention. This option is disabled by default for each input configured on the configuration page. If this feature is needed for your use case, you can enable it without affecting the pulling of previous data.


### Input Field Filtering

SentinelOne includes the ability to include or exclude fields that should be included when retrieving SentinelOne Inputs. Field filtering is configured under the `Application Configuration` dashboard on the `Fields` tab. You may specify fields that should be included for a channel or fields that should be excluded for a channel. If no filtering is defined for a channel all fields will be included by default.

If filtering nested JSON fields you should specify the field name with a "." between each key (e.g. `activeDirectory.computerMemberOf`). This will match the example below.

    {"activeDirectory": {"computerMemberOf": "CN=global"}}

A wild card is supported for arrays of information. (`activeDirectory.*.computerMemberOf`). This will match the example JSON below.

    {"activeDirectory": [{"computerMemberOf": "CN=global"}, {"computerMemberOf": "CN=global"}]}

Similarly, a wildcard is supported to target all elements in the array. (`activeDirectory.lastUserMemberOf.*`). This will match example JSON below.

    {"activeDirectory": {"lastUserMemberOf": ["data1", "data2", "data3"]}}

### Adaptive Alert Actions

SentinelOne includes the following adaptive alert actions.

- Network Control
  - Allows the Splunk admin to manage the network status for an agent.
  - *Action*
    - Connect or disconnect
  - *Management Host*
    - Connect or disconnect
  - *Site ID*
    - Site Id field
  - *Agent ID*
    - Agent Id field
- Threat Control
  - Allows the Splunk admin to configure the incident status and analyst verdict for a threat.
  - *Incident Status*
    - Unresolved, In Progress, or Resolved
    - In order to set the incident status to resolved a verdict must be specified
  - *Analyst Verdict*
    - Undefined, True Positive, Suspicious, False Positive
  - *Management Host*
    - Connect or disconnect
  - *Site ID*
    - Site Id field
  - *Threat ID*
    - Threat Id field

### Custom Commands

SentinelOne includes the following custom commands.

- sentineloneagentaction
  - Allows the Splunk admin to manage the network status for an agent.
  - *action_type*
    - Connect or disconnect
  - *management*
    - Connect or disconnect
  - *site_id*
    - Site Id field (defaults to siteId)
  - *agent_id*
    - Agent Id field (defaults to id)
  - Sample Usage
    - `index=sentinelone sourcetype="sentinelone:channel:agents" | fields id siteId | eval siteId=siteId."", management="testhost.sentinelone.net" | stats values(*) as * by id | sentineloneagentaction action_type=connect`
- sentinelonethreataction
  - Allows the Splunk admin to configure the incident status and analyst verdict for a threat.
  - *status*
    - Incident status
    - Unresolved, In Progress, or Resolved
    - In order to set the incident status to resolved a verdict must be specified
  - *verdict*
    - Undefined, True Positive, Suspicious, False Positive
  - *management*
    - Connect or disconnect
  - *site_id*
    - Site Id field (defaults to siteId)
  - *threat_id*
    - Threat Id field (defaults to id)
  - Sample Usage
    - `index=sentinelone sourcetype="sentinelone:channel:threats" | fields id siteId | eval siteId=siteId."", management="testhost.sentinelone.net" | stats values(*) as * by id | sentinelonethreataction status=resolved verdict=false_positive`
- sentineloneapi
  - Allows the SentinelOne API to be quried for specific actions
  - *management*
    - The Management host to use (from search results)
  - Current Features
    - `activity_types`: pulls the activity types from the configured APIs.
  - Sample Usage
    - `| rest "/servicesNS/-/IA-sentinelone_app_for_splunk/configs/conf-authhosts" splunk_server=local | fields + url | rename url as management | sentineloneapi activity_types`
    
### Monitoring Console Health Checks

SentinelOne includes the following health checks in the Monitoring Console health check list(`default/checklist.conf`).

- SentinelOne_HealthCheck
  - Provides basic Yes/No if there is SentinelOne data present.

## Legacy Data

This extension introduces new sourcetypes that are more inline with best practices. If the extension is being upgraded from an existing version of the SentinelOne app, these instructions can be followed to allow "overlap" of the data sources. Each of the different sourcetypes will follow the same procedure to enable searching on the old data, concurrent with the new data.

The steps are as follows, and should be done in `local/eventtypes.conf`:

1.  Update and enable the legacy index event type `sentinelone_legacy_index` with the index that contains the legacy data.

### Agents

- Update and enable the `sentinelone_legacy_agents` event type.

- Add `sentinelone_legacy_agents` to the `sentinelone_agents` event type

  - `eventtype IN (sentinelone_updated_agents, sentinelone_legacy_agents)`

### Threats

- Update and enable the `sentinelone_legacy_threats` event type.

- Add `sentinelone_legacy_threats` to the `sentinelone_threats` event type

  - `eventtype IN (sentinelone_updated_threats, sentinelone_legacy_threats)`

### Activities

- Update and enable the `sentinelone_legacy_activities` event type.

- Add `sentinelone_legacy_activities` to the `sentinelone_activities` event type

  - `eventtype IN (sentinelone_updated_activities, sentinelone_legacy_activities)`

### Groups

- Update and enable the `sentinelone_legacy_groups` event type.

- Add `sentinelone_legacy_groups` to the `sentinelone_groups` event type

  - `eventtype IN (sentinelone_updated_groups, sentinelone_legacy_groups)`

## Lookups

The SentinelOne contains the following lookup files.

|                            |                                      |                                      |
|----------------------------|--------------------------------------|--------------------------------------|
| Transform                  | Filename                             | Description                          |
| sentinelone_activity_types | sentinelone_activity_types_5.2.0.csv | Describes SentinelOne Activity Types |

## Scripts and binaries

|                                     |                                                                        |
|-------------------------------------|------------------------------------------------------------------------|
| Diag.py                             | This is to assist in diag creation for support.                        |
| cim_actions.py                      | Splunk Alert Actions Support script                                    |
| s1_client.py                        | Class to allow access to S1 in support of Mod inputs and Alert actions |
| s1_upgrader.py                      | Modular input run on startup to check and upgrade the app.             |
| sentinelone.py                      | Modular Input script file.                                             |
| AlertAction.py                      | Helper file for Alert Actions                                          |
| ModularInput.py                     | Helper file for Modular Inputs                                         |
| Utilities.py                        | Helper file for Utilities                                              |
| version.py                          | Technical Version of the app.                                          |
| sentinelone-network-control.py      | This is the script for the Network Control adaptive alert action.      |
| sentinelone-threat-control.py       | This is the script for the Threat Control adaptive alert action.       |
| sentinelone_cmd_agent_action.py     | This is the script for the Agent Control custom command.               |
| sentinelone_cmd_threat_action.py    | This is the script for the Threat Control custom command.              |
| s1_alert_action.py                  | Class with base Alert Action object                                    |
| s1_command.py                       | Class with base Search Command object                                  |
| s1_utilities.py                     | Class with specific S1 related utilities                               |
| app_properties.py                   | Dynamically generated to help with multiple classes and loggers        |
| \_paths.py                          | Global import to target `lib` folder.                                  |

## Event Generator

SentinelOne does not include an event generator.

## Acceleration

- Summary Indexing: No

- Data Model Acceleration: No

- Report Acceleration: No

## Indexed Fields

There is one indexed field:

- `siteName`

## Upgrader

SentinelOne includes an updater to assist in upgrades to the app. It is a modular input with stanza `s1_upgrader://DF945543-967A-4488-975E-757F4D5E2B41`.

## Known Issues

Versions prior to 5.2.0 have the following known issues:

- Due to Changes in S1 API parameter enforcement, enhancing inputs with "Threat Events" may cause errors.
- Affected S1 Management Consoles: `W#91` or newer,

**WORKAROUND**: This is a code update. In the file `s1_client.py`, find the line

    resp = self.s1_mgmt.threat_explore.get_events(threat_id)

Update this line to read:

    resp = self.s1_mgmt.threat_explore.get_events(threat_id, limit=1000)

This will resolve the error, and allow threat event ingest.

Version 5.2.6 of SentinelOne has the following known issues:

- If the `mgmt_sdk` log outputs at any level, the search command will fail with `Error in command: Invalid message received from external search command during search, see search.log.`

  - This is only at the final phase of execution. The command most likely functions correctly prior to that.

# Installation

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements ](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

### Download

Download SentinelOne at <https://splunkbase.splunk.com/app/5433>.

## Deployment Guide

**Note: Do not install Add-Ons and Apps on the same system.**

- Single Instance 

  - (Pre-requisite) [Splunk CIM Add-on](https://splunkbase.splunk.com/app/1621/)

  - Only the SentinelOne App ([IA-sentinelone_app_for_splunk](https://splunkbase.splunk.com/app/5433/>))

- Single Instance + Heavy Forwarder 

  - Single Instance:

    - (Pre-requisite) [Splunk CIM Add-on](https://splunkbase.splunk.com/app/1621/)

    - SentinelOne App ([IA-sentinelone_app_for_splunk](https://splunkbase.splunk.com/app/5433/>))

  - Heavy Forwarder: IA-sentinelone_app_for_splunk ([IA-sentinelone_app_for_splunk](https://splunkbase.splunk.com/app/5436))

- Distributed deployment 

  - Heavy Forwarder: IA-sentinelone_app_for_splunk ([IA-sentinelone_app_for_splunk](https://splunkbase.splunk.com/app/5436))

  - Search Head:

    - (Pre-requisite) \`Splunk CIM Add-on <https://splunkbase.splunk.com/app/1621/>\`\_

    - SentinelOne App ([IA-sentinelone_app_for_splunk](https://splunkbase.splunk.com/app/5433/>))

  - Indexer: TA-sentinelone_app_for_splunk ([TA-sentinelone_app_for_splunk](https://splunkbase.splunk.com/app/5435))

- Splunk Cloud

  - Contact Splunk Cloud Support handle this installation.

# Release Notes

## Version 6.1.0
* New Features
  * Exposed `Bulk Import Limit` as a configurable field in the Application Configuration UI for snapshot channels (Applications, Agents, Groups)
    * Minimum: 1,000,000 (default). Values below the minimum are automatically clamped.
    * UI validates cron interval against the configured limit (1 hour per 1M records)
  * Added `Separate STAR Details` toggle for Threats channel
    * STAR alert details can be emitted as a dedicated `threats:star_details` sourcetype
  * Added `Separate Indicators` toggle for Threats channel
    * Threat indicators can be emitted as a dedicated sourcetype for improved extraction

## Version 6.0.0
* New Features
  * Added UAM Alerts channel for ingesting alerts from SentinelOne's GraphQL API
    * Supports view type filtering (ALL, ENDPOINT, IDENTITY, CLOUD, THIRD_PARTY, CUSTOM_ALERTS)
    * Includes OCSF-compliant severity_id mapping
    * Dual-query strategy ensures complete alert coverage (updatedAt + createdAt)
  * Added `alert_title` field to threat events
    * STAR alert titles are now propagated to associated threat events
    * Enables single-search discovery of threats and their events by alert name

## Version 5.2.6
* Changes
  * Implemented automatic input restarts if the data ingestion process is delayed or gets stuck for more than 25 hours. This ensures the system remains responsive by automatically restarting the input.

## Version 5.2.5
* Changes
  * Removed the system status check API call from the Modular inputs.
  * Updated Python dependencies to the latest versions: Splunk SDK to 2.1.0 and six to 1.17.0.
  * Updated the 'Manage Threats' table query to facilitate updates to the Management, ComputerName and Username field values.


## Version 5.2.4
* Bug Fix
  * Fixed the threat and agent actions.
* Changes
  * Updated `lock file mechanism`, now this is user configurable.
  
## Version 5.2.3

* Bug Fix
  * The Index dropdowns will support more than 30 indexes.
  * Fixed incorrect JS import on certain dashboards.
* Changes
  * Updated `lock` timeout to 1h (3600 seconds)
  * Updated retry options

## Version 5.2.2

* Bug Fix
  * The Index dropdowns will support more than 30 indexes.

## Version 5.2.1

* Improvements
  * The "Applications" input for  S1 Cloud Management Consoles will consume the inventory of applications.
    * There is no change for On-Prem S1 Management Consoles.
* New Feature 
  * The "Risk" input will allow for CVE based inventory of Applications.
    * This will not work on On-Prem S1 Management Consoles.
* Bug Fix
  * For extremely large threat events, with storyline events enabled, the input may cause a concurrency issue when running in Splunk Cloud stacks. 
    * A "lock file" has been implemented to alleviate the concurrency issues.
  * A max of 1000 threat events will be pulled for any given threat.
  * 
## Version 5.2.0

- Improvements
  - Modular Inputs have been changed to cron intervals.
    - Existing input intervals are not affected.
    - New or updates to inputs will need to follow the cron expressions for Splunk.
    - Example: `0 0 * * *` ← Every day at midnight.
  - CIM 5.1 review
  - Applications input uses a new S1 API endpoint to reduce load on ingest.
  - Threats are now enhanced with STAR Details (if applicable)
- Splunk Cloud
  - Updated lookups to versioned, to allow lookups to be updated in Splunk Cloud
  - Retry on Errors
    - Status codes 502, 503, and 504 are added to the forced list to perform retries.
- New Features
  - Command `sentineloneapi` allows a user to query for the following API calls
    - `activity_types`
  - Saved Search `sentinelone_activity_types_lookup_generation`
    - Disabled by default (enable to run)
    - Re-generates the activity types lookup daily, based on current API results.
  
## Version 5.1.9

- Updated Field Options dropdown to not discard already configured values
- Enforce SSL usage by default on Proxy configurations.

## Version 5.1.8

- Updated base index configuration section on Application Configuration setup page.

  - **Upgrade Note:** Original configuration values will work, but should be re-configured to support the new UI component.

- Fixed: For certain inputs, adding a filtering field configuration caused only a single event to be returned. This has been rectified to return all items.

## Version 5.1.7

- added field filtering for nested JSON

## Version 5.1.6

- added field filtering to Modular Input

## Version 5.1.5

- hotfix to allow the IA/TA to have the correct logging configuration file

- added field filtering to Modular Input

## Version 5.1.4

- updated Manage Agents to use correct agent id field, and better verbiage on errors.

- increased base limit of api pulls to 1000 (200 for groups API)

- added a `Logging` tab to enable log levels on configured items via UI.

- removed guid from Modular Input logging file name.

## Version 5.1.3

- updated app.conf for simple trigger reloads

- updated Application Configuration Page to correctly update API token

- updated Application Configuration Page to simplify base index configuration

- updated Diag collection to account for non-standard Splunk install locations

## Version 5.1.2

- Updated dashboards to be compliant with v1.1 SimpleXML and jquery 3.5

- Better error management and reporting within modular inputs

- Fixed Proxy issues with modular inputs

## Version 5.1.0

- New Features

  - Dashboard - Manage Agents Overview

  - Dashboard - Manage Threats Overview

  - Adaptive Alert - Network Control

  - Adaptive Alert - Threat Control

  - Custom Command - agentaction

  - Custom Command - threataction

# Troubleshooting

## Actions

- Check the Monitoring Console (`>=v6.5`) for errors

## Questions and answers

Access questions and answers specific to SentinelOne at <https://answers.splunk.com>. Be sure to tag your question with the name of the app: "SentinelOne".

## Support

- Support Email: <support@sentinelone.com>
- Support Offered: Splunk Answers, Community Engagement, Email
- 
Please create a support request here https://community.sentinelone.com/s/login/?ec=302&startURL=%2Fs%2F or call *1-855-868-3733 <tel:18558683733>*.

## Diagnostics Generation

If a support representative asks for it, a support diagnostic file can be generated. Use the following command to generate the file. Send the resulting file to support.

    $SPLUNK_HOME/bin/splunk diag --collect=app:IA-sentinelone_app_for_splunk

This file should be collected on the node/instance that is presenting with an issue. If a Heavy Forwarder is being used for inputs, but no data is being collected, perform the command on the Heavy Forwarder. If the alert actions or search commands are not working, run the diagnostic on the Search Head(s) in question.

# Troubleshooting

This section provides some tips for troubleshooting the SentinelOne application.

- Enable debug logging for modular inputs, alert actions, and custom commands

  - Copy `default/log.cfg` to `local/log.cfg`. Edit `local/log.cfg` and change the logging level for each component to "DEBUG" to get debugging messages

  - Specific logging names can be found using `index=_internal action=logger_name`

  - Examples

        [IA-sentinelone_app_for_splunk]
        modularinput=DEBUG
        restclient=DEBUG
        utilities=DEBUG
        kenny_loggins=WARN
        sentinelone=DEBUG
        s1_client=DEBUG
        sentinelone-threat-control=DEBUG
        sentinelone-network-control=DEBUG
        sentinelone_cmd_threat_action=DEBUG

- Application Configuration

  - If nothing appears under the "Application Configuration" header on the application configuration dashboard you can check for web page errors

    - Firefox: `Tools, Web Developer, Web Developer Tools`. Errors will display in the console tab

    - Chrome: `Customize and control Google option (right hand corner of the address bar), More Tools, Developer Tools`

- Helpful searches

  - SentinelOne creates several log files that reside in `$SPLUNK_HOME/var/log`. These are indexed in to the Splunk environment in the "\_internal" index. To view these log files you can run the following search:

        index=_internal source="*sentinelone*"

  - The base index contains a sourcetype sentinelone:error that contains error information from the modular input and alert actions. This search will retrieve these logs:

        eventtype=sentinelone_base_index sourcetype="*error*"

- Common Issues

  - Some of the common issues include:

  - Proxy Error. Check that the proxy settings are correct.

        index=_internal source="*sentinelone*" ProxyError

- Configurations Dashboard

  - There is a dashboard that is not within the navigation. It can be loaded using the following url: `https://<yourSplunk>/<language>/IA-sentinelone_app_for_splunk/sentinelone_current_configurations/`. This dashboard displays configured information for each input, and how they interact with each other configuration.

# Third-party software

## Aplura, LLC Components

Components Written by Aplura, LLC Copyright © 2016-2024 Aplura, ,LLC

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
