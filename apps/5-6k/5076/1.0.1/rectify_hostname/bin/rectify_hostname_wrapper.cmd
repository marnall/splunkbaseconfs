REM store path of this bin folder
set "BINPATH=%~dp0"
REM set "SPLUNK_HOME=C:\Program Files\SplunkUniversalForwarder"

%SystemRoot%\system32\WindowsPowerShell\v1.0\Powershell -ExecutionPolicy ByPass -File "%BINPATH%rectify_hostname.ps1" -splunkHome "%SPLUNK_HOME%"
