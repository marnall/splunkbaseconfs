$scriptPath = split-path -parent $MyInvocation.MyCommand.Definition

Set-Location $scriptPath

. .\lib\loginpi.read-config.ps1

try {
    $apiProfiles = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/profilesapi/profiles" -Credential $cred
} catch {
    throw $_.Exception
    exit 1
}

foreach ($profile in $apiProfiles) {
    
    $profileId = $profile.id
    try {
        $apiHealthSessions = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/sessionsapi/profiles/$profileId/sessions/successrate/current?ScaleUnit=Minutes&ScaleValue=$interval" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }
    
    $totalSessions = $apiHealthSessions.totalSessions
    $successfulSessions = $apiHealthSessions.successfulSessions
    $failedSessions = $apiHealthSessions.failedSessions
    
    $healthSessions = New-Object psobject
    $healthSessions | Add-Member -Name profileId -Value $profileId -Type NoteProperty
    $healthSessions | Add-Member -Name totalSessions -Value $totalSessions -Type NoteProperty
    $healthSessions | Add-Member -Name successfulSessions -Value $successfulSessions -Type NoteProperty
    $healthSessions | Add-Member -Name failedSessions -Value $failedSessions -Type NoteProperty
   
    $healthSessions 
}

