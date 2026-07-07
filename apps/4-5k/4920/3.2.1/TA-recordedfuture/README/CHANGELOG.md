Change Log
==========

All notable changes to the Recorded Future for Splunk will be documented
in this file.

\[3.2.1\] (2026-04-27)
----------------------

### Bugfixes

-   Compatibility with Splunk Enterprise 10.2.0 Cloud.

\[3.2.0\] (2026-04-23)
----------------------

### Improvements

-   Introduced Detection Rules based Threat Hunts for Autonomous Threat
    Operations.

-   Added the `create_threat_actor_hunt_from_spl` REST endpoint to
    create Threat Actor hunt profiles directly from SPL. Example usage:

        | rest splunk_server=local /services/TA-recordedfuture/create_threat_actor_hunt_from_spl profile_name="Lazarus Group Hunt" actor_id="QCwdoU" actor_name="Lazarus Group"

-   Dynamically map "Risk" to TI framework "weight" value for each
    ingested IOC. Please recreate any existing TI framework feeds to
    take advantage of this new feature.

-   Consolidate timeout settings to a single "API Timeout" setting that
    applies to all API connections, including Attack Surface
    Intelligence, Recorded Future API, and Splunk APIs.

-   Added a configurable timeout for Sigma Threat Hunt searches
    (default: 600 seconds). This can be adjusted in the Features section
    of the Settings page.

### Changes

-   The frequency of `Recorded Future - Download Risk Lists` savedsearch
    has been reduced from every 5 to every 20 min.

-   Default Indicator Searches have been renamed to Detection Targets.

-   Migrations no longer run automatically on every REST request. A "Run
    migrations" button has been added to the Troubleshooting tab in
    Settings to trigger them manually. You would only ever need to use
    this button if you are upgrading from a version older than 3.0.0.

### Bugfixes

-   Moving state variables to KV store instead of .conf file to prevent
    issues in clustered environments.

-   Fix to risk events not being generated in ES \[Regression issue\].
    Existing RBA feeds must be recreated.

-   "No Technical Links" threat hunt status has been changed to "Empty
    Hunting Package" to better be more general.

-   "Empty Hunt Package" is now reported as a successful hunt in
    Autonomous Threat Operations.

-   Fixing issue with MITRE parsing for ES notables.

\[3.1.1\] (2026-03-19)
----------------------

### Improvement

-   The app no longer reads the `app.conf` file at runtime to avoid
    unexpected access errors for non-admin users.

-   Large payloads are now gzipped before being sent to the BFI.

### Bugfixes

-   Fix to risk events not being generated in ES \[Regression issue\].
    Existing RBA feeds must be recreated.

-   "No Technical Links" threat hunt staus has been changed to "Empty
    Hunting Package" to better be more general.

-   "Empty Hunt Package" is now reported as successful hunt to ATO.

-   Fixing issue with MITRE parsing for ES notables.

-   Fix logging of number of fetched IOCs from the risklists.

\[3.1.0\] (2026-01-30)
----------------------

### Improvements

-   Introduced Autonomous Threat Operations for Detect: Allows
    configuration of relevant indicators of compromise in the Portal and
    remote deployment of continuous detection (correlation) into your
    Splunk environment.

\[3.0.2\] (2026-03-19)
----------------------

### Improvement

-   The app no longer reads the `app.conf` file at runtime to avoid
    unexpected access errors for non-admin users.

-   Large payloads are now gzipped before being sent to the BFI.

### Bugfixes

-   Fix to risk events not being generated in ES \[Regression issue\].
    Existing RBA feeds must be recreated.

-   "No Technical Links" threat hunt status has been changed to "Empty
    Hunting Package" to better be more general.

-   "Empty Hunt Package" is now reported as successful hunt to ATO.

-   Fixing issue with MITRE parsing for ES notables.

-   Fix logging of number of fetched IOCs from the risklists.

\[3.0.1\] (2026-01-23)
----------------------

### Bug Fixes

-   Fixed an issue introduced in v3.0.0 where enabling Default Indicator
    Searches could corrupt the configuration of existing Threat Hunts.
    Please see [Important note](#important_note_3_0_1)

-   Clarified SPL syntax for filtering in search for Correlation
    Dashboard in documentation.

-   Fix loading of Sigma Rules page in case of malformed Mitre ATT&CK
    Techniques data.

-   Fixed an issue where ATO Threat hunt schedule could be edited in the
    application.

-   Fixed several minor UI issues on Threat Hunt Profile modal, Threat
    Hunt dashboard and Settings page.

### Important note

-   If you **configured Detection Targets** and have **Threat Hunts
    created before v3.0.0**, you **must re-configure those existing
    Threat Hunts** after upgrading to **v3.0.1** to ensure they work
    correctly.

-   Customers who **did not configure Detection Targets** are **not
    affected** and **do not need to take any action**.

\[3.0.0\] (2025-12-05)
----------------------

### Improvements

-   New feature called Autonomous Threat Operations for Threat hunts.
    Configure indicators of compromise you are interested in or relevant
    to your organization in the Portal. Then with very small effort
    Splunk will run Threat Hunts based on these indicators of compromise
    automatically.

Look up Autonomous Threat Operations in the documentation to learn more.

\[2.9.2\] (2025-11-28)
----------------------

### Bug Fixes

-   Fixed missing "Recorded Future Enrichment" adaptive response action
    in Splunk Enterprise Security.

-   Added complete static configuration properties to
    `rfes_ar_enrichment` in `alert_actions.conf`, including command,
    label, description, CAM metadata, and all required parameters for
    proper Enrichment adaptive response action integration with Splunk
    Enterprise Security.

-   Fixed broken layout in "Recorded Future Collective Insights"
    adaptive response action form for Splunk ES 8.1.1. Updated CSS to
    display form fields correctly in vertical layout. Added inline
    comments documenting Splunk ES 8.1.1 rendering limitations for
    non-form HTML elements.

-   Fetch 1000 classic alerts per Alerting Rule on Recorded Future
    Alerts page to avoid truncation of alerts for bigger time periods.

-   Allow to inspect search for Threat Hunt Jobs for all users.

-   Add hard limits for KV Store retention.

\[2.9.1\] (2025-09-22)
----------------------

### Improvements

-   Use `_internal` index instead of `_*` when running "Recorded
    Future - Timing logs extractor" savedsearch.

-   `rfenrich` command runs only on Search Head.

-   `rfenrich` command now accepts an optional `api_key` field which is
    used instead of the existing one (useful if user running the command
    does not have the `list_storage_password` capability).

-   Classic Alerts ingestion is now limited to a maximum 1-hour time
    range. This ensures faster processing and prevents delays caused by
    large amount of requests.

-   Sigma rules can be accessed with `| inputlookup sigma_detection`

\[2.9.0\] (2025-07-29)
----------------------

### Deprecations

-   Deprecated Splunk Enterprise Security Correlations. All existing ES
    correlations will remain available.

-   Automatic migrations of old configurations to new format will be
    disabled from version 3.0 of our app. We are deprecating this
    because it has proved to have reliability issues. Instead if you are
    upgrading from an old version and need to run these migrations there
    will be an option to do so manually in the troubleshooting section.

### Improvements

-   Resolving actions for Playbook Alerts.

-   Multiple projects for ASI dashboards.

-   Import settings using the troubleshooting package. Only exports of
    version 2.8.3+ can be imported.

-   Creation of Notables from Sigma detections and Threat Hunts (<span
    class="menuchoice">Configuration &gt; Settings &gt; Splunk
    Enterprise Security</span>)

-   Specified an earliest time for all searches to avoid running over
    All Time.

-   Adding the ability to index alerts ingested into KV stores.

-   A new button to contact support at <span
    class="menuchoice">Configuration &gt; Settings &gt;
    Troubleshooting</span>

### Bug Fixes

-   Fix communication with Splunk API when `requireClientCert` is set to
    `true` in `server.conf`.

-   Fix displaying of Threat Hunt results without risk and category on
    Threat Hunt Runs page.

-   Fix IOCs links for Threat Hunt for Threat Actor.

\[2.8.1\] (2025-05-13)
----------------------

### Bug Fixes

-   Fix communication with Splunk API when `requireClientCert` is set to
    `true` in `server.conf`.

-   Fix displaying of Threat Hunt results without risk and category on
    Threat Hunt Runs page.

-   Fix to issue where "permission" warning message on threat hunt
    configuration was displayed in error.

-   Fix IOCs links for Threat Hunt for Threat Actor.

-   Fix ASI set up for cloud instances.

\[2.8.0\] (2025-04-02)
----------------------

### Improvements

-   Deeplink functionality for Recorded Future Alerts, Playbook Alerts,
    and Sigma Detections pages.

-   Including multiorg owner-organization in the PBA redirect link for
    correct viewing in the portal.

-   Added ASI feature including dashboards and settings page.

-   Changed savedsearch name from "Recorded Future - Check Asynchronous
    Jobs" to "Recorded Future - Threat Hunt Result Collector" to resolve
    ambiguity.

-   Support for Splunk ES 9.4.

-   New enrichment command `rfenrich` to enrich events in a search.

-   Enriching Vulnerabilities now contains CSSVv3 and CSSVv4

-   Introducing Adaptive Response Action to contribute Findings to
    Collective Insights.

-   New home page replacing Alert Center as the default page when
    starting the app.

-   Now FIPS compliant and can be run in a FIPS environment.

-   Improvements to playbook alerts

-   New tab for Settings page "Troubleshooting" allowing you to easily
    export logs and settings to send to support for further
    investigation.

### Changes

-   Moved Troubleshooting page from Configuration menu into <span
    class="menuchoice">Configuration &gt; Settings &gt;
    Troubleshooting</span>.

### Bug Fixes

-   Fix an issue with RBA feeds where the risk threshold was set to 0
    after upgrading from v2.6.x.

-   Fix displaying of invoked Adaptive Response Actions in Mission
    Control.

-   IMPORTANT. If you are using Sigma rules you are strongly encouraged
    to update to 2.8 or forthcoming 2.7.3. There was a bug where if the
    corresponding SPL for a sigma rule was broken, other sigma rule
    searches would not run correctly. All Sigma rules searches now run
    separately and when saving we validate that the SPL is valid, ie can
    run without issues. To check whether you are affected by this bug
    update to the latest version and look for the following error "Sigma
    search got 400 error investigate".

We have identified three problematic sigma rules, if you use any of
these you are definitely affected.

-   doc:v-9-ef - Insikt Validated TTP: Detecting NovaSentinel Using
    Sigma

-   doc:1sioHH - Sigma Rule: Drive Overwriting with "cipher" Command

-   doc:2uXk09 - Sigma Rule: Detecting Scheduled Tasks Named "Windows
    Update ALPHV", Used by Various Ransomware Families

We encourage you to disable these for the time being.

Once upgraded, if you have custom SPL in the sigma rules we encourage
you to edit these rules and click save again, as this will validate that
the SPL is indeed valid. If the SPL is invalid you will get an error and
won’t be able to save the rule.

\[2.7.3\] (2025-01-04)
----------------------

### Bug fixes

-   Fix an issue with RBA feeds where the risk threshold was set to 0
    after upgrading from v2.6.x.

-   Fix displaying of invoked Adaptive Response Actions in Mission
    Control.

-   IMPORTANT. If you are using Sigma rules you are strongly encouraged
    to update to 2.8 or forthcoming 2.7.3. There was a bug where if the
    corresponding SPL for a sigma rule was broken, other sigma rule
    searches would not run correctly. All Sigma rules searches now run
    separately and when saving we validate that the SPL is valid, ie can
    run without issues. To check whether you are affected by this bug
    update to the latest version and look for the following error "Sigma
    search got 400 error investigate".

We have identified three problematic sigma rules, if you use any of
these you are definitely affected.

-   doc:v-9-ef - Insikt Validated TTP: Detecting NovaSentinel Using
    Sigma

-   doc:1sioHH - Sigma Rule: Drive Overwriting with "cipher" Command

-   doc:2uXk09 - Sigma Rule: Detecting Scheduled Tasks Named "Windows
    Update ALPHV", Used by Various Ransomware Families

We encourage you to disable these for the time being.

Once upgraded, if you have custom SPL in the sigma rules we encourage
you to edit these rules and click save again, as this will validate that
the SPL is indeed valid. If the SPL is invalid you will get an error and
won’t be able to save the rule.

\[2.7.2\] (2025-03-05)
----------------------

### Improvements

-   Dynamic base url in javascript allowing for on-premise installations
    to have custom url paths.

### Bug fixes

-   Fix Technical Links occasionally not showing up for certain malware.

-   Fix an upgrade issue when you’re using an old 2.x version of the
    Recorded Future app.

\[2.7.1\] (2025-02-05)
----------------------

### Improvements

-   Add support for Splunk ES 8.0

-   Add support for Splunk Enterprise 9.4

### Bug Fixes

-   btool errors for sigma rules

-   Error with "search preview"

\[2.7.0\] (2025-01-08)
----------------------

### Improvements

-   Adding the option to pivot from the Threat Hunt result page to the
    Search itself via '…​' menu. A "Search and Export" button is now
    available there.

-   Adding "Description" and "Timestamp" to third-party collective
    insights call.

-   Multiple indexes are now available to be selected for sigma rules.

-   Including multiorg owner-organization in the PBA redirect link for
    correct viewing in the portal.

-   Removing jQuery from our code. jQuery is still in use for Splunk
    provided components where Splunk is responsible for updates.

-   Change format for Mitre ATT&K Techniques on Sigma rules page to
    include the name of the technique.

-   Renaming modules to better reflect what they do.

-   Risk Based alerting has been renamed to Enterprise Security
    Correlations

-   Adaptive response has been renamed to TI Framework Ingestion.

-   Indexing of playbook alerts in KVstore

-   Enrichment page now contains an AI summary

-   Better UX for starting Threat hunts in both threat map and threat
    table.

-   Threat hunting with threat actors in addition to hunting with
    malware.

-   Data Model is now an option for configuring Threat Hunts

-   Improved when a hunt is failing

-   The command
    `| rest /services/TA-recordedfuture/migrate_remove_threat_intel_entries`
    will clean out all old threat intel data from Recorded Future.

### Bug fixes

-   Fix high runtimes for correlations in 2.6

-   Change hashing function so that the Recorded Future app works in
    FIPS environment.

-   Fixing the issue of old entries in the TI framework kvstores are
    left behind by reverting to a CSV solution for the TI framework.

\[2.6.3\] (2025-02-05)
----------------------

### Improvement

-   Support for Splunk ES 8.0

-   Support for Splunk Enterprise 9.4

### Bug fixes

-   Fix UI regression affecting Threat Hunt view when upgrading to
    Splunk 9.4.

-   Revert Threat Intelligence Framework usage of kvstore; now using CSV
    as a ingestion.

\[2.6.2\] (2024-12-16)
----------------------

### Bug fixes

-   Fix an issue where searches exceeded the search concurrency limit of
    historical searches. This affected the migration handler preventing
    us to run migrations needed when upgrading from one version to
    another.

### Improvement

-   Add the following rest command, making it accessible to easily
    update a conf file.
    `| rest /services/TA-recordedfuture/write_conf_file filename=recordedfuture_settings stanza=conf_version data="{\"fail_counter\": 0}"`

\[2.6.1\] (2024-11-26)
----------------------

### Bug fixes

-   Risklist are now stored in .csv’s again following abnormal increase
    in correlation\_search runtime.

-   Fixing a broken link on the settings page.

### Improvements

-   Changes to "Weekly Active User" metrics.

\[2.6.0\] (2024-10-07)
----------------------

### Improvements

-   Risklist are now stored in KV store rather than .csv

-   Optional KV store ingestion of Alerts.

-   Optional KV store ingestion of Playbook Alerts.

-   Threat Hunt Scheduling capability.

-   Ability to disable continuous cached correlation searches in UI.

-   Correlation dashboard "live mode" that runs correlation on dashboard
    visits when caching of correlation searches is disabled.

-   Display v3 alerts on Recorded Future Alerts page.

-   Collective insights storing event time rather than detection time.

-   Collective insight will start recording "actions" seen in relation
    to a detection, i.e. firewall allowed/blocked for a firewall based
    correlation.

-   Consolidation of adaptive response and app logfile. Errors and
    Warnings are still listed on the troubleshooting view.

### UI improvements

-   Configure threat hunt directly from Threat Map.

-   New UI for settings page.

\[2.5.1\] (2024-09-04)
----------------------

### Bug Fixes

-   Adding quotes to mitigate the space in field used in default
    correlations.

-   Splunk 9.3 issue where menu was not displayed correctly after app
    first-time-setup.

-   Change to threat hunt where hunts could run outside specified time
    scope.

-   Fixed an issue with disappearing Link block for enrichment pages.

\[2.5.0\] (2024-04-19)
----------------------

### Improvements

-   Better Threat Hunt results grouping and representation.

-   Fields selected for **Datamodel** correlations will now
    automatically be displayed on the correlation dashboard.

-   Added input for custom correlation delay on Datamodel and ES
    correlation setup page.

-   Added nightly search for correlations that picks up events with big
    indexing delay.

### Bug Fixes

-   **Index-based** correlation will now use \_index\_time instead of
    \_time, removing the risks of index delay.

\[2.4.3\] (2024-09-04)
----------------------

### Bug Fixes

-   Adding quotes to mitigate the space in field used in default
    correlations

-   Splunk 9.3 issue where menu was not displayed correctly after app
    first-time-setup.

-   Change to threat hunt where hunts could run outside specified time
    scope.

-   Fixed an issue with disappearing Link block for enrichment pages.

\[2.4.2\] (2024-04-24)
----------------------

-   Added input for custom correlation delay on Datamodel and ES
    correlation setup page.

-   Added nightly search for correlations that picks up events with big
    indexing delay.

### Bug Fixes

-   **Index-based** correlation will now use \_index\_time instead of
    \_time, removing the risks of index delay.

\[2.4.1\] (2024-03-14)
----------------------

### Bug Fixes

-   Removed `localop` in index search for sigma setup page.

-   Renamed deprecated `distsearch.conf` stanza.

-   Added query logic to process an empty response to clear the .csv
    risklists correlation feed file.

-   Removed stray rename statement from ES correlation searches.

-   Fixed Sigma Modal view when update to a rule is received.

-   Fixed issue where Playbook Alerts released upon received empty API
    payload.

\[2.4.1\] (2024-03-14)
----------------------

### Bug Fixes

-   Removed `localop` in index search for sigma setup page.

-   Renamed deprecated `distsearch.conf` stanza.

-   Added query logic to process an empty response to clear the .csv
    risklists correlation feed file.

-   Removed stray rename statement from ES correlation searches.

-   Fixed Sigma Modal view when update to a rule is received.

-   Fixed issue where Playbook Alerts released upon received empty API
    payload.

\[2.4.0\] (2024-02-08)
----------------------

### Improvements

#### Correlation Dashboard

-   Added the ability to select columns to display.

-   Added SPL filter option to filter correlations.

#### Correlation Setup

-   Added extra tuning options for correlations.

-   Added ability to correlate on any number of fields with one rule.

-   Added ability to correlate on multi-value fields with one rule.

-   Adding search preview to display the correlation search as it is
    being constructed.

-   Added pivot from setup page to Splunk search app to run and view
    results of correlation rule search.

#### General

-   Configuration page will now automatically refresh after the app has
    been fully configured.

-   Update the URI format for playbook alerts.

-   Added earliest\_time and latest\_time parameters to the sigma
    savedsearch.

-   Added support for "json" format of the response to
    "/fetch\_single\_alert" endpoint.

### Bug Fixes

-   Improved RBA exception handling to prevent naked/empty notables in
    Incident Review.

-   Added more verbose logging for RBA searches.

-   Reworked how indexes and sourcetypes were identified, no longer
    using `index=*` syntax, instead a different tstats query.

\[2.3.3\] (2024-03-14)
----------------------

### Bug Fixes

-   Removed `localop` in index search for sigma setup page.

-   Renamed deprecated `distsearch.conf` stanza.

-   Added query logic to process an empty response to clear the .csv
    risklists correlation feed file.

-   Fixed Sigma Modal view when update to a rule is received.

-   Fixed issue where Playbook Alerts released upon received empty API
    payload.

\[2.3.2\] (2024-01-18)
----------------------

### Bug Fixes

-   Improved RBA exception handling to prevent naked/empty notables in
    Incident Review.

-   Added more verbose logging for RBA searches.

-   Update %-search query on Correlation setup page to avoid undefined
    result value.

-   Fixing Collective Insights support page link issue.

-   Updated url format for the playbook alerts portal redirect.

\[2.3.1\] (2023-11-16)
----------------------

### Improvements

-   Filtering out special fields from the configuration for the Threat
    Hunt:

    -   tag

    -   tag::\*

    -   eventtype

### Bug fixes

-   Fixed error for the hidden Sigma rules that received the update.

-   Added `splunk_server=local` to fix the problem for clustered
    environments with the next savedsearches:

    -   Recorded Future - Send Weekly Active Users statistics

    -   Recorded Future - Check Asynchronous Jobs

-   Fixed the issue with never-ending failed Threat Hunt.

\[2.3.0\] (2023-10-13)
----------------------

### General

-   "Intelligence Cloud" renamed to "Collective Insights"

-   Removed mandatory "ID" field when configuring correlation, it is now
    auto-generated.

-   Added 'Threat Hunt' feature support.

    -   Added "Threat Hunts" dashboard.

    -   Added "Threat Hunt Runs" results page.

    -   Added Malware Threat Map.

### Improvements

-   The "new" badge disappears after two weeks of the import of the
    sigma rule.

-   Added the ability to perform IP enrichment on CIDR ranges.

-   Added improved loading indicators.

-   Removed required ID field when setting up a new Correlation/TI
    Feed/RBA.

-   Re-introducing the ability to not verify SSL certificates for
    on-prem setups. Not applicable for Cloud.

### Bug fixes

-   Be able to sort on status in Sigma configuration view.

-   Faster loading in correlation view

-   Added a missing collection.

-   Disabling a savedsearch pending a thorough investigation into
    reports of performance issues. Impact: correlation dashboard risk
    update is disabled until further notice.

-   Added purging of deprecated sigma rules.

\[2.2.2\] (2023-09-20)
----------------------

### Bug fixes

-   Ensure that the collection `recordedfuture_conf` is added to
    `collections.conf`. The omission of this entry in `collections.conf`
    is an issue for Splunk Cloud.

-   Increasing the timeout from 45s to 180s for requests to Recorded
    Future’s api.

\[2.2.1\] (2023-08-18)
----------------------

### Improvements

-   Include a new endpoint
    `/services/TA-recordedfuture/get_spl_sigma_rules`, to get sigma
    rules formatted for spl.

### Bug Fixes.

-   Fixed an issue where risklists could not be pulled into ES because
    of a default limit in ES.

-   Fixed an issue where Notable events were not generated correct when
    using a threshold with RBA.

\[2.2.0\] (2023-07-10)
----------------------

### General

-   Added support for Playbook Alerts, 2.2 ships with "Domain Abuse".
    Additional types will be distributed in the future without any need
    to upgrade the integration.

    -   Separate page with Playbook Alerts in the Alert Center section

    -   Configuration of Playbook Alerts on the same page as Classic
        Alerts.

    -   Displaying of total count of alerts on the Overview page.

-   Updated RBA feature set

    -   Added Threshold option to RBA feeds. This option sets a minimum
        severity for which notable events are created. Anything below
        threshold is only created as a risk event.

        -   RBA feeds from versions 2.1.x will be migrated into an RBA
            feed which is only producing Notable events.

    -   Added optional Estimate; when configuring splunk ES correlations
        with Risk Based Alerting this can be used to estimate daily
        notable event count.

-   Splunk ES adaptive response action that performs correlation on
    related indicators (Links). Correlations are displayed in ES as
    notables or ingested as risk events.

-   For customers that are sharing data, they also share the
    recordedfuture\_settings.conf, so it becomes easier to debug.

-   The app produces statistics about how many users uses the different
    endpoints in the app and forwards those to Recorded Futures API.
    Only the number of users per endpoint along with min/avg/max
    response times are sent.

### Improvements

-   Added the ability to contribute to Collective Insight with matches
    in the TI data model. Please visit Intelligence cloud configuration
    page and review settings.

-   Updated Intelligence Cloud configuration page.

-   UI update on the TIfeed page to accommodate the Risk Based Alerting
    Threshold Option.

-   Notable Events created by our Risk Based Alerting integration now
    contains the original event.

-   Added multi-org support for Recorded Future alerts. Alerting rules
    and alerts will now display which organization owns the alert. Added
    filtering option on "owner".

-   Added support for specifying organization when participating in
    Collective insight for clients that are multi-organization clients.

-   RBA feeds without threshold now only produce notable events and not
    risk notables. Risk handling is left fully to splunk RBA based of
    events in the risk index. Feeds created before 2.2 will be upgraded
    accordingly.

### Bug Fixes.

-   Splunk ES sometimes derives IOC from Recorded Future indicators
    which have no risk in the Recorded Future platform. If the occurs a
    message will be displayed in the notable event.

-   Bug with regexp in distsearch.conf that caused risklists to be
    replicated to indexers in cluster environments.

-   Python2.7 compatibility issue with Adaptive Response Enrichment.

-   For new installations, the collections
    `TA_recorded_future_incident_state` and
    `TA_recorded_future_detections` have the owner Nobody. If needed,
    you can change this manually in Settings &gt; All
    configurations &gt; Re-assign Knowledge object.

-   Resolve an issue where the alert center view may trigger a
    jsondecode error. As updated risklists come in, the risk score in
    correlations and alert center gets updated. Initial risk is kept in
    cache in the field `initial_risk`

-   IOCs that no longer exist in downloaded risklists will not show up
    in the correlation view. These IOCs will continue to be available in
    the alert center; but the risk score will be out of date.

### Engineering

-   Updated `metadata/default.meta` file by adding write permissions for
    `sc_admin` role which is an alternative `admin` role on cloud
    instances.

-   A migration of the following collections
    correlation\_cache\_{category}, where category is either,
    vulnerability, url, domain, hash or ip. Only 50k of these
    collections will be migrated by default. If you require to migrate a
    larger amount of these collections ensure that larger values are set
    for the following entries in `limits.conf`. This will also ensure
    that out of date risk scores is being updated correctly.

When the migration happen it will normalize the
collection\_cache\_{category}. This means that only one correlation hit
will appear in a single correlation dashboard. So it may appear that
correlations are missing compared to before the upgrade. However, that
is not the case, duplicated correlations have with the correlation been
deduplicated.

The following change needs to be added to `limits.conf` in
`/etc/system/local/limits.conf`. You may adjust the values according to
your system’s need.

    [searchresults]
    maxresultrows = 10000000

    [join]
    subsearch_maxout = 10000000

    [kvstore]
    max_rows_per_query = 1000000

-   Risk Based Alerting feeds from 2.1 will be migrated over to 2.2 as
    pure Notable Events feeds and will not produce any Risk events.
    Please recreate these to reintroduce risk event generation.

-   Removed the ability to disable SSL verification of external traffic.

### Changes

-   Renamed "Configuration" → "Recorded Future Alerts" to "Alerting
    Rules".

\[2.1.4\] (2023-06-07)
----------------------

### Improvements

-   Added multiorg support for Recorded Future alerts. Alerting rules
    and alerts will now display which organization owns the alert. Added
    filtering option on "owner".

-   Added more in-app documentation

### Bug fixes

-   Bug with regexp in distsearch.conf that caused risklists to be
    replicated to indexers in cluster environments.

-   Python2.7 compatibility issue with Adaptive Response Enrichment.

-   Bug involving the conversion of Splunk event to JSON

-   Increased timeout of a number of calls causing premature timeouts.

-   For new installations, the collections
    `TA_recorded_future_incident_state` and
    `TA_recorded_future_detections` have the owner Nobody. If needed,
    you can change this manually in Settings &gt; All
    configurations &gt; Re-assign Knowledge object.

-   Resolve an issue where the alert center view may trigger a
    jsondecode error.

\[2.1.3\] (2023-03-20)
----------------------

### Improvements

-   Improved performance of Correlation Setup for massive log
    environments.

-   Improved performance of Sigma Setup for massive log environments.

-   Added documentation for new "Infrastructure Detections" enrichment
    panel.

-   Improved in-app documentation for Correlation "Search String" option

### Bug fixes

-   Notifications text sometimes clipped outside its border.

-   Subset of in-app correlation risked being missed.

-   Risklist sync failure caused correlation setup to fail with an
    incorrect error message.

\[2.1.2\] (2023-02-13)
----------------------

### Improvements

-   Ad-hoc invocations of Adaptive Response will now create Notable
    events.

-   Title Prefix option which allows for customization of Notable event
    title.

-   UI improvements for notifications.

-   Added a quickstart guide for setting up the app.

-   Removed save button in the configuration page.

### Bug fixes

-   Bug where events containing multi-value fields were incorrectly
    filtered out from results when the `make_json` macro was used.

-   Fixed bug where previous correlation view ID were shown in dropdown.

-   HTTPS-proxy support disabled for splunk 8 as it lacks support.
    Please upgrade to Splunk 9 to get the full HTTPS proxy support.

\[2.1.1\] (2022-12-15)
----------------------

### Changes

-   Invalid config in app.manifest fixed.

\[2.1.0\] (2022-12-15)
----------------------

### Changes

-   Removed the migration tool - migration is only supported between
    versions 1.x and 2.0.

### General

-   Added Sigma Rule Detection

-   Top navigation menu reworked

-   Added Alert Center displaying Sigma Detections and Correlations

-   Correlations

    -   Correlation now works via a cached approach, reducing load times
        of dashboards

    -   All correlations available in a new dashboard

-   Updated documentation.

-   Reworked Recorded Future Alerts

-   A new tab "Intelligence Cloud" added to Configuration. An option to
    either share or not share any unattributable data for analytical
    purposes can be made here. The default option is to share data.

### Enterprise Security

-   Added integration into the Risk Based Alerting framework

    -   Notable events enriched directly - duplicate events are not
        created anymore

    -   Notables also annotated with Mitre ATT&CK codes

\[2.0.8\] (2023-02-01)
----------------------

### Bug fixes

-   HTTPS-proxy settings issue occurring for users of Splunk 8. Splunk 8
    is using a version of urllib3 that does not support HTTPS proxies,
    and will use HTTP regardless of configuration. Please upgrade to
    Splunk 9 to get the full HTTPS proxy support.

-   Fixed edgecase on migration from 1.1, where a setup without any
    usecases loaded cause the migration to fail.

\[2.0.7\] (2023-01-17)
----------------------

### Improvements

-   Ad-hoc invocations of Adaptive Response will now create Notable
    events.

-   Title Prefix option which allows for customization of Notable event
    title.

-   Updated UI for Recorded Future Alerting rule page.

\[2.0.6\] (2022-12-13)
----------------------

### Bug fixes

-   Configured Correlation use cases that become unavailable confused
    the correlation configuration view.

-   Tighter filter on what data is shared from Adaptive Response.

### Improvements

-   Tightened security in Python made any deployments using an HTTPS
    proxy to fail if the SSL certificates of the proxy were not properly
    signed. Implemented a setting to make it possible to disable
    verification of the proxy SSL certificates.

\[2.0.5\] (2022-10-11)
----------------------

### Bug fixes

-   The Adaptive response code contained code that was not python2
    compatible. Some instances of Splunk still runs Adaptive Responses
    using python2.

\[2.0.4\] (2022-09-13)
----------------------

### Bug fixes

-   Change in 2.0.3 caused a degradation in performance for correlations
    of accelerated data models. This has been remedied.

-   Calculated fields were missing when setting up a correlation for
    accelerated data models.

\[2.0.3\] (2022-09-05)
----------------------

### Bug fixes

-   Machines that use self-signed certificates and upgrade to 2.0.x
    won’t have issues upgrading.

-   Fix log parsing

-   Clicking on "Search string" button in correlation configuration will
    no longer give you an error.

-   Removal of all f-strings that cause issues for AR actions as it runs
    python 2.7.

-   Be able to filter on Network Traffic, allowed/block without issues.

-   Enrich action pivots from ES Notable events correctly.

\[2.0.2\] (2022-06-16)
----------------------

### Bug fixes

-   Broken python2 compatibility exhibited in Adaptive response.

-   Notable events that don’t have threat\_match\_value will no longer
    throw an error

-   "Event" text has been removed from Accelerated correlation
    configuration step.

### Improvements

-   Improved dialog options for Enterprise Security correlation
    writebacks with a new menu option "Intelligence Sharing".

\[2.0.1\] (2022-05-11)
----------------------

### Bug fixes

-   Documentation fixes

-   Javascript interoperability issues

-   Collections are not replicated to indexers

-   Correlation setup wizards now include calculated fields

### Improvements

-   Documentation improvements

-   Performance improvements in the correlation setup views

-   Usability improvements in the correlation setup views

-   The Splunk system is now requested to reload configurations once a
    new ES thread feed has been added. This avoids having to restart the
    Splunk system for the new feed to become available

-   Improved error messages

-   Additional information available about Recorded Future alerts.

\[2.0.0\] - 2021-12-25
----------------------

### Improvements

### General

-   Correlation dashboards are now dynamically generated based on input
    from the user.

    -   Added MITRE ATT&CK codes.

    -   Support for accelerated data models.

-   Enrichment dashboards are now dynamically generated.

-   New overview page that shows statistics based on configuration of
    the app.

-   Menu is dynamically generated to suit the current configuration.

-   New and improved configuration pages.

    -   Validation of API URL and token.

    -   Separate pages for correlations and alerts.

-   Now uses an API that is adapted to suit the integration app.

-   Updated documentation.

-   Updated workflow actions.

-   Global Map dashboard removed.

-   Added migration tool for users upgrading from version 1.x of this
    app.

-   Refactored code and made more robust.

-   Design updates.

### Enterprise Security

-   Improved Adaptive Response module

### Bug fixes

-   Stuff
