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
        $apiWorkloadActions = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/workloadactionsapi/profiles/$profileId/workloadactions/category/Appstart" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }
    
    $max = 10
    $i = 0

    for ($i = 0; $i -lt $max; $i++)
    {
        try {
            $apiWorkloadActionResults = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/workloadactionsapi/v2/profiles/$profileId/workloadactionresults/statistics?Take=1&ScaleUnit=Minutes&ScaleValue=$interval&floating=true&group=None&Categories=Appstart" -Credential $cred
        } catch {
            throw $_.Exception
            exit 1
        }
        
        if ($apiWorkloadActionResults.All.workloadActionStatistics) {
            break
        }
        
        $retry = $i + 1
        Write-Host (Get-Date)"- Retry attempt: $retry" 
        Start-Sleep -Milliseconds 500
       
    }

    if (!$apiWorkloadActionResults.All.workloadActionStatistics)
    {
        exit 1
    }

    $apiWorkloadActionResultsName = $apiWorkloadActionResults.All.workloadActionStatistics | Get-Member | Where-Object {$_.MemberType -eq "NoteProperty"} | Select Name

    foreach ($apiWorkloadActionResultName in $apiWorkloadActionResultsName) {
        $workloadActionResult = New-Object psobject

        $id = $apiWorkloadActionResultName.Name
        $name = ($apiWorkloadActions | Where-Object {$_.id -eq $id}).name
        $timestamp = $apiWorkloadActionResults.All.timeStamp  
        $average = $apiWorkloadActionResults.All.workloadActionStatistics.$id.average
        $threshold = $apiWorkloadActionResults.All.workloadActionStatistics.$id.threshold
        
        $workloadActionResult | Add-Member -Name profileId -Value $profileId -Type NoteProperty
        $workloadActionResult | Add-Member -Name id -Value $id -Type NoteProperty
        $workloadActionResult | Add-Member -Name name -Value $name -Type NoteProperty    
        $workloadActionResult | Add-Member -Name timestamp -Value $timestamp -Type NoteProperty
        $workloadActionResult | Add-Member -Name average -Value $average -Type NoteProperty    
        $workloadActionResult | Add-Member -Name threshold -Value $threshold -Type NoteProperty
        
        
        $workloadActionResult
    }
}
