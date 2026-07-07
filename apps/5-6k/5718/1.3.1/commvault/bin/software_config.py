#Code for setting path of forwarder software
# | softwareconfig $path$ $ostype$

import sys
import os
import json
import helper
import base64
import time
import requests
import splunklib.client as splunk_client
import splunk.Intersplunk
import encode_decode
import splunklogger as SL
import clean_operation
import installation_helper

def get_path(software_path):
    path_list = software_path.split('%20')
    new_path = ""
    for i in range(len(path_list)-1):
        new_path = new_path + path_list[i] + " "
    new_path = new_path + path_list[len(path_list)-1]
    return new_path

def os_exists(os_type):
    fp = open('../local/software.conf','r')
    content = fp.read()
    content_list = content.split('\n')
    for i in content_list:
        if os_type in i:
            return True
    return False

def file_exists():
    try:
        fp = open('../local/software.conf','r')
        fp.close()
        return True
    except Exception as excp:
        return False

def write_to_file(software_path, os_type):
    req_path = get_path(software_path)
    if not file_exists():
        fp = open('../local/software.conf','a')
        fp.write("[" + os_type + "]\n")
        fp.write(req_path + '\n')
        fp.close()
        return

    if(os_exists(os_type)):
        with open("../local/software.conf","r") as fp:
            lines = fp.readlines()

        i = 0
        with open("../local/software.conf","w") as fp:
            while(i < len(lines)):
                os_type_file = lines[i]
                if os_type in os_type_file:
                    fp.write(lines[i])
                    fp.write(req_path + '\n')
                    i = i + 2
                else:
                    fp.write(lines[i])
                    i = i + 1
    else:
        fp = open('../local/software.conf','a')
        fp.write('[' + os_type + ']\n')
        fp.write(req_path + '\n')
        fp.close()

def get_pending_clients(os_type):
    try:
        fp = open("../local/software_status.conf",'r')
        content = fp.read()
        content_list = content.split('\n')
        i = 0
        comm_to_client = {}
        while(i < len(content_list)-1):
            if os_type.lower() in content_list[i+2].lower():
                webserver = content_list[i].strip("]")
                webserver = webserver.split("[")[1]
                if webserver not in comm_to_client:
                    comm_to_client[webserver] = []
                client_name = content_list[i+1].split(":")[1]
                comm_to_client[webserver].append(client_name)
            i = i + 3
        return comm_to_client

    except Exception as excp:
        return {}

def get_client_id(commserve_url, auth_code, client_name):
    resp = helper.get_clients(auth_code,commserve_url)
    json_resp = helper.convert_to_json(resp)
    client_properties = json_resp["clientProperties"]
    for i in client_properties:
        req_client_name = i["client"]["clientEntity"]["clientName"]
        if client_name == req_client_name:
            client_id = i["client"]["clientEntity"]["clientId"]
            return str(client_id)

def delete_from_software_status(commserve, client):
    with open("../local/software_status.conf",'r') as fp:
        lines = fp.readlines()

    i = 0;
    with open("../local/software_status.conf","w") as fp:
        while i < len(lines):
            webserver = lines[i].split("]")[0]
            webserver = webserver.split("[")[1]
            client_name = lines[i+1].split(":")[1].strip('\n')
            if commserve.lower() == webserver.lower() and client.lower() == client_name.lower():
                i = i + 3
            else:
                fp.write(lines[i])
                fp.write(lines[i+1])
                fp.write(lines[i+2])
                i = i + 3

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

def add_forwarder_details(commserve,client_name):
    encry_pass = encode_decode.encode_string("commvaultadmin")
    client_ip = get_ip_from_file(client_name, commserve)
    fp = open("../local/forwarder_details.conf","a")
    commserver_content = "[" + commserve + "]\n"
    client_name_content = "clientname:" + client_name + '\n'
    client_ip_content = "clientip:" + client_ip + '\n'
    client_type_content = "type:" + "SplunkForwarder" + '\n'
    splunk_username_content = "splunkusername:" + "admin" + '\n'
    splunk_password_content = "splunkpassword:" + encry_pass + '\n'
    splunk_port_content = "splunkport:" + "8089" + '\n'
    fp.write(commserver_content + client_name_content + client_ip_content + client_type_content + splunk_username_content + splunk_password_content + splunk_port_content)
    fp.close()

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
    except Exception as excp:
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


def install_software(os_type, software_path, indexer_ip_port, session_key):
    file_path = get_path(software_path)
    SL.make_entry("software_config","Getting staged clients with OS type as " + os_type)
    comm_client = get_pending_clients(os_type)
    if "windows" in os_type.lower():
        for i in comm_client:
            for client in comm_client[i]:
                try:
                    username,password,commserve_url = helper.get_credentials(i, session_key)
                    auth_code = helper.get_authcode(username,password,commserve_url)
                    client_id = get_client_id(commserve_url, auth_code, client)
                    try:
                        installation_helper.install_software(os_type, client_id, client, software_path, indexer_ip_port, commserve_url, auth_code)
                    except Exception as excp:
                        SL.make_entry("software_config","ERROR while installing software for client " + client)
                        clean_operation.clean(client, i)
                        helper.commit_failed_clients(client, i, 'Software install')
                        continue
                    delete_from_software_status(i,client)
                    add_forwarder_details(i,client)
                    if check_index_conf():
                        index_name = get_index()
                        client_ip = get_ip_from_file(client,i)
                        log_dir = get_log_directory(i,client)
                        SL.make_entry("software_config","Sending monitoring request")
                        try:
                            installation_helper.monitor_file(client_ip, index_name, log_dir)
                        except Exception as excp:
                            SL.make_entry("software_config","Failed to monitor client " + client)
                            clean_operation.clean(client, i)
                            helper.commit_failed_clients(client, i, 'Monitoring log files')
                            continue

                        installation_helper.restart_splunk(client_ip)
                        remove_from_new_client(client,i)
                except Exception as excp:
                    SL.make_entry("software_config","Operation Failed for client " + client)
                    clean_operation.clean(client, i)
                    helper.commit_failed_clients(i['client'], commserve, 'Service error')
                    continue
    else:
        for i in comm_client:
            for client in comm_client[i]:
                try:
                    username,password,commserve_url = helper.get_credentials(i, session_key)
                    auth_code = helper.get_authcode(username,password,commserve_url)
                    client_id = get_client_id(commserve_url, auth_code, client)
                    try:
                        installation_helper.install_software(os_type, client_id, client, software_path, indexer_ip_port, commserve_url, auth_code)
                    except Exception as excp:
                        SL.make_entry("software_config","ERROR while installing software for client " + client)
                        clean_operation.clean(client, i)
                        helper.commit_failed_clients(client, i, 'Install software')
                        continue
                    delete_from_software_status(i,client)
                    add_forwarder_details(i,client)
                    if check_index_conf():
                        index_name = get_index()
                        client_ip = get_ip_from_file(client,i)
                        log_dir = get_log_directory(i,client)
                        SL.make_entry("software_config","Sending Monitoring request")
                        try:
                            installation_helper.monitor_file(client_ip, index_name, log_dir)
                        except Exception as excp:
                            SL.make_entry("software_config","Failed to monitor file on client " + client)
                            clean_operation.clean(client,i)
                            helper.commit_failed_clients(client, i, 'Monitor log files')
                            continue

                        installation_helper.restart_splunk(client_ip)
                        remove_from_new_client(client,i)
                except Exception as excp:
                    SL.make_entry("software_config","Operation failed for client " + client)
                    clean_operation.clean(client, i)
                    helper.commit_failed_clients(client, i, 'Service error')
                    continue

def get_updated_info():
    try:
        fp = open("../local/indexerip.conf","r")
        contents = fp.read()
        content_list = contents.split('\n')
        ip_port = content_list[0]
        fp.close()
        return ip_port
    except Exception as excp:
        return ""

try:

    SL.make_entry("software_config","***********Started executing software update operation**********")

    idx_name = get_index()
    if(idx_name == ""):
        SL.make_entry("software_config", "index not configured skipping forwarder configuration")
        exit(0)
        
    indexer_ip = sys.argv[1]
    receiving_port = sys.argv[2]

    old_ip_port = get_updated_info()

    if(old_ip_port != ""):
        old_ip = old_ip_port.split(":")[0]
        old_port = old_ip_port.split(":")[1]
        indexer_info = old_ip + ":" + old_port

    if(old_ip_port == "" and indexer_ip == "None" and receiving_port == "None"):
        SL.make_entry("software_config", "Indexer IP and port not configured, exiting the process")
        exit(0)

    if(indexer_ip != "None" and receiving_port != "None"):
        indexer_info = indexer_ip + ":" + receiving_port
        fp_indexer = open("../local/indexerip.conf","w")
        fp_indexer.write(indexer_info + '\n')
        fp_indexer.close()
    elif(indexer_ip != "None"):
        indexer_info = indexer_ip + ":" + old_port
        fp_indexer = open("../local/indexerip.conf","w")
        fp_indexer.write(indexer_info + '\n')
        fp_indexer.close()
    elif(receiving_port != "None"):
        indexer_info = old_ip + ":" + receiving_port
        fp_indexer = open("../local/indexerip.conf","w")
        fp_indexer.write(indexer_info + '\n')
        fp_indexer.close()
    else:
        SL.make_entry("software_config", "No changes in indexer ip and port")

    res,d1,setting = splunk.Intersplunk.getOrganizedResults()
    session_key = setting['sessionKey']

    for i in res:
        os_list = i['ostype'].split(',')
        path_list = i['path'].split(',')
    for i in range(len(os_list)):
        software_path = path_list[i]
        os_type = os_list[i]
        if software_path != " ":
            SL.make_entry("software_config","Saving acquired information")
            write_to_file(software_path, os_type)
            SL.make_entry("software_config","Installing software on staged clients")
            install_software(os_type, software_path, indexer_info, session_key)

    SL.make_entry("software_config","Finished executing software config")
except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("software_config","ERROR " + entry_content)
