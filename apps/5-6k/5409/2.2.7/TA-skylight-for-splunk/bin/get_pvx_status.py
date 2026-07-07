from splunk.persistconn.application import PersistentServerConnectionApplication
import json
import os
import requests
import sys
import splunk.rest as rest
import splunk.appserver.mrsparkle.lib.util as util
dir = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','ta_skylight_for_splunk','aob_py' + str(sys.version_info.major))
if not dir in sys.path:
    sys.path.append(dir)

from splunk_aoblib.setup_util import Setup_Util

class AlertHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, args):
        data = self.getAPIkey(args)
        return {"payload": data, "status": 200}

    def getAPIkey(self, args):
        try:
            payload = json.loads(args)
            token = payload["session"]["authtoken"] 

            uri = 'https://127.0.0.1:8089'

            setup_util = Setup_Util(uri, token)
            pvx_address = setup_util.get_customized_setting("ip_address")
            url = 'https://{}/api/echo?name=statusOK'.format(pvx_address)
    
            try:
                response = requests.get(url, verify=False)
            except:
                return {"payload": "Skylight sensor is unavailable", "status": 200}
                
            response_must_be =  "{\n    \"type\": \"result\",\n    \"result\": {\n        \"name\": \"statusOK\"\n    }\n}\n"

            if(response_must_be != response.text):
                return {"payload": "Skylight sensor is unavailable", "status": 200}
            try:
                cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
                with open(cwd, 'r') as file:
                    pvx_api_key = file.read().splitlines()[0]
            except Exception as e:
                pvx_api_key="NONE"
                return {"payload": "Can't get api key. Please, press 'Save' to regenerate it", "status": 200}

            url = 'https://{}/api/query?expr=traffic SINCE @now-60'.format(pvx_address)
            headers = {'PVX-Authorization': pvx_api_key}
            response = requests.get(url, headers=headers, verify=False)

            if("AUTHENTICATION-NEEDED" not in response.text and "INVALID-CREDENTIALS" not in response.text):
                return {"payload": "Skylight sensor is connected", "status": 200}
            else:
                return {"payload": "Skylight sensor is not authenticate", "status": 200}

        except Exception as e:
            return {"payload": "Skylight sensor is not connected: {}".format(e), "status": 200}
