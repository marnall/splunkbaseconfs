# This file contains possible settings you can use to configure the Splunk
# Infrastructure Monitoring Add-on. 
#
# There is a sim.conf in $SPLUNK_HOME/etc/apps/splunk_ta_sim/default. To set custom
# configurations, place a sim.conf in $SPLUNK_HOME/etc/apps/splunk_ta_sim/local.
# You must restart the Splunk Infrastructure Monitoring Add-on to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

[sim_api]
* This stanza includes settings used by the Splunk Infrastructure Monitoring Add-on
* to connect to Infrastructure Monitoring APIs and process Infrastructure Monitoring API data.

sim_api_timeout = <integer>
* The Infrastructure Monitoring REST API request timeout, in seconds. 
* Default: 5

sim_command_flow_metadata_fields_to_ignore = <comma-separated list>
* A list of metadata fields removed from the Infrastructure Monitoring metrics data
* when processed by the Splunk Infrastructure Monitoring Add-on 'flow' query.
* Default: sf_createdOnMs,sf_isPreQuantized,sf_key,sf_metric,sf_type,sf_singletonFixedDimensions,sf_originatingMetric

sim_command_event_metadata_fields_to_ignore = <comma-separated list>
* A list of metadata fields removed from the Infrastructure Monitoring events data
* when processed by the Splunk Infrastructure Monitoring Add-on 'event' query.
* Default: sf_recipients

sim_mod_input_metadata_fields_to_ignore_in_materialized_view = <comma-separated list>
* A list of metadata fields removed from the Infrastructure Monitoring metrics data
* when processed by the Splunk Infrastructure Monitoring Data Streams modular input
* in materialized view mode.
* Default: sf_createdOnMs,sf_isPreQuantized,sf_key,sf_metric,sf_type,sf_singletonFixedDimensions,sf_originatingMetric

sim_mod_input_metadata_fields_to_ignore_in_optimized_view = <comma-separated list>
* A list of metadata fields removed from the Infrastructure Monitoring metrics data
* when processed by the Splunk Infrastructure Monitoring Data Streams modular input
* in optimized view mode.
* Default: sf_createdOnMs,sf_isPreQuantized,sf_metric,sf_type,sf_singletonFixedDimensions

sim_mod_input_retry_wait_time = <integer>
* The number of seconds the Splunk Infrastructure Monitoring Data Streams modular input
* waits to retry the Infrastructure Monitoring SignalFlow API.
* Default: 3

sim_mod_input_retry_count = <integer>
* The number of retries the Splunk Infrastructure Monitoring Data Streams modular input
* makes to the Infrastructure Monitoring SignalFlow API before stopping.
* Default: 3

sim_mod_input_enable_materialized_view = <boolean>
* Whether the Splunk Infrastructure Monitoring Data Streams modular input
* works in materialized view mode.
* If "1", the modular input works in materialized view mode.
* If "0", the modular input works in optimized view mode.
* Default: 1

sim_mod_input_store_to_metric_index = <boolean>
* Whether the Splunk Infrastructure Monitoring Data Streams modular input 
* stores the collected data in a metrics index.
* If "1", collected metrics data is stored in a metric index.
* If "0", collected metrics are stored in an events index.
* Default: 1

sim_mod_input_stop_mod_input_when_one_computation_fails = <boolean>
* Whether the Splunk Infrastructure Monitoring Data Streams modular input
* stops when a computation fails.
* If "1", the modular input stops when one computation fails.
* If "0", the modular input stops only when all computations fail.
* Default: 0

sim_api_signal_flow_use_sse = <boolean>
* Whether the add-on uses Server-Sent Events (SSE) transport to communicate 
* with the Infrastructure Monitoring SignalFlow API.
* If "1", the add-on uses SSE transport.
* If "0", the add-on uses Websocket transport call.
* Default: 0

sim_api_proxy_url = <string>
* This setting is used only in proxy-enabled environments to support proxy 
* through Infrastructure Monitoring SignalFlow API communication.
* The proxy URL (http(s)://<host>:port/) is to communicate with the Infrastructure Monitoring SignalFlow API.
* Proxy-based Infrastructure Monitoring SignalFlow API communication is supported 
* only in SSE transport (sim_api_signal_flow_use_sse = 1).

sim_search_timeout_seconds = <integer>
* This setting is used to define timeout of watchdog in signalflow 
* Default: 600

sim_flow_enable_watchdog = <boolean>
* This setting will make watchdog enable or disable in signalflow
* Default: True