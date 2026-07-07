 # Define paths and hostnames
 $server_conf = 'C:\Program Files\SplunkUniversalForwarder\etc\system\local\server.conf'
 $instance_cfg = 'C:\Program Files\SplunkUniversalForwarder\etc\instance.cfg'
 $marker_file = 'C:\Program Files\SplunkUniversalForwarder\instance_cfg_deleted.marker'
 $expected_server_hostname = $env:COMPUTERNAME
 
 # Remediation flags, set to true if remediation is required
 $Remediation_Hostname = $false
 $remediation_guid = $false
 $remediation_service = $false
 
 $global:RemediationStatus = "noaction"
 
 function Remediation_Hostname {
     param (
         [string]$Path,
         [string]$Pattern,
         [string]$ExpectedHostname
     )
     $content = Get-Content -Path $Path -ErrorAction SilentlyContinue
     if ($content -eq $null) { return $false, "File not found" }
 
     $line = $content | Where-Object { $_ -match $Pattern }
     if (-not $line) {
         if ($Remediation_Hostname) {
             # Add the expected hostname if not found
             $content += "`n$Pattern = $ExpectedHostname"
             $content | Set-Content -Path $Path
             $global:RemediationStatus = "remediated_hostname"
             return $true, $ExpectedHostname
         } else {
             return $false, "Hostname not found"
         }
     }
 
     $currentHostname = $line -replace "$Pattern\s*=\s*", ''
     if ($currentHostname -eq $ExpectedHostname) {
         return $true, $currentHostname
     } else {
         if ($Remediation_Hostname) {
             $content = $content -replace $line, "$Pattern = $ExpectedHostname"
             $content | Set-Content -Path $Path
             $global:RemediationStatus = "remediated_hostname"
             return $true, $ExpectedHostname
         }
         return $false, $currentHostname
     }
 }
 
 function GetSplunkAgentGuid {
     param ($FilePath)
     try {
         $content = Get-Content -Path $FilePath -ErrorAction SilentlyContinue
         if ($content -eq $null) { return 'notfound' }
         
         $guidLine = $content | Where-Object { $_ -match 'guid\s*=\s*(.*)' }
         $guid = $guidLine -replace '.*guid\s*=\s*(.*)', '$1'
         return $guid.Trim()
     }
     catch {
         return 'notfound'
     }
 }
 
 function GetSplunkServiceInfo {
     $service = Get-WmiObject -Class Win32_Service -Filter "Name='SplunkForwarder'" -ErrorAction SilentlyContinue
     if ($service) {
         $startupType = switch ($service.StartMode) {
             "Auto" { "automatic" }
             "Manual" { "manual" }
             "Disabled" { "disabled" }
             default { "unknown" }
         }
         return $service.StartName, $startupType
     } else {
         return 'notfound', 'notfound'
     }
 }
 
 # Function to delete instance.cfg file
 function Delete-InstanceCfg {
     param ($FilePath, $MarkerFile)
     if (Test-Path $FilePath) {
         Remove-Item $FilePath -Force -ErrorAction SilentlyContinue -WarningAction SilentlyContinue | Out-Null
         # Create a marker file to indicate deletion has occurred
         New-Item -Path $MarkerFile -ItemType File -Force -ErrorAction SilentlyContinue -WarningAction SilentlyContinue | Out-Null
         $global:RemediationStatus = "remediated_guid"
     }
 }
 
 # Function to change Splunk service logon account to LocalSystem
 function Set-SplunkServiceToLocalSystem {
     param ($serviceName)
     $service = Get-CimInstance -ClassName Win32_Service -Filter "name = '$serviceName'" -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
     if ($service) {
         if ($service.StartName -ne "LocalSystem") {
             try {
                 $service | Invoke-CimMethod -MethodName Change -Arguments @{
                     StartName       = 'LocalSystem'
                     StartPassword   = $null
                     DesktopInteract = $false
                 } -ErrorAction SilentlyContinue -WarningAction SilentlyContinue | Out-Null
                 $global:RemediationStatus = "remediated_service"
             } catch {
                 # Handle the error silently if its there
             }
         }
     }
 }
 
 # Remediate hostname if necessary
 $result, $currentServerHost = Remediation_Hostname -Path $server_conf -Pattern "serverName" -ExpectedHostname $expected_server_hostname
 $serverConfigVerification = "@{ServerConfMatch=$(if ($result) {'true'} else {'false'})}"
 $currentServerHostOutput = "@{CurrentServerHost=$currentServerHost}"
 
 # Check if the marker file exists before deleting instance.cfg
 if ($remediation_guid -and -not (Test-Path $marker_file -ErrorAction SilentlyContinue -WarningAction SilentlyContinue)) {
     Delete-InstanceCfg -FilePath $instance_cfg -MarkerFile $marker_file
 }
 
 # Perform service remediation if necessary
 if ($remediation_service) {
     Set-SplunkServiceToLocalSystem -serviceName 'SplunkForwarder'
 }
 
 # Get the Splunk service account and startup type
 $splunkServiceAccount, $splunkServiceStartup = GetSplunkServiceInfo
 $splunkServiceAccountOutput = "@{SplunkServiceAccount=$splunkServiceAccount}"
 $splunkServiceStartupOutput = "@{SplunkServiceStartup=$splunkServiceStartup}"
 
 # Get the Splunk Agent GUID
 $SplunkCfgInstanceGuid = GetSplunkAgentGuid $instance_cfg
 $SplunkCfgInstanceGuidOutput = "@{SplunkCfgInstanceGuid=$SplunkCfgInstanceGuid}"
 
 # Get OS type
 function GetWindowsOSType {
     $osType = "unknown"
     $productType = (Get-WmiObject -Class Win32_OperatingSystem -ErrorAction SilentlyContinue -WarningAction SilentlyContinue).ProductType
     if ($productType -eq 1) {
         $osType = "windows_workstation"
     } elseif ($productType -eq 2 -or $productType -eq 3) {
         $osType = "windows_server"
     }
     return $osType
 }
 
 $OsType = GetWindowsOSType
 $OsTypeOutput = "@{ostype=$OsType}"
 
 # Create remediation status output
 $RemediationStatusOutput = "@{remediationstatus=$RemediationStatus}"
 
 # Output the results
 Write-Output $serverConfigVerification
 Write-Output $currentServerHostOutput
 Write-Output $splunkServiceAccountOutput
 Write-Output $splunkServiceStartupOutput
 Write-Output $SplunkCfgInstanceGuidOutput
 Write-Output $OsTypeOutput
 Write-Output $RemediationStatusOutput
  