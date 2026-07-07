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
        os.environ["SPLUNK_HOME"] + "/var/log/splunk/get_se_groups.log",
        maxBytes=25000000,
        backupCount=5,
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger(logging.INFO)


class GetGroupList(PersistentServerConnectionApplication):
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
            api_url = f"https://{host}/v1/groups"
            headers = {
                "Content-Type": "application/json",
            }
            params = {
                "limit": 500,
                "offset": 0,
            }

            logger.info("Starting API session...")

            groups = []

            with requests.Session() as session:
                session.auth = requests.auth.HTTPBasicAuth(client_id, api_key)
                while True:
                    response = session.get(url=api_url, params=params, headers=headers)
                    status_code = response.status_code

                    if status_code != 200:
                        logger.info(f"{response.text}")
                        api_response = {
                            "payload": response.text,
                            "status": status_code,
                            "headers": headers,
                        }

                        return api_response

                    items = response.json().get("data")

                    if len(items) == 0:
                        api_response = {
                            "payload": json.dumps(groups),
                            "status": status_code,
                            "headers": headers,
                        }
                        logger.info(f"Done API call. Status={status_code}.")

                        return api_response

                    groups.extend(items)
                    params["offset"] += params["limit"]

        except Exception as e:
            logger.info(
                f"Exception occurred. "
                f"Error_code={type(e).__name__} "
                f"Error_message={e.__repr__()}"
            )

            e_response = {"payload": e.__repr__(), "status": 500, "headers": headers}

            return e_response
