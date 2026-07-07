$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent

if (-not $env:SPLUNK_HOME) {
    echo "SPLUNK_HOME is not set. Exiting script."
    exit 1
}

$LOG_FILE = "$env:SPLUNK_HOME\var\log\splunk\upgrader_package_delivery.log"

# Indicate if the package has been delivered or not
$PKG_DELIVERED_FILE = "$SCRIPT_DIR\pkg_delivered"

# The UF packages should be placed in this dir
$SRC_PKG_DIR = "$SCRIPT_DIR\..\local\packages"

function Print-Log {
    param (
        [string]$msg
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp $msg`r`n"
    
    $maxRetries = 3
    $retryCount = 0
    
    while ($retryCount -lt $maxRetries) {
        $fileStream = $null
        $streamWriter = $null
        
        try {
            # Open file with shared read access to allow other processes to read
            $fileStream = [System.IO.FileStream]::new(
                $LOG_FILE,
                [System.IO.FileMode]::Append,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::Read
            )
            
            $streamWriter = [System.IO.StreamWriter]::new($fileStream, [System.Text.Encoding]::UTF8)
            $streamWriter.WriteLine($logMessage.TrimEnd())
            $streamWriter.Flush()
            return

        } catch {
            $retryCount++
            if ($retryCount -ge $maxRetries) {
                return
            }
            Start-Sleep -Milliseconds (100 * $retryCount)
            
        } finally {
            if ($streamWriter) { $streamWriter.Dispose() }
            if ($fileStream) { $fileStream.Dispose() }
        }
    }
}

# Function to run a command and log its output
function Run-Cmd {
    param (
        [string]$cmd
    )
    Print-Log "Running cmd: $cmd"
    try {
        $output = Invoke-Expression $cmd
        if ($output) {
            $output -split "`n" | ForEach-Object { Print-Log $_ }
        }
    } catch {
        Print-Log "Error while running cmd: $cmd"
        Print-Log $_.Exception.Message
        throw
    }
}

# Function to check if there are any files under a given directory
function Found-Files-In-Dir {
    param (
        [string]$dir,
        [string[]]$exclude = @()
    )
    if (Test-Path $dir) {
        if ($exclude.Count -gt 0) {
            if (Get-ChildItem -Path $dir -Exclude $exclude) {
                return $true
            }
        } else {
            if (Get-ChildItem -Path $dir) {
                return $true
            }
        }
    }
    return $false
}

# Function to cancel delivery and wait for next interval
function Cancel-Delivery-And-Wait-For-Next-Interval {
    param (
        [string]$msg
    )
    Print-Log $msg
    Print-Log "Cancelling package delivery and waiting for next interval."
    exit 1
}

if (Test-Path $PKG_DELIVERED_FILE) {
    exit 1
}

Print-Log "Checking if any forwarder packages are available"
if (Found-Files-In-Dir $SRC_PKG_DIR) {
    Print-Log "Found files in $SRC_PKG_DIR. Will deliver them."
} else {
    Print-Log "No packages available in $SRC_PKG_DIR. Canceling package delivery"
    exit 1
}

# Read dest dir from $env:SPLUNK_HOME\var\run\splunk\splunkupdater\info
$info_path = "$env:SPLUNK_HOME\var\run\splunk\splunkupdater\info"
if (-not (Test-Path $info_path)) {
    Cancel-Delivery-And-Wait-For-Next-Interval "Conf file from UF updater does not exist at `$info_path`. The UF updater is likely not installed or running."
}

# Source the info file
$maxRetries = 5
$retryDelay = 2 # seconds
$retryCount = 0

while ($retryCount -lt $maxRetries) {
    try {
        Print-Log "Attempting to read $info_path (Attempt $($retryCount + 1) of $maxRetries)"
        Get-Content $info_path | ForEach-Object {
            if ($_ -match "^(.*?)=(.*)$") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                Set-Variable -Name ${key} -Value $value
            } else {
                Print-Log "Skipping invalid line in `${info_path}` : $_"
            }
        }
        break
    } catch {
        Print-Log "Failed to read $info_path : $($_.Exception.Message)"
        $retryCount++
        if ($retryCount -ge $maxRetries) {
            Cancel-Delivery-And-Wait-For-Next-Interval "Unable to read $info_path after $maxRetries attempts. Exiting."
        }
        Start-Sleep -Seconds $retryDelay
    }
}

$FWD_PKG_DIR = $FWD_PKG_DIR.Trim('"') -replace '\\', '\'

# Validate FWD_UPGRADE_TRIGGER_FILENAME
if (-not $FWD_UPGRADE_TRIGGER_FILENAME) {
    Cancel-Delivery-And-Wait-For-Next-Interval "FWD_UPGRADE_TRIGGER_FILENAME is not defined in $info_path"
}

# Validate FWD_PKG_DIR
if (-not $FWD_PKG_DIR) {
    Cancel-Delivery-And-Wait-For-Next-Interval "FWD_PKG_DIR is not defined in $info_path"
} elseif (-not (Test-Path $FWD_PKG_DIR)) {
    Cancel-Delivery-And-Wait-For-Next-Interval "FWD_PKG_DIR=$FWD_PKG_DIR does not exist"
}

# FWD_PKG_DIR is not empty, which means the UF upgrade is still ongoing
# "temp" folder is a folder RU create when working with user capability. 
# And it might use it for other purposes in the future.
# So we check exclude "temp" folder in deciding whether 
# RU is currently going through an upgrade process. 
if (Found-Files-In-Dir $FWD_PKG_DIR "temp") {
    Cancel-Delivery-And-Wait-For-Next-Interval "Target dir `$FWD_PKG_DIR` is not empty"
}

# Copy UF packages from ./local/packages to the dest dir
Print-Log "Copying files from $SCRIPT_DIR\..\local\packages to $FWD_PKG_DIR"
Run-Cmd "Copy-Item -Path `"$SCRIPT_DIR\..\local\packages\*`" -Destination `"$FWD_PKG_DIR`" -Recurse"

# Create a file in UF updater to trigger the upgrade
Print-Log "Creating a trigger file to start upgrade : $FWD_PKG_DIR\$FWD_UPGRADE_TRIGGER_FILENAME"
Run-Cmd "New-Item -Path `"$FWD_PKG_DIR\$FWD_UPGRADE_TRIGGER_FILENAME`" -ItemType File"

# Create pkg_delivered file to stop this script
Print-Log "Completed the package delivery. Creating a file to make sure it only happens once."
Run-Cmd "New-Item -Path `"$PKG_DELIVERED_FILE`" -ItemType File"
Print-Log "Completed!"