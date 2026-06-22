import base64
import json
import os
import sys
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from key import Key, KeyBuilder

APP_NAME = "TA-cribl-decrypt"
BYTES_SEP = b"\r\n"
TAR_HEADER_SIZE = 512


def get_session_token(request_data: Dict[str, any]) -> str:
    """
    Pull the session key information out of the request data coming from the app server

    Args:
        request_data (Dict[str, any]): The Splunk request information

    Returns:
        str: The auth token associated with the session
    """
    return request_data["session"]["authtoken"]


def get_keys(keys_bytes: bytes) -> List[Key]:
    """
    Process the key bundle JSON coming from Stream

    Args:
        keys_bytes (bytes): The content of keys.json

    Returns:
        List[Key]: List of the built key objects
    """
    keys: List[Dict[str, any]] = []
    return_keys: List[Key] = []

    keys = [json.loads(x) for x in keys_bytes.split(b"\n") if x]

    for key in keys:
        key_builder = (
            KeyBuilder()
            .set_id(key["keyId"])
            .set_description(key["description"])
            .set_algorithm(key["algorithm"])
            .set_cipher_key(base64.b64decode(key["cipherKey"]))
            .set_use_iv(key["useIV"])
            .set_key_class(key["keyclass"])
            .set_created(key["created"])
            .set_expires(key["expires"])
            .set_kms(key["kms"])
        )

        if "ivSize" in key:
            key_builder.set_iv_size(key["ivSize"])

        return_keys.append(key_builder.build())

    return return_keys


def wrap_response(message: str, status: int) -> str:
    """Consistent generation of output expected for key management .

    Args:
        message (str): The message to return.
        status (int): The return code to pass.

    Returns:
        str: An object containing the result message and status code of the request serialized to a JSON string.
    """
    return json.dumps(
        {
            "payload": {"message": message, "status": status},
        }
    )
