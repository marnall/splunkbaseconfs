[<stanza name>]

## Boolean fields

disabled = <boolean>
* Default: 0

bookmark = <boolean>
* Default: 0

search_hidden = <boolean>
* Default: 0

dispatch_context_force = <boolean>
* Specifies when to force opening searches in the context of the dispatch_context
* Default: 0

## Integer fields

# 1 = Cloud, 2 = On Prem or Enterprise and 3 for both or any platform
env_run = <integer>
* Default: 3

sleep_after = <integer>
* Default: 10

splunk_certified = <boolean>
* Default: 0

## String Fields

category = <string>
* No default.


# Possible values: [hourly | daily | monthly | weekly]. This will be used in the SSEF builder to create collection sub-groups based on the search schedule.
ssef_cron = <string>
* No default.

# Possible values: [summary | search | licensing | indexing | apps | ...]. it needs to match one of the existent KPI tabs and will indicate where the search result card will be displayed.
target_component = <string>
* No default.

date_created = <string>
* No default.

date_updated = <string>
* No default.

description = <string>
* No default.

dispatch_context = <string>
* Default: searchbase

execution_plan = <string>
* No default.

explanation = <string>
* No default.

solution = <string>
* No default.

# Images or logos associated with a search
img_path = <string>
* No default.

related_info = <string>
* No default.

search = <string>
* No default.

search_author = <string>
* No default.

quid = <string>
* No default.

search_name = <string>
* No default.

search_origin = <string>
* Default: searchbase


severity_critical_text = <string> 
* No default.

severity_high_text = <string>
* No default.

severity_info_text = <string>
* No default.

severity_medium_text = <string>
* No default.

severity_normal_text = <string>
* No default.

severity_low_text = <string>
* No default.

severity_critical_alert_weight = <integer> 
* No default.

severity_high_alert_weight = <integer>
* No default.

severity_info_alert_weight = <integer>
* No default.

severity_medium_alert_weight = <integer>
* No default.

severity_normal_alert_weight = <integer>
* No default.

severity_low_alert_weight = <integer>
* No default.

sub_category = <string>
* No default.

tags = <string>
* No default.

# When search is cloned and updated
updated_author = <string>
* No default.

version = <string>
* Default: 1.0.0

default_viz = <string>
# Possible values: splunk.area, splunk.bar, splunk.column, splunk.events, splunk.line, splunk.pie, splunk.singlevalue, splunk.singlevalueradial, splunk.table
* Default: splunk.table

viz_options = <viz-options-json>
* Specify recommend UDF viz options to use when visualizing the results of the search 

diagnostic_searches = <string>
* No default.

## Other fields

dispatch_context_uid = <cron string>
* Specifies the App ID on Splunkbase
* No default.

dispatch_earliest_time = <time-str>
* Specifies the earliest time for this search. Can be a relative or absolute
  time.
* If this value is an absolute time, use the 'dispatch.time_format' setting
  to format the value.
* Default: empty string

dispatch_latest_time = <time-str>
* Specifies the latest time for this saved search. Can be a relative or
  absolute time.
* If this value is an absolute time, use the 'dispatch.time_format' setting
  to format the value.
* Default: empty string

