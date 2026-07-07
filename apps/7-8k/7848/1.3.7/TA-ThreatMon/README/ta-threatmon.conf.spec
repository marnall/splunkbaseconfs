# ta-threatmon.conf.spec
# Configuration specification for ThreatMon app

[main]
* Use this stanza to configure main ThreatMon settings.

username = <string>
* Username for ThreatMon API authentication.
* Required.

password = <string>
* Password for ThreatMon API authentication.
* Required.

verify_ssl = <boolean>
* Whether to verify SSL certificates when connecting to ThreatMon API.
* Default: true

log_level = <integer>
* Logging level for the collector.
* Valid values: 10 (DEBUG), 20 (INFO), 30 (WARNING), 40 (ERROR), 50 (CRITICAL)
* Default: 30

update_interval = <integer>
* Interval in seconds between IOC collection runs.
* Minimum: 300 (5 minutes)
* Default: 3600

index = <string>
* Splunk index to store collected IOCs.
* Default: threat_intel

[default]
* Use this stanza to set default values for all stanzas below.

[threatmon_ioc_feed]
* Use this stanza to configure the ThreatMon IOC feed collector.

collection_id = <string>
* ThreatMon collection ID to fetch IOCs from.
* Required.

log_level = <integer>
* Logging level for the collector.
* Valid values: 10 (DEBUG), 20 (INFO), 30 (WARNING), 40 (ERROR), 50 (CRITICAL)
* Default: 30

update_interval = <integer>
* Interval in seconds between IOC collection runs.
* Minimum: 300 (5 minutes)
* Default: 3600

index = <string>
* Splunk index to store collected IOCs.
* Default: threat_intel

sourcetype = <string>
* Sourcetype for collected IOCs.
* Default: threatmon:ioc

disabled = <boolean>
* Whether the input is disabled.
* Default: false 