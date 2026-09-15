Statseeker Add-On for Splunk
============================

Overview
--------
This add-on collects Statseeker interface telemetry, device snapshots, and operational records into Splunk. Port, CPU, and memory timeseries are modeled as metrics, while device health, temperature, WAN 3G, and event-style resources are modeled as JSON events because they are current-state snapshots with mixed descriptive fields rather than clean sampled series.

![Overview Screenshot](media/ss_screenshot_overview_01.png)

Example dashboards
------------------
This add-on includes the example dashboards shown on Splunkbase: Statseeker Overview (statseeker_overview.xml) and Statseeker Port Activity (statseeker_port_activity.xml). They are included in the TA package but are not exposed in the add-on menu. To use either dashboard, copy its XML file into your own Splunk app.

Build process
-------------
Build and package from the TA root with UCC. Replace 0.0.18 with the version being released.

```
python3 -m venv .venv
source .venv/bin/activate
pip install splunk-add-on-ucc-framework
ucc-gen build --source package --ta-version 0.0.18
ucc-gen package --path output/TA-statseeker
```

The resulting package is ready to be uploaded to Splunk/Splunkbase. See the UCC documentation at https://splunk.github.io/addonfactory-ucc-generator/.

Setup and installation
----------------------
1. Install the add-on from Splunkbase - or build the package and upload to a Splunk search head or heavy forwarder (or as a private app in Splunk Cloud)
2. Open the add-on configuration page in Splunk.
3. Create an account with the Statseeker base URL, username, password, authentication mode, and TLS verification preference.
4. Create one or more inputs and choose an event index for snapshot/event inputs or a metrics index for metric inputs.

Account requirements
--------------------
The Statseeker account must:
- have API access enabled
- have permission to read the Statseeker resources you plan to collect, including cdt_port, cdt_device, temperature, and cisco_wan_3g where applicable
- support either token authentication through /ss-auth or HTTP Basic authentication
- be appropriately powerful to support API queries without timeout

Statseeker API reference
------------------------
The Statseeker API documentation at https://docs.statseeker.com/api/ describes the resources, fields, filters, timefilters, and other parameters that can help configure these modular inputs.

Modular input: Device Health Snapshots
--------------------------------------
Input name: statseeker_device_health

Purpose:
Collect current cdt_device health and inventory data as one JSON event per device. Optional ping metrics are retrieved as averages over the configured timefilter.

Key settings:
- Device fields: comma-separated scalar cdt_device fields to include in each event, such as ipaddress, vendor, sysLocation, snmp_state, ping_state, sysName, sysDescr, and memorySize
- Ping metric fields: optional comma-separated cdt_device timeseries fields to query with avg format, such as ping_rtt, ping_jitter, and ping_lost_percent
- Timefilter: Statseeker timefilter expression applied when Ping metric fields are configured
- Page size: number of devices to request per API page
- Device ID filter: optional raw filter expression applied to deviceid
- Device name filter: optional raw filter expression applied to the device name

Modular input: Port Metrics
---------------------------
Input name: statseeker_port_metrics

Purpose:
Collect interface-level timeseries metrics from Statseeker and ingest them into Splunk as metrics.

Key settings:
- Metric fields: comma-separated cdt_port timeseries fields such as RxBps, TxBps, RxUtil, TxUtil, or RxTxDiscardsPercent
- Timefilter: raw Statseeker timefilter expression, for example range=now - 6m to now - 1m
- Sample interval: sampling interval in seconds requested from Statseeker
- Page size: number of interfaces to request per API page
- Device ID filter: optional raw filter expression applied to deviceid
- Device name filter: optional linked-resource filter applied via cdt_device.name_filter
- Port name filter: optional raw filter expression applied to the interface name

Filter syntax:
Device name filters that use LIKE() or REGEX() must use single quotes around the pattern, for example LIKE('lab-%'). Invalid filter expressions cause errors while polling the Statseeker APIs.

Example configuration
---------------------
- Metric fields: RxBps,TxBps,RxUtil,TxUtil,RxTxDiscardsPercent
- Timefilter: range=now - 6m to now - 1m
- Sample interval: 60
- Page size: 500

Data format
-----------
The modular input writes one metric event per port sample timestamp with shared dimensions that include port ID, port name, and device ID. Each event can contain multiple measurements using top-level fields in the form metric_name:statseeker.port.<field>.

Performance and timeout tuning
------------------------------
If Statseeker port metric collections time out or take too long to complete, reduce the amount of data returned by each API request rather than only increasing the poll interval.

Recommended tuning options:
- Lower the Page size to reduce the number of interfaces returned in each API request. This is usually the first and safest tuning lever when a single request is taking too long.
- Use more frequent polling with a smaller Timefilter window so each run asks Statseeker for less history. For example, a 60 second poll interval can be paired with Sample interval 60 and a Timefilter such as range=now - 2m to now - 1m.
- Keep Sample interval aligned with the data density you actually need. A smaller sample interval returns more samples per run and increases request cost, while a larger sample interval may be too coarse for short timefilter windows.
- Split large collections into multiple inputs of the same type, each with a narrower filter. Device name filter is a practical way to partition collection by site, region, or naming convention, for example one input for LIKE('NYC%') and another for LIKE('SFO%').
- Reduce the number of requested Metric fields if a single input is querying more timeseries than you need for a given use case.

Suggested approach:
- Start by lowering Page size.
- If requests are still slow, shorten the Timefilter and poll more frequently.
- If a single input is still too large, create multiple statseeker_port_metrics inputs with different Device name filter values so the load is split across smaller API queries.

Troubleshooting
---------------
- Review Splunk logs - search `index=_internal source="*/ta-statseeker_*input.log"` for add-on execution errors.
- If token authentication fails, switch the account to auto or basic mode based on your Statseeker RESTful API Authentication Mode.
- If no events are indexed, verify that the configured metric fields return timeseries data from the Statseeker API and that the selected index accepts metrics data.
- If TLS verification fails, import the CA chain used by Statseeker into Splunk or temporarily disable verification for testing.

Modular input: Device Temperature Snapshots
-------------------------------------------
Input name: statseeker_device_temperature

Purpose:
Collect current temperature entity values from Statseeker and emit one JSON event per temperature row. This input is modeled as event data because the API usage here returns current values paired with descriptive sensor metadata.

Key settings:
- Value fields: current-format temperature fields such as temperatureValueCelsius
- Metadata fields: scalar context such as temperatureDescr, temperatureType, idx, and cdt_device.name
- Timefilter: Statseeker timefilter expression used when requesting current values
- Device ID filter: optional raw filter expression applied to deviceid
- Device name filter: optional linked-resource filter applied via cdt_device.name_filter
- Temperature entity name filter: optional raw filter expression applied to the temperature entity name

Modular input: Cisco WAN 3G Snapshots
-------------------------------------
Input name: statseeker_wan3g

Purpose:
Collect current Cisco WAN 3G modem rows and embed associated nearby-cell readings in each JSON event. This input is modeled as event data because each collection represents a current operational snapshot with counters, identifiers, and nested child records.

Key settings:
- Current value fields: fields such as ModemTemp, GsmRSSI, GsmEcIo, NearbyCells, RetriesRemaining, RxBytes, and TxBytes
- Metadata fields: scalar context such as IMEI, GsmCountry, GsmNetwork, idx, and cdt_device.name
- Nearby cell current fields: current-format child fields such as PrimaryScramblingCode, RSCP, and EcIoMeasurement
- Timefilter: Statseeker timefilter expression used when requesting current values
- Device ID filter: optional raw filter expression applied to deviceid
- Device name filter: optional linked-resource filter applied via cdt_device.name_filter
- WAN 3G entity name filter: optional raw filter expression applied to the Cisco WAN 3G entity name
