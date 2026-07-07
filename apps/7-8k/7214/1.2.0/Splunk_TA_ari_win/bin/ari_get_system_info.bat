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

for /f "tokens=* delims=" %%T in ('wmic os get * /format:list') do (
    set line=%%T
    if "!line:~0,8!"=="Caption=" (
        set os=!line:~8,-1!
    )
    if "!line:~0,8!"=="Version=" (
        set os_version=!line:~8,-1!
    )
    if "!line:~0,12!"=="BuildNumber=" (
        set os_build=!line:~12,-1!
    )
    if "!line:~0,13!"=="Manufacturer=" (
        set os_vendor=!line:~13,-1!
    )
    if "!line:~0,10!"=="BuildType=" (
        set os_build_type=!line:~10,-1!
    )
    if "!line:~0,12!"=="InstallDate=" (
        set os_install_date=!line:~12,-1!
    )
    if "!line:~0,17!"=="WindowsDirectory=" (
        set windows_directory=!line:~17,-1!
    )
    if "!line:~0,16!"=="SystemDirectory=" (
        set system_directory=!line:~16,-1!
    )
    if "!line:~0,15!"=="LastBootUpTime=" (
        set system_boot_time=!line:~15,-1!
    )
    if "!line:~0,11!"=="BootDevice=" (
        set boot_device=!line:~11,-1!
    )
    if "!line:~0,13!"=="Organization=" (
        set registered_organization=!line:~13,-1!
    )
    if "!line:~0,15!"=="RegisteredUser=" (
        set registered_user=!line:~15,-1!
    )
    if "!line:~0,23!"=="TotalVirtualMemorySize=" (
        set virtual_mem=!line:~23,-1!
    )
    if "!line:~0,23!"=="TotalVisibleMemorySize=" (
        set memory=!line:~23,-1!
    )
    if "!line:~0,15!"=="OSArchitecture=" (
        set system_type=!line:~15,-1!
    )
    if "!line:~0,19!"=="FreePhysicalMemory=" (
        set available_memory=!line:~19,-1!
    )
    if "!line:~0,18!"=="FreeVirtualMemory=" (
        set available_virtual_memory=!line:~18,-1!
    )
)

for /f "tokens=* delims=" %%T in ('wmic bios get * /format:list') do (
    set line=%%T
    if "!line:~0,13!"=="SerialNumber=" (
        set serial=!line:~13,-1!
    )
    if "!line:~0,5!"=="Name=" (
        set bios_version=!line:~5,-1!
    )
)

for /f "tokens=* delims=" %%T in ('wmic computersystem get * /format:list') do (
    set line=%%T
    if "!line:~0,11!"=="DomainRole=" (
        set os_configuration=!line:~11,-1!
    )
    if "!line:~0,7!"=="Domain=" (
        set domain=!line:~7,-1!
    )
    if "!line:~0,6!"=="Model=" (
        set system_model=!line:~6,-1!
    )
    if "!line:~0,13!"=="Manufacturer=" (
        set aura_vendor=!line:~13,-1!
    )
)

set /a cpu_count=0
set /a cpu_cores=0
for /f "tokens=* delims=" %%T in ('wmic cpu get * /format:list') do (
    set line=%%T
    if "!line:~0,14!"=="NumberOfCores=" (
        set /a cpu_cores+=!line:~14,-1!
        set /a cpu_count+=1
    )
)

for /f "skip=1" %%i in ('wmic cpu get CurrentClockSpeed') do if not defined cpu_mhz (
    for /f "delims=" %%j in ("%%i") do if not "%%j"=="" set cpu_mhz=%%j
)

for /f "skip=1 delims=^," %%i in ('wmic cpu get Name /VALUE') do if not defined cpu_name (
    for /f "delims== tokens=2" %%j in ("%%i") do if not "%%j"=="" set cpu_name=%%j
)

set output=!date_time! ari_nt_host=%COMPUTERNAME%
if not "!os!"=="" (set output=!output! os="!os!")
if not "!os_version!"=="" (set output=!output! os_version="!os_version!")
if not "!os_build!"=="" (set output=!output! os_build="!os_build!")
if not "!os_vendor!"=="" (set output=!output! os_vendor="!os_vendor!")
if not "!os_configuration!"=="" (set output=!output! os_configuration="!os_configuration!")
if not "!os_build_type!"=="" (set output=!output! os_build_type="!os_build_type!")
if not "!os_install_date!"=="" (set output=!output! os_install_date="!os_install_date!")
if not "!windows_directory!"=="" (set output=!output! windows_directory="!windows_directory!")
if not "!system_directory!"=="" (set output=!output! system_directory="!system_directory!")
if not "!system_boot_time!"=="" (set output=!output! system_boot_time="!system_boot_time!")
if not "!boot_device!"=="" (set output=!output! boot_device="!boot_device!")
if not "!registered_user!"=="" (set output=!output! registered_user="!registered_user!")
if not "!registered_organization!"=="" (set output=!output! registered_organization="!registered_organization!")
if not "!virtual_mem!"=="" (set output=!output! virtual_mem="!virtual_mem!")
if not "!cpu_name!"=="" (set output=!output! processor="!cpu_name!")
if not "!cpu_cores!"=="" (set output=!output! cpu_cores="!cpu_cores!")
if not "!cpu_mhz!"=="" (set output=!output! cpu_mhz="!cpu_mhz!")
if not "!cpu_count!"=="" (set output=!output! cpu_count="!cpu_count!")
if not "!domain!"=="" (set output=!output! ari_domain="!domain!")
if not "!memory!"=="" (set output=!output! mem="!memory!")
if not "!system_type!"=="" (set output=!output! system_type="!system_type!")
if not "!available_memory!"=="" (set output=!output! available_memory="!available_memory!")
if not "!available_virtual_memory!"=="" (set output=!output! available_virtual_memory="!available_virtual_memory!")
if not "!serial!"=="" (set output=!output! serial="!serial!")
if not "!aura_vendor!"=="" (set output=!output! ari_vendor="!aura_vendor!")
if not "!bios_version!"=="" (set output=!output! bios_version="!bios_version!")
if not "!system_model!"=="" (set output=!output! ari_product="!system_model!")

echo !output!