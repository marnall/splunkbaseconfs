"""This module contains constants used throughout the add-on"""

ADDON_NAME = "Splunk_TA_SAA"
JOB_SOURCETYPE = "splunk:aa:job"
JOB_TASK_SOURCETYPE = "splunk:aa:job:task"
JOB_RESOURCE_SOURCETYPE = "splunk:aa:job:resource"


NOTABLE_QUERY = (
    "search index=notable"
    '| where _time>relative_time("{orig_time}", "-3m") AND _time<relative_time("{orig_time}", "+3m")'
    '| search orig_bkt="{orig_bkt}" orig_time="{orig_time}"'
    '| eval indexer_guid=replace(_bkt,".*~(.+)","\\1"),event_hash=md5(_time._raw),'
    'event_id=indexer_guid."@@".index."@@".event_hash,rule_id=event_id'
    '| search event_id="*"'
    "| fields indexer_guid, event_hash, event_id, index, rule_id | dedup rule_id"
)
