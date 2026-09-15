[phishing_events://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
lookback_hours = How far behind the newest event seen to re-query each run, to catch events written late. occurredAt is event time, not ingest time, so an event can arrive carrying an older timestamp. 1 is a sane default. Raising this value re-indexes the events in the slice it newly covers, once: the checkpoint only remembers ids inside the old window, so events between the old and new horizon are seen as unread. Measured at 70 duplicates going 24h to 168h on a 1,200-event tenant. It is duplicates rather than gaps, it happens only on the run after the change, and `| dedup` resolves it -- but widen deliberately, not experimentally. (Default: 1)
page_size = Rows per API request. Max 10000. (Default: 1000)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[audit_events://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
lookback_hours = How far behind the newest event seen to re-query each run, so an event written with an older timestamp is still picked up: a timestamp is assigned when an event is logged, not when its transaction commits, so a row can become visible behind the point already read. Event ids inside this window are remembered in the checkpoint to suppress duplicates; above 100000 ids the oldest are dropped and a warning is logged, after which events in the older part of the window may be indexed twice. Raise this only as far as your tenant's volume allows. Set it to 0 only if you accept losing a late-committed row; the input then resumes from the stored cursor exactly, re-reading nothing. Raising this value re-indexes the events in the slice it newly covers, once: the checkpoint only remembers ids inside the old window, so events between the old and new horizon are seen as unread. Measured at 70 duplicates going 24h to 168h on a 1,200-event tenant. It is duplicates rather than gaps, it happens only on the run after the change, and `| dedup` resolves it -- but widen deliberately, not experimentally. (Default: 1)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[training_state://<name>]
account = Account to use for this input.
index = (Default: default)
interval = Time interval of the data input, in seconds. This is also the resolution of _time on these events: each change is stamped with the moment this input observed it, so the interval bounds how stale that observation can be. (Default: 3600)
max_tracked = Above this many (user, training) pairs the change-detection map is dropped and every row is emitted each run, to keep the checkpoint within a KV-store document. Capped at 100000: each tracked pair costs about 83 bytes in the checkpoint document, so a MongoDB document's 16MB limit is reached near 150000 — and a checkpoint that fails to save leaves the input re-emitting every row forever. (Default: 50000)
page_size = Rows per API request. Server maximum is 5000. (Default: 1000)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[ransomleak_risk://<name>]
account = Account to use for this input. Its API token must carry the 'integration' scope — the scope the Grafana query endpoint is guarded by, and NOT one of the scopes the Phishing Events, Audit Events or Training State inputs need. A token minted for those returns 403 here.
channel = Optional. Applies to the phishing click/report rate metrics only, and is ignored by every other metric. Leave blank for the server default (email).
index = (Default: default)
interval = Time interval of the data input, in seconds. Every metric buckets by UTC day, so polling faster than the day moves gains nothing except a fresher value for the current, partial day; the interval is what bounds how stale that value may be. (Default: 3600)
lookback_days = How many days of history each poll asks for, ending at the current instant. A bucket is re-indexed only when its value changes, so a wide window costs one query per metric rather than repeated events — but the server rejects a daily series longer than 1000 days, which is why 999 is the ceiling. (Default: 30)
metrics = Which metrics this input collects. The whole catalogue is offered here and on the Programme Metrics input; the split between the two is only a default, so one input can collect everything if you prefer. Each selected metric is one request per interval. (Default: human_risk_score,assignments_overdue,overdue_users)
team = Optional. Restrict every metric to one team by name. The literal 'Unassigned' selects users with no team. Leave blank for the whole tenant.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[ransomleak_metrics://<name>]
account = Account to use for this input. Its API token must carry the 'integration' scope — the scope the Grafana query endpoint is guarded by, and NOT one of the scopes the Phishing Events, Audit Events or Training State inputs need. A token minted for those returns 403 here.
channel = Optional. Applies to the phishing click/report rate metrics only, and is ignored by every other metric. Leave blank for the server default (email).
index = (Default: default)
interval = Time interval of the data input, in seconds. Longer than the Risk Posture input's by default: these metrics are reporting-grade rather than alerting-grade, they bucket by UTC day, and they are the heavier queries against your tenant database. (Default: 7200)
lookback_days = How many days of history each poll asks for, ending at the current instant. A bucket is re-indexed only when its value changes, so a wide window costs one query per metric rather than repeated events — but the server rejects a daily series longer than 1000 days, which is why 999 is the ceiling. (Default: 30)
metrics = Which metrics this input collects. The whole catalogue is offered here and on the Risk Posture input; the split between the two is only a default, so one input can collect everything if you prefer. Each selected metric is one request per interval. (Default: training_completion_rate,phishing_click_rate,phishing_report_rate,assignments_by_category,auto_assigned_via_grafana)
team = Optional. Restrict every metric to one team by name. The literal 'Unassigned' selects users with no team. Leave blank for the whole tenant.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
