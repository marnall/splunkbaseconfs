[thehive_alerts_cases://<name>]
additional_information = 
date = 
extra_data = 
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: 60)
max_size_value = (Default: 1000)
type = 

[backfill_alerts_cases://<name>]
additional_information = 
backfill_end = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. If only a date is provided, it will include the entire day until 23:59:59.
backfill_start = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. Example: 2023-01-01 or 2023-01-01T12:00:00.
date = 
extra_data = 
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: -1)
max_size_value = (Default: 1000)
type = 

[thehive_observables://<name>]
event_mode = Detailed: collect the full observable event. Summarized: collect only data, dataType, ioc, type and tags fields. (Default: detailed)
extra_data = 
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: 60)
max_size_value = (Default: 1000)

[backfill_observables://<name>]
backfill_end = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. If only a date is provided, it will include the entire day until 23:59:59.
backfill_start = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. Example: 2023-01-01 or 2023-01-01T12:00:00.
date = 
event_mode = Detailed: collect the full observable event. Summarized: collect only data, dataType, ioc, type and tags fields. (Default: detailed)
extra_data = 
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: -1)
max_size_value = (Default: 1000)

[thehive_audit://<name>]
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: 60)
max_size_value = (Default: 1000)

[backfill_audit://<name>]
backfill_end = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. If only a date is provided, it will include the entire day until 23:59:59.
backfill_start = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. Example: 2023-01-01 or 2023-01-01T12:00:00.
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: -1)
max_size_value = (Default: 1000)

[thehive_timeline://<name>]
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: 60)
max_events_per_case = Number of most recent events to take per case (0 = unlimited). (Default: 0)
max_size_value = (Default: 1000)
timeline_event_kinds = Filter by timeline event kinds. Leave empty for all.

[backfill_timeline://<name>]
backfill_end = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. If only a date is provided, it will include the entire day until 23:59:59.
backfill_start = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS. Example: 2023-01-01 or 2023-01-01T12:00:00.
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: -1)
max_events_per_case = Number of most recent events to take per case (0 = unlimited). (Default: 0)
max_size_value = (Default: 1000)
timeline_event_kinds = Filter by timeline event kinds. Leave empty for all.

[thehive_tasks://<name>]
date_field = Field used for incremental polling (Greater than or equal to current time - interval). (Default: updatedAt)
extra_data = Select additional information to retrieve for each task.
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: 300)
max_size_value = (Default: 1000)

[backfill_tasks://<name>]
backfill_end = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS.
backfill_start = Format: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS.
date_field = (Default: updatedAt)
extra_data = Select additional information to retrieve for each task.
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: -1)
max_size_value = (Default: 1000)

[thehive_instance_status://<name>]
fields_removal = 
index = (Default: default)
instance_id = Select the instance from the list.
interval = (Default: 300)
