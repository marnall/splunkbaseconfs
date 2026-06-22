from typing import Dict
import os
import sys
import json
import logging as logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication  # type: ignore
from splunk.clilib.bundle_paths import make_splunkhome_path  # type: ignore

from secret_manager import SecretManager
import handler_utils as utils

logger.basicConfig(
    level=logger.INFO,
    format="%(asctime)s %(levelname)s  %(message)s",
    datefmt="%m-%d-%Y %H:%M:%S.000 %z",
    filename=make_splunkhome_path(["var", "log", "splunk", "cribl-decrypt.log"]),
    filemode="a",
)

APP_NAME = "TA-cribl-decrypt"

logger.info("New persistent connection started for Cribl-Decrypt (key deleter).")

# https://stackoverflow.com/questions/60207053/creating-a-rest-handler-for-any-of-splunks-rest-endpoints
if sys.platform == "win32":
    import msvcrt

    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class Delete(PersistentServerConnectionApplication):
    """
    Received an ID for a specific key to issue a delete request.
    """

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string: bytes):
        """
        Handles the incoming request from the REST app server.

        Args:
            in_string (bytes): The request from the REST app server.

        Returns:
            str: JSON response from this endpoint.
        """
        try:
            request_data: Dict[str, str] = json.loads(in_string)

            session_key: str = utils.get_session_token(request_data)
            secret_manager = SecretManager(session_key)

            key_id: str = None
            for field in request_data["form"]:
                if field[0] == "key":
                    key_id = field[1]

            if key_id is not None:
                if secret_manager.key_exists(key_id):
                    response = secret_manager.delete_key(key_id)
                    logger.info(f"Deleted key {key_id}")
                    if response.status == 200:
                        return utils.wrap_response(
                            f"Successfully deleted key {key_id}.",
                            200,
                        )
                    else:
                        return utils.wrap_response(
                            f"Failed to delete key {key_id}. Messsage {response.messages}",
                            response.status,
                        )
                else:
                    logger.error("The provided key ID was not found in the secret store.")
                    return utils.wrap_response(
                        "The provided key ID was not found in the secret store.",
                        404,
                    )

            else:
                logger.error("No valid key was passed to delete.")
                return utils.wrap_response(
                    "No valid key was passed to delete.",
                    400,
                )
        except Exception as e:
            logger.exception("Exception deleting key.")
            return utils.wrap_response(
                f"Delete failed. {str(e)}",
                500,
            )
