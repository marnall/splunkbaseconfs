# SA-metricator-for-nmon

Copyright 2017 Octamis limited - Copyright 2017 Guilhem Marchand

All rights reserved.

Sample indexes.conf:

# indexes.conf

########################
# default Indexes scheme
########################

# The default indexing scheme uses a combination of 4 indexes:

# - metrics ingested with the metric stores
# - nmon metric data ingested as regular events
# - nmon configuration data ingested as regular events
# - application internal data ingested as regular events

# CUSTOMIZATION:

# if you need more segmentation, for example if you are indexing data from several data centers, we suggest you use
# the same naming convention across naming convention such that you easily customize eventtypes and macros

# nmon data ingested as metrics
[os-unix-nmon-metrics]
disabled = false
coldPath = $SPLUNK_DB/os-unix-nmon-metrics/colddb
datatype = metric
homePath = $SPLUNK_DB/os-unix-nmon-metrics/db
splitByIndexKeys = metric_name,host
thawedPath = $SPLUNK_DB/os-unix-nmon-metrics/thaweddb
repFactor = auto

# nmon data ingested as regular events
[os-unix-nmon-events]
disabled = false
coldPath = $SPLUNK_DB/os-unix-nmon-events/colddb
homePath = $SPLUNK_DB/os-unix-nmon-events/db
thawedPath = $SPLUNK_DB/os-unix-nmon-events/thaweddb
repFactor = auto

# nmon config ingested as regular events
[os-unix-nmon-config]
disabled = false
coldPath = $SPLUNK_DB/os-unix-nmon-config/colddb
homePath = $SPLUNK_DB/os-unix-nmon-config/db
thawedPath = $SPLUNK_DB/os-unix-nmon-config/thaweddb
repFactor = auto

# nmon internal data
[os-unix-nmon-internal]
disabled = false
coldPath = $SPLUNK_DB/os-unix-nmon-internal/colddb
homePath = $SPLUNK_DB/os-unix-nmon-internal/db
thawedPath = $SPLUNK_DB/os-unix-nmon-internal/thaweddb
repFactor = auto

