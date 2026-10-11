[cisodium_feed://<name>]
account = The Cisodium tenant to read from (Configuration → Cisodium accounts).
feed = What to copy. Every change to a record arrives as a new event with the record's full state. (Default: incidents)
index = (Default: default)
interval = How often to ask Cisodium for changes, in seconds (60 to 86400). (Default: 300)
page_size = Records per request (1 to 1000). (Default: 500)
start_date = Optional. Only records changed on or after this date (UTC), e.g. 2026-01-01. Leave empty to copy the whole history on the first run. Used once; later runs continue from where the last one stopped.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
