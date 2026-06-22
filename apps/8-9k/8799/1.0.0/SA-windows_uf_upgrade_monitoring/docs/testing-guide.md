###################################################

# Splunk Windows Universal Forwarder Upgrade App Testing Guide

###################################################

## Overview

This guide provides a methodical test plan for validating the Splunk Windows Universal Forwarder Upgrade App on a Windows test host.

The goal is to validate:

* App deployment
* Script execution
* Log generation
* Log ingestion
* Scheduled Task creation and execution
* Splunk service stop/start behavior
* MSI upgrade success and failure handling
* JSON state management
* Retry-loop prevention
* Force retry behavior
* Retry reset behavior
* Event code generation
* Dashboard-ready test data

This guide assumes the app is deployed to a Windows Universal Forwarder and that testing is performed in a controlled environment.

The solution is organized into three Splunk apps:

| App                                             | Purpose                                                                                                                                                         |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SA-windows_uf_upgrade_monitoring`                     | Search Head app for dashboards, data model, navigation, and documentation.                                                                                      |
| `TA-windows_uf_upgrade_automation`         | Endpoint-side Windows Universal Forwarder upgrade automation app. Includes upgrade execution, log collection, state tracking, and optional retry-control logic. |
| `TA-windows_uf_upgrade_parsing` | Parsing and indexing support app for upgrade logs and MSI logs.                                                                                                 |

---

###################################################

## Should This File Be Kept?

###################################################

Yes. This testing guide should be kept.

The Windows UF Upgrade App is not a simple log collection TA. It performs operational actions on endpoints, including:

* Creating and starting a Windows Scheduled Task
* Running PowerShell scripts
* Stopping and starting the Splunk Universal Forwarder service
* Running an MSI installer
* Writing persistent JSON state
* Preventing retry loops
* Supporting controlled retry operations through disabled-by-default retry-control inputs

Because of this, a repeatable test guide is valuable for:

* Pre-release validation
* Customer acceptance testing
* Regression testing after script changes
* Dashboard and data model validation
* Splunkbase packaging validation
* Troubleshooting difficult event codes
* Proving retry-loop prevention works correctly
* Proving controlled retry behavior works correctly

---

###################################################

## Test Scope

###################################################

This guide covers the following event code groups:

| Group                    | Event Codes                            |
| ------------------------ | -------------------------------------- |
| Setup / Validation       | `9800`, `9801`                         |
| Scheduled Task           | `9802`, `9803`, `9804`, `9805`, `9806` |
| Cleanup                  | `9807`, `9823`                         |
| Splunk Service           | `9808`, `9809`, `9810`, `9811`         |
| Upgrade Result           | `9812`, `9813`                         |
| Version Validation       | `9814`, `9815`, `9816`, `9817`, `9818` |
| Retry Prevention / State | `9819`, `9820`, `9821`, `9822`         |
| Retry Control            | `9830`, `9831`, `9832`                 |
| Retry Reset              | `9833`, `9834`, `9835`                 |

Some event codes can be triggered through normal testing.

Some event codes require controlled fault injection.

---

###################################################

## Event Code Cheat Sheet

###################################################

| EventCode | Meaning                                                                                      |
| --------: | -------------------------------------------------------------------------------------------- |
|    `9800` | MSI installer was not found in the `splunk_installer` folder.                                |
|    `9801` | Splunk binary was not found at the expected path.                                            |
|    `9802` | Failed to create the Windows Scheduled Task.                                                 |
|    `9803` | Windows Scheduled Task was created successfully.                                             |
|    `9804` | Failed to remove the Windows Scheduled Task.                                                 |
|    `9805` | Windows Scheduled Task started successfully.                                                 |
|    `9806` | Windows Scheduled Task failed to start.                                                      |
|    `9807` | Failed to remove the Splunk installer MSI file.                                              |
|    `9808` | Splunkd / Splunk Forwarder service started successfully.                                     |
|    `9809` | Splunkd / Splunk Forwarder service failed to start.                                          |
|    `9810` | Splunkd / Splunk Forwarder service stopped successfully.                                     |
|    `9811` | Splunkd / Splunk Forwarder service failed to stop.                                           |
|    `9812` | Splunk Universal Forwarder upgrade completed successfully.                                   |
|    `9813` | Splunk Universal Forwarder upgrade failed.                                                   |
|    `9814` | Failed to parse the current Splunk version.                                                  |
|    `9815` | Failed to extract the target version from the MSI filename.                                  |
|    `9816` | Target version is equal to or lower than the current installed version. Upgrade was skipped. |
|    `9817` | Target major version is too far ahead of the current major version.                          |
|    `9818` | Version validation checks passed.                                                            |
|    `9819` | Installer was already attempted and skipped to prevent a retry loop.                         |
|    `9820` | Force retry flag was detected and removed. Retry was allowed.                                |
|    `9821` | Upgrade state file was written successfully.                                                 |
|    `9822` | State file read/write/hash operation failed, or force retry flag could not be removed.       |
|    `9823` | Splunk installer MSI file was removed successfully.                                          |
|    `9830` | Force retry flag was created successfully.                                                   |
|    `9831` | Force retry logic already ran; marker exists and no new flag was created.                    |
|    `9832` | Force retry logic failed to create `force_retry.flag`.                                       |
|    `9833` | Retry reset logic removed `force_retry_helper_created.marker` successfully.                  |
|    `9834` | Retry reset logic ran, but marker was not present.                                           |
|    `9835` | Retry reset logic failed to remove the marker.                                               |

---

###################################################

## Test Environment

###################################################

Recommended test environment:

| Item               | Recommended Value                               |
| ------------------ | ----------------------------------------------- |
| OS                 | Windows Server or Windows workstation test host |
| Splunk Component   | Splunk Universal Forwarder                      |
| Main Endpoint App  | `TA-windows_uf_upgrade_automation`         |
| Search Head App    | `SA-windows_uf_upgrade_monitoring`                     |
| Parsing App        | `TA-windows_uf_upgrade_parsing` |
| Index              | `splunk_upgrade`                                |
| Primary Sourcetype | `splunk_upgrade`                                |
| MSI Sourcetype     | `splunk_upgrade_msi`                            |
| Log Path           | `C:\ProgramData\SplunkUpgrade\`                 |
| State Path         | `C:\ProgramData\SplunkUpgrade\state\`           |

---

###################################################

## Required Paths

###################################################

The main endpoint app is expected to be installed under:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\
```

The installer folder is:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\splunk_installer\
```

The main script folder is:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\bin\
```

The log folder is:

```
C:\ProgramData\SplunkUpgrade\
```

The state folder is:

```
C:\ProgramData\SplunkUpgrade\state\
```

---

###################################################

## Important State and Retry-Control Files

###################################################

| File                                                                   | Purpose                                                                |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json`         | Tracks installer attempt state and prevents retry loops.               |
| `C:\ProgramData\SplunkUpgrade\state\force_retry.flag`                  | Allows the same MSI hash to run one additional time.                   |
| `C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker` | Prevents retry-control logic from creating repeated force retry flags. |
| `C:\ProgramData\SplunkUpgrade\splunk_upgrade_force_retry_helper.log`   | Captures force retry and retry reset events.                           |

---

###################################################

## Recommended Testing Approach

###################################################

For controlled validation, keep the main upgrade scripted input disabled and run the wrapper manually.

This prevents accidental repeated runs while testing failure conditions.

Recommended local testing input override:

```
[script://.\bin\splunk_upgrade_wrapper.bat]
disabled = true
interval = 300

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

Optional retry-control inputs should remain disabled unless intentionally testing retry behavior.

Example pattern:

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

The exact retry-control script names may vary by release.

Place local overrides here:

```
C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\local\inputs.conf
```

Restart the Universal Forwarder after input changes:

```
& "C:\Program Files\SplunkUniversalForwarder\bin\splunk.exe" restart
```

---

###################################################

## Manual Execution Commands

###################################################

Run PowerShell as Administrator.

Run the main upgrade wrapper:

```
cd "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\bin"
.\splunk_upgrade_wrapper.bat
```

Run the force retry wrapper manually, if included in the release:

```
cd "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\bin"
.\splunk_upgrade_force_retry_wrapper.bat
```

Run the retry reset wrapper manually, if included in the release:

```
cd "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\bin"
.\splunk_upgrade_force_retry_reset_wrapper.bat
```

Check the last exit code after running a wrapper:

```
$LASTEXITCODE
```

Expected successful wrapper exit code:

```
0
```

---

###################################################

## Single-Host Multi-Identity Testing

###################################################

If only one physical test host is available, the host can be cycled through multiple logical names to generate dashboard test data.

Example logical host names:

```
uf_01
uf_02
uf_03
```

Update host value in:

```
C:\Program Files\SplunkUniversalForwarder\etc\system\local\inputs.conf
```

Example:

```
[default]
host = uf_01
```

Update server name in:

```
C:\Program Files\SplunkUniversalForwarder\etc\system\local\server.conf
```

Example:

```
[general]
serverName = uf_01
```

Restart the Universal Forwarder:

```
& "C:\Program Files\SplunkUniversalForwarder\bin\splunk.exe" restart
```

Repeat the process for `uf_02` and `uf_03` as needed.

Important:

Using multiple logical host names on one physical host is useful for event-code and dashboard testing, but it does not represent three real endpoint states.

---

###################################################

## Reset Commands for Testing

###################################################

Use these commands between test cases when needed.

Remove local upgrade logs:

```
Remove-Item "C:\ProgramData\SplunkUpgrade\*.log" -Force -ErrorAction SilentlyContinue
```

Remove local state files:

```
Remove-Item "C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\SplunkUpgrade\state\force_retry.flag" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker" -Force -ErrorAction SilentlyContinue
```

Remove staged MSI installers:

```
Remove-Item "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\splunk_installer\*.msi" -Force -ErrorAction SilentlyContinue
```

Remove leftover scheduled task:

```
Get-ScheduledTask -TaskName "z_splunk_upgrader_task_v01" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
```

Full local test reset:

```
Remove-Item "C:\ProgramData\SplunkUpgrade\*.log" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\SplunkUpgrade\state\force_retry.flag" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Program Files\SplunkUniversalForwarder\etc\apps\TA-windows_uf_upgrade_automation\splunk_installer\*.msi" -Force -ErrorAction SilentlyContinue
Get-ScheduledTask -TaskName "z_splunk_upgrader_task_v01" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
```

---

###################################################

## Splunk Validation Searches

###################################################

### View Recent Upgrade Events

```
index=splunk_upgrade sourcetype=splunk_upgrade earliest=-30m
| table _time host sourcetype eventcode status message details
| sort _time
```

### Event Code Coverage

```
index=splunk_upgrade sourcetype=splunk_upgrade earliest=-24h
| stats count values(host) AS hosts values(status) AS statuses values(message) AS messages by eventcode
| sort eventcode
```

### Missing Expected Event Codes

```
| makeresults
| eval expected_codes="9800,9801,9802,9803,9804,9805,9806,9807,9808,9809,9810,9811,9812,9813,9814,9815,9816,9817,9818,9819,9820,9821,9822,9823,9830,9831,9832,9833,9834,9835"
| makemv delim="," expected_codes
| mvexpand expected_codes
| rename expected_codes AS eventcode
| join type=left eventcode [
    search index=splunk_upgrade sourcetype=splunk_upgrade earliest=-24h
    | stats count by eventcode
]
| fillnull value=0 count
| eval status=if(count>0,"Observed","Missing")
| table eventcode status count
| sort eventcode
```

### Retry Control Events

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9820,9830,9831,9832,9833,9834,9835)
| table _time host eventcode status message details force_retry_file marker_file
| sort -_time
```

### Hosts Blocked by Retry Prevention

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9819
| stats latest(_time) AS last_seen latest(status) AS status latest(message) AS message latest(details) AS details latest(installer_name) AS installer_name latest(target_version) AS target_version latest(cleanup_status) AS cleanup_status by host
| eval last_seen=strftime(last_seen, "%Y-%m-%d %H:%M:%S")
| table last_seen host status message installer_name target_version cleanup_status details
| sort host
```

### Upgrade Results

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9812,9813)
| table _time host eventcode status message previous_version current_version target_version msi_log_file details
| sort -_time
```

### State Tracking Errors

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9822
| table _time host eventcode status message details installer_name installer_hash force_retry_file
| sort -_time
```

---

###################################################

## Test Case Matrix

###################################################

| Test ID | EventCode | Meaning                              | Test Method                                                                   | Type            |
| ------- | --------: | ------------------------------------ | ----------------------------------------------------------------------------- | --------------- |
| TC-001  |    `9800` | MSI not found                        | Remove MSI and run wrapper                                                    | Normal          |
| TC-002  |    `9815` | Target version not found in filename | Use `splunkforwarder-badname.msi`                                             | Normal          |
| TC-003  |    `9816` | Target version equal/lower           | Use same/lower version MSI                                                    | Normal          |
| TC-004  |    `9817` | Major version too far apart          | Use target major greater than current major + 1                               | Conditional     |
| TC-005  |    `9818` | Version validation passed            | Use valid higher-version MSI                                                  | Normal          |
| TC-006  |    `9803` | Scheduled task created               | Valid higher-version MSI                                                      | Normal          |
| TC-007  |    `9805` | Scheduled task started               | Valid higher-version MSI                                                      | Normal          |
| TC-008  |    `9813` | Upgrade failed                       | Use corrupt/fake MSI with valid filename                                      | Normal          |
| TC-009  |    `9810` | Splunkd stopped                      | Run upgrade path                                                              | Normal          |
| TC-010  |    `9808` | Splunkd started                      | Run upgrade path                                                              | Normal          |
| TC-011  |    `9812` | Upgrade succeeded                    | Use valid higher-version MSI                                                  | Normal          |
| TC-012  |    `9823` | Installer removed                    | Run upgrade or failed upgrade cleanup                                         | Normal          |
| TC-013  |    `9819` | Retry prevented                      | Re-run same MSI after terminal state                                          | Normal          |
| TC-014  |    `9820` | Force retry detected                 | Create or enable retry-control logic to create `force_retry.flag`, then rerun | Normal          |
| TC-015  |    `9821` | State file written                   | Any state update                                                              | Normal          |
| TC-016  |    `9807` | Installer cleanup failed             | Lock MSI or deny delete permission                                            | Fault Injection |
| TC-017  |    `9802` | Scheduled task creation failed       | Run setup as non-admin or break task creation permissions                     | Fault Injection |
| TC-018  |    `9801` | Splunk binary not found              | Temporarily point Splunk binary variable to fake path                         | Fault Injection |
| TC-019  |    `9814` | Current version parse failed         | Force invalid version output                                                  | Fault Injection |
| TC-020  |    `9806` | Scheduled task failed to start       | Break scheduled task action                                                   | Fault Injection |
| TC-021  |    `9804` | Scheduled task removal failed        | Force task removal failure                                                    | Fault Injection |
| TC-022  |    `9811` | Splunkd stop failed                  | Force stop check failure                                                      | Fault Injection |
| TC-023  |    `9809` | Splunkd start failed                 | Force start check failure                                                     | Fault Injection |
| TC-024  |    `9822` | State operation failed               | Break state write/read/hash or force retry removal                            | Fault Injection |
| TC-025  |    `9830` | Retry-control logic created flag     | Run force retry input with no marker present                                  | Normal          |
| TC-026  |    `9831` | Retry-control logic skipped          | Run force retry input after marker already exists                             | Normal          |
| TC-027  |    `9832` | Retry-control logic failed           | Break state path or permissions                                               | Fault Injection |
| TC-028  |    `9833` | Retry reset removed marker           | Run retry reset input when marker exists                                      | Normal          |
| TC-029  |    `9834` | Retry reset skipped                  | Run retry reset input when marker does not exist                              | Normal          |
| TC-030  |    `9835` | Retry reset failed                   | Break marker path or permissions                                              | Fault Injection |

---

###################################################

## Detailed Test Cases

###################################################

### TC-001 - Missing MSI Installer

Purpose:

Validate event code `9800`.

Steps:

```
1. Remove all MSI files from the splunk_installer directory.
2. Run splunk_upgrade_wrapper.bat.
3. Search for eventcode=9800.
```

Expected result:

```
Event code 9800 is logged.
Upgrade does not proceed.
Scheduled task is not created.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9800
| table _time host eventcode status message details
```

---

### TC-002 - Invalid MSI Filename

Purpose:

Validate event code `9815`.

Steps:

```
1. Place an MSI with an invalid filename in the splunk_installer directory.
2. Example: splunkforwarder-badname.msi
3. Run splunk_upgrade_wrapper.bat.
4. Search for eventcode=9815.
```

Expected result:

```
Event code 9815 is logged.
Upgrade does not proceed.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9815
| table _time host eventcode status message details installer_name
```

---

### TC-003 - Same or Lower Target Version

Purpose:

Validate event code `9816`.

Steps:

```
1. Place an MSI with the same or lower version than the currently installed UF.
2. Run splunk_upgrade_wrapper.bat.
3. Search for eventcode=9816.
```

Expected result:

```
Event code 9816 is logged.
Upgrade is skipped.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9816
| table _time host eventcode status message details target_version current_version
```

---

### TC-004 - Major Version Difference Too Large

Purpose:

Validate event code `9817`.

Steps:

```
1. Place an MSI with a target major version outside the supported upgrade path.
2. Run splunk_upgrade_wrapper.bat.
3. Search for eventcode=9817.
```

Expected result:

```
Event code 9817 is logged.
Upgrade does not proceed.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9817
| table _time host eventcode status message details target_version current_version
```

---

### TC-005 - Version Validation Passed

Purpose:

Validate event code `9818`.

Steps:

```
1. Place a valid higher-version Splunk Universal Forwarder MSI in the splunk_installer directory.
2. Run splunk_upgrade_wrapper.bat.
3. Search for eventcode=9818.
```

Expected result:

```
Event code 9818 is logged.
Upgrade workflow proceeds.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9818
| table _time host eventcode status message details target_version current_version
```

---

### TC-006 - Scheduled Task Created

Purpose:

Validate event code `9803`.

Steps:

```
1. Use a valid higher-version MSI.
2. Run splunk_upgrade_wrapper.bat.
3. Search for eventcode=9803.
4. Confirm scheduled task exists or existed.
```

Expected result:

```
Event code 9803 is logged.
Scheduled task is created.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9803
| table _time host eventcode status message details taskname
```

---

### TC-007 - Scheduled Task Started

Purpose:

Validate event code `9805`.

Steps:

```
1. Use a valid higher-version MSI.
2. Run splunk_upgrade_wrapper.bat.
3. Search for eventcode=9805.
```

Expected result:

```
Event code 9805 is logged.
Scheduled task starts.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9805
| table _time host eventcode status message details taskname
```

---

### TC-008 - Upgrade Failed

Purpose:

Validate event code `9813`.

Steps:

```
1. Use a corrupt or invalid MSI with a valid-looking filename.
2. Run splunk_upgrade_wrapper.bat.
3. Allow scheduled task to run.
4. Search for eventcode=9813.
```

Expected result:

```
Event code 9813 is logged.
MSI log path is recorded when available.
State file is updated with a terminal failure state.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9813
| table _time host eventcode status message details msi_log_file
```

---

### TC-009 - Splunkd Stopped

Purpose:

Validate event code `9810`.

Steps:

```
1. Run an upgrade path that reaches execution.
2. Confirm the execution script attempts to stop Splunk.
3. Search for eventcode=9810.
```

Expected result:

```
Event code 9810 is logged when Splunkd is stopped successfully.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9810
| table _time host eventcode status message details splunkd_status
```

---

### TC-010 - Splunkd Started

Purpose:

Validate event code `9808`.

Steps:

```
1. Run an upgrade path that reaches execution.
2. Confirm the execution script attempts to start Splunk after the MSI attempt.
3. Search for eventcode=9808.
```

Expected result:

```
Event code 9808 is logged when Splunkd starts successfully.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9808
| table _time host eventcode status message details splunkd_status
```

---

### TC-011 - Upgrade Succeeded

Purpose:

Validate event code `9812`.

Steps:

```
1. Use a valid higher-version Splunk Universal Forwarder MSI.
2. Run splunk_upgrade_wrapper.bat.
3. Allow the scheduled task and MSI upgrade to complete.
4. Confirm Universal Forwarder restarts.
5. Search for eventcode=9812.
```

Expected result:

```
Event code 9812 is logged.
Current version reflects the target version.
State file is updated with `last_status=success`.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9812
| table _time host eventcode status message previous_version current_version target_version details
```

---

### TC-012 - Installer Cleanup Success

Purpose:

Validate event code `9823`.

Steps:

```
1. Run an upgrade or failed upgrade path that reaches cleanup.
2. Confirm the MSI is removed from the splunk_installer directory.
3. Search for eventcode=9823.
```

Expected result:

```
Event code 9823 is logged.
Staged MSI file is removed.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9823
| table _time host eventcode status message details installer_name
```

---

### TC-013 - Retry Prevention

Purpose:

Validate event code `9819`.

Steps:

```
1. Run an upgrade attempt that reaches a terminal state.
2. Ensure the same MSI remains or is placed back into the splunk_installer directory.
3. Run splunk_upgrade_wrapper.bat again.
4. Search for eventcode=9819.
```

Expected result:

```
Event code 9819 is logged.
Same installer hash is skipped.
Scheduled task is not created for the repeated attempt.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9819
| table _time host eventcode status message installer_name target_version cleanup_status do_not_retry details
```

---

### TC-014 - Force Retry Consumed

Purpose:

Validate event code `9820`.

Steps:

```
1. Create or enable retry-control logic to create `force_retry.flag`.
2. Confirm `force_retry.flag` exists.
3. Run splunk_upgrade_wrapper.bat.
4. Search for eventcode=9820.
```

Expected result:

```
Event code 9820 is logged.
Main setup script removes `force_retry.flag`.
Same MSI is allowed to run one additional time.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9820
| table _time host eventcode status message details force_retry_file
```

---

### TC-015 - State File Written

Purpose:

Validate event code `9821`.

Steps:

```
1. Run any workflow that writes or updates the state file.
2. Confirm the state file exists.
3. Search for eventcode=9821.
```

Expected result:

```
Event code 9821 is logged.
State file exists under `C:\ProgramData\SplunkUpgrade\state\`.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9821
| table _time host eventcode status message installer_name target_version attempt_count last_status cleanup_status do_not_retry
```

---

### TC-025 - Force Retry Flag Created

Purpose:

Validate event code `9830`.

Steps:

```
1. Ensure `force_retry_helper_created.marker` does not exist.
2. Enable or manually run the force retry control.
3. Search for eventcode=9830.
```

Expected result:

```
Event code 9830 is logged.
`force_retry.flag` is created.
`force_retry_helper_created.marker` is created.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9830
| table _time host eventcode status message details force_retry_file marker_file
```

---

### TC-026 - Force Retry Skipped Because Marker Exists

Purpose:

Validate event code `9831`.

Steps:

```
1. Ensure `force_retry_helper_created.marker` exists.
2. Enable or manually run the force retry control.
3. Search for eventcode=9831.
```

Expected result:

```
Event code 9831 is logged.
No new `force_retry.flag` is created.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9831
| table _time host eventcode status message details marker_file
```

---

### TC-028 - Retry Reset Removed Marker

Purpose:

Validate event code `9833`.

Steps:

```
1. Ensure `force_retry_helper_created.marker` exists.
2. Enable or manually run the retry reset control.
3. Search for eventcode=9833.
```

Expected result:

```
Event code 9833 is logged.
`force_retry_helper_created.marker` is removed.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9833
| table _time host eventcode status message details marker_file
```

---

### TC-029 - Retry Reset Skipped Because Marker Missing

Purpose:

Validate event code `9834`.

Steps:

```
1. Ensure `force_retry_helper_created.marker` does not exist.
2. Enable or manually run the retry reset control.
3. Search for eventcode=9834.
```

Expected result:

```
Event code 9834 is logged.
No reset action is needed.
```

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode=9834
| table _time host eventcode status message details marker_file
```

---

###################################################

## Fault Injection Notes

###################################################

Some event codes require intentionally breaking a condition. Perform fault injection only in a controlled test environment.

Examples:

| EventCode | Fault Injection Idea                                                                     |
| --------: | ---------------------------------------------------------------------------------------- |
|    `9801` | Temporarily point the script to an invalid Splunk binary path.                           |
|    `9802` | Run setup without required privileges or break scheduled task creation.                  |
|    `9804` | Force scheduled task removal failure.                                                    |
|    `9806` | Break the scheduled task action or path.                                                 |
|    `9807` | Lock the MSI file or deny delete permissions.                                            |
|    `9809` | Prevent the Splunk service from starting.                                                |
|    `9811` | Prevent the Splunk service from stopping.                                                |
|    `9814` | Force invalid current version output.                                                    |
|    `9822` | Break state file permissions, corrupt state JSON, or prevent `force_retry.flag` removal. |
|    `9832` | Prevent force retry control from writing to the state directory.                         |
|    `9835` | Prevent retry reset control from removing the marker.                                    |

Important:

```
Restore normal permissions and script logic after fault injection testing.
Do not run fault injection tests on production endpoints.
```

---

###################################################

## Dashboard Validation

###################################################

After generating test data, validate the Search Head dashboards in:

```
SA-windows_uf_upgrade_monitoring
```

Expected dashboards:

```
Windows UF Upgrade Overview
Windows UF Upgrade Troubleshooting
```

The Overview dashboard should show:

* Total targeted hosts
* Hosts with recent upgrade activity
* Successful upgrades
* Failed upgrades
* Hosts not on the target version
* Retry prevention events
* Retry-control events
* State tracking errors
* Cleanup errors

The Troubleshooting dashboard should show:

* Setup and validation events
* Scheduled task events
* Splunk service stop/start events
* Version validation events
* Upgrade result events
* Cleanup events
* State and retry prevention events
* Retry-control and retry-reset events
* Raw event detail by host

---

###################################################

## Data Model Validation

###################################################

If the app uses a data model, validate that expected fields are available.

Recommended fields:

```
eventcode
status
message
details
installer_name
installer_hash
target_version
previous_version
current_version
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

Example validation search:

```
| datamodel splunk_upgrade search
| table _time host eventcode status message details
| head 20
```

If using accelerated data models, do not enable acceleration until the fields and constraints are validated.

---

###################################################

## Pass / Fail Criteria

###################################################

The app passes basic validation when:

* `TA-windows_uf_upgrade_automation` deploys successfully to the Windows test UF.
* Logs are written under `C:\ProgramData\SplunkUpgrade\`.
* Logs are indexed into `splunk_upgrade`.
* Primary events use sourcetype `splunk_upgrade`.
* MSI logs use sourcetype `splunk_upgrade_msi`.
* Key-value fields are extracted.
* Version validation events are generated correctly.
* Scheduled task events are generated correctly.
* Upgrade success or failure events are generated correctly.
* State file is written correctly.
* Retry-loop prevention logs event `9819` when expected.
* Force retry consumption logs event `9820` when expected.
* Retry-control logic logs `9830`, `9831`, or `9832` when expected.
* Retry-reset logic logs `9833`, `9834`, or `9835` when expected.
* Dashboards show expected data.
* No unintended repeated upgrade loop occurs.

The app fails validation when:

* Logs are not created.
* Logs are not indexed.
* Required fields are missing.
* Main workflow runs repeatedly against the same failed MSI without administrator action.
* State file cannot be written during normal operation.
* Splunk service is left stopped after a failed upgrade attempt.
* Dashboards cannot find expected index, sourcetype, or data model fields.
* Retry-control inputs create repeated retries without marker protection.

---

###################################################

## Recommended Release Validation Sequence

###################################################

Before submitting or publishing a release:

```
1. Validate app package structure.
2. Validate app.conf package id and version.
3. Validate metadata/default.meta permissions.
4. Validate no local directory is included unless intentionally required.
5. Validate no endpoint-specific state files are packaged.
6. Validate no MSI is accidentally packaged unless the release intentionally includes one.
7. Validate TA-windows_uf_upgrade_parsing includes required index and parsing configuration.
8. Validate SA-windows_uf_upgrade_monitoring dashboards load.
9. Validate TA-windows_uf_upgrade_automation deploys to a test Windows UF.
10. Run TC-001 through TC-015.
11. Run retry-control test cases TC-025, TC-026, TC-028, and TC-029.
12. Run selected fault injection tests as needed.
13. Validate dashboards and data model fields.
14. Run AppInspect.
15. Correct warnings or document expected platform limitations.
```

---

###################################################

## Splunk Cloud and Platform Notes

###################################################

This solution includes endpoint-side Windows components intended for Windows Universal Forwarders.

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
docs/quick-start-installation.md
docs/state-management.md
README/README.md
```

