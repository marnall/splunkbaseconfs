[rogue_ap://<name>]
type = honeypot (honeypots) / lan (wired rogue) / others / spoof, default is others
duration = 1d / 1h, default is 1d
limit = max number of results, default = 100

[audit_log://<name>]
duration = 
limit = 

[active_client_events://<name>]
filter_by_events = 
duration = 1d / 1h, default is 1d
limit = max number of results, default = 100

[marvis_events://<name>]
duration = for hour specify 10m,1h, 2h, for seconds specify 60, 3600. for days 1d,2d etc. End time will be always the current time and start time will be calculated on the basis of duration
acked = whether the events are acknowledged, all / true / false, default is false
resolved = whether the resolved, all / true / false, default is all
limit = maximum number of records to be retrieved.

[system_events://<name>]
filter_events = Helps to filter  the events that will be pushed to splunk. If you select All then all the events are  selected
duration = for hour specify 10m,1h, 2h, for seconds specify 60, 3600. for days 1d,2d etc. End time will be always the current time and start time will be calculated on the basis of duration
limit = maximum number of record to be retrieved.