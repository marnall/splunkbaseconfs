##################################

# Splunk Windows Universal Forwarder Upgrade App

##################################

## Overview

This README supports the Splunk Windows Universal Forwarder Upgrade App solution.

The Search Head component is packaged as:

```
sa_uf_upgrade_for_windows
```

`sa_uf_upgrade_for_windows` is the Search Head app for the Windows Universal Forwarder upgrade solution.

This app provides the reporting, documentation, dashboards, and data model content used to monitor Windows Universal Forwarder upgrade activity across an environment.

The Search Head app is designed to help administrators answer questions such as:

* Which Windows Universal Forwarders attempted an upgrade?
* Which hosts upgraded successfully?
* Which hosts failed?
* Which hosts are currently on the target Splunk Universal Forwarder version?
* Which hosts are not on the target version?
* Were setup, scheduled task, service control, MSI, cleanup, or state tracking issues observed?
* Did retry-loop prevention work?
* Were controlled retry or retry reset actions performed?
* Which endpoints need remediation?

This app does not perform endpoint upgrades directly.

Endpoint-side upgrade execution is handled by:

```
ta_uf_upgrade_application_for_windows
```

Parsing and index configuration are handled by:

```
ta_uf_upgrade_application_for_windows_parsing
```

---

##################################

## Solution Components

##################################

The complete solution includes the following apps and TAs.

| App                                             | Deployment Target                          | Purpose                                                                                                  |
| ----------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `sa_uf_upgrade_for_windows`                     | Search Head / Search Head Cluster          | Dashboards, data model, navigation, documentation, and reporting views.                                  |
| `ta_uf_upgrade_application_for_windows`         | Windows Universal Forwarders               | Endpoint-side upgrade execution, local log collection, state tracking, and optional retry-control logic. |
| `ta_uf_upgrade_application_for_windows_parsing` | Parsing tier / Indexers / Heavy Forwarders | Index creation and parsing configuration for upgrade logs and MSI logs.                                  |

The solution intentionally separates:

* Search Head dashboards and reporting
* Windows endpoint upgrade execution
* Parsing and indexing configuration

---

##################################

## What This Search Head App Provides

##################################

`sa_uf_upgrade_for_windows` provides Search Head functionality for the upgrade solution.

Typical contents include:

* Dashboards
* Navigation
* Data model
* Search-time knowledge objects
* Event code documentation
* State management documentation
* Testing guide
* Quick-start installation guide
* Optional saved searches or lookups

This app should be installed on:

```
Search Heads
Search Head Cluster members through the SHC deployer
```

This app should not be used as the endpoint-side upgrade execution TA.

Do not deploy `sa_uf_upgrade_for_windows` to Windows Universal Forwarders.

---

##################################

## Deployment Model

##################################

The recommended deployment model has three layers:

```
1. Search Head layer
2. Parsing / indexing layer
3. Windows Universal Forwarder endpoint layer
```

### Search Head Layer

Deploy:

```
sa_uf_upgrade_for_windows
```

Purpose:

```
Dashboards, data model, reporting views, navigation, and documentation.
```

### Parsing / Indexing Layer

Deploy:

```
ta_uf_upgrade_application_for_windows_parsing
```

Purpose:

```
indexes.conf, props.conf, sourcetype parsing, timestamp handling, line breaking, and index creation.
```

### Windows Universal Forwarder Layer

Deploy:

```
ta_uf_upgrade_application_for_windows
```

Purpose:

```
Upgrade scripts, wrapper, scheduled task creation, MSI execution, state tracking, retry-loop prevention, optional retry-control logic, and local log collection.
```

---

##################################

## Recommended Installation Order

##################################

Install and validate the solution in this order:

```
1. Deploy ta_uf_upgrade_application_for_windows_parsing to the parsing/indexing tier.
2. Confirm the splunk_upgrade index exists.
3. Deploy sa_uf_upgrade_for_windows to Search Heads / SHC.
4. Validate dashboards load successfully.
5. Deploy ta_uf_upgrade_application_for_windows to a small Windows UF test group.
6. Place the target Splunk Universal Forwarder MSI in the endpoint TA splunk_installer directory.
7. Enable the endpoint upgrade scripted input when ready.
8. Monitor Windows UF Upgrade Overview.
9. Review Windows UF Upgrade Troubleshooting for failed endpoints.
10. Fix failed endpoint issues.
11. Use the force retry input only for endpoints that need a controlled retry.
12. If another retry wave is needed later, use the retry reset input first, then use the force retry input again.
```

---

##################################

## Search Head Installation

##################################

Deploy this app to:

```
$SPLUNK_HOME/etc/apps/sa_uf_upgrade_for_windows/
```

For Search Head Cluster environments, deploy this app using the SHC deployer.

Example standalone Search Head path:

```
/opt/splunk/etc/apps/sa_uf_upgrade_for_windows/
```

Example Windows Search Head path:

```
C:\Program Files\Splunk\etc\apps\sa_uf_upgrade_for_windows\
```

Example SHC deployer bundle location:

```
$SPLUNK_HOME/etc/shcluster/apps/sa_uf_upgrade_for_windows/
```

After placing the app, restart Splunk or apply the Search Head Cluster bundle using your standard process.

Example standalone restart:

```
$SPLUNK_HOME/bin/splunk restart
```

Example SHC deployer push:

```
$SPLUNK_HOME/bin/splunk apply shcluster-bundle -target https://<search_head_captain>:8089
```

---

##################################

## Parsing Tier Installation

##################################

Deploy the parsing TA to the parsing/indexing tier:

```
ta_uf_upgrade_application_for_windows_parsing
```

Deploy this TA to:

* Indexers
* Indexer clusters
* Heavy Forwarders, if Heavy Forwarders perform parsing in your environment

This TA should include:

```
indexes.conf
props.conf
```

The parsing TA is responsible for:

* Creating the `splunk_upgrade` index
* Defining parsing behavior for `splunk_upgrade`
* Defining parsing behavior for `splunk_upgrade_msi`
* Timestamp handling
* Event breaking
* Line merging behavior
* Sourcetype-level parsing behavior

Do not rely only on the Search Head app for parsing behavior in a distributed environment.

---

##################################

## Endpoint Upgrade TA Installation

##################################

Deploy the main endpoint TA to Windows Universal Forwarders:

```
ta_uf_upgrade_application_for_windows
```

Expected endpoint path:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\ta_uf_upgrade_application_for_windows\
```

The Splunk Universal Forwarder MSI should be placed in:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\ta_uf_upgrade_application_for_windows\splunk_installer\
```

The MSI filename must start with:

```
splunkforwarder
```

and should include a parseable version.

Example:

```
splunkforwarder-9.4.2-x64-release.msi
```

The endpoint TA performs the upgrade workflow.

The Search Head app only visualizes and reports on the results.

---

##################################

## Retry-Control Logic

##################################

Controlled retry logic is included in:

```
ta_uf_upgrade_application_for_windows
```

Retry-control inputs should be disabled by default.

Use retry-control logic only when a failed endpoint needs one additional retry with the same MSI installer.

The retry-control workflow uses the following files:

```
C:\ProgramData\SplunkUpgrade\state\force_retry.flag
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

The force retry flag allows the same MSI hash to run one additional time.

The marker file prevents repeated force retry flag creation if the retry-control input remains enabled.

Expected force retry event codes:

| EventCode | Meaning                                                               |
| --------: | --------------------------------------------------------------------- |
|    `9830` | Force retry flag created successfully.                                |
|    `9831` | Force retry logic already ran and marker exists; no new flag created. |
|    `9832` | Force retry logic failed to create the force retry flag.              |
|    `9820` | Main setup script consumed `force_retry.flag` and allowed one retry.  |

The retry reset workflow removes:

```
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

Expected retry reset event codes:

| EventCode | Meaning                                        |
| --------: | ---------------------------------------------- |
|    `9833` | Retry marker removed successfully.             |
|    `9834` | Retry marker was not present; no reset needed. |
|    `9835` | Retry reset logic failed to remove the marker. |

Important:

```
Do not intentionally enable the force retry input and retry reset input at the same time during normal operations.
```

---

##################################

## Index and Sourcetypes

##################################

Default index:

```
splunk_upgrade
```

Primary upgrade sourcetype:

```
splunk_upgrade
```

MSI log sourcetype:

```
splunk_upgrade_msi
```

If your environment uses a different index or sourcetype naming standard, update:

* Parsing TA configuration
* Endpoint TA `inputs.conf`
* Data model constraints
* Dashboards
* Saved searches
* Documentation examples

---

##################################

## Data Sources

##################################

The endpoint upgrade TA writes logs to:

```
C:\ProgramData\SplunkUpgrade\
```

Primary logs:

| Log File                                | Sourcetype           | Purpose                                                                                                       |
| --------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------- |
| `splunk_upgrade_setup.log`              | `splunk_upgrade`     | Setup, validation, state checks, retry prevention, force retry flag consumption, and scheduled task creation. |
| `splunk_upgrade_exec.log`               | `splunk_upgrade`     | Main upgrade execution, Splunk service control, MSI execution, result logging, cleanup, and final state.      |
| `splunk_upgrade_msi_<timestamp>.log`    | `splunk_upgrade_msi` | Verbose MSI installer output.                                                                                 |
| `splunk_upgrade_force_retry_helper.log` | `splunk_upgrade`     | Force retry and retry reset activity.                                                                         |

Important:

```
The retry-control log monitor should live in the main endpoint TA so retry-control events can continue to be collected after retry-control inputs are disabled.
```

---

##################################

## Dashboards

##################################

This Search Head app provides dashboards for operational visibility.

Common dashboards include:

```
Windows UF Upgrade Overview
Windows UF Upgrade Troubleshooting
```

### Windows UF Upgrade Overview

The Overview dashboard is intended to answer high-level rollout questions:

* How many hosts attempted upgrade?
* How many hosts upgraded successfully?
* How many hosts failed upgrade?
* What percentage of Windows UFs are on the target version?
* Which Windows UFs are not on the target version?
* Were retry prevention events observed?
* Were retry-control actions observed?
* Were state tracking errors observed?
* Were installer cleanup failures observed?

The primary remediation panel should be:

```
Hosts Not on Target Version
```

Use this panel to identify systems that still require action.

### Windows UF Upgrade Troubleshooting

The Troubleshooting dashboard is intended for deeper investigation:

* Setup and precheck errors
* Scheduled task issues
* Upgrade failures
* Splunk service stop/start behavior
* MSI installer diagnostics
* JSON state tracking
* Retry-loop prevention
* Force retry activity
* Retry reset activity
* Raw structured upgrade events

Use this dashboard when a host failed upgrade, did not retry, generated state errors, or needs detailed operational review.

---

##################################

## Data Model

##################################

This Search Head app may include a data model for upgrade reporting.

The data model should support dashboard acceleration and structured reporting for fields such as:

```
eventcode
status
message
details
installer_name
installer_hash
installer_path
target_version
previous_version
current_version
upgrade_success
attempt_count
last_status
cleanup_status
do_not_retry
force_retry_file
marker_file
taskname
splunkd_status
msi_log_file
date
time
```

If using data model acceleration, validate field availability before enabling acceleration.

If dashboards show counts but table fields appear empty, confirm the relevant fields exist in the data model.

---

##################################

## Search-Time Field Extraction

##################################

Upgrade app events are written in key-value format.

Recommended search-time behavior for `splunk_upgrade`:

```
[splunk_upgrade]
KV_MODE = auto
```

This allows Splunk to extract fields such as:

```
eventcode
status
message
details
installer_name
installer_hash
target_version
attempt_count
last_status
cleanup_status
do_not_retry
force_retry_file
marker_file
taskname
splunkd_status
msi_log_file
```

Parsing settings such as timestamp extraction and line breaking should live in:

```
ta_uf_upgrade_application_for_windows_parsing
```

Search-time reporting objects should live in:

```
sa_uf_upgrade_for_windows
```

---

##################################

## Normal Upgrade Workflow

##################################

The normal endpoint workflow is performed by:

```
ta_uf_upgrade_application_for_windows
```

Workflow summary:

```
1. Splunk runs the scripted input wrapper.
2. Wrapper runs the setup PowerShell script.
3. Setup validates the MSI, Splunk binary, target version, and state.
4. Setup creates and starts a Windows Scheduled Task.
5. Scheduled task runs the execution script as SYSTEM.
6. Execution script writes retry-protection state.
7. Execution script stops Splunk.
8. Execution script runs msiexec.
9. Execution script logs success or failure.
10. Execution script attempts installer cleanup.
11. Execution script writes final state.
12. Execution script starts Splunk.
```

Expected successful upgrade event flow:

```
9818
9821
9803
9805
9821
9810
9812
9823
9821
9808
```

Expected failed upgrade with cleanup success event flow:

```
9818
9821
9803
9805
9821
9810
9813
9823
9821
9808
```

---

##################################

## State and Retry Behavior

##################################

The endpoint upgrade TA stores local state in:

```
C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json
```

The app hashes the MSI installer.

If the same MSI hash has already been attempted and is marked:

```
do_not_retry=true
```

the setup script skips the upgrade and logs:

```
9819
```

This prevents repeated upgrade loops when:

* The MSI remains in `splunk_installer`
* Installer cleanup fails
* Splunk restarts after upgrade
* The scripted input runs again
* The same app package is redeployed
* A previous failed attempt already reached a terminal state

To retry intentionally, use the controlled retry workflow.

---

##################################

## Controlled Retry Workflow

##################################

Use this workflow when an endpoint failed and needs one more attempt with the same MSI.

### First Retry Attempt

```
1. Identify failed endpoints in the dashboard.
2. Review failure details and MSI logs.
3. Fix the underlying issue.
4. Enable the force retry input for selected failed endpoints.
5. Force retry logic creates force_retry.flag and marker.
6. Main upgrade setup script consumes force_retry.flag.
7. Main upgrade setup script logs event code 9820.
8. Main upgrade workflow retries the same MSI one time.
9. Disable the force retry input after the retry wave.
```

### Additional Retry Attempt

If the force retry input already ran once and the marker exists, the force retry logic will log `9831` and will not create another flag.

To prepare for another retry wave:

```
1. Fix the underlying issue.
2. Enable the retry reset input for affected endpoints.
3. Retry reset logic removes force_retry_helper_created.marker.
4. Retry reset logic logs event code 9833.
5. Disable the retry reset input.
6. Enable the force retry input again for selected endpoints.
7. Force retry logic creates a new force_retry.flag.
8. Main app consumes the flag and allows another retry.
9. Disable the force retry input after the retry wave.
```

Important:

```
Do not intentionally enable the force retry input and retry reset input at the same time during normal operations.
```

---

##################################

## Important Operational Notes

##################################

* The Search Head app does not run endpoint upgrade scripts.
* Endpoint upgrade execution is handled by `ta_uf_upgrade_application_for_windows`.
* Index and parsing configuration should be deployed using `ta_uf_upgrade_application_for_windows_parsing`.
* Retry-control inputs should be enabled only when retry-control actions are needed.
* Do not intentionally enable the force retry input and retry reset input at the same time during normal operations.
* Failed upgrade events remain in Splunk for historical visibility.
* A later successful upgrade does not remove earlier failure events.
* Use `Hosts Not on Target Version` as the primary remediation view.
* Use failure panels for historical troubleshooting and root cause analysis.
* Do not delete the state file in production unless intentionally resetting local retry protection.
* Prefer controlled retry inputs over manual state deletion when retrying endpoints at scale.

---

##################################

## Quick Validation Searches

##################################

### Recent Upgrade Events

```
index=splunk_upgrade sourcetype=splunk_upgrade earliest=-24h
| table _time host eventcode status message details
| sort -_time
```

### Upgrade Results

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9812,9813)
| table _time host eventcode status message previous_version current_version details
| sort -_time
```

### Hosts Blocked by Retry Prevention

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9819
| table _time host eventcode status message installer_name target_version cleanup_status details
| sort -_time
```

### Retry Control Activity

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9820,9830,9831,9832,9833,9834,9835)
| table _time host eventcode status message details force_retry_file marker_file
| sort -_time
```

### State Tracking Errors

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9822
| table _time host eventcode status message details state_file installer_path force_retry_file
| sort -_time
```

### Current Windows UF Version Inventory

```
index=_internal source=*metrics.log* group=tcpin_connections os=Windows
| stats latest(_time) AS last_seen latest(version) AS uf_version latest(sourceHost) AS source_ip by hostname
| eval last_seen=strftime(last_seen, "%Y-%m-%d %H:%M:%S")
| table hostname uf_version source_ip last_seen
| sort hostname
```

---

##################################

## Documentation

##################################

Additional documentation is available in the `docs` directory.

Recommended documentation files:

```
docs/quick-start-installation.md
docs/eventcodes.md
docs/state-management.md
docs/testing-guide.md
```

Recommended use:

| Document                      | Purpose                                                                       |
| ----------------------------- | ----------------------------------------------------------------------------- |
| `quick-start-installation.md` | Practical installation and first-use guide.                                   |
| `eventcodes.md`               | Event code reference for dashboards, troubleshooting, and validation.         |
| `state-management.md`         | Explanation of JSON state, retry prevention, force retry, and reset behavior. |
| `testing-guide.md`            | Step-by-step validation and fault-injection guide.                            |

---

##################################

## Basic Troubleshooting

##################################

### No dashboard data appears

Check:

```
index=splunk_upgrade sourcetype=splunk_upgrade
| stats count by host sourcetype
```

If no events appear:

* Confirm the `splunk_upgrade` index exists.
* Confirm `ta_uf_upgrade_application_for_windows_parsing` is deployed to the parsing/indexing tier.
* Confirm endpoint inputs are enabled.
* Confirm logs exist under `C:\ProgramData\SplunkUpgrade\`.
* Confirm Windows Universal Forwarders are forwarding data.
* Confirm dashboards and data model constraints use the correct index and sourcetype.

---

### Events appear but fields are missing

Check:

* `KV_MODE = auto` is configured for `splunk_upgrade`.
* Search-time field extraction is available on the Search Head.
* Data model fields include the expected fields.
* Data model acceleration has been rebuilt after field changes.
* The dashboard field names match the data model field names.

---

### MSI not found

Expected event:

```
9800
```

Check that the MSI exists in:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\ta_uf_upgrade_application_for_windows\splunk_installer\
```

The filename should begin with:

```
splunkforwarder
```

---

### Same installer is skipped

Expected event:

```
9819
```

This means the same installer hash was already attempted and marked:

```
do_not_retry=true
```

Use the controlled retry workflow if another retry is intended.

---

### Force retry input does not create a new flag

Expected event:

```
9831
```

This means the marker already exists:

```
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

Use the retry reset input first if another retry wave is intended.

---

### Retry reset says marker not present

Expected event:

```
9834
```

This means there was no marker to remove.

If a retry flag is needed, enable or run the force retry input after confirming marker state.

---

##################################

## File and State Locations

##################################

Endpoint log path:

```
C:\ProgramData\SplunkUpgrade\
```

Endpoint state path:

```
C:\ProgramData\SplunkUpgrade\state\
```

State file:

```
C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json
```

Force retry flag:

```
C:\ProgramData\SplunkUpgrade\state\force_retry.flag
```

Force retry marker:

```
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

Retry-control log:

```
C:\ProgramData\SplunkUpgrade\splunk_upgrade_force_retry_helper.log
```

---

##################################

## Splunk Cloud and Platform Notes

##################################

This solution includes endpoint-side Windows components intended for Windows Universal Forwarders.

Do not deploy `ta_uf_upgrade_application_for_windows` to Splunk Cloud search or indexing tiers.

The Search Head app `sa_uf_upgrade_for_windows` provides dashboards and reporting content. Validate Splunk Cloud compatibility requirements before installing any app in a Splunk Cloud environment.

The parsing app `ta_uf_upgrade_application_for_windows_parsing` should be deployed only where parsing and index configuration are supported by your Splunk deployment model.

---

##################################

## Change History

##################################

### Version 1.0.0

* Added Windows Universal Forwarder upgrade reporting app.
* Added dashboard guidance for successful attempts, failed attempts, and hosts not on target version.
* Added event code documentation.
* Added state management documentation.
* Added testing guide.

### Updated Solution Structure

* Clarified that `sa_uf_upgrade_for_windows` is the Search Head app.
* Added `ta_uf_upgrade_application_for_windows_parsing` as the parsing/indexing tier TA.
* Added `ta_uf_upgrade_application_for_windows` as the endpoint upgrade execution TA.
* Consolidated retry-control and retry-reset logic into `ta_uf_upgrade_application_for_windows`.
* Removed references to separate force retry and retry reset helper TAs.
* Added retry-control event codes `9830-9835`.
* Added state and retry prevention guidance.
* Added dashboard and data model validation guidance.

