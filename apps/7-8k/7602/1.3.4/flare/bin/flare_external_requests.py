import sys


if sys.version_info < (3, 9):
    sys.exit("Error: This application requires Python 3.9 or higher.")


import json
import os
import splunk

from urllib import parse


sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vendor"))
from data_store import ConfigDataStore
from flare import FlareAPI
from logger import Logger


class FlareValidateApiKey(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        logger = Logger(class_name=__file__)
        payload = self.request["payload"]
        params = parse.parse_qs(payload)

        if "apiKey" not in params:
            raise Exception("API Key is required")

        flare_api = FlareAPI(api_key=params["apiKey"][0], logger=logger)
        flare_api.fetch_api_key_validation()
        self.response.setHeader("Content-Type", "application/json")
        self.response.write(json.dumps({}))


class FlareUserTenants(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        logger = Logger(class_name=__file__)
        payload = self.request["payload"]
        params = parse.parse_qs(payload)

        if "apiKey" not in params:
            raise Exception("API Key is required")

        flare_api = FlareAPI(api_key=params["apiKey"][0], logger=logger)
        response = flare_api.fetch_tenants()
        response_json = response.json()
        logger.debug(f"FlareUserTenants: {response_json}")
        self.response.setHeader("Content-Type", "application/json")
        self.response.write(json.dumps(response_json))


class FlareSeverityFilters(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        logger = Logger(class_name=__file__)
        payload = self.request["payload"]
        params = parse.parse_qs(payload)

        if "apiKey" not in params:
            raise Exception("API Key is required")

        flare_api = FlareAPI(api_key=params["apiKey"][0], logger=logger)
        response = flare_api.fetch_filters_severity()
        response_json = response.json()
        logger.debug(f"FlareSeverityFilters: {response_json}")
        self.response.setHeader("Content-Type", "application/json")
        self.response.write(json.dumps(response_json))


class FlareSourceTypeFilters(splunk.rest.BaseRestHandler):
    def handle_POST(self) -> None:
        logger = Logger(class_name=__file__)
        payload = self.request["payload"]
        params = parse.parse_qs(payload)

        if "apiKey" not in params:
            raise Exception("API Key is required")

        flare_api = FlareAPI(api_key=params["apiKey"][0], logger=logger)
        response = flare_api.fetch_filters_source_type()
        response_json = response.json()
        logger.debug(f"FlareSourceTypeFilters: {response_json}")
        self.response.setHeader("Content-Type", "application/json")
        self.response.write(json.dumps(response_json))


class FlareIngestionStatus(splunk.rest.BaseRestHandler):
    def handle_GET(self) -> None:
        logger = Logger(class_name=__file__)

        data_store = ConfigDataStore()
        last_fetched_timestamp = data_store.get_last_fetch()

        status_resp = {
            "last_fetched_at": last_fetched_timestamp.isoformat()
            if last_fetched_timestamp is not None
            else None
        }
        logger.debug(f"FlareIngestionStatus: {status_resp}")
        self.response.setHeader("Content-Type", "application/json")
        self.response.write(json.dumps(status_resp))
