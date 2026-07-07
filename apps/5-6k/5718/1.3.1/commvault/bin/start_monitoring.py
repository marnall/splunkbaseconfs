#this file is used when user selects clients to monitor the log files from the GUI

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
import installation_helper
import log_dir_helper

def client_exists(client_name):

    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    """
    for i in range(len(content_list)):
        if client_name in content_list[i] and ip in content_list[i-1]:
            return True
    return False
    """
    i = 0
    while(i < len(content_list)-1):
        if commserve in content_list[i]:
            existing_client = content_list[i+1].split(':')[1].strip()
            if existing_client == client_name:
                return True
        i = i + 9
    return False

def check_index_conf():
    try:
        fp = open("../local/commindex.conf","r")
        return True
    except Exception as excp:
        return False

def get_index():
    fp = open("../local/commindex.conf","r")
    content = fp.read()
    content_list = content.split("\n")
    return content_list[0]

def write_to_forwarder_details(commserve,client_name,client_ip):
    encry_pass = encode_decode.encode_string("commvaultadmin")
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


def get_indexer_info():
    try:
        fp = open("../local/indexerip.conf","r")
        contents = fp.read()
        content_list = contents.split('\n')
        return content_list[0]
    except Exception as excp:
        return ""

try:
    SL.make_entry("start_monitoring", "**********Started monitioring operation in start_monitoring script**************")
    fp = open("../local/client.conf","a")
    fp_details = open("../local/client_details.conf","a")
    fp_new_client = open("../local/new_client.conf","a")

    if(not check_index_conf()):
        index_flag = False
    else:
        index_flag = True

    res,d1,settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']
    commserve = sys.argv[1]
    username,password,url = helper.get_credentials(commserve, session_key)
    auth_code = helper.get_authcode(username, password, url)

    client_conf_status = {}
    SL.make_entry("start_monitoring","started to write to client.conf and new_client.conf")
    failed_clients = []
    deconfig_clients = []
    client_list = []
    commserve_content = "[" + commserve + "]\n"
    first_line_flag = True
    first_line_flag_client = True

    buffered_clients = helper.get_buffered_clients()
    fp_buffer = open("../local/clientbuffer.conf","a")
    for i in res:
        if(i['client'] not in buffered_clients):
            fp_buffer.write(i['client']+"\n")
    fp_buffer.close()

    for i in res:
        if(i['client'] in buffered_clients):
            SL.make_entry("start_monitoring", "Client " + i['client'] + "already in processing")
            continue

        client_list.append(i['client'])
        SL.make_entry("start_monitoring","checking Splunk software status for client " + i['client'])
        try:
            client_prop = helper.client_prop_byname(auth_code, i['client'], url)
            is_deleted_client = client_prop["clientProperties"][0]["clientProps"]["IsDeletedClient"]
            if(is_deleted_client):
                SL.make_entry("start_monitoring", i['client'] + " is a de-configured client, skipping it for monitoring")
                deconfig_clients.append(i['client'])
                clean_operation.clean(i['client'], commserve)
                continue
            client_id = str(client_prop["clientProperties"][0]["client"]["clientEntity"]["clientId"])
            info_list = installation_helper.check_software_status(i['client'], commserve, client_id, auth_code, url)
        except Exception as excp:
            SL.make_entry("start_monitoring","ERROR Failed to check software status for client " + i['client'] + " Check client connectivity")
            failed_clients.append(i['client'])
            clean_operation.clean(i['client'], commserve)
            helper.commit_failed_clients(i['client'], commserve, 'Check software status')
            continue

        software_status = info_list[0]
        software_type = info_list[1]
        os_type = info_list[2]

        if not software_status:
            SL.make_entry("start_monitoring","Splunk Software Not initialized on the client " + i['client'])
            SL.make_entry("start_monitoring","Checking for Software on the local machine")
            status, path = helper.check_software_available(os_type)
            indexer_ip_port = get_indexer_info()
            if(status and indexer_ip_port != ""):
                SL.make_entry("start_monitoring","Software found and started remote installation on client machine")
                try:
                    installation_helper.install_software(os_type, client_id, i['client'], path, indexer_ip_port, url, auth_code)
                except Exception as excp:
                    SL.make_entry("start_monitoring","ERROR Software installation failed for client " + i['client'] + " Try to manually install forwarder and then select client to monitor")
                    failed_clients.append(i['client'])
                    clean_operation.clean(i['client'], commserve)
                    helper.commit_failed_clients(i['client'], commserve, "Install software")
                    continue

                SL.make_entry("start_monitoring","Software installation completed successfully")
                client_conf_status[i['client']] = True
                software_pre_installed = False
            else:
                SL.make_entry("start_monitoring","Software or indexer info not found, staging client for further processing")
                fp_software = open("../local/software_status.conf","a")
                fp_software.write("[" + commserve  + "]\n")
                fp_software.write("clientname:" + i['client'] + '\n')
                fp_software.write("ostype:" + os_type + '\n')
                fp_software.close()
                software_pre_installed = True
                client_conf_status[i['client']] = False
        else:
            SL.make_entry("start_monitoring","Splunk Software found on client machine, staging client for further processing")
            client_conf_status[i['client']] = False
            software_pre_installed = True

        if first_line_flag_client:
            fp.write(commserve_content)
            first_line_flag_client = False
        fp.write(i['client']+"\n")

        if(not index_flag or software_pre_installed):
            if first_line_flag:
                fp_new_client.write(commserve_content)
                first_line_flag = False
            fp_new_client.write(i['client']+"\n")

    end_content = "[" + "end" + "]\n"
    if not first_line_flag_client:
        fp.write(end_content)
    fp.close()

    if(not index_flag or not first_line_flag):
        fp_new_client.write(end_content)
    fp_new_client.close()

    SL.make_entry("start_monitoring","Started collecting addition information about clients")
    for client_name in client_list:
        try:
            if client_name not in failed_clients and client_name not in deconfig_clients:
                client_prop = helper.client_prop_byname(auth_code, client_name, url)
                display_name = client_prop["clientProperties"][0]["client"]["displayName"]
                client_id = client_prop["clientProperties"][0]["client"]["clientEntity"]["clientId"]
                host_name = client_prop["clientProperties"][0]["client"]["clientEntity"]["hostName"]
                client_ip = helper.get_ip(auth_code, client_id, url)
                os_type = client_prop["clientProperties"][0]["client"]["osInfo"]["Type"]
                install_dir = client_prop["clientProperties"][0]["client"]["installDirectory"]
                SL.make_entry("start_monitoring","Getting log directory of the client " + client_name)
                try:
                    commserve_hostname = url.split("//")[1].split(":")[0]
                    log_dir = log_dir_helper.get_log_directory(os_type, client_name, client_id, commserve_hostname, auth_code, install_dir)
                    if "exception" in log_dir.lower():
                        SL.make_entry("start_monitoring","Failed to get log directory of client " + client_name + " Error " + log_dir)
                        clean_operation.clean(client_name, commserve)
                        helper.commit_failed_clients(client_name, commserve, 'Get log dir')
                        continue
                except Exception as excp:
                    SL.make_entry("start_monitoring","Failed to get log directory of client " + str(excp))
                    clean_operation.clean(client_name, commserve)
                    helper.commit_failed_clients(client_name, commserve, 'Get log dir')
                    continue
                SL.make_entry("start_monitoring","Log Directory path detected " + log_dir)
                if client_conf_status[client_name]:
                    write_to_forwarder_details(commserve, client_name, client_ip)

                if index_flag and client_conf_status[client_name]:
                    index_name = get_index()
                    SL.make_entry("start_monitoring","Passing monitoring command to client with index " + index_name)
                    try:
                        installation_helper.monitor_file(client_ip, index_name, log_dir)
                    except Exception as excp:
                        SL.make_entry("start_monitoring","ERROR Failed to monitor client " + client_name)
                        clean_operation.clean(client_name, commserve)
                        helper.commit_failed_clients(client_name, commserve, 'Monitor log files')
                        continue
                    installation_helper.restart_splunk(client_ip)
                    SL.make_entry("start_monitoring","Monitoring Log Files Successfully for client " + client_name)

                if not client_exists(client_name):
                    writing_items = []
                    writing_items.append("[" + commserve + "]\n")
                    writing_items.append("clientname:" + client_name + "\n")
                    writing_items.append("commserver:" + commserve + "\n")
                    writing_items.append("displayname:" + display_name + "\n")
                    writing_items.append("hostname:" + host_name + "\n")
                    writing_items.append("clientip:" + client_ip + "\n")
                    writing_items.append("ostype:" + os_type + "\n")
                    writing_items.append("logdir:" + log_dir + "\n")
                    writing_items.append("[end]\n")
                    for i in writing_items:
                        fp_details.write(i)
        except Exception as excp:
            SL.make_entry("start_monitoring","ERROR Failed to get additional information about the client " + client_name)
            clean_operation.clean(client_name, commserve)
            helper.commit_failed_clients(client_name, commserve, 'Service error')
            continue

    fp = open("../local/clientbuffer.conf","w")
    fp.close()

    SL.make_entry("start_monitoring","start_monitoring finished execution")

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = "ERROR " + str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("start_monitoring", entry_content)
