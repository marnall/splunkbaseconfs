# inputs.conf.spec
# Configuration specification for ThreatMon inputs

[threatmon_ioc_feed://<name>]
* Use this stanza to configure ThreatMon IOC feed collection inputs.

disabled = <boolean>
* Whether this input is disabled.
* Default: false

interval = <integer>
* How often to run the IOC collection (in seconds).
* Minimum: 300 (5 minutes)
* Default: 600

polling_interval = <integer>
* Polling interval in seconds for IOC collection.
* Minimum: 300 (5 minutes)
* Default: 600

username = <string>
* ThreatMon username for API authentication.
* Optional if configured in setup.

password = <string>
* ThreatMon password for API authentication.
* Optional if configured in setup.

collection_id = <string>
* ThreatMon collection ID to fetch IOCs from.
* Optional if configured in setup.

verify_ssl = <boolean>
* Whether to verify SSL certificates.
* Default: true

log_level = <integer>
* Logging level.
* Valid values: 10, 20, 30, 40, 50
* Default: 30

python.version = <string>
* Python version to use.
* Default: python3

start_by_shell = <boolean>
* Whether to start by shell.
* Default: false

sourcetype = <string>
* Sourcetype for events.
* Default: threatmon:ioc

index = <string>
* Index to store events.
* Default: threat_intel 