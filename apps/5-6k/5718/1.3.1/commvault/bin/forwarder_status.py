#File for displaying contents of Forwarder Configuration table

import sys
import os
import splunk.Intersplunk
import requests
import helper
import encode_decode
import splunklogger as SL
import clean_operation
import installation_helper


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

def get_os_from_file(req_client,ip):

    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    n = len(content_list)
    i = 0
    while(i < n-1):
        if ip in content_list[i]:
            client_name = content_list[i+1].split(":")[1].strip("\r")
            if client_name == req_client:
                client_os = content_list[i+6].split(":")[1].strip("\r")
                return client_os
        i = i + 9

def get_latest_info(client_name, commserve, session_key):
    os_type = get_os_from_file(client_name, commserve)
    username, password, commserve_url = helper.get_credentials(commserve, session_key)
    auth_code = helper.get_authcode(username, password, commserve_url)
    client_resp = helper.client_prop_byname(auth_code, client_name, commserve_url)
    client_id = str(client_resp['clientProperties'][0]['client']['clientEntity']['clientId'])
    status_info = installation_helper.check_software_status(client_name, commserve, client_id, auth_code, commserve_url)
    return status_info[0], status_info[1]

def write_to_file(client_name,client_ip,commserve,type):
    try:
        fp = open("../local/forwarder.conf","r")
        contents = fp.read()
        content_list = contents.split("\n")
        i = 0
        comm_client = {}
        while(i < len(content_list)-1):
            webserver = content_list[i].strip("]")
            webserver = webserver.split("[")[1]
            if webserver not in comm_client:
                comm_client[webserver] = []
            client_name_file = content_list[i+1].split(":")[1]
            if client_name_file not in comm_client:
                comm_client[webserver].append(client_name_file)
            i = i + 4
        fp.close()
    except Exception as excp:
        comm_client = {}

    if commserve not in comm_client or client_name not in comm_client[commserve]:

        fp = open("../local/forwarder.conf","a")
        ip_content = "[" + commserve + "]\n"
        client_name_content = "clientname:" + client_name + "\n"
        client_ip_content = "clientip:" + client_ip + "\n"
        type_content = "type:" + type + "\n"
        fp.write(ip_content + client_name_content + client_ip_content + type_content)
        fp.close()

def get_forwarder_info(ip,client_name):
    fp = open("../local/forwarder_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    i = 0
    while(i < len(content_list)-1):
        webserver = content_list[i].strip("]")
        webserver = webserver.split("[")[1]
        if(webserver == ip):
            client_name_file = content_list[i+1].split(":")[1]
            if client_name_file == client_name:
                info_dict = {
                'ip':content_list[i+2].split(":")[1],
                'type':content_list[i+3].split(":")[1],
                'splunk_username':content_list[i+4].split(":")[1],
                'splunk_port':content_list[i+6].split(":")[1]
                }
                return info_dict
        i = i + 7

try:

    SL.make_entry("forwarder_status","************Started executing forwarder status***********")
    ip = sys.argv[1]
    results, dr, settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']
    SL.make_entry("forwarder_status","Getting configured forwarders")
    config_forwarders = configured_forwarders()

    if ip in config_forwarders:
        config_clients = config_forwarders[ip]
    else:
        config_clients = []

    SL.make_entry("forwarder_status","Getting staged clients")
    commserver_client = read_new_client_file()
    if ip in commserver_client:
        client_list = commserver_client[ip]
    else:
        client_list = []

    json_list = []

    for i in client_list:
        temp = {}
        temp['ClientName'] = i
        client_ip = get_ip_from_file(i,ip)
        temp['IP'] = client_ip
        temp['Username'] = "Not Configured"
        temp['Password'] = "Not Configured"
        temp["ManagementPort"] = "Not Configured"
        if i not in config_clients:
            SL.make_entry("forwarder_status","Getting updated info about the client " + i)
            try:
                status,type = get_latest_info(i,ip,session_key)
            except Exception as excp:
                SL.make_entry("forwarder_status","Operation failed for client " + i)
                clean_operation.clean(i, ip)
                helper.commit_failed_clients(i, ip, 'Forwarder info')
                continue
            if(status):
                SL.make_entry("forwarder_status","Found software on client " + i)
                temp['SplunkSoftware'] = 'Installed'
                temp['Type'] = type
                write_to_file(i,client_ip,ip,type)
            else:
                temp['SplunkSoftware'] = 'Not Installed'
                temp['Type'] = '-'
            json_list.append(temp)

    for i in config_clients:
        info_dict = get_forwarder_info(ip,i)
        temp = {}
        temp['ClientName'] = i
        temp['IP'] = info_dict['ip']
        temp['SplunkSoftware'] = 'Installed'
        temp['Type'] = info_dict['type']
        temp['Username'] = info_dict['splunk_username']
        temp['Password'] = "Configured"
        temp["ManagementPort"] = info_dict['splunk_port']
        json_list.append(temp)

    SL.make_entry("forwarder_status","Finished executing forwarder status")
    splunk.Intersplunk.outputResults(json_list)

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("forwarder_status","ERROR " + entry_content)
