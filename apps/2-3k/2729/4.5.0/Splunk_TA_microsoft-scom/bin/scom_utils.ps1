#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

Function EscapeXML($dict){
    $out_dict = @{}
    foreach($prop_key in $dict.keys){
        $value = $dict.$prop_key
        $value_str = @()
        foreach($val in $value){
            if($val -eq $null){
                continue
            }
            $str = $val.ToString()
            $value_str += $str
        }
        $prop_str = $value_str -Join ", "
        $prop_str = [Security.SecurityElement]::Escape($prop_str)
        $out_dict.$prop_key = $prop_str
    }
    return $out_dict
}

####################log#######################
# supported log level
$g_logLevels = @{
    'DEBUG' = 1
    'WARN'  = 2
    'ERROR' = 3
}

# file path
$g_logPath = $SplunkHome + '\var\log\splunk\ta_scom'
$g_ckptPath = $SplunkHome +'\var\lib\splunk\modinputs\scom\'

$global:g_currLogPath = $g_logPath + '.log'
$global:g_bakLogPath = $g_logPath + '_bak.log'
$global:g_loglevel = 2


###############################################
# Function name: printLog
# Description: print log to file
# Parameters:
#       - level [string] : log level
#       - msg [string]   : log message
# Return:
#       - None
###############################################
Function printLog($level, $msg) {

    # lock
    $mutex = new-object System.Threading.Mutex $false, 'SCOM_log_mutex'

    if ($mutex.WaitOne(1000)) {
        try {
            if ((Test-Path $global:g_currLogPath) -and (Get-Item $global:g_currLogPath).length -gt 10mb) {
                if (Test-Path $global:g_bakLogPath) {
                    remove-item $global:g_bakLogPath
                }
                rename-item $global:g_currLogPath $global:g_bakLogPath
            }
        } catch {
            # "Cannot remove > 10MB log file '$g_currLogPath'."
        } finally {
            # unlock
            $mutex.ReleaseMutex()
        }
    }

    if ($g_logLevels.Keys -contains $level) {
        $priority = $g_logLevels.$level
    } else {
        $priority = 1
    }

    if ($priority -lt $global:g_loglevel) {
        return
    }

    $time = Get-Date
    $text = $time.ToString('yyyy-MM-dd HH:mm:ss zzzz') + " [" + $level.ToUpper() + "] " + $msg

    $retry = 3
    while ($retry -gt 0) {
        try {
            # append text to log file
            $text | out-file -filepath $global:g_currLogPath -Append -Width 1000
            break
        } catch {
            Start-Sleep -m 100
            $retry -= 1
        }
    }
}


###############################################
# Function name: setupLog
# Description: setup log settings
# Parameters:
#       - loglevel [string] : debug log level
# Return:
#       - None
###############################################
Function setupLog($loglevel) {

    # setup loglevel
    if ($loglevel -and ($g_logLevels.Keys -contains $loglevel)) {
        $global:g_loglevel = $g_logLevels.$loglevel
    } elseif ($loglevel) {
        $global:g_loglevel = 2
        printLog warn "Loglevel '$loglevel' is not defined. Use default value 'WARN'."
    } else {
        $global:g_loglevel = 2
    }

}



Function getEncodeManagementgroup($managementgroup){
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($managementgroup)
    $base64_str = [System.Convert]::ToBase64String($bytes)
    $encode_str = $base64_str.replace("/", "-")
    return $encode_str
}
