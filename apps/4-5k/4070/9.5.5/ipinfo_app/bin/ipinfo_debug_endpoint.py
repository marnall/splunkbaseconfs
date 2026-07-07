import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

import splunk
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from ipinfo_utils import (
    get_bearer_token,
    get_management_uri,
    get_service,
    get_service_from_session_key,
    get_shcluster_current_mgmt_uri,
    get_shcluster_members,
)


class DebugIpinfo(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        response = {}
        self.response.setStatus(200)
        self.response.setHeader("content-type", "application/json")

        bearer_token = get_bearer_token(self.sessionKey, False)

        query = self.request.get("query")
        name = query["name"]

        response["timestamp"] = int(time.time())

        if name == "check_auth_with_session_key":
            try:
                service = get_service_from_session_key(get_management_uri(), self.sessionKey)
                service.splunk_version
                response[name] = "yes"
            except Exception as e:
                response[name] = f"no (error: '{e}')"
        elif name == "check_bearer_token_valid":
            service = get_service(get_management_uri(), bearer_token)
            try:
                service.splunk_version
                response[name] = "yes"
            except Exception as e:
                response[name] = f"no (error: '{e}')"

        elif name == "get_management_uri":
            response[name] = get_management_uri()
        elif name == "get_service":
            service = get_service(get_management_uri(), bearer_token)
            response[name] = service.info()
        elif name == "get_shcluster_current_mgmt_uri":
            response[name] = get_shcluster_current_mgmt_uri(self.sessionKey) or "none"
        elif name == "get_shcluster_members":
            response[name] = get_shcluster_members(self.sessionKey, get_shcluster_current_mgmt_uri(self.sessionKey))

        self.response.write(json.dumps(response))
