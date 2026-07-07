import sys
from pathlib import Path

BIN_PATH = Path(__file__).parent
if BIN_PATH.as_posix() not in sys.path:
    sys.path.insert(0, BIN_PATH.as_posix())
LIBS_PATH = BIN_PATH.parent.joinpath("lib")
sys.path.insert(0, LIBS_PATH.joinpath("common").as_posix())

if sys.platform == "win32":
    sys.path.insert(0, LIBS_PATH.joinpath("windows").as_posix())
else:
    sys.path.insert(0, LIBS_PATH.joinpath("linux").as_posix())

import asyncio
import base64
import json
import logging
import os

from logging_splunk import set_logger
from splunk import ResourceNotFound
from splunk.rest import simpleRequest
from utils_splunk import LastDataTimeHandlerSplunk, TransformerDetectionsSplunk

from integration.main import ServiceClient
from integration.models import Config, DataSource

set_logger()


class ServiceClientSplunk(ServiceClient):
    def __init__(self) -> None:
        super().__init__()

    def _get_config(self) -> Config:
        return Config("Splunk", "0.3.0")

    def _get_transformer_data(self) -> TransformerDetectionsSplunk:
        return TransformerDetectionsSplunk(self.env_vars)

    def _get_last_data_time_handler(self, data_source: DataSource) -> LastDataTimeHandlerSplunk:
        return LastDataTimeHandlerSplunk(data_source, self.env_vars.interval)

    def _validate_if_run_incidents(self) -> bool:
        return False


def main() -> None:
    session_key = sys.stdin.read()
    try:
        _, content = simpleRequest(
            "/services/storage/passwords/:eset:",
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            method="GET",
            raiseAllErrors=True,
        )
    except ResourceNotFound:
        logging.info("Credentials not stored yet")
    else:
        logging.info("Getting detections")
        data = json.loads(content.decode("utf-8"))
        json_b64_data = data["entry"][0]["content"]["clear_password"]

        config = json.loads(base64.b64decode(json_b64_data).decode())

        os.environ["USERNAME_INTEGRATION"] = config["username"]
        os.environ["PASSWORD_INTEGRATION"] = config["password"]
        os.environ["INSTANCE_REGION"] = config["region"].lower()
        os.environ["INTERVAL"] = "5"
        os.environ["EP_INSTANCE"] = "yes" if config["epc"] else "no"
        os.environ["EI_INSTANCE"] = "yes" if config["eic"] else "no"
        os.environ["ECOS_INSTANCE"] = "no"  # ecos is not supported yet

        service_client = ServiceClientSplunk()
        try:
            asyncio.run(service_client.run())
        except Exception as e:
            logging.exception(e)


if __name__ == "__main__":
    main()
