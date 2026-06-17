$snapins  = Get-PSSnapin | where { $_.Name -like "Citrix*" }

function ConvertTo-Name
{
    param($sid)
    $ID = New-Object System.Security.Principal.SecurityIdentifier($sid)
    $User = $ID.Translate( [System.Security.Principal.NTAccount])
    $User.Value
}

if ($snapins -eq $null)
{
   Get-PSSnapin -Registered "Citrix*" | Add-PSSnapin
   Add-PSSnapin "PvsPsSnapin"
}

$ScriptRunTime = (get-date).ToFileTime()

Get-BrokerSession -MaxRecordCount 10000 | foreach-object {
    $Session = $_
    $output = $Session | Get-Member -MemberType Properties | %{
        $Key = $_.Name
        $Value = $Session.$Key -join ";" 
        if($Key -eq "DesktopSID")
        {
            '{0}="{1}"' -f $key,$Value
            '{0}="{1}"' -f "DesktopName",((ConvertTo-Name -sid $Value) -replace "\$","")
        }
        else
        {
            '{0}="{1}"' -f $Key,$Value
        }
    }

    if($Session.SessionState -match "Active|Disconnected|PreparingSession")
    {
        if( ( $Session.ClientVersion -eq "" ) -and ( $Session.ClientName = "mobile" ) )
        {
            $output += 'VDAClientID="{0}:{1}"' -f $Session.ClientAddress,"mobile_NoClientVersion"
        }
        else
        {
            $output += 'VDAClientID="{0}:{1}"' -f $Session.ClientAddress,$Session.ClientVersion
        }
    }
    else
    {
        $output += 'VDAClientID="NonBrokeredSession"'
    }

    $output += '{0}="{1}:{2}:{3}"' -f "SessionUID",$Session.StartTime.ToFileTime(),$Session.UserSID,$Session.DesktopSID
    $output += '{0}="{1}"' -f "ScriptRunTime",$ScriptRunTime
    
    Write-Host ("{0:MM/dd/yyyy HH:mm:ss} GMT - {1}" -f ((get-date).ToUniversalTime()),( $output -join " " ))
    
}




