[effective-configuration-add-on://configuration]
addOnTimeout = <positive integer>
* The timeout in seconds for the whole Effective Configuration Add-On execution.
* If met, TA will be stopped and EC won't be sent until Splunk restart.
* Default: 300

splunkCommandsExecTimeout = <positive integer>
* The timeout in seconds for each Splunk command executed by the EC Add-On.
* It's used especially for Btool, but can be used for other CLI commands as well.
* Default: 10

jitterMaxTime = <positive integer>
* The maximum time in seconds to wait before the next attempt of sending EC to Agent Manager.
* Can be used to reduce load on the server, especially if the server is under heavy load.
* It should be configured together with 'jitterMinTimeInSecs', 'addOnTimeoutInSecs' (from this file)
* and 'maxConcurrentDownloads' from serverclass.conf on the Agent Manager.
* Default: 15

jitterMinTime = <positive integer>
* The minimum time in seconds required to wait before the next attempt of sending EC to Agent Manager.
* Can be used to reduce load on the server, especially if the server is under heavy load.
* It should be configured together with 'jitterMaxTimeInSecs', 'addOnTimeoutInSecs' (from this file)
* and 'maxConcurrentDownloads' from serverclass.conf on the Agent Manager.
* Default: 1

retriesCount = <positive integer>
* The number of retry attempts for HTTP requests to Agent Manager server.
* Must be greater than or equal to 0.
* Default: 6

retryDefaultWaitTime = <positive integer>
* The default wait time in seconds between retry attempts.
* Must be greater than or equal to 0.
* Default: 5

retryMaxWaitTime = <positive integer>
* The maximum wait time in seconds between retry attempts.
* Must be greater than or equal to 'retryDefaultWaitTime'.
* Default: 60
