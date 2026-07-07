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
from splunklib.results import JSONResultsReader

from utils import (CHANNEL_ID, form_args_to_dict_with_multi_value,
                   load_common_attributes)
logger: Logger = Logs().get_logger(f"{ADDON_NAME.lower()}_delete")


class DeleteActionableAlertContent(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        # logger.debug(in_string)
        load_common_attributes(self, in_string, logger)
        # logger.debug(f"client_id={self.client_id}, client_secret={self.client_secret}")
        if not all([self.client_id, self.client_secret]):
            return {
                "payload": {
                    "error": "Either client ID or client Secret is not set Probably credentials are not set"
                },
                "status": 200,
            }

        sixgill_client = SixgillActionableAlertClient(
            self.client_id, self.client_secret, CHANNEL_ID, logger=logger, verify=True
        )

        alert_delete_response = {}
        try:
            if self.method == "POST":
                json_body = form_args_to_dict_with_multi_value(
                    self.request_payload.get("form")
                )
                logger.debug(json_body)
                alert_ids = json_body.get("alert_ids[]", [])
                index = json_body.get("index", ["default"])[0]
                logger.info(alert_ids)
                if not alert_ids:
                    raise ValueError(f"Alerts ID is empty {alert_ids}")
                params = ",".join(['"{}"'] * len(alert_ids))
                query = f'search index="{index}" sourcetype="src_cybersixgill_actionable_alert" | where parent_id in ({params}) OR id in ({params}) | delete'.format(
                    *alert_ids, *alert_ids
                )
                logger.debug(query)
                result_reader = JSONResultsReader(self.splunk_client.jobs.oneshot(query, output_mode="json"))
                result_dict = [r for r in result_reader][0] if result_reader else {}
                logger.debug(result_dict)
                if result_dict:
                    try:
                        sixgill_client.delete_actionable_alert(
                            actionable_alert_ids=alert_ids
                        )
                        logger.info(f"Deleted alerts with ID: {alert_ids}")
                    except Exception as ex:
                        logger.exception(ex)
        except Exception as ex:
            logger.exception(ex)
        return {"payload": dumps(alert_delete_response), "status": 200}
