@ECHO OFF

set SplunkApp=SecKit_TA_idm_windows

%SystemRoot%\system32\WindowsPowerShell\v1.0\powershell.exe -executionPolicy RemoteSigned -command ". '%SPLUNK_HOME%\etc\apps\%SplunkApp%\bin\powershell\%1'"
