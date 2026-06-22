########################################################################################
##
## SPLUNK_TA_EXPOSUREANALYTICS_WIN Edge Discovery
##
## Copyright (C) 2026 - Splunk Inc. - All Rights Reserved
## Splunk Software Licence and Support Agreement
##
########################################################################################

. "$PSScriptRoot\ea_utils.ps1"

function Write-UserEvent {
    Write-Event `
        "user_id" $userId `
        "account_active" $accountActive `
        "last_logon" $lastLogon
}

try {
    $quserResult = quser 2>$null

    if (-not $quserResult -or $quserResult.Count -lt 2) { throw }

    $header = $quserResult[0]
    $lines = $quserResult[1..($quserResult.Count - 1)]

    $userIdIndex = $header.IndexOf("USERNAME")
    $userIdLength = $header.IndexOf("SESSIONNAME") - $userIdIndex
    $accountActiveIndex = $header.IndexOf("STATE")
    $accountActiveLength = $header.IndexOf("IDLE TIME") - $accountActiveIndex
    $lastLogonIndex = $header.IndexOf("LOGON TIME")

    foreach ($line in $lines) {
        $lastLogonLength = $line.Length - $lastLogonIndex

        $userId = $line.Substring($userIdIndex, $userIdLength).Trim()
        $accountActive = $line.Substring($accountActiveIndex, $accountActiveLength).Trim()
        $lastLogon = $line.Substring($lastLogonIndex, $lastLogonLength).Trim()

        Write-UserEvent
    }
}
catch {
    $logonSessions = Get-CimInstance Win32_LogonSession

    foreach ($session in $logonSessions) {
        if ($session.LogonType -eq 2 -or $session.LogonType -eq 10) {
            $links = Get-CimAssociatedInstance -InputObject $session -ResultClassName Win32_Account

            foreach ($user in $links) {
                $userId = $user.Name
                $lastLogon = $session.StartTime.toString('o')

                Write-UserEvent
            }
        }
    }

    if (-not $userId) {
        $userId = $env:USERNAME

        Write-UserEvent
    }
}