[securityonion_alerts://<name>]
* Security Onion alerts modular input

interval = <value>
* How often to run the modular input, in seconds
* Required

search_window = <value>
* How far back in time to pull alerts from (in minutes)
* Defaults to 5
* Optional

event_limit = <value>
* Maximum number of events to retrieve per run
* Defaults to 400
* Optional

disabled = <value>
* Whether the input is disabled
* Defaults to 0 (enabled)