import json
import os
import sys
from urllib.parse import parse_qs
import requests

from splunk.persistconn.application import PersistentServerConnectionApplication

# Within the splunk ecosystem, this line is needed before we can import other custom modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ataportal import CSZTAP
from Utilities import Utilities


class ValidateHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):

        response_status_code = 500
        try:
            request = json.loads(in_string)
            request_payload = parse_qs(request["payload"])

            should_send_test_event = (
                _get_payload_value(request_payload, "test_event") == "true"
            )
            url = _get_payload_value(request_payload, "url")
            proxy = {
                "use_ssl": (
                    "true"
                    if _get_payload_value(request_payload, "proxy_protocol") == "https"
                    else "false"
                ),
                "proxy_url": _get_payload_value(request_payload, "proxy_host"),
                "proxy_port": _get_payload_value(request_payload, "proxy_port"),
                "proxy_user": _get_payload_value(request_payload, "proxy_user"),
                "proxy_pass": _get_payload_value(request_payload, "proxy_pass"),
            }
            body = {
                "psa_id": _get_payload_value(request_payload, "psa_id"),
                "logstash_token": _get_payload_value(request_payload, "logstash_token"),
            }

            session = requests.Session()
            headers = {"content-type": "application/json"}

            Utilities.verify_https(url)
            response = session.post(
                url=url,
                data=json.dumps(body),
                headers=headers,
                proxies=Utilities.build_proxy_string(proxy),
            )
            response_status_code = response.status_code
            response.raise_for_status()
            configuration = response.json()

            if should_send_test_event:
                response_status_code = 500
                response = self.send_test_event(request)
                response_status_code = response.status_code
                response.raise_for_status()

            return {"payload": configuration, "status": response_status_code}

        except Exception:
            ex_type, ex_value, _ = sys.exc_info()
            return {
                "payload": {
                    "error_type": ex_type.__name__,
                    "error_message": str(ex_value),
                },
                "status": response_status_code,
            }

    def send_test_event(self, request):

        # Pull the alert action config to get the ztap host guid
        session_key = request["session"]["authtoken"]
        utils = Utilities(app_name="ztap_app", session_key=session_key)
        conf = utils.get_configuration("alert_actions", "ataportal")
        ztap_host_guid = conf["param.ztap_host_guid"]
        proxy_guid = conf.get("param.proxy_guid")

        client = CSZTAP(
            json.dumps(
                {
                    "session_key": session_key,
                    "configuration": {
                        "ztap_host_guid": ztap_host_guid,
                        "proxy_guid": proxy_guid,
                    },
                }
            ),
            "Test Event",
        )
        return client.send_test_event()


def _get_payload_value(payload, key):
    vals = payload.get(key, [])
    if len(vals):
        return vals[0]
    else:
        return ""
