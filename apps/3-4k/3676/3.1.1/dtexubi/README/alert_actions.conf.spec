# dtex_custom_alerts configurations

[dtex_custom_alerts]

param.category = <string>
* select the category name for which the alert is generated

param.risk_score = <float>
* define risk_score for the category

param.severity = <string>
* define severity of alert

param.time = <date>
* define the time field which contain time value 
 
param.username = <string>
* define the username field which contain user name value 

param.triggered_at = <$trigger_time$>
* get the triggered time of alert

python.version = {default|python|python2|python3}
* Set the default python version for the Alert Action.

* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: not set; uses the system-wide Python version.