@echo off

REM // ########################################################################################
REM // ##
REM // ## SPLUNK_TA_ARI_WIN Edge Discovery
REM // ##
REM // ## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
REM // ## Splunk Software Licence and Support Agreement
REM // ##
REM // ########################################################################################

setlocal enabledelayedexpansion

REM Set current date and time
for /f "tokens=1,2*" %%T in ('wmic os get LocalDateTime 2^>nul ^| findstr /v "LocalDateTime" ^| findstr /R "."') do set dt=%%T
set /a offsetHours=(%dt:~22,5%)/(60)
if !offsetHours! LSS 10 (
    set offsetHours=0%offsetHours%
)
set /a offsetMins=(%dt:~22,5%)%%(60)
if !offsetMins! LSS 10 (
    set offsetMins=0%offsetMins%
)
set date_time=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%T%dt:~8,2%:%dt:~10,2%:%dt:~12,2%%dt:~21,1%%offsetHours%%offsetMins%

quser 2>nul >nul
IF %ERRORLEVEL% EQU 0 (
    for /f "delims=," %%A in ('quser') do (
        set row=%%A

        if not !headerRowPrinted! == true (
            set "headerRowPrinted=true"

            call :find_position "!row!" "USERNAME" USER_START
            call :find_position "!row!" "SESSIONNAME" SESSION_START
            call :find_position "!row!" "STATE" STATE_START
            call :find_position "!row!" "IDLE" IDLE_START
            call :find_position "!row!" "LOGON" LOGON_START

            set /a USER_LENGTH=!SESSION_START!-!USER_START!
            set /a STATE_LENGTH=!IDLE_START!-!STATE_START!
            set /a LOGON_LENGTH=30
        ) else (
            call set "name=%%row:~!USER_START!,!USER_LENGTH!%%"
            call set "status=%%row:~!STATE_START!,!STATE_LENGTH!%%"
            call set "logon=%%row:~!LOGON_START!,!LOGON_LENGTH!%%"

            call :trim name !name!
            call :trim status !status!
            call :trim logon !logon!

            if not "!name!"=="" (
                set output=!date_time! ari_nt_host=%COMPUTERNAME% ari_user_id="!name!"
                if not "!status!"=="" (set output=!output! account_active="!status!")
                if not "!logon!"=="" (set output=!output! last_logon="!logon!")

                echo !output!
            )
        )
    )
)

endlocal
exit /b

:trim
setLocal
set Params=%*
for /f "tokens=1*" %%a in ("!Params!") do endlocal & set %1=%%b
exit /b

:find_position
setlocal

rem Get search string length
set "search_str=%~2"
set /a search_str_length=0
:calculate_length
set "sub_str=!search_str:~%search_str_length%!"
if "!sub_str!"=="" goto :found_length
set /a search_str_length+=1
goto :calculate_length
:found_length

rem Get column index
set "header=%~1"
set /a start_index=0
:loop
set sub_str=!header:~%start_index%,%search_str_length%!
if /i "!sub_str!"=="%search_str%" (
    endlocal & set "%~3=%start_index%"
) else (
    set /a start_index+=1
    goto :loop
)