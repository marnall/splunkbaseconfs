[ataportal]

python.version = <string>
* Specifies the Python version to use for this alert action
* Valid values: python3, python3.9, python3.13
* Default: python3

python.required = <string>
* Comma-separated list of Python versions this alert action supports
* Used by Splunk Cloud Platform 10.2+ to select the highest available version
* Example: 3.9, 3.13

param._cam = <value>
* CIM Actions / Adaptive Response Requirement

param.base_url = <string>
* Configure Portal URL

param.auth_token = <string>
* Configure Portal Token

param.psa_id = <string>
* Configure *your* Customer ID

param.search_query = <string>
* The search query string to send to ZTAP

param.search_earliest = <string>
* The earliest timestamp of the search window

param.search_latest = <string>
* The latest timestamp of the search window