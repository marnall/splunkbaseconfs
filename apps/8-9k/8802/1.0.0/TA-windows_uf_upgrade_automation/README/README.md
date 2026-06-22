##################################

# Splunk Windows Universal Forwarder Upgrade App - Endpoint Upgrade TA

##################################

## Package Name

```
TA-windows_uf_upgrade_automation
```

---

## Overview

`TA-windows_uf_upgrade_automation` is the endpoint-side upgrade execution TA for the Splunk Windows Universal Forwarder Upgrade App solution.

This TA is deployed to Windows Universal Forwarders and is responsible for staging, validating, executing, logging, and controlling Splunk Universal Forwarder upgrades on Windows systems.

The TA uses a scripted input to launch a wrapper script. The wrapper runs the setup PowerShell script, which validates the environment, checks local state, and creates a Windows Scheduled Task. The scheduled task then runs the main upgrade execution script as `SYSTEM`.

This TA also includes disabled-by-default retry-control logic used to allow a failed endpoint to retry the same MSI one additional time without deleting the local state file.

This TA is designed to support controlled upgrades while preventing repeated retry loops against the same MSI installer.

---

##################################

## Solution Components

##################################

The full solution includes three Splunk apps.

| App                                             | Deployment Target                          | Purpose                                                                                                                         |
| ----------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| `SA-windows_uf_upgrade_monitoring`                     | Search Head / Search Head Cluster          | Dashboards, data model, navigation, documentation, and reporting views.                                                         |
| `TA-windows_uf_upgrade_automation`         | Windows Universal Forwarders               | Endpoint-side upgrade execution, local log collection, state tracking, retry-loop prevention, and optional retry-control logic. |
| `TA-windows_uf_upgrade_parsing` | Parsing tier / Indexers / Heavy Forwarders | Index creation and parsing configuration for upgrade logs and MSI logs.                                                         |

---

##################################

## Purpose

##################################

This TA is responsible for:

* Detecting a Splunk Universal Forwarder MSI in the `splunk_installer` directory
* Validating the currently installed Splunk Universal Forwarder version
* Extracting the target version from the MSI filename
* Calculating the installer hash
* Reading and writing persistent JSON upgrade state
* Preventing repeated retry loops for the same installer
* Creating and starting a Windows Scheduled Task
* Running the MSI upgrade process as `SYSTEM`
* Stopping and starting the Splunk Universal Forwarder service
* Logging setup, execution, MSI, cleanup, state, and retry events
* Monitoring local upgrade logs for forwarding to Splunk
* Creating a controlled `force_retry.flag` when the force retry input is enabled
* Resetting the retry marker when the retry reset input is enabled

This TA should be deployed to Windows Universal Forwarders that are intended to participate in the upgrade workflow.

---

##################################

## What This TA Does Not Do

##################################

This TA does not:

* Provide Search Head dashboards
* Provide Search Head navigation
* Provide the data model
* Define indexer-side parsing configuration
* Create the `splunk_upgrade` index
* Provide reporting-only functionality

Dashboards, data model, navigation, and documentation are handled by:

```
SA-windows_uf_upgrade_monitoring
```

Index and parsing configuration are handled by:

```
TA-windows_uf_upgrade_parsing
```

---

##################################

## Deployment Target

##################################

Deploy this TA to:

```
Windows Universal Forwarders
```

Do not deploy this TA to:

```
Search Heads
Indexers
Cluster Managers
Linux Universal Forwarders
Splunk Cloud search or indexing tiers
```

A Deployment Server may store and distribute this TA as an app package source, but the TA is intended to run on Windows Universal Forwarders.

Recommended deployment method:

```
Splunk Deployment Server
```

This TA should be assigned to a server class containing the Windows Universal Forwarders that should receive the upgrade package.

---

##################################

## Requirements

##################################

This TA requires:

* Windows operating system
* Splunk Universal Forwarder already installed
* PowerShell 5.1 or higher
* Administrative privileges for scheduled task creation
* Administrative privileges for service control
* Administrative privileges for MSI installation
* Access to run PowerShell scripts with `ExecutionPolicy Bypass`
* Splunk Universal Forwarder configured to forward logs to the indexing tier
* `splunk_upgrade` index created on the indexing tier
* `TA-windows_uf_upgrade_parsing` deployed to the parsing/indexing tier

The upgrade workflow assumes the default Splunk Universal Forwarder installation path:

```
C:\Program Files\SplunkUniversalForwarder\
```

If your environment uses a non-default path, update the script variables before deployment.

---

##################################

## File Structure

##################################

Expected app structure:

```
TA-windows_uf_upgrade_automation/
├── bin/
│   ├── splunk_upgrade_wrapper.bat
│   ├── splunk_windows_upgrade_task_setup.ps1
│   ├── splunk_windows_upgrade_exec.ps1
│   ├── splunk_upgrade_force_retry_wrapper.bat
│   ├── splunk_upgrade_force_retry.ps1
│   ├── splunk_upgrade_force_retry_reset_wrapper.bat
│   └── splunk_upgrade_force_retry_reset.ps1
├── default/
│   ├── app.conf
│   └── inputs.conf
├── metadata/
│   └── default.meta
├── README/
│   └── README.md
└── splunk_installer/
    └── splunkforwarder-<version>-x64-release.msi
```

The exact retry-control script names may vary by release. The important design is that retry and retry reset logic are included in this TA and disabled by default.

---

##################################

## MSI Installer Placement

##################################

Place the Splunk Universal Forwarder MSI in:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\splunk_installer\
```

The MSI filename must start with:

```
splunkforwarder
```

The filename must include a parseable version.

Example:

```
splunkforwarder-9.4.2-x64-release.msi
```

The setup script uses the MSI filename to extract the target version.

If no MSI is found, the setup script logs:

```
eventcode=9800
```

If the target version cannot be extracted from the MSI filename, the setup script logs:

```
eventcode=9815
```

Only stage one intended MSI installer in the `splunk_installer` directory for a given deployment wave.

---

##################################

## How It Works

##################################

The upgrade workflow runs in two major phases:

```
1. Setup phase
2. Execution phase
```

### Setup Phase

The setup phase is launched by the Splunk scripted input.

Workflow:

```
1. Splunk runs splunk_upgrade_wrapper.bat.
2. The wrapper launches the setup PowerShell script with ExecutionPolicy Bypass.
3. The setup script validates the MSI installer.
4. The setup script validates the Splunk binary path.
5. The setup script extracts the target version from the MSI filename.
6. The setup script calculates the installer hash.
7. The setup script checks the JSON state file.
8. The setup script checks for force_retry.flag.
9. The setup script validates the upgrade path.
10. The setup script writes setup state.
11. The setup script creates a Windows Scheduled Task.
12. The setup script starts the Windows Scheduled Task.
```

### Execution Phase

The execution phase runs from the Windows Scheduled Task as `SYSTEM`.

Workflow:

```
1. Scheduled task runs the execution PowerShell script.
2. Execution script validates state and installer details.
3. Execution script writes do_not_retry=true before running the MSI.
4. Execution script stops the Splunk Universal Forwarder service.
5. Execution script runs msiexec.
6. Execution script captures MSI result.
7. Execution script validates upgrade result.
8. Execution script attempts to remove the MSI installer.
9. Execution script writes final state.
10. Execution script starts the Splunk Universal Forwarder service.
11. Execution script removes the scheduled task when appropriate.
```

---

##################################

## inputs.conf Guidance

##################################

The main upgrade scripted input should be enabled only when the app package and MSI are ready for deployment.

Recommended production input:

```
# Main upgrade wrapper | Runs every 30 days | enabled by default for targeted upgrade deployments
[script://.\bin\splunk_upgrade_wrapper.bat]
disabled = false
interval = 2592000
sourcetype = splunk_upgrade
index = splunk_upgrade
```

Recommended log monitors:

```
# Setup log | Prechecks, state checks, retry prevention, and scheduled task creation
[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_setup.log]
disabled = false
sourcetype = splunk_upgrade
index = splunk_upgrade

# Execution log | MSI execution, service control, cleanup, and final state
[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_exec.log]
disabled = false
sourcetype = splunk_upgrade
index = splunk_upgrade

# MSI logs | Wildcard required because each MSI log filename contains a timestamp
[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_msi_*.log]
disabled = false
sourcetype = splunk_upgrade_msi
index = splunk_upgrade
crcSalt = <SOURCE>
ignoreOlderThan = 30d

# Retry-control log | Force retry and retry reset events
[monitor://C:\ProgramData\SplunkUpgrade\splunk_upgrade_force_retry_helper.log]
disabled = false
sourcetype = splunk_upgrade
index = splunk_upgrade
```

Optional retry-control inputs should be disabled by default:

```
# Force retry control | Disabled by default | Enable only for selected failed endpoints
[script://.\bin\splunk_upgrade_force_retry_wrapper.bat]
disabled = true
interval = -1
sourcetype = splunk_upgrade
index = splunk_upgrade

# Retry reset control | Disabled by default | Enable only when preparing selected endpoints for another retry wave
[script://.\bin\splunk_upgrade_force_retry_reset_wrapper.bat]
disabled = true
interval = -1
sourcetype = splunk_upgrade
index = splunk_upgrade
```

Important:

```
Do not intentionally enable the force retry input and retry reset input at the same time during normal operations.
```

During testing, you may disable the main scripted input and run the wrapper manually.

---

##################################

## Log Files

##################################

The application writes upgrade logs to:

```
C:\ProgramData\SplunkUpgrade\
```

Primary log files:

| Log File                                | Purpose                                                                                                              |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `splunk_upgrade_setup.log`              | Setup, validation, retry prevention, state checks, force retry flag consumption, and scheduled task creation events. |
| `splunk_upgrade_exec.log`               | Main upgrade execution, Splunk service control, MSI execution, cleanup, and final state events.                      |
| `splunk_upgrade_msi_<timestamp>.log`    | Verbose MSI installer output for each upgrade attempt.                                                               |
| `splunk_upgrade_force_retry_helper.log` | Force retry and retry reset events.                                                                                  |

---

##################################

## Index and Sourcetypes

##################################

Default index:

```
splunk_upgrade
```

Primary operational sourcetype:

```
splunk_upgrade
```

MSI log sourcetype:

```
splunk_upgrade_msi
```

The `splunk_upgrade` index should be created by:

```
TA-windows_uf_upgrade_parsing
```

The endpoint TA should send all upgrade-related logs to:

```
index = splunk_upgrade
```

---

##################################

## State Management

##################################

The TA uses a persistent JSON state file to prevent uncontrolled retry loops.

State file:

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
* Last event code
* Last error
* MSI log file
* State source
* `do_not_retry`

The most important retry-prevention field is:

```
do_not_retry
```

If the same MSI hash has already been attempted and is marked:

```
do_not_retry=true
```

the setup script skips the upgrade and logs:

```
eventcode=9819
```

This prevents repeated upgrade loops when:

* The MSI remains in `splunk_installer`
* Installer cleanup fails
* Splunk restarts
* The scripted input runs again
* Deployment Server redeploys the same app package
* A failed attempt already reached a terminal state

---

##################################

## Controlled Retry Behavior

##################################

This TA includes retry-control logic for selected failed endpoints.

### Force Retry

The force retry control creates:

```
C:\ProgramData\SplunkUpgrade\state\force_retry.flag
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

The main setup script consumes:

```
C:\ProgramData\SplunkUpgrade\state\force_retry.flag
```

When `force_retry.flag` exists, the setup script will:

```
1. Detect force_retry.flag.
2. Remove force_retry.flag.
3. Log eventcode=9820.
4. Allow the same MSI hash to run one additional time.
```

The marker file prevents repeated flag creation if the force retry input remains enabled.

### Retry Reset

The retry reset control removes:

```
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

Use retry reset only when preparing an endpoint for another future retry wave.

The main upgrade workflow does not remove the marker. This is intentional.

If the main upgrade workflow removed the marker after consuming `force_retry.flag`, the force retry input could recreate the flag on its next run and cause repeated retry attempts.

---

##################################

## Controlled Retry Workflow

##################################

Use this workflow when an endpoint failed and needs another attempt with the same MSI.

### First Retry Attempt

```
1. Identify failed endpoints in the dashboard.
2. Review failure details and MSI logs.
3. Fix the underlying issue.
4. Enable the force retry input for selected failed endpoints.
5. Force retry logic creates force_retry.flag and force_retry_helper_created.marker.
6. Main upgrade setup script consumes force_retry.flag.
7. Main upgrade setup script logs eventcode=9820.
8. Main upgrade workflow retries the same MSI one time.
9. Disable the force retry input after the retry wave.
```

### Additional Retry Attempt

If the force retry input already ran once and the marker exists, the force retry logic logs:

```
eventcode=9831
```

and does not create another flag.

To prepare for another retry wave:

```
1. Fix the underlying issue.
2. Enable the retry reset input for affected endpoints.
3. Retry reset logic removes force_retry_helper_created.marker.
4. Retry reset logic logs eventcode=9833.
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

## Event Code Summary

##################################

Common event codes generated by this TA include:

| EventCode | Meaning                                                         |
| --------: | --------------------------------------------------------------- |
|    `9800` | MSI installer was not found.                                    |
|    `9801` | Splunk binary was not found.                                    |
|    `9802` | Failed to create the Windows Scheduled Task.                    |
|    `9803` | Windows Scheduled Task created successfully.                    |
|    `9804` | Failed to remove the Windows Scheduled Task.                    |
|    `9805` | Windows Scheduled Task started successfully.                    |
|    `9806` | Windows Scheduled Task failed to start.                         |
|    `9807` | Failed to remove the MSI installer.                             |
|    `9808` | Splunkd service started successfully.                           |
|    `9809` | Splunkd service failed to start.                                |
|    `9810` | Splunkd service stopped successfully.                           |
|    `9811` | Splunkd service failed to stop.                                 |
|    `9812` | Upgrade completed successfully.                                 |
|    `9813` | Upgrade failed.                                                 |
|    `9814` | Failed to parse current Splunk UF version.                      |
|    `9815` | Failed to extract target version from MSI filename.             |
|    `9816` | Target version is equal to or lower than current version.       |
|    `9817` | Target major version is too far ahead of current major version. |
|    `9818` | Version validation passed.                                      |
|    `9819` | Installer already attempted; skipped to prevent retry loop.     |
|    `9820` | Force retry flag detected and removed; retry allowed.           |
|    `9821` | State file written successfully.                                |
|    `9822` | State read/write/hash failure or force retry removal failure.   |
|    `9823` | Splunk installer removed successfully.                          |
|    `9830` | Force retry flag created successfully.                          |
|    `9831` | Force retry logic already ran; marker exists.                   |
|    `9832` | Force retry logic failed.                                       |
|    `9833` | Retry reset removed marker.                                     |
|    `9834` | Retry reset skipped because marker was not present.             |
|    `9835` | Retry reset failed.                                             |

---

##################################

## Expected Event Flows

##################################

### Missing MSI

```
9800
```

### Invalid MSI Filename

```
9815
```

### Same or Lower Version MSI

```
9816
```

### Major Version Too Far Apart

```
9817
```

### Successful Upgrade

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

### Failed Upgrade with Cleanup Success

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

### Retry Prevention

```
9819
```

### Force Retry Consumed

```
9820
9818
9821
9803
9805
```

---

##################################

## Installation Instructions

##################################

### 1. Confirm Parsing TA Is Deployed

Before deploying this endpoint TA at scale, confirm the parsing/indexing TA is deployed:

```
TA-windows_uf_upgrade_parsing
```

Confirm the index exists:

```
| eventcount summarize=false index=splunk_upgrade
```

---

### 2. Stage the MSI Installer

Place the Splunk Universal Forwarder MSI in:

```
TA-windows_uf_upgrade_automation\splunk_installer\
```

Example:

```
TA-windows_uf_upgrade_automation/
└── splunk_installer/
    └── splunkforwarder-9.4.2-x64-release.msi
```

---

### 3. Review inputs.conf

Confirm the scripted input and log monitors are configured for your environment.

Check:

* `disabled`
* `interval`
* `index`
* `sourcetype`
* MSI wildcard monitor
* Retry-control log monitor
* Force retry input is disabled by default
* Retry reset input is disabled by default

---

### 4. Deploy to a Test Server Class

Deploy this TA to a small Windows Universal Forwarder test group first.

Recommended deployment method:

```
Splunk Deployment Server
```

Validate:

* App arrives on endpoint
* MSI arrives in `splunk_installer`
* Scripted input runs
* Logs are created
* Logs are indexed
* Dashboards populate
* State file is created
* Scheduled task behavior is correct

---

### 5. Expand Deployment

After successful validation, expand the server class to the intended Windows Universal Forwarder population.

Monitor rollout using:

```
Windows UF Upgrade Overview
Windows UF Upgrade Troubleshooting
```

---

##################################

## Manual Test Execution

##################################

For controlled testing, disable the scripted input and manually run the wrapper.

Run PowerShell as Administrator:

```
cd "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\bin"
.\splunk_upgrade_wrapper.bat
```

Run the force retry wrapper manually, if included:

```
cd "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\bin"
.\splunk_upgrade_force_retry_wrapper.bat
```

Run the retry reset wrapper manually, if included:

```
cd "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\bin"
.\splunk_upgrade_force_retry_reset_wrapper.bat
```

Check the setup log:

```
Get-Content "C:\ProgramData\SplunkUpgrade\splunk_upgrade_setup.log" -Tail 50
```

Check the exec log:

```
Get-Content "C:\ProgramData\SplunkUpgrade\splunk_upgrade_exec.log" -Tail 50
```

Check the retry-control log:

```
Get-Content "C:\ProgramData\SplunkUpgrade\splunk_upgrade_force_retry_helper.log" -Tail 50
```

Check state:

```
Get-Content "C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json"
```

Check retry files:

```
Test-Path "C:\ProgramData\SplunkUpgrade\state\force_retry.flag"
Test-Path "C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker"
```

---

##################################

## Validation Searches

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

### MSI Logs

```
index=splunk_upgrade sourcetype=splunk_upgrade_msi earliest=-24h
| table _time host source _raw
| sort -_time
```

---

##################################

## Troubleshooting

##################################

### MSI Not Found

Expected event:

```
9800
```

Check:

* MSI exists in `splunk_installer`
* MSI filename starts with `splunkforwarder`
* Deployment Server delivered the MSI to the endpoint

---

### Invalid MSI Filename

Expected event:

```
9815
```

Check:

* MSI filename contains a parseable version
* Filename follows expected Splunk UF naming format

Example:

```
splunkforwarder-9.4.2-x64-release.msi
```

---

### Same Installer Skipped

Expected event:

```
9819
```

Meaning:

```
The same installer hash was already attempted and is marked do_not_retry=true.
```

Resolution:

```
Fix the underlying issue, then use the controlled retry workflow to allow one additional retry.
```

---

### Force Retry Flag Consumed

Expected event:

```
9820
```

Meaning:

```
The setup script found and removed force_retry.flag and allowed one retry.
```

---

### Force Retry Input Did Not Create a New Flag

Expected event:

```
9831
```

Meaning:

```
force_retry_helper_created.marker already exists.
```

Resolution:

```
If another retry wave is needed, enable the retry reset input first.
After the marker is removed, enable the force retry input again.
```

---

### Retry Reset Says Marker Was Not Present

Expected event:

```
9834
```

Meaning:

```
force_retry_helper_created.marker did not exist.
```

This is not necessarily a failure. If another retry flag is needed, the endpoint may already be ready for the force retry input.

---

### State Tracking Error

Expected event:

```
9822
```

Check:

* State directory exists
* State file is not locked
* State file is valid JSON
* File permissions allow read/write/delete
* Installer hash can be calculated
* Force retry flag can be removed if present

State path:

```
C:\ProgramData\SplunkUpgrade\state\
```

---

### Scheduled Task Did Not Start

Expected event:

```
9806
```

Check:

* Scheduled task action path
* PowerShell execution policy
* Script path
* Permissions
* Windows Task Scheduler logs
* `splunk_upgrade_setup.log`

---

### Splunk Service Did Not Stop

Expected event:

```
9811
```

Check:

* Splunk service state
* Permissions
* Service name
* Service control output
* `splunk_upgrade_exec.log`

---

### Splunk Service Did Not Start

Expected event:

```
9809
```

Check:

* Splunk service state
* Splunk logs
* MSI upgrade result
* Service control output
* `splunk_upgrade_exec.log`

---

### Upgrade Failed

Expected event:

```
9813
```

Check:

* `splunk_upgrade_exec.log`
* `splunk_upgrade_msi_<timestamp>.log`
* MSI return code
* Windows Installer errors
* Current UF version
* Target UF version

---

### Installer Cleanup Failed

Expected event:

```
9807
```

Check:

* MSI file lock
* Permissions
* Antivirus or EDR lock
* Installer still in use
* File path
* `splunk_upgrade_exec.log`

Important:

```
A cleanup failure should not cause repeated retries if state was written successfully.
```

---

##################################

## Best Practices

##################################

* Test the TA in a non-production environment first.
* Deploy to a small test server class before broad rollout.
* Validate the MSI package before deployment.
* Confirm the MSI filename is parseable.
* Confirm the `splunk_upgrade` index exists before endpoint deployment.
* Confirm the parsing TA is deployed before logs are forwarded.
* Keep log monitoring enabled.
* Keep retry-control inputs disabled unless intentionally needed.
* Use dashboards to identify failed endpoints.
* Use `Hosts Not on Target Version` as the primary remediation view.
* Do not delete state files in production unless intentionally resetting retry protection.
* Use controlled retry inputs instead of manual state deletion when retrying endpoints at scale.
* Do not intentionally enable the force retry input and retry reset input at the same time.
* Disable retry-control inputs after the intended retry or reset action is complete.
* Keep `local/` changes limited to testing or environment-specific overrides.

---

##################################

## Related Documentation

##################################

See also:

```
SA-windows_uf_upgrade_monitoring/docs/quick-start-installation.md
SA-windows_uf_upgrade_monitoring/docs/eventcodes.md
SA-windows_uf_upgrade_monitoring/docs/state-management.md
SA-windows_uf_upgrade_monitoring/docs/testing-guide.md
SA-windows_uf_upgrade_monitoring/README/README.md
TA-windows_uf_upgrade_parsing/README/README.md
```

---

##################################

## Splunk Cloud and Platform Notes

##################################

This TA includes endpoint-side Windows components intended for Windows Universal Forwarders.

Do not deploy `TA-windows_uf_upgrade_automation` to Splunk Cloud search or indexing tiers.

The parsing app `TA-windows_uf_upgrade_parsing` should be deployed only where parsing and index configuration are supported by your Splunk deployment model.

The Search Head app `SA-windows_uf_upgrade_monitoring` provides dashboards and reporting content. Validate Splunk Cloud compatibility requirements before installing any app in a Splunk Cloud environment.

---

##################################

## Change History

##################################

### Version 1.0.0

* Added Windows Universal Forwarder endpoint upgrade workflow.
* Added setup and execution script documentation.
* Added scheduled task workflow documentation.
* Added setup, execution, MSI, and retry-control log guidance.
* Added JSON state management and retry-loop prevention guidance.
* Added force retry and retry reset behavior.
* Added retry-control event codes `9830-9835`.
* Added validation and troubleshooting searches.
* Documented the three-app solution structure.

