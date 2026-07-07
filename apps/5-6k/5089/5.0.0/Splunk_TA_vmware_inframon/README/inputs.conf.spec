# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
[ta_vmware_collection_worker_inframon://<name>]
capabilities = <value>
* this is the comma delimited list of actions that the worker can perform (hostvmperf, clusterperf, etc.)
log_level = <value>
* the level at which the worker will log data.
max_empty_job_polls = <value>
* the number of consecutive empty job polls before the worker exits cleanly and lets Splunk relaunch it on the next interval
duration = <value>
* the minimum time between runs of the input should it exit for some reason

[ta_vmware_collection_scheduler_inframon://<name>]
* the scheduler should only exist once
log_level = <value>
* the level at which the scheduler will log data.
duration = <value>
* the minimum time between runs of the input should it exit for some reason
