$source = Get-CimInstance -Class Win32_Product  -Filter "Name='UniversalForwarder'" | select -ExpandProperty InstallLocation
$loc = 'etc\apps\uf_win_upgrade\bin\upgrade.ps1'
$scriptDir = $source+$loc
Invoke-Command -ScriptBlock {param($scriptDir) C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -command $scriptDir} -ArgumentList $scriptDir