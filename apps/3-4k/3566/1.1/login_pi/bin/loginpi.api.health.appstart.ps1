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
        $apiHealthAppStart = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/workloadactionsapi/profiles/$profileId/workloadactions/bycategory/Appstart/performancehealth?minutes=$interval" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }

    $total = $apiHealthAppStart.total
    $withInThreshold = $apiHealthAppStart.withInThreshold
    $exceededThreshold = $apiHealthAppStart.exceededThreshold
    
    $healthAppStart = New-Object psobject
    $healthAppStart | Add-Member -Name profileId -Value $profileId -Type NoteProperty
    $healthAppStart | Add-Member -Name total -Value $total -Type NoteProperty
    $healthAppStart | Add-Member -Name withInThreshold -Value $withInThreshold -Type NoteProperty
    $healthAppStart | Add-Member -Name exceededThreshold -Value $exceededThreshold -Type NoteProperty
   
    $healthAppStart 
}

