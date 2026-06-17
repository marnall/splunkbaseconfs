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

Get-BrokerDesktopGroup -MaxRecordCount 10000 | foreach-object {
    $DesktopGroup = $_
    $output = $DesktopGroup | Get-Member -MemberType Properties | %{
        $Key = $_.Name
        $Value = $DesktopGroup.$Key -join ";" 
        '{0}="{1}"' -f $Key,$Value
    }

    $output += '{0}="{1}"' -f "ScriptRunTime",$ScriptRunTime
    
    Write-Host ("{0:MM/dd/yyyy HH:mm:ss} GMT - {1}" -f ((get-date).ToUniversalTime()),( $output -join " " ))
            
}