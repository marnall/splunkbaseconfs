
from json import dumps
from logging import Logger
from os import environ, path
from sys import path as sys_path
from pathlib import Path


splunk_home = environ["SPLUNK_HOME"]
ADDON_NAME = "cybersixgill_actionable_alerts"
sys_path.append(path.join(splunk_home, "etc", "apps", ADDON_NAME, "lib"))
sys_path.append(str(Path(__file__).parent.absolute()))

from sixgill.sixgill_actionable_alert_client import \
    SixgillActionableAlertClient
from solnlib.log import Logs
from splunk.persistconn.application import \
    PersistentServerConnectionApplication

from utils import (CHANNEL_ID, form_args_to_dict_with_multi_value,
                   load_common_attributes)
logger: Logger = Logs().get_logger(f"{ADDON_NAME.lower()}_content")


class FetchActionableAlertContent(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        # logger.debug(in_string)
        load_common_attributes(self, in_string, logger=logger)
        # logger.debug(f"client_id={self.client_id}, client_secret={self.client_secret}")
        if not all([self.client_id, self.client_secret]):
            return {
                "payload": {"error": "Either client ID or client Secret is not set."},
                "status": 200,
            }

        sixgill_client = SixgillActionableAlertClient(
            self.client_id, self.client_secret, CHANNEL_ID, verify=True
        )

        alert_content = {}
        if self.method == "GET":
            query = form_args_to_dict_with_multi_value(
                self.request_payload.get("query")
            )
            logger.debug(query)
            try:
                alert_id = query.get("alert_id", [None])[0]
                if alert_id:
                    alert_content = sixgill_client.get_actionable_alert_content(
                        alert_id
                    )
            except Exception as ex:
                logger.error(ex)
        return {"payload": dumps(alert_content), "status": 200}
