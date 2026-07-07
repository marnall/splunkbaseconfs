##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

Function newSCOMManagementGroupConnection($computerName,$username,$password){
    $SecureString = ConvertTo-SecureString $password -AsPlainText -Force
    $Credentials = New-Object System.Management.Automation.PSCredential $username, $SecureString
    New-SCOMManagementGroupConnection -ComputerName $computerName -Credential $Credentials
}

try{
    import-module OperationsManager
    $computerName=[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[0]))
    $username=[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[1]))
    $password=[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($args[2]))
    newSCOMManagementGroupConnection $computerName $username $password
}catch [Exception] {
    $string_err = $_ | Out-String
    $msg = "Failed to establish a connection with SCOM server: {0}`n{1}`n{2}" -f $string_err, $_.ScriptStackTrace,$_.Exception.StackTrace
    return "$msg"
}
return "true"
