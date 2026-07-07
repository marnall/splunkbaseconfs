# This file contains possible settings you can use to configure SIM Modular inputs.
#
# There is an inputs.conf in $SPLUNK_HOME/etc/apps/splunk_ta_sim/default To set custom
# configurations, place an inputs.conf in $SPLUNK_HOME/etc/apps/splunk_ta_sim/local.
# You must restart SIM Add-on to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# https://docs.splunk.com/Documentation/SIMAddon/1.0.0/Install/ModInput

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#   * You can also define global settings outside of any stanza, at the top of
#     the file.
#   * Each conf file should have at most one default stanza. If there are
#     multiple default stanzas, settings are combined. In the case of
#     multiple definitions of the same setting, the last definition in the
#     file wins.
#   * If a setting is defined at both the global level and in a specific
#     stanza, the value in the specific stanza takes precedence.

[sim_modular_input://<name>]
* Streams Infrastructure Monitoring metrics data into Splunk using SignalFlow Programs.

org_id = <string>
* The Infrastructure Monitoring Organization ID used to fetch the metrics data into Splunk.
* When provided, the command fetch the results from the provided sim organization account.
* When not provided, the command fetch the results from the default sim organization account.
* There is no default.

signal_flow_programs = <string>
* The Signal Flow Programs used to stream Splunk Infrastructure Monitoring metrics data into Splunk.
* This setting is required
* There is no default.

additional_meta_data_flag = <boolean>
* When "true", the metric stream results contains full metadata.
* Default: false

sim_modinput_restart_interval_seconds = <integer>
* This setting will exit the ModularInput script if the data is stucked longer than the configured time.
* Need to be configured in seconds.
* Default: 3600

metric_resolution = <integer>
* The metric resolution of stream results.
* Default: -1

sim_max_delay = <integer>
* Max Delay is a parameter of Analytics jobs. By default, the ideal Max Delay is automatically computed based on the historical delay of the data in the query.
* A statically configured Max Delay allows the customer to prevent Analytics from waiting for delayed data
* Need to be configured in miliseconds.
* Default: -1

log_level = <DEBUG|INFO|WARN|ERROR>
* The logging level of the Modular Input.
* DEFAULT: INFO

log_format = <string>
* Format of the log
* DEFAULT: %(asctime)s, Level=%(levelname)s, Pid=%(process)s, RequestId=%(request_id)s, Logger=%(name)s, File=%(filename)s, Line=%(lineno)s, %(message)s
