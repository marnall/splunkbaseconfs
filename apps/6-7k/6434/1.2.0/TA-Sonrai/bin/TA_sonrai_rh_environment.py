import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..')))
import json
import requests
import common.proxy as pro
from common.const import GET_ENVIRONMENT_QUERY, ENVIRONMENT_QUERY_NAME
import splunk.admin as admin
from solnlib.utils import is_true
from splunktaucclib.rest_handler.error import RestError
import common.utility as utility


class GetEnvironments(admin.MConfigHandler):

    def setup(self):
        self.supportedArgs.addOptArg("sonrai_account")
    
    def handleList(self, conf_info):
        sonrai_account = self.callerArgs.get("sonrai_account")
        if sonrai_account:
            # sonrai_account is in the form of list with one element
            sonrai_account = sonrai_account[0]
            session_key = self.getSessionKey()
            account_info = utility.read_conf_file(session_key, "ta_sonrai_account", stanza=sonrai_account)
            request_url = utility.get_host_url(account_info.get("organization_id"), account_info.get("sonrai_host"))
            verify_certs = account_info.get("verify_certs")
            headers = utility.get_headers(account_info.get("sonrai_token"), ENVIRONMENT_QUERY_NAME)
            payload = utility.get_payload(GET_ENVIRONMENT_QUERY)
            proxy_settings = pro.read_proxies_from_conf(session_key=session_key)
            try:
                response = requests.post(
                    request_url,
                    data=payload,
                    headers=headers,
                    proxies=proxy_settings,
                    timeout=30,
                    verify=is_true(verify_certs)
                )
                environments = response.json().get("data")

            except Exception as e:
                raise RestError(409, "Something went wrong while fetching Environments. Error: {}".format(e))
            else:
                for env in environments.get("Environments").get("items"):
                    conf_info[env["name"]].append('label', env["name"])

if __name__ == "__main__":
    admin.init(GetEnvironments, admin.CONTEXT_NONE)