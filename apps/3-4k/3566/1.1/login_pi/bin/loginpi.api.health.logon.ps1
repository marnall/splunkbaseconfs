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
        $apiHealthLogonAction = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/workloadactionsapi/profiles/$profileId/workloadactions/bycategory/LogonAction/performancehealth?minutes=$interval" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }

    $total = $apiHealthLogonAction.total
    $withInThreshold = $apiHealthLogonAction.withInThreshold
    $exceededThreshold = $apiHealthLogonAction.exceededThreshold
    
    $healthLogonAction = New-Object psobject
    $healthLogonAction | Add-Member -Name profileId -Value $profileId -Type NoteProperty
    $healthLogonAction | Add-Member -Name total -Value $total -Type NoteProperty
    $healthLogonAction | Add-Member -Name withInThreshold -Value $withInThreshold -Type NoteProperty
    $healthLogonAction | Add-Member -Name exceededThreshold -Value $exceededThreshold -Type NoteProperty
   
    $healthLogonAction 
}

