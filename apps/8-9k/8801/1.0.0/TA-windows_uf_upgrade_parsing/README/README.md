##################################

# TA-windows_uf_upgrade_parsing

##################################

## Overview

`TA-windows_uf_upgrade_parsing` provides the parsing-tier and indexing configuration required by the Splunk Windows Universal Forwarder Upgrade App solution.

This TA supports the upgrade solution by defining the `splunk_upgrade` index and parsing behavior for operational upgrade logs and MSI installer logs.

This TA is intended for the parsing and indexing tier.

It does not perform endpoint upgrades, collect endpoint data directly, or provide dashboards.

---

##################################

## Purpose

##################################

This TA is responsible for:

* Defining the custom `splunk_upgrade` index
* Providing parsing configuration for upgrade operational logs
* Providing parsing configuration for MSI installer logs
* Ensuring timestamp recognition is consistent
* Ensuring event breaking and line merging behavior is consistent
* Supporting the Search Head dashboards and data model by standardizing indexed event behavior

This TA supports these sourcetypes:

```
splunk_upgrade
splunk_upgrade_msi
```

---

##################################

## What This TA Does Not Do

##################################

This TA does not:

* Perform Splunk Universal Forwarder upgrades
* Run PowerShell scripts
* Create Windows Scheduled Tasks
* Collect endpoint logs directly
* Create force retry flags
* Reset retry markers
* Provide dashboards
* Provide Search Head navigation
* Provide user interface components

Endpoint upgrade execution, endpoint log collection, state tracking, retry-loop prevention, and optional retry-control logic are handled by:

```
TA-windows_uf_upgrade_automation
```

Dashboards, data model, navigation, and documentation are handled by:

```
SA-windows_uf_upgrade_monitoring
```

---

##################################

## Deployment Target

##################################

Deploy this TA to the parsing and indexing tier.

Required deployment targets:

```
Indexers
Indexer clusters
```

Optional deployment targets:

```
Heavy Forwarders
```

Deploy to Heavy Forwarders only if Heavy Forwarders perform parsing before forwarding events to indexers in your environment.

Do not deploy this TA to:

```
Windows Universal Forwarders
Deployment Server clients that are not parsing or indexing data
```

In most environments, this TA does not need to be deployed to Search Heads. Search-time reporting content should be provided by `SA-windows_uf_upgrade_monitoring`.

---

##################################

## Solution Placement

##################################

The full solution is normally deployed across three tiers.

| App                                             | Deployment Target                          | Purpose                                                                                                  |
| ----------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `SA-windows_uf_upgrade_monitoring`                     | Search Head / Search Head Cluster          | Dashboards, data model, navigation, documentation, and reporting views.                                  |
| `TA-windows_uf_upgrade_automation`         | Windows Universal Forwarders               | Endpoint-side upgrade execution, local log collection, state tracking, and optional retry-control logic. |
| `TA-windows_uf_upgrade_parsing` | Parsing tier / Indexers / Heavy Forwarders | Index creation and parsing configuration for upgrade and MSI logs.                                       |

---

##################################

## Configuration Files

##################################

This TA may include the following configuration files:

```
default/indexes.conf
default/props.conf
```

### indexes.conf

`indexes.conf` defines the custom index used by the upgrade solution.

Default index:

```
splunk_upgrade
```

The index stores:

* Setup log events
* Execution log events
* MSI installer log events
* Force retry events
* Retry reset events

### props.conf

`props.conf` defines sourcetype parsing behavior for:

```
splunk_upgrade
splunk_upgrade_msi
```

This includes configuration such as:

* Timestamp recognition
* Event breaking
* Line merging behavior
* Sourcetype-level parsing behavior

---

##################################

## Index Configuration

##################################

The default index used by the solution is:

```
splunk_upgrade
```

Example `indexes.conf`:

```
[splunk_upgrade]
homePath = $SPLUNK_DB/splunk_upgrade/db
coldPath = $SPLUNK_DB/splunk_upgrade/colddb
thawedPath = $SPLUNK_DB/splunk_upgrade/thaweddb
disabled = 0
```

Review and adjust index settings according to your environment standards.

Items to review:

* Storage paths
* Volume usage
* Retention
* Sizing
* Replication factor requirements
* Search factor requirements
* Indexer cluster standards
* Frozen data handling

---

##################################

## Parsing Configuration

##################################

The primary operational sourcetype is:

```
splunk_upgrade
```

Recommended parsing behavior:

```
[splunk_upgrade]
SHOULD_LINEMERGE = false
TIME_PREFIX = ^
TIME_FORMAT = %Y-%m-%d %H:%M:%S
MAX_TIMESTAMP_LOOKAHEAD = 19
KV_MODE = auto
```

The MSI installer sourcetype is:

```
splunk_upgrade_msi
```

MSI logs are written as verbose Windows Installer logs and are collected using a wildcard monitor input from the endpoint TA.

Review the `splunk_upgrade_msi` parsing configuration to ensure MSI log events are broken and timestamped according to your operational requirements.

---

##################################

## Data Sources Supported

##################################

This parsing TA supports events collected from the following endpoint log files.

| Log File                                                             | Sourcetype           | Purpose                                                                                                              |
| -------------------------------------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `C:\ProgramData\SplunkUpgrade\splunk_upgrade_setup.log`              | `splunk_upgrade`     | Setup, validation, retry prevention, state checks, force retry flag consumption, and scheduled task creation events. |
| `C:\ProgramData\SplunkUpgrade\splunk_upgrade_exec.log`               | `splunk_upgrade`     | Upgrade execution, Splunk service control, MSI execution, cleanup, and final state events.                           |
| `C:\ProgramData\SplunkUpgrade\splunk_upgrade_force_retry_helper.log` | `splunk_upgrade`     | Force retry and retry reset operational events.                                                                      |
| `C:\ProgramData\SplunkUpgrade\splunk_upgrade_msi_<timestamp>.log`    | `splunk_upgrade_msi` | Verbose MSI installer output for each upgrade attempt.                                                               |

---

##################################

## Installation Instructions

##################################

### Standalone Indexer

Deploy this TA to:

```
$SPLUNK_HOME/etc/apps/TA-windows_uf_upgrade_parsing/
```

Restart Splunk:

```
$SPLUNK_HOME/bin/splunk restart
```

---

### Indexer Cluster

Deploy this TA through the cluster manager.

Typical location on the cluster manager:

```
$SPLUNK_HOME/etc/master-apps/TA-windows_uf_upgrade_parsing/
```

For newer Splunk versions, the cluster manager app path may be:

```
$SPLUNK_HOME/etc/manager-apps/TA-windows_uf_upgrade_parsing/
```

Apply the cluster bundle using your standard process.

Example:

```
$SPLUNK_HOME/bin/splunk apply cluster-bundle
```

Follow your organization’s standard indexer cluster deployment and rolling restart process.

---

### Heavy Forwarder

Deploy this TA to Heavy Forwarders only if Heavy Forwarders are responsible for parsing in your environment.

Typical location:

```
$SPLUNK_HOME/etc/apps/TA-windows_uf_upgrade_parsing/
```

Restart Splunk on the Heavy Forwarder after deployment:

```
$SPLUNK_HOME/bin/splunk restart
```

---

##################################

## Deployment Order

##################################

Recommended installation order:

```
1. Deploy TA-windows_uf_upgrade_parsing to the parsing/indexing tier.
2. Confirm the splunk_upgrade index exists.
3. Deploy SA-windows_uf_upgrade_monitoring to Search Heads / SHC.
4. Deploy TA-windows_uf_upgrade_automation to a small Windows UF test group.
5. Validate events are indexed correctly.
6. Validate dashboards and data model fields.
7. Expand deployment to additional Windows UFs.
```

The parsing TA should be deployed before endpoint logs are forwarded.

---

##################################

## Validation

##################################

After deployment, confirm the index exists.

```
| eventcount summarize=false index=splunk_upgrade
```

Confirm recent upgrade events are searchable:

```
index=splunk_upgrade sourcetype=splunk_upgrade earliest=-24h
| table _time host sourcetype eventcode status message details
| sort -_time
```

Confirm MSI log events are searchable:

```
index=splunk_upgrade sourcetype=splunk_upgrade_msi earliest=-24h
| table _time host sourcetype _raw
| sort -_time
```

Confirm sourcetype distribution:

```
index=splunk_upgrade earliest=-24h
| stats count by sourcetype
| sort sourcetype
```

Confirm event code extraction:

```
index=splunk_upgrade sourcetype=splunk_upgrade earliest=-24h
| stats count by eventcode status
| sort eventcode
```

---

##################################

## Requirements

##################################

This TA requires:

* Splunk Enterprise indexer or Heavy Forwarder
* Appropriate permissions to deploy apps to the parsing/indexing tier
* Available disk capacity for the `splunk_upgrade` index
* Consistent deployment across all indexers in a distributed environment
* Endpoint TA configured to send events to the `splunk_upgrade` index

---

##################################

## Best Practices

##################################

* Deploy this TA consistently across all indexers.
* Do not manually modify index settings on individual indexers in a cluster.
* Use the cluster manager for indexer cluster deployments.
* Use volumes where appropriate to align with enterprise storage standards.
* Keep retention and sizing aligned with expected upgrade log volume.
* Deploy parsing configuration before deploying endpoint collection at scale.
* Keep parsing/index configuration separate from Search Head dashboard content.
* Keep endpoint upgrade execution separate from parsing/indexing configuration.
* Validate sourcetypes before enabling data model acceleration.
* Confirm field extraction works before relying on dashboards.

---

##################################

## Troubleshooting

##################################

### Index Not Found

Symptom:

```
Searches against index=splunk_upgrade return an index not found error.
```

Check:

* Confirm `indexes.conf` exists in this TA.
* Confirm this TA is deployed to all required indexers.
* Confirm the index stanza is named `splunk_upgrade`.
* Confirm Splunk was restarted or the cluster bundle was applied.
* Review `splunkd.log` for index configuration errors.

Validation search:

```
| eventcount summarize=false index=splunk_upgrade
```

---

### Data Not Appearing

Symptom:

```
The index exists, but no upgrade events appear.
```

Check:

* Confirm Windows Universal Forwarders are sending to the correct indexers.
* Confirm endpoint `inputs.conf` uses `index = splunk_upgrade`.
* Confirm endpoint log files exist under `C:\ProgramData\SplunkUpgrade\`.
* Confirm the endpoint TA is deployed and inputs are enabled.
* Confirm forwarder outputs are configured correctly.
* Confirm the index is not disabled.

Validation search:

```
index=splunk_upgrade earliest=-24h
| stats count by host sourcetype
```

---

### Sourcetype Is Wrong

Symptom:

```
Events arrive in the index but have the wrong sourcetype.
```

Check:

* Confirm endpoint monitor inputs assign the expected sourcetype.
* Confirm `splunk_upgrade` is used for operational logs.
* Confirm `splunk_upgrade_msi` is used for MSI logs.
* Confirm no competing props/transforms are overriding sourcetype assignment.

Validation search:

```
index=splunk_upgrade earliest=-24h
| stats count by sourcetype source
| sort sourcetype source
```

---

### Events Are Merging Incorrectly

Symptom:

```
Multiple log lines appear as one event.
```

Check:

* Confirm `SHOULD_LINEMERGE = false` is configured for `splunk_upgrade`.
* Confirm the parsing TA is deployed to the parsing tier.
* Confirm the sourcetype is assigned correctly at input time.
* Confirm no other app overrides the sourcetype stanza.

Validation search:

```
index=splunk_upgrade sourcetype=splunk_upgrade earliest=-24h
| table _time host source _raw
| sort -_time
```

---

### Timestamps Are Incorrect

Symptom:

```
Events are indexed with unexpected timestamps.
```

Check:

* Confirm `TIME_PREFIX = ^`.
* Confirm `TIME_FORMAT = %Y-%m-%d %H:%M:%S`.
* Confirm `MAX_TIMESTAMP_LOOKAHEAD = 19`.
* Confirm log lines begin with a timestamp in the expected format.

Expected timestamp example:

```
2026-05-23 17:52:34
```

---

### Fields Are Missing in Dashboards

Symptom:

```
Events are searchable, but dashboards or data model panels show missing fields.
```

Check:

* Confirm `KV_MODE = auto` is available for the `splunk_upgrade` sourcetype.
* Confirm the Search Head app is deployed.
* Confirm the data model includes the expected fields.
* Confirm data model acceleration has been rebuilt after field changes.
* Confirm dashboards reference the correct data model field names.

Important:

```
Parsing controls event breaking and timestamping.
Search-time field extraction and data model reporting must also be available on the Search Head layer.
```

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
```

---

##################################

## Splunk Cloud and Platform Notes

##################################

This TA provides parsing and indexing configuration.

Deploy `TA-windows_uf_upgrade_parsing` only where parsing and index configuration are supported by your Splunk deployment model.

Do not deploy this TA to Windows Universal Forwarders.

Do not deploy endpoint-side upgrade logic to Splunk Cloud search or indexing tiers.

---

##################################

## Change History

##################################

### Version 1.0.0

* Added index configuration for `splunk_upgrade`.
* Added parsing configuration for `splunk_upgrade`.
* Added parsing configuration for `splunk_upgrade_msi`.
* Clarified parsing-tier deployment requirements.
* Clarified that this TA does not perform endpoint upgrades.
* Clarified that this TA does not provide dashboards.
* Updated solution references to the consolidated three-app structure.
* Added validation and troubleshooting guidance.

