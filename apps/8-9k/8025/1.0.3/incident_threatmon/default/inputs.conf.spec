[threatmon_incidents://<stanza_name>]
* API based input for ThreatMon Incidents.

* api_url = <string>
  URL endpoint for ThreatMon API.

* api_key = <string>
  API Key (will be stored encrypted by Splunk).

* index = <string>
  Target Splunk index where events will be stored.

* interval = <int>
  Polling interval in seconds.

* sourcetype = <string>
  Sourcetype for indexed data.

* disabled = <bool>
  0 = enabled (default), 1 = disabled
