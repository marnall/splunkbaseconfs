########################################################################################
##
## SPLUNK_TA_ARI_WIN Edge Discovery
##
## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## Splunk Software Licence and Support Agreement
##
########################################################################################

. "$PSScriptRoot\ari_utils.ps1"

function Write-VolumeEvent {
    Write-Event `
        "volume_label" $volumeLabel `
        "volume_letter" $volumeLetter `
        "volume_type" $volumeType `
        "drive_type" $driveType `
        "size" $size `
        "bitLocker_version" $bitLockerVersion `
        "conversion_status" $conversionStatus `
        "encryption_method" $encryptionMethod `
        "protection_status" $protectionStatus
}

try {
    $bitlockerResults = manage-bde -status 2>$null

    if ( $bitlockerResults -join " " -match "ERROR:" ) { throw }

    foreach ($line in $bitlockerResults) {
        if ($line -match "^Volume\s(\w):\s+\[(.*)\]") {
            if ($volumeLetter) {
                Write-VolumeEvent

                $volumeType = ""
                $driveType = ""
                $size = ""
                $bitLockerVersion = ""
                $conversionStatus = ""
                $encryptionMethod = ""
                $protectionStatus = ""
            }

            $volumeLabel=$matches[2]
            $volumeLetter=$matches[1]
        }
        elseif ($line -match "\[(.*)\]" ) {
            $volumeType = $matches[1]
            $driveType = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID = '${volumeLetter}:'").DriveType
        }
        elseif ($line -match "Size:\s+(.*)" ) {
            $size = $matches[1]
        }
        elseif ($line -match "Bitlocker Version:\s+(.*)" ) {
            $bitLockerVersion = $matches[1]
        }
        elseif ($line -match "Conversion Status:\s+(.*)" ) {
            $conversionStatus = $matches[1]
        }
        elseif ($line -match "Encryption Method:\s+(.*)" ) {
            $encryptionMethod = $matches[1]
        }
        elseif ($line -match "Protection Status:\s+(.*)" ) {
            $protectionStatus = $matches[1]
        }
    }

    if ($volumeLetter) { Write-VolumeEvent }
    else { throw }
}
catch {
    $conversionStatusMap = @{
        0 = 'Fully Decrypted'
        1 = 'Encryption In Progress'
        2 = 'Decryption In Progress'
        3 = 'Fully Encrypted'
    }

    $encryptionMethodMap = @{
        0 = 'None'
        1 = 'AES 128'
        2 = 'AES 256'
        3 = 'AES 128 with Diffuser'
        4 = 'AES 256 with Diffuser'
        6 = 'XTS-AES 128'
        7 = 'XTS-AES 256'
    }

    $protectionStatusMap = @{
        0 = 'Protection Off'
        1 = 'Protection On'
        2 = 'Unknown'
    }

    $volumes = Get-CimInstance -Class Win32_LogicalDisk
    try {
        $bitLockerVolumes = Get-WmiObject -Namespace "Root\CIMv2\Security\MicrosoftVolumeEncryption" -Class Win32_EncryptableVolume -ErrorAction Stop
    }
    catch {
        $bitLockerVolumes = @{}
    }

    foreach ($volume in $volumes) {
        $volumeLetter = $volume.DeviceID;

        $bitLockerVolume = $bitLockerVolumes | Where-Object { $_.DriveLetter -eq $volumeLetter }
        if (-not $bitLockerVolume) {
            $bitLockerVolume = @{
                ConversionStatus = 0
                EncryptionMethod = 0
                ProtectionStatus = 0
            }
        }

        $volumeLabel=$volume.VolumeName
        $volumeLetter=$volumeLetter -replace ':', ''
        $volumeType="$(if ($volume.DeviceID -eq $env:SystemDrive) { "OS" } else { "Data" }) Volume"
        $driveType=$volume.DriveType
        $size="$([math]::Round($volume.Size / 1GB, 2)) GB"
        $conversionStatus=$conversionStatusMap[[int]$bitLockerVolume.ConversionStatus]
        $encryptionMethod=$encryptionMethodMap[[int]$bitLockerVolume.EncryptionMethod]
        $protectionStatus=$protectionStatusMap[[int]$bitLockerVolume.ProtectionStatus]

        Write-VolumeEvent
    }
}
