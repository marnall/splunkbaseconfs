###################################################

# Splunk Windows Universal Forwarder Upgrade App Quick Start Installation Guide

###################################################

## Overview

This guide provides quick-start installation and deployment instructions for the Splunk Windows Universal Forwarder Upgrade App solution.

The goal of this document is to answer:

* Which app goes where?
* Which app goes to the Search Head?
* Which TA goes to the parsing/indexing tier?
* Which TA goes to Windows Universal Forwarders?
* Where does the Splunk Universal Forwarder MSI go?
* Which inputs should be enabled or disabled?
* How does the normal upgrade workflow run?
* How do retry and reset controls work?
* How do I validate the app is working?

This guide is intended to be a practical quick-start reference.

For deeper architecture, troubleshooting, dashboard interpretation, state behavior, and edge-case testing, refer to the additional documentation included with the app package.

---

###################################################

## Solution Components

###################################################

The solution includes three Splunk apps:

| App                                             | Deployment Target                          | Purpose                                                                                                                            |
| ----------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `SA-windows_uf_upgrade_monitoring`                     | Search Head / Search Head Cluster          | Provides dashboards, data model, navigation, documentation, and reporting views.                                                   |
| `TA-windows_uf_upgrade_automation`         | Windows Universal Forwarders               | Performs the Windows Universal Forwarder upgrade workflow, collects local upgrade logs, and includes optional retry-control logic. |
| `TA-windows_uf_upgrade_parsing` | Parsing tier / Indexers / Heavy Forwarders | Provides index and parsing configuration for upgrade logs and MSI logs.                                                            |

The solution intentionally separates search-head content, endpoint execution logic, and parsing/indexing configuration.

---

###################################################

## Recommended Deployment Model

###################################################

The recommended deployment model has three layers:

```
1. Search Head layer
2. Parsing / indexing layer
3. Windows Universal Forwarder endpoint layer
```

---

### Search Head / Search Head Cluster

Deploy this app to the Search Head layer:

```
SA-windows_uf_upgrade_monitoring
```

This app contains reporting and search-head content such as:

* Dashboards
* Data model
* Navigation
* Documentation
* Optional saved searches or lookups
* Search-time reporting knowledge objects

This app should not perform the endpoint upgrade workflow.

Do not deploy `SA-windows_uf_upgrade_monitoring` to Windows Universal Forwarders.

---

### Parsing / Indexing Tier

Deploy this TA to the parsing/indexing tier:

```
TA-windows_uf_upgrade_parsing
```

Deploy this TA to:

* Indexers
* Indexer clusters
* Heavy Forwarders, if Heavy Forwarders perform parsing in your environment

This TA contains parsing and indexing configuration such as:

* `indexes.conf`
* `props.conf` for `splunk_upgrade`
* `props.conf` for `splunk_upgrade_msi`
* Timestamp recognition
* Line breaking / line merging behavior
* Sourcetype parsing behavior

This TA should not run endpoint upgrade scripts.

Do not deploy `TA-windows_uf_upgrade_parsing` as the primary endpoint upgrade app.

---

### Windows Universal Forwarders

Deploy this app to Windows Universal Forwarders that should be upgraded:

```
TA-windows_uf_upgrade_automation
```

This app contains the endpoint-side upgrade components, including:

* Wrapper script
* Setup PowerShell script
* Execution PowerShell script
* Optional retry-control scripts
* Optional retry-reset scripts
* `splunk_installer` directory
* Scripted input configuration
* Log monitor configuration

This TA is responsible for:

* Validating the MSI installer
* Validating the installed Splunk Universal Forwarder version
* Creating the Windows Scheduled Task
* Running the MSI upgrade
* Stopping and starting the Splunk Universal Forwarder service
* Writing upgrade state
* Collecting local upgrade logs
* Preventing retry loops
* Supporting controlled retry actions when intentionally enabled

---

###################################################

## App Placement Summary

###################################################

| Component                                       | Deploy To                                  | Notes                                                                                        |
| ----------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `SA-windows_uf_upgrade_monitoring`               | Search Head / SHC                          | Dashboards, data model, navigation, documentation, and reporting content.                    |
| `TA-windows_uf_upgrade_parsing` | Parsing tier / Indexers / Heavy Forwarders | Index creation and parsing rules for upgrade and MSI logs.                                   |
| `TA-windows_uf_upgrade_automation`         | Windows Universal Forwarders               | Main endpoint upgrade workflow, log collection, state tracking, and optional retry controls. |

---

###################################################

## Recommended Installation Order

###################################################

Install the apps in this order:

```
1. Deploy TA-windows_uf_upgrade_parsing to the parsing/indexing tier.
2. Confirm the splunk_upgrade index exists.
3. Deploy SA-windows_uf_upgrade_monitoring to Search Heads / SHC.
4. Validate that the dashboards load.
5. Deploy TA-windows_uf_upgrade_automation to a small Windows UF test group.
6. Place the target Splunk Universal Forwarder MSI in the splunk_installer directory.
7. Validate log ingestion and field extraction.
8. Validate dashboards and troubleshooting searches.
9. Expand TA-windows_uf_upgrade_automation deployment to the intended Windows UF population.
10. Use retry-control inputs only when retry or marker reset actions are needed.
```

---

###################################################

## Directory Layout

###################################################

### Search Head App

Expected location:

```
$SPLUNK_HOME/etc/apps/SA-windows_uf_upgrade_monitoring/
```

Typical contents:

```
SA-windows_uf_upgrade_monitoring/
├── default/
├── metadata/
├── docs/
├── README/
└── static/
```

Common Search Head contents may include:

```
default/app.conf
default/datamodels.conf
default/indexes.conf
default/props.conf
default/data/models/splunk_upgrade.json
default/data/ui/nav/default.xml
default/data/ui/views/splunk_windows_overview.xml
default/data/ui/views/splunk_windows_troubleshooting.xml
docs/eventcodes.md
docs/quick-start-installation.md
docs/state-management.md
docs/testing-guide.md
metadata/default.meta
README/README.md
static/appIcon.png
static/appLogo.png
```

Note:

```
If indexes.conf or props.conf are included in the Search Head app, they are intended to support local testing, dashboard visibility, or search-time behavior. Distributed production parsing and index creation should be handled by TA-windows_uf_upgrade_parsing.
```

---

### Parsing TA

Expected location on parsing tier:

```
$SPLUNK_HOME/etc/apps/TA-windows_uf_upgrade_parsing/
```

Typical contents:

```
TA-windows_uf_upgrade_parsing/
├── default/
├── metadata/
└── README/
```

Common parsing-tier contents may include:

```
default/indexes.conf
default/props.conf
metadata/default.meta
README/README.md
```

Expected sourcetypes:

```
splunk_upgrade
splunk_upgrade_msi
```

---

### Main Windows UF Upgrade TA

Expected location:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\
```

Typical contents:

```
TA-windows_uf_upgrade_automation/
├── bin/
├── default/
├── metadata/
├── README/
└── splunk_installer/
```

Expected endpoint-side files may include:

```
bin\splunk_upgrade_wrapper.bat
bin\splunk_windows_upgrade_task_setup.ps1
bin\splunk_windows_upgrade_exec.ps1
bin\splunk_upgrade_force_retry_wrapper.bat
bin\splunk_upgrade_force_retry.ps1
bin\splunk_upgrade_force_retry_reset_wrapper.bat
bin\splunk_upgrade_force_retry_reset.ps1
splunk_installer\splunkforwarder-<version>-x64-release.msi
```

The exact script names may vary by release. The important requirement is that the main endpoint TA contains the upgrade workflow, log monitors, and disabled-by-default retry controls.

---

###################################################

## Index and Sourcetype Requirements

###################################################

Default index:

```
splunk_upgrade
```

Primary sourcetype:

```
splunk_upgrade
```

MSI log sourcetype:

```
splunk_upgrade_msi
```

If your environment uses a different index, update:

* `inputs.conf`
* `indexes.conf`
* Data model constraints
* Dashboards
* Saved searches
* Documentation examples

---

###################################################

## Create the Index

###################################################

The `splunk_upgrade` index should be created on the indexing tier.

This is normally handled by:

```
TA-windows_uf_upgrade_parsing
```

Example `indexes.conf`:

```
[splunk_upgrade]
homePath = $SPLUNK_DB/splunk_upgrade/db
coldPath = $SPLUNK_DB/splunk_upgrade/colddb
thawedPath = $SPLUNK_DB/splunk_upgrade/thaweddb
disabled = 0
```

Deploy this index configuration according to your environment standards.

For distributed environments, ensure the index exists on the indexing tier before the Universal Forwarders begin sending logs.

For indexer clusters, deploy index configuration using the cluster manager according to your organization’s standard process.

---

###################################################

## Parsing Configuration

###################################################

The parsing TA should define parsing behavior for:

```
splunk_upgrade
splunk_upgrade_msi
```

Recommended `props.conf` concepts for `splunk_upgrade`:

```
[splunk_upgrade]
SHOULD_LINEMERGE = false
TIME_PREFIX = ^
TIME_FORMAT = %Y-%m-%d %H:%M:%S
MAX_TIMESTAMP_LOOKAHEAD = 19
KV_MODE = auto
```

Recommended `props.conf` concepts for `splunk_upgrade_msi` depend on the MSI log format collected by the app.

The parsing TA is the correct location for:

* Event breaking
* Timestamp parsing
* Line merging behavior
* Sourcetype-level parsing behavior
* Index creation

Do not rely only on the Search Head app for parsing behavior in a distributed environment.

---

###################################################

## Search Head Installation

###################################################

Deploy the Search Head app:

```
SA-windows_uf_upgrade_monitoring
```

To:

```
$SPLUNK_HOME/etc/apps/
```

For a Search Head Cluster, deploy using the SHC deployer.

The Search Head app should contain:

* Dashboards
* Data model
* Navigation
* Documentation
* Optional saved searches or lookups
* Search-time reporting knowledge objects

After deployment, restart Splunk or perform the appropriate SHC bundle push.

Example standalone Search Head restart:

```
$SPLUNK_HOME/bin/splunk restart
```

Example SHC deployer push:

```
$SPLUNK_HOME/bin/splunk apply shcluster-bundle -target https://<search_head_captain>:8089
```

---

###################################################

## Search-Time Field Extraction

###################################################

The `splunk_upgrade` sourcetype uses key-value formatted events.

Recommended search-time extraction behavior:

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

If using accelerated data models, add required fields to the data model before enabling acceleration.

Important:

```
Parsing settings should live in TA-windows_uf_upgrade_parsing on the parsing/indexing tier.
Reporting objects, dashboards, and data models should live in SA-windows_uf_upgrade_monitoring on the Search Head layer.
```

---

###################################################

## Main Windows UF Upgrade TA Installation

###################################################

Deploy the main endpoint TA:

```
TA-windows_uf_upgrade_automation
```

To Windows Universal Forwarders using Deployment Server, manual install, configuration management, or another approved deployment method.

Expected endpoint location:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\
```

This TA should include:

* Upgrade wrapper script
* Setup PowerShell script
* Execution PowerShell script
* Optional retry-control scripts
* Optional retry-reset scripts
* `splunk_installer` directory
* Scripted input for the main upgrade workflow
* Monitor inputs for setup, execution, MSI, and retry-control logs

---

###################################################

## Splunk Universal Forwarder MSI Placement

###################################################

Place the target Splunk Universal Forwarder MSI in:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\splunk_installer\
```

Expected MSI naming pattern:

```
splunkforwarder-<version>-x64-release.msi
```

Example:

```
splunkforwarder-9.4.2-x64-release.msi
```

The app extracts the target version from the MSI filename.

If the target version cannot be extracted, the app logs event code:

```
9815
```

Only stage one intended MSI installer in the `splunk_installer` directory for a given deployment wave.

---

###################################################

## Endpoint Inputs

###################################################

The main endpoint TA should contain the input definitions required to run the upgrade workflow and collect logs.

Recommended main upgrade input:

```
[script://.\bin\splunk_upgrade_wrapper.bat]
disabled = false
interval = 2592000
sourcetype = splunk_upgrade
index = splunk_upgrade
```

Recommended log monitor inputs:

```
[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_setup.log]
disabled = false
sourcetype = splunk_upgrade
index = splunk_upgrade

[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_exec.log]
disabled = false
sourcetype = splunk_upgrade
index = splunk_upgrade

[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_msi_*.log]
disabled = false
sourcetype = splunk_upgrade_msi
index = splunk_upgrade
crcSalt = <SOURCE>
ignoreOlderThan = 30d

[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_force_retry_helper.log]
disabled = false
sourcetype = splunk_upgrade
index = splunk_upgrade
```

For controlled testing, you may disable the main scripted input and run the wrapper manually.

For production deployment, enable the main scripted input only when the app package and MSI are ready.

---

###################################################

## Optional Retry-Control Inputs

###################################################

Retry-control logic is included in:

```
TA-windows_uf_upgrade_automation
```

The retry-control inputs should be disabled by default.

The exact script names may vary by release, but the intended pattern is:

```
[script://.\bin\splunk_upgrade_force_retry_wrapper.bat]
disabled = true
interval = -1
sourcetype = splunk_upgrade
index = splunk_upgrade

[script://.\bin\splunk_upgrade_force_retry_reset_wrapper.bat]
disabled = true
interval = -1
sourcetype = splunk_upgrade
index = splunk_upgrade
```

Use the force retry input only when a failed endpoint needs one additional retry with the same MSI installer.

Use the retry reset input only when preparing an endpoint for another future retry wave.

Do not intentionally enable the force retry input and retry reset input at the same time during normal operations.

---

###################################################

## Normal Upgrade Workflow

###################################################

The normal upgrade workflow is:

```
1. Administrator deploys TA-windows_uf_upgrade_automation to targeted Windows Universal Forwarders.
2. Administrator stages the target Splunk Universal Forwarder MSI in the splunk_installer directory.
3. The main wrapper runs based on the configured scripted input interval.
4. Setup validates the MSI and installed Splunk Universal Forwarder version.
5. Setup writes or updates local JSON state.
6. Setup creates and starts a Windows Scheduled Task.
7. The scheduled task runs the upgrade execution script.
8. The execution script stops the Splunk Universal Forwarder service.
9. The execution script runs the MSI upgrade.
10. The execution script records success or failure.
11. The execution script attempts cleanup of the staged MSI.
12. The execution script updates the JSON state file.
13. The execution script starts the Splunk Universal Forwarder service.
14. The Universal Forwarder resumes forwarding upgrade logs.
15. Dashboards in SA-windows_uf_upgrade_monitoring show upgrade activity and results.
```

---

###################################################

## State and Retry Prevention

###################################################

The app writes a local JSON state file to:

```
C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json
```

The state file tracks:

* Installer name
* Installer hash
* Target version
* Previous version
* Current version
* Attempt count
* Last status
* Cleanup status
* `do_not_retry` value
* Last event code
* MSI log file

The app uses this state file to prevent uncontrolled retry loops.

If the same installer hash was already attempted and is marked:

```
do_not_retry=true
```

The setup script skips the upgrade and logs event code:

```
9819
```

This behavior is expected and protects endpoints from repeatedly attempting the same MSI after a failure or cleanup issue.

---

###################################################

## Controlled Retry Workflow

###################################################

Use this workflow when an endpoint failed and needs another attempt with the same MSI.

### First Controlled Retry

```
1. Identify failed endpoints in the dashboard.
2. Review failure details and MSI logs.
3. Fix the underlying issue.
4. Enable the force retry input for selected failed endpoints.
5. Retry-control logic creates force_retry.flag.
6. Retry-control logic creates force_retry_helper_created.marker.
7. Main upgrade setup script consumes force_retry.flag.
8. Main upgrade setup script logs event code 9820.
9. Main upgrade workflow retries the same MSI one time.
10. Disable the force retry input after the intended retry wave.
```

Expected retry-control events:

| EventCode | Meaning                                                                   |
| --------: | ------------------------------------------------------------------------- |
|    `9830` | Force retry flag was created successfully.                                |
|    `9831` | Force retry logic already ran and marker exists; no new flag was created. |
|    `9832` | Force retry logic failed to create the force retry flag.                  |
|    `9820` | Main setup script consumed `force_retry.flag` and allowed one retry.      |

### Additional Controlled Retry Wave

If the force retry logic has already run and the marker exists, the retry-control logic logs `9831` and does not create another flag.

To prepare for another retry wave:

```
1. Fix the underlying issue.
2. Enable the retry reset input for selected endpoints.
3. Retry-reset logic removes force_retry_helper_created.marker.
4. Retry-reset logic logs event code 9833.
5. Disable the retry reset input.
6. Enable the force retry input again for the affected endpoints.
7. Retry-control logic creates a new force_retry.flag.
8. Main setup script consumes the flag and allows another retry.
```

Expected retry-reset events:

| EventCode | Meaning                                                         |
| --------: | --------------------------------------------------------------- |
|    `9833` | Force retry helper marker was removed successfully.             |
|    `9834` | Force retry helper marker was not present; no reset was needed. |
|    `9835` | Retry reset logic failed to remove the marker.                  |

Important:

```
Do not intentionally enable the force retry input and retry reset input at the same time during normal operations.
```

---

###################################################

## Force Redeploy Guidance

###################################################

Deployment Server may not redeploy an app if the app package has not changed.

If the endpoint TA needs to be redeployed but its content has not changed, add or update a harmless marker file such as:

```
force_redeploy.txt
```

Example on Linux/macOS:

```
touch force_redeploy.txt
```

Example on Windows PowerShell:

```
New-Item -ItemType File -Force .\force_redeploy.txt
```

This can help force the app package to be updated and redeployed.

---

###################################################

## Deployment Server Guidance

###################################################

Recommended server classes:

| Server Class                       | Apps                                                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Windows UF Upgrade - Main          | `TA-windows_uf_upgrade_automation`                                                                       |
| Windows UF Upgrade - Retry Control | `TA-windows_uf_upgrade_automation` with local override enabling force retry input for selected endpoints |
| Windows UF Upgrade - Retry Reset   | `TA-windows_uf_upgrade_automation` with local override enabling retry reset input for selected endpoints |

Recommended workflow:

```
1. Deploy TA-windows_uf_upgrade_automation to Windows UFs targeted for upgrade.
2. Use dashboards to monitor upgrade results.
3. Create or update a server class containing failed endpoints.
4. Use a local inputs.conf override to enable the force retry input only for those failed endpoints.
5. Disable the force retry input after the retry wave.
6. If another retry wave is needed, enable the retry reset input first.
7. Disable the retry reset input.
8. Enable the force retry input again only when another controlled retry is needed.
```

---

###################################################

## Validation Searches

###################################################

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

### Retry Prevention Events

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9819
| table _time host eventcode status message installer_name target_version cleanup_status details
| sort -_time
```

### Retry Control Events

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

### Current UF Version Inventory

```
index=_internal source=*metrics.log* group=tcpin_connections os=Windows
| stats latest(_time) AS last_seen latest(version) AS uf_version latest(sourceHost) AS source_ip by hostname
| eval last_seen=strftime(last_seen, "%Y-%m-%d %H:%M:%S")
| table hostname uf_version source_ip last_seen
| sort hostname
```

---

###################################################

## Dashboard Validation

###################################################

After installing the Search Head app, validate the dashboards:

```
Windows UF Upgrade Overview
Windows UF Upgrade Troubleshooting
```

The Overview dashboard should answer:

* How many hosts attempted upgrade?
* How many succeeded?
* How many failed?
* What percentage of Windows UFs are on the target version?
* Were retry prevention events observed?
* Were retry-control actions observed?
* Were state tracking or cleanup errors observed?

The Troubleshooting dashboard should answer:

* Which setup or precheck failures occurred?
* Which scheduled task failures occurred?
* Which upgrade failures occurred?
* Did Splunk stop/start correctly?
* Were MSI errors logged?
* Did state tracking work?
* Did retry prevention work?
* Did retry-control logic create or reset retry-control files?
* What raw events were generated by each host?

---

###################################################

## Quick Troubleshooting

###################################################

### No dashboard data appears

Check:

```
index=splunk_upgrade sourcetype=splunk_upgrade
| stats count by host sourcetype
```

If no events appear:

* Confirm the `splunk_upgrade` index exists.
* Confirm `TA-windows_uf_upgrade_parsing` is deployed to the parsing/indexing tier.
* Confirm endpoint inputs are enabled.
* Confirm logs exist under `C:\ProgramData\SplunkUpgrade\`.
* Confirm the Universal Forwarder is forwarding to the correct indexers.
* Confirm data model constraints match the configured index and sourcetype.

---

### Events are indexed but fields are missing

Check:

* `KV_MODE = auto` is configured for the `splunk_upgrade` sourcetype.
* The relevant fields are included in the data model.
* The dashboard is using the correct data model field names.
* Parsing/search-time knowledge objects are deployed to the correct tier.

---

### MSI installer was not found

Expected event:

```
9800
```

Check:

* The MSI exists in the endpoint TA `splunk_installer` directory.
* The MSI was packaged with the app or deployed correctly.
* The MSI filename matches the expected Splunk Universal Forwarder naming pattern.
* File permissions allow the script to read the MSI.

---

### Target version could not be extracted

Expected event:

```
9815
```

Check:

* The MSI filename includes a valid version.
* The filename follows a standard pattern such as `splunkforwarder-9.4.2-x64-release.msi`.
* The staged file is a real Splunk Universal Forwarder MSI.

---

### Upgrade skipped because target is same or lower

Expected event:

```
9816
```

This means the target version is equal to or lower than the currently installed Splunk Universal Forwarder version.

This is expected when testing with the same version or an older installer.

---

### Upgrade failed

Expected event:

```
9813
```

Check:

* The `details` field.
* The MSI log path in `msi_log_file`.
* The endpoint operating system.
* MSI installation permissions.
* Whether the Splunk Universal Forwarder service was stopped and restarted successfully.
* Whether endpoint security tools blocked the installer.

---

### Retry prevention skipped the upgrade

Expected event:

```
9819
```

This means the same installer hash was already attempted and is marked:

```
do_not_retry=true
```

This is expected after a terminal state and confirms retry-loop prevention is working.

To retry the same installer, use the controlled retry workflow.

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

If a retry flag is needed, enable the force retry input after confirming the marker state.

---

###################################################

## Recommended First-Time Deployment Sequence

###################################################

```
1. Deploy TA-windows_uf_upgrade_parsing to the parsing/indexing tier.
2. Confirm the splunk_upgrade index exists.
3. Deploy SA-windows_uf_upgrade_monitoring to Search Heads / SHC.
4. Validate dashboards load.
5. Deploy TA-windows_uf_upgrade_automation to a small Windows UF test group.
6. Place the target Splunk UF MSI in splunk_installer.
7. Enable the main upgrade scripted input when ready.
8. Monitor Windows UF Upgrade Overview.
9. Review Windows UF Upgrade Troubleshooting for failed endpoints.
10. Fix failed endpoint issues.
11. Enable the force retry input only for endpoints that need a controlled retry.
12. If another retry wave is needed later, enable the retry reset input first, then enable the force retry input again.
```

---

###################################################

## Splunk Cloud Note

###################################################

This solution includes endpoint-side Windows components that are intended for deployment to Windows Universal Forwarders.

Do not deploy `TA-windows_uf_upgrade_automation` to Splunk Cloud search or indexing tiers.

The Search Head app `SA-windows_uf_upgrade_monitoring` provides dashboards and reporting content. Validate Splunk Cloud compatibility requirements before installing any app in a Splunk Cloud environment.

The parsing app `TA-windows_uf_upgrade_parsing` should be deployed only where parsing and index configuration are supported by your Splunk deployment model.

---

###################################################

## Related Documentation

###################################################

See also:

```
docs/eventcodes.md
docs/state-management.md
docs/testing-guide.md
README/README.md
```

