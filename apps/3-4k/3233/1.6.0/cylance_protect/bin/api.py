from __future__ import print_function
import sys,csv,splunk.Intersplunk,string
import jwt # PyJWT version 1.5 .3 as of the time of authoring.
import uuid
import requests # requests version 2.18 .4 as of the time of authoring.
import json, sys, re
from datetime import datetime, timedelta

## CUSTOMER MUST FILL IN THE FOLLOWING DATA FROM THEIR TENANT ##
tid_val = "ENTER VALUE HERE" #The tenant 's unique identifier.
app_id = "ENTER VALUE HERE" # The application's unique identifier.
app_secret = "ENTER VALUE HERE" #The application 's secret to sign the auth token with.
BASE_AUTH_URL = "https://protectapi.cylance.com"

# Create Authentication token which is used to retrieve an access token for further API access
def auth():
    # 30 minutes from now 
    timeout = 1800 
    now = datetime.utcnow() 
    timeout_datetime = now + timedelta(seconds = timeout) 
    epoch_time = int((now - datetime(1970, 1, 1)).total_seconds()) 
    epoch_timeout = int((timeout_datetime - datetime(1970, 1, 1)).total_seconds()) 

    jti_val = str(uuid.uuid4()) 

    claims = { 
    "exp": epoch_timeout, 
    "iat": epoch_time, 
    "iss": "http://cylance.com", 
    "sub": app_id, 
    "tid": tid_val, 
    "jti": jti_val 
    # The following is optional and is being noted here as an example on how one can restrict 
    # the list of scopes being requested 
    # "scp": "policy:create, policy:list, policy:read, policy:update" 
    } 

    AUTH_URL = BASE_AUTH_URL + "/auth/v2/token"
    encoded = jwt.encode(claims, app_secret, algorithm='HS256') 
    #print "auth_token:\n" + encoded + "\n" 

    payload = {"auth_token": encoded.decode('UTF-8')}
    headers = {"Content-Type": "application/json; charset=utf-8"} 
    resp = requests.post(AUTH_URL, headers=headers, data=json.dumps(payload)) 
    #print "http_status_code: " + str(resp.status_code) 
    #print "access_token:\n" + json.loads(resp.text)['access_token'] + "\n"

    access_token = json.loads(resp.text)['access_token']
    # or access_token = json.loads(resp.text).get('access_token') 
    # using the get method quietly bypasses the exception thrown when customer data not populated 
    return(access_token)

# GET request to API that may have page numbers
def get_req_page(access_token, AUTH_URL):
    headers = {"Accept": "application/json",
               "Authorization": "Bearer " + access_token } 
    resp = requests.get(AUTH_URL, headers=headers)
    json_resp=json.loads(resp.text) 

    # Print header
    for entry in json_resp['page_items'][:1]:
        for key, value in list(entry.items()):
            print((str(key) + ', '), end='')
        print('')

    # Print contents
    for entry in json_resp['page_items']:
        for key, value in list(entry.items()):
            print(str(value) + ', ', end='')
        print('')

    return()

    
# GET request to API that cannot have page numbers
def get_req(access_token, AUTH_URL):
    headers = {"Accept": "application/json",
               "Authorization": "Bearer " + access_token } 
    resp = requests.get(AUTH_URL, headers=headers)
    json_resp=json.loads(resp.text) #print resp.text 
    print(json.dumps(json_resp, indent=4))
    return()

# POST request to API that cannot have page numbers
def post_req(access_token, AUTH_URL, payload):
    headers = {"Content-Type": "application/json; charset=utf-8",
               "Accept": "application/json",
               "Authorization": "Bearer " + access_token } 
    resp = requests.post(AUTH_URL, headers=headers, data=json.dumps(payload))
    print("HTTP STATUS CODE: " + str(resp.status_code))
    print("HTTP RESPONSE: " + str(resp.text))
    return()

# POST request to API that cannot have page numbers
def delete_req(access_token, AUTH_URL, payload):
    headers = {"Content-Type": "application/json; charset=utf-8",
               "Accept": "application/json",
               "Authorization": "Bearer " + access_token } 
    resp = requests.delete(AUTH_URL, headers=headers, data=json.dumps(payload))
    print("HTTP STATUS CODE: " + str(resp.status_code))
    print("HTTP RESPONSE: " + str(resp.text))
    return()

## Starts main ##
(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
#print "answer"

# Check for the number of arguments
if len(sys.argv)<2:
    usage="""\nError: Incorrect number of arguments. Valid syntax: api.py <function> <possible_parameter>\n
    Global list functions:
    + getwhitelist
    + getblacklist
    + addwhitelist <SHA256>
    + addblacklist <SHA256>
    + deleteblacklist <SHA256>
    + deletegloballist <SHA256>\n
    Device functions:
    + getdevices
    + getdevice <device_id>
    + getdevicethreats <device_id>\n"""
    print(usage)
    sys.exit()

function=sys.argv[1]  # Get the function from the user
access_token = auth()  # Authenticate to get the access token
#print access_token

# GLOBAL LIST FUNCTIONS
if function=="getwhitelist":
    AUTH_URL = BASE_AUTH_URL + "/globallists/v2?listTypeId=1"
    get_req_page(access_token, AUTH_URL)
elif function=="getblacklist":
    AUTH_URL = BASE_AUTH_URL + "/globallists/v2?listTypeId=0"
    get_req_page(access_token, AUTH_URL)
elif function=="addwhitelist":
    if len(sys.argv)<3:
        print("\nError: Did not specify SHA256 hash")
        sys.exit()
    sha256=sys.argv[2]
    AUTH_URL = BASE_AUTH_URL + "/globallists/v2"
    payload = {"sha256": sha256, "list_type":"GlobalSafe", "category":"None", "reason":"APIv2 Whitelist" }
    post_req(access_token, AUTH_URL, payload)
elif function=="addblacklist":
    if len(sys.argv)<3:
        print("\nError: Did not specify SHA256 hash")
        sys.exit()
    sha256=sys.argv[2]
    AUTH_URL = BASE_AUTH_URL + "/globallists/v2"
    payload = {"sha256": sha256, "list_type":"GlobalQuarantine", "category":"None", "reason":"APIv2 Whitelist" }
    post_req(access_token, AUTH_URL, payload)
elif function=="deletewhitelist":
    if len(sys.argv)<3:
        print("\nError: Did not specify SHA256 hash")
        sys.exit()
    sha256=sys.argv[2]
    AUTH_URL = BASE_AUTH_URL + "/globallists/v2"
    payload = {"sha256": sha256, "list_type":"GlobalSafe" }
    delete_req(access_token, AUTH_URL, payload)
elif function=="deleteblacklist":
    if len(sys.argv)<3:
        print("\nError: Did not specify SHA256 hash")
        sys.exit()
    sha256=sys.argv[2]
    AUTH_URL = BASE_AUTH_URL + "/globallists/v2"
    payload = {"sha256": sha256, "list_type":"GlobalQuarantine" }
    delete_req(access_token, AUTH_URL, payload)

# DEVICE FUNCTIONS
elif function=="getdevices":
    AUTH_URL = BASE_AUTH_URL + "/devices/v2"
    get_req_page(access_token, AUTH_URL)
elif function=="getdevice":
    if len(sys.argv)<3:
        print("\nError: Did not specify device_id")
        sys.exit()
    device_id=sys.argv[2]
    AUTH_URL = BASE_AUTH_URL + "/devices/v2/" + device_id
    get_req(access_token, AUTH_URL)
elif function=="getdevicethreats":
    if len(sys.argv)<3:
        print("\nError: Did not specify device_id")
        sys.exit()
    device_id=sys.argv[2]
    AUTH_URL = BASE_AUTH_URL + "/devices/v2/" + device_id + "/threats"
    get_req_page(access_token, AUTH_URL)
else:
    print("Specified function is not valid")

