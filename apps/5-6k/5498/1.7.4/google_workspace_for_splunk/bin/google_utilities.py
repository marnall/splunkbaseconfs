import json
from Utilities import Utilities


class GSuiteUtilities(Utilities):
    def __init__(self, **kwargs):
        Utilities.__init__(self, **kwargs)

    def get_proxy(self, proxy_guid):
        uri = self._build_endpoint_uri(['configs', 'conf-proxy', proxy_guid])
        server_response, server_content = self._make_get_request(uri, args={"output_mode": "json"})
        proxy = json.loads(server_content)["entry"][0]["content"]
        self._log.debug("action=checking_proxy_user user={}".format("proxy_user" in proxy))
        if "proxy_user" in proxy:
            proxy["proxy_pass"] = self.get_credential(self._app_name,
                                                      "pr-{}".format(proxy_guid))
        return proxy

    def get_workspace_creds(self, guid):
        uri = self._build_endpoint_uri(['configs', 'conf-googleworkspacecredentials', guid])
        server_response, server_content = self._make_get_request(uri, args={"output_mode": "json"})
        t = json.loads(server_content)["entry"][0]["content"]
        return {"domain": t["domain"], "impersonation_user": t["impersonation_user"],
                "proxy_guid": t.get("proxy_guid", None)}

    def get_command(self, cmd_name):
        self._log.debug(
            "action=getting_command_information name={}".format(cmd_name))
        uri = self._build_endpoint_uri(['configs', 'conf-commands', cmd_name])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"})
        return json.loads(server_content)["entry"][0]["content"]

    def get_server_info(self):
        uri = self._build_endpoint_uri(["server", "info"])
        sr, sc = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(sc)["entry"][0]["content"]

    def get_current_user_information(self):
        auth = self.get_current_auth_context()
        return auth

    def get_user_information(self, user):
        uri = self._build_endpoint_uri(["authentication", "users", user])
        sr, sc = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(sc)["entry"][0]["content"]

    def get_current_auth_context(self):
        uri = self._build_endpoint_uri(["authentication", "current-context"])
        sr, sc = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(sc)["entry"][0]["content"]
