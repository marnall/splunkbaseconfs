@echo off
REM ============================================================================
REM Splunk UF Upgrade Force Retry Marker Reset Wrapper
REM ============================================================================
REM
REM Purpose:
REM   Runs reset_force_retry_marker.ps1 using PowerShell ExecutionPolicy Bypass.
REM
REM Use case:
REM   Enables an admin-controlled reset so the force retry helper can create
REM   another force_retry.flag during a future retry wave.
REM
REM ============================================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%reset_force_retry_marker.ps1 

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

exit /b %ERRORLEVEL%
