[ti-cisco-vuln://<name>]

auth_url = <string>
* This is the base Cisco OAuth2.0 Auth URL
* It must be a secure URL (I.e. Start with https://)
* Default: https://cloudsso.cisco.com/as/token.oauth2

auth_client_id = <string>
* This is your Cisco API Client ID

auth_client_secret = <string>
* This is your Cisco API Client Secret

advisories_url = <string>
* This is the base Cisco Security Advisories URL
* It must be a secure URL (I.e. Start with https://)
* Default: https://api.cisco.com/security/advisories

advisories_window = <int>
* This is "look back" window, in days, for quering the advisories
* In code, this will be used to calculate the number of days back to look at
* Therefore a value of 1 would mean the window would be today and yesterday
* Default: 6

advisories_summary_plain = <0|1>
* If set to True (True, true or 1) a plain text version of the HTML summary field will be created
* This will marginally increase the event size, but makes working with the data a LOT easier!
* Default: 0

advisories_type = <string>
* Experimental
* Use to switch the input between, all, ios, etc...
* Default: all

interval = <int|cron>
* The time interval for running the script

debug = <0|1>
* Used to enable debug logging
* CAUTION: This will log sensitive API Keys
