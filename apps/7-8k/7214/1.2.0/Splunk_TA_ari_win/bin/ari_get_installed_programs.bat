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

REM Setting file path variables
set app_details_raw_output_file_path="%~dp0..\tmp\app_list_output.txt"

REM Counter to get array length
set /a counter=0

REM Setting host_name with machine name
set host_name=%COMPUTERNAME%

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

REM Getting details of all the apps and save it to app_list_output.txt at location "app_details_raw_output_file_path"
REG QUERY "HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Uninstall" /s | findstr "HKEY_LOCAL_MACHINE DisplayName DisplayVersion InstallDate InstallLocation Publisher" | findstr /v "DisplayName_Localized" > !app_details_raw_output_file_path!
REG QUERY "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" /s | findstr "HKEY_LOCAL_MACHINE DisplayName DisplayVersion InstallDate InstallLocation Publisher" | findstr /v "DisplayName_Localized" >> !app_details_raw_output_file_path!

REM Reading app_list_output.txt line by line
for /f "tokens=*" %%H in ('type !app_details_raw_output_file_path!') do (

    REM Skip iteration when line contains full key "HKEY_LOCAL_MACHINE\..." and add counter value when next key will be found
    echo "%%H" | find /I "HKEY_LOCAL_MACHINE">nul && (
        set /a counter+=1
    ) || (

        REM Reading each key value pair of app
        for /f "tokens=1,2* delims= " %%D in ('echo "%%H"') do (

            REM Removing quote from start of keys
            set dd=%%D
            set "dd=!dd:~1!"

            REM Removing quote from end of values
            set ff=%%F
            set "ff=!ff:~0,-1!"

            REM Saving app details to an array
            if not "!ff!"=="" (
                if !dd!==DisplayName (
                    set app[!counter!].DisplayName="!ff!"
                ) else if !dd!==DisplayVersion (
                    set app[!counter!].DisplayVersion=!ff!
                ) else if !dd!==InstallDate (
                    set app[!counter!].InstallDate=!ff!
                ) else if !dd!==InstallLocation (
                    set app[!counter!].InstallLocation="!ff!"
                ) else if !dd!==Publisher (
                    set app[!counter!].Publisher="!ff!"
                )
            )
        )
    )
)

REM Printing all app details in csv format
for /l %%i in (0 1 !counter!) do  (
    if defined app[%%i].DisplayName (
        set output=!date_time! ari_nt_host=!host_name!
        if defined app[%%i].InstallDate (
            set output=!output! install_date=%%app[%%i].InstallDate%%
        )
        if defined app[%%i].InstallLocation (
            set output=!output! install_location=%%app[%%i].InstallLocation%%
        )
        set output=!output! ari_software_product=%%app[%%i].DisplayName%%
        if defined app[%%i].Publisher (
            set output=!output! ari_software_vendor=%%app[%%i].Publisher%%
        )
        if defined app[%%i].DisplayVersion (
            set output=!output! ari_software_version=%%app[%%i].DisplayVersion%%
        )
        call echo !output!
    )
)

REM Deleting app_list_output.txt as post script cleanup
del !app_details_raw_output_file_path!