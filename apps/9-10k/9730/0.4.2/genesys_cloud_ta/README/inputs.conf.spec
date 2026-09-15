[actions_metrics://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[audit_query://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
max_poll_attempts = Maximum number of status checks (polls) performed for an audit query transaction before giving up. Increase for long-running queries; each attempt waits 'Poll interval (seconds)' between checks. (Default: 10)
poll_interval_seconds = Seconds to wait between status checks (polls) of the audit query transaction_id. Lower values respond faster but use more API calls; higher values reduce rate-limit pressure. (Default: 2)
start_date = Start date for data collection. Default: 7 days ago. Format: YYYY-MM-DD

[queue_observations://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[edges_trunks_metrics://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[edges_metrics://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[edges_phones://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[user_aggregates://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[conversations_metrics://<name>]
account = Account to use for this input.
direction = The direction of the communication (select at least one) (Default: inbound|outbound)
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
media_types = The session media type(s) to ingest (select at least one) (Default: callback|chat|cobrowse|email|internalmessage|message|screenshare|video|voice)

[conversations_details://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
start_date = Start date for data collection. Default: 7 days ago. Format: YYYY-MM-DD

[user_routing_status://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[status_page_metrics://<name>]
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
