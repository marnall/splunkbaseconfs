[statseeker_port_metrics://<name>]
account = Account to use for this input.
device_filter = Optional Statseeker deviceid filter expression, for example IS("123") or IN("123","456").
device_name_filter = Optional Statseeker device name filter expression applied via cdt_device.name_filter, for example LIKE("AVN%").
index = (Default: default)
interval = How often Splunk runs the collection job, in seconds. (Default: 300)
metadata_fields = Comma-separated scalar cdt_port fields to add to each metric event as dimensions or context. (Default: ifAlias,ifDescr,ifAdminStatus,ifOperStatus,ifSpeed,idx,cdt_device.name,cdt_device.ipaddress)
metric_fields = Comma-separated cdt_port timeseries fields to ingest as Splunk metrics. (Default: RxBps,TxBps,RxUtil,TxUtil,RxDiscardsPercent,TxDiscardsPercent,RxErrorPercent,TxErrorPercent)
page_size = Number of ports to request per API page. (Default: 500)
port_filter = Optional Statseeker interface name filter expression, for example LIKE("Gigabit%").
sample_interval = Sampling interval in seconds for the requested timeseries values. (Default: 60)
timefilter = Statseeker timefilter expression used for each collection run. The default covers one 5-minute run plus a 1-minute buffer while avoiding the current partial minute. (Default: range=now - 6m to now - 1m)

[statseeker_device_health://<name>]
account = Account to use for this input.
device_fields = Comma-separated scalar cdt_device fields to emit in each JSON event. (Default: ipaddress,vendor,sysLocation,snmp_poll,snmp_state,ping_poll,ping_state,sysName,sysDescr,sysObjectID,memorySize)
device_filter = Optional Statseeker deviceid filter expression, for example IS("123") or IN("123","456").
index = (Default: default)
interval = How often Splunk runs the collection job, in seconds. (Default: 300)
name_filter = Optional Statseeker device name filter expression, for example LIKE("AVN%").
page_size = Number of devices to request per API page. (Default: 500)
ping_metric_fields = Comma-separated cdt_device timeseries fields to query with avg format and include in each JSON event. (Default: ping_rtt,ping_jitter,ping_lost_percent)
timefilter = Statseeker timefilter expression applied to any requested ping metric fields. The default covers one 5-minute run plus a 1-minute buffer while avoiding the current partial minute. (Default: range=now - 6m to now - 1m)

[statseeker_device_temperature://<name>]
account = Account to use for this input.
current_fields = Comma-separated temperature fields to query in current format and emit in each JSON event. (Default: temperatureValueCelsius)
device_filter = Optional Statseeker deviceid filter expression, for example IS("123") or IN("123","456").
device_name_filter = Optional Statseeker device name filter expression applied via cdt_device.name_filter, for example LIKE("AVN%").
include_null_values = Enable to emit temperature rows even when the requested current value fields are null.
index = (Default: default)
interval = How often Splunk runs the collection job, in seconds. (Default: 300)
name_filter = Optional Statseeker temperature entity name filter expression.
page_size = Number of temperature rows to request per API page. (Default: 500)
temperature_fields = Comma-separated scalar temperature fields to emit alongside the current temperature values. (Default: temperatureDescr,temperatureType,idx,cdt_device.name)
timefilter = Statseeker timefilter expression applied when requesting current temperature values. The default covers one 5-minute run plus a 1-minute buffer without scanning a broader history window. (Default: range=now - 6m to now)

[statseeker_wan3g://<name>]
account = Account to use for this input.
current_fields = Comma-separated Cisco WAN 3G fields to query in current format and emit in each JSON event. (Default: ModemTemp,GsmRSSI,GsmEcIo,NearbyCells,RetriesRemaining,RxBytes,TxBytes)
device_filter = Optional Statseeker deviceid filter expression, for example IS("123") or IN("123","456").
device_name_filter = Optional Statseeker device name filter expression applied via cdt_device.name_filter, for example LIKE("AVN%").
index = (Default: default)
interval = How often Splunk runs the collection job, in seconds. (Default: 300)
name_filter = Optional Statseeker Cisco WAN 3G entity name filter expression.
nearby_current_fields = Comma-separated nearby-cell fields to query in current format and embed under nearby_cells. (Default: PrimaryScramblingCode,RSCP,EcIoMeasurement)
page_size = Number of WAN 3G rows to request per API page. (Default: 500)
timefilter = Statseeker timefilter expression applied when requesting current WAN 3G values. The default covers one 5-minute run plus a 1-minute buffer without scanning a broader history window. (Default: range=now - 6m to now)
wan3g_fields = Comma-separated scalar Cisco WAN 3G fields to emit alongside the current values. (Default: IMEI,GsmCountry,GsmNetwork,idx,cdt_device.name)

[statseeker_cpu_metrics://<name>]
account = Account to use for this input.
device_filter = Optional Statseeker deviceid filter expression.
device_name_filter = Optional Statseeker device name filter expression applied via cdt_device.name_filter, for example LIKE("AVN%").
index = (Default: default)
interval = How often Splunk runs the collection job, in seconds. (Default: 300)
metadata_fields = Comma-separated scalar cdt_cpu fields to add to each metric event as dimensions or context. (Default: cpuDescr,cpuType,idx,cdt_device.name)
metric_fields = Comma-separated cdt_cpu timeseries fields to ingest as Splunk metrics. (Default: cpuLoad)
name_filter = Optional Statseeker CPU entity name filter expression.
page_size = Number of CPU rows to request per API page. (Default: 500)
sample_interval = Sampling interval in seconds for the requested timeseries values. (Default: 60)
timefilter = Statseeker timefilter expression used for each collection run. The default covers one 5-minute run plus a 1-minute buffer while avoiding the current partial minute. (Default: range=now - 6m to now - 1m)

[statseeker_memory_metrics://<name>]
account = Account to use for this input.
device_filter = Optional Statseeker deviceid filter expression.
device_name_filter = Optional Statseeker device name filter expression applied via cdt_device.name_filter, for example LIKE("AVN%").
index = (Default: default)
interval = How often Splunk runs the collection job, in seconds. (Default: 300)
metadata_fields = Comma-separated scalar cdt_memory fields to add to each metric event as dimensions or context. (Default: memoryDesc,memoryType,memorySize,idx,cdt_device.name)
metric_fields = Comma-separated cdt_memory timeseries fields to ingest as Splunk metrics. (Default: memoryUsedPercent,memoryFreePercent,memoryUsed,memoryFree)
name_filter = Optional Statseeker memory entity name filter expression.
page_size = Number of memory rows to request per API page. (Default: 500)
sample_interval = Sampling interval in seconds for the requested timeseries values. (Default: 60)
timefilter = Statseeker timefilter expression used for each collection run. The default covers one 5-minute run plus a 1-minute buffer while avoiding the current partial minute. (Default: range=now - 6m to now - 1m)

[statseeker_device_lookup://<name>]
account = Account to use for this input.
device_fields = Comma-separated cdt_device fields to export into the lookup file. (Default: ipaddress,vendor,sysLocation,snmp_poll,snmp_state,ping_poll,ping_state,sysName,sysDescr,sysObjectID,memorySize)
device_filter = Optional Statseeker deviceid filter expression.
interval = How often Splunk refreshes the device lookup file, in seconds. (Default: 300)
lookup_filename = CSV lookup file to write under the app lookups directory. (Default: statseeker_device_inventory.csv)
name_filter = Optional Statseeker device name filter expression.
page_size = Number of devices to request per API page. (Default: 500)

[statseeker_event_records://<name>]
account = Account to use for this input.
device_filter = Optional Statseeker deviceid filter expression.
entity_type_filter = Optional entityTypeName filter expression, useful for threshold_record collections.
event_filter = Optional event filter expression, for example IS("ping_state") or IS("IF-MIB.ifOperStatus").
fields = Optional comma-separated field list. Leave blank to use the add-on default for the selected resource.
index = (Default: default)
interval = How often Splunk runs the collection job, in seconds. (Default: 300)
page_size = Number of rows to request per API page. (Default: 500)
resource_name = Select which event-style Statseeker resource to collect. (Default: event_record)
state_filter = Optional state filter expression, for example IS("down") or IS("up").
text_filter = Optional syslog text filter expression, for example LIKE("%down%").
timefilter = Statseeker timefilter expression applied to the resource time field. The default covers one 5-minute run plus a 1-minute buffer without repeatedly rescanning older records. (Default: range=now - 6m to now)
type_filter = Optional syslog type filter expression.
