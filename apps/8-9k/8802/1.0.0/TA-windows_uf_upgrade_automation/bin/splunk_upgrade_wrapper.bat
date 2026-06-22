@echo off
REM Wrapper to run the PowerShell script from Splunk
powershell.exe -ExecutionPolicy Bypass -File "%~dp0\splunk_windows_upgrade_setup.ps1"
