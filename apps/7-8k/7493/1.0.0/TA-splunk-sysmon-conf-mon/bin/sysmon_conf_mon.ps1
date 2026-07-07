 # Initialize default outputs
 $serviceStatus = "@{Service=NoSysmonInstalled}"
 $productRunningPathOutput = "@{ProductRunningPath=NotFound}"
 $agentVersionOutput = "@{ProductVersion=NotFound}"
 $xmlDirectoryOutput = "@{XmlDirectory=NotFound}"
 $xmlHashOutput = "@{XmlHash=NotFound}"
 $xmlVersionOutput = "@{XmlVersion=NotFound}"
 
 # Check Sysmon service status
 $check32 = Get-Service -Name sysmon -WarningAction SilentlyContinue -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status
 $check64 = Get-Service -Name sysmon64 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status
 
 if ($check32 -eq 'Running') {
     $serviceStatus = "@{Service=Running32Bit}"
     $productRunningPath = (Get-ItemPropertyValue -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Sysmon" -Name "ImagePath" -ErrorAction SilentlyContinue) -replace '"', ''
     if ($productRunningPath) {
         $productRunningPathOutput = "@{ProductRunningPath=$productRunningPath}"
     }
 } elseif ($check64 -eq 'Running') {
     $serviceStatus = "@{Service=Running64Bit}"
     $productRunningPath = (Get-ItemPropertyValue -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Sysmon64" -Name "ImagePath" -ErrorAction SilentlyContinue) -replace '"', ''
     if ($productRunningPath) {
         $productRunningPathOutput = "@{ProductRunningPath=$productRunningPath}"
     }
 }
 
 # Check Sysmon agent version
 $agentVersion = $null
 if ($check32 -eq 'Running' -or $check64 -eq 'Running') {
     $agentPath = (Get-WmiObject Win32_Service | Where-Object { $_.Name -match 'sysmon' }).PathName
     $agentVersion = (Get-ItemProperty -Path $agentPath -ErrorAction SilentlyContinue).VersionInfo.ProductVersion
 }
 if ($agentVersion) {
     $agentVersionOutput = "@{ProductVersion=$agentVersion}"
 }
 
 # Retrieve and output the configuration file path and hash
 try {
     $SysmonConfigPath = Get-ItemPropertyValue -Path "HKLM:\SYSTEM\CurrentControlSet\Services\SysmonDrv\Parameters" -Name "ConfigFile" -ErrorAction SilentlyContinue
     $SysmonConfigHash = Get-ItemPropertyValue -Path "HKLM:\SYSTEM\CurrentControlSet\Services\SysmonDrv\Parameters" -Name "ConfigHash" -ErrorAction SilentlyContinue
 
     if ($SysmonConfigPath) {
         $xmlDirectoryOutput = "@{XmlDirectory=$SysmonConfigPath}"
     }
 
     if ($SysmonConfigHash) {
         $xmlHashOutput = "@{XmlHash=$SysmonConfigHash}"
     }
 } catch {
     # Outputs for XmlDirectory and XmlHash are already initialized to 'NotFound'
 }
 
 # Check for version information in the configuration file content
 if ($SysmonConfigPath -and (Test-Path $SysmonConfigPath)) {
     $XmlContent = Get-Content -Path $SysmonConfigPath -ErrorAction SilentlyContinue
     $VersionLine = $XmlContent | Where-Object { $_ -match "<!--version:(.+)-->" }
     if ($VersionLine) {
         $xmlVersion = $VersionLine -replace ".*<!--version:(.+?)-->.*", '$1'
         $xmlVersionOutput = "@{XmlVersion=$xmlVersion}"
     }
 }
 
 # Output the results
 Write-Output $serviceStatus
 Write-Output $productRunningPathOutput
 Write-Output $agentVersionOutput
 Write-Output $xmlDirectoryOutput
 Write-Output $xmlHashOutput
 Write-Output $xmlVersionOutput 