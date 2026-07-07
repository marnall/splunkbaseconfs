import requests
import json
import base64
import sys
import splunk.Intersplunk
from xml.dom import minidom
import encode_decode
import helper
import splunklogger as SL

def write_to_file(webserver_url, username, password, commcell_name):
    results, dr, settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']

    headers = {'Authorization': ('Splunk %s' %session_key)}
    data = {'name':username, 'password':password}

    resp = requests.request("POST", 'https://127.0.0.1:8089/servicesNS/nobody/search/storage/passwords', headers=headers, data=data, verify=False)
    if(resp.status_code == 201):
        keys = minidom.parseString(resp.text).getElementsByTagName('s:key')
        enc_password = ""

        for k in keys:
            if k.hasAttribute('name') and k.getAttribute('name') == 'encr_password':
                enc_password = k.firstChild.nodeValue
                break

        if(enc_password == ""):
            return False

    elif(resp.status_code == 409):
        #if username already exists - update the password
        SL.make_entry("click_result", "Password pre exists for username: " + username + " .Overwriting it")
        data = {'password':password}
        encoded_username = username.replace("\\","\\\\")
        resp = requests.request("POST", 'https://127.0.0.1:8089/servicesNS/nobody/search/storage/passwords/'+encoded_username, headers=headers, data=data, verify=False)
        if(resp.status_code != 200):
            return False

        keys = minidom.parseString(resp.text).getElementsByTagName('s:key')
        enc_password = ""

        for k in keys:
            if k.hasAttribute('name') and k.getAttribute('name') == 'encr_password':
                enc_password = k.firstChild.nodeValue
                break

        if(enc_password == ""):
            return False
    else:
        return False

    fp = open("../local/commcell.conf","a")
    stanza_name = "[" + webserver_url + "]\n"
    commcell_entry = "commcellname = " + commcell_name + "\n"
    username_entry = "username = " + username + "\n"
    password_entry = "password = " + enc_password + "\n"
    fp.write(stanza_name)
    fp.write(commcell_entry)
    fp.write(username_entry)
    fp.write(password_entry)
    fp.close()
    return True

def login(username, password, webserver_url):
    try:
        password_base64 = base64.b64encode(password.encode()).decode("utf-8")
        url = webserver_url + "/SearchSvc/CVWebService.svc/Login"
        data = {"password":password_base64,"username":username}
        json_obj = json.dumps(data)
        headers = {"Accept": "application/json","Content-Type": "application/json"}
        response = requests.request("POST", url, headers=headers, json=data)
        json_resp = response.json()
        if response.status_code == 200 and "errList" in json_resp and len(json_resp["errList"]) == 0:
            return True, json_resp["token"]
        return False, ""
    except Exception as excp:
        return False, ""

def get_commcell(webserver_url, auth_code):
    url = webserver_url + "/SearchSvc/CVWebService.svc/commserv"
    headers = {"Accept": "application/json", "Authtoken":auth_code}
    response = requests.request("GET", url, headers=headers)
    if response.status_code == 200:
        json_resp = response.json()
        return json_resp['commcell']['commCellName']

    raise Exception("Error while getting commcell name")

try:

    webserver = sys.argv[1]
    username = sys.argv[2]
    try:
        password = sys.argv[3]
    except Exception as excp:
        SL.make_entry("click_result", "Password not entered. Please give a password")
        print("Result")
        print("Login failed: Password not entered")
        exit(0)

    if "http://" in webserver or "https://" in webserver:
        SL.make_entry("click_result","Attempting to login")
        login_status, auth_code = login(username, password, webserver)
        if(login_status):
            commcell_name = get_commcell(webserver, auth_code)
            if(not write_to_file(webserver, username, password, commcell_name)):
                SL.make_entry("click_result", "Failed to store the password. Check splunkd logs.")
                print("Result")
                print("Failed to store password.")
            else:
                SL.make_entry("click_result","Login Successful")
                print("Result")
                print("Commcell Addition Successful. Please Refresh The Page.")
        else:
            SL.make_entry("click_result","ERROR Login Failed")
            print("Result")
            print("Commcell Addition Failed. Please Try Again.")
    else:
        SL.make_entry("click_result","Invalid url")
        print("Result")
        print("Invalid URL. Please ensure URL starts with HTTP or HTTPs.")

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = "ERROR " + str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("click_result", entry_content)
    print("Result")
    print("Failed to login. Check logs")
