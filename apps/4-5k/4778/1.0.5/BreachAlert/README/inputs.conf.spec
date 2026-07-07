[BreachAlert://default]

api_key = <key>
* API key requested from Skurio support
* support@skurio.com

app_key = 
* Application key, requested from api.skurio.com

folder_search = 
* Regex to match the folder name of alerts whose results should be retrieved
* If blank, all alerts are matched
* If used with alert_search, both matches must be true to retrieve the results

alert_search = 
* Regex to match the name of alerts whose results should be retrieved
* If blank, all alerts are matched
* If used with folder_search, both matches must be true to retrieve the results

override_range = 
* Date range to pull results on the next fetch
* Format: <start_date> <end_date>
* Start and end dates in yyyy-mm-dd format
* e.g. 2019-09-01 2019-10-01

passAuth = <username>
* User to run the script as.
* If you provide a username, the instance generates an auth token for that user and passes it to the script via stdin.
* The script requires splunk-system-user or equivalent in order to securely store API tokens