########################################################################################
##
## SPLUNK_TA_ARI_WIN Edge Discovery
##
## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## Splunk Software Licence and Support Agreement
##
########################################################################################

. "$PSScriptRoot\ari_utils.ps1"

$adapters = Get-CimInstance -ClassName Win32_NetworkAdapterConfiguration

foreach ($adapter in $adapters) {
    $ips = $adapter.IPAddress
    $mac = $adapter.MACAddress
    if ($adapter.IPEnabled -and $ips -and $mac) {
        foreach ($ip in $ips) {
            Write-Event `
                "$($appPrefix)_ip" $ip `
                "$($appPrefix)_mac" $mac
        }
    }
}