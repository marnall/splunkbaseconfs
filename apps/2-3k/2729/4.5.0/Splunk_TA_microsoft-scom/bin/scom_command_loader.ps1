#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

param(
[array]$commands = $null,
[array]$groups = $null,
[string]$server = $null,
[string]$loglevel = $null,
[string]$starttime = $null,
[string]$performancefilter = $null
)

. "$PSScriptRoot\scom_utils.ps1"

# predefined groups
$g_groups = @{
    "alert"       = @('Get-SCOMAlert', 'Get-SCOMAlert | Get-SCOMAlertHistory');
    "monitor"     = @("Get-SCOMMonitor");
    "diagnostic"  = @("Get-SCOMDiagnostic");
    "task"        = @("Get-SCOMTask", "Get-SCOMTaskResult");
    "recovery"    = @("Get-SCOMRecovery");
    "discovery"   = @("Get-SCOMDiscovery");
    "override"    = @("Get-SCOMOverride", "Get-SCOMOverrideResult -Instance (Get-SCOMClassInstance) -Monitor (Get-SCOMMonitor)");
    "event"       = @('Get-SCOMEvent');
    "rule"        = @('Get-SCOMRule');
    "internal"    = @('Get-SCOMClass', 'Get-SCOMClassInstance', 'Get-SCOMRelationship', 'Get-SCOMRelationshipInstance');
    "network"     = @(
        'Get-SCOMConnector',
        'Get-SCOMAgent',
        'Get-SCOMAgentlessManagedComputer',
        'Get-SCAdvisorProxy',
        'Get-SCOMParentManagementServer -Agent (Get-SCOMAgent)',
        'Get-SCAdvisorAgent',
        'Get-SCOMADAgentAssignment',
        'Get-SCOMGatewayManagementServer'
    );
    "mgmt"        = @(
        'Get-SCOMManagementPack',
        'Get-SCOMRunAsAccount',
        'Get-SCOMRunAsProfile',
        'Get-SCOMRunAsAccount | Get-SCOMRunAsDistribution',
        'Get-SCOMHeartbeatSetting',
        'Get-SCOMManagementGroup',
        'Get-SCOMManagementServer',
        'Get-SCOMUserRole',
        'Get-SCOMAlertResolutionSetting',
        'Get-SCOMAlertResolutionState',
        'Get-SCOMManagementGroupConnection',
        'Get-SCOMAccessLicense',
        'Get-SCOMDatabaseGroomingSetting',
        'Get-SCOMDataWarehouseSetting',
        'Get-SCOMErrorReportingSetting',
        'Get-SCOMReportingSetting',
        'Get-SCOMResourcePool',
        'Get-SCOMRMSEmulator',
        'Get-SCOMGroup',
        'Get-SCOMWebAddressSetting',
        'Get-SCOMAgentApprovalSetting',
        'Get-SCOMLocation',
        'Get-SCOMTieredManagementGroup',
        'Get-SCOMNotificationChannel',
        'Get-SCOMNotificationSubscriber',
        'Get-SCOMNotificationSubscription',
        'Get-SCOMMaintenanceMode',
        'Get-SCOMPendingManagement',
        'Get-SCOMTieredManagementGroup | Get-SCOMTierConnector'
    );
}

$a_allowed_commands = @(
    'Get-SCAdvisorAgent',
    'Get-SCAdvisorProxy',

    'Get-SCOMAccessLicense',
    'Get-SCOMADAgentAssignment'
    'Get-SCOMAgent',
    'Get-SCOMAgentApprovalSetting',
    'Get-SCOMAgentlessManagedComputer',
    'Get-SCOMAlert',
    'Get-SCOMAlertResolutionSetting',
    'Get-SCOMAlertResolutionState',
    'Get-SCOMAlert | Get-SCOMAlertHistory',
    'Get-SCOMAllPerfData',
    'Get-SCOMClass',
    'Get-SCOMClassInstance',
    'Get-SCOMConnector',
    'Get-SCOMDatabaseGroomingSetting',
    'Get-SCOMDataWarehouseSetting',
    'Get-SCOMDiagnostic',
    'Get-SCOMDiscovery',
    'Get-SCOMErrorReportingSetting',
    'Get-SCOMEvent',
    'Get-SCOMGatewayManagementServer',
    'Get-SCOMGroup'
    'Get-SCOMHeartbeatSetting',
    'Get-SCOMLocation',
    'Get-SCOMMaintenanceMode',
    'Get-SCOMManagementGroup',
    'Get-SCOMManagementGroupConnection',
    'Get-SCOMManagementPack',
    'Get-SCOMManagementServer',
    'Get-SCOMMonitor',
    'Get-SCOMMonitoringObject',
    'Get-SCOMNotificationChannel',
    'Get-SCOMNotificationSubscriber',
    'Get-SCOMNotificationSubscription',
    'Get-SCOMOverride',
    'Get-SCOMOverrideResult -Instance (Get-SCOMClassInstance) -Monitor (Get-SCOMMonitor)',
    'Get-SCOMParentManagementServer -Agent (Get-SCOMAgent)',
    'Get-SCOMPendingManagement',
    'Get-SCOMRecovery',
    'Get-SCOMRelationship',
    'Get-SCOMRelationshipInstance',
    'Get-SCOMReportingSetting',
    'Get-SCOMResourcePool',
    'Get-SCOMRMSEmulator',
    'Get-SCOMRule',
    'Get-SCOMRunAsAccount',
    'Get-SCOMRunAsAccount | Get-SCOMRunAsDistribution',
    'Get-SCOMRunAsProfile',
    'Get-SCOMTask',
    'Get-SCOMTaskResult',
    'Get-SCOMTieredManagementGroup',
    'Get-SCOMTieredManagementGroup | Get-SCOMTierConnector',
    'Get-SCOMUserRole',
    'Get-SCOMWebAddressSetting'
)

# add some properties based on commands during index time
$g_properties = @{
    "Get-SCOMAlert" = @{
        type = 'alert'
    };
}

# field as the timestamp
$g_timestamp = @{
    # events
    "Get-SCOMAlert"      = "TimeAdded"
    'Get-SCOMEvent'      = "TimeAdded"
    "Get-SCOMMonitor"    = "LastModified"
    "Get-SCOMDiagnostic" = "LastModified"
    "Get-SCOMTask"       = "LastModified"
    "Get-SCOMRecovery"   = "LastModified"
    "Get-SCOMDiscovery"  = "LastModified"
    "Get-SCOMOverride"   = "LastModified"
    "Get-SCOMRule"       = "LastModified"
    "Get-SCOMTaskResult" = "LastModified"
    "Get-SCOMAlert | Get-SCOMAlertHistory"  = "TimeAdded"

    # mgmt
    'Get-SCOMManagementPack'    = "LastModified"
    'Get-SCOMResourcePool'      = "LastModified"
    'Get-SCOMUserRole'          = "LastModified"
    'Get-SCOMRMSEmulator'       = "LastModified"
    'Get-SCOMManagementServer'  = "LastModified"
    'Get-SCOMRunAsAccount'      = "LastModified"
    'Get-SCOMGroup'             = "LastModified"
    'Get-SCOMRunAsProfile'      = "LastModified"
    'Get-SCOMLocation'          = "LastModified"
    'Get-SCOMMaintenanceMode'   = "LastModified"
    'Get-SCOMPendingManagement' = "LastModified"


    # network
    "Get-SCOMConnector"                 = "LastModified"
    'Get-SCOMAgent'                     = "LastModified"
    'Get-SCOMAgentlessManagedComputer'  = "LastModified"
    'Get-SCAdvisorAgent'                = "LastModified"
    'Get-SCOMGatewayManagementServer'   = "LastModified"
    'Get-SCOMParentManagementServer -Agent (Get-SCOMAgent)' = "LastModified"

    # internal
    "Get-SCOMClass"             = "LastModified"
    "Get-SCOMClassInstance"     = "LastModified"
    "Get-SCOMRelationship"      = "LastModified"
    "Get-SCOMMonitoringObject"  = "LastModified"
    "Get-SCOMRelationshipInstance"  = "LastModified"
}

# convert the object to string
$g_object2string = @{
    'Microsoft.EnterpriseManagement.Administration.NotificationRecipientDevice' = 'name'
    'Microsoft.EnterpriseManagement.Administration.NotificationRecipient'       = 'name'
    'Microsoft.EnterpriseManagement.Configuration.ManagementPackDiscoveryClass' = 'TypeID'
    'Microsoft.EnterpriseManagement.Monitoring.MonitoringObject'                = 'DisplayName'
}

# Deducting one day from current date and converting to UTC time
$default_starttime = (Get-Date).AddDays(-1).ToUniversalTime().ToString("yyyy-MM-ddThh:mm:ssZ")
$perfdata_cmd = 'Get-SCOMAllPerfData'
$scom_timestamp = 'scom_timestamp'

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
        } catch [Exception] {
            # "Cannot remove > 10MB log file '$g_currLogPath'."
            $info = "{0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
            $msg=$msg+"`r`n"+$info
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
    $text = $time.ToString('yyyy-MM-dd HH:mm:ss zzzz') + " [ log_level=" + $level.ToUpper() + " pid=" + $PID + " input=" + $SplunkStanzaName +" ] " + $msg

    $retry = 3
    while ($retry -gt 0) {
        try {
            # append text to log file
            $mutex.WaitOne() | Out-Null
            $text | out-file -filepath $global:g_currLogPath -Append -Width 1000
            break
        } catch {
            Start-Sleep -m 100
            $retry -= 1
        }finally{
            $mutex.ReleaseMutex() | Out-Null
        }
    }
}



###############################################
# Function name: getCheckpoint
# Description: get checkpoint from file
# Parameters:
#       - cmd [string]  : the SCOM command
# Return:
#       - ckpt [object] : the datetime object as the checkpoint
###############################################

Function getCheckpoint($managementgroup, $cmd) {
    printLog debug "--> getCheckpoint $cmd"
    # replace |
    $cmd = $cmd.replace("|", "_")
    if($managementgroup){
        $managementgroup_path = "###" + (getEncodeManagementgroup $managementgroup) + "###"
        $path = $g_ckptPath + $managementgroup_path + $cmd
    }else{
        $path = $g_ckptPath + $cmd
    }

    if (-not (Test-Path $path)) {
        printLog debug "No checkpoint file '$path'"
        return $null
    }

    printLog debug "Getting checkpoint from file '$path'..."

    $retry = 3
    while ($retry -ge 0) {
        try {
            $cont = Get-Content $path | out-string
            $cont = $cont.Trim()
            $ckpt = [datetime]::ParseExact($cont, "MM/dd/yyyy HH:mm:ss.fff", $null)
            printLog debug "Got checkpoint '$cont' from file '$path' successfully."
            break
        } catch [Exception] {
            if ($retry -gt 0) {
                printLog debug "Got exception when getting checkpoint $cont . Retry $retry... $_"
                $retry -= 1
                continue
            }
            $retry -= 1
            printLog error "Get checkpoint failed from file '$path'. It will be overwritten when --> setCheckpoint"
            $ckpt = $null
        }
    }
    return $ckpt
}

###############################################
# Function name: setCheckpoint
# Description: write checkpoint to file
# Parameters:
#       - cmd [string]  : the SCOM command
#       - ckpt [string] : the checkpoint to be saved
# Return:
#       - None
###############################################

Function setCheckpoint($managementgroup, $cmd, $ckpt) {
    $cmd = $cmd.Trim()
    $ckpt = $ckpt.ToString().Trim()

    printLog debug "--> setCheckpoint ($managementgroup, $cmd, $ckpt)"

    # replace |
    $cmd = $cmd.replace("|", "_")
    if($managementgroup){
        $managementgroup_path = "###" + (getEncodeManagementgroup $managementgroup) + "###"
        $path = $g_ckptPath + $managementgroup_path + $cmd
    }else{
        $path = $g_ckptPath + $cmd
    }
    printLog debug "Saving checkpoint to file '$path'..."

    $retry = 3
    $mutex = new-object System.Threading.Mutex $false, $cmd
    while ($retry -ge 0) {
        try {
            $mutex.WaitOne() | Out-Null
            $ckpt | out-file -filepath $path
            printLog debug "Set checkpoint '$ckpt' to file '$path' successfully."
            break
        } catch [Exception] {
            if ($retry -gt 0) {
                printLog debug "Got exception when setting checkpoint. Retry $retry..."
                $retry -= 1
                continue
            }
            $retry -= 1
            printLog error "Set checkpoint failed to file '$path'. Next time that might be some duplicated data for command '$cmd'."
        }finally{
            $mutex.ReleaseMutex() | Out-Null
        }
    }

    return
}

###############################################
# Function name: getTimeProperties
# Description: get all the "datetime" properties
# Parameters:
#       - obj [object]    : the PowerShell object
# Return:
#       - timeprops [array] : property name which type is "datetime"
###############################################

Function getTimeProperties($obj)
{
    $timeprops = @()
    try {
        $props = $obj | Get-Member -MemberType Property
    } catch {
        printLog debug "$obj is not a PowerShell Object."
        return $timeprops
    }
    foreach ($prop in $props) {
        $definition = $prop.definition
        if ($definition.StartsWith('datetime') -or $definition.StartsWith('System.Nullable[datetime]') -or $definition.StartsWith("System.Datetime") ) {
            $timeprops += $prop.name
        }
    }
    return $timeprops
}

###############################################
# Function name: executeCmd
# Description: execute the SCOM command
# Parameters:
#       - cmd [string] : the command to be executed
# Return:
#       - objs [array] : results of the PowerShell objects
###############################################

Function executeCmd($managementgroup, $cmd, $starttime)
{
    try {
        if ($a_allowed_commands -Contains $cmd){
            printLog debug "--> executeCmd $managementgroup $cmd"
        } else {
            throw "Command '$cmd' outside of allowed commands list"
        }

        if ($g_timestamp.Keys -contains $cmd) {
            $timefield = $g_timestamp.$cmd
            $timestamp = getCheckpoint $managementgroup $cmd
            if ($timestamp){ # continue data collection from timestamp, highest priority
                $starttime = $timestamp
            }
            elseif (-Not $starttime){ #if timestamp and starttime aren't present, use the default starttime
                $starttime = $default_starttime
            }
            $timestamp = $starttime
        }


        if ($timestamp) { # the ckpt from file
            printLog debug "Get objects '$cmd' when '$timefield' > $timestamp"
            iex $cmd | where {$_.$timefield -gt $timestamp} | ForEach-Object {
                return $_
            }
        } else {
            printLog debug "Get object '$cmd' without checkpoint"
            if(-Not ($cmd.ToLower() -eq "Get-SCOMOverrideResult -Instance (Get-SCOMClassInstance) -Monitor (Get-SCOMMonitor)".ToLower())){
                iex $cmd |ForEach-Object{
                    return $_
                }
            } else {
                printLog debug "handle result: Get-SCOMOverrideResult -Instance (Get-SCOMClassInstance) -Monitor (Get-SCOMMonitor)"
                iex $cmd | ForEach-Object {
                    $_ | ForEach-Object {
                        return $_
                    }
                }
            }
        }
    } catch [Exception] {
        $info = "Execute command '$cmd' failed. {0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
        printLog warn $info
        return $null
    }
}

###############################################
# Function name: serialize
# Description: serialize the PowerShell objects to strings. Print results to stdout
# Parameters:
#       - cmd [string]  : the SCOM command
#       - objs [array]  : the PowerShell objects
# Return:
#       - None
###############################################

Function serialize($managementgroup, $cmd, $objs, $objsMetaData)
{
    if($objsMetaData.first_exec_flag -eq 1){
        printLog debug "--> serialize($cmd)"
    }
    if ($objs -eq $null) {
        printLog debug "No data to serialize."
        return
    }

    $addProps = $g_properties.$cmd

    if($objsMetaData.first_exec_flag -eq 1){
        $objsMetaData.timeprops_ref = getTimeProperties($objs[0])
    }

    if ($objs.gettype().name -eq "string") {
        $value = $objs.Trim().replace('"', "'")
        $props = @{
            $cmd = $value
            "scom_command" = $cmd.ToLower()
        }
        if ($objsMetaData.scomGroup) {
            $props."splunk_scom_group" = $objsMetaData.scomGroup.ToLower()
       }
        printLog debug "Command '$cmd' returns a string $value."
        New-object PSObject -Property $props
        return
    }

    foreach ($obj in $objs) {
        $outprops = @{}
        $props = @{}

        # convert properties to hash
        $obj.psobject.properties | foreach {$props[$_.name] = $_.value}

        foreach ($prop in $props.keys) {
            $value = $props.$prop
            # add properties based on g_properties
            if ($addProps) {
                foreach ($item in $addProps.keys) {
                    $outprops.$item = $addProps.$item
                }
            }

            # the datetime properties is already in UTC time
            if ($value -and ($objsMetaData.timeprops_ref -contains $prop)) {
                $time = (Get-Date $value)
                $value = $time.ToString("MM'/'dd'/'yyyy HH:mm:ss")
            }

            # replace " to '
            if ($value -and ($value.ToString().Contains('"'))) {
                $value = $value.ToString().Trim().replace('"', "'")
            }

            $prop = $prop.ToLower()

            $propstrs = @()
            foreach ($val in $value) {
                if($val -eq $null){
                    continue
                }
                $str = $val.ToString()
                if ($g_object2string.Keys -contains $str) {
                    $sprop = $g_object2string.$str
                    $propstrs += $val.$sprop
                } else {
                    $propstrs += $str
                }
            }

            #handle key containing "[" or "]"
            $prop_escape = $prop.replace("[","_")
            $prop_escape = $prop_escape.replace("]","_")
            $prop_str = $propstrs -Join ", "
            $prop_str = [Security.SecurityElement]::Escape($prop_str)
            $outprops.$prop_escape= $prop_str
        }

        # add original command to event
        $outprops."scom_command" = $cmd.ToLower()

        if ($objsMetaData.scomGroup) {
            $outprops."splunk_scom_group" = $objsMetaData.scomGroup.ToLower()
        }

        if ($objsMetaData.timefield) {
            $time = $obj.$timefield
            #set timestamp field
            $outprops[$scom_timestamp] = $outprops[$objsMetaData.timefield.ToLower()]
            if ($objsMetaData.latestTime_ref -lt $time) {
                $objsMetaData.latestTime_ref = $time
            }
        }

        New-object PSObject -Property $outprops
    }
}

###############################################
# Function name: getCommands
# Description: check groups & commands of the args
# Parameters:
#       - groups [array]   : the command groups predefined in the $g_groups
#       - commands [array] : the arbitrary commands
# Return:
#       - commands [array] : the unique commands from both groups & commands
###############################################

Function getCommands($groups, $commands)
{
    printLog debug "--> getCommands (groups=$groups, commands=[$commands])"
    $cmds = @{}

    if ($groups) {
        foreach ($group in $groups) {
            if ($g_groups.Keys -contains $group) {
                foreach ($item in $g_groups.$group) {
                    $cmds.$item = 1
                }
                printLog debug "Add group '$group'."
            } else {
                printLog error "Group '$group' is not defined. Remove it."
            }
        }
    }

    foreach ($item in $commands) {
        $cmds.$item = 1
    }

    if (-not $cmds) {
        printLog error "No commands or groups found. Please check the parameters. Exit running."
        exit 0
    }
    return $cmds.Keys
}


###############################################
# Function name: run
# Description: main method for SCOM TA
# Parameters:
#       - groups [array]    : the command groups predefined in the $g_groups
#       - commands [array]  : the arbitrary commands
#       - loglevel [string] : debug log level, should be debug, warn or error
# Return:
#       - None
###############################################

Function run($groups, $commands, $managementgroup, $loglevel, $starttime, $performancefilter)
{
    printLog debug "--> run (groups=$groups, commands=[$commands], loglevel=$loglevel)"

    if($managementgroup){
        try{
            newSCOMManagementGroupConnection($managementgroup)
        }catch [ScomTAServerConfigurationException]{
            printLog error "Server $managementgroup is missing/deleted/misconfigured."
            $conf_url = $SplunkServerUri.Trim("/") + "/servicesNS/nobody/Splunk_TA_microsoft-scom/messages"
            $headers = @{Authorization = "Splunk " + $SplunkSessionKey}
            $body = @{severity = "error"; name = "$managementgroup Error";
            value = "Server $managementgroup is missing/deleted/misconfigured."}
            $message = Invoke-RestMethod -Method POST -URI $conf_url -Body $body -Headers $headers
            return
        }catch [Exception] {
            $info = "New SCOMManagementGroupConnection Fail: {0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
            printLog error $info
            return
        }
    }

    # checkpoint dir
    if (-not (Test-Path $g_ckptPath)) {
        (MD $g_ckptPath)
        printLog debug "Create dir '$g_ckptPath'"
    }

    $cmds = getCommands $groups $commands

    printLog debug "Command list: $cmds"
    foreach ($cmd in $cmds) {
        $timefield = $null
        if ($cmd -ne $perfdata_cmd) {
            try{
                if ($g_timestamp.Keys -contains $cmd) {
                    $timefield = $g_timestamp.$cmd
                }
                if ($groups) {
                    foreach ($group in $g_groups.Keys) {
                        if ($g_groups.$group -Contains $cmd) {
                            $scomGroup = $group.ToUpper()
                            printLog debug "Add field splunk_scom_group='$scomGroup'"
                            break
                        }
                    }
                }
                $objCount = 0
                executeCmd $managementgroup $cmd $starttime | ForEach-Object -Begin {
                    # Initialize values for first execution
                    $timeprops = @()
                    $latestTime = (Get-Date  "01/01/1999 00:00:00")
                    $objsMetaData = @{
                        first_exec_flag = 1;
                        timefield = $timefield;
                        scomGroup = $scomGroup;
                        timeprops_ref = $timeprops;
                        latestTime_ref = $latestTime;
                    }
                } -Process {
                        # In case of the exception in the executecmd, we don't have to increase the count
                        if ($_ -ne $null){
                            $objCount += 1
                        }
                        serialize $managementgroup $cmd $_ $objsMetaData
                        $objsMetaData.first_exec_flag = 0
                }
                printLog debug "Get $($objCount) objects by '$cmd'"
                $latestTime = $objsMetaData.latestTime_ref

                if ($objCount -eq 0) {
                    if ($g_timestamp.Keys -contains $cmd) {
                        printLog debug "No result for Command '$cmd' with checkpoint."
                    } else {
                        printLog debug "No result for Command '$cmd'. Please check your environment."
                    }
                }
				if($timefield -and $objCount -gt 0) {
                    setCheckpoint $managementgroup $cmd $latestTime.ToString("MM/dd/yyyy HH:mm:ss.fff")
                }
            }catch [Exception]{
                $info = "{0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
                printLog error $info
            }
        }else{
            GetSCOMPerformanceData $managementgroup $cmd $starttime $performancefilter
        }
    }
}

Function GetSCOMPerformanceData($managementgroup, $cmd, $starttime, $performancefilter){
    printLog debug "--> executeCmd $managementgroup $cmd"
    $timestamp = getCheckpoint $managementgroup $cmd
    $timefield = "TimeSampled"
    try {
        if (-Not $starttime){
            $starttime = $default_starttime
        }
        if ($timestamp -and ($timestamp -gt $starttime)) { # the ckpt from file
            $starttime = $timestamp
        }
        $endtime = (Get-Date).ToUniversalTime().Addminutes(-15)
        #the GetValueReader api don't use the millisecond field for time filter
        $endtime = (Get-Date $endtime.ToString("yyyy-MM-dd HH:mm:ss"))
        if ($endtime -lt $starttime){
            printLog error "The starttime is illegal: endtime:$endtime < starttime:$starttime"
            return
        }
        printLog debug "Get objects '$cmd' when '$timefield' between $starttime and $endtime"
        try{
            $managementgroupobj = NewSCOMManagementGroupObject($managementgroup)
        }catch [Exception] {
            $info = "New SCOMManagementGroupConnection Fail: {0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
            printLog error $info
            return
        }
        $storage_info = GetTotalStorageInfo($managementgroup)

        $objCount = 0
        if ($performancefilter){
            printLog warn "Filter parameter for Performance Data is: $performancefilter"
        }else{
            printLog warn "Filter parameter for Performance Data not found. Using default parameter: CounterName IS NOT NULL"
            $performancefilter="CounterName IS NOT NULL"
        }
        $reader = $managementgroupobj.OperationalData.GetMonitoringPerformanceDataReader($performancefilter)

        while ($reader.Read())
        {
            #Create the performance data object and then get values in the date/time range
            $perfData = $reader.GetMonitoringPerformanceData()
            $valueReader = $perfData.GetValueReader($starttime,$endtime)
            #Return each value
            while ($valueReader.Read())
            {
                $extra_info = @{}
                $perfValue = $valueReader.GetMonitoringPerformanceDataValue()
                if($perfValue."TimeSampled" -ge $endtime){
                    continue
                }
                $perf_fullname = $perfData.'monitoringobjectfullname'
                if($storage_info.$perf_fullname -ne $null){
                    $extra_info.'total_storage_mb' = $storage_info.$perf_fullname
                }
                NewReturnPerfObject $perfData $perfValue $extra_info
                $objCount = $objCount + 1
            }
        }
    } catch [Exception] {
        $info = "Execute command '$cmd' failed. {0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
        printLog warn $info
        return $null
    }
    if ($objCount -eq 0) {
        if ($timestamp) {
            printLog debug "No result for Command '$cmd' with checkpoint. Won't update checkpoint"
        } else {
            printLog debug "No result for Command '$cmd'. Please check your environment."
        }
    }else{
        printLog debug "Get $objCount objects by '$cmd'"
        if($endtime){
            setCheckpoint $managementgroup $cmd $endtime.ToString("MM/dd/yyyy HH:mm:ss.fff")
        }
    }
}

Function NewSCOMManagementGroupObject($managementgroup){
    if(-not $managementgroup){
        $mg = New-Object Microsoft.EnterpriseManagement.ManagementGroup("127.0.0.1")
        return $mg
    }
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
	[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls11 -bor [Net.SecurityProtocolType]::Tls12
    $conf_url = $SplunkServerUri.Trim("/") + "/servicesNS/nobody/Splunk_TA_microsoft-scom/splunk_ta_ms_scom_server/" + [System.Net.WebUtility]::UrlEncode($managementgroup)
    $headers = @{Authorization = "Splunk " + $SplunkSessionKey}
    $body = @{output_mode="json"; "--get-clear-credential--"="1"}
    $result =  Invoke-RestMethod -Method Post -Uri $conf_url -Headers $headers -Body $body
    $server_conf_url = $SplunkServerUri.Trim("/") + "/servicesNS/nobody/Splunk_TA_microsoft-scom/configs/conf-microsoft_scom_servers/" + [System.Net.WebUtility]::UrlEncode($managementgroup)
    $server_body = @{output_mode="json"}
    $server_result =  Invoke-RestMethod -Method Post -Uri $server_conf_url -Headers $headers -Body $server_body
    $computerName = $server_result.entry.content.host
    $username = $result.entry.content.username
    $password = $result.entry.content.password
    $settings = New-Object Microsoft.EnterpriseManagement.ManagementGroupConnectionSettings($computerName)
    $settings.Username = $username
    $settings.Password = ConvertTo-SecureString $password -AsPlainText -Force
    $mg = New-Object Microsoft.EnterpriseManagement.ManagementGroup($settings)
    printLog debug "New SCOMManagementGroupConnection success"
    return $mg
}

Function NewReturnPerfObject($perfData, $perfValue, $extra_info){
    $outprops = @{}
    foreach ($prop in $extra_info.keys) {
        $value = $extra_info.$prop
        $outprops.$prop = $value
    }
    $perfData.psobject.properties | foreach {$outprops[$_.name.ToLower()] = $_.value}
    $perfValue.psobject.properties | foreach {$outprops[$_.name.ToLower()] = $_.value}
    $outprops."scom_command" = $perfdata_cmd.ToLower()
    #handle timeadded field
    if($outprops["timesampled"]){
        $time_added = $outprops["timesampled"]
        $outprops[$scom_timestamp] = $time_added
    }
    New-object PSObject -Property (EscapeXML $outprops)
}

class ScomTAServerConfigurationException: System.Exception{
    $Emessage
    ScomTAServerConfigurationException([string]$msg){
        $this.Emessage=$msg
    }
}

# jscpd:ignore-start
Function newSCOMManagementGroupConnection($managementgroup){
    $managementgrouparray = $managementgroup -split ","
    $managementgrouparray | ForEach-Object {
        [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls11 -bor [Net.SecurityProtocolType]::Tls12
        $conf_url = $SplunkServerUri.Trim("/") + "/servicesNS/nobody/Splunk_TA_microsoft-scom/splunk_ta_ms_scom_server/" + [System.Net.WebUtility]::UrlEncode($PSItem)
        $headers = @{Authorization = "Splunk " + $SplunkSessionKey}
        $body = @{output_mode="json"; "--get-clear-credential--"="1"}
        $server_conf_url = $SplunkServerUri.Trim("/") + "/servicesNS/nobody/Splunk_TA_microsoft-scom/configs/conf-microsoft_scom_servers/" + [System.Net.WebUtility]::UrlEncode($managementgroup)
        $server_body = @{output_mode="json"}
        $SCOMManagementGroupConnection = $false
        try{
            $result =  Invoke-RestMethod -Method Post -Uri $conf_url -Headers $headers -Body $body
            $server_result = Invoke-RestMethod -Method Post -Uri $server_conf_url -Headers $headers -Body $server_body
            $SCOMManagementGroupConnection = $true
        }catch [Exception] {
            $info = "New SCOMManagementGroupConnection Fail: {0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
            printLog error $info
            throw [ScomTAServerConfigurationException]"The server $PSItem is either missing or misconfigured"
        }
        if ( $SCOMManagementGroupConnection ){
            $computerName = $server_result.entry.content.host
            $username = $result.entry.content.username
            $password = $result.entry.content.password
            $SecureString = ConvertTo-SecureString $password -AsPlainText -Force
            $Credentials = New-Object System.Management.Automation.PSCredential $username, $SecureString
            New-SCOMManagementGroupConnection -ComputerName $computerName -Credential $Credentials
            printLog debug "New SCOMManagementGroupConnection success"
        }
    }
}
# jscpd:ignore-end

Function GetTotalStorageInfo($managementgroup){
    $storage_info = @{}
    try{
        $logicaldisks = Get-SCOMClass -Name "*logicaldisk*" | Get-SCOMClassInstance
        $physicaldisks =  Get-SCOMClass -Name "*physicaldisk*" | Get-SCOMClassInstance
        if($logicaldisks -ne $null){
            foreach ($logicaldisk in $logicaldisks){
                if($logicaldisk.'[microsoft.windows.server.logicaldisk].sizeinmbs' -ne $null){
                    $dest_fullname = $logicaldisk.'fullname'
                    $storage_size = $logicaldisk.'[microsoft.windows.server.logicaldisk].sizeinmbs'.'value'
                    $storage_info.$dest_fullname = $storage_size
                }
            }
        }
        if($physicaldisks -ne $null){
            foreach ($physicaldisk in $physicaldisks){
                if($physicaldisk.'[microsoft.windows.server.physicaldisk].sizeinmbs' -ne $null){
                    $dest_fullname = $physicaldisk.'fullname'
                    $storage_size = $physicaldisk.'[microsoft.windows.server.logicaldisk].sizeinmbs'.'value'
                    $storage_info.$dest_fullname = $storage_size
                }
            }
        }
        return $storage_info
    }catch [Exception]{
        $info = "cannot get storage info of physical or logical disks: {0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
        printLog error $info
        return $storage_info
    }
}




Function import_scom_module(){
    $mutex = new-object System.Threading.Mutex $false, "scom_module"
    try{
        $mutex.WaitOne() | Out-Null
        import-module OperationsManager
        return $true
    }catch [Exception] {
        printLog error "import_scom_module exception ... $_"
        return $false
    } finally {
        # unlock
        $mutex.ReleaseMutex() | Out-Null
    }
}

###############################################
# Entrance of SCOM TA
###############################################
$ret = setupLog($loglevel)
if ($SplunkStanzaName -eq $null) {
    # Handle StanzaName for Splunk 7.3.0
    $SplunkStanzaName = $stanza.name
}

printLog warn "Start SCOM TA"
$mutex = new-object System.Threading.Mutex $false, ("scom_" + $SplunkStanzaName)
try{
   if ($mutex.WaitOne(1000)) {
        try {
            if ($groups -or $commands) {
                if($starttime){
                    $starttime =  (Get-Date -Date $starttime).ToUniversalTime()
                }
                $import_success = import_scom_module
                if(-not $import_success){
                    return
                }
                run $groups $commands $server $loglevel $starttime $performancefilter
            } else {
                printLog error "Need at least one of -groups and -commands parameters."
            }
        } catch [Exception]{
            $info = "{0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
            printLog error $info
        } finally {
            # unlock
            $mutex.ReleaseMutex()
        }
    } else {
        printLog warn "There is another input named '$SplunkStanzaName' is running. This round just exits"
    }
}catch [Exception]{
    $info = "run scom exception ... {0}`n{1}`n{2}" -f $_, $_.ScriptStackTrace,$_.Exception.StackTrace
    printLog error $info
}finally{
    printLog warn "End SCOM TA"
}
