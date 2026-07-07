import base64

from phantom.vault import Vault
import phantom.app as phantom

from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

import simplejson as json
import pythonwhois
import datetime

from cyware_consts import *
from tenantapps import TenantAppsAuth


def _json_fallback(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        return obj


class CywareConnector(BaseConnector):
    ACTION_ID_INCIDENT_REPORTING = "create_ticket"

    def __init__(self):

        # Call the BaseConnectors init first
        super(CywareConnector, self).__init__()

    def _test_connectivity(self, param):

        config = self.get_config()

        # get token and secret
        token = config.get("token")
        secret = config.get("secret")
        server = config.get("server")

        if not server:
            self.save_progress("Server is not valid.")
            return self.get_status()

        # checking token and secret is there
        if not token or not secret:
            self.save_progress("Token and/or Secret invalid.")
            return self.get_status()

        self.save_progress("Checking connectivity with Cyware.")

        try:
            connectivity = TenantAppsAuth(token, secret, server).test_connectivity()
        except Exception as e:
            self.set_status(phantom.APP_ERROR, CYWARE_ERR_SERVER_CONNECTION, e)
            self.append_to_message(CYWARE_ERR_CONNECTIVITY_TEST)
            return self.get_status()

        if connectivity["status"] == 200:
            return self.set_status_save_progress(phantom.APP_SUCCESS, CYWARE_SUCC_CONNECTIVITY_TEST)
        else:
            return self.set_status_save_progress(phantom.APP_SUCCESS, "Token or Secret is Invalid.")

    def _handle_report_incident(self, param):
        config = self.get_config()

        self.debug_print("param", param)

        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)

        # get the Authentication parameters
        token = config.get("token")
        secret = config.get("secret")
        server = config.get("server")

        title = param["title"]
        description = param["description"]
        file = base64.b64encode(open(Vault.get_file_path(param["vault_id"])).read())

        attachment = Vault.get_file_info(vault_id=param["vault_id"], file_name=None, container_id=None)[0]

        object = TenantAppsAuth(access_id=token, secret_key=secret, server=server)

        data = {
            "title": title,
            "description": description,
            "attachments": [{
                "file": file,
                "file_name": attachment["name"],
                "type": "base64"
            }]
        }
        action_result.update_summary({"message": "Unable to report event to Cyware."})
        try:
            response = object.report_incident(data=data)
            action_result.add_data(response)
            action_result.update_summary({"message": "Event reported successfully."})
            action_result.set_status(phantom.APP_SUCCESS)
        except Exception as e:
            action_result.set_status(phantom.APP_ERROR, "Unable to report event to Cyware. Error: ", e)
        return action_result.get_status()

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == self.ACTION_ID_INCIDENT_REPORTING:
            ret_val = self._handle_report_incident(param)
        elif action_id == phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)
        return ret_val


if __name__ == '__main__':

    import sys
    import pudb

    pudb.set_trace()

    if len(sys.argv) < 2:
        print "No test json specified as input"
        exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = CywareConnector()
        connector.print_progress_message = True
        ret_val = connector.handle_action(json.dumps(in_json))
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)
