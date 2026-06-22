:: $SPLUNK_HOME\etc\apps\subzero\bin\wrapper.bat
@ECHO OFF
SET ThisScriptsDirectory=%~dp0
SET PowerShellScriptPath=%ThisScriptsDirectory%\buckets.ps1
:: Call PowerShell, bypass execution policy for the current session, and run the script
Powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%PowerShellScriptPath%'"