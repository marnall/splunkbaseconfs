import requests
import xmltodict
import json
import base64
import os
import http
import sys
import encode_decode
import splunk.Intersplunk
from xml.dom import minidom
import splunklib.client as splunk_client
import datetime
import time
import helper
import splunklogger as SL

def convert_to_json(xml_resp):
    resp = xml_resp.text.encode('utf-8')
    json_obj = resp.decode('utf-8').replace("'",'"')
    req_json = json.loads(json_obj)
    return req_json

#Pass password and username of the comm server(Get it from UI)
def get_authcode(username,password,url):

    url = url + "/SearchSvc/CVWebService.svc/Login"
    password_base64 = base64.b64encode(password.encode()).decode("utf-8")
    data = {"password":password_base64,"username":username}
    json_obj = json.dumps(data)
    headers = {"Accept": "application/json","Content-Type": "application/json"}
    response = requests.request("POST", url, headers=headers, data = json_obj)

    if response.status_code == 200:
        json_resp = convert_to_json(response)
        auth_code = json_resp["token"]
        return auth_code

    raise Exception("Failed to get auth token. Check if Commvault Services are running")


def get_clients(auth_code,url):
    url = url + "/SearchSvc/CVWebService.svc/Client"
    payload  = {}
    headers = {"Accept": "application/json","Authtoken": auth_code}
    response = requests.request("GET", url, headers=headers, data = payload)
    if response.status_code == 200:
        return response
    raise Exception("Failed to get clients. Check if Commvault Services are running")

def client_prop(auth_code,id,url):
    url = url + "/SearchSvc/CVWebService.svc/Client/"+str(id)
    payload = {}
    headers = {"Accept": "application/json","Authtoken": auth_code}
    response = requests.request("GET", url, headers=headers, data = payload)
    if response.status_code == 200:
        json_obj = convert_to_json(response)
        return json_obj
    raise Exception("Failed to get client properties. Check if Commvault Services are running")

def client_prop_byname(auth_code, client_name, url):
    url = url + "/SearchSvc/CVWebService.svc/Client/byName(clientName='%s')"
    url = url % client_name
    payload = {}
    headers = {"Accept": "application/json","Authtoken": auth_code}
    response = requests.request("GET", url, headers=headers, data = payload)
    if response.status_code == 200:
        json_obj = convert_to_json(response)
        return json_obj
    raise Exception("Failed to get client properties. Check if Commvault Services are running")

def get_sla_report(auth_code, url):
    try:
        url_frag = url.split(":")
        url_withoutport = url_frag[0] + ":" + url_frag[1]
        req_url =  url_withoutport + "/CustomReportsEngine/rest/reportsplusengine/reports/name:SLA"
        payload = {}
        json_obj = json.dumps(payload)

        headers = {"Accept": "application/json","Authtoken": auth_code, "Content-Type": "application/json"}
        response = requests.request("GET", req_url, headers=headers, data = json_obj)

        if(response.status_code != 200):
            return -1

        json_data = json.loads(response.text)

        dataset_list = json_data["pages"][0]["dataSets"]["dataSet"]
        dataset_id = -1
        for i in dataset_list:
            if(i["dataSet"]["dataSetName"] == "PieChart"):
                dataset_id = i["dataSet"]["dataSetId"]
                break

        if(dataset_id == -1):
            return -1

        url = url_withoutport + "/CustomReportsEngine/rest/reportsplusengine/datasets/" + str(dataset_id) + "/data"
        response = requests.request("GET", url, headers=headers, data = json_obj)

        if(response.status_code != 200):
            return -1

        json_data = json.loads(response.text)
        met_sla = json_data["records"][0][5]
        return met_sla

    except Exception as excp:
        return -1

def get_os_info(auth_code,id,url):
    response = client_prop(auth_code,id,url)
    return response["clientProperties"][0]["client"]["osInfo"]["Type"]

def get_credentials(ip, session_key):
    fp = open("../local/commcell.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    for i in range(0,len(content_list)-1,4):
        commcell_name = content_list[i+1].split("=",1)[1].strip()
        if(ip == commcell_name):
            username = content_list[i+2].split("=",1)[1].strip()
            encoded_username = username.replace("\\", "\\\\")
            headers = {'Authorization': ('Splunk %s' %session_key)}
            resp = requests.request("GET", 'https://127.0.0.1:8089/servicesNS/nobody/search/storage/passwords/'+encoded_username, headers=headers, verify=False)
            if(resp.status_code != 200):
                return "","",""
            keys = minidom.parseString(resp.text).getElementsByTagName('s:key')
            password = ""
            for k in keys:
                if k.hasAttribute('name') and k.getAttribute('name') == 'clear_password':
                    password = k.firstChild.nodeValue
                    break
            url = content_list[i].split("[")[1].split("]")[0]
            return username,password,url

def get_configured_clients(commcell=None):

    try:
        fp = open("../local/client.conf","r")
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

        # if(commcell != None):
        #     if(commcell != websever):
        #         continue

        if webserver not in commserver_client:
            commserver_client[webserver] = []
        i = i + 1
        while(i < len(content_list) and content_list[i] != "[end]"):
            commserver_client[webserver].append(content_list[i])
            i = i + 1
        i = i + 1
    return commserver_client

def get_ip(auth_code,client_id,url):
    url = url + "/SearchSvc/CVWebService.svc/CommServ/DataInterfacePairs/HostInterfaces?hostId=" + str(client_id)
    payload = {}
    headers = {"Accept": "application/json","Authtoken": auth_code}
    response = requests.request("GET", url, headers=headers, data = payload)
    if response.status_code == 200:
        json_obj = convert_to_json(response)
        client_ip = json_obj["interfaces"][0]
        return client_ip
    raise Exception("Failed to get ip of the client. Check if Commvault Services are running")


def check_software_available(os_type):
    try:
        fp = open("../local/software.conf","r")
    except Exception as excp:
        return False, ""

    if "windows" in os_type.lower():
        os_type_req = "Windows"
    else:
        os_type_req = "Unix"

    content = fp.read()
    content_list = content.split('\n')
    i = 0
    while(i < len(content_list)-1):
        if os_type_req in content_list[i]:
            return True, content_list[i+1]
        i = i + 2

    return False,""

def splunk_service_check(ip, port, username, password):
    start_time = time.time()
    service_flag = False
    total_time = 0
    while(not service_flag and total_time <= 15):
        try:
            service = splunk_client.connect(host=ip,port=port,username=username,password=password)
            service_flag = True
        except Exception as excp:
            total_time = time.time() - start_time
            total_time = int(total_time / 60)
            continue

    if service_flag:
        return

    raise Exception("Not able to detect the splunk service on the client machine")

def commit_failed_clients(client_name, commserve, state):
    fp = open("../local/failedclients.conf","a")
    date_time = datetime.datetime.now()
    fp.write(str(date_time) + " " + commserve + " " + client_name + " " + state + '\n')
    fp.close()

def get_buffered_clients():
    try:
        fp = open("../local/clientbuffer.conf","r")
        contents = fp.read()
        content_list = contents.split("\n")
        return content_list
    except Exception as excp:
        return []
