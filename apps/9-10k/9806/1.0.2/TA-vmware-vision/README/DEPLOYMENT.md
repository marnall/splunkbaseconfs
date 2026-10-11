# Heavy forwarders, indexers and search heads

## Choose the first parsing tier

| Tier | What to install |
|---|---|
| Search head | Full `vmware_vision` app |
| Search head cluster | Full app through the deployer |
| HF receiving raw VMware logs | `TA-vmware-vision` and your managed inputs/outputs |
| Indexers receiving only cooked HF data | Index definitions; no additional TA needed solely for parsing that path |
| Indexers receiving raw or unparsed UF data | `TA-vmware-vision` and index definitions |
| Indexer cluster | Deploy required TA/index definitions through the cluster manager |
| Universal forwarder | File inputs, index/sourcetype assignments and forwarding configuration |

The TA has event boundaries, timestamp extraction, truncation and UTF-8 settings. It has no Python, CIM mappings or dashboards. The full app's search-time knowledge is distributed from search heads to search peers through Splunk's search bundle. Installing the TA on indexers does not replace that bundle.

For a complete input and verification example, read `TA_CONFIGURATION.md` alongside this guide. It is included in the installed TA under `README/`.

## Deploy to an HF

1. Extract the TA using your deployment process into `$SPLUNK_HOME/etc/apps/TA-vmware-vision`.
2. Put monitor inputs and output routing in your collection app's `local/` configuration.
3. Assign the exact VMware Vision sourcetype and an existing index to each input.
4. Verify effective settings with `splunk btool props list vmware:vision:vcenter --debug`.
5. Restart the HF when required by the configuration change.
6. Send one controlled source event, then inspect `_raw`, `_time`, host and sourcetype in Splunk.

Do not enable a second listener on a port already owned by your syslog receiver. Durable collection, buffering, transport security and firewall rules belong to the collection design.

## Deploy to indexers

For standalone indexers, use your normal deployment process. For a cluster, stage the TA only when indexers need to parse raw data, and stage VMware index definitions in the cluster manager's `manager-apps` area. Include `repFactor=auto` in clustered index definitions where required by your design.

Validate and apply the cluster bundle using the manager's supported workflow. Do not edit individual peer app directories. The inactive examples under `ta-examples/` distinguish standalone and clustered index definitions.

## Deploy to search heads

Install the full app and set `vmware_vision_indexes`. For an SHC, use the deployer and preserve local/user-owned settings according to your cluster workflow. Install the supported CIM app on search heads if you need [CIM integration](CIM.md); Enterprise Security normally supplies its supported version.

Verify that the search bundle includes the lookup script, `vmware_vision_parser.py`, `vmware_vision_cim.py`, props, transforms, fields, eventtypes and tags. Do not exclude the app's `bin/` directory through a bundle replication rule.

## Acceptance checks

Use a time range with known source data:

```spl
index=vmware sourcetype=vmware:vision:*
| stats count by splunk_server sourcetype parser_version parser_status
```

```spl
index=vmware sourcetype=vmware:vision:* record_kind=event
| table _time splunk_server vcenter vm_name vm_id user event_type vmware_action action status
```

Run from VMware Vision and Search & Reporting. Check a peer that actually holds matching data; an empty index cannot establish peer-side lookup behavior. Confirm the result against the original log and verify the source timestamp and sender identity.

Then validate both custom models and, if installed, the two CIM models. Test summaries only after raw-backed queries return expected events. Repeat these checks on the real distributed topology before relying on production reports. Standalone lab results do not validate bundle replication, network collection or cluster behavior.
