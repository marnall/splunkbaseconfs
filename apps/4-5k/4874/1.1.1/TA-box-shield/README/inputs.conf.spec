[box_shield_input://<name>]
box_account = The Box account to use for data collection.
start_time = The start time for data collection in "%Y-%m-%dT%H:%M:%S" format.
collection_interval = Time interval of input in seconds between 5 and 60. Default is 60.
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.