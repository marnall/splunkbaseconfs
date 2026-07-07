[threatq_indicators://<name>]
export_id = The ThreatQ export ID to use for data collection
export_token = The ThreatQ export token to use for data collection
export_hash = The ThreatQ export hash to use for data collection
threshold_score = Minimum threshold score for collecting indicators. Indicators with score greater than equal to provided score will only be collected
indicator_status = Indicator status for collecting indicators. Indicators with provided status will only be collected
checkbox_for_index = If checkbox is selected then indicator data will be indexed.
pull_all_iocs = Enabling this checkbox will force pull all data on input edit. On input creation it is mandatory to enable this checkbox before saving. Enable this when changing status or score value for any input.
response_page_size = Defines the number of indicators to retrieve per API request.
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.

[threatq_indicators]
export_id = The ThreatQ export ID to use for data collection
export_token = The ThreatQ export token to use for data collection
export_hash = The ThreatQ export hash to use for data collection
threshold_score = Minimum threshold score for collecting indicators. Indicators with score greater than equal to provided score will only be collected
indicator_status = Indicator status for collecting indicators. Indicators with provided status will only be collected
checkbox_for_index = If checkbox is selected then indicator data will be indexed.
pull_all_iocs = Enabling this checkbox will force pull all data on input edit. On input creation it is mandatory to enable this checkbox before saving. Enable this when changing status or score value for any input.
response_page_size = Defines the number of indicators to retrieve per API request.
python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.