param(
  [string]$splunkHome  = $env:SPLUNK_HOME
)

if ( -not ($splunkHome) ) {
  $splunkHome = "$env:ProgramFiles\SplunkUniversalForwarder"
}

if ( -not ($PSScriptRoot) ) {
  # for Powershell 2 compatibility
  $PSScriptRoot = Split-Path $MyInvocation.MyCommand.Path -Parent
}


[string]$SERVERCONF = "$splunkHome\etc\system\local\server.conf"
[string]$INPUTSCONF = "$splunkHome\etc\system\local\inputs.conf"

# set comment-string for replacement
[string]$CONFCOMMENT = "#" + (Get-Date).GetDateTimeFormats()[66] + " changed by rectify_hostname"
[bool]$REBOOTFLAG = $false

# get lowercase hostname
# use hostname.exe instead of $($Env:COMPUTERNAME)
# abort if result is too short or long
[string]$LOWERHOSTNAME = $(Invoke-Expression $Env:SystemRoot\System32\HOSTNAME.EXE).ToLower()
if ($LOWERHOSTNAME.Length -gt 20 -Or $LOWERHOSTNAME.Length -lt 3) {
 exit
}

# check SERVER.CONF
if (-Not (Select-String -Pattern "^serverName = $LOWERHOSTNAME$" -CaseSensitive -Path "$SERVERCONF" -quiet)) {

 ((Get-Content "$SERVERCONF") -creplace "^(\s*?serverName\s*?=.*?)$","$CONFCOMMENT`r`n#`${1}`r`nserverName = $LOWERHOSTNAME" ) | Set-Content "$SERVERCONF"

 # verify
 if (Select-String -Pattern "^serverName = $LOWERHOSTNAME$" -CaseSensitive -Path "$SERVERCONF" -quiet) {
  $REBOOTFLAG = $true
 }
}

# check INPUTS.CONF
if (-Not (Select-String -Pattern "^host = $LOWERHOSTNAME$" -CaseSensitive -Path "$INPUTSCONF" -quiet)) {

 ((Get-Content "$INPUTSCONF") -creplace "^(\s*?host\s*?=.*?)$","$CONFCOMMENT`r`n#`${1}`r`nhost = $LOWERHOSTNAME" ) | Set-Content "$INPUTSCONF"

 # verify
 if (Select-String -Pattern "^host = $LOWERHOSTNAME$" -CaseSensitive -Path "$INPUTSCONF" -quiet) {
  $REBOOTFLAG = $true
 }
}

# restart splunk if necessary
if ( $REBOOTFLAG ) {
 # delete GUID.  never do this on an Indexer.
 Remove-Item -LiteralPath "$splunkHome\etc\instance.cfg"
 echo restarting splunk
 Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList "$PSScriptRoot\restart_splunk.cmd"
}
