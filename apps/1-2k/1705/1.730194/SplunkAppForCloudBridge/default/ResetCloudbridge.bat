@echo This command will stop splunk and reset your CloudBridge app installation (erasing all collected data.) 
pause
"%ProgramFiles%\Splunk\bin\splunk.exe" stop 
"%ProgramFiles%\Splunk\bin\splunk.exe" clean eventdata -index cloudbridge
del "%ProgramFiles%\Splunk\etc\apps\SplunkAppForCloudBridge\log\*.*"
del "%ProgramFiles%\Splunk\etc\apps\SplunkAppForCloudBridge\lookups\CloudBridgeAppName.csv"
del "%ProgramFiles%\Splunk\etc\apps\SplunkAppForCloudBridge\lookups\CloudBridgeObserver.csv"
"%ProgramFiles%\Splunk\bin\splunk.exe" start

