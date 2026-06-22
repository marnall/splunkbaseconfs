###################################################

# Splunk Windows Universal Forwarder Upgrade App State Management

###################################################

## Overview

The Splunk Windows Universal Forwarder Upgrade App uses a persistent JSON state file to track upgrade attempts and prevent retry loops.

This is required because the upgrade workflow can restart the Splunk Universal Forwarder service. If the MSI installer remains in the `splunk_installer` directory after an upgrade attempt, the scripted input may run again after Splunk restarts.

Without persistent state tracking, the same installer could be attempted repeatedly.

The state file provides a durable record of the current installer attempt and whether the same MSI should be retried.

The solution also supports controlled retry operations through optional retry-control logic included in the main endpoint TA:

```
TA-windows_uf_upgrade_automation
```

Retry-control logic is disabled by default and should only be enabled for selected endpoints when an administrator intentionally wants to allow another controlled retry attempt.

The solution is organized into three Splunk apps:

| App                                             | Purpose                                                                                                                                                         |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SA-windows_uf_upgrade_monitoring`              | Search Head app for dashboards, data model, navigation, and documentation.                                                                                      |
| `TA-windows_uf_upgrade_automation`              | Endpoint-side Windows Universal Forwarder upgrade automation app. Includes upgrade execution, log collection, state tracking, and optional retry-control logic. |
| `TA-windows_uf_upgrade_parsing`                  | Parsing and indexing support app for upgrade logs and MSI logs.                                                                                                 | 

---

###################################################

## State File Location

###################################################

The state file is written to:

```
C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json
```

The state directory is created automatically if it does not already exist:

```
C:\ProgramData\SplunkUpgrade\state\
```

The state file is local to each Windows Universal Forwarder endpoint.

It is not stored inside the Splunk app directory and should not be packaged with the app.

---

###################################################

## State Management Purpose

###################################################

State management prevents retry loops caused by scenarios such as:

* MSI installer cleanup failure
* Splunk Universal Forwarder restart
* Scripted input running again after restart
* Same MSI remaining in the `splunk_installer` directory
* Scheduled task being recreated for the same installer
* In-memory retry counters resetting after script exit
* Deployment Server redeploying the same app package
* Failed upgrade attempts leaving local artifacts behind

The state file solves this by persisting the installer attempt status to disk.

The key state field is:

```
do_not_retry=true
```

When the same installer hash is marked `do_not_retry=true`, the setup script skips the upgrade and logs event code `9819`.

---

###################################################

## Retry Loop Example

###################################################

Without state management, this loop can occur:

```
1. MSI exists in splunk_installer.
2. Script validates MSI.
3. Scheduled task starts upgrade.
4. Upgrade fails or cleanup fails.
5. MSI remains in splunk_installer.
6. Splunk restarts.
7. Scripted input runs again.
8. Same MSI is attempted again.
9. Loop repeats.
```

With state management, the setup script checks the state file before creating the scheduled task.

If the same MSI hash is marked `do_not_retry=true`, the setup script skips the upgrade and logs event code `9819`.

---

###################################################

## State File Fields

###################################################

The JSON state file stores information about the most recent installer attempt.

Example:

```
{
  "installer_name": "splunkforwarder-9.4.2-x64-release.msi",
  "installer_hash": "ABC123EXAMPLEHASH",
  "target_version": "9.4.2",
  "previous_version": "9.3.1",
  "current_version": "9.4.2",
  "attempt_count": 1,
  "last_status": "success",
  "cleanup_status": "cleanup_success",
  "do_not_retry": true,
  "last_eventcode": "9812",
  "last_error": "",
  "msi_log_file": "C:\\ProgramData\\SplunkUpgrade\\splunk_upgrade_msi_20260523_120000.log",
  "last_attempt_time": "2026-05-23 12:00:00",
  "state_source": "exec",
  "state_file_version": "1.0"
}
```

---

###################################################

## Field Definitions

###################################################

| Field                | Description                                                                      |
| -------------------- | -------------------------------------------------------------------------------- |
| `installer_name`     | Name of the MSI installer found in the `splunk_installer` directory.             |
| `installer_hash`     | SHA256 hash of the MSI installer. Used to identify the exact installer file.     |
| `target_version`     | Target Splunk Universal Forwarder version extracted from the MSI filename.       |
| `previous_version`   | Splunk Universal Forwarder version before the upgrade attempt.                   |
| `current_version`    | Splunk Universal Forwarder version after the upgrade attempt or validation step. |
| `attempt_count`      | Number of attempts recorded for the same installer hash.                         |
| `last_status`        | Most recent upgrade workflow state.                                              |
| `cleanup_status`     | Most recent installer cleanup state.                                             |
| `do_not_retry`       | Boolean flag that tells setup whether the same installer should be skipped.      |
| `last_eventcode`     | Most recent significant event code associated with the state update.             |
| `last_error`         | Last captured error message, if applicable.                                      |
| `msi_log_file`       | Path to the MSI verbose log generated for the attempt.                           |
| `last_attempt_time`  | Timestamp of the most recent state update.                                       |
| `state_source`       | Script that last wrote the state file, such as `setup` or `exec`.                |
| `state_file_version` | Version of the state file schema.                                                |

---

###################################################

## State Status Values

###################################################

The `last_status` field tracks the upgrade lifecycle.

| Status            | Meaning                                                           |
| ----------------- | ----------------------------------------------------------------- |
| `setup_validated` | Setup validation passed and the scheduled task is being prepared. |
| `upgrade_started` | The execution script started processing the MSI.                  |
| `success`         | The MSI upgrade completed successfully.                           |
| `failed`          | The MSI upgrade failed.                                           |
| `unknown`         | The result could not be determined.                               |

Important note:

```
cleanup_failed is tracked in the cleanup_status field, not as the primary last_status value.
```

The app may have:

```
last_status=failed
cleanup_status=cleanup_failed
```

This means the upgrade failed and the installer cleanup also failed.

---

###################################################

## Cleanup Status Values

###################################################

The `cleanup_status` field tracks whether the MSI installer was removed.

| Status            | Meaning                                 |
| ----------------- | --------------------------------------- |
| `not_started`     | Cleanup has not started yet.            |
| `cleanup_success` | MSI installer was removed successfully. |
| `cleanup_failed`  | MSI installer could not be removed.     |

Cleanup failures are important because the MSI may remain in the `splunk_installer` directory.

If cleanup fails but state was written successfully, the app should still prevent automatic retry loops for the same installer hash.

---

###################################################

## Terminal States

###################################################

A terminal state means the app should not automatically retry the same MSI installer.

Terminal states should set:

```
do_not_retry=true
```

Examples of terminal states:

| Terminal State   | Reason                                                                       |
| ---------------- | ---------------------------------------------------------------------------- |
| `success`        | Upgrade completed successfully.                                              |
| `failed`         | Upgrade failed and should not repeatedly retry without administrator action. |
| `cleanup_failed` | MSI cleanup failed; retrying automatically could cause an endless loop.      |

The app intentionally treats failed upgrades as terminal by default.

This is safer than allowing repeated MSI execution against the same endpoint without administrator review.

---

###################################################

## Force Retry Flag

###################################################

The app supports a force retry flag.

To intentionally retry the same MSI installer, create this file:

```
C:\ProgramData\SplunkUpgrade\state\force_retry.flag
```

When the setup script detects this file, it will:

```
1. Remove the force_retry.flag file.
2. Log event code 9820.
3. Allow the same installer to run one additional time.
```

If the force retry flag cannot be removed, the setup script should exit instead of continuing.

This prevents the force retry flag from causing another retry loop.

The force retry flag is normally created by optional retry-control logic included in:

```
TA-windows_uf_upgrade_automation
```

Manual creation is supported for testing but is not the preferred production workflow at scale.

---

###################################################

## Force Retry Helper Marker

###################################################

The retry-control logic creates a marker file after it creates the force retry flag.

Marker file:

```
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

Purpose:

```
The marker prevents retry-control logic from creating force_retry.flag repeatedly if the retry-control input remains enabled.
```

The marker is created by the force retry control in:

```
TA-windows_uf_upgrade_automation
```

The marker is removed by the retry reset control in:

```
TA-windows_uf_upgrade_automation
```

The main upgrade workflow does not remove the marker.

This is intentional.

If the main upgrade workflow removed the marker after consuming `force_retry.flag`, the retry-control input could recreate the flag on its next run and cause repeated retry attempts.

---

###################################################

## Retry Behavior

###################################################

The setup script uses the following logic before creating the scheduled task:

| Condition                                                                                                        | Behavior                               |
| ---------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| No state file exists                                                                                             | Continue with upgrade workflow.        |
| State file exists but MSI hash is different                                                                      | Treat as a new installer and continue. |
| State file exists and MSI hash matches with `do_not_retry=false`                                                 | Continue with upgrade workflow.        |
| State file exists and MSI hash matches with `do_not_retry=true`                                                  | Skip upgrade and log `9819`.           |
| `force_retry.flag` exists and can be removed                                                                     | Allow one retry and log `9820`.        |
| `force_retry.flag` exists but cannot be removed                                                                  | Exit and log `9822`.                   |
| MSI is locked and hash cannot be recalculated, but state matches installer name/version with `do_not_retry=true` | Skip upgrade and log `9819`.           |
| State file cannot be written before scheduling or running upgrade                                                | Exit and log `9822`.                   |

Important behavior:

```
The app should not create or start the scheduled task if the setup script cannot write the state file.
```

Important behavior in the execution script:

```
The execution script should not stop Splunk or run msiexec unless it can first write do_not_retry=true to the state file.
```

This protects the endpoint from uncontrolled retry behavior.

---

###################################################

## Controlled Retry Workflow

###################################################

Use this workflow when a failed endpoint needs another attempt with the same MSI installer.

### Normal Failure Flow

```
1. Upgrade attempt fails.
2. Execution script writes terminal state with do_not_retry=true.
3. MSI may or may not be removed depending on cleanup outcome.
4. Later setup run sees same installer hash.
5. Setup skips the upgrade and logs event code 9819.
```

### First Controlled Retry

```
1. Administrator reviews the failure.
2. Administrator fixes the underlying issue.
3. Administrator enables the force retry input in TA-windows_uf_upgrade_automation for selected failed endpoints.
4. Retry-control logic creates force_retry.flag.
5. Retry-control logic creates force_retry_helper_created.marker.
6. Main setup script detects and removes force_retry.flag.
7. Main setup script logs event code 9820.
8. Same MSI is allowed to run one additional time.
9. Administrator disables the force retry input after the intended retry wave.
```

Expected retry-control events:

| EventCode | Meaning                                                                   |
| --------: | ------------------------------------------------------------------------- |
|    `9830` | Force retry flag was created successfully.                                |
|    `9831` | Force retry logic already ran and marker exists; no new flag was created. |
|    `9832` | Force retry logic failed to create the flag.                              |
|    `9820` | Main setup script consumed `force_retry.flag` and allowed one retry.      |

### Additional Retry Wave

If the first controlled retry has already occurred and another retry is needed later, the marker must be removed first.

```
1. Administrator fixes the underlying issue.
2. Administrator enables the retry reset input in TA-windows_uf_upgrade_automation for selected endpoints.
3. Retry-reset logic removes force_retry_helper_created.marker.
4. Retry-reset logic logs event code 9833.
5. Administrator disables the retry reset input.
6. Administrator enables the force retry input again when another controlled retry is needed.
7. Retry-control logic creates a new force_retry.flag.
8. Main setup script consumes force_retry.flag and allows one additional retry.
9. Administrator disables the force retry input after the intended retry wave.
```

Expected retry reset events:

| EventCode | Meaning                                                   |
| --------: | --------------------------------------------------------- |
|    `9833` | Retry reset logic removed the helper marker successfully. |
|    `9834` | Retry reset logic ran, but the marker was not present.    |
|    `9835` | Retry reset logic failed to remove the marker.            |

Important operational rule:

```
Do not intentionally enable the force retry input and retry reset input at the same time during normal operations.
```

---

###################################################

## Retry-Control Inputs

###################################################

Retry-control inputs are included in:

```
TA-windows_uf_upgrade_automation
```

They should be disabled by default.

Example input pattern:

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

The exact script names may vary by release.

The intended behavior is:

| Input              | Default State                    | Purpose                                                                                    |
| ------------------ | -------------------------------- | ------------------------------------------------------------------------------------------ |
| Main upgrade input | Enabled or deployment-controlled | Runs the normal upgrade workflow.                                                          |
| Force retry input  | Disabled                         | Creates `force_retry.flag` and `force_retry_helper_created.marker` for selected endpoints. |
| Retry reset input  | Disabled                         | Removes `force_retry_helper_created.marker` so another future retry flag can be created.   |

Recommended Deployment Server approach:

```
1. Keep retry-control inputs disabled in default configuration.
2. Use local inputs.conf overrides or targeted server classes to enable force retry or retry reset for selected endpoints.
3. Disable the input after the intended control action is complete.
4. Do not enable both retry-control inputs at the same time.
```

---

###################################################

## State File Write Timing

###################################################

The state file should be written before risky or disruptive actions occur.

Recommended behavior:

| Workflow Stage          | State Behavior                                                                   |
| ----------------------- | -------------------------------------------------------------------------------- |
| Setup validation passed | Write or update state before creating scheduled task.                            |
| Scheduled task creation | Do not create task if required state cannot be written.                          |
| Execution start         | Write `upgrade_started` and `do_not_retry=true` before stopping Splunk.          |
| Upgrade success         | Update state with `last_status=success`, version details, and event code `9812`. |
| Upgrade failure         | Update state with `last_status=failed`, failure details, and event code `9813`.  |
| Cleanup success         | Update `cleanup_status=cleanup_success` and log event code `9823`.               |
| Cleanup failure         | Update `cleanup_status=cleanup_failed` and log event code `9807`.                |

This timing is important because the Universal Forwarder service may stop or restart during the upgrade workflow.

The state file must survive process restarts and service restarts.

---

###################################################

## Event Codes Related to State Management

###################################################

| EventCode | Severity | Meaning                                                                                    |
| --------: | -------- | ------------------------------------------------------------------------------------------ |
|    `9819` | INFO     | Same installer was already attempted and skipped because `do_not_retry=true`.              |
|    `9820` | INFO     | Force retry flag was detected and removed; same installer is allowed one additional retry. |
|    `9821` | INFO     | State file was written successfully.                                                       |
|    `9822` | ERROR    | State file read/write/hash operation failed, or force retry flag could not be removed.     |
|    `9830` | INFO     | Force retry flag was created successfully.                                                 |
|    `9831` | INFO     | Force retry logic already ran and marker exists; no new flag was created.                  |
|    `9832` | ERROR    | Force retry logic failed to create the flag.                                               |
|    `9833` | INFO     | Retry reset logic removed the helper marker successfully.                                  |
|    `9834` | INFO     | Retry reset logic ran, but the marker was not present.                                     |
|    `9835` | ERROR    | Retry reset logic failed to remove the marker.                                             |

---

###################################################

## Troubleshooting State Management

###################################################

### Same MSI is skipped

Expected event:

```
9819
```

Meaning:

```
The same installer hash was already attempted and is marked do_not_retry=true.
```

This is expected after a terminal state.

Recommended action:

```
Review previous failure or success events.
Confirm whether another retry is actually needed.
If another retry is needed, use the controlled retry workflow.
```

---

### Force retry was consumed

Expected event:

```
9820
```

Meaning:

```
The main setup script found force_retry.flag, removed it, and allowed the same MSI to run one additional time.
```

Recommended action:

```
Confirm the retry was intentional.
Review follow-on upgrade result events 9812 or 9813.
Disable the force retry input after the intended retry wave.
```

---

### State file operation failed

Expected event:

```
9822
```

Meaning:

```
The app could not read, write, hash, calculate, or remove required state information.
```

Common causes:

* Permission issue under `C:\ProgramData\SplunkUpgrade\state\`
* Locked state file
* Corrupt JSON state file
* MSI hash calculation failure
* `force_retry.flag` could not be removed

Recommended action:

```
Review the details field.
Check endpoint file permissions.
Confirm the state directory exists.
Confirm the Splunk Universal Forwarder service account can access the state path.
Remove or repair corrupt state only after reviewing endpoint upgrade history.
```

---

### Force retry input did not create a new flag

Expected event:

```
9831
```

Meaning:

```
The marker file already exists, so retry-control logic did not create a new force_retry.flag.
```

Marker file:

```
C:\ProgramData\SplunkUpgrade\state\force_retry_helper_created.marker
```

Recommended action:

```
If another retry wave is intended, enable the retry reset input first.
After reset succeeds, enable the force retry input again.
```

---

### Retry reset input says marker not present

Expected event:

```
9834
```

Meaning:

```
Retry-reset logic ran, but the marker file was not present.
```

Recommended action:

```
Confirm whether a reset was actually needed.
If a force retry is needed, enable the force retry input.
```

---

###################################################

## Validation Searches

###################################################

### State and Retry Events

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9819,9820,9821,9822,9830,9831,9832,9833,9834,9835)
| table _time host eventcode status message details installer_name target_version attempt_count last_status cleanup_status do_not_retry force_retry_file marker_file
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

### Force Retry Activity

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9820,9830,9831,9832)
| eval retry_action=case(
    eventcode="9820", "Force retry flag consumed by setup",
    eventcode="9830", "Force retry flag created",
    eventcode="9831", "Force retry skipped because marker exists",
    eventcode="9832", "Force retry flag creation failed",
    true(), "Unknown retry action"
)
| table _time host eventcode status retry_action message details force_retry_file marker_file
| sort -_time
```

### Retry Reset Activity

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9833,9834,9835)
| eval reset_action=case(
    eventcode="9833", "Retry marker removed",
    eventcode="9834", "Retry marker not present",
    eventcode="9835", "Retry marker reset failed",
    true(), "Unknown reset action"
)
| table _time host eventcode status reset_action message details marker_file
| sort -_time
```

### Upgrade Results with State Context

```
index=splunk_upgrade sourcetype=splunk_upgrade eventcode IN (9812,9813,9819,9820,9821,9822)
| table _time host eventcode status message installer_name target_version previous_version current_version attempt_count last_status cleanup_status do_not_retry details
| sort -_time
```

---

###################################################

## Operational Notes

###################################################

* The state file is endpoint-local and should not be packaged with the app.
* The state file should be written before the app performs disruptive actions such as stopping Splunk or running `msiexec`.
* The app intentionally treats failed upgrades as terminal unless an administrator performs a controlled retry.
* Event code `9819` confirms retry-loop prevention is working.
* Event code `9820` confirms the main setup script consumed `force_retry.flag`.
* Event code `9830` confirms retry-control logic created a new retry flag.
* Event code `9831` means retry-control logic did not create a new flag because the marker already exists.
* Event code `9833` confirms retry-reset logic removed the marker.
* The main upgrade workflow should not remove `force_retry_helper_created.marker`.
* The force retry input and retry reset input should not be intentionally enabled at the same time.
* Use Deployment Server targeting or local input overrides to enable retry controls only for selected endpoints.
* Disable retry-control inputs after the intended action is complete.
* If the app package has not changed but must be redeployed through Deployment Server, update or add a harmless marker file such as `force_redeploy.txt`.

---

###################################################

## Related Documentation

###################################################

See also:

```
docs/eventcodes.md
docs/quick-start-installation.md
docs/testing-guide.md
README/README.md
```

