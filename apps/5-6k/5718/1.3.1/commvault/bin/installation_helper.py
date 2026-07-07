import requests
import xmltodict
import json
import base64
import os
import http
import sys
import encode_decode
import splunk.Intersplunk
import splunklib.client as splunk_client
import helper
import time
import clean_operation
import splunklogger as SL

def monitor_file(ip, index_name, log_dir):
    forwarder_app = r"https://" + ip + ":8089/servicesNS/nobody/SplunkUniversalForwarder/configs/conf-inputs"
    stanza_name = r"monitor://" + log_dir
    data = {'name':stanza_name, 'index': index_name, 'sourcetype':'commvaultlogs', 'disabled':'false', 'crcSalt':'<SOURCE>', 'blacklist': r'^(.*)?_\d*_*.log'}
    returned_resp = requests.post(forwarder_app, data=data, auth=('admin', 'commvaultadmin'), verify=False)
    if returned_resp.status_code != 201:
        SL.make_entry("installation_helper", "Monitor Request Failed.Entry might already be present.Check inputs.conf file of forwarder app in client machine, status code " + str(returned_resp.status_code) + " " + returned_resp.text)
        raise Exception("Monitor Request Failed")

def restart_splunk(ip, port='8089', username='admin', password='commvaultadmin'):
    service = splunk_client.connect(host=ip, port=port, username=username, password=password)
    service.restart()
    time.sleep(15)

def request_process_check_command(client_id, client_name):

    command = '<App_ExecuteCommandReq arguments="" scriptType="2" waitForProcessCompletion="1"> <client clientId="%s" clientName="%s"/>'
    command += '<scriptLines val="$ComputerName = $null"/>'
    command += '<scriptLines val="$CredentialsFile = $null"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="Function ExecuteCommand() {"/>'
    command += '<scriptLines val="    Get-Service | Where-Object {$_.Name -like &quot;*Splunk*&quot;}"/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="If ($ComputerName -eq $null) {"/>'
    command += '<scriptLines val="    ExecuteCommand"/>'
    command += '<scriptLines val="} Else {"/>'
    command += '<scriptLines val="    Set-Item WSMan:\localhost\Client\Trustedhosts -Value $ComputerName -Concatenate -Force"/>'
    command += '<scriptLines val="    $Credentials = Import-Clixml $CredentialsFile"/>'
    command += '<scriptLines val="    Invoke-Command -ComputerName $ComputerName -Credential $Credentials -ScriptBlock ${function:ExecuteCommand} -HideComputerName"/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val=""/>"'
    command += '</App_ExecuteCommandReq>'

    return command % (str(client_id),client_name)

def make_command_request(url, auth_code, req_parmeter):

    url = url + "/SearchSvc/CVWebService.svc/Qcommand/qoperation execute"
    headers = {"Authtoken": auth_code, "Accept":"application/json"}
    response = requests.request("POST", url, headers=headers, data = req_parmeter)
    if response.status_code == 200:
        return response
    raise Exception("Failed To Run Command Remotely")

def handle_resp(resp):

    if resp.status_code == 200:
        json_output = resp.json()
        if "errorMessage" not in json_output:
            if "commandLineOutput" in json_output:
                return json_output["commandLineOutput"]
            return ""
        SL.make_entry("installation_helper","ERROR " + json_output["errorMessage"])
        raise Exception("Remote Command Request Failed")
    raise Exception("Remote Command Request Failed")

def request_unix_command(command, client_id, client_name):

    xml_execute_command = """
        <App_ExecuteCommandReq arguments="" command="{0}" waitForProcessCompletion="1">
            <processinginstructioninfo>
                <formatFlags continueOnError="1" elementBased="1" filterUnInitializedFields="0" formatted="0" ignoreUnknownTags="1" skipIdToNameConversion="0" skipNameToIdConversion="0"/>
            </processinginstructioninfo>
            <client clientId="{1}" clientName="{2}"/>
        </App_ExecuteCommandReq>
        """.format(
            command,
            client_id,
            client_name
        )

    return xml_execute_command

def check_software_status(client_name, commserve, client_id, auth_code, url):
    SL.make_entry("installation_helper","Getting OS info of client " + client_name)
    os_type = helper.get_os_info(auth_code, client_id, url)
    if 'windows' in os_type.lower():

        SL.make_entry("installation_helper","OS info of client set to windows")
        SL.make_entry("installation_helper","Sending process check request to client")
        req_param = request_process_check_command(client_id, client_name)

    else:
        SL.make_entry("installation_helper","OS info of client set to Unix")
        SL.make_entry("installation_helper","Sending process check command to the client")
        check_software_command = r"ps -el | grep splunk"
        req_param = request_unix_command(check_software_command, client_id, client_name)

    resp = make_command_request(url, auth_code, req_param)
    handled_resp = handle_resp(resp)
    if "SplunkForwarder" in handled_resp:
        return [True,"SplunkForwarder",os_type]
    elif "Splunkd" in handled_resp:
        return [True,"Splunkd",os_type]
    elif "splunk" in handled_resp:
        return [True,"Splunkd",os_type]
    else:
        return [False,"",os_type]

def _make_request(upload_url, file_contents, headers, request_id=None, chunk_offset=None):

    if request_id is not None:
        upload_url += '&requestId={0}'.format(request_id)

    response = requests.request("POST", url=upload_url, headers=headers, data = file_contents)

    if response.json():
        if 'errorCode' in response.json():
            error_code = int(response.json()['errorCode'])

            if error_code != 0:
                error_string = response.json()['errorString']
                raise Exception('File Upload Failed')

        if 'requestId' in response.json():
            request_id = response.json()['requestId']

        if 'chunkOffset' in response.json():
            chunk_offset = response.json()['chunkOffset']

        return request_id, chunk_offset

    else:
        raise Exception('File Upload  Failed')

def upload_file(source_file_path, destination_folder, auth_code, client_id, url):

    chunk_size = 1024 ** 2 * 2
    request_id = None
    chunk_offset = None

    file_name = os.path.split(source_file_path)[-1]

    file_size = os.path.getsize(source_file_path)
    headers = {
        'Authtoken': auth_code,
        'Accept': 'application/json',
        'FileName': base64.b64encode(file_name.encode('utf-8')),
        'FileSize': str(file_size),
        'ParentFolderPath': base64.b64encode(destination_folder.encode('utf-8'))
    }

    file_stream = open(source_file_path, 'rb')

    if file_size <= chunk_size:

        upload_url = url + "/SearchSvc/CVWebService.svc/Client/%s/file/action/upload?uploadType=fullFile"
        upload_url = upload_url % str(cient_id)
        _make_request(upload_url, file_stream.read(), headers)

    else:

        upload_url = url + "/SearchSvc/CVWebService.svc/Client/%s/file/action/upload?uploadType=chunkedFile"
        upload_url = upload_url % str(client_id)

        while file_size > chunk_size:
            file_size = file_size - chunk_size
            headers['FileEOF'] = str(0)
            request_id, chunk_offset = _make_request(
                upload_url, file_stream.read(chunk_size), headers, request_id, chunk_offset
            )

        headers['FileEOF'] = str(1)
        _make_request(
            upload_url, file_stream.read(file_size), headers, request_id, chunk_offset
        )

def request_install_command(client_id, client_name, file_path, indexer_ip_port):

    command = '<App_ExecuteCommandReq arguments="" scriptType="2" waitForProcessCompletion="1"> <client clientId="%s" clientName="%s"/>'
    command += '<scriptLines val="$ComputerName = $null"/>'
    command += '<scriptLines val="$CredentialsFile = $null"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="Function ExecuteCommand() {"/>'
    command += '<scriptLines val="    msiexec.exe /i \'%s\' SPLUNKUSERNAME=admin SPLUNKPASSWORD=commvaultadmin SET_ADMIN_USER=1 RECEIVING_INDEXER=&#x27;%s&#x27; ENABLEADMON=1 LAUNCHSPLUNK=1 AGREETOLICENSE=yes /quiet"/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="If ($ComputerName -eq $null) {"/>'
    command += '<scriptLines val="    ExecuteCommand"/>'
    command += '<scriptLines val="} Else {"/>'
    command += '<scriptLines val="    Set-Item WSMan:\localhost\Client\Trustedhosts -Value $ComputerName -Concatenate -Force"/>'
    command += '<scriptLines val="    $Credentials = Import-Clixml $CredentialsFile"/>'
    command += '<scriptLines val="    Invoke-Command -ComputerName $ComputerName -Credential $Credentials -ScriptBlock ${function:ExecuteCommand} -HideComputerName"/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val=""/>"'
    command += '</App_ExecuteCommandReq>'

    return command % (str(client_id), client_name, file_path, indexer_ip_port)

def install_software(os_type, client_id, client_name, file_path, indexer_ip_port, url, auth_code):

    json_resp = helper.client_prop(auth_code, client_id, url)
    install_dir = json_resp["clientProperties"][0]["client"]["jobResulsDir"]["path"] #changed from install dir to job results dir
    SL.make_entry("installation_helper","Starting to upload splunk software to client " + client_name)
    upload_file(file_path, install_dir, auth_code, str(client_id), url)
    SL.make_entry("installation_helper","Splunk Software upload completed")
    SL.make_entry("installation_helper","Starting Splunk Installation and configuration")

    if "/" in file_path:
        file_path_list = file_path.split("/")
    else:
        file_path_list = file_path.split("\\")

    if file_path_list[len(file_path_list)-1] == "":
        software_name = file_path_list[len(file_path_list)-2]
    else:
        software_name = file_path_list[len(file_path_list)-1]

    if 'windows' in os_type.lower():

        remote_file_path = install_dir + "\\" + software_name          #make a dir for splunk and install from there
        SL.make_entry("installation_helper","Processing software found at: " + remote_file_path)
        req_param = request_install_command(client_id, client_name, remote_file_path, indexer_ip_port)
        resp = make_command_request(url, auth_code, req_param)
        handle_resp(resp)

    else:
        remote_file_path = install_dir + "/" + software_name
        SL.make_entry("installation_helper","Processing software found at: " + remote_file_path)
        unzip_command = r"tar xvzf %s -C /opt" % remote_file_path
        req_param = request_unix_command(unzip_command, client_id, client_name)
        resp = make_command_request(url, auth_code, req_param)
        handle_resp(resp)
        configure_command = r"cd /opt/splunkforwarder/bin &amp;&amp; ./splunk start --accept-license --answer-yes --no-prompt --seed-passwd commvaultadmin"
        add_forwarder_command = r"cd /opt/splunkforwarder/bin &amp;&amp; ./splunk add forward-server '%s' -auth admin:commvaultadmin"
        add_forwarder_command = add_forwarder_command % indexer_ip_port
        req_param = request_unix_command(configure_command, client_id, client_name)
        resp = make_command_request(url,auth_code, req_param)
        handle_resp(resp)
        req_param = request_unix_command(add_forwarder_command, client_id, client_name)
        resp = make_command_request(url, auth_code, req_param)
        handle_resp(resp)

    try:
        SL.make_entry("installation_helper","Checking Splunk services on the client " + client_name)
        client_ip = helper.get_ip(auth_code, client_id, url)
        service = splunk_client.connect(host=client_ip, port="8089", username="admin", password = "commvaultadmin")
        SL.make_entry("installation_helper","Splunk services detected successfully on client " + client_name)
    except Exception as excp:
        raise Exception("Failed to detect splunk service on client")

def enable_forwarder_command(splunk_username, splunk_password, client_name, client_id, splunk_home_dir):
    command = '<App_ExecuteCommandReq arguments="" scriptType="2" waitForProcessCompletion="1"> <client clientId="%s" clientName="%s"/>'
    command += '<scriptLines val="$ComputerName = $null"/>'
    command += '<scriptLines val="$CredentialsFile = $null"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="Function ExecuteCommand() {"/>'
    command += r'<scriptLines val="    cd &#x27;%s\bin&#x27;; .\splunk enable app SplunkForwarder -auth %s:%s "/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="If ($ComputerName -eq $null) {"/>'
    command += '<scriptLines val="    ExecuteCommand"/>'
    command += '<scriptLines val="} Else {"/>'
    command += '<scriptLines val="    Set-Item WSMan:\localhost\Client\Trustedhosts -Value $ComputerName -Concatenate -Force"/>'
    command += '<scriptLines val="    $Credentials = Import-Clixml $CredentialsFile"/>'
    command += '<scriptLines val="    Invoke-Command -ComputerName $ComputerName -Credential $Credentials -ScriptBlock ${function:ExecuteCommand} -HideComputerName"/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val=""/>"'
    command += '</App_ExecuteCommandReq>'

    req_command = command % (str(client_id),client_name,splunk_home_dir,splunk_username,splunk_password)
    return req_command

def config_forwarder_command(splunk_username, splunk_password, client_name, client_id, splunk_home_dir, ip_port):
    command = '<App_ExecuteCommandReq arguments="" scriptType="2" waitForProcessCompletion="1"> <client clientId="%s" clientName="%s"/>'
    command += '<scriptLines val="$ComputerName = $null"/>'
    command += '<scriptLines val="$CredentialsFile = $null"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="Function ExecuteCommand() {"/>'
    command += r'<scriptLines val="    cd &#x27;%s\bin&#x27;; .\splunk add forward-server %s -auth %s:%s "/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val="If ($ComputerName -eq $null) {"/>'
    command += '<scriptLines val="    ExecuteCommand"/>'
    command += '<scriptLines val="} Else {"/>'
    command += '<scriptLines val="    Set-Item WSMan:\localhost\Client\Trustedhosts -Value $ComputerName -Concatenate -Force"/>'
    command += '<scriptLines val="    $Credentials = Import-Clixml $CredentialsFile"/>'
    command += '<scriptLines val="    Invoke-Command -ComputerName $ComputerName -Credential $Credentials -ScriptBlock ${function:ExecuteCommand} -HideComputerName"/>'
    command += '<scriptLines val="}"/>'
    command += '<scriptLines val=""/>'
    command += '<scriptLines val=""/>"'
    command += '</App_ExecuteCommandReq>'

    req_command = command % (str(client_id), client_name, splunk_home_dir, ip_port, splunk_username, splunk_password)
    return req_command
