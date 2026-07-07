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

rem Check if manage-bde is installed
where manage-bde >nul 2>&1
if %errorlevel% equ 0 (
    REM Counter to get array length
    set /a counter=0

    REM Getting bitlocker details of all the volume
    for /f "skip=5 tokens=1,2 delims=:" %%A in ('manage-bde -status') do (
        for /f "tokens=*" %%C in ('echo %%A') do (
            set key=%%C
        )
        for /f "tokens=*" %%D in ('echo %%B') do (
            set value=%%D
        )

        echo !key! | findstr /R "^Volume">nul && (
            set /a counter+=1

            REM Removing "[" from start and "]" from end of value
            set label=!value!
            set "label=!label:~1!"
            set "label=!label:~0,-1!"

            REM Getting volume letter
            set letter=!key!
            set "letter=!letter:~7!"

            REM Setting label and letter of volume
            set Volume[!counter!].Label=!label!
            set Volume[!counter!].Letter=!letter!
            for /f "skip=1 tokens=1,2" %%A in ('wmic logicaldisk get DeviceID^, DriveType') do (
                if "!letter!:" == "%%A" (
                    set Volume[!counter!].DriveType=%%B
                )
            )
        ) || echo !key! | findstr "Volume">nul && (

            REM Removing "[" from start and "]" from end of key
            set type=!key!
            set "type=!type:~1!"
            set "type=!type:~0,-1!"

            REM Setting Volume type
            set Volume[!counter!].Type=!type!
        ) || (
            REM Saving Volume details to an array
            if "!key!"=="Size" (
                set Volume[!counter!].Size=!value!
            ) else if "!key!"=="BitLocker Version" (
                set Volume[!counter!].BitLocker_Version=!value!
            ) else if "!key!"=="Conversion Status" (
                set Volume[!counter!].Conversion_Status=!value!
            ) else if "!key!"=="Encryption Method" (
                set Volume[!counter!].Encryption_Method=!value!
            ) else if "!key!"=="Protection Status" (
                set Volume[!counter!].Protection_Status=!value!
            )
        )
    )

    REM Printing all Volume details in csv format
    for /l %%i in (0 1 !counter!) do  (
        if defined Volume[%%i].Letter (

            call set volume_label=%%Volume[%%i].Label%%
            call set volume_letter=%%Volume[%%i].Letter%%
            call set volume_type=%%Volume[%%i].Type%%
            call set drive_type=%%Volume[%%i].DriveType%%
            call set size=%%Volume[%%i].Size%%
            call set bitLocker_version=%%Volume[%%i].BitLocker_Version%%
            call set conversion_status=%%Volume[%%i].Conversion_Status%%
            call set encryption_method=%%Volume[%%i].Encryption_Method%%
            call set protection_status=%%Volume[%%i].Protection_Status%%

            set output=!date_time! ari_nt_host=%COMPUTERNAME%
            if not "!volume_label!"=="" (set output=!output! volume_label="!volume_label!")
            if not "!volume_letter!"=="" (set output=!output! volume_letter="!volume_letter!")
            if not "!volume_type!"=="" (set output=!output! volume_type="!volume_type!")
            if not "!drive_type!"=="" (set output=!output! drive_type="!drive_type!")
            if not "!size!"=="" (set output=!output! size="!size!")
            if not "!bitLocker_version!"=="" (set output=!output! bitLocker_version="!bitLocker_version!")
            if not "!conversion_status!"=="" (set output=!output! conversion_status="!conversion_status!")
            if not "!encryption_method!"=="" (set output=!output! encryption_method="!encryption_method!")
            if not "!protection_status!"=="" (set output=!output! protection_status="!protection_status!")

            echo !output!
       )
    )
)