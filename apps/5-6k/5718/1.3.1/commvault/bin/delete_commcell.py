import splunk.Intersplunk
import helper
import splunklogger as SL
import sys
import urllib
import splunklib.client as splunk_client
import requests
import encode_decode

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

def restart_splunk(ip, username, password, mgm_port):

    service = splunk_client.connect(host=ip,port=mgm_port,username=username,password=password)
    service.restart()

def get_forwarder_info(client_name, commserve_ip):
    fp = open("../local/forwarder_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    i = 0
    while(i < len(content_list)-1):
        req_client_name = content_list[i+1].split(":")[1]
        if commserve_ip in content_list[i] and req_client_name == client_name:
            type = content_list[i + 3].split(":")[1]
            username = content_list[i + 4].split(":")[1]
            password = content_list[i + 5].split(":")[1]
            decry_pass = encode_decode.decode_string(password)
            mgm_port = content_list[i + 6].split(":")[1]
            return username, decry_pass, mgm_port, type
        i = i + 7

def unmonitor_client(client_name, client_ip, log_dir, commserve_ip):
    username, password, mgm_port, type = get_forwarder_info(client_name, commserve_ip)
    monitor_endpoint = r"monitor://" + log_dir
    try:
        url_encoded = urllib.quote(monitor_endpoint, safe="")
    except Exception as excp:
        url_encoded = urllib.parse.quote(monitor_endpoint, safe="")

    if "forwarder" in type.lower():
        forwarder_app = r"https://" + client_ip + ":" + mgm_port + "/servicesNS/nobody/SplunkUniversalForwarder/configs/conf-inputs/" + url_encoded
    else:
        forwarder_app = r"https://" + client_ip + ":" + mgm_port + "/servicesNS/nobody/SplunkForwarder/configs/conf-inputs/" + url_encoded

    try:
        returned_resp = requests.delete(forwarder_app, data={}, auth=(username, password), verify=False)
        if returned_resp.status_code != 200:
            SL.make_entry("delete_commcell", "Unmonitor operation failed. inputs.conf might be corrupted or end point is not reachable. Error: " + str(returned_resp.text))
            return
    except Exception as excp:
        SL.make_entry("delete_commcell", "ERROR: Unmoinitor request failed")
        return

    SL.make_entry("delete_commcell","Restarting splunk instance on client " + client_name)
    restart_splunk(client_ip, username, password, mgm_port)

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

def check_if_file_exists(filename):
    try:
        fp = open("../local/"+filename,"r")
        fp.close()
        return True
    except Exception as excp:
        return False


try:
    fp = open("../local/commcell.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    processed_commcell = []
    output_list = []

    commcell_name = ""

    for i in range(0,len(content_list)-1,4):
        commcell_name = content_list[i+1].split("=",1)[1].strip()

    if commcell_name == "":
        SL.make_entry("delete_commcell", "Failed to get commcell name")
        exit(0)

    fp.close()
    res,d1,settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']

    SL.make_entry("delete_commcell", "Getting monitored clients")
    config_clients = helper.get_configured_clients()

    fp = open("../local/commcell.conf","w")
    fp.close()

    if commcell_name in config_clients:
        req_client_list = config_clients[commcell_name]
    else:
        SL.make_entry("delete_commcell", "No clients to delete")
        exit(0)

    if(len(req_client_list) == 0):
        SL.make_entry("delete_commcell", "No clients to delete")
        exit(0)

    SL.make_entry("delete_client","Reading Staged Clients")
    new_commserve_client = read_new_client_file()

    if commcell_name in new_commserve_client:
        new_commserve_client_list = new_commserve_client[commcell_name]
    else:
        new_commserve_client_list = []

    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    fp.close()
    content_list = contents.split("\n")
    n = len(content_list)
    i = 0
    json_list = []
    while(i < n-1):
        if commcell_name in content_list[i]:
            client_name = content_list[i+1].split(":")[1].strip("\r")
            if client_name in req_client_list and client_name not in new_commserve_client_list:
                client_ip = content_list[i+5].split(":")[1].strip("\r")
                log_dir = content_list[i+7].split(":",1)[1].strip("\r")
                SL.make_entry("delete_client", "Starting unmonitor operation for " + client_name)
                unmonitor_client(client_name, client_ip, log_dir, commcell_name)
                SL.make_entry("delete_client", "Unmonitor operation Successfull")
        i = i + 9

    SL.make_entry("delete_commcell", "cleaning client entry in conf files")
    fp = open("../local/client.conf","w")
    fp.close()
    fp = open("../local/new_client.conf","w")
    fp.close()
    fp = open("../local/client_details.conf","w")
    fp.close()

    if check_if_file_exists("forwarder_details.conf"):
        fp = open("../local/forwarder_details.conf","w")
        fp.close()

    if check_if_file_exists("software_status.conf"):
        fp = open("../local/software_status.conf","w")
        fp.close()

    if check_if_file_exists("forwarder.conf"):
        fp = open("../local/forwarder.conf","w")
        fp.close()

    SL.make_entry("delete_commcell","delete_client operation finished")

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_str = "ERROR " + str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("delete_commcell",entry_str)
