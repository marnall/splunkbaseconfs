from VMWUtilities import Utilities
import json


class CBCUtilities(Utilities):
    def __init__(self, **kwargs):
        Utilities.__init__(self, **kwargs)

    def get_tenant(self, tenant_guid):
        uri = self._build_endpoint_uri(
            ['configs', 'conf-tenants', tenant_guid])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"})
        return json.loads(server_content)["entry"][0]["content"]

    def get_proxy(self, proxy_guid):
        uri = self._build_endpoint_uri(['configs', 'conf-proxy', proxy_guid])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"})
        proxy = json.loads(server_content)["entry"][0]["content"]
        self._log.debug("action=checking_proxy_user user={}".format(
            "proxy_user" in proxy))
        if "proxy_user" in proxy:
            proxy["proxy_pass"] = self.get_credential(self._app_name,
                                                      "pr-{}".format(proxy_guid))
        return proxy

    def get_command(self, cmd_name):
        self._log.debug(
            "action=getting_command_information name={}".format(cmd_name))
        uri = self._build_endpoint_uri(['configs', 'conf-commands', cmd_name])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"})
        return json.loads(server_content)["entry"][0]["content"]

