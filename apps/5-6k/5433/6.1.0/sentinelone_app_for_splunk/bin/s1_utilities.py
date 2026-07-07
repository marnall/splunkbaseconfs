import hashlib
import json
import sys
import requests
from Utilities import Utilities
from splunk.appserver.mrsparkle.lib.util import getProductName
from s1_app_properties import __app_name__, __version__ as version


class S1Utilities(Utilities):
    def __init__(self, **kwargs):
        Utilities.__init__(self, **kwargs)
        self._ua_delim = kwargs.get("ua-delim", ";")

    def create_user_agent(self, **kwargs):
        server_info = self.get_server_info()
        self._log.debug(f"action=user_agent system_info={json.dumps(server_info)}")
        ua_items = {
            "productName": f"Splunk_{getProductName()}",
            "productVersion": server_info.get("version", "unknown"),
            "splunkExtensionName": __app_name__,
            "splunkExtensionVersion": version,
            "pythonVersion": sys.version,
        }
        try:
            ua_items["requestsVersion"] = requests.__version__
        except:
            ua_items["requestsVersion"] = "unable_to_retrieve"
        for x in ["os_name", "os_version", "cpu_arch"]:
            ua_items[x] = server_info.get(x, "not_found")
        for x in kwargs:
            ua_items[x] = kwargs.get(x, "not_found")

        def s(st):
            return st.replace("\n", " ")

        return self._ua_delim.join([f"{x}={s(ua_items[x])}" for x in ua_items.keys()])

    def get_api_config(self, api_config_guid):
        self._log.debug("action=checking_api_config guid={}".format(api_config_guid))
        uri = self._build_endpoint_uri(["configs", "conf-authhosts", api_config_guid])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        return json.loads(server_content)["entry"][0]["content"]

    def get_api_config_by_host(self, api_config_host):
        self._log.debug("action=checking_api_config_by_host")
        uri = self._build_endpoint_uri(["configs", "conf-authhosts"])
        server_response, server_content = self._make_get_request(
            uri,
            args={"output_mode": "json", "search": "url={}".format(api_config_host)},
        )
        cnt = json.loads(server_content)
        if len(cnt["entry"]) == 1:
            return self.get_api_config(cnt["entry"][0]["content"])
        else:
            self._log.fatal(
                "action=failure msg=unable_to_find_mgmt_host url={}".format(
                    api_config_host
                )
            )
            raise Exception(
                "Failed to find Auth Host configured with {}".format(api_config_host)
            )

    def get_proxy(self, proxy_guid):
        uri = self._build_endpoint_uri(["configs", "conf-proxy", proxy_guid])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        proxy = json.loads(server_content)["entry"][0]["content"]
        self._log.debug(
            "action=checking_proxy_user user={}".format("proxy_user" in proxy)
        )
        if "proxy_user" in proxy:
            proxy["proxy_pass"] = self.get_credential(
                self._app_name, "pr-{}".format(proxy_guid)
            )
        return proxy

    def get_command(self, cmd_name):
        self._log.debug("action=getting_command_information name={}".format(cmd_name))
        uri = self._build_endpoint_uri(["configs", "conf-commands", cmd_name])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        self._log.info("action=got_command_url sc={}".format(server_content))
        return json.loads(server_content)["entry"][0]["content"]
    
    def get_auth_hosts(self, cmd_name):
        self._log.debug("action=getting_auth_hosts name={}".format(cmd_name))
        uri = self._build_endpoint_uri(["configs", "conf-authhosts"])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        self._log.info("action=got_auth_hosts sc={}".format(server_content))
        return json.loads(server_content)["entry"]

    def get_alert_action(self, action_name):
        self._log.debug(
            "action=getting_alert_actions_information name={}".format(action_name)
        )
        uri = self._build_endpoint_uri(["configs", "conf-alert_actions", action_name])
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        return json.loads(server_content)["entry"][0]["content"]

    def get_field_options(self, field_option_name):
        self._log.debug(
            "action=getting_field_options name={}".format(field_option_name)
        )
        uri = self._build_endpoint_uri(
            ["configs", "conf-fieldoptions", field_option_name]
        )
        server_response, server_content = self._make_get_request(
            uri, args={"output_mode": "json"}
        )
        return json.loads(server_content)["entry"][0]["content"]

    def get_server_info(self):
        uri = self._build_endpoint_uri(["server", "info"])
        sr, sc = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(sc)["entry"][0]["content"]

    def get_server_sysinfo(self):
        uri = self._build_endpoint_uri(["server", "sysinfo"])
        sr, sc = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(sc)["entry"][0]["content"]

    def get_splunk_info(self):
        info = self.get_server_info()
        sysinfo = self.get_server_sysinfo()
        info.update(sysinfo)
        return info

    def get_evt_type(self, evt):
        uri = self._build_endpoint_uri(["saved", "eventtypes", evt])
        sr, sc = self._make_get_request(uri, args={"output_mode": "json"})
        return json.loads(sc)["entry"][0]["content"]["search"]

    @staticmethod
    def sha384(string):
        m = hashlib.sha384()
        m.update(string.encode("utf-8"))
        return m.hexdigest()

    def md5(self, string):
        m = hashlib.md5()
        m.update(string.encode("utf-8"))
        return m.hexdigest()
