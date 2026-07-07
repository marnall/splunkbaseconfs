[flashpoint_intelligence://<name>]
global_account = <string>
* Select the account for which you want to collect data.
* Example: user1

type = <string>
* Type of data either Report or Indicators or CVE
* Example: Report

index = <string>
* Index name. Index to which you want to send data. It refers to index name in indexes.conf.
* Example: index_flashpoint

interval = <integer>
* Interval in seconds. The input will be triggered at every interval amount of time and fetch the data from Flashpoint-intel endpoint.
* Minimum interval allowed is 1800 seconds i.e. 30 minutes.
* Example: 1800

start_date = <string>
* Date and time from which you want to fetch events. Enter the value in 'YYYY-MM-DDThh:mm:ss' format e.g. 2013-04-17T09:12:36. TimeZone will be set to UTC TimeZone.

collect_plain_text_password = <boolean> 0/1
* Should plain text password be collected for compromised creds events?
is_fresh = <boolean> 0/1
* Should the compromised credentials being fetched be fresh?
password_complexity_has_lowercase = <boolean> 0/1
* Should the password include at least one lowercase letter?
password_complexity_has_number = <boolean> 0/1
* Should the password include at least one numeric digit?
password_complexity_has_symbol = <boolean> 0/1
* Should the password include at least one special symbol?
collect_enrichments = <boolean> 0/1
* Should the ransomware events include enrichments data?
password_complexity_has_uppercase = <boolean> 0/1
* Should the password include at least one uppercase letter?
password_complexity_length = <text>
* Minimum length of the compromised credentials.

python.version = {default|python|python2|python3}
* For Splunk 8.0.x and Python scripts only, selects which Python version to use.
* Either "default" or "python" select the system-wide default Python version.
* Optional.
* Default: python3