########################################################################################
##
## SPLUNK_TA_ARI_WIN Edge Discovery
##
## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## Splunk Software Licence and Support Agreement
##
########################################################################################

. "$PSScriptRoot\ari_utils.ps1"

$programs = Get-ItemProperty -Path `
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*", `
    "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"`
    -ErrorAction SilentlyContinue

foreach ($program in $programs) {
    $installDate = $program.InstallDate
    $installLocation = $program.InstallLocation
    $softwareProduct = $program.DisplayName
    $softwareVendor = $program.Publisher
    $softwareVersion = $program.DisplayVersion

    if ($softwareProduct) {
        Write-Event `
            "install_date" $installDate `
            "install_location" $installLocation `
            "$($appPrefix)_software_product" $softwareProduct `
            "$($appPrefix)_software_vendor" $softwareVendor `
            "$($appPrefix)_software_version" $softwareVersion
    }
}