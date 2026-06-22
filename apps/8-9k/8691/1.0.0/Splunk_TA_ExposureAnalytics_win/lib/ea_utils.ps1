########################################################################################
##
## SPLUNK_TA_EXPOSUREANALYTICS_WIN Edge Discovery
##
## Copyright (C) 2026 - Splunk Inc. - All Rights Reserved
## Splunk Software Licence and Support Agreement
##
########################################################################################

function Get-Prefix {
    $dateTime = (Get-Date -Format yyyy-MM-ddTHH:mm:sszzz) -replace ":(\d\d)$", '$1'
    $ntHost = $env:COMPUTERNAME

    return @("$dateTime nt_host=$ntHost")
}

function Write-Event {
    param (
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Args
    )

    $events = @()
    for ($i = 0; $i -lt $Args.Count; $i += 2) {
        $field = $Args[$i]
        $value = $Args[$i + 1].trim()

        if ($value) {
            $events += "$field=""$($value.Replace('""', '\""'))"""
        }
    }

    "$(Get-Prefix) $events"
}