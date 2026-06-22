########################################################################################
##
## SPLUNK_TA_EXPOSUREANALYTICS_WIN Edge Discovery
##
## Copyright (C) 2026 - Splunk Inc. - All Rights Reserved
## Splunk Software Licence and Support Agreement
##
########################################################################################

. "$PSScriptRoot\ea_utils.ps1"

$adapters = Get-CimInstance -ClassName Win32_NetworkAdapterConfiguration

foreach ($adapter in $adapters) {
    $ips = $adapter.IPAddress
    $mac = $adapter.MACAddress
    if ($adapter.IPEnabled -and $ips -and $mac) {
        foreach ($ip in $ips) {
            Write-Event `
                "ip" $ip `
                "mac" $mac
        }
    }
}