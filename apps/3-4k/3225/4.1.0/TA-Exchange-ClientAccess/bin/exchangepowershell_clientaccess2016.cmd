@ECHO OFF

SET SplunkApp=TA-Exchange-ClientAccess

GOTO ExchangeVersionOth

:ExchangeVersionOth
Powershell -command ". '%SPLUNK_HOME%\etc\apps\%SplunkApp%\bin\powershell\%2'"
goto:eof
