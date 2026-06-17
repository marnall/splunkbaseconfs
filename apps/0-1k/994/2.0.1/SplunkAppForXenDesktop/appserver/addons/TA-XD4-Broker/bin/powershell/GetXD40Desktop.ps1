$snapins  = Get-PSSnapin XDCommands
if ($snapins -eq $null)
{
    Add-PSSnapin XDCommands
}

function Get-DNSHostName
{
    Param(
        $ComputerName
    )
    Try
    {
        $IPHostEntry = [system.net.dns]::GetHostEntry($ComputerName)
        $IPHostEntry.HostName
    }
    catch
    {
        $ComputerName
    }
}

$ScriptRunTime = (get-date).ToFileTime()

Get-XdVirtualDesktop -DesktopDetails | foreach-object {
	$Desktop = $_
	$output = $Desktop | Get-Member -MemberType Properties | %{
		$Key = $_.Name
		$Value = $Desktop.$Key -join ";" 
        switch -exact ($Key)
        {
            "Name"              { 
                                    '{0}="{1}"' -f "MachineName",$Value -replace "\$","" 
                                    '{0}="{1}"' -f "DNSName",( Get-DNSHostName -Computer ($Value -replace ".*\\(.*)\$",'$1') )
                                }
            "State"             {
                                    if($Value -ne "NotRegistered")
                                    {
                                        '{0}="{1}"' -f "State",$Value 
                                        '{0}="{1}"' -f "RegistrationState","Registered" 
                                        '{0}="{1}"' -f "SummaryState","Available"
                                    }
                                    else
                                    {
                                        '{0}="{1}"' -f "State",$Value 
                                        '{0}="{1}"' -f "RegistrationState","UnRegistered"
                                        '{0}="{1}"' -f "SummaryState","UnRegistered" 

                                    }
                                }
            "GroupName"         { 
                                    '{0}="{1}"' -f "DesktopGroupName",$Value 
                                    '{0}="{1}"' -f "CatalogName",$Value 
                                }
            "MaintenanceMode"   { '{0}="{1}"' -f "InMaintenanceMode",$Value }
            "HostingName"       { '{0}="{1}"' -f "HostingServerName",$Value }
            "OSName"            { '{0}="{1}"' -f "OSType",$Value }
            default             { '{0}="{1}"' -f $Key,$Value }
        }

	}

    $output += '{0}="{1}"' -f "ScriptRunTime",$ScriptRunTime
	Write-Host ("{0:MM/dd/yyyy HH:mm:ss} GMT - {1}" -f ((get-date).ToUniversalTime()),( $output -join " "))
			
} 

@"
Desktop Info:
	MachineName
	PowerState
	InMaintenanceMode
	DesktopGroupName
	CatalogName
	OSType
	IPAddress
	AgentVersion
	HostingServerName
	HypervisorConnectionName
	HostedMachineName
	LastDeregistrationReason
	LastDeregistrationTime
	LastDeregistrationReason
    RegistrationState
    SummaryState
"@ | out-null

