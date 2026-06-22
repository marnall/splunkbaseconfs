###################################################
########## SPLUNK WINDOWS UPGRADE SETUP ###########
###################################################
#
# Purpose:
# This script performs pre-upgrade validation and creates/starts a Windows
# Scheduled Task that runs the main Splunk Universal Forwarder upgrade script.
#
# This setup script performs:
# - MSI discovery
# - Splunk binary validation
# - Current/target version validation
# - Retry-loop prevention using a persistent JSON state file
# - Scheduled task cleanup, creation, and start
#
# JSON State Purpose:
# The JSON state file prevents endless retry loops. For example, if the upgrade
# script fails to remove the MSI installer, Splunk may restart and run this setup
# script again. Without persistent state, the same MSI can be attempted forever.
#
# State file location:
# C:\ProgramData\SplunkUpgrade\state\splunk_upgrade_state.json
#
# Force retry:
# To intentionally retry the same MSI, create this file:
# C:\ProgramData\SplunkUpgrade\state\force_retry.flag
#
# The setup script will detect the flag, allow one retry, and remove the flag.
#

###################################################
# Path and runtime variables
###################################################

$scriptPath = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
$installerScript = Join-Path $scriptPath "splunk_windows_upgrade_exec.ps1"
$rootDir = Split-Path -Path $scriptPath -Parent

$LogFolder = "C:\ProgramData\SplunkUpgrade"
$LogFile = Join-Path $LogFolder "splunk_upgrade_setup.log"

$StateFolder = Join-Path $LogFolder "state"
$StateFile = Join-Path $StateFolder "splunk_upgrade_state.json"
$ForceRetryFile = Join-Path $StateFolder "force_retry.flag"

$InstallerFolder = Join-Path $rootDir "splunk_installer"

$taskName = "z_splunk_upgrader_task_v01"
$taskDescription = "This runs the MSI installer to upgrade your Windows UF version"

$splunkBinary = "C:\Program Files\SplunkUniversalForwarder\bin\splunk.exe"

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$installerScript`""

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddYears(10)

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest


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

    # Ensure SYSTEM, Administrators, and Users can write/read the log location.
    # Users:M is intentional so Splunk/script execution contexts can append logs.
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

    # State needs to persist across Splunk restarts, service restarts, and script reruns.
    # This prevents the same installer from being retried forever.
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
    # That was causing installer_hash to become a log line instead of a SHA256 hash.

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
# Event logging helpers
###################################################

function Log-CheckEventSuccess {
    param (
        [string]$EventCode,
        [string]$Message
    )

    Write-Log "eventcode=$EventCode status=Success message=""$Message"""
}

function Log-CheckEventFailure {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$Details
    )

    Write-Log "eventcode=$EventCode status=Failure message=""$Message"" details=""$Details"""
}

function Log-CheckEventSkipped {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$Details,
        [string]$InstallerName,
        [string]$InstallerHash,
        [string]$TargetVersion,
        [string]$LastStatus,
        [string]$CleanupStatus
    )

    Write-Log "eventcode=$EventCode status=Skipped message=""$Message"" details=""$Details"" installer_name=""$InstallerName"" installer_hash=""$InstallerHash"" target_version=""$TargetVersion"" last_status=""$LastStatus"" cleanup_status=""$CleanupStatus"""
}

function Log-TaskEventSuccess {
    param (
        [string]$EventCode,
        [string]$Message,
        [string]$TaskName
    )

    Write-Log "eventcode=$EventCode status=Success message=""$Message"" taskname=""$TaskName"""
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

function Set-UpgradeState {
    param (
        [string]$InstallerName,
        [string]$InstallerHash,
        [string]$TargetVersion,
        [string]$CurrentVersion,
        [string]$LastStatus,
        [string]$CleanupStatus,
        [string]$LastEventCode,
        [string]$LastError,
        [bool]$DoNotRetry,
        [int]$AttemptCount
    )

    Initialize-StatePath

    $state = [ordered]@{
        installer_name     = $InstallerName
        installer_hash     = $InstallerHash
        target_version     = $TargetVersion
        current_version    = $CurrentVersion
        attempt_count      = $AttemptCount
        last_status        = $LastStatus
        cleanup_status     = $CleanupStatus
        do_not_retry       = $DoNotRetry
        last_eventcode     = $LastEventCode
        last_error         = $LastError
        last_attempt_time  = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        state_source       = "setup"
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

        Write-Log "eventcode=9821 status=Success message=""Upgrade state file written successfully."" installer_name=""$InstallerName"" installer_hash=""$InstallerHash"" target_version=""$TargetVersion"" attempt_count=""$AttemptCount"" last_status=""$LastStatus"" do_not_retry=""$DoNotRetry"""

        return $true
    }
    catch {
        Write-Log "eventcode=9822 status=Failure message=""Failed to write upgrade state file."" details=""$($_.Exception.Message.Trim())"" state_file=""$StateFile"""
        return $false
    }
}

function Get-NextAttemptCount {
    param (
        [object]$ExistingState,
        [string]$InstallerHash
    )

    if ($ExistingState -and $ExistingState.installer_hash -eq $InstallerHash -and $ExistingState.attempt_count) {
        return ([int]$ExistingState.attempt_count + 1)
    }

    return 1
}

function Test-InstallerAlreadyAttempted {
    param (
        [object]$ExistingState,
        [string]$InstallerHash
    )

    if (-not $ExistingState) {
        return $false
    }

    if (-not $InstallerHash) {
        return $false
    }

    if ($ExistingState.installer_hash -ne $InstallerHash) {
        return $false
    }

    if ($ExistingState.do_not_retry -eq $true) {
        return $true
    }

    return $false
}

function Test-InstallerAlreadyAttemptedByNameAndVersion {
    param (
        [object]$ExistingState,
        [string]$InstallerName,
        [string]$TargetVersion
    )

    if (-not $ExistingState) {
        return $false
    }

    if ($ExistingState.installer_name -ne $InstallerName) {
        return $false
    }

    if ($ExistingState.target_version -ne $TargetVersion) {
        return $false
    }

    if ($ExistingState.do_not_retry -eq $true) {
        return $true
    }

    return $false
}


###################################################
# Main setup workflow
###################################################

Initialize-LogPath -LogFolder $LogFolder -LogFile $LogFile
Initialize-StatePath

# Find the first Splunk Universal Forwarder MSI in the installer folder.
# The filename must begin with splunkforwarder and end in .msi.
$msi = Get-ChildItem -Path $InstallerFolder -Filter "splunkforwarder*.msi" -File -ErrorAction SilentlyContinue | Select-Object -First 1
$installPath = if ($msi) { $msi.FullName } else { $null }
$splunkFileName = if ($msi) { $msi.Name } else { "Unknown" }

if (-not $installPath) {
    Log-CheckEventFailure `
        -EventCode "9800" `
        -Message "MSI not found." `
        -Details "Please ensure the Splunk MSI file is located within '$InstallerFolder'."

    exit 1
}

# Read existing state before calculating hash so locked-file retry prevention can still work.
$existingState = Get-UpgradeState

# Extract target version from MSI name early.
# This fallback is used if the MSI is locked and the hash cannot be recalculated.
$targetVersionFromName = "Unknown"

if ($splunkFileName -match '(\d+\.\d+\.\d+)') {
    $targetVersionFromName = $Matches[1]
}

# Calculate installer hash.
# This is the preferred key for retry-loop prevention.
$installerHash = Get-InstallerHash -Path $installPath

if (-not $installerHash) {
    # If the MSI is locked, Get-FileHash may fail.
    # In that case, fall back to installer_name + target_version only if the
    # existing state already says do_not_retry=true.
    if (Test-InstallerAlreadyAttemptedByNameAndVersion `
            -ExistingState $existingState `
            -InstallerName $splunkFileName `
            -TargetVersion $targetVersionFromName) {

        Log-CheckEventSkipped `
            -EventCode "9819" `
            -Message "Installer was already attempted. Skipping to prevent retry loop." `
            -Details "Installer hash could not be recalculated because the MSI may be locked, but the existing state file marks this installer and target version as do_not_retry=true." `
            -InstallerName $splunkFileName `
            -InstallerHash $existingState.installer_hash `
            -TargetVersion $targetVersionFromName `
            -LastStatus $existingState.last_status `
            -CleanupStatus $existingState.cleanup_status

        exit 0
    }

    Log-CheckEventFailure `
        -EventCode "9822" `
        -Message "Installer hash could not be calculated." `
        -Details "Unable to safely determine whether installer '$splunkFileName' was previously attempted."

    exit 1
}

if (-not (Test-Path -LiteralPath $splunkBinary)) {
    Log-CheckEventFailure `
        -EventCode "9801" `
        -Message "Splunk binary not found." `
        -Details "If Splunk was installed outside of the default directory, please update the splunkBinary variable within the setup PowerShell script."

    exit 1
}

$versionOutput = & $splunkBinary version 2>&1

try {
    Write-Host "Getting current Splunk version."

    if ($versionOutput -match '(\d+\.\d+\.\d+)') {
        $currentVersion = $Matches[1]
        $currentMajorVersion = ([version]$currentVersion).Major
    }
    else {
        $eventcode = "9814"
        $message = "Unable to parse current Splunk version."
        throw "The splunk.exe version command returned '$versionOutput' and did not match expected regex '(\d+\.\d+\.\d+)'."
    }

    Write-Host "Getting target version from MSI file."

    if ($msi.Name -match '(\d+\.\d+\.\d+)') {
        $targetVersion = $Matches[1]
        $targetMajorVersion = ([version]$targetVersion).Major
    }
    else {
        $eventcode = "9815"
        $message = "Unable to extract MSI version."
        throw "Please ensure the Splunk filename remains unaltered. MSI filename: '$($msi.Name)'"
    }

    Write-Host "Running version validation checks."

    if ([version]$targetVersion -le [version]$currentVersion) {
        $eventcode = "9816"
        $message = "Splunk UF is already up to date."
        throw "Current Splunk Version: '$currentVersion' Target Splunk Version: '$targetVersion'"
    }

    if ($targetMajorVersion -gt ($currentMajorVersion + 1)) {
        $eventcode = "9817"
        $message = "Major versions too far apart."
        throw "Current Splunk Major Version: '$currentMajorVersion' Target Splunk Major Version: '$targetMajorVersion'"
    }

    Log-CheckEventSuccess `
        -EventCode "9818" `
        -Message "All checks passed. Proceeding with upgrade from current Splunk version: $currentVersion to target Splunk version: $targetVersion"
}
catch {
    Log-CheckEventFailure `
        -EventCode "$eventcode" `
        -Message "$message" `
        -Details $($_.Exception.Message.Trim())

    exit 1
}


###################################################
# Retry-loop prevention
###################################################
#
# At this point:
# - MSI exists
# - MSI hash was calculated
# - splunk.exe exists
# - current version was parsed
# - target version was parsed
# - version validation passed
#
# Now check the persistent JSON state file before scheduling the upgrade task.
# If the same MSI hash already reached a terminal do_not_retry state, skip.
#

$forceRetry = $false

if (Test-Path -LiteralPath $ForceRetryFile) {
    try {
        Remove-Item -LiteralPath $ForceRetryFile -Force -ErrorAction Stop
        $forceRetry = $true

        Write-Log "eventcode=9820 status=Success message=""Force retry flag detected and removed. The same installer will be allowed to run one more time."" installer_name=""$splunkFileName"" installer_hash=""$installerHash"" target_version=""$targetVersion"" force_retry_file=""$ForceRetryFile"""
    }
    catch {
        Write-Log "eventcode=9822 status=Failure message=""Force retry flag detected but could not be removed. Exiting to prevent retry loop."" details=""$($_.Exception.Message.Trim())"" force_retry_file=""$ForceRetryFile"""
        exit 1
    }
}

if (-not $forceRetry -and (Test-InstallerAlreadyAttempted -ExistingState $existingState -InstallerHash $installerHash)) {
    Log-CheckEventSkipped `
        -EventCode "9819" `
        -Message "Installer was already attempted. Skipping to prevent retry loop." `
        -Details "The same installer hash is marked do_not_retry=true in the upgrade state file. Delete the state file or create force_retry.flag to retry intentionally." `
        -InstallerName $splunkFileName `
        -InstallerHash $installerHash `
        -TargetVersion $targetVersion `
        -LastStatus $existingState.last_status `
        -CleanupStatus $existingState.cleanup_status

    exit 0
}

# Mark the setup stage as ready/scheduled. This is not a terminal state.
# do_not_retry remains false here because the exec script has not attempted
# the MSI yet. The exec script should update this same state file to terminal
# success/failure/cleanup_failed.
$attemptCount = Get-NextAttemptCount -ExistingState $existingState -InstallerHash $installerHash

$stateWriteSucceeded = Set-UpgradeState `
    -InstallerName $splunkFileName `
    -InstallerHash $installerHash `
    -TargetVersion $targetVersion `
    -CurrentVersion $currentVersion `
    -LastStatus "setup_validated" `
    -CleanupStatus "not_started" `
    -LastEventCode "9818" `
    -LastError "" `
    -DoNotRetry $false `
    -AttemptCount $attemptCount

if ($stateWriteSucceeded -ne $true) {
    Log-CheckEventFailure `
        -EventCode "9822" `
        -Message "Setup cannot continue because upgrade state file could not be written." `
        -Details "Scheduled task will not be created because retry-loop protection state could not be persisted."

    exit 1
}

###################################################
# Scheduled task cleanup
###################################################
#
# If a previous scheduled task exists, remove it first so this run uses the
# latest script path and installer state.
#

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
        Write-Host "Scheduled task removed successfully."
    }
    catch {
        Log-TaskEventFailure `
            -EventCode "9804" `
            -Message "Failed to remove scheduled task." `
            -Details $($_.Exception.Message.Trim()) `
            -TaskName $taskName

        exit 1
    }
}


###################################################
# Scheduled task creation
###################################################

try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Description $taskDescription `
        -ErrorAction Stop

    Log-TaskEventSuccess `
        -EventCode "9803" `
        -Message "Scheduled task created successfully." `
        -TaskName $taskName
}
catch {
    Log-TaskEventFailure `
        -EventCode "9802" `
        -Message "Failed to create scheduled task." `
        -Details $($_.Exception.Message.Trim()) `
        -TaskName $taskName

    exit 1
}


###################################################
# Scheduled task start
###################################################

try {
    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop

    Log-TaskEventSuccess `
        -EventCode "9805" `
        -Message "Scheduled task started successfully." `
        -TaskName $taskName
}
catch {
    Log-TaskEventFailure `
        -EventCode "9806" `
        -Message "Failed to start task." `
        -Details $($_.Exception.Message.Trim()) `
        -TaskName $taskName

    exit 1
}
