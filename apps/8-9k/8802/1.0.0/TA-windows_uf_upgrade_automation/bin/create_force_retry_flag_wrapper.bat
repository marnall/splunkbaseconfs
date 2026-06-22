@echo off
REM ============================================================================
REM Splunk UF Upgrade Force Retry Helper Wrapper
REM ============================================================================
REM
REM Purpose:
REM   This wrapper is executed by Splunk as a scripted input.
REM   It launches the PowerShell helper script using ExecutionPolicy Bypass.
REM
REM Why this exists:
REM   Splunk scripted inputs can call .bat files reliably.
REM   The .bat wrapper ensures the PowerShell script runs with:
REM     - No user/system profile loading
REM     - Execution policy bypass for this process only
REM     - Proper path resolution relative to this app's bin directory
REM
REM Expected script:
REM   create_force_retry_flag.ps1
REM
REM ============================================================================

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%create_force_retry_flag.ps1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

exit /b %ERRORLEVEL%
