$snapins  = Get-PSSnapin XDCommands

if ($snapins -eq $null)
{
    Add-PSSnapin XDCommands
}

$ScriptRunTime = (get-date).ToFileTime()

Get-XDDesktopGroup -DesktopDetails | foreach-object {

    $DesktopGroup = $_
    $output = $DesktopGroup | Get-Member -MemberType Properties | ?{$_.name -ne "Desktops"} | %{
        $Key = $_.Name
        $Value = $DesktopGroup.$Key -join ";" 
        '{0}="{1}"' -f $Key,$Value
    }

    $Sessions = Get-XdSession -Group $_.Name
    $Desktops = $_.Desktops
    $DesktopsAvailable    = @( $Desktops | where { $_.State -eq "Available" } )
    $DesktopsUnregistered = @( $Desktops | where { $_.State -eq "NotRegistered" } )
    $DesktopsDisconnected = @( $Sessions | where { $_.State -eq "Disconnected" } )
    $DesktopsInUse        = @( $Sessions | where { $_.State -eq "Connected" } )

    $Output += 'TotalDesktops="{0}"'        -f ( $Desktops.Count ) 
    $Output += 'DesktopsAvailable="{0}"'    -f ( $DesktopsAvailable.Count )
    $Output += 'DesktopsUnregistered="{0}"' -f ( $DesktopsUnregistered.Count )
    $Output += 'DesktopsDisconnected="{0}"' -f ( $DesktopsDisconnected.Count )
    $Output += 'DesktopsInUse="{0}"'        -f ( $DesktopsInUse.Count )
    $Output += '{0}="{1}"' -f "ScriptRunTime",$ScriptRunTime
    
    Write-Host ("{0:MM/dd/yyyy HH:mm:ss} GMT - {1}" -f ((get-date).ToUniversalTime()),( $output -join " " ))
            
}

@"
Desktop Group:
	TotalDesktops
	DesktopsUnregistered
	DesktopsAvailable
	DesktopsDisconnected
	DesktopsInUse
"@ | out-null