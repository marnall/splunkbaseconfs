# System import
import splunk
import os
import sys
import json


splunk_home = os.getenv("SPLUNK_HOME")

# Append PYTHONPATH so script will load corresponding library
sys.path.append(splunk_home + "/etc/apps/Endgame/bin/")
sys.path.append(splunk_home + "/etc/apps/Endgame/bin/apputils")

from logger import setup_logging as create_logger

logger = create_logger("endgame_logger", "endgame.log")

from endgame_api_helper import APIHelper
from splunk.persistconn.application import PersistentServerConnectionApplication

LOG_MAX_SIZE_BYTES = 1024 ** 2 * 100
LOG_MAX_ROTATIONS = 5

enpoints = {
    "login": "/api/auth/login",
    "logout": "/api/v1/logout",
    "aggregate": "/api/v1/aggregate",
    "aggregations": "/api/v1/alerts/aggregations",
    "activities": "/api/v1/activities",
    "investigations": "/api/v1/investigations",
    "investigations_stats": "/api/v1/investigations/stats",
    "investigate_endpoint": "/api/v1/investigations/{0}",
    "investigation_details": "/api/v1/investigations/{0}",
    "alerts_details": "/api/v1/alerts/{0}",
    "dashboard-stats": "/api/v1/alerts/dashboard-stats",
    "endpoints": "/api/v1/endpoints",
    "endpoints-stats": "/api/v1/endpoints/stats",
    "endpoint_details": "/api/v1/endpoints/{0}",
    "task-descriptions": "/api/v1/task-descriptions/",
    "collections": "/api/v1/collections/",
    "collections_details": "/api/v1/collections/{0}",
    "alerts": "/api/v1/alerts",
    "alerts-stats": "/api/v1/alerts/stats",
    "alert_timeline": "/api/v1/alerts/{0}/timeline",
    "find_powershell": "/api/v1/event_search/find_powershell",
    "find_malicious": "/api/v1/event_search/find_malicious",
    "search_process": "/api/v1/event_search/search_process",
    "parent_process_tree": "/api/v1/event_search/parent_process_tree",
    "search_dns": "/api/v1/event_search/search_dns",
    "search_network": "/api/v1/event_search/search_network",
    "/search_user": "/api/v1/event_search/search_user",
    "search_alert": "/api/v1/event_search/search_alert",
    "malware-report": "/api/v1/cloud/malware-report",
    "smp-host": "/smp-host",
    "smp_version": "/api/v1/version",
    "deployment-status": "/api/v1/deployment-stats",
    "endpoints-facets": "/api/v1/endpoints/facets",
    "tasks": "/api/v1/tasks",
    "task-descriptions": "/api/v1/task-descriptions",
    "native_url": "/api/v1/native_url",
    "policies": "/api/v1/policies",
    "rules": "/api/v1/rules/{0}",
}


class RESTHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, payload):
        """
        Handles different types of requests for API call.
        """
        response = {}
        result = {}
        try:
            # get the request method
            json_data = json.loads(payload)
            method = json_data["method"]
        except:
            raise Exception("handle: %s" % (sys.exc_info()[0]))

        if method == "GET":
            result = self.handleGET(json_data)

        elif method == "POST":
            result = self.handlePOST(json_data)

        elif method == "PUT":
            result = self.handlePUT(json_data)

        elif method == "DELETE":
            result = self.handleDELETE(json_data)

        else:
            logger.error("No request method received to make an API call")

        response["payload"] = result
        return response

    def handleGET(self, data):
        """
        Handles GET request API calls.
        """
        result = {}
        apihelper = APIHelper(data["session"]["authtoken"], data["session"]["user"])
        query = data["query"]
        api_name = self.extract_apiname(query)
        api_url = enpoints[api_name]
        url_ext = ""
        url = api_url
        if len(query) > 1:
            url_ext = self.generateURL(query)
            url = api_url + url_ext

        if api_name in [
            "investigate_endpoint",
            "investigation_details",
            "alerts_details",
            "endpoint_details",
            "collections_details",
            "alert_timeline",
            "rules",
        ]:
            url = api_url.format(url_ext)

        if api_name in ["native_url"]:
            result = apihelper.getNativeAppBaseURL()
        else:
            result = apihelper.invoke_api("GET", url)

        return result

    def handlePOST(self, data):
        """
        Handles POST request API calls.
        """
        result = {}
        apihelper = APIHelper(data["session"]["authtoken"], data["session"]["user"])
        data = json.loads(json.dumps(data))

        try:
            url = enpoints[data["rest_path"].replace("/endgame/post/", "")]
        except Exception as exp:
            logger.error(str(exp))
            result["payload"] = {"msg": str(exp)}

        try:
            result["payload"] = apihelper.invoke_api("POST", url, data["payload"])
        except Exception as exp:
            logger.error(str(exp))
            result["payload"] = {"msg": str(exp)}

        return result

    def handlePUT(self, data):
        """
        Handles PUT request API calls.
        """
        result = {}
        apihelper = APIHelper(data["session"]["authtoken"], data["session"]["user"])
        data = json.loads(json.dumps(data))

        try:
            url = enpoints[data["rest_path"].replace("/endgame/put/", "")]
        except Exception as exp:
            logger.error(str(exp))
            result["payload"] = {"msg": str(exp)}

        try:
            result["payload"] = apihelper.invoke_api("PUT", url, data["payload"])
        except Exception as exp:
            logger.error(str(exp))
            result["payload"] = {"msg": str(exp)}

        return result

    def handleDELETE(self, data):
        """
        Handles DELETE request API calls.
        """
        return data

    def extract_apiname(self, params):
        """
        Extracts source_api parameter which is used to determine url to make request.
        """
        api_name = None
        for param in params:
            if param[0] in "source_api":
                api_name = str(param[1])
        return api_name

    def generateURL(self, params):
        """
        Generates URL to request with encoded parameters if any given.
        """
        urlstring = "?"
        for param in params:
            if param[0] not in "source_api" and param[0] not in "url_value":
                urlstring = urlstring + str(param[0] + "=" + str(param[1]) + "&")
            elif param[0] in "url_value":
                urlstring = str(param[1]) + "&"
                break

        return urlstring[:-1]
