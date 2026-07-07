
#    Version = 1.0.0
#    Change History at bottom

param([string]$ip0 , [string]$remvCheck, [string]$uname, [string]$password, [string]$new_mode  )

############################################################################################
# Set to true for PowerShell remoting Copy-Item -ToSession.  Set to false to use \\server\c$
############################################################################################
$runmode = $new_mode
#$runmode = "mbbr_wmi"

$mbbrversion = 3

###########################################################################################
# Debugging - Fill and uncomment variables below
###########################################################################################
#$remvCheck = 'remove'
#$ip0 = '10.0.0.4'
#$uname = '127.0.0.1\Administrator'
#$password = ''

[string[]] $ip = $ip0 -split "\s+"

#$splunkhomeloc = $Env:SPLUNK_HOME
$splunkhomeloc = 'C:\Program Files\Splunk'
$logFileLoc    = $splunkhomeloc+'\var\log\splunk\mbbr_powershell.log'
$mbbrBatLoc    = $splunkhomeloc+'\etc\apps\mbbr\bin'
$mbbrExeLoc    = $splunkhomeloc+'\etc\apps\mbbr\bin'

$Time = Get-Date
"$Time $ip0 $remvCheck $uname ********" | out-file $logFileLoc -append

if (!(Test-Path $logFileLoc))
{
   New-Item -path $splunkhomeloc'\var\log\splunk' -name mbbr_powershell.log -type "file"
}

# Convert password to secure string
$pass = ConvertTo-SecureString -AsPlainText $password -Force
$Cred = New-Object System.Management.Automation.PSCredential -ArgumentList $uname,$pass


Function QuickCheckPort {
  # Does an asynchronous TCP connection to IP/Port.  Timeout terminates much
  # quicker than other tests lke PING.  Port 135 should always be reachable
  # 445 for file sharing.  WMI is random unless locked down.  WinRM has 5985 Http 5986 Https
  [CmdletBinding()]
    PARAM(
    [Parameter(Mandatory =$true, ValueFromPipeline=$true)]  [String]$computername,
    [Parameter(Mandatory =$true, ValueFromPipeline=$true)]  [String]$port,
    [Parameter(Mandatory =$false, ValueFromPipeline=$true)] [String]$timeoutms = 1500
  )
    $tcpobject = new-Object system.Net.Sockets.TcpClient
    $connect   = $tcpobject.BeginConnect($computername,$port,$null,$null)
    $wait      = $connect.AsyncWaitHandle.WaitOne($timeoutms,$false)
    If (-Not $Wait) {
        $false
    } Else
    {
        $error.clear()
        $tcpobject.EndConnect($connect) | out-Null
        If ($Error[0]) {
            # Write-warning ("{0}" -f $error[0].Exception.Message)
            $false
        } Else
        { $true
        }
    }
}

Function Deploy-WinRm {
    #################################################################################################
    # Deploy using PowerShell Remoting WinRM
    #################################################################################################
    [CmdletBinding()]
    Param(
       [Parameter(position=0, ValueFromPipeline = $true)][String]$computername,
       [String]$share,
       [PsCredential] $cred,
       [String]$sourcepath,
       [String]$deploypath,
       [Array]$deployfiles,
       [String]$runfile
    )

    BEGIN {}

    PROCESS {
        $Time = Get-Date
		# Required log line to start Transaction
		"$Time dest_ip=$computername action=""Powershell script execution started for the ip $ip *********""" | out-file $logFileLoc -append
        "$Time dest_ip=$computername action=""$computername $remvCheck $Username ********""" | out-file $logFileLoc -append
        "$Time dest_ip=$computername status=PENDING action=""Pending for further action""" | out-file $logFileLoc -append

        $online = QuickCheckPort -computername $computername -port 135
        if (-not $online) {
            "$Time dest_ip=$computername status=FAILED action=""MBBR script execution"" message=""Offline""" | out-file $logFileLoc -append
            # "$Time dest_ip=$computername status=FAILED action=""MBBR script execution"" message="" $_.Exception.Message """| out-file $logFileLoc -append
            return $time,$computername,$false
        }

        try{
            # If a PSSession already exits, remove it
            $currsesssion = Get-PSSession -ComputerName $computername -credential $Cred
            "$Time dest_ip=$computername action=""Removing existing pssession""" | out-file $logFileLoc -append
            $currsesssion | Remove-PSSession


            # creating pssession with the remote computer
            "$Time dest_ip=$computername action=""Creating pssession connection""" | out-file $logFileLoc -append
            $psSession = New-PSSession -ComputerName $computername -credential $Cred  -ErrorAction Stop
            "$Time dest_ip=$computername status=CONNECTED action=""Connected to remote host""" | out-file $logFileLoc -append

            # reading the system drive of the remote computer.  cmd/c used, so environment variable is resolved
            $sysdrive = Invoke-Command -Session $psSession -ScriptBlock {Invoke-Expression -Command:"cmd.exe /c 'echo %SystemDrive%'"}  -ErrorAction Stop
            "$Time dest_ip=$computername action=""Read system drive""" | out-file $logFileLoc -append

            # create mbber_remediation folder in the remote computer if not existing
            $Test =   Invoke-Command -Session $psSession -ScriptBlock {Invoke-Expression -Command:"cmd.exe /c 'IF EXIST $sysdrive\mbbr_remediation\ (echo yes) ELSE (echo no)'"}

            if($Test -eq 'no'){
                Invoke-Command -Session $psSession -ScriptBlock {Invoke-Expression -Command:"cmd.exe /c 'mkdir $sysdrive\mbbr_remediation'"}    -ErrorAction Stop
                "$Time dest_ip=$computername status=""CREATED directory"" action=""Created %sysdrive%\mbbr_remediation\ folder in the remote host""" | out-file $logFileLoc -append

            }else{
                if($Test -eq 'yes') {
                    "$Time dest_ip=$computername status=""CREATED directory"" action=""%sysdrive%\mbbr_remediation\ folder already exists in the remote host""" | out-file $logFileLoc -append
                } else {
                    "$Time dest_ip=$computername status=""CREATED directory"" action=""%sysdrive%\mbbr_remediation\ folder status undetermined""" | out-file $logFileLoc -append
                }
            }

            "$Time dest_ip=$computername action=""Copying by Winrm""" | out-file $logFileLoc -append
            foreach ($file in $deployfiles){
                Copy-Item -Path $sourcepath\$file -Destination $sysdrive\$deploypath -ToSession $psSession -Force -ErrorAction Stop
                "$Time dest_ip=$computername action=""Copied $file in the remote host""" | out-file $logFileLoc -append
            }

            # initiate mbbr.bat file execution in the remote computer
            "$Time dest_ip=$computername action=""$runfile execution is about to start..""" | out-file $logFileLoc -append
            $result = Invoke-Command -Session $psSession -ScriptBlock ([ScriptBlock]::Create("& $sysdrive\$deploypath\$runfile")) -AsJob -ErrorAction Stop
	        "$Time dest_ip=$computername status=PROCESSING action=""mbbr.bat execution triggered"" message=""$($result.Name) $($result.State)"""| out-file $logFileLoc -append
            # $result | Format-List * -Force
            # TODO: Review stopping PsSession
		    # $psSession | Remove-PSSession
            # "$Time dest_ip=$computername action=""Remove pssession""" | out-file $logFileLoc -append


        }catch{
            $Time = Get-Date
            "$Time dest_ip=$computername status=FAILED action=""MBBR script execution"" message="" $_.Exception.Message """| out-file $logFileLoc -append
            Write-Error "$Time title=""MBBR Batch script execution failed in remote ip $computername"" message="" $_.Exception.Message "
        }

    } # PROCESS END

} # End DeployWinrm


Function Deploy-Wmi {
    [CmdletBinding()]
    Param(
      [Parameter(position=0, ValueFromPipeline = $true)][String]$computername,
       [String]$share,
       [PsCredential] $cred,
       [String]$sourcepath,
       [String]$deploypath,
       [Array]$deployfiles,
       [String]$runfile
    )

    BEGIN {}

    PROCESS {
        $Time = Get-Date
		# Required log line to start Transaction
		"$Time dest_ip=$computername action=""Powershell script execution started for the ip $ip *********""" | out-file $logFileLoc -append
        "$Time dest_ip=$computername action=""$computername $remvCheck $Username ********""" | out-file $logFileLoc -append
        "$Time dest_ip=$computername status=PENDING action=""Pending for further action""" | out-file $logFileLoc -append

        $success = $false
        $online = QuickCheckPort -computername $computername -port 135
        if (-not $online) {
            "$Time dest_ip=$computername status=FAILED action=""MBBR script execution"" message=""Offline""" | out-file $logFileLoc -append
            return $time,$computername,$success
        }

        try {
            ###################################################################################
            # Test WMI Connection and get SystemDrive
            ###################################################################################
            "$Time dest_ip=$computername action=""Reading WMI connection""" | out-file $logFileLoc -append
            $wmiobject = Get-WMIObject -class Win32_OperatingSystem -Computername $computername -Credential $cred
            # Write-Host 'PSComputerName : ' $wmiobject.PSComputerName
            # Write-Host 'Caption        : ' $wmiobject.Caption
            # Write-Host 'LastBootUpTime : ' $wmiobject.LastBootUpTime
            # Write-Host 'OSArchitecture : ' $wmiobject.OSArchitecture
            # Write-Host 'OSLanguage     : ' $wmiobject.OSLanguage
            # Write-Host 'SerialNumber   : ' $wmiobject.SerialNumber
            # Write-Host 'SystemDrive    : ' $wmiobject.SystemDrive
            # Write-Host 'Version        : ' $wmiobject.Version


            $macaddress =""
            $nicdescription=""
            $nicdhcpenabled = ""
            $nicdhcpleaseexpires=""
            $colItems = get-wmiobject -class "Win32_NetworkAdapterConfiguration" -computername $computername -Credential $cred  |Where{$_.IpEnabled -Match "True" -and $_.Index -eq 1}
            foreach ($objItem in $colItems)
            {
               # $objItem | select Description,MACAddress,Index,DHCPEnabled,DHCPLeaseExpires
               $macaddress=$objitem.MACAddress
               $nicdescription=$objItem.Description
               $nicdhcpenabled=$objitem.DHCPEnabled
               $nicdhcpleaseexpiers=$objItem.DHCPLeaseExpires
            }

            ###################################################################################
            # If share is not specified, default it to x$ from remote env::SystemDrive
            ###################################################################################
            if ($share -eq "") {
                $share = $wmiobject.SystemDrive.Substring(0,1) + '$'
            }

            NET USE "\\$computername\$share" /DELETE 2> null
            $username = $cred.UserName
            NET USE \\$computername\$share $cred.GetNetworkCredential().password /USER:$username
            ###################################################################################
            # Make target directory folder
            ###################################################################################
            $newdir  = "Filesystem::\\" + $computername + "\" + $share + "\" + $deploypath
            $makedir = New-Item -path $newdir -ItemType "Directory" -Force
            "$Time dest_ip=$computername status=""CREATED directory"" action=""Created $newdir folder in the remote host""" | out-file $logFileLoc -append

            ###################################################################################
            # Deploy files
            ##################################################################################
            $destination = '\\' + $computername + '\' + $share + '\' + $deploypath
            foreach ($file in $deployfiles) {
                Copy-Item -Path $sourcepath\$file -Destination $destination -Force -ErrorAction Stop
                "$Time dest_ip=$computername action=""Copied $file in the remote host""" | out-file $logFileLoc -append
            }

            ###################################################################################
            # Start remote process via WMI
            ###################################################################################
            $cmd = "cmd.exe /c %SystemDrive%\$deploypath\$runfile"
            "$Time dest_ip=$computername action=""$runfile execution is about to start..""" | out-file $logFileLoc -append
            $process = Invoke-WmiMethod -ComputerName $computername -Class win32_process -Name create -ArgumentList $cmd -Credential $cred -ErrorAction Stop
            "$Time dest_ip=$computername status=PROCESSING action=""mbbr.bat execution triggered"" message=""ProcessID $($process.ProcessID) ReturnValue $($process.ReturnValue)"""| out-file $logFileLoc -append
            $success = $true
        } catch
        {
            $Time = Get-Date
            "$Time dest_ip=$computername status=FAILED action=""MBBR script execution"" message="" $_.Exception.Message """| out-file $logFileLoc -append
            Write-Error "$Time title=""MBBR Batch script WMI execution failed in remote ip $ip1"" message="" $_.Exception.Message "
            NET USE "\\$computername\$share" /DELETE 2> null
            # return $computername,$success,$macaddress,$wmiobject.PSComputerName,$wmiobject.caption,$wmiobject.SerialNumber,$process.ProcessID
        }
        NET USE "\\$computername\$share" /DELETE 2> null
        # return $computername,$success,$macaddress,$wmiobject.PSComputerName,$wmiobject.caption,$wmiobject.SerialNumber,$process.ProcessID
    } # PROCESS END
}



# Choose either scanning or removal batch file based on the input from the Python script output
If($remvCheck -eq 'remove'){
    $runfile = 'mbbr_remove_batch.bat'
}Else{
    $runfile = 'mbbr_scan_batch.bat'
}

# Handle machine\username for non-domain endpoints
if ($uname -like "127.0.0.1\*") {
   $domaincred = $false
} else {
   $domaincred = $true
}

switch ($mbbrversion) {
    '2'
        {
            $deployfiles = @('mbbr.EXE','mbbr_scan_batch.bat','mbbr_remove_batch.bat')
        }
    '3' {
            $deployfiles = @('mbbr-3.EXE','mbbr_scan_batch.bat','mbbr_remove_batch.bat','xlist1.json','ioclist1.json')
        }
    default {
        Write-Error 'Error'
    }
}

switch ($runmode) {
    "mbbr_winrm"
        {
            # If non-domain machines, add all local computers to the trusted hosts list
            # Reference https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_remote_troubleshooting?view=powershell-6
            if (-not $domaincred)
            {
                # Could do individually, but difficult to manage.  This list is deleted at end of run.
                # Set-Item wsman:localhost\client\trustedhosts -Value $ip1 -Concatenate -Force
                Set-Item wsman:localhost\client\trustedhosts -Value * -Force
            }

            $ip | Deploy-WinRm -cred $Cred -sourcepath $mbbrBatLoc -deployfiles $deployfiles -deploypath 'mbbr_remediation' `
                -runfile $runfile

            if (-not $domaincred)
            {
                    # Blank out TrustedHosts
                    Set-Item wsman:localhost\client\trustedhosts -Value '' -Force
            }

        }
    "mbbr_wmi"
        {
             $ip | Deploy-Wmi -cred $Cred -sourcepath $mbbrBatLoc -deployfiles $deployfiles -deploypath 'mbbr_remediation' `
                -runfile $runfile

        }
     default
        {
           Write-Error "Its an error"
        }

}

