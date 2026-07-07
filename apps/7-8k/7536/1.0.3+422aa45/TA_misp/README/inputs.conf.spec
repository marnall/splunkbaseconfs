[misp_indicator_input://<name>]
continuous_importing = Continuous Importing is the default mode, import continues from last imported event import timestamp, so only attributes from new or modified events are imported. Disabling continuous importing would result in importing all attributes during each execution which makes only sense if the amount of attributes is lower than the limits. Max Events is used as maximum amount of requests in this case.  Default: True
exclude_tags = MISP tag include filter, e.g.: "tlp:white,tlp:amber"
expand_tags = Expand each attributes tag to a single event to avoid mvexpand.  Default: True
import_period = Import period over which indicators should be imported in day(s), month(s) or year(s) (<int>d|h|m)  Default: 180d
include_tags = MISP tag include filter, e.g.: "tlp:red,tlp:amber"
index = Default: ioc
interval = Time interval of the data input, in seconds.  Default: 300
max_requests = Must be a multiple of the depending request limit. Max amount of Events from which Attributes should be imported each import execution (max is 100k)  Default: 1000
misp_instance = Name of the MISP Instance
normalize_field_names = Normalize attribute field names, each field name will begin with "misp_*" and the data structure will be flattened.  Default: True
normalized_field_prefix = Defines the prefix for normalized fields, which is "misp_" by default.  Default: misp_
override_timestamps = Force to use ingest time instead of attribute timestamp.  Default: False
published = Only ingest attributes which are published.  Default: True
sourcetype = Default: misp:ti:attributes
to_ids = If enabled, only attributes with to_ids=true are imported.  Default: False
types = MISP type filter, e.g.: "domain,domain|ip".
warning_list = Prevents ingestion of Attributes which are in a warninglist.  Default: True

[misp_event_input://<name>]
continuous_importing = Continuous Importing is the default mode, import continues from last imported event import timestamp, so only new or modified events are imported. Disabling continuous importing would result in importing all events during each execution which makes only sense if the amount of events is lower than the limits. Max Events is used as maximum amount of requests in this case.  Default: True
expand_tags = Expand each misp event tag to a single event to avoid mvexpand.  Default: True
import_period = Import period over which indicators should be imported in day(s), month(s) or year(s) (<int>d|h|m)  Default: 180d
index = Default: ioc
interval = Time interval of the data input, in seconds.  Default: 300
max_requests = Must be a multiple of the depending request limit. Max amount of Events from which events should be imported each import execution (max is 100k)  Default: 1000
misp_instance = Name of the MISP Instance
normalize_field_names = Normalize event field names, each field name will begin with "misp_*" and the datastructure will be flatteneds.  Default: True
normalized_field_prefix = Defines the prefix for normaized fields, which is "misp_" by default.  Default: misp_
override_timestamps = Force to use ingest time instead of event timestamp.  Default: False
published = Only ingest events which are published.  Default: True
sourcetype = Default: misp:ti:events
