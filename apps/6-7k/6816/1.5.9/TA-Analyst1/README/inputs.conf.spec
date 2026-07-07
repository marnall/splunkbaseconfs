# Base stanza - system defaults (not user-configurable)
[analyst1_indicator]
start_by_shell = Whether to start the script via shell
python.version = Python version to use (python3)
interval = Heartbeat interval in seconds
refresh_factor = Number of intervals between full refreshes

# Instance stanza - user-configurable per-input settings
[analyst1_indicator://<name>]
global_account = The account to use for API authentication
indicator_types = Select the type of indicators to collect
sensor_id = The indicators of the mentioned Sensor ID will be collected
