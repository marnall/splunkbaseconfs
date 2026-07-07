import os
import requests as req
import json
import time

access_token = "daafafefsdfsa"

#Setter/Getter for Checkpoint
def get_checkpoint():
    with open(os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'ISVLogging', 'appserver', 'static', 'checkpoint.json')) as f:
        data = json.load(f)
        return data["lastTimestamp"]

def set_checkpoint():
    obj = { 'lastTimestamp' : int(time.time()*1000) }
    with open(os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'ISVLogging', 'appserver', 'static', 'checkpoint.json'),'w') as f:
        json.dump(obj, f)
########################################

def get_access_token():
    tokenReqURL = "https://ISVTENANTURL:443/v1.0/endpoint/default/token"
    parameters  = {
        "client_id" : "client_id",
        "client_secret" : "client_secret",
        "grant_type" : "client_credentials"
    }
    response_json = req.post(tokenReqURL, data=parameters).json()
    access_token = response_json["access_token"]
    return access_token


def isv_api_call(requestURL, header, parameter):
    response = req.get(requestURL, headers=header, params=parameter)
    
    if response.status_code == 401:
        global access_token
        token = get_access_token()
        access_token = token
        get_tenant_events()

    elif response.status_code != 200:
        print(response.status_code)
        exit()

    else :
        data = response.json()
        return data

def get_tenant_events():
    global access_token
    requestURL = "https://ISVTENANTURL:443/v1.0/events"
    header = {
        "Authorization" : "Bearer " +  access_token
    }
    parameter = {
        "from" : get_checkpoint(),
        "size" : 10000,
        "all_events" : "yes"
    }
    return isv_api_call(requestURL, header, parameter)


def main():
    tenant_logs = get_tenant_events()
    if tenant_logs != None:
        for events in tenant_logs["response"]["events"]["events"]:
            print(json.dumps(events))
        set_checkpoint()
    else:
        main()


if __name__ == "__main__":
    main()
