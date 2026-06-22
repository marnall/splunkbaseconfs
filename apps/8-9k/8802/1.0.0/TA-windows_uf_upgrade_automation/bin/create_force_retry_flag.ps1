###################################################
#### SPLUNK WINDOWS UPGRADE FORCE RETRY HELPER ####
###################################################
#
# Purpose:
# Creates a one-time force_retry.flag for the Splunk UF upgrade app.
#
# This helper is intended to be deployed through Splunk Deployment Server
# to endpoints that previously failed an upgrade and need one controlled retry.
#
# Main upgrade app watches for:
# C:\ProgramData\SplunkUpgrade\state\force_retry.flag
#
# Once the setup script sees the flag, it removes it and allows one retry.
#
# This helper also creates its own marker file so it does not recreate
# force_retry.flag forever on every scripted input interval.
#

$LogFolder = "C:\ProgramData\SplunkUpgrade"
$StateFolder = Join-Path $LogFolder "state"

$ForceRetryFile = Join-Path $StateFolder "force_retry.flag"
$HelperMarkerFile = Join-Path $StateFolder "force_retry_helper_created.marker"

$LogFile = Join-Path $LogFolder "splunk_upgrade_force_retry_helper.log"

function Initialize-Paths {
    if (-not (Test-Path -LiteralPath $LogFolder)) {
        New-Item -ItemType Directory -Force -Path $LogFolder | Out-Null
    }

    if (-not (Test-Path -LiteralPath $StateFolder)) {
        New-Item -ItemType Directory -Force -Path $StateFolder | Out-Null
    }

    if (-not (Test-Path -LiteralPath $LogFile)) {
        New-Item -ItemType File -Force -Path $LogFile | Out-Null
    }

    & icacls $LogFolder /inheritance:e | Out-Null
    & icacls $LogFolder /grant `
        "NT AUTHORITY\SYSTEM:(OI)(CI)F" `
        "BUILTIN\Administrators:(OI)(CI)F" `
        "Users:(OI)(CI)M" /C | Out-Null

    & icacls $StateFolder /inheritance:e | Out-Null
    & icacls $StateFolder /grant `
        "NT AUTHORITY\SYSTEM:(OI)(CI)F" `
        "BUILTIN\Administrators:(OI)(CI)F" `
        "Users:(OI)(CI)M" /C | Out-Null
}

function Write-HelperLog {
    param (
        [string]$Message
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $cleanMessage = $Message -replace "(`r`n|`n|`r)", " "
    $entry = "$timestamp  $cleanMessage"

    $maxRetries = 8
    $retry = 0
    $written = $false

    while (-not $written -and $retry -lt $maxRetries) {
        $fs = $null
        $sw = $null

        try {
            $fs = [System.IO.File]::Open(
                $LogFile,
                [System.IO.FileMode]::Append,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::ReadWrite
            )

            $sw = New-Object System.IO.StreamWriter($fs)
            $sw.WriteLine($entry)

            $written = $true
        }
        catch {
            Start-Sleep -Milliseconds 200
            $retry++
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

    if (-not $written) {
        Write-Warning "Failed to write helper log after $maxRetries attempts: $LogFile"
    }
}

Initialize-Paths

# If this helper already created the retry flag once, do not recreate it.
# This prevents endless forced retries if the helper app remains deployed.
if (Test-Path -LiteralPath $HelperMarkerFile) {
    Write-HelperLog "eventcode=9831 status=Skipped message=""Force retry helper already ran on this endpoint. No new flag created."" marker_file=""$HelperMarkerFile"""
    exit 0
}

try {
    New-Item -ItemType File -Force -Path $ForceRetryFile | Out-Null
    New-Item -ItemType File -Force -Path $HelperMarkerFile | Out-Null

    Write-HelperLog "eventcode=9830 status=Success message=""Force retry flag created successfully."" force_retry_file=""$ForceRetryFile"" marker_file=""$HelperMarkerFile"""
    exit 0
}
catch {
    Write-HelperLog "eventcode=9832 status=Failure message=""Failed to create force retry flag."" details=""$($_.Exception.Message.Trim())"" force_retry_file=""$ForceRetryFile"""
    exit 1
}
