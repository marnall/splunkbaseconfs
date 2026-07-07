## This script generates DefenderATPStatus Logs, useful to check whether DefenderATP is installed on the system or not.


# Checks if the registry value is present or not
function Get-RegistryValue {
    param (
        [parameter(Mandatory=$true)]
        [ValidateNotNullOrEmpty()]$Path,
        [parameter(Mandatory=$true)]
        [ValidateNotNullOrEmpty()]$Value
    )
    try {
        $Return = Get-ItemProperty -Path $Path | Select-Object -ExpandProperty $Value -ErrorAction Stop
        if ($Return.Length -eq 0){
            return "NotFound"
        }
        return $Return
    }
    catch {
        return "NotFound"
    }
}


if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows Advanced Threat Protection\Status'){
    try{
        $OnboardingState = Get-RegistryValue -Path "HKLM:\SOFTWARE\Microsoft\Windows Advanced Threat Protection\Status" -Value OnboardingState

        if ($OnboardingState -eq "NotFound"){
            Write-Output "The defender ATP is not installed.";
        }
        else{
            $LastConnected = " "
            try{
                $LastConnected = Get-RegistryValue -Path "HKLM:\SOFTWARE\Microsoft\Windows Advanced Threat Protection\Status" -Value LastConnected
                $LastConnected = [DateTime]::FromFiletimeUtc([Int64]::Parse($LastConnected))
                $LastConnected = "" + $LastConnected + " UTC"
            }
            catch{
                $LastConnected = " "
            }

            Write-Output ( "The defender ATP is installed. OnboardingState=" + $OnboardingState + ", LastConnected=" + $LastConnected ) ;
        }
    }
    catch{
        Write-Output "The defender ATP is not installed.";
    }
}
else{
    Write-Output "The defender ATP is not installed.";
}

exit
