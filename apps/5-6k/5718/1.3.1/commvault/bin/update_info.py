#This is used when user uses Forwarder configuration table to update the details

import sys
import encode_decode
import requests
import splunklib.client as splunk_client
import splunk.Intersplunk
import splunklogger as SL
import helper
import clean_operation
import installation_helper

def forwarder_info():
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

def update_forwarder_info(ip, type):
    fp = open("../local/forwarder_details.conf","a")
    commserver_content = "[" + commserve + "]\n"
    client_name_content = "clientname:" + client_name + '\n'
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
            SL.make_entry("update_info","Enabling splunk forwarder app on client machine")
            req_command = installation_helper.enable_forwarder_command(splunk_username, splunk_password, client_name, client_id, splunk_home_dir)
            resp = installation_helper.make_command_request(commserve_url, auth_code, req_command)
            installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            helper.splunk_service_check(ip,splunk_port,splunk_username,splunk_password)
            SL.make_entry("update_info","Splunk forwarder app enabled successfully")

            #Commented below code as we dont point the forwarder to indexer anymore
            # SL.make_entry("update_info","Making splunk forwarder configuration")
            # req_command = installation_helper.config_forwarder_command(splunk_username, splunk_password, client_name, client_id, splunk_home_dir, splunk_ip_port)
            # resp = installation_helper.make_command_request(commserve_url, auth_code, req_command)
            # installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            # helper.splunk_service_check(ip,splunk_port,splunk_username,splunk_password)
            # SL.make_entry("update_info","Splunk forwarder app configuration successful")

        else:
            #code for unix

            service = splunk_client.connect(host=ip,port=splunk_port,username=splunk_username,password=splunk_password)
            splunk_home_dir = service.settings['content']['SPLUNK_HOME']
            SL.make_entry("update_info","Enabling splunk forwarder app on client machine")
            forwarder_add_command = "cd %s/bin &amp;&amp; ./splunk enable app SplunkForwarder -auth %s:%s"
            req_command = forwarder_add_command % (splunk_home_dir, splunk_username, splunk_password)
            req_param = installation_helper.request_unix_command(req_command, client_id, client_name)
            resp = installation_helper.make_command_request(commserve_url, auth_code, req_param)
            installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            helper.splunk_service_check(ip, splunk_port, splunk_username, splunk_password)
            SL.make_entry("update_info","Enabling splunk forwarder app on client machine successful")

            #Commented below code as we dont point the forwarder to indexer anymore
            # SL.make_entry("update_info","Making forwarder configuration on client machine")
            # forwarder_add_command = "cd %s/bin &amp;&amp; ./splunk add forward-server %s -auth %s:%s"
            # req_command = forwarder_add_command % (splunk_home_dir, splunk_ip_port, splunk_username, splunk_password)
            # req_param = installation_helper.request_unix_command(req_command, client_id, client_name)
            # resp = installation_helper.make_command_request(commserve_url, auth_code, req_param)
            # installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            # helper.splunk_service_check(ip,splunk_port,splunk_username,splunk_password)
            # SL.make_entry("update_info","Forwarder configuration successful")

        forwarder_app = r"https://" + ip + ":" + str(splunk_port) + "/servicesNS/nobody/SplunkForwarder/configs/conf-inputs"

    else:
        forwarder_app = r"https://" + ip + ":" + str(splunk_port) + "/servicesNS/nobody/SplunkUniversalForwarder/configs/conf-inputs"

    stanza_name = r"monitor://" + log_dir
    data = {'name':stanza_name, 'index': index_name, 'sourcetype':'commvaultlogs', 'disabled':'false', 'crcSalt':'<SOURCE>', 'blacklist': r'^(.*)?_\d*_*.log'}
    returned_resp = requests.post(forwarder_app, data=data, auth=(splunk_username, splunk_password), verify=False)
    if returned_resp.status_code != 201:
        SL.make_entry("update_info", "Monitor request failed with error " + str(returned_resp.text))
        raise Exception("Failed To Monitor File")

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

def monitor_client(client_ip, index_name, log_dir, splunk_username, splunk_password, splunk_port, type, commserve, client_name, session_key):

    monitor_file(client_ip, index_name, log_dir, splunk_username, splunk_password, splunk_port, type, commserve, client_name, session_key)
    installation_helper.restart_splunk(client_ip, username=splunk_username, password=splunk_password, port=splunk_port)

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

def get_indexer_info():
    try:
        fp = open("../local/indexerip.conf","r")
        contents = fp.read()
        content_list = contents.split('\n')
        return content_list[0]
    except Exception as excp:
        return ""

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

try:

    SL.make_entry("update_info","************Starting executing updateoperation***********")
    commserve = sys.argv[1]
    res,d1,settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']
    for i in res:
        client_list = i['myclient'].split(",")
        username_list = i['myusername'].split(",")
        password_list = i['mypassword'].split("cvpass")
        mgmport_list = i['mymgmport'].split(",")

    for i in range(len(client_list)):
        try:
            client_name = client_list[i]
            splunk_username = username_list[i]
            splunk_password = password_list[i]
            splunk_port = mgmport_list[i]
            SL.make_entry("update_info","checking client in staged files")
            ip,type = forwarder_info() #content in temp file where we stage
            if ip == "":
                #code to change details of already configured forwarders
                SL.make_entry("update_info","Updating already existing info")
                update_already_existing(commserve,client_name,splunk_username,splunk_password,splunk_port)
            else:
                commserve_client = read_new_client_file()

                if(commserve not in commserve_client):
                    SL.make_entry("update_info", "Client " + client_name + " do not exist, might have been removed because of previous errors. Please again select the client for monitoring")
                    continue

                if(client_name not in commserve_client[commserve]):
                    SL.make_entry("update_info", "Client " + client_name + " do not exist, might have been removed because of previous errors. Please again select the client for monitoring")
                    continue

                SL.make_entry("update_info","Saving newly acquired information")
                updated_type = update_forwarder_info(ip,type)  #write to forwarder_details.conf
                delete_entry(commserve,client_name)
                SL.make_entry("update_info","Checking for index configuration")
                if(check_index_conf()):
                    index_name = get_index()
                    indexer_ip_port = get_indexer_info()
                    log_dir = get_log_directory(commserve,client_name)
                    SL.make_entry("update_info","Index set to " + index_name)
                    SL.make_entry("update_info","Sending monitoring request to client " + client_name)
                    if index_name != "":
                        try:
                            monitor_client(ip, index_name, log_dir, splunk_username, splunk_password, splunk_port, updated_type, commserve, client_name, session_key)
                        except Exception as excp:
                            SL.make_entry("update_info","Failed to monitor client " + client_name)
                            clean_operation.clean(client_name, commserve)
                            helper.commit_failed_clients(client_name, commserve, 'Monitor Log Files')
                            continue

                        SL.make_entry("update_info","Successfully started monitoring " + client_name)
                        remove_from_new_client([client_name],commserve)
                        SL.make_entry("update_info","Removed client from staging")
        except Exception as excp:
            SL.make_entry("update_info", "Operation failed for client " + client_name)
            clean_operation.clean(client_name, commserve)
            helper.commit_failed_clients(client_name, commserve, 'Service error')
            continue

    SL.make_entry("update_info","Finished executing update operation")
except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = 'ERROR ' + str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("update_info",entry_content)
