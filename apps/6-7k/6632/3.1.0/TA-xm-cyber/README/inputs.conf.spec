[audit_trail://<name>]
account = Account to use for this input.
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 300
time_id = <string> Time Range of the data in format (<yyyy-mm-dd>T<hh:mm:ss>.<sss>Z).

[all_entities://<name>]
account = Account to use for this input.
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 86400
ingest_chokepoints = Ingest chokepoint stats

[sensors://<name>]
account = Account to use for this input.
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 300

[findings_exposures://<name>]
account = Account to use for this input.
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 86400

[security_risk_score://<name>]
account = Account to use for this input.
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 86400
time_id = Time Range of the report. Default: timeAgo_days_7
ingest_scenarios = Ingest riskscore related data for all scenarios individually.

[scenario://<name>]
account = Account to use for this input.
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 86400

[vrm_data://<name>]
account = Account to use for this input.
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 86400
