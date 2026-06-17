$Parent = Split-Path $MyInvocation.MyCommand.Path -Parent
$Path = "{0}\ClientDetails.exe" -f $Parent
$ScriptRunTime = (get-date).ToFileTime()
$output = (& $Path) -split "\,"
$MyOutput = @()

if($output)
{
    switch -regex ($output)
    {
        "^ClientAddress"    {
                                $MyOutput += "{0}={1}" -f $_.split("=")
                                $ClientAddress = $_.Split("=")[1].Trim('"')
                                continue
                            }
        "^ClientName"       {
                                $MyOutput += "{0}={1}" -f $_.split("=")
                                $ClientName = $_.Split("=")[1].Trim('"')
                                continue
                            }
        "^ClientBuild"      { $MyOutput += "{0}={1}" -f $_.split("=") ; continue }
        "^ClientVersion"    {
                                $MyOutput += "{0}={1}" -f $_.split("=")
                                $ClientVersion = $_.Split("=")[1].Trim('"')
                                if($ClientVersion -eq "")
                                {
                                    $ClientVersion = "NoClientVersion"                                
                                }
                                continue
                            }
        "^ClientHardwareId" { $MyOutput += "{0}={1}" -f $_.split("=") ; continue }
        "^ClientProductId"  { $MyOutput += "{0}={1}" -f $_.split("=") ; continue }
    }
    
    
    if( ( $ClientVersion -eq "NoClientVersion" ) -and ( $ClientName = "mobile" ) )
    {
        $MyOutput += 'VDAClientID="{0}:{1}"' -f $ClientAddress,"mobile_NoClientVersion"
    }
    else
    {
        $MyOutput += 'VDAClientID="{0}:{1}"' -f $ClientAddress,$ClientVersion
    }
    
    Write-Host ('{0:MM/dd/yyyy HH:mm:ss} GMT - {1} ScriptRunTime="{2}"' -f ((get-date).ToUniversalTime()),($MyOutput -join " "),$ScriptRunTime)
}
