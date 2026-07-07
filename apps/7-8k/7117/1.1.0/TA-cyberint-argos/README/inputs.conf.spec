[TA_cyberint_argos://<name>]
account = Specify the account credentials to be used for fetching data. Ensure that the chosen account has the necessary permissions.
client_name = Provide the company (client) name associated with your Cyberint instance.
environment = Indicate the Cyberint environment if you manage multiple environments (Please provide environments separated by commas). If not specified, data from all environments will be retrieved.
include_csv = Check to receive CSV attachments with additional data, enhancing the alert information.Defaults set to False
index = Select the destination index in Splunk where the fetched data will be stored. Defaults to the 'default' index. (Default: default)
instance_domain = Cyberint API URL on which the services run (i.e https://yourcompany.cyberint.io).
interval = Set the time interval for this data input in seconds. Defaults to 300 seconds (5 minutes). (Default: 300)
max_fetch = Limit the number of alerts fetched in each loop. Defaults to 100 alerts per loop. (Default: 100)
severities = Specify the severity of the alerts you're interested in. If none are selected, alerts of all severities will be fetched.
start_time = Choose the starting time frame for data retrieval. If modified, the app will reset and fetch data based on your new selection. If not set, the app will fetch data from the current time.
statuses = Choose the status of the alerts you wish to monitor. By default, alerts of all statuses ('Open', 'Acknowledged', 'Closed') will be fetched if none are selected.
types = Select specific types of threats you're interested in. If no type is selected, alerts of all types will be fetched.
