import json
import time
import requests
from solnlib import splunkenv, log
from splunklib import client
from splunktaucclib.rest_handler import error
from Splunk_TA_Appdynamics_BaseRestHandler import BaseRestHandler
from analytics_service import AnalyticsService
from ucc_utils import Util

logger = log.Logs().get_logger("appdynamics_analytics_data_validation")


def _validate_credentials(account_name, session_key, query):
    if account_name is None:
        return
    logger.info("Validating Analytics Data Query: account=%s, query=%s", account_name, query)

    try:
        analytics = AnalyticsService(account_name, session_key, throw_exceptions=True, external_logger=logger)
    except Exception as e:
        raise error.RestError(500, f"The Analytics Account Key was not found?")

    try:
        analytics.search(query, limit=1)
    except Exception as e:
        raise e
    return


class CustomRestHandler(BaseRestHandler):
    def handleEdit(self, confInfo):
        _validate_credentials(
            self.payload.get("analytics_account"),
            self.getSessionKey(),
            self.payload.get("query"),
        )
        super().handleEdit(confInfo)

    def handleCreate(self, confInfo):
        _validate_credentials(
            self.payload.get("analytics_account"),
            self.getSessionKey(),
            self.payload.get("query"),
        )
        super().handleCreate(confInfo)
