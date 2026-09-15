[<stanza name>]

## Boolean fields

disabled = <boolean>
* Default: 0

bookmark = <boolean>
* Default: 0

search_hidden = <boolean>
* Default: 0

readonly = <boolean>
* Default: 0

dispatch_context_force = <boolean>
* Specifies when to force opening searches in the context of the dispatch_context
* Default: 0

## Integer fields

# 1 = Cloud, 2 = On Prem or Enterprise and 3 for both or any platform
env_run = <integer>
* Default: 3

ranking = <integer>
* Default: 1 (lowest) 5 (highest)

sleep_after = <integer>
* Default: 10

search_order = <integer>
* No default.

splunk_certified = <boolean>
* Default: 0

## String Fields

# `search_parent` represents the ID of the search.
search_parent = <string>
* No Default: 

category = <string>
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

# Possible values: discovery | summary | display. This field will be helpful in determining which searches can be displayed in the list of checks that can be added to a new collection (only summary searches).
search_type = <string>
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

# Provenance only: records the app a search was originally harvested from.
dispatch_context_origin = <string>
* Snapshot of the `dispatch_context` value at the time the search was
  imported into this catalogue. It exists so the original source app stays
  recoverable after `dispatch_context` is retargeted.
* Has NO effect on dispatch, search execution, or the app a search runs in.
  Nothing reads it at runtime; it is metadata for catalogue maintainers.
* No default.

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

drilldown_stanza_ids = <comma-separated-list>
* Optional ordered list of stanza names (the values inside `[stanza_name]`) to
  use as this search's contextual drilldown workflow. Insights Workspace
  exposes Back/Forward navigation when more than one target resolves and
  dispatches only the active target over the current dashboard time range.
* Duplicate targets are removed and at most 24 targets are retained.
* The referenced stanza should normally use `default_viz = splunk.table` and
  provide table column metadata in `viz_options`.
* No default.

drilldown_stanza_id = <string>
* Compatibility field for one canonical target stanza id. Existing
  configuration remains supported, but new configuration and admin writes use
  `drilldown_stanza_ids`.
* No default.

drilldown_search_name = <string>
* Deprecated compatibility field containing a target stanza's friendly
  `search_name`. Existing `local/searchbase.conf` overrides remain supported,
  but new configuration and admin writes must use `drilldown_stanza_ids`.
* When both keys are present and non-empty, the legacy key wins so an existing
  local override is not masked by newly shipped default stanza ids. New admin
  writes set `drilldown_stanza_ids` and clear both compatibility keys.
* No default.

drilldown_button_title = <string>
* Optional tooltip / accessible label for the tile-level drilldown affordance.
* Used only when a canonical or legacy drilldown target is set.
* No default.

search_post = <string>
* No default.

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

sub_category = <string>
* No default.

suggested_action = <string>
* No default.

tags = <string>
* No default.

# To identify a search to be replaced 
temp_replace_by = <string>
* No default.

# To identify a search to be replaced 
temp_replace_of = <string>
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
* Specify recommended UDF viz options to use when visualizing the results of
  the search.
* Common tile keys:
  * seriesColors: array of hex colors.
  * lineWidth: number.
  * nullValueDisplay: string.
  * stackMode: string.
  * legendDisplay: string.
  * dataValuesDisplay: string.
  * majorColor / singleValueColor / unit: single-value display hints.
* Table drilldown modal keys, read when another stanza references this stanza
  through `drilldown_stanza_ids` (or a compatibility key):
  * modalTitle: string title shown in the modal header.
  * modalSubtitle: string subtitle. Supports `{rangeLabel}`, `{RangeLabel}`,
    `{searchName}`, and `{drilldownSearchName}` tokens.
  * buttonTitle: optional fallback label for the parent tile's drilldown button.
  * rowKeyField: output field used as each table row key.
  * statusField: output field used for status badges and available/unavailable
    summary counts.
  * availableStatus: string value considered available. Default: Available.
  * unavailableStatus: string value considered unavailable. Default: Unavailable.
  * emptyMessage: message shown when the drilldown search returns no rows.
  * errorMessage: message shown when the drilldown search fails.
  * columns: array of objects with `field`, `label`, optional `align`
    (`left` or `right`), optional `kind` (`text`, `status`, or `metric`),
    optional `fallback`, and optional `truncate`.

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

ssef_search = <string>
* No default.

severity_rule = <string>
* No default.
