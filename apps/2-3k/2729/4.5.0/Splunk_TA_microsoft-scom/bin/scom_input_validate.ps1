#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

# Import module function for dll file
Function import_scom_module(){
    $mutex = new-object System.Threading.Mutex $false, "scom_input_validation_module"
    try{
        $mutex.WaitOne() | Out-Null
        import-module OperationsManager
        return $true
    } catch [Exception]{
        return $false
    } finally{
        # unlock
        $mutex.ReleaseMutex() | Out-Null
    }
}
# Function for scom management group connection
Function NewSCOMManagementGroupObject($managementgroup,$serveruri,$sessionkey){
    if($managementgroup -eq "localhost"){
        $mg = New-Object Microsoft.EnterpriseManagement.ManagementGroup("127.0.0.1")
        return $mg
    }
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls11 -bor [Net.SecurityProtocolType]::Tls12
    $conf_url = $serveruri + "/servicesNS/nobody/Splunk_TA_microsoft-scom/splunk_ta_ms_scom_server/" + [System.Net.WebUtility]::UrlEncode($managementgroup)
    $headers = @{Authorization = "Splunk " + $sessionkey}
    $body = @{output_mode="json"; "--get-clear-credential--"="1"}
    $result =  Invoke-RestMethod -Method Post -Uri $conf_url -Headers $headers -Body $body
    $server_conf_url = $serveruri + "/servicesNS/nobody/Splunk_TA_microsoft-scom/configs/conf-microsoft_scom_servers/" + [System.Net.WebUtility]::UrlEncode($managementgroup)
    $server_body = @{output_mode="json"}
    $server_result =  Invoke-RestMethod -Method Post -Uri $server_conf_url -Headers $headers -Body $server_body
    $computerName = $server_result.entry.content.host
    $username = $result.entry.content.username
    $password = $result.entry.content.password
    $settings = New-Object Microsoft.EnterpriseManagement.ManagementGroupConnectionSettings($computerName)
    $settings.Username = $username
    $settings.Password = ConvertTo-SecureString $password -AsPlainText -Force
    $mg = New-Object Microsoft.EnterpriseManagement.ManagementGroup($settings)
    return $mg
}

$import_success = import_scom_module
if(-not $import_success){
	return "Encountered an error while importing OperationsManager SCOM module."
}
try{
        $server = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[0]))
        $server_uri = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[1]))
        $session_key = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[2]))

		$managementgroupobj = NewSCOMManagementGroupObject $server $server_uri $session_key

	}catch [Exception] {
        $string_err = $_ | Out-String
        $msg = "Failed to establish a connection with SCOM server: {0}`n{1}`n{2}" -f $string_err, $_.ScriptStackTrace,$_.Exception.StackTrace
        return "$msg"
	}
# Checking given filter parameter
try{
        $filter_parameter = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[3]))
		$reader = $managementgroupobj.OperationalData.GetMonitoringPerformanceDataReader($filter_parameter)
	}catch [Exception] {

		return "Invalid Filter Parameter provided."
	}
	return "True"
