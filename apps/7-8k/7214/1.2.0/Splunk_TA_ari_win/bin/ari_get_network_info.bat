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

for /f "tokens=* delims=" %%T in ('wmic nicconfig where IPEnabled^=True get IPAddress^,MACAddress /format:table') do (
    set line=%%T
    if "!line:~0,1!"=="{" (
        for /f "tokens=1,2 delims=}" %%A in ('echo !line!') do (
            set raw_ip=%%A
            set raw_mac=%%B
            set aura_mac=!raw_mac:~-19,-2!
            call :trim aura_mac !aura_mac!
            if not "!aura_mac!"=="" (
                for /f "tokens=1,2 delims=," %%T in ('echo "!raw_ip!"') do (
                    set aura_ip=%%T
                    set aura_ip="!aura_ip:~3,-1!"
                    set output=!date_time! ari_nt_host=%COMPUTERNAME% ari_ip=!aura_ip! ari_mac="!aura_mac!"
                    echo !output!

                    set ipv6=%%U
                    set "ipv6=!ipv6:"=!"
                    call :trim ipv6 !ipv6!
                    if not "!ipv6!"=="" (
                        set output=!date_time! ari_nt_host=%COMPUTERNAME% ari_ip="!ipv6!" ari_mac="!aura_mac!"
                        echo !output!
                    )
                )
            )

            set previous_mac=!aura_mac!
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