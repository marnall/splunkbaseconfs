$scriptPath = split-path -parent $MyInvocation.MyCommand.Definition

Set-Location $scriptPath

. .\lib\loginpi.read-config.ps1

try {
    $apiProfiles = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/profilesapi/profiles" -Credential $cred
} catch {
    throw $_.Exception
    exit 1
}

foreach ($apiProfile in $apiProfiles) {
    
    $id = $apiProfile.id
    try {
        $apiSessionSuccessRate = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/sessionsapi/profiles/$id/sessions/successrate/current?ScaleUnit=Minutes&ScaleValue=$interval" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }
    
    $profileId = $apiProfile.id
    $totalSessions = $apiSessionSuccessRate.totalSessions
    $successfulSessions = $apiSessionSuccessRate.successfulSessions
    $failedSessions = $apiSessionSuccessRate.failedSessions

    $sessionSuccessRate = New-Object psobject
    $sessionSuccessRate | Add-Member -Name profileId -Value $profileId -Type NoteProperty
    $sessionSuccessRate | Add-Member -Name totalSessions -Value $totalSessions -Type NoteProperty
    $sessionSuccessRate | Add-Member -Name successfulSessions -Value $successfulSessions -Type NoteProperty
    $sessionSuccessRate | Add-Member -Name failedSessions -Value $failedSessions -Type NoteProperty

    $sessionSuccessRate
}