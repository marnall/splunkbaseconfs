# Get Counters
$ICASessions = Get-WMIOBject -Class Win32_PerfFormattedData_CitrixICA_ICASession -Filter "Name!='_Server Total'"
$ScriptRunTime = (get-date).ToFileTime()
# Process Counters
if($ICASessions)
{
    $ICASessions | foreach-object {
        $Session = $_
        $output = $Session | Get-Member -MemberType Properties | foreach-object {
            $Key = $_.Name
            $Value = $Session.$Key -join ";" 
            '{0}="{1}"' -f $Key,$Value
            if($Key -eq "Name")
            {
                '{0}="{1}"' -f "UserName",($Value -replace ".*\((.*)\)",'$1')
            }
        }
        $output += '{0}="{1}"' -f "ScriptRunTime",$ScriptRunTime
        Write-Host ("{0:MM/dd/yyyy HH:mm:ss} GMT - {1}" -f ((get-date).ToUniversalTime()),( $output -join " " ))
    }
}