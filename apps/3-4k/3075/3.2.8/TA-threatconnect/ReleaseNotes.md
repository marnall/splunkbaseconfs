# 3.2.8

-   APP-3375 - Fixed invalid result count type issue that prevents searches from running properly.

# 3.2.7

-   APP-3022 - Updated UI to sanitize tags strings before displaying.
-   APP-3075 - Upgraded Python dependencies including splunk-sdk (version 1.16.16).
-   APP-3076 - Added Owner filter for the custom and datamodel search configuration.
-   APP-3077 - Added ThreatAssessScore filter for the custom and datamodel search configuration.
-   APP-3078 - Added ThreatAssessScore filter on the indicator download configuration.
-   APP-3123 - Reworked Javascript/HTML pages for easier support.
-   APP-3341 - Updated data model data command to remove all previous entries before updating.

# 3.2.6

-   Updated app.conf [triggers] stanza for the tc_setup/password configuration file.
-   Updated tc_clear command query usage.

# 3.2.5

-   Updated search command to fix issue with timing on secondary search.
-   Updated variable definition for alert_actions.conf.
-   Added app.conf [triggers] stanza for the tc_setup.conf configuration file.

# 3.2.4

-   Updated proxy logic to fix issue where no proxy user/pass is provided.

# 3.2.3

-   Updated group download command to store all base metadata (e.g. dateAdded, type, and webLink).

# 3.2.2

-   Updated group download command to store all base metadata (e.g. dateAdded, webLink).

# 3.2.1

-   Updated custom/datamodel search logic to improve performance when downloading results.

# 3.2.0

-   Update all Python code to support Python 3 only.
-   Renamed Connectivity test to Pre-flight checks.
-   Changed label on Indicator Download Exclude Tag checkbox to specify OR operation.

# 3.1.12

-   Added a new configuration to tc_setup.conf (max_chunk_size) that controls the max chunk size used during datamodel and custom searches
-   Add logging for error messages returned in a search's results.
-   Updated TC-CSV-File-Indicator saved search to split file hash indicator into multiple rows.

# 3.1.11

-   Update tc_workflow_add_indicator page to match new UI style and display appropriate error messages on failure to add indicator.
-   Changed tag input fields to list first 500 tags and allow freeform inputs.
-   Changed indicator duplicate validation to improve indicator download performance.
-   Small performance improvements in several backend commands.

# 3.1.10

-   Updated search module to better handle indicators with multiple file hashes.

# 3.1.9

-   Added a new configuration to tc_setup.conf (tc_max_batch_size) that controls the maximum number of indicators in each batch save during indicator download.
-   Added arlib module for send to playbook adaptive response action and simplified sys.path handling.

# 3.1.8

-   Updated the group download script to address duplicates when processing groups with the same name.
-   Updated tc_verify_ssl in configuration to allow specifying a cert file.
-   Updated indicator review page to properly filter indicators with null values.

# 3.1.7

-   Update to correct path for bin lib directory.

# 3.1.6

-   Updated indicator review table to use proper timestamp value.
-   Added force option to migrations command.
-   Updated workflow action REST call to retrieve all workflow actions from the local search head.
-   Updated datamodel search field selection to no longer display hidden fields.
-   Multiple updates in support of Splunk Cloud certification.

# 3.1.5

-   Update to Adaptive Response actions to address issues with actions not showing.

# 3.1.4

-   Updated playbook download command to pull 5k playbooks.
-   Updated "Clear and Save" action to use updated clear command.
-   Updated location of alert_actions.conf.spec file to prevent startup errors.
-   Fixed issue with proxy enable setting.
-   Updated Event Triage search SPL.

# 3.1.3

-   Updated playbook list page to better handle playbooks with a single label.
-   Updated indicator review page to use proper timestamp format.
-   Updated search on event triage page to handle rating and confidence with empty values.
-   Updated event triage launch playbook modal to handle null description on a playbook.
-   Updated Threat Indicator Report page to handle indicator types with spaces in the name.

# 3.1.2

-   Added labels display to playbook list page.
-   Added labels filter for playbook downloads in settings page.
-   Added labels filter all adaptive response, event triage, and workflow action dropdowns.
-   Updated playbook download command to provide better output and to better handle labels.
-   Updated playbook launch commands inputs.
-   Updated workflow action commands to better handle inputs and to provide better output.
-   Fixed issue with preserving playbook password on updates.

# 3.1.1

-   Updated Support menu.

# 3.1.0

-   Added Adaptive Response that can call ThreatConnect Playbooks with notable event data in Splunk ES.
-   Change Data Model Search Config to allow free-form spl input to filter results.
-   Added search previews to Data Model Search Config and Custom Search Config pages.
-   Added configurable Workflow Actions to send data to ThreatConnect Playbooks.
-   Added the ability to send events to ThreatConnect Playbooks from the Event Triage page.
-   Added the ability to add arbitrary labels to events.
-   Added the ability for static values and dynamic values to be automatically added to event.
-   Added migration scripts 0.0.2 and 0.0.3 to migrate the previous state of events to pre-populate the new labels field, and to pre-populate the free-form spl in the Data Model Search Config.
-   Added Playbooks menu section that manages downloading and configuration of Playbooks from ThreatConnect, and configuring Playbook Workflow Actions.

# 3.0.1

-   Added logging to Indicator Downloads Config for issues surrounding save failures.
-   Removed logging when running playbooks that could reveal sensitive information.
-   Fixed Max False Positives label for Indicators Download list if it doesn't have a value.
-   Moved flag to disable SSL Verification for ThreatConnect connection from the settings page to the tc_setup.conf file.

# 3.0.0

-   New data structure for matched event data using KV Store and tc_event_data index.
-   ThreatConnect dashboard now has full date picker.
-   ThreatConnect dashboard updates to row expansion.
-   Indicator dashboard now has full date picker.
-   Event triage inputs updated to multi-select for Indicator Types, Owners, and States.
-   Event triage now has full date picker.
-   Event triage row expansion now includes Search name.
-   Event triage notes moved to row expansion and is now stored at the event summary level.
-   Custom and Data Model searches now support earliest and latest times.
-   Custom and Data Model searches now support additional tag filters.
-   Multiple updates to indicator downloads to improve performance and efficiency.
-   Indicator download now supports False Positive filter.
-   Indicator download row expansion now shows Last Download time, Local Indicator count, and Remote Indicator count for enabled Owners.
-   New indicator whitelist feature added for Indicator downloads.
-   Moved App logs from kvstore to tc_app_logs index.

# 2.3.4

-   Updated app to support retrieving more than 30 records during password lookup.

# 2.3.3

-   Updated enable/disable toggle on indicator downloads page to support older versions of Splunk
-   Updated Indicator Review for retrieving additional info

# 2.3.0

-   Retrieving additional indicator info from TC and viewing in splunk.
-   Dashboard filter for FP and Marked as Read
-   Additional time ranges in Splunk Event Triage
-   Filtered Result Count on Dashboards
-   Updated time of a record field on kv store collections
-   Show Table of Owner Configurations rather than drop down list
-   Search within kvstore indicators
-   Search within kvstore victims
-   Change the navbar to the same colors as TC's navbar
-   Add annotation to the event triage page
-   Toggle indicator downloads

# 2.2.1

-   Updated list pages to limit REST scope to local server and changed join type to left.
-   Added empty app.log file for app distribution.
-   Updated `run` link in indicator downloads.

# 2.2.0

-   Update to the ThreatConnect Dashboard to support custom indicators.
-   Update to Event Triage Dashboard to support custom indicators and better performance on batch actions.
-   Added 2 new Example XML dashboard for user customization.
-   Update to Lookup indicator workflow action to redirect to Indicator Search page.
-   Update to Threat Indicator Report to support custom indicators.
-   Update to Custom Search page to better organize the data.
-   Added Additional Rating/Confidence Filter to Custom Search configuration page.
-   Added Victim White List to Custom Search configuration page.
-   Changed Confidence Reset functionality from a checkbox and slider to a single dropdown on Custom Search configuration page.
-   Update to Data Model Search page to better organize the data.
-   Added Additional Rating/Confidence Filter to Data Model Search configuration page.
-   Changed Confidence Reset functionality from a checkbox and slider to a single dropdown on Data Model Search configuration page.
-   Added Victim White List to Data Model Search configuration page.
-   Update to Indicator Download page to better organize the data.
-   Added Bulk OnDemand checkbox to Indicator Download configuration.
-   Added "Or" Tag Filter checkbox to Indicator Download configuration.
-   Update Threat Rating and Confidence filter to support null value (No Filter).
-   Removed Bulk OnDemand checkbox from global Configuration.
-   Added Victim Whitelist Configuration screen supporting filter type of String, CIDR and regex.
-   The tc_admin role permission have been updated (adds list_storage_passwords and schedule_search capability).
-   Added tc_user role for non-admin actions (adds list_storage_passwords capability).
-   Indicator Lookup workflow action now redirects the user to the Indicator Lookup page.
-   Indicator add workflow improvements to allow multiple groups for association and custom indicator types.
-   Added Indicator Types command.
-   Added Group Types command.
-   Added new "Connectivity Test" sub-menu item to the Support menu.
-   Added tci_ciortt inputlookup
-   Removed tcmigrate command
-   Updated six.py to version 1.10.0.
-   Updated Requests module to version 2.13.0.
-   Updated Splunklib module to version 1.6.2.

# 2.1.6

-   removed setup.xml - application setup will be done directly in the app now.
-   changed is_configured to be 1 so app is always accessible even if settings has not been updated

# 2.1.5

-   Replaced setup.xml with custom settings pages with configuration settings in the KV Store.
-   Proxy Pass and API Secret are stored in the 'storage/password' endpoint
-   Update Data Model search to better handle URL matching.

# 2.1.4

-   Added configuration flag to enable/disable SSL certificate check for Splunk REST service.
-   Added disable attribute to download and clear button on submit.
-   Added logic to recreate custom and datamodel saved search if user manually deleted the search.

# 2.1.3

-   Added configuration option for Splunk REST URL (not in setup.xml)
-   Added configuration options for search sleep/timeout settings (not in setup.xml)
-   Updated indicator download to handle 0 valued confidence
-   Added sys.exit() back to splunk_error method
-   Updated all XML dashboards to HTML
-   Removed ES specific entries from default.meta
-   Remove all unused JavaScript libraries
-   Added functionality to delete duplicate indicators
-   INT-99 - resolved
-   INT-177 - resolved
-   INT-214 - resolved
-   INT-257 - resolved
-   INT-276 - resolved

# 2.1.2

-   Removed version specific javascript library

# 2.1.1

-   Updated searches to perform case insensitive indicators matches
-   Fixed bulk ondemand flag to register as an int/bool

# 2.1.0

-   New Event Triage Dashboard
-   New Data Model search management and configuration screens (old Data Model search has been disabled by default)
-   Removed Data Model and Observations checkboxes from Settings
-   New Custom search management and configuration screens
-   The "Owners Configuration" screen has been renamed to "Indicator Downloads"
-   New Indicator Downloads management screen
-   Indicator Download configuration screen allows for clearing indicators for an Owner
-   Indicator Dashboard now allows a time selection
-   Performance increase in Data Model searches
-   Performance increases for searches on Diamond Dashboard
-   Performance increases for indicator downloads (including bulk on-demand)
-   New confidence reset feature to extend deprecation based on observations
-   Added Splunk API socket test to "| tcdebug" command
-   Updated ThreatConnect Python SDK to version 2.4.3
-   Updated App Logs Dashboard now has a Refresh button
-   Updated App Logs schema to include delta and runtime

# 2.0.3

-   changed web datamodel field Web.url_path to Web.uri_path
-   logging Splunk job SID in tc_logs for datamodel searches

# 2.0.2

-   added additional fields to match on datamodel search (Web.http_referrer [WEB datamodel], Web.url_path [Web datamodel], All_Email.recipient [Email datamodel])
-   added indicator flag to tcclear on tc_events collection (| tcclear collection=tc_events indicator=127.0.0.1) so that events can be deleted.

# 2.0.1

-   added optional parameter to indicator download to force the use of bulk (use_bulk=true).
-   updated tcdebug to only try the TC api call 1 time instead of the default 5 times.
-   fixed main dashboard table where improper search was being used for rating and confidence ('>' instead of '>=')
-   fixed tcdebug command so that direct connectivity check to TC would be skipped if proxy was enabled
-   fixed bulk download where download would fail if bulk was enabled after first indicator pull

# 2.0

-   app renamed to TA-threatconnect
-   threatconnect index moved to Splunk KV Store
-   main dashboard table updated
-   indicator observations feature added
-   indicator false positive feature added
-   indicator add feature added
-   Splunk Enterprise Security integration added
-   new role "tc_admin" create to control access to restricted commands
-   several minor tweaks and bug fixes

# 1.80

-   added datetime picker to Main Dashboard table
-   added log collection (| inputlookup tcl)
-   added additional logging
    -   catch when splunk api does not return jobs
-   added tcclear command to clear key stores
-   change app setting to support logging level
-   fixed bug causing chart on main dashboard to sometimes not display

# 1.78.1

-   Bug fix for tc\*.log path on windows.

# 1.78

-   Added filter operator for tag filters on Owner configuration screen.
-   Bug fix for filtering on tags while downloading indicators.

# 1.77

-   Fixed a bug where debug flag had to be set for some functionality to work properly.
-   Added feature to tcdebug to show app debug log in Splunk.
-   Updated tc_add_indicator.py script in preparation for 2.0 Splunk App (feedback loop).

# 1.76

-   added victim column to main dashboard table
-   updated documentation link on resource page

# 1.75

## Dependencies

-   The Splunk Common Information Model App is now required (https://splunkbase.splunk.com/app/1621/)
-   python modules
    -   six.py
    -   dateutil
    -   enum
    -   requests
    -   splunklib
    -   threatconnect python sdk

## Backend Updates

-   changed from using CSV lookup files to Splunk KeyStore
-   added support for Windows

## Dashboards

### Diamond Dashboard (New)

-   Enables a user to lookup a threat, adversary, or incident providing a diamond model overview of the object including all known:
    -   Related incidents, reports, or detection signatures
    -   Malware
    -   CVEs
    -   IPs
    -   Domains
    -   URLs
-   Matches various CIM events and displays them to the dashboard allowing users to know how they are affected by the threat

### Owner Configuration (New)

-   added new dashboard to manage indicator download per owner

### ThreatConnect Dashboard (Updated)

-   added trending to single value indicator counts
-   replace pie charts with an area chart displaying the matches per day by indicator type
-   updated formatting of Matched Indicators table

### Indicator Dashboard (Updated)

-   replaced pie charts with an area chart showing the matches per day by owner

### Resources (Update)

-   added new styling

# 1.03

## Resources Page

-   initial add of the Resources page

## Threat Lookup

-   bug fix for output when no results are found

## Workflow Actions

-   added additional CIM compliant lookups

## Debug

-   added timestamp to debug file
-   added additional debugging

## Indicator Download

-   output count for each indicator result download for output
-   updated saved search to fix improper cron format
-   added digest so results of previous jobs can be viewed

## Setup

-   Added Debug boolean to control app debugging

# 1.02

## Main Dashboard

-   added time picker on main dashboard
-   new drilldown action for Trigger column which links to search for indicator
-   new drilldown action for Owner column which links to ThreatConnect.com owner page.

## Indicator Dashboard

-   Indicator table at the bottom has new quick link switcher. This allows a full width tables without losing dashboard real estate.

## DB Data

-   new quick link switcher on multiple dashboards. (including address indicator map)

## Debug

-   added new debug command "| script tc_debug TCDEBUG"
