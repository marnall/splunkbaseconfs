# This file contains possible settings you can use to configure metric anomaly detection.
# Use anomaly detection to identify trends and outliers in KPI search results that might
# indicate an issue with your system.
#
# There is a mad.conf in $SPLUNK_HOME/etc/apps/SA-ITSI-MetricAD/default. To set custom
# configurations, place a mad.conf in $SPLUNK_HOME/etc/apps/SA-ITSI-MetricAD/local.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

# To learn more about metric anomaly detection, see
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/Enableanomalydetection

# In most situations, the default values specified in mad.conf should work as-is.
# Modifying this file can result in negative changes to anomaly detection accuracy.
# Do NOT remove any stanzas or settings in the configuration file.

# For <duration> format, this configuration file accepts the following units:
#   * ms => milliseconds
#   * s, sec, secs, second, seconds => second
#   * m, min, mins, minute, minutes => minute
#   * h, hr, hrs, hour, hours => hour
#   * d, day, days => day

[service]

unbounded_buffer_size = <duration>
* The size of the data buffer used in batch mode.
* For example, "4d" stores a maximum of 4 days of data.
* Default: 400d

kvstore_connect_interval = <duration>
* How often to retry connecting to the KV store when the connection is lost.
* Default: 30s

rest_ssl_permissive_trustmanager = <boolean>
* Whether to enable PermissiveX509TrustManager with HTTPS connection to Splunk REST API.
* Do not modify this setting unless Splunk is not running in HTTPS mode.
* Default: true

rest_ssl_permissive_hostnameverifier = <boolean>
* Whether hostname verification is strict or permissive.
* If set to "true", hostname verification is permissive.
* If set to "false", hostname verification is strict.
* This setting can be disabled when the Splunk certificate is not self-signed.
* Default: true

trending_bounded_buffer_size = <duration>
* The size of the data buffer for the trending algorithm in real-time mode.
* This setting MUST be larger than the value of the 'training_period'
  setting in the [trending] stanza.
* Default: 15d

cohesive_bounded_rt_buffer_size = <duration>
* The size of the real-time data buffer for the cohesive algorithm in real-time mode.
* Default: 12h

cohesive_bounded_backfill_buffer_size = <duration>
* The size of the backfill data buffer for the cohesive algorithm in real-time mode.
* Default: 25h

[trending]
* Use this stanza to configure the 'mad' command for the trending algorithm.

periods.days = <positive integer>
* How many days to look back for normal patterns in the data.
* Must be a value greater than zero.
* Default: 6

periods.weeks = <integer>
* How many weeks to look back for normal patterns in the data.
* Must be a value greater than or equal to zero.
* Default: 2

window_size = <positive integer>
* How many data points to use to construct an analysis window.
* Must be a value greater than 1.
* Default: 60

step_size = <positive integer>
* The offset size of two consecutive analysis window.
* Must be a value greater than 0.
* Default: 1

training_period = <duration>
* The amount of time used to train the algorithm.
* Must be a value greater than 1.
* Default: 7d

max_NA_ratio = <float>
* The maximum possible ratio of NaN (undefined) data points.
* Must be a decimal between 0.0 and 1.0.
* Default: 0.5

na_rm = <boolean>
* Whether or not to remove NaN (undefined) data points.
* If set to "true", NaN data points are removed.
* Default: true

Nkeep = <duration>
* How much data to keep in memory for analysis.
* Default: 50h

Naccum = <float>
* The accumulation score for anomaly alerting.
* Must be a value greater than zero.
* Default: 35.0

[trending:limits]
* Use this stanza to configure the 'naccum' command for trending algorithm.

Naccum_max = <float>
* The maximum accumulation score to use for detecting anomalies.
* This value MUST be larger than the 'Naccum' setting in the [trending] stanza.
* Default: 50.0

Naccum_min = <float>
* The minimum accumulation score to use for detecting anomalies.
* This value MUST be smaller than the 'Naccum' in the [trending] stanza.
* Default: 30.0

sensitivity_max = <integer>
* The number of sensitivity levels.
* Must be a value greater than 1.
* Default: 10

[cohesive]
* Use this stanza to configure the 'mad' command for the cohesive algorithm.

window_size = <positive integer>
* How many data points to use to construct an analysis window.
* Must be a value greater than 1.
* Default: 60

step_size = <positive integer>
* The offset size of two consecutive analysis windows.
* Must be a value greater than 0.
* Default: 1

training_period = <duration>
* The amount of time used to train the algorithm.
* Must be a value greater than 1.
* Default: 7d

max_NA_ratio = <float>
* The maximum possible ratio of NaN (undefined) data points.
* Must be a decimal between 0.0 and 1.0.
* Default: 0.5

na_rm = <boolean>
* Whether or not to remove NaN (undefined) data points.
* If set to "true", NaN data points are removed.
* Default: true

Nkeep = <duration>
* How much data to keep in memory for analysis.
* Default: 10h

Naccum = <float>
* The accumulation score for anomaly alerting.
* Must be a number greater than zero.
* Default: 35.0

norm_Ntrend = <integer>
* The window of moving median for normalization of incoming data.
* Default: 10

norm_maxNAratio = <float>
* The maximum ratio of NaN data points allowed in the dataset for normalization of incoming data.
* Must be a decimal between 0.0 and 1.0.
* Default: 0.5

norm_trendOnly = <boolean>
* Whether to use only the trend of the data for normalization.
* Default: false

norm_MAratio = 0.8
* The moving average ratio of the normalization window.
* Must be a decimal between 0.0 and 1.0.
* Default: 0.8

norm_NArm = <boolean>
* Whether to remove NaN (undefined) data points for normalization.
* Default: false

norm_Nwindow = <integer>
* The size, in data points, of the normalization buffer.
* Default: 10080

norm_Nshift = <integer>
* The interval at which the normalization constants are recalculated.
* After receiving this many data points, the constants are recalculated.
* Default: 1440

norm_Ninit = <integer>
* The number of data points needed to calculate the normalization constants.
* Default: 30

norm_batch = <boolean>
* Deprecated option
* Enable/disable batch normalization

metrics_maximum = <integer>
* The maximum number of metrics that can be analyzed for the cohesive algorithm.
* Default: 30

[cohesive:limits]
* Use this stanza to configure the 'naccum' command for the cohesive algorithm.

Naccum_max = <float>
* The maximum accumulation score that can be used for detecting anomalies.
* This value MUST be larger than the 'Naccum' setting in the [cohesive] stanza.
* Default: 50.0

Naccum_min = <float>
* The minimum accumulation score that can be used for detecting anomalies.
* This value MUST be smaller than the 'Naccum' setting in the [cohesive] stanza.
* Default: 30.0

sensitivity_max = <integer>
* The number of sensitivity levels.
* Must be a value greater than 1.
* Default: 10

[logging]
* Use this stanza to configure logging.

metric_registry = <boolean>
* Enable logging metrics of the 'mad' command.
* CAUTION: Enabling this setting will have a significant performance impact.
* Default: false

[alerting]
* Use this stanza to configure external HTTP endpoint connections for posting alerts.

rest_ssl_permissive_trustmanager = <boolean>
* Whether to enable PermissiveX509TrustManager with HTTPS connection to the Splunk REST API.
* Default: true

rest_ssl_permissive_hostnameverifier = <boolean>
* Whether to be strict or permissive in hostname verification.
* If set to "true", hostname verification is permissive.
* If set to "false", hostname verification is strict.
* Default: true

max_http_connection = 100
* How many simultaneous HTTP connections are allowed.
* Default: 100