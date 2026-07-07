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
        $apiMetrics = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/sessionmetricsapi/profiles/$profileId/sessionmetrics/statistics?Take=1&ScaleUnit=Minutes&ScaleValue=$interval&floating=true&group=None" -Credential $cred
    } catch {
        throw $_.Exception
        exit 1
    }

    $timeStamp = $apiMetrics.none.timestamp
    $latency = $apiMetrics.none.latency.average
    $framesPerSecond = $apiMetrics.none.framespersecond.average
    $bandwidth = $apiMetrics.none.bandwidth.average
    $cpuLoad = $apiMetrics.none.cpuLoad.average
    $memoryLoad = $apiMetrics.none.memoryLoad.average
    $numberOfProcesses = $apiMetrics.none.numberOfProcesses.average
    $diskInputOutput = $apiMetrics.none.diskInputOutput.average
    $concurrentUsers = $apiMetrics.none.concurrentUsers.average

    
    $metric = New-Object psobject
    $metric | Add-Member -Name profileId -Value $profileId -Type NoteProperty
    $metric | Add-Member -Name timeStamp -Value $timeStamp -Type NoteProperty
    $metric | Add-Member -Name latency -Value $latency -Type NoteProperty
    $metric | Add-Member -Name framesPerSecond -Value $framesPerSecond -Type NoteProperty
    $metric | Add-Member -Name bandwidth -Value $bandwidth -Type NoteProperty
    $metric | Add-Member -Name cpuLoad -Value $cpuLoad -Type NoteProperty
    $metric | Add-Member -Name memoryLoad -Value $memoryLoad -Type NoteProperty
    $metric | Add-Member -Name numberOfProcesses -Value $numberOfProcesses -Type NoteProperty
    $metric | Add-Member -Name diskInputOutput -Value $diskInputOutput -Type NoteProperty
    $metric | Add-Member -Name concurrentUsers -Value $concurrentUsers -Type NoteProperty
    
    $metric
    
}

