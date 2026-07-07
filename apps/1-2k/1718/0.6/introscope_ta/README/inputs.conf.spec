[introscope://<name>]
* Hostname and port from the instroscope server (port schould be the one from the web-api)
introscope_host = <value>

* Path from the metrics service (/introscope-web-services/services/MetricsDataService)
introscope_path = <value>

* Define the end of the time-frame your are requesting : (now - x minutes)
offset = <value>

* Define how often the app is asking for data (every x minutes)
polling_interval = <value>

* Username for the introscope http authentification 
username = <value>

* Password for the introscope http authentification 
password = <value>

* Regex from the agents you want to receive (same syntax as for introscope metric grouping in workstation or webview)
agentRegex = <value>

* Regex from the metrics  you want to receive (same syntax as for introscope metric grouping in workstation or webview)
metricRegex = <value>

* Granularity from the Data receive, like span=x seconds in Splunk
dataFrequency = <value>

* Indicate Splunk if the key used as key=value should be agent or metric name [metricName | agentName]
outputElement = <value>

* You must specify a regex, that is applied on the outputElement, so that everything or a part of it is used as key. Format is the same as for rex command, all fields found are concatenated with _ (Queues\|(?P<queue>test[^\|]*)\.L)
outputRegex = <value>

* is the template used to make the soap request send to introscope : $agentRegex,$metricRegex,$startTime,$endTime,$dataFrequency should be set as place older on the proper place
soapTemplate = <value>