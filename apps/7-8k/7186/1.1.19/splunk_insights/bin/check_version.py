import sys
import os
import json
import tempfile
import requests
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

"""
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
"""

APP_NAME = "splunk_insights"
APPID = "7186"

class CheckVersionHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()

    def convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}

        for key, val in query:

            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]

            # If the entry is already included as a list, then just add the entry
            elif key in parameters:
                parameters[key].append(val)

            # Otherwise, just add the entry
            else:
                parameters[key] = val

        return parameters

    def parse_in_string(self, in_string):
        """
        Parse the in_string
        """

        
        params = json.loads(in_string)

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))


        return params
    
    def handle(self, args):
        try:
            #dbg.set_breakpoint()
            local_version = self.get_local_version(os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", APP_NAME))
            splunkbase_version = self.get_splunkbase_version(APPID)

            return {
                "status": 200,
                "payload": json.dumps({"status" : 200,"localversion" : local_version, "sbversion": self.tuple_to_version_string(splunkbase_version) ,"message": self.check_for_update(local_version, splunkbase_version)}),
                "headers": {'Content-Type': 'application/json'}
            } 
            
        
            

        except Exception as e:
            return {
                "status": 500,
                "payload": json.dumps({"status" : 500, "message": "Error : Unable to determine versions."}),
                "headers": {'Content-Type': 'application/json'}
            } 
            

    def _error(self, message, code):
        return {
            "status": code,
            "payload": json.dumps({"error": message}),
            "headers": {'Content-Type': 'application/json'}
        }
    def tuple_to_version_string(self,t):
        # remove trailing zeros
        parts = list(t)
        while len(parts) > 1 and parts[-1] == 0:
            parts.pop()
        return ".".join(map(str, parts))
    
    def get_local_version(self,app_path):
        """
        Reads the local version from app.conf
        """
        app_conf_path = os.path.join(app_path, "default", "app.conf")
        if not os.path.exists(app_conf_path):
            app_conf_path = os.path.join(app_path, "local", "app.conf")
        
        if not os.path.exists(app_conf_path):
            raise FileNotFoundError("app.conf not found in default or local directory")

        version = None
        with open(app_conf_path, "r") as f:
            for line in f:
                if line.strip().startswith("version"):
                    version = line.split("=")[1].strip()
                    break
        return version

    def get_splunkbase_version(self,app_id):
        """
        Fetches the latest version of the app from Splunkbase.
        app_id is the numeric ID from the app’s URL on splunkbase.
        """
        url = f"https://splunkbase.splunk.com/api/v1/app/{app_id}/release"
        resp = requests.get(url, headers={"User-Agent": "Splunk-App-Version-Checker"})
        resp.raise_for_status()
        releases = resp.json()

        versions = []
        for rel in releases:
            v = rel.get("name")
            if v:
                versions.append(self.normalize_version(v))

        if not versions:
            return None

        return max(versions, key=lambda x: self.normalize_version(x))
        

    def normalize_version(self, v, max_parts = 3) :
        if isinstance(v, tuple):
            # Already normalized
            return v

        if not isinstance(v, str):
            v = str(v)

        parts = v.split(".")
        nums = []
        for p in parts:
            try:
                nums.append(int(p))
            except ValueError:
                # ignore non-numeric parts (e.g. "1.2-beta" -> "1.2")
                break

        while len(nums) < max_parts:
            nums.append(0)

        return tuple(nums[:max_parts])
    
    def check_for_update(self,local_version, splunkbase_version):
        

        if local_version is None or splunkbase_version is None:
            return "Unable to determine versions"

        local_norm = self.normalize_version(local_version)
        latest_norm = self.normalize_version(splunkbase_version)

        if local_norm >= latest_norm:
            return False
        else:
            return True
