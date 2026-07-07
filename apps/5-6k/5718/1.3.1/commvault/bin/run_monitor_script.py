# this file is invoked when index option is changed in
#splunk conf page in gui

import requests
import json
import os
import http
import sys
import encode_decode
import urllib
import splunk.Intersplunk
import splunklib.client as splunk_client
import helper
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


def client_prop(auth_code,client_name):
    url = "http://" + ip + ":81/SearchSvc/CVWebService.svc/Client/byName(clientName=\'" + client_name + "\')"
    payload = {}
    headers = {"Accept": "application/json","Authtoken": auth_code}
    response = requests.request("GET", url, headers=headers, data = payload)
    json_obj = helper.convert_to_json(response)
    osinfo = json_obj["clientProperties"][0]["client"]["osInfo"]["Type"]
    client_id = json_obj["clientProperties"][0]["client"]["clientEntity"]["clientId"]
    return osinfo, client_id

def monitor_file(ip, index_name, log_dir, splunk_username, splunk_password, splunk_port, client_name, client_id, os_info, type, commserve, commserve_url, session_key):

    if type.lower() == "splunkd":
        username, password, commserve_url = helper.get_credentials(commserve, session_key)
        auth_code = helper.get_authcode(username, password, commserve_url)
        if "windows" in os_info.lower():
            service = splunk_client.connect(host=ip,port=splunk_port,username=splunk_username,password=splunk_password)
            splunk_home_dir = service.settings['content']['SPLUNK_HOME']

            SL.make_entry("run_monitor_script", "Enabling forwarder")
            req_command = installation_helper.enable_forwarder_command(splunk_username, splunk_password, client_name, client_id, splunk_home_dir)
            resp = installation_helper.make_command_request(commserve_url, auth_code, req_command)
            installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            helper.splunk_service_check(ip,splunk_port,splunk_username,splunk_password)
            SL.make_entry("run_monitor_script", "Enabled forwarder successfully")

        else:
            #code for unix
            service = splunk_client.connect(host=ip,port=splunk_port,username=splunk_username,password=splunk_password)
            splunk_home_dir = service.settings['content']['SPLUNK_HOME']

            SL.make_entry("run_monitor_script", "Enabling forwarder")
            forwarder_add_command = "cd %s/bin &amp;&amp; ./splunk enable app SplunkForwarder -auth %s:%s"
            req_command = forwarder_add_command % (splunk_home_dir, splunk_username, splunk_password)
            req_param = installation_helper.request_unix_command(req_command, client_id, client_name)
            resp = installation_helper.make_command_request(commserve_url, auth_code, req_param)
            installation_helper.restart_splunk(ip, username=splunk_username, password=splunk_password, port=splunk_port)
            helper.splunk_service_check(ip,splunk_port,splunk_username,splunk_password)
            SL.make_entry("run_monitor_script", "Enabled forwarder successfully")

        forwarder_app = r"https://" + ip + ":" + str(splunk_port) + "/servicesNS/nobody/SplunkForwarder/configs/conf-inputs"

    else:
        forwarder_app = r"https://" + ip + ":" + str(splunk_port) + "/servicesNS/nobody/SplunkUniversalForwarder/configs/conf-inputs"

    SL.make_entry("run_monitor_script", "Sending monitor request for log file")
    stanza_name = r"monitor://" + log_dir
    data = {'name':stanza_name, 'index': index_name, 'sourcetype':'commvaultlogs', 'disabled':'false', 'crcSalt':'<SOURCE>', 'blacklist': r'^(.*)?_\d*_*.log'}
    returned_resp = requests.post(forwarder_app, data=data, auth=(splunk_username, splunk_password), verify=False)
    if returned_resp.status_code != 201:
        SL.make_entry("run_monitor_script", "Monitor request failed " + str(returned_resp.text))
        raise Exception("Monitor File Request Failed with status " + str(returned_resp.status_code))
        
    SL.make_entry("run_monitor_script", "Successfully started monitoring log files on client " + client_name)

def get_ip_from_file(req_client,ip):
    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    n = len(content_list)
    i = 0
    while(i < n-1):
        if ip in content_list[i]:
            client_name = content_list[i+1].split(":")[1].strip("\r")
            if client_name == req_client:
                client_ip = content_list[i+5].split(":")[1].strip("\r")
                return client_ip
        i = i + 9

def change_index_api(client_ip, log_dir, splunk_username, splunk_password, splunk_port, splunk_type):

    monitor_endpoint = r"monitor://" + log_dir
    try:
        url_encoded = urllib.quote(monitor_endpoint, safe="")
    except Exception as excp:
        url_encoded = urllib.parse.quote(monitor_endpoint, safe="")

    if "forwarder" in splunk_type.lower():
        forwarder_app = r"https://" + client_ip + ":" + splunk_port + "/servicesNS/nobody/SplunkUniversalForwarder/configs/conf-inputs/" + url_encoded
        data = {'index':index_name}
        returned_resp = requests.post(forwarder_app, data=data, auth=(splunk_username, splunk_password), verify=False)
    else:
        forwarder_app = r"https://" + client_ip + ":" + splunk_port + "/servicesNS/nobody/SplunkForwarder/configs/conf-inputs/" + url_encoded
        data = {'index':index_name}
        returned_resp = requests.post(forwarder_app, data=data, auth=(splunk_username, splunk_password), verify=False)

    if returned_resp.status_code != 200:
        raise Exception("Failed to change index because of status code " + str(returned_resp.status_code))

def configured_forwarders():
    try:
        fp = open("../local/forwarder_details.conf","r")
        content = fp.read()
        content_list = content.split('\n')
        comm_client = {}
        i = 0
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

def get_splunk_info(commserve, client):
    try:
        fp = open("../local/forwarder_details.conf","r")
        content = fp.read()
        content_list = content.split('\n')
        comm_client = {}
        i = 0
        while(i < len(content_list)-1):
            webserver = content_list[i].strip("]")
            webserver = webserver.split("[")[1].strip("\n")
            client_name = content_list[i+1].split(":")[1].strip("\n")
            if commserve == webserver and client_name == client:
                splunk_username = content_list[i+4].split(":")[1].strip("\n")
                password = content_list[i+5].split(":")[1].strip("\n")
                splunk_password = encode_decode.decode_string(password)
                splunk_port = content_list[i+6].split(":")[1].strip("\n")
                return splunk_username, splunk_password, splunk_port
            i = i + 7

        return "","",""

    except Exception as excp:
        return "","",""

def get_splunk_type(commserve, client):
    try:
        fp = open("../local/forwarder_details.conf","r")
        content = fp.read()
        content_list = content.split('\n')
        comm_client = {}
        i = 0
        while(i < len(content_list)-1):
            webserver = content_list[i].strip("]")
            webserver = webserver.split("[")[1].strip("\n")
            client_name = content_list[i+1].split(":")[1].strip("\n")
            if commserve == webserver and client_name == client:
                splunk_type = content_list[i+3].split(":")[1].strip("\n")
                return splunk_type
            i = i + 7
    except Exception as excp:
        return ""

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

def change_index():
    comm_to_client = helper.get_configured_clients()
    for i in comm_to_client:
        for j in comm_to_client[i]:
            splunk_username, splunk_password, splunk_port = get_splunk_info(i, j)
            if splunk_username != "":
                client_ip = get_ip_from_file(j,i)
                log_dir = get_log_directory(i,j)
                splunk_type = get_splunk_type(i,j)
                change_index_api(client_ip, log_dir, splunk_username, splunk_password, splunk_port, splunk_type)
                installation_helper.restart_splunk(client_ip, username=splunk_username, password=splunk_password, port=splunk_port)

def forwarder_info(commserve, client_name):
    fp = open('../local/forwarder_details.conf','r')
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
        i = i + 7

def get_updated_info():
    try:
        fp = open("../local/commindex.conf","r")
        contents = fp.read()
        content_list = contents.split('\n')
        index_name = content_list[0]
        fp.close()
    except Exception as excp:
        index_name = ""

    return index_name

try:
    SL.make_entry("run_monitor_script", "*************Started executing run monitor script because of index selection in GUI************")
    index_name = sys.argv[1]
    results, dr, settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']

    old_index_name = get_updated_info()

    if index_name != "None":
        fp_index = open("../local/commindex.conf", "w")
        fp_index.write(index_name + "\n")
        fp_index.close()

    index_name = get_updated_info()

    json_list = []
    SL.make_entry("run_monitor_script","Getting configured forwarders")
    forwarder_comm_client = configured_forwarders()
    SL.make_entry("run_monitor_script","Getting staged clients")
    comm_to_client = read_new_client_file()
    for commserve in comm_to_client:
        username, password, commserve_url = helper.get_credentials(commserve, session_key)
        ip = commserve
        if ip in forwarder_comm_client:
            forwarder_client_list = forwarder_comm_client[ip]
        else:
            forwarder_client_list = []
        for client in comm_to_client[commserve]:
            try:
                if client in forwarder_client_list:
                    temp = {}
                    temp['ClientName'] = client
                    auth_code = helper.get_authcode(username, password, commserve_url)
                    os_info, client_id = client_prop(auth_code, client)
                    log_dir = get_log_directory(commserve, client)
                    temp['LogDir'] = log_dir
                    temp["State"] = "Success"
                    temp['Commserve'] = commserve
                    client_ip = helper.get_ip(auth_code, client_id, commserve_url)
                    splunk_username, splunk_password, splunk_port = get_splunk_info(commserve, client)
                    ip,type = forwarder_info(commserve, client)
                    SL.make_entry("run_monitor_script","Sending monitoring request for client " + client + " with index " + index_name)
                    monitor_file(client_ip, index_name, log_dir, splunk_username, splunk_password, splunk_port, client, client_id, os_info, type, commserve, commserve_url, session_key)
                    installation_helper.restart_splunk(client_ip, username=splunk_username, password=splunk_password, port=splunk_port)
                    helper.splunk_service_check(client_ip,splunk_port,splunk_username,splunk_password)
                    SL.make_entry("run_monitor_script","Removing client from staged files")
                    remove_from_new_client([client],commserve)
                    json_list.append(temp)
            except Exception as excp:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                entry_content = str(exc_tb.tb_lineno) + ' ' + str(excp)
                SL.make_entry("run_monitor_script","ERROR Failed to monitor client " + entry_content)
                clean_operation.clean(client, commserve)
                helper.commit_failed_clients(client, commserve, 'Monitoring log files')
                continue

    if old_index_name != index_name:
        SL.make_entry("run_monitor_script","Starting to change index")
        change_index()
        SL.make_entry("run_monitor_script","Change index successful")

    SL.make_entry("run_monitor_script","run_monitor_script execution completed")
    splunk.Intersplunk.outputResults(json_list)

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("run_monitor_script",entry_content)
