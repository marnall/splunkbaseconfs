from collections import defaultdict
from json import loads
from logging import Logger
from pathlib import Path
from typing import Optional, Any
from os import environ

from solnlib.conf_manager import ConfManager
from solnlib.splunk_rest_client import SplunkRestClient
from solnlib.modular_input.checkpointer import KVStoreCheckpointer, FileCheckpointer

splunk_home = environ["SPLUNK_HOME"]


CHANNEL_ID = "7d274d05e666cfa5a95aac2182a142b7"
ADDON_NAME = "cybersixgill_actionable_alerts"


def form_args_to_dict(raw_payload: Optional[list[tuple[str, Any]]]) -> dict:
    """Parse Raw payload to dict.

    Args:
        raw_payload (Optional[List[Tuple[str, Any]]]): Payload format send by Splunk

    Returns:
        Dict: Python dictionary
    """
    if not raw_payload:
        return {}
    # return {item[0]: item[1] for item in raw_payload}
    return dict(item for item in raw_payload)


def form_args_to_dict_with_multi_value(items):
    if not items:
        return {}
    final_dict = defaultdict(list)
    for key, value in items:
        final_dict[key].append(value)

    return dict(final_dict)


def get_account_api_key(session_key: str, logger):
    cfm = ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-cybersixgill_actionable_alerts_account",
    )
    logger.info("cfm created")
    account_conf_file = cfm.get_conf("cybersixgill_actionable_alerts_account")
    logger.info("account_conf_file")
    cybersixgill_client_id = cybersixgill_client_secret = organization_id = None
    for _, creds in account_conf_file.get_all().items():
        cybersixgill_client_id = creds.get("cybersixgill_client_id", "")
        cybersixgill_client_secret = creds.get("cybersixgill_secret_id", "")
        organization_id = creds.get("cybersixgill_organization_id")
        if all([cybersixgill_client_id, cybersixgill_client_secret]):
            break
    # logger.info(f"{organization_id}, {cybersixgill_client_id}, {cybersixgill_client_secret}")
    return cybersixgill_client_id, cybersixgill_client_secret, organization_id


# Base class for PersistentServerConnectionApplication

def load_common_attributes(instance, in_string: str, logger: Logger):
    """Assign common attributes to subclass instance of PersistentServerConnectionApplication.

    Args:
        instance : Sub class instance of PersistentServerConnectionApplication
        in_string (str): JSON payload as string
        logger (Logger): RotatingFileHandler Logger instance
    """
    instance.request_payload = loads(in_string)
    logger.info("Assigning common attributes to sub-class instance of PersistentServerConnectionApplication")
    splunk_auth_token = instance.request_payload.get("session", {}).get("authtoken")
    instance.splunk_client = SplunkRestClient(
        session_key=splunk_auth_token,
        app=ADDON_NAME
    )
    logger.info("Creating")
    instance.client_id, instance.client_secret, instance.org_id = get_account_api_key(splunk_auth_token, logger)
    logger.info("fetched creds")
    instance.method = instance.request_payload.get("method", "").upper()

def migrate_checkpointer_from_file_to_kvstore(session_key: str, key_name: str) -> KVStoreCheckpointer:
    # check if file checkpointer exists
    value = file_chk_pt = None
    checkpoint_path = Path(splunk_home).absolute() / f"var/lib/splunk/modinputs/{ADDON_NAME}"
    # if yes, extract value
    if checkpoint_path.exists():
        file_chk_pt = FileCheckpointer(checkpoint_dir=str(checkpoint_path))
        value = file_chk_pt.get(key_name)
    kv_chk_pt = KVStoreCheckpointer(f"{ADDON_NAME}_checkpoints", session_key, ADDON_NAME)
    value_from_kv = kv_chk_pt.get(key_name)
    # Move value to kv checkpointer and delete file checkpointer
    if value is not None and value_from_kv is None:
        kv_chk_pt.update(key_name, value)
        # TODO: uncomment this later
        file_chk_pt.delete(key_name)
    return kv_chk_pt

# def process_json_reader(reader: JSONResultsReader) -> Optional[Union[List[Union[dict, Mess]]]]:
#     results = []
#     for result in reader:
#         if any([isinstance(result, item) for item in [dict, Message]]):
#             results.append(result)
#     if len(results) == 1:
#         return results[0]
#     return results
