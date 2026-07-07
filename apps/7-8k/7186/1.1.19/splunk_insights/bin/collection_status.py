import sys
import os
import json
import tempfile
import requests
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

""""
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
"""

class CollectionStatusHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()

    def get_local_apps(self, session_key) :
        endpoint = "/servicesNS/-/-/apps/local?output_mode=json"

        response, content = rest.simpleRequest(
            endpoint,
            sessionKey=session_key,
            method="GET"
        )

        if response.status != 200:
            raise Exception(f"Failed to get installed apps : HTTP {response.status}")

        data = json.loads(content)

        return data
    
    def get_server_info(self, session_key) :
        endpoint = "/services/server/info?output_mode=json"

        response, content = rest.simpleRequest(
            endpoint,
            sessionKey=session_key,
            method="GET"
        )

        if response.status != 200:
            raise Exception(f"Failed to get server info : HTTP {response.status}")

        data = json.loads(content)

        return data

    def get_ssef_conf(self, session_key):
        """
        Read ssef.conf using Splunk internal REST API
        """

        endpoint = "/servicesNS/-/splunk_insights/configs/conf-ssef?output_mode=json"

        response, content = rest.simpleRequest(
            endpoint,
            sessionKey=session_key,
            method="GET"
        )

        if response.status != 200:
            raise Exception(f"Failed to read ssef.conf: HTTP {response.status}")

        data = json.loads(content)

        return data
    
    def normalize(self,name):
        return name if name.startswith("ssef_collection://") else "ssef_collection://" + name

    def handle(self, args):
        try:
            #dbg.set_breakpoint()
            request = json.loads(args)
            session_key = request["session"]["authtoken"]
            apps = self.get_local_apps(session_key)
            
            target_apps = {"SplunkEnterpriseSecuritySuite", "itsi"}

            def compute_status(content):
                disabled = content.get("disabled")
                visible = content.get("visible")

                if disabled == "1":
                    return "Disabled"
                elif disabled == "0":
                    return "Enabled"
                elif visible == "0":
                    return "Disabled"
                else:
                    return "Unknown"

            premiumApps = []

            for app in apps["entry"]:
                name = app.get("name")

                if name in target_apps:
                    status = compute_status(app.get("content", {}))
                    premiumApps.append({
                        "name": name,
                        "status": status
                    })

            server_info = self.get_server_info(session_key)
            serverInfo = {
                "serverName": server_info["entry"][0]["content"].get("serverName"),
                "isSplunkCloud": bool(server_info["entry"][0]["content"].get("instance_type")) if "instance_type" in server_info["entry"][0]["content"] else False
            }

            def is_collection_compatible(collection, platform):
                platform_field = collection.get("content", {}).get("platform")

                if not platform_field or platform_field == "all":
                    return True

                if platform and platform_field == "cloud":
                    return True

                if not platform and platform_field == "enterprise":
                    return True

                return False


            def is_collection_for_premium_apps(collection, premium_apps):
                # remove prefix
                col_name = collection.get("name", "").replace("ssef_collection://", "")

                if col_name == "es_adoption_collection":
                    if not any(
                        a.get("name") == "SplunkEnterpriseSecuritySuite" and a.get("status") == "Enabled"
                        for a in premium_apps
                    ):
                        return False

                if col_name == "ssef_itsi_collection":
                    if not any(
                        a.get("name") == "itsi" and a.get("status") == "Enabled"
                        for a in premium_apps
                    ):
                        return False

                return True


            ssefConf = self.get_ssef_conf(session_key)

            path = request["rest_path"]

            # Extract collection name if present
            parts = path.split("/")
            collection_name = parts[-1] if len(parts) > 1 and parts[-1] != "collectionstatus" else None

            collections = []
            for entry in ssefConf["entry"]:

                name = entry["name"]

                if "ssef_collection://" not in name:
                    continue

                if entry["content"]["visible"] == "0":
                    continue

                if is_collection_compatible(entry, serverInfo["isSplunkCloud"]) == False:
                    continue
                
                if is_collection_for_premium_apps(entry , premiumApps) == False :
                    continue

                status = "notactivated"

                content = entry["content"]

                if "searches" in content and content["searches"]:

                    searches = content["searches"].split(",")

                    if len(searches) == 0:
                        status = "notactivated"
                    else:

                        statuses = []

                        for s in searches:

                            found = any(
                                e["name"] in [
                                    "default_is4s_ssef_hourly_group",
                                    "default_is4s_ssef_daily_group",
                                    "default_is4s_ssef_weekly_group",
                                    "default_is4s_ssef_monthly_group"
                                ] and s in e["content"]["checks"].split(",")

                                for e in ssefConf["entry"]
                            )

                            statuses.append(found)

                        if True in statuses and False in statuses:
                            status = "notactivated"
                        elif all(statuses):
                            status = "activated"

                collections.append({
                    "name": entry["name"],
                    "owner": entry["acl"]["owner"],
                    "sharing": entry["acl"]["sharing"],
                    "title": content.get("collection_name"),
                    "description": content.get("description"),
                    "groups": content.get("groups"),
                    "searches": content.get("searches"),
                    "status": status,
                    "selectedkpis": content.get("selectedkpis", []),
                    "type": content.get("type"),
                    "homepage": content.get("homepage"),
                    "readonly": content.get("readonly") == "1",
                    "personas": content.get("personas")
                })

            if collection_name:
                return {
                    "status": 200,
                    "payload": [item for item in collections if item["name"] == self.normalize(collection_name)],
                    "headers": {'Content-Type': 'application/json'}
                } 
            else :
                return {
                    "status": 200,
                    "payload": collections,
                    "headers": {'Content-Type': 'application/json'}
                } 
            
        
            

        except Exception as e:
            return {
                "status": 500,
                "payload": json.dumps({"status" : 500, "message": "Error : Unable to find the collection."}),
                "headers": {'Content-Type': 'application/json'}
            } 
            

    def _error(self, message, code):
        return {
            "status": code,
            "payload": json.dumps({"error": message}),
            "headers": {'Content-Type': 'application/json'}
        }
