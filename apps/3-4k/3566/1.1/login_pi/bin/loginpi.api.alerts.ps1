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
        $apiAlerts = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/alertsapi/profiles/$profileId/alerts?minutes=$interval" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }
    
    foreach ($alertItem in $apiAlerts) {

        $source = $alertItem.source
        $displayTitle = $alertItem.displayTitle
        $description = $alertItem.description
        $alertType = $alertItem.alertType
        $created = $alertItem.created

        $alert = New-Object psobject
        $alert | Add-Member -Name profileId -Value $profileId -Type NoteProperty
        $alert | Add-Member -Name source -Value $source -Type NoteProperty
        $alert | Add-Member -Name displayTitle -Value $displayTitle -Type NoteProperty
        $alert | Add-Member -Name description -Value $description -Type NoteProperty
        $alert | Add-Member -Name alertType -Value $alertType -Type NoteProperty
        $alert | Add-Member -Name created -Value $created -Type NoteProperty
        
        $alert
    }
}

