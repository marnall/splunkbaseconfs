########################################################################################
##
## SPLUNK_TA_ARI_WIN Edge Discovery
##
## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## Splunk Software Licence and Support Agreement
##
########################################################################################

. "$PSScriptRoot\ari_utils.ps1"

$osInfo = Get-CimInstance Win32_OperatingSystem
$biosInfo = Get-CimInstance Win32_BIOS
$computerSystemInfo = Get-CimInstance Win32_ComputerSystem
$cpuInfo = @(Get-CimInstance Win32_Processor)

$os = $osInfo.Caption
$osVersion = $osInfo.Version
$osBuild = $osInfo.BuildNumber
$osVendor = $osInfo.Manufacturer
$osConfiguration = $computerSystemInfo.DomainRole
$osBuildType = $osInfo.BuildType
$osInstallDate = $osInfo.InstallDate.toString('o')
$windowsDirectory = $osInfo.WindowsDirectory
$systemDirectory = $osInfo.SystemDirectory
$systemBootTime = $osInfo.LastBootUpTime.toString('o')
$bootDevice = $osInfo.BootDevice
$registeredUser = $osInfo.RegisteredUser
$registeredOrganization = $osInfo.Organization
$virtualMem = $osInfo.TotalVirtualMemorySize
$processor = $cpuInfo[0].Name
$cpuCores = $cpuInfo[0].NumberOfCores
$cpuMhz = $cpuInfo[0].CurrentClockSpeed
$cpuCount = $cpuInfo.Count
$domain = $computerSystemInfo.Domain
$mem = $osInfo.TotalVisibleMemorySize
$systemType = $osInfo.OSArchitecture
$availableMemory = $osInfo.FreePhysicalMemory
$availableVirtualMemory = $osInfo.FreeVirtualMemory
$serial = $biosInfo.SerialNumber
$vendor = $computerSystemInfo.Manufacturer
$biosVersion = $biosInfo.Name
$product = $computerSystemInfo.Model

Write-Event `
    "os" $os `
    "os_version" $osVersion `
    "os_build" $osBuild `
    "os_vendor" $osVendor `
    "os_configuration" $osConfiguration `
    "os_build_type" $osBuildType `
    "os_install_date" $osInstallDate `
    "windows_directory" $windowsDirectory `
    "system_directory" $systemDirectory `
    "system_boot_time" $systemBootTime `
    "boot_device" $bootDevice `
    "registered_user" $registeredUser `
    "registered_organization" $registeredOrganization `
    "virtual_mem" $virtualMem `
    "processor" $processor `
    "cpu_cores" $cpuCores `
    "cpu_mhz" $cpuMhz `
    "cpu_count" $cpuCount `
    "$($appPrefix)_domain" $domain `
    "mem" $mem `
    "system_type" $systemType `
    "available_memory" $availableMemory `
    "available_virtual_memory" $availableVirtualMemory `
    "serial" $serial `
    "$($appPrefix)_vendor" $vendor `
    "bios_version" $biosVersion `
    "$($appPrefix)_product" $product