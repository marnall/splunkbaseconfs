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
        $apiLogonActions = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/workloadactionsapi/profiles/$profileId/workloadactions/category/LogonAction" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }

    $max = 10
    $i = 0

    for ($i = 0; $i -lt $max; $i++)
    {
        try {
            $apiLogonActionsResults = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/workloadactionsapi/v2/profiles/$profileId/workloadactionresults/statistics?Take=1&ScaleUnit=Minutes&ScaleValue=$interval&floating=true&group=None&Categories=LogonAction" -Credential $cred
        } catch {
            throw $_.Exception
            exit 1
        }
        if ($apiLogonActionsResults.All.workloadActionStatistics) {
            break
        }
        
        $retry = $i + 1
        Write-Host (Get-Date)"- Retry attempt: $retry" 
        Start-Sleep -Milliseconds 500  
    }

    if (!$apiLogonActionsResults.All.workloadActionStatistics)
    {
        exit 1
    }

    $apiLogonActionsResultsName = $apiLogonActionsResults.All.workloadActionStatistics | Get-Member | Where-Object {$_.MemberType -eq "NoteProperty"} | Select Name

    foreach ($apiLogonActionsResultName in $apiLogonActionsResultsName) {
        $logonActionResult = New-Object psobject
        
        $id = $apiLogonActionsResultName.Name
        $name = ($apiLogonActions | Where-Object {$_.id -eq $id}).name
        $timestamp = $apiLogonActionsResults.All.timeStamp  
        $average = $apiLogonActionsResults.All.workloadActionStatistics.$id.average
        $threshold = $apiLogonActionsResults.All.workloadActionStatistics.$id.threshold
        
        $logonActionResult | Add-Member -Name profileId -Value $profileId -Type NoteProperty
        $logonActionResult | Add-Member -Name id -Value $id -Type NoteProperty
        $logonActionResult | Add-Member -Name name -Value $name -Type NoteProperty    
        $logonActionResult | Add-Member -Name timestamp -Value $timestamp -Type NoteProperty
        $logonActionResult | Add-Member -Name average -Value $average -Type NoteProperty    
        $logonActionResult | Add-Member -Name threshold -Value $threshold -Type NoteProperty
        
        $logonActionResult
    }
}
