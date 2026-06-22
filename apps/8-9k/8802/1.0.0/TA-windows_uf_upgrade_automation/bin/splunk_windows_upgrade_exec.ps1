###################################################
########### SPLUNK WINDOWS UPGRADE EXEC ###########
###################################################
#
# Purpose:
# This script performs the actual Splunk Universal Forwarder upgrade.
#
# This script is normally launched by the Windows Scheduled Task created by:
# splunk_windows_upgrade_task_setup.ps1
#
# This execution script performs:
# - Log path initialization
# - State path initialization
# - MSI discovery
# - Installer hash calculation
# - Persistent JSON state updates
# - Splunkd stop
# - MSI upgrade execution
# - Upgrade success/failure logging
# - MSI cleanup
# - Scheduled task cleanup
# - Splunkd start
#
# JSON State Purpose:
# The JSON state file prevents endless retry loops. If the MSI cannot be
# removed after an upgrade attempt, Splunk may restart and run this setup
# script again after Splunk starts. The state file allows the setup script
# and exec script to detect that the same MSI was already attempted and skip it.
#
# State file location:
# C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json
#
# Force retry:
# To intentionally retry the same MSI, create this file before setup runs:
# C:\ProgramData\SplunkUpgrade\state\force_retry.flag
#

###################################################
# Path and runtime variables
###################################################

$scriptPath = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$rootDir = Split-Path -Path $scriptPath -Parent

$LogFolder = "C:\ProgramData\SplunkUpgrade"
$LogFile = Join-Path $LogFolder "splunk_upgrade_exec.log"

$StateFolder = Join-Path $LogFolder "state"
$StateFile = Join-Path $StateFolder "splunk_upgrade_state.json"

$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$msiLogFile = Join-Path $LogFolder "splunk_upgrade_msi_$runStamp.log"

$InstallerFolder = Join-Path $rootDir "splunk_installer"

$taskName = "z_splunk_upgrader_task_v01"
$splunkBinary = "C:\Program Files\SplunkUniversalForwarder\bin\splunk.exe"


###################################################
# Logging and path initialization
###################################################

function Initialize-LogPath {
    param (
        [string]$LogFolder,
        [string]$LogFile
    )

    if (-not (Test-Path -LiteralPath $LogFolder)) {
        New-Item -ItemType Directory -Force -Path $LogFolder | Out-Null
    }

    if (-not (Test-Path -LiteralPath $LogFile)) {
        New-Item -ItemType File -Force -Path $LogFile | Out-Null
    }

    # Ensure common execution contexts can write to the log directory.
    & icacls $LogFolder /inheritance:e | Out-Null
    & icacls $LogFolder /grant `
        "NT AUTHORITY\SYSTEM:(OI)(CI)F" `
        "BUILTIN\Administrators:(OI)(CI)F" `
        "Users:(OI)(CI)M" /C | Out-Null

    & icacls $LogFile /inheritance:e | Out-Null
    & icacls $LogFile /grant `
        "NT AUTHORITY\SYSTEM:F" `
        "BUILTIN\Administrators:F" `
        "Users:M" /C | Out-Null
}

function Initialize-StatePath {
    if (-not (Test-Path -LiteralPath $StateFolder)) {
        New-Item -ItemType Directory -Force -Path $StateFolder | Out-Null
    }

    # State must persist across Splunk restarts and script reruns.
    & icacls $StateFolder /inheritance:e | Out-Null
    & icacls $StateFolder /grant `
        "NT AUTHORITY\SYSTEM:(OI)(CI)F" `
        "BUILTIN\Administrators:(OI)(CI)F" `
        "Users:(OI)(CI)M" /C | Out-Null
}

function Write-Log {
    param (
        [string]$Message
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $cleanMessage = $Message -replace "(`r`n|`n|`r)", " "
    $entry = "$timestamp  $cleanMessage"

    # IMPORTANT:
    # Do not use Write-Output here.
    # Write-Output writes to the success pipeline and can pollute return values
    # from functions such as Get-InstallerHash and Remove-SplunkInstaller.
    # That was causing installer_hash and cleanup state to become incorrect.

    $maxRetries = 8
    $retry = 0
    $written = $false

    while (-not $written -and $retry -lt $maxRetries) {
        try {
            $fs = [System.IO.File]::Open(
                $LogFile,
                [System.IO.FileMode]::Append,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::ReadWrite
            )

            $sw = New-Object System.IO.StreamWriter($fs)
            $sw.WriteLine($entry)
            $sw.Close()
            $fs.Close()

            $written = $true
        }
        catch {
            Start-Sleep -Milliseconds 200
            $retry++
            Write-Warning "Log write attempt $retry failed: $($_.Exception.Message.Trim())"
        }
    }

    if (-not $written) {
        Write-Warning "FAILED TO WRITE LOG AFTER $maxRetries ATTEMPTS -> $LogFile"
    }
}


###################################################
# JSON state helpers
###################################################

function Get-InstallerHash {
    param (
        [string]$Path
    )

    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    try {
        $hashResult = Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop

        if ($hashResult.Hash -match '^[A-Fa-f0-9]{64}$') {
            return $hashResult.Hash
        }

        Write-Log "eventcode=9822 status=Failure message=""Failed to calculate installer hash."" details=""Hash result was empty or invalid."" installer_path=""$Path"""
        return $null
    }
    catch {
        Write-Log "eventcode=9822 status=Failure message=""Failed to calculate installer hash."" details=""$($_.Exception.Message.Trim())"" installer_path=""$Path"""
        return $null
    }
}

function Get-UpgradeState {
    if (-not (Test-Path -LiteralPath $StateFile)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $StateFile -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Write-Log "eventcode=9822 status=Failure message=""Failed to read upgrade state file."" details=""$($_.Exception.Message.Trim())"" state_file=""$StateFile"""
        return $null
    }
}

function Get-NextAttemptCount {
    param (
        [object]$ExistingState,
        [string]$InstallerHash
    )

    if ($ExistingState -and $ExistingState.installer_hash -eq $InstallerHash -and $ExistingState.attempt_count) {
        return ([int]$ExistingState.attempt_count)
    }

    return 1
}

function Set-UpgradeState {
    param (
        [string]$InstallerName,
        [string]$InstallerHash,
        [string]$TargetVersion,
        [string]$PreviousVersion,
        [string]$CurrentVersion,
        [int]$AttemptCount,
        [string]$LastStatus,
        [string]$CleanupStatus,
        [string]$LastEventCode,
        [string]$LastError,
        [string]$MSILogFile,
        [bool]$DoNotRetry
    )

    Initialize-StatePath

    $state = [ordered]@{
        installer_name     = $InstallerName
        installer_hash     = $InstallerHash
        target_version     = $TargetVersion
        previous_version   = $PreviousVersion
        current_version    = $CurrentVersion
        attempt_count      = $AttemptCount
        last_status        = $LastStatus
        cleanup_status     = $CleanupStatus
        do_not_retry       = $DoNotRetry
        last_eventcode     = $LastEventCode
        last_error         = $LastError
        msi_log_file       = $MSILogFile
        last_attempt_time  = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        state_source       = "exec"
        state_file_version = "1.0"
    }

    try {
        $stateJson = $state | ConvertTo-Json -Depth 5

        $fs = [System.IO.File]::Open(
            $StateFile,
            [System.IO.FileMode]::Create,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )

        $sw = New-Object System.IO.StreamWriter($fs)
        $sw.Write($stateJson)
        $sw.Close()
        $fs.Close()

        Write-Log "eventcode=9821 status=Success message=""Upgrade state file written successfully."" installer_name=""$InstallerName"" installer_hash=""$InstallerHash"" target_version=""$TargetVersion"" attempt_count=""$AttemptCount"" last_status=""$LastStatus"" cleanup_status=""$CleanupStatus"" do_not_retry=""$DoNotRetry"""

        return $true
    }
    catch {
        Write-Log "eventcode=9822 status=Failure message=""Failed to write upgrade state file."" details=""$($_.Exception.Message.Trim())"" state_file=""$StateFile"""
        return $false
    }
    finally {
        if ($sw) {
            $sw.Dispose()
        }

        if ($fs) {
            $fs.Dispose()
        }
    }
}

function Get-VersionFromInstallerName {
    param (
        [string]$InstallerName
    )

    if ($InstallerName -match '(\d+\.\d+\.\d+)') {
        return $Matches[1]
    }

    return "Unknown"
}

function Get-VersionFromSplunkOutput {
    param (
        [string]$VersionOutput
    )

    if ($VersionOutput -match '(\d+\.\d+\.\d+)') {
        return $Matches[1]
    }

    return "Unknown"
}


###################################################
# Event logging helpers
###################################################

function Log-SplunkdSuccess {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$SplunkdStatus
    )

    Write-Log "eventcode=$EventCode status=Success message=""$Message"" splunkd_status=""$SplunkdStatus"""
}

function Log-SplunkdFailure {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$Details,
        [string]$SplunkdStatus
    )

    Write-Log "eventcode=$EventCode status=Failure message=""$Message"" details=""$Details"" splunkd_status=""$SplunkdStatus"""
}

function Log-UpgradeSuccess {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$PreviousVersion,
        [string]$CurrentVersion,
        [string]$MSILogFile
    )

    Write-Log "eventcode=$EventCode status=Success message=""$Message"" previous_version=""$PreviousVersion"" current_version=""$CurrentVersion"" upgrade_success=true msi_log_file=""$MSILogFile"""
}

function Log-UpgradeFailure {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$Details,
        [string]$PreviousVersion,
        [string]$CurrentVersion,
        [string]$MSILogFile
    )

    Write-Log "eventcode=$EventCode status=Failure message=""$Message"" details=""$Details"" previous_version=""$PreviousVersion"" current_version=""$CurrentVersion"" upgrade_success=false msi_log_file=""$MSILogFile"""
}

function Log-TaskEventFailure {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$Details,
        [string]$TaskName
    )

    Write-Log "eventcode=$EventCode status=Failure message=""$Message"" details=""$Details"" taskname=""$TaskName"""
}

function Log-MSIRemovalSuccess {
    param (
        [string]$SplunkFileName
    )

    Write-Log "eventcode=9823 status=Success message=""Splunk installer removed successfully."" installer_name=""$SplunkFileName"""
}

function Log-MSIRemovalFailure {
    param (
        [string]$Details,
        [string]$SplunkFileName
    )

    Write-Log "eventcode=9807 status=Failure message=""Failed to remove installer $SplunkFileName"" details=""$Details"""
}


###################################################
# Scheduled task cleanup
###################################################

function Remove-ScheduledTaskSafe {
    param (
        [string]$TaskName
    )

    try {
        if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
            Write-Host "Scheduled task removed successfully."
        }
    }
    catch {
        Log-TaskEventFailure `
            -EventCode "9804" `
            -Message "Failed to remove scheduled task." `
            -Details $($_.Exception.Message.Trim()) `
            -TaskName $TaskName
    }
}


###################################################
# Installer cleanup
###################################################

function Remove-SplunkInstaller {
    param (
        [string]$InstallPath,
        [string]$SplunkFileName
    )

    if (-not $InstallPath) {
        return $false
    }

    try {
        Remove-Item -LiteralPath $InstallPath -Force -ErrorAction Stop

        Log-MSIRemovalSuccess `
            -SplunkFileName $SplunkFileName

        return $true
    }
    catch {
        Log-MSIRemovalFailure `
            -Details $($_.Exception.Message.Trim()) `
            -SplunkFileName $SplunkFileName

        return $false
    }
}


###################################################
# Splunk service control
###################################################

function Splunkd-Start {
    param (
        [string]$SplunkPath = $splunkBinary
    )

    $splunk_status = ""

    try {
        & $SplunkPath start 2>&1 | Out-Null

        $maxRetries = 3
        $retry = 0

        do {
            Start-Sleep -Seconds 10
            $splunk_status = & $SplunkPath status 2>&1
            $retry++
        } while (($splunk_status -notmatch "SplunkForwarder:\s*Running") -and ($retry -lt $maxRetries))

        if ($splunk_status -match "SplunkForwarder:\s*Running") {
            Log-SplunkdSuccess `
                -EventCode "9808" `
                -Message "Splunkd started successfully." `
                -SplunkdStatus $splunk_status
        }
        else {
            throw "Splunkd failed to start within the timeout period. Max attempts = '$maxRetries'"
        }
    }
    catch {
        Log-SplunkdFailure `
            -EventCode "9809" `
            -Message "Failed to start Splunkd." `
            -Details $($_.Exception.Message.Trim()) `
            -SplunkdStatus $splunk_status

        exit 1
    }
}

function Splunkd-Stop {
    param (
        [string]$SplunkPath = $splunkBinary
    )

    $splunk_status = ""

    try {
        & $SplunkPath stop 2>&1 | Out-Null

        $maxRetries = 3
        $retry = 0

        do {
            Start-Sleep -Seconds 10
            $splunk_status = & $SplunkPath status 2>&1
            $retry++
        } while (($splunk_status -notmatch "SplunkForwarder:\s*Stopped") -and ($retry -lt $maxRetries))

        if ($splunk_status -match "SplunkForwarder:\s*Stopped") {
            Log-SplunkdSuccess `
                -EventCode "9810" `
                -Message "Splunkd stopped successfully." `
                -SplunkdStatus $splunk_status
        }
        else {
            throw "Splunkd failed to stop within the timeout period."
        }
    }
    catch {
        Log-SplunkdFailure `
            -EventCode "9811" `
            -Message "Failed to stop Splunkd." `
            -Details $($_.Exception.Message.Trim()) `
            -SplunkdStatus $splunk_status

        throw
    }
}


###################################################
# MSI upgrade workflow
###################################################

function MSI-Upgrade-Splunk {
    param (
        [string]$MSILogFile,
        [string]$InstallPath,
        [string]$SplunkFileName,
        [string]$InstallerHash,
        [string]$TargetVersion,
        [int]$AttemptCount
    )

    $previous_version = & $splunkBinary version 2>&1
    $previous_version_clean = Get-VersionFromSplunkOutput -VersionOutput $previous_version
    $current_version = "Unknown"

    $upgradeStatus = "unknown"
    $cleanupStatus = "not_started"
    $lastEventCode = ""
    $lastError = ""

    # Important:
    # Mark the MSI as attempted BEFORE stopping Splunk or launching msiexec.
    # This protects against loops if the service restarts, the script crashes,
    # or the MSI remains in the installer folder.
    $stateWriteSucceeded = Set-UpgradeState `
    -InstallerName $SplunkFileName `
    -InstallerHash $InstallerHash `
    -TargetVersion $TargetVersion `
    -PreviousVersion $previous_version_clean `
    -CurrentVersion $current_version `
    -AttemptCount $AttemptCount `
    -LastStatus "upgrade_started" `
    -CleanupStatus "not_started" `
    -LastEventCode "9821" `
    -LastError "" `
    -MSILogFile $MSILogFile `
    -DoNotRetry $true

if ($stateWriteSucceeded -ne $true) {
    Write-Log "eventcode=9822 status=Failure message=""Exec cannot continue because upgrade state file could not be written."" details=""MSI upgrade will not start because retry-loop protection state could not be persisted."" state_file=""$StateFile"""
    Remove-ScheduledTaskSafe -TaskName $taskName
    exit 1
}
    try {
        Splunkd-Stop

        $process = Start-Process msiexec.exe `
            -ArgumentList "/i `"$InstallPath`" AGREETOLICENSE=Yes /quiet /norestart /Le `"$MSILogFile`"" `
            -Wait `
            -NoNewWindow `
            -PassThru

        $current_version = & $splunkBinary version 2>&1
        $current_version_clean = Get-VersionFromSplunkOutput -VersionOutput $current_version

        if ($process.ExitCode -eq 0) {
            $upgradeStatus = "success"
            $lastEventCode = "9812"
            $lastError = ""

            Log-UpgradeSuccess `
                -EventCode "9812" `
                -Message "Universal Forwarder has been successfully upgraded." `
                -PreviousVersion $previous_version `
                -CurrentVersion $current_version `
                -MSILogFile $MSILogFile
        }
        else {
            throw "MSI installer returned exit code $($process.ExitCode). Please check '$MSILogFile' for more details."
        }
    }
    catch {
        $upgradeStatus = "failed"
        $lastEventCode = "9813"
        $lastError = $($_.Exception.Message.Trim())

        Log-UpgradeFailure `
            -EventCode "9813" `
            -Message "Splunk upgrade failed." `
            -Details $lastError `
            -PreviousVersion $previous_version `
            -CurrentVersion $current_version `
            -MSILogFile $MSILogFile
    }
    finally {
        # Try to remove the MSI. If removal fails, write cleanup_failed to JSON state
        # so setup will not retry the same MSI forever.
        $cleanupSucceeded = Remove-SplunkInstaller `
            -InstallPath $InstallPath `
            -SplunkFileName $SplunkFileName

        if ($cleanupSucceeded -eq $true) {
            $cleanupStatus = "cleanup_success"
        }
        else {
            $cleanupStatus = "cleanup_failed"

            # If cleanup failed, keep the MSI protected by do_not_retry=true.
            # This is the exact condition that prevents the retry loop.
            if (-not $lastEventCode) {
                $lastEventCode = "9807"
            }

            if (-not $lastError) {
                $lastError = "Installer cleanup failed. MSI may still exist in splunk_installer."
            }
        }

        # Remove the scheduled task if it still exists.
        # This failure is logged separately as 9804 but does not change the main upgrade terminal state.
        Remove-ScheduledTaskSafe -TaskName $taskName

        # Write terminal state before starting Splunk again.
        # This ensures that if Splunk restarts and the setup script runs again,
        # it sees do_not_retry=true for this same MSI hash.
        $finalCurrentVersion = $current_version
        $finalCurrentVersionClean = Get-VersionFromSplunkOutput -VersionOutput $finalCurrentVersion

        $finalStateWriteSucceeded = Set-UpgradeState `
        -InstallerName $SplunkFileName `
    	-InstallerHash $InstallerHash `
   	-TargetVersion $TargetVersion `
    	-PreviousVersion $previous_version_clean `
    	-CurrentVersion $finalCurrentVersionClean `
    	-AttemptCount $AttemptCount `
    	-LastStatus $upgradeStatus `
    	-CleanupStatus $cleanupStatus `
    	-LastEventCode $lastEventCode `
    	-LastError $lastError `
    	-MSILogFile $MSILogFile `
    	-DoNotRetry $true

if ($finalStateWriteSucceeded -ne $true) {
    Write-Log "eventcode=9822 status=Failure message=""Final upgrade state could not be written."" details=""Splunk will still be started, but retry-loop protection may not reflect the final upgrade result."" state_file=""$StateFile"""
}
        # Start Splunk after state is written.
        Splunkd-Start
    }
}


###################################################
# Main execution workflow
###################################################

Initialize-LogPath -LogFolder $LogFolder -LogFile $LogFile
Initialize-StatePath

# Find the first Splunk Universal Forwarder MSI in the installer folder.
$msi = Get-ChildItem -Path $InstallerFolder -Filter "splunkforwarder*.msi" -File -ErrorAction SilentlyContinue | Select-Object -First 1
$installPath = if ($msi) { $msi.FullName } else { $null }
$splunkFileName = if ($msi) { $msi.Name } else { "Unknown" }

if (-not $installPath) {
    Write-Log "eventcode=9800 status=Failure message=""MSI not found."" details=""Please ensure the Splunk MSI file is located within '$InstallerFolder'."""
    Remove-ScheduledTaskSafe -TaskName $taskName
    exit 1
}

$installerHash = Get-InstallerHash -Path $installPath

if (-not $installerHash) {
    Write-Log "eventcode=9822 status=Failure message=""Installer hash could not be calculated."" details=""Unable to safely track installer state for '$splunkFileName'."""
    Remove-ScheduledTaskSafe -TaskName $taskName
    exit 1
}

if (-not (Test-Path -LiteralPath $splunkBinary)) {
    Write-Log "eventcode=9801 status=Failure message=""Splunk binary not found."" details=""Expected Splunk binary path '$splunkBinary' was not found."""
    Remove-ScheduledTaskSafe -TaskName $taskName
    exit 1
}

$targetVersion = Get-VersionFromInstallerName -InstallerName $splunkFileName

$existingState = Get-UpgradeState

# Exec-side retry-loop guard.
# This protects against a duplicate scheduled task run or any case where the exec script
# is launched again after the same installer has already reached a do_not_retry state.
if ($existingState `
    -and $existingState.installer_hash -eq $installerHash `
    -and $existingState.do_not_retry -eq $true `
    -and $existingState.last_status -ne "setup_validated") {

    Write-Log "eventcode=9819 status=Skipped message=""Installer was already attempted. Exec script exiting to prevent retry loop."" installer_name=""$splunkFileName"" installer_hash=""$installerHash"" target_version=""$targetVersion"" last_status=""$($existingState.last_status)"" cleanup_status=""$($existingState.cleanup_status)"""

    Remove-ScheduledTaskSafe -TaskName $taskName
    exit 0
}

$attemptCount = Get-NextAttemptCount -ExistingState $existingState -InstallerHash $installerHash

# Execute the MSI upgrade.
MSI-Upgrade-Splunk `
    -InstallPath $installPath `
    -MSILogFile $msiLogFile `
    -SplunkFileName $splunkFileName `
    -InstallerHash $installerHash `
    -TargetVersion $targetVersion `
    -AttemptCount $attemptCount
