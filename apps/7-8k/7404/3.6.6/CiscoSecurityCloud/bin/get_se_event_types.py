import json  # noqa: I001
import logging
import logging.handlers
import os
from urllib.parse import parse_qs

import requests

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
except ModuleNotFoundError:

    class PersistentServerConnectionApplication:
        pass


def setup_logger(level):
    logger = logging.getLogger("custom_rest")
    logger.propagate = False  # Prevent the log messages from being duplicated
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        os.environ["SPLUNK_HOME"] + "/var/log/splunk/get_se_event_types.log",
        maxBytes=25000000,
        backupCount=5,
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger(logging.INFO)


class GetEventTypeList(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):

        front_request = json.loads(in_string.decode("utf-8"))

        payload_str = front_request["payload"]

        payload_dict = parse_qs(payload_str)
        host = payload_dict.get("api_host")[0]
        client_id = payload_dict.get("client_id")[0]
        api_key = payload_dict.get("api_key")[0]

        logger.info(f"Starting API call to the host: {host}")

        try:
            api_url = f"https://{host}/v1/event_types"
            headers = {
                "Content-Type": "application/json",
            }

            logger.info("Starting API session...")

            with requests.Session() as session:
                session.auth = requests.auth.HTTPBasicAuth(client_id, api_key)
                response = session.get(url=api_url, headers=headers)
                status_code = response.status_code

                if status_code != 200:
                    logger.info(f"{response.text}")
                    api_response = {
                        "payload": response.text,
                        "status": status_code,
                        "headers": headers,
                    }

                    return api_response

                event_types = response.json().get("data")

            logger.info(f"Done API call. Status={status_code}.")
            return {
                "payload": json.dumps(event_types),
                "status": status_code,
                "headers": {"Content-Type": "application/json"},
            }
        except Exception as e:
            logger.info(
                f"Exception occurred. "
                f"Error_code={type(e).__name__} "
                f"Error_message={e.__repr__()}"
            )

            e_response = {"payload": e.__repr__(), "status": 500, "headers": headers}

            return e_response
