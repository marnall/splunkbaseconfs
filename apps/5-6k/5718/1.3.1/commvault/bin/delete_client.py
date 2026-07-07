
import sys
import urllib
import splunklib.client as splunk_client
import splunk.Intersplunk
import requests
import encode_decode
import splunklogger as SL

res,d1,d2 = splunk.Intersplunk.getOrganizedResults()
arg1 = sys.argv[1]
commserve_ip = arg1

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
            SL.make_entry("delete_client", "Unmonitor operation failed. inputs.conf might be corrupted or end point is not reachable. Error: " + str(returned_resp.text))
            return
    except Exception as excp:
        SL.make_entry("delete_client", "ERROR: Unmoinitor request failed")
        return

    SL.make_entry("delete_client","Restarting splunk instance on client " + client_name)
    restart_splunk(client_ip, username, password, mgm_port)

def client_prop(auth_code,client_name):
    url = "http://" + ip + ":81/SearchSvc/CVWebService.svc/Client/byName(clientName=\'" + client_name + "\')"
    payload = {}
    headers = {"Accept": "application/json","Authtoken": auth_code}
    response = requests.request("GET", url, headers=headers, data = payload)
    json_obj = convert_to_json(response)
    osinfo = json_obj["clientProperties"][0]["client"]["osInfo"]["Type"]
    client_id = json_obj["clientProperties"][0]["client"]["clientEntity"]["clientId"]
    return osinfo, client_id

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

# def remove_from_forward(commserve_ip, client_name):
#     fp = open("../local/forwarder_details.conf","r")
#     contents = fp.read()
#     content_list = contents.split('\n')
#     fp.close()
#
#     i = 0
#     with open("../local/forwarder_details.conf","w") as fp:
#         while(i < len(content_list)-1):
#             webserver = content_list[i].split("]")[0]
#             webserver = webserver.split("[")[1]
#             client_name_req = content_list[i+1].split(":")[1]
#             if webserver == commserve_ip and client_name_req == client_name:
#                 i = i + 7
#             else:
#                 for j in range(0,7):
#                     fp.write(content_list[i+j] + '\n')
#                 i = i + 7

def check_if_file_exists(filename):
    try:
        fp = open("../local/"+filename,"r")
        fp.close()
        return True
    except Exception as excp:
        return False

def delete_entry_from_forwarder_details(client_list, commserve):
    fp = open("../local/forwarder_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    fp.close()

    i = 0
    with open("../local/forwarder_details.conf","w") as fp:
        while(i < len(content_list)-1):
            webserver = content_list[i].split("]")[0]
            webserver = webserver.split("[")[1]
            client_name = content_list[i+1].split(":")[1]
            if webserver == commserve and client_name in client_list:
                i = i + 7
            else:
                for j in range(0,7):
                    fp.write(content_list[i+j] + '\n')
                i = i + 7

def delete_entry_from_software_status(client_list, commserve):
    fp = open("../local/software_status.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    fp.close()

    if(len(content_list) != 0):
        i = 0
        with open("../local/software_status.conf","w") as fp:
            while(i < len(content_list)-1):
                webserver = content_list[i].split("]")[0]
                webserver = webserver.split("[")[1]
                client_name = content_list[i+1].split(":")[1]
                if webserver == commserve and client_name in client_list:
                    i = i + 3
                else:
                    fp.write(content_list[i] + '\n')
                    fp.write(content_list[i+1] + '\n')
                    fp.write(content_list[i+2] + '\n')
                    i = i + 3

def delete_entry_from_forwarder(client_list, commserve):
    fp = open("../local/forwarder.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    fp.close()

    i = 0
    with open("../local/software_status.conf","w") as fp:
        while(i < len(content_list)-1):
            webserver = content_list[i].split("]")[0]
            webserver = webserver.split("[")[1]
            client_name = content_list[i+1].split(":")[1]
            if webserver == commserve and client_name in client_list:
                i = i + 4
            else:
                for j in range(0,4):
                    fp.write(content_list[i+j] + '\n')
                i = i + 4
try:

    SL.make_entry("delete_client","************Started Executing Delete Operation************")
    client_list = []

    commserve = sys.argv[1]

    SL.make_entry("delete_client","Reading Staged Clients")
    new_commserve_client = read_new_client_file()

    if commserve in new_commserve_client:
        new_commserve_client_list = new_commserve_client[commserve]
    else:
        new_commserve_client_list = []

    for i in res:
        client_list.append(i['client'])

    #populating ends here

    req_client_list = client_list
    client_ip_dict = {}
    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    n = len(content_list)
    i = 0
    json_list = []
    while(i < n-1):
        if commserve_ip in content_list[i]:
            client_name = content_list[i+1].split(":")[1].strip("\r")
            if client_name in req_client_list and client_name not in new_commserve_client_list:
                client_ip = content_list[i+5].split(":")[1].strip("\r")
                log_dir = content_list[i+7].split(":",1)[1].strip("\r")
                SL.make_entry("delete_client", "Starting unmonitor operation for " + client_name)
                unmonitor_client(client_name, client_ip, log_dir, commserve_ip)
                SL.make_entry("delete_client", "Unmonitor operation Successfull")
        i = i + 9

    SL.make_entry("delete_client","cleaning client entry in conf files")
    with open("../local/client.conf","r") as fp:
        lines = fp.readlines()

    i = 0
    with open("../local/client.conf","w") as fp:
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

    if check_if_file_exists("forwarder_details.conf"):
        delete_entry_from_forwarder_details(client_list, commserve)

    if check_if_file_exists("software_status.conf"):
        delete_entry_from_software_status(client_list, commserve)

    if check_if_file_exists("forwarder.conf"):
        delete_entry_from_forwarder(client_list, commserve)

    SL.make_entry("delete_client","delete_client operation finished")

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_str = "ERROR " + str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("delete_client",entry_str)
