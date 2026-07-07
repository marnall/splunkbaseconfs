# Copyright (C) 2017 Recorded Future, Inc.
#
# This file contains possible attributes/value pairs used by the app.
# 
[logging]
log_level = <string>
    * The log level as a string: warning, info, debug
    * Defaults to info

[network]
proxy = <string>
    * A proxy, ex http://proxy.example.com:8080
    * Defaults to no proxy

[domain_risk_list]
enabled = <bool>
    * Whether to use this risk list or not.
    * Defaults to true
interval = <int>
    * The interval in seconds between updates of the list.
    * Defaults to 3600
max_entries = <int>
    * Tune the threshold to produce approximately this many entries.
    * Defaults to 25000.

[hash_risk_list]
enabled = <bool>
    * Whether to use this risk list or not.
    * Defaults to true
interval = <int>
    * The interval in seconds between updates of the list.
    * Defaults to 86400
max_entries = <int>
    * Tune the threshold to produce approximately this many entries.
    * Defaults to 25000.

[ip_risk_list]
enabled = <bool>
    * Whether to use this risk list or not.
    * Defaults to true
interval = <int>
    * The interval in seconds between updates of the list.
    * Defaults to 3600
max_entries = <int>
    * Tune the threshold to produce approximately this many entries.
    * Defaults to 25000.

[vulnerability_risk_list]
enabled = <bool>
    * Whether to use this risk list or not.
    * Defaults to true
interval = <int>
    * The interval in seconds between updates of the list.
    * Defaults to 86400
max_entries = <int>
    * Tune the threshold to produce approximately this many entries.
    * Defaults to 25000.
