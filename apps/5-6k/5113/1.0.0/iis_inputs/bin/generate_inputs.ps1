# generate inputs.conf for IIS

if ( -not ($PSScriptRoot) ) {
  # for Powershell 2 compatibility
  $PSScriptRoot = Split-Path $MyInvocation.MyCommand.Path -Parent
}

Import-Module WebAdministration
$INPUTSCONF = "$PSScriptRoot\..\default\inputs.conf"

# only if IIS websites exist and inputs.conf contains no monitors
If ((Get-Website) -And (-Not (Select-String -Pattern "^\[monitor" -Path "$INPUTSCONF" -quiet))) {
 foreach($WebSite in $(get-website)) {
  $logFile="$($Website.logFile.directory)\W3SVC$($website.id)".replace("%SystemDrive%",$env:SystemDrive)
  Add-Content -Path "$INPUTSCONF" -Value ""
  Add-Content -Path "$INPUTSCONF" -Value "# $($website.name)"
  Add-Content -Path "$INPUTSCONF" -Value "[monitor://$logfile]"
  Add-Content -Path "$INPUTSCONF" -Value "disabled = false"
  Add-Content -Path "$INPUTSCONF" -Value "ignoreOlderThan = 14d"
  Add-Content -Path "$INPUTSCONF" -Value "sourcetype = ms:iis:auto"
  Add-Content -Path "$INPUTSCONF" -Value "index = default"
 }
 # restart splunk if inputs.conf now contains monitors
 if (Select-String -Pattern "^\[monitor" -Path "$INPUTSCONF" -quiet) {
  Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList "$PSScriptRoot\restart_splunk.cmd"
 }
}
