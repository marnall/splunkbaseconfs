[cwaap_audit://<name>]
account_id = Cloud portal: Accounts > API Keys > Account ID Details > Application Protection ID (a UUID such as 12345678-abcd-4ef0-9876-0123456789ab). Sent as the 'context' header. The 24-character internal Account ID is not accepted by the API (HTTP 401).
api_key = API key created under Accounts > API Keys. Stored encrypted.
index = (Default: default)
initial_lookback_minutes = History collected on the FIRST run only; later runs resume from the checkpoint. 1440 = one day, 43200 = 30 days (for example at cut-over from the legacy Radware CWAF Event Collector). The API serves at most 100 days (144000). 0 = start from now. (Default: 1440)
interval = Polling interval in seconds. 300 is recommended; the audit log is low volume. (Default: 300)
max_backfill_minutes = After an outage the input catches up from its checkpoint, at most this far back (default 1440 = one day). The first run always covers the full initial look-back. (Default: 1440)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
