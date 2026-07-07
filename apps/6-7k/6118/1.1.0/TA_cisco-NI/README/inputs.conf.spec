[cisco_ni://<name>]
alert_type = Select the type of the input i.e. Anomalies or Advisories.
anomalies_category = Select the Category to filter anomalies data.
advisories_category = Select the Category to filter advisories data.
severity = Select the Severity to filter data.
global_account = Select the account for which you want to collect data.
time_range = Time range for last N hours. If 0 is specified, all events (from start of time) should be collected.

[cisco_ni]
python.version = Select which Python version to use. {default|python|python2|python3}