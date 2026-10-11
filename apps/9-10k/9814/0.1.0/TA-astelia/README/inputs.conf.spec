[astelia_audit_logs://<name>]
account = The organization configured on the Configuration page.
index = (Default: default)
interval = Seconds between polls. 60-300 is typical for a near-real-time feed; each poll drains every new event since the stored checkpoint. (Default: 300)
page_size = Events fetched per API request (1-1000). (Default: 500)
start_from = Optional. Only used on the first poll: an RFC 3339 UTC timestamp (e.g. 2026-09-01T00:00:00Z) to backfill from. Leave empty to start from the oldest available event (Astelia keeps 12 months).
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[astelia_connectors://<name>]
account = The organization configured on the Configuration page.
index = (Default: default)
interval = Seconds between polls. Every poll writes one event per connector with its current health, so the newest event per connector is its state. (Default: 300)
stale_after_hours = How long an integration connector may go without a successful collection before it is reported stale (1-168). Set it to your collection cadence; agent connectors use fixed thresholds. (Default: 24)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
