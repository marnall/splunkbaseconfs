$scriptPath = split-path -parent $MyInvocation.MyCommand.Definition

Set-Location $scriptPath

. .\lib\loginpi.read-config.ps1

try {
    $apiProfiles = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/profilesapi/profiles" -Credential $cred
} catch {
    throw $_.Exception
    exit 1
}

try {
    $apiConnectors = Invoke-RestMethod -Method GET -Uri "http://$loginPiHost/connectionsapi/connectors" -Credential $cred
} catch {
    throw $_.Exception
    exit 1
}

foreach ($apiProfile in $apiProfiles) {

    $id = $apiProfile.id
    $name = $apiProfile.name
    $description = $apiProfile.description
    $connectorId = $apiProfile.connectorId
    $connector = $apiConnectors[$connectorId -1].Name

    $profile = New-Object psobject
    $profile | Add-Member -Name id -Value $id -Type NoteProperty
    $profile | Add-Member -Name name -Value $name -Type NoteProperty
    $profile | Add-Member -Name description -Value $description -Type NoteProperty
    $profile | Add-Member -Name connector -Value $connector -Type NoteProperty
    
    $profile
}
