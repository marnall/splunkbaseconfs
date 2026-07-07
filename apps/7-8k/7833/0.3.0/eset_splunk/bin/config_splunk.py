import sys
from pathlib import Path

BIN_PATH = Path(__file__).parent
if BIN_PATH.as_posix() not in sys.path:
    sys.path.insert(0, BIN_PATH.as_posix())

import base64
import json
import logging

from logging_splunk import set_logger
from splunk import ResourceNotFound
from splunk.rest import BaseRestHandler, simpleRequest

set_logger()

KEY_NAME = "eset"
BASE_SECRET_ENDPOINT = "/services/storage/passwords"


class ConfigHandler(BaseRestHandler):
    def handle_GET(self) -> None:
        logging.info("Get config")

        try:
            _, content = simpleRequest(
                f"{BASE_SECRET_ENDPOINT}/:{KEY_NAME}:",
                sessionKey=self.sessionKey,
                getargs={"output_mode": "json"},
                method="GET",
                raiseAllErrors=True,
            )
        except ResourceNotFound:
            logging.warning("Credentials not stored yet")
            self.response.write(
                json.dumps({"username": "", "password": "", "region": "EU", "epc": False, "eic": False})
            )
        else:
            data = json.loads(content.decode("utf-8"))
            json_b64_data = data["entry"][0]["content"]["clear_password"]

            self.response.setHeader("content-type", "application/json")
            self.response.write(base64.b64decode(json_b64_data).decode("utf-8"))

        self.response.setStatus(200)
        self.response.setHeader("content-type", "application/json")

    def handle_POST(self) -> None:
        logging.info("Save config")

        json_data = self.request["payload"]

        logging.info("Try to delete previous record")
        try:
            simpleRequest(f"{BASE_SECRET_ENDPOINT}/:{KEY_NAME}:", sessionKey=self.sessionKey, method="DELETE")
        except ResourceNotFound:
            logging.info("Nothing to delete")

        try:
            simpleRequest(
                BASE_SECRET_ENDPOINT,
                sessionKey=self.sessionKey,
                method="POST",
                postargs={
                    "name": KEY_NAME,
                    "password": base64.b64encode(json_data.encode("utf-8")).decode("utf-8"),
                },
                raiseAllErrors=True,
            )

        except Exception as e:
            logging.exception(e)
            self.response.setStatus(500)
            self.response.write(json.dumps({"message": "Save was not successful"}))
        else:
            self.response.setStatus(200)
            self.response.write(json.dumps({"message": "Saved"}))

        self.response.setHeader("content-type", "application/json")
