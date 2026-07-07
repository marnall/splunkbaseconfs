from splunk.persistconn.application import PersistentServerConnectionApplication
import json
import os
import requests
import sys
import splunk.rest as rest
import splunk.appserver.mrsparkle.lib.util as util
import datetime
import subprocess
dir = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','ta_skylight_for_splunk','aob_py' + str(sys.version_info.major))
if not dir in sys.path:
    sys.path.append(dir)

from splunk_aoblib.setup_util import Setup_Util

class AlertHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, args):
        data = self.generateAPIkey(args)
        return {"payload": data, "status": 200}

    def generateAPIkey(self, args):

        try:
            payload = json.loads(args)
            token = payload["session"]["authtoken"]
            uri = 'https://127.0.0.1:8089'
            setup_util = Setup_Util(uri, token)
            pvx_address = setup_util.get_customized_setting("ip_address")
            pvx_username = setup_util.get_customized_setting("username")
            
            if sys.version_info.major==3:
                import urllib.parse
                pvx_password = urllib.parse.urlencode(setup_util.get_customized_setting("password"))
            else:
                import urllib
                pvx_password = urllib.quote(setup_util.get_customized_setting("password"))
            
            

            try:
                url = 'https://{}/api/login?user={}&password={}'.format(pvx_address, pvx_username, pvx_password)
                r = requests.get(url, verify=False)
                response_1 = json.loads(r.text)
                session_id = response_1['result']
            except Exception as e:
                return   {"payload": "Can't generate ssesion. IP, username or password is invalid", "status": 400}    
            
            try:
                url = 'https://{}/api/create-api-key?name=name-{}&_session={}'.format(pvx_address, datetime.datetime.now(), session_id)
                r = requests.get(url, verify=False)
                response_2 = json.loads(r.text)
                pvx_api_key = response_2['result']
            except Exception as e:
                return   {"payload": "Can't generate API Key", "status": 400}

            try:
                cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
                with open(cwd, 'w+') as file:
                    file.write(pvx_api_key)
                    return  {"payload": "You created API Key", "status": 200}
            except Exception as e:
                return {"payload": "Can't generate API Key", "status": 400}

            
        except Exception as e:
            return {"payload": "Can't generate API Key",
                    "status": 400}
