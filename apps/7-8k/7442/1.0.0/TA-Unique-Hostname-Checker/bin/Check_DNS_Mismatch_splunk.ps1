# Define paths and hostnames
#$input_conf = 'C:\Program Files\SplunkUniversalForwarder\etc\system\local\inputs.conf'
$server_conf = 'C:\Program Files\SplunkUniversalForwarder\etc\system\local\server.conf'
$instance_cfg = 'C:\Program Files\SplunkUniversalForwarder\etc\instance.cfg'
$expected_input_hostname = $env:COMPUTERNAME
$expected_server_hostname = $env:COMPUTERNAME

# Toggle for enabling or disabling updates
$updateEnabled = $false

# Function to update file content if $updateEnabled is True
function Update-FileContent {
    param (
        [string]$Path,
        [string]$Pattern,
        [string]$Replacement,
        [string]$ExpectedHostname
    )
    $content = Get-Content -Path $Path
    $line = $content | Where-Object { $_ -match $Pattern }
    if (-not $line) {
        return $false, "Hostname not found"
    }

    $currentHostname = $line -replace "$Pattern\s*=\s*", ''
    if ($currentHostname -eq $ExpectedHostname) {
        return $true, $currentHostname
    } else {
        if ($updateEnabled) {
            $content = $content -replace $line, "$Pattern = $ExpectedHostname"
            $content | Set-Content -Path $Path
        }
        return $false, $currentHostname
    }
}

# Function to read the Splunk Agent GUID
function GetSplunkAgentGuid {
    param ($FilePath)
    try {
        $content = Get-Content -Path $FilePath
        $guidLine = $content | Where-Object { $_ -match 'guid\s*=\s*(.*)' }
        $guid = $guidLine -replace '.*guid\s*=\s*(.*)', '$1'
        return $guid.Trim()
    }
    catch {
        return 'Read Error'
    }
}

# Check which user the Splunk service is running as
function GetSplunkServiceAccount {
    $service = Get-WmiObject -Class Win32_Service -Filter "Name='SplunkForwarder'"
    if ($service) {
        return $service.StartName
    } else {
        return 'Service Not Found'
    }
}

# Read and optionally update inputs.conf
#$result, $currentInputHost = Update-FileContent -Path $input_conf -Pattern "host" -Replacement "host = $expected_input_hostname" -ExpectedHostname $expected_input_hostname
#$inputsConfVerification = "@{InputsConfMatch=$result}"
#$currentInputHostOutput = "@{CurrentInputHost=$currentInputHost}"

# Read and optionally update server.conf
$result, $currentServerHost = Update-FileContent -Path $server_conf -Pattern "serverName" -Replacement "serverName = $expected_server_hostname" -ExpectedHostname $expected_server_hostname
$serverConfigVerification = "@{ServerConfMatch=$result}"
$currentServerHostOutput = "@{CurrentServerHost=$currentServerHost}"

# Get the Splunk service account
$splunkServiceAccount = GetSplunkServiceAccount
$splunkServiceAccountOutput = "@{SplunkServiceAccount=$splunkServiceAccount}"

# Get the Splunk Agent GUID
$SplunkCfgInstanceGuid = GetSplunkAgentGuid $instance_cfg
$SplunkCfgInstanceGuidOutput = "@{SplunkCfgInstanceGuid=$SplunkCfgInstanceGuid}"

# Output the results
#Write-Output $inputsConfVerification
#Write-Output $currentInputHostOutput
Write-Output $serverConfigVerification
Write-Output $currentServerHostOutput
Write-Output $splunkServiceAccountOutput
Write-Output $SplunkCfgInstanceGuidOutput
