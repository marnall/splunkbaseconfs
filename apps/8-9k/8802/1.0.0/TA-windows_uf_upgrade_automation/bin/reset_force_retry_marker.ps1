###################################################
##### SPLUNK WINDOWS UPGRADE FORCE RETRY RESET ####
###################################################
#
# Purpose:
# Removes the force retry helper marker file.
#
# This allows the force retry helper to create a new force_retry.flag again
# during a future run.
#
# Use case:
# - A previous force retry helper deployment already created the marker.
# - Admin wants to allow another controlled retry wave.
# - Deploy/enable this reset action only intentionally.
#

$LogFolder = "C:\ProgramData\SplunkUpgrade"
$StateFolder = Join-Path $LogFolder "state"

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

    & icacls $LogFile /inheritance:e | Out-Null
    & icacls $LogFile /grant `
        "NT AUTHORITY\SYSTEM:F" `
        "BUILTIN\Administrators:F" `
        "Users:M" /C | Out-Null
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

try {
    if (Test-Path -LiteralPath $HelperMarkerFile) {
        Remove-Item -LiteralPath $HelperMarkerFile -Force -ErrorAction Stop

        Write-HelperLog "eventcode=9833 status=Success message=""Force retry helper marker removed successfully."" marker_file=""$HelperMarkerFile"""
        exit 0
    }
    else {
        Write-HelperLog "eventcode=9834 status=Skipped message=""Force retry helper marker was not present. No reset needed."" marker_file=""$HelperMarkerFile"""
        exit 0
    }
}
catch {
    Write-HelperLog "eventcode=9835 status=Failure message=""Failed to remove force retry helper marker."" details=""$($_.Exception.Message.Trim())"" marker_file=""$HelperMarkerFile"""
    exit 1
}
