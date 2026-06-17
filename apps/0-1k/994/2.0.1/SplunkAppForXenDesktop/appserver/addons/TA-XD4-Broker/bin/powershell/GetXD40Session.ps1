$snapins  = Get-PSSnapin XDCommands

if ($snapins -eq $null)
{
    Add-PSSnapin XDCommands
}

$ScriptRunTime = (get-date).ToFileTime()

Get-XDSession -SessionDetails | foreach-object {
    $Session = $_
    $output = $Session | Get-Member -MemberType Properties | %{
        $Key = $_.Name
        $Value = $Session.$Key -join ";" 
        switch -exact ($Key)
        {
            "DesktopName"       { '{0}="{1}"' -f $Key,$Value -replace "\$","" ; continue}
            "State"             {
                                    if($Value -eq "Connected")
                                    {
                                        'SessionState="Active"' 
                                    }
                                    else
                                    {
                                        'SessionState="Disconnected"'
                                    }
                                    'XD40State="{0}"' -f $Value
                                    continue
                                }
            "EndpointAddress"   { '{0}="{1}"' -f "LaunchedViaIP",$Value ; continue}
            "EndpointId"        { '{0}="{1}"' -f "DeviceId",$Value ; continue}
            "EndpointName"      { '{0}="{1}"' -f "ClientName",$Value ; continue}
            "DesktopSid"        { '{0}="{1}"' -f "DesktopSID",$Value ; continue}
            "UserSid"           { '{0}="{1}"' -f "UserSID",$Value ; continue}
            default             { '{0}="{1}"' -f $Key,$Value ; continue}
        }
    }
    
    $output += '{0}="{1}:{2}:{3}"' -f "SessionUID",$Session.StartTime.ToFileTime(),$Session.UserSID,$Session.DesktopSID
    $output += '{0}="{1}"' -f "ScriptRunTime",$ScriptRunTime

    Write-Host ("{0:MM/dd/yyyy HH:mm:ss} GMT - {1}" -f ((get-date).ToUniversalTime()),( $output -join " " ))
} 

@"
SessionState
	BrokeringTime
	StartTime
	SessionStateChangeTime
	ClientAddress
	 ClientName
	 ClientVersion
	 DesktopSID
	 DeviceId
	 HardwareId
	 Protocol
	 UserSID
	UserName
	LaunchedViaIP
	ConnectedViaIP
"@ | out-null 



