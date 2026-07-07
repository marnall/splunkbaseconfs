# Broken Hosts App for Splunk

The Broken Hosts App for Splunk is a useful tool for monitoring data going into Splunk. It has the ability to alert when hosts stop sending data into Splunk, as well as inspect the last time the final combination of data was received by Splunk.

If the arrival of the final log for the index/sourcetype/host combination is later than expected, the Broken Hosts App will send an alert. This allows for quick status detection of the hosts and fast issue resolution.

The Broken Hosts App for Splunk is the app for monitoring missing data in Splunk. The app’s three main objectives include:
1. Alerting when data has stopped sending to Splunk.
2. Utilizing saved searches to facilitate rapid detection of the missing data.
3. Creating dashboards for visualization to help with further investigations.

## Features
- Detects gaps in data being collected into Splunk
- Detects unexpected latency in data being collected into Splunk
- Generates statistics about data being collected into Splunk for other uses
- Includes dashboards for investigating broken data sources
- Use Splunk modular alert actions for sending alerts
- Lookup and Eventtype-based configuration

## 5.1.1 Release Notes

Bugfix release.

### Fixed
- The **Configure Lookup** and **Configure Suppressions** tables could rapidly flip between two text-wrapping layouts ("flickering") at certain browser window sizes. Table column widths are now stable regardless of window size.

## 5.1.0 Release Notes

The 5.1.0 release is a UI refresh focused on the **Configure Lookup** and **Configure Suppressions** dashboards. Alerting and suppression semantics are unchanged.

### What's new
- **Faster dashboards at scale.** The configuration tables stay responsive when your `expectedTime` collection holds tens of thousands of rows. Scrolling, sorting, and filtering work smoothly at 25,000+ entries.
- **Smart Index / Sourcetype / Host inputs.** When adding or editing entries, these fields now autocomplete against your environment's actual values. Type two or more characters to see matches; free-text values that don't appear in the dropdown are still accepted.
- **Cleaner batch entry layout.** "Add Multiple Entries" lays each row's fields out vertically so long index/sourcetype/host names no longer scrunch.
- **Refreshed look.** Dashboards use the current generation of Splunk's UI components for a more consistent look with modern Splunk Enterprise / Cloud.

### Fixed
- The Configure Lookup table search filter now broadens results when you correct a typo, instead of narrowing further from the previous match.
- The "Populate with Default Values" button no longer appears when a search filters the table to zero matches. It only appears when the underlying collection is genuinely empty.
- Edits, additions, and deletions are immediately visible to subsequent searches without a page refresh.

### Note on first install
The Index / Sourcetype / Host autocomplete reads from three lookups populated by scheduled searches that run every four hours (`Lookup Gen - bh_host_cache`, `Lookup Gen - bh_index_cache`, `Lookup Gen - bh_sourcetype_cache`). On a brand-new install the autocomplete dropdowns will be empty until the first scheduled run completes. A Splunk admin can run any of these searches manually to populate the caches immediately.

### Upgrading from 5.0.x
No data migration or configuration changes are required. Install the new version through Splunkbase or by reloading the app; the new dashboards take effect immediately.

## IMPORTANT - Upgrading from pre-5.0 Broken Hosts
Starting with Broken Hosts 5.0.0 data source alert threshold tunings and suppressions have been separated into separate lookups.

Note that the below searches use the ``| outputlookup`` command to update the lookups used by Broken Hosts. This command is labled as risky by default in Splunk,
and a warning message will be displayed if this has not been changed. Users can safely click through this warning. If you wish to permanently disable it,
Cloud customers can open a support case to remove it from the list of risky commands. Enterprise customers can add a commands.conf file to the
default/ directory in the Broken Hosts app to prevent the warning from popping up.

Existing alerting will still function until the following steps are completed, but issues may arise if the following steps are not followed.
Additionally, you will not be able to add new suppressions to expectedTime after updating.

Steps to upgrade to version 5.0.0:
1. Run the search `Broken Hosts - Populate bh_suppressions from expectedTime`
2. Run the search `Broken Hosts - Clear Permanent Suppressions expectedTime`
3. Enable the search `Broken Hosts - Auto Sort v5`
4. Disable the search `Broken Hosts - Auto Sort`
5. Enable the search `Broken Hosts - Purge and Sort bh_suppressions`

The above searches will automatically populate the new bh_suppressions lookup with currently used suppression entries in expectedTime,
clear expectedTime of all permanent suppressions, enable new expectedTime sorting logic, and schedule a search to automatically remove
outdated entries from bh_suppressions.

## Quickstart

1. Install the `Broken Hosts App for Splunk` on your ad-hoc search head.
2. Use the `Broken Hosts` dashboard to determine appropriate baselines for all of your critical data.
3. Use the `Configure Tunings` and  dashboard to configure your baselines and create suppressions.
4. Configure alert actions on the `Broken Hosts Alert Search` saved search in the Broken Hosts
   App for Splunk.
5. Enable the `Broken Hosts Alert Search` saved search in the Broken Hosts App for Splunk.
6. Run the search `Broken Hosts - Clear Permanent Suppressions from expectedTime`

## Documentation
https://brokenhosts.hurricanelabs.com

## Cloud Configuration
- By default this app is configured and all configuration options are optional. The following macros are available to configure:
- `default_contact`
- `default_expected_time`
- `ignore_after`		
- `linuxoslog_index`		
- `min_count`		
- `search_additions`	
- `wineventlog_index`
- `bh_volume_alerting_indexes`
- You can also configure the requirement of a ticket number being in comments when updating the table on the Configure Broken Hosts Lookup page. This configuration is availabe on the Setup page in the app.