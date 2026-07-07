import requests
# from requests.auth import HTTPBasicAuth
import os
import urllib3
# import splunklib.client as client
import json


# def servers(token):
#     serverPort = '62038'
    
#     host = "localhost"
#     user = 'admin'
#     password = 'password'
    
#     url = "https://{}:{}/servicesNS/-/splunkupgrader/run-backup?output_mode=json".format(host, serverPort)
#     text = "install"
#     storedUser = user
#     clearPass = password
#     isLocal = "False"
#     curServer = "idx1"
#     mgmt_port = 8089
    
#     data = 'message={}'.format(text)
#     headers = {
#     'Content-Type': 'application/x-www-form-urlencoded',
#     'Authorization': 'Bearer {}'.format(token)
  
#     }
#     response = requests.request("POST", url, headers=headers, data=data, verify=False) 
    
def get_session(username, password, remote_server, remote_port):
    # auth = HTTPBasicAuth('admin', 'password')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic'
    }
        
    data = {"username": username, "password": password}
    url = "https://{}:{}/services/auth/login/?output_mode=json".format(remote_server, remote_port)
    response = requests.request("POST", url, data=data, headers=headers, verify=False)
    token = json.loads(response.text)['sessionKey']
    return token
