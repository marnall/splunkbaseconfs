#file for updating common credetials from GUI

import sys
import os
import splunk.Intersplunk
import requests
import splunklib.client as splunk_client
import helper
import encode_decode
import splunklogger as SL
import clean_operation
import installation_helper

def read_new_client_file():
    try:
        fp = open('../local/new_client.conf','r')
    except Exception as excp:
        return {}

    contents = fp.read()
    content_list = contents.split("\n")
    commserver_client = {}
    i = 0

    while i < len(content_list)-1:
        if(content_list[i] == "[end]"):
            i = i + 1
            continue
        webserver = content_list[i].strip("]")
        webserver = webserver.split("[")[1]
        if webserver not in commserver_client:
            commserver_client[webserver] = []
        i = i + 1
        while(i < len(content_list) and content_list[i] != "[end]"):
            commserver_client[webserver].append(content_list[i])
            i = i + 1
        i = i + 1
    return commserver_client

def forwarder_info(commserve, client_name):
    try:
        fp = open('../local/forwarder.conf','r')
    except Exception as excp:
        return "",""

    contents = fp.read()
    content_list = contents.split('\n')
    i = 0
    comm_client = {}
    while( i < len(content_list)-1):
        webserver = content_list[i].strip("]")
        webserver = webserver.split("[")[1]
        if webserver == commserve:
            client_name_file = content_list[i+1].split(":")[1]
            if client_name == client_name_file:
                return content_list[i+2].split(":")[1],content_list[i+3].split(":")[1]
        i = i + 4
    return "",""

def update_forwarder_info(ip, splunk_username, splunk_password, splunk_port, client):
    fp = open("../local/forwarder_details.conf","a")
    commserver_content = "[" + commserve + "]\n"
    client_name_content = "clientname:" + client + '\n'
    client_ip_content = "clientip:" + ip + '\n'
    service = splunk_client.connect(host=ip, port=splunk_port, username=splunk_username, password=splunk_password)
    splunk_type = service.info['license_labels'][0]
    if "forwarder" in splunk_type.lower():
        type = "SplunkForwarder"
    else:
        type = "Splunkd"
    client_type_content = "type:" + type + '\n'
    splunk_username_content = "splunkusername:" + splunk_username + '\n'
    encrypted_pass = encode_decode.encode_string(splunk_password)
    splunk_password_content = "splunkpassword:" + encrypted_pass + '\n'
    splunk_port_content = "splunkport:" + splunk_port + '\n'
    fp.write(commserver_content + client_name_content + client_ip_content + client_type_content + splunk_username_content + splunk_password_content + splunk_port_content)
    fp.close()
    return type

def delete_entry(commserve,client_name):
    with open("../local/forwarder.conf","r") as fp:
        lines = fp.readlines()
    i = 0
    with open("../local/forwarder.conf","w") as fp:
        while(i < len(lines)):
            webserver = lines[i]
            webserver = webserver.split("]")[0]
            webserver = webserver.split("[")[1]
            client_name_file = lines[i+1].split(":")[1].strip("\n")
            if webserver != commserve or client_name_file != client_name:
                 fp.write(lines[i])
                 fp.write(lines[i+1])
                 fp.write(lines[i+2])
                 fp.write(lines[i+3])
            i = i + 4

def check_index_conf():
    try:
        fp = open("../local/commindex.conf","r")
        return True
    except Exception as excp:
        return False

def get_index():
    try:
        fp = open("../local/commindex.conf","r")
        content = fp.read()
        content_list = content.split("\n")
        return content_list[0]
    except Excpetion as excp:
        return ""

def get_log_directory(commserve, req_client_name):

    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    n = len(content_list)
    i = 0
    while(i < n-1):
        if commserve in content_list[i]:
            client_name = content_list[i+1].split(":")[1].strip("\r")
            if client_name == req_client_name:
                log_dir = content_list[i+7].split(":",1)[1].strip("\r")
                return log_dir
        i = i + 9


def get_os_info(commserve, req_client_name):
    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    n = len(content_list)
    i = 0
    while(i < n-1):
        if commserve in content_list[i]:
            client_name = content_list[i+1].split(":")[1].strip("\r")
            if client_name == req_client_name:
                os_info = content_list[i+6].split(":",1)[1].strip("\r")
                return os_info
        i = i + 9

def monitor_file(ip, index_name,log_dir, splunk_username, splunk_password, splunk_port, type, commserve, client_name, session_key):

    if type.lower() == "splunkd":
        os_type = get_os_info(commserve, client_name)
        username,password,commserve_url = helper.get_credentials(commserve, session_key)
        auth_code = helper.get_authcode(username,password,commserve_url)
        client_resp = helper.get_clients(auth_code,commserve_url)
        json_resp = helper.convert_to_json(client_resp)
        client_properties = json_resp["clientProperties"]
        for i in client_properties:
            client =  i["client"]["clientEntity"]["clientName"]
            if client == client_name:
                client_id = i["client"]["clientEntity"]["clientId"]
                break

        if "windows" in os_type.lower():

            service = splunk_client.connect(host=ip,port=splunk_port,username=splunk_username,password=splunk_password)
            splunk_home_dir = service.settings['content']['SPLUNK_HOME']
            SL.make_entry("update_common_cred","Enabling splunk forwarder app on client machine")
            req_command = installation_helper.enable_forwarder_command(splunk_username, splunk_password, client_name, client_id, splunk_home_dir)
            resp = installation_helper.make_command_request(commserve_url, auth_code, req_command)
            installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            helper.splunk_service_check(ip,splunk_port,splunk_username,splunk_password)
            SL.make_entry("update_common_cred","Splunk forwarder app enabled successfully")

        else:
            #code for unix

            service = splunk_client.connect(host=ip,port=splunk_port,username=splunk_username,password=splunk_password)
            splunk_home_dir = service.settings['content']['SPLUNK_HOME']
            SL.make_entry("update_common_cred","Enabling splunk forwarder app on client machine")
            forwarder_add_command = "cd %s/bin &amp;&amp; ./splunk enable app SplunkForwarder -auth %s:%s"
            req_command = forwarder_add_command % (splunk_home_dir, splunk_username, splunk_password)
            req_param = installation_helper.request_unix_command(req_command, client_id, client_name)
            resp = installation_helper.make_command_request(commserve_url, auth_code, req_param)
            installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            helper.splunk_service_check(ip, splunk_port, splunk_username, splunk_password)
            SL.make_entry("update_common_cred","Enabling splunk forwarder app on client machine successful")

        forwarder_app = r"https://" + ip + ":" + str(splunk_port) + "/servicesNS/nobody/SplunkForwarder/configs/conf-inputs"

    else:
        forwarder_app = r"https://" + ip + ":" + str(splunk_port) + "/servicesNS/nobody/SplunkUniversalForwarder/configs/conf-inputs"

    stanza_name = r"monitor://" + log_dir
    data = {'name':stanza_name, 'index': index_name, 'sourcetype':'commvaultlogs', 'disabled':'false', 'crcSalt':'<SOURCE>', 'blacklist': r'^(.*)?_\d*_*.log'}
    returned_resp = requests.post(forwarder_app, data=data, auth=(splunk_username, splunk_password), verify=False)
    if returned_resp.status_code != 201:
        SL.make_entry("update_common_cred", "Monitor request failed with error " + str(returned_resp.text))
        raise Exception("Failed To Monitor File")

def monitor_client(client_ip, index_name, log_dir, splunk_username, splunk_password, splunk_port, type, commserve, client_name, session_key):

    monitor_file(client_ip, index_name, log_dir, splunk_username, splunk_password, splunk_port, type, commserve, client_name, session_key)
    installation_helper.restart_splunk(client_ip, username=splunk_username, password=splunk_password, port=splunk_port)

def remove_from_new_client(client_list,commserve):
    with open("../local/new_client.conf","r") as fp:
        lines = fp.readlines()

    i = 0
    with open("../local/new_client.conf","w") as fp:
        while i < len(lines):
            ip = lines[i]
            webserver = ip.split("]")[0]
            webserver = webserver.split("[")[1]
            fp.write(lines[i])
            i = i + 1
            if commserve == webserver:
                while(i < len(lines) and lines[i] != "[end]"):
                    if(lines[i].strip("\n") not in client_list):
                        fp.write(lines[i])
                        i = i + 1
                    else:
                        i = i + 1
            else:
                while(i < len(lines) and lines[i] != "[end]"):
                    fp.write(lines[i])
                    i = i + 1
            if(i < len(lines) and lines[i] == "[end]"):
                fp.write(lines[i])
            i = i + 1

def configured_forwarders():
    try:
        fp = open("../local/forwarder_details.conf","r")
        content = fp.read()
        content_list = content.split('\n')
        comm_client = {}
        i = 0
        #{'comm':[cl1,cl2]}
        while(i < len(content_list)-1):
            webserver = content_list[i].strip("]")
            webserver = webserver.split("[")[1].strip("\n")
            if webserver not in comm_client:
                comm_client[webserver] = []
            client_name = content_list[i+1].split(":")[1].strip("\n")
            if client_name not in comm_client[webserver]:
                comm_client[webserver].append(client_name)
            i = i + 7
        return comm_client

    except Exception as excp:
        return {}

def update_already_existing(commserve,client_name,splunk_username,splunk_password,splunk_port):
    fp = open("../local/forwarder_details.conf","r")
    content = fp.read()
    fp.close()
    content_list = content.split("\n")
    i = 0
    with open("../local/forwarder_details.conf","w") as fp:
        while(i < len(content_list)-1):
            webserver = content_list[i].strip("]")
            webserver = webserver.split("[")[1].strip("\n")
            client_name_file = content_list[i+1].split(":")[1]
            if webserver == commserve and client_name_file == client_name:
                fp.write(content_list[i] + '\n')
                fp.write(content_list[i+1] + '\n')
                fp.write(content_list[i+2] + '\n')
                fp.write(content_list[i+3] + '\n')
                if splunk_username != " ":
                    fp.write("splunkusername:" + splunk_username + '\n')
                else:
                    fp.write(content_list[i+4] + '\n')
                if splunk_password != " ":
                    encry_pass = encode_decode.encode_string(splunk_password)
                    fp.write("splunkpassword:" + encry_pass + '\n')
                else:
                    fp.write(content_list[i+5] + '\n')
                if splunk_port != " ":
                    fp.write("splunkport:" + splunk_port + '\n')
                else:
                    fp.write(content_list[i+6] + '\n')
                i = i + 7
            else:
                for j in range(0,7):
                    fp.write(content_list[i+j] + '\n')
                i = i + 7

try:
    commserve = sys.argv[1]
    update_all_set_token = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    mgmport = sys.argv[5]

    if(update_all_set_token != "None"):
        is_update_all_set = True
    else:
        is_update_all_set = False

    results, dr, settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']

    if(username != "None" and password != "None" and mgmport != "None"):
        if(is_update_all_set):
            SL.make_entry("update_common_cred", "Getting configured forwarders")
            config_forwarders = configured_forwarders()
            if commserve in config_forwarders:
                config_clients = config_forwarders[commserve]
                for client in config_clients:
                    SL.make_entry("update_common_cred","updating already existing password for client " + client)
                    update_already_existing(commserve,client,username,password,mgmport)

        SL.make_entry("update_common_cred", "Updating cred for unconfigured clients")
        commserver_client = read_new_client_file()
        new_client_list = []
        if commserve in commserver_client:
            new_client_list = commserver_client[commserve]
            
            for client in new_client_list:
                try:
                    ip, type = forwarder_info(commserve, client)
                    SL.make_entry("update_common_cred", "Saving creds for client " + client)
                    updated_type = update_forwarder_info(ip, username, password, mgmport, client)
                    delete_entry(commserve, client)
                    SL.make_entry("update_common_cred","Checking for index configuration")
                    if(check_index_conf()):
                        index_name = get_index()
                        log_dir = get_log_directory(commserve,client)
                        SL.make_entry("update_common_cred","Index set to " + index_name)
                        SL.make_entry("update_common_cred","Sending monitoring request to client " + client)
                        if index_name != "":
                            try:
                                monitor_client(ip, index_name, log_dir, username, password, mgmport, updated_type, commserve, client, session_key)
                            except Exception as excp:
                                SL.make_entry("update_common_cred","Failed to monitor client " + client)
                                clean_operation.clean(client, commserve)
                                helper.commit_failed_clients(client, commserve, 'Monitor Log Files')
                                continue
                            SL.make_entry("update_common_cred","Successfully started monitoring " + client)
                            remove_from_new_client([client],commserve)
                            SL.make_entry("update_common_cred","Removed client from staging")
                except Exception as excp:
                    SL.make_entry("update_common_cred", "Operation failed for client " + client)
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    entry_content = str(exc_tb.tb_lineno) + ' ' + str(excp)
                    SL.make_entry("update_common_cred","ERROR " + entry_content)
                    continue
    else:
        SL.make_entry("update_common_cred", 'Provide username, password and management port to update in bulk')

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("update_common_cred","ERROR " + entry_content)
