[thresholds]
total_vcpu_sec_th = <number>
* Threshold for the cumulative CPU time consumed by the search across the full environment.

total_mem_gib_sec_th = <number>
* Threshold for the cumulative memory GiB-seconds consumed by the search across the full environment.

shs_vcpu_sec_th = <number>
* Threshold for the cumulative CPU time consumed on all search heads.

shs_mem_gib_sec_th = <number>
* Threshold for the cumulative memory GiB-seconds consumed on all search heads.

idxs_vcpu_sec_th = <number>
* Threshold for the cumulative CPU time consumed on all indexers.

idxs_mem_gib_sec_th = <number>
* Threshold for the cumulative memory GiB-seconds consumed on all indexers.

max_shs_vcpu_sec_th = <number>
* Threshold for the peak instantaneous CPU usage recorded on a search head.

max_idxs_vcpu_sec_th = <number>
* Threshold for the peak instantaneous CPU usage recorded on an indexer.

max_shs_mem_usage_th = <number>
* Threshold for the peak instantaneous memory usage in GiB recorded on a search head.

max_idxs_mem_usage_th = <number>
* Threshold for the peak instantaneous memory usage in GiB recorded on an indexer.

[general]
sendemail = true|false
* Controls whether Splunk WLM Resource Protection App sends notification emails when it terminates a search.
