# Configure TA-vmware-vision

TA-vmware-vision 1.0.2 supplies event boundaries, timestamp settings and UTF-8 encoding. Its beacon icon distinguishes it from the full VMware Vision app. Both packages share a repository so their raw parsing settings stay aligned.

The TA has no setup page, Python lookup, credentials or VMware API connection. Collection inputs, forwarding and index definitions are managed separately. Search-time fields, dashboards, custom models and CIM mappings come from the full app on the search tier.

## 1. Choose the parsing tier

For a syslog collector feeding a heavy forwarder, install the TA on the HF. If indexers receive raw data directly or unparsed data from a universal forwarder, install it on those indexers. If an HF already parses the events, downstream indexers do not need another copy solely for that path. A standalone instance with the full VMware Vision app already has these parsing settings.

Use your normal deployment process. An independent HF uses `$SPLUNK_HOME/etc/apps/TA-vmware-vision`; an indexer cluster receives the required app through its cluster manager. Do not extract packages directly onto individual cluster peers.

## 2. Create the destination index

Create or select an index on the indexing tier before enabling collection. The examples use `vmware`; replace it consistently with your chosen index. Set retention and search-role access according to your environment. The TA does not create an index.

The inactive `indexes-indexer.conf.example` and `indexes-cluster.conf.example` files show the relevant placement differences. Clustered index definitions include `repFactor = auto`. Example files live under `docs/ta-examples/` in source and `README/examples/` in the installed TA.

## 3. Assign each source stream

| Input content | Sourcetype |
|---|---|
| vCenter syslog | `vmware:vision:vcenter` |
| ESXi syslog | `vmware:vision:esxi` |
| Aria syslog or supported forwarded records | `vmware:vision:aria` |
| Supported VMware JSON event records, one per line | `vmware:vision:json` |

Keep source families separate where possible. Preserve the original sender and timestamp in the raw event. Do not put vCenter, ESXi and Aria into one undifferentiated input just to reduce the number of stanzas. Aria appliance diagnostics are not a substitute for forwarded vCenter activity records.

## 4. Configure collector file inputs

This example assumes your syslog collector writes separate files on the HF, and the Splunk service account can read them. Add the stanzas to your managed collection app's `local/inputs.conf`, for example `$SPLUNK_HOME/etc/apps/your_vmware_collection/local/inputs.conf`. Replace the paths before use. Do not edit the TA's `default` files.

```ini
[monitor:///var/log/remote/vcenter/*.log]
index = vmware
sourcetype = vmware:vision:vcenter
disabled = 0

[monitor:///var/log/remote/esxi/*.log]
index = vmware
sourcetype = vmware:vision:esxi
disabled = 0

[monitor:///var/log/remote/aria/*.log]
index = vmware
sourcetype = vmware:vision:aria
disabled = 0
```

Unlike the enabled example above, the shipped `inputs-hf.conf.example` keeps every stanza disabled. Copy only the stanzas you need and enable them after editing. It includes plain TCP alternatives; choose one collection path for each stream to avoid duplicates. Do not add a listener on a port already used by your syslog collector. When a UF monitors the files, put inputs on that UF and the TA on the first full parsing tier downstream.

For the input settings, see Splunk's [file monitoring documentation](https://help.splunk.com/splunk-cloud-platform/get-data-in/get-started-getting-data-in/9.3.2411/get-data-from-files-and-directories/monitor-files-and-directories-with-inputs.conf).

## 5. Verify forwarding and effective configuration

Use the HF's existing managed Splunk-to-Splunk forwarding configuration. Check that its destination group or indexer discovery configuration reaches the intended indexing tier. Preserve your site's TLS settings. The TA does not include `outputs.conf`; installing it alone does not forward events. See the [outputs.conf reference](https://help.splunk.com/en/splunk-enterprise/administer/admin-manual/10.0/configuration-file-reference/10.0.0-configuration-file-reference/outputs.conf) for routing settings.

On the relevant input or parsing instance, run as the Splunk service account:

```bash
/opt/splunk/bin/splunk btool inputs list --debug
/opt/splunk/bin/splunk btool outputs list --debug
/opt/splunk/bin/splunk btool props list vmware:vision:vcenter --debug
/opt/splunk/bin/splunk btool props list vmware:vision:esxi --debug
/opt/splunk/bin/splunk btool props list vmware:vision:aria --debug
```

Use your actual Splunk installation path. Confirm the input path, index and sourcetype; then confirm the TA supplies the effective parsing settings. Resolve conflicting local settings or other apps before testing. Restart the affected standalone HF or indexer when required; for managed clusters, use the supported bundle workflow and its restart handling.

## 6. Verify records on the search head

Install the full VMware Vision app on the search head. Set its `vmware_vision_indexes` macro to your actual indexes, for example `(index=vmware)`. Confirm the searching role can access them.

Use a short time range containing a known event:

```spl
index=vmware sourcetype=vmware:vision:*
| table _time host source sourcetype vcenter event_type parser_status
        vm_name vmware_action action status user
| head 50
```

Compare `_time`, the original `_raw`, sender, event boundaries and sourcetype with the source record. Run the search in VMware Vision and Search & Reporting. Verify an indexer that actually holds matching data; an empty search cannot prove knowledge bundle replication. See the deployment guide's acceptance checks for distributed searches.

The TA does not configure models. On the search tier, follow the repository's `docs/DATA_MODELS.md` for VMware models and `docs/CIM.md` for Authentication, Change and ES setup. In an installed TA, use the public [data-model guide](https://github.com/majidershadi/vmware-vision/blob/main/docs/DATA_MODELS.md) and [CIM guide](https://github.com/majidershadi/vmware-vision/blob/main/docs/CIM.md).

## Upgrade from TA 1.0.1

Back up local settings and deploy the 1.0.2 archive through your existing process. This release changes branding and documentation only. It retains enabled update checks and identical parsing settings. No reindexing, model rebuild or VMware Vision app upgrade is required for this TA update.
