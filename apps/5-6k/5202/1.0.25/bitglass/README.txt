Changes from 1.0.14 to 1.0.23:
- handling of 429 rate limit; won't hit server until the reset time
- 429 or http errors and nextpagetoken is not used
- nextpagetoken missing or using earlier date due to threading
- invalid nextpagetoken (empty array) due to dates later than last entry
- update Forcepoint software license agreement

Changes from 1.0.13 to 1.0.14:

- Drop Python 2 support
- Support saving the log stream context to a variable for platforms where File I/O is not available
- Improve some log messages including the ones for log stream context reset
- Fix parsing the syslog sink destination
- Minor bug fixes (including ESLint, flake8 and other static code scanners' warnings and exceptions)
- Code refactoring and cleanups

Changes from 1.0.10 to 1.0.13:

- Use Bitglass API version 1.1.5 by default
- Add healthproxy, healthapi and healthsystem log types
- Support Splunk 8.2.2
- Switch to using JQuery 3.5
- Fixed drilldown links in some widgets
- Other minor bug fixes

Changes from 1.0.9 to 1.0.10:

- 'Rewind Logs' option to re-ingest the logs starting from 30 days ago (resets lastlog-*.json files)
- Fix logs hold up when the very first request after launching the app for the first time fails

Changes from 1.0.8 to 1.0.9:

- Use Bitglass API version 1.1.0 by default
- Add swgweb and swgwebdlp log types
- Add the option to override the default index 'main' (manual steps are still required, please see below)
- Test and support the Redhat distro in addition to Ubuntu
- Split the lastlog.json file into multiple lastlog-<log type>.json files with added ingestion time and last status for better diagnostics
- Fix occasional multiple events lumped into one due to triggering the default multiline merging logic in Splunk by adding the props.conf file with SHOULD_LINEMERGE = false
- Fix the "Top 10 Devices" widget for the swgweb log type
- Fix Bandit and ESLint security warnings (no actual problems were found)


Changes from 1.0.6 to 1.0.8:

- Fix Splunk cloud certification report issues: potential file access outside of the app folder; changed the log file location to var/log/splunk; disable unmasking token and password input fields; mask the proxy data as it may contain a password
- Add authorize_sample.conf and indexes_sample.conf
- Display the app version and the latest supported Bitglass API version
- Support the latest Splunk 7.2 version (7.2 10.1) that still uses Python 2 only
- Add Logging Interval setting
- Fix errors logged to the Splunk index


Changes from 1.0.4 to 1.0.6:

- Store OAuth 2.0 token encrypted in passwords.conf
- Fix AppInspect warnings
- Fix js errors in the setup page on connection failure
- Cosmetic updates to the setup page
- Added support for Bitglass API versions 1.0.8 and 1.0.9
- Added Policy ID widget
- Bug fixes
- Initial data import is increased from 7 to 30 days


Troubleshooting tips, known issues and miscellaneous notes:

- In some browsers, after submitting the app configuration settings form, you may be prompted repeatedly to configure the app again. In such case, restart the Splunk instance and the app widget screen should show up normally
- The app logs are available in $SPLUNK_HOME/var/log/splunk/bitglass.log
- The Splunk logs are available in $SPLUNK_HOME/var/log/splunk/splunkd.log
- The API connection settings such as the URL, OAuth token etc. are saved in $SPLUNK_HOME/etc/apps/bitglass/local/forward.json
- The last ingested data with the time and error code (if failed) is available in the app directory $SPLUNK_HOME/etc/apps/bitglass/local in lastlog-*.json files
- To Configure a new index to override the use of the default Splunk index 'main' please follow the steps below:
    1. Settings / Indexes / New Index / Enter 'bitglass' under Index Name / Save
    2. Settings / Roles / user / 3. Indexes / Click 'Default' checkbox for 'bitglass' / Save
    3. Go to the app setup page and choose 'bitglass' index instead of 'default'
    4. Optional: If you need to re-populate the new index with the past log events from 30 days ago on, click 'Rewind Logs' and confirm
    5. Click 'Save'
