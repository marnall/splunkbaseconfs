import json
import requests
import import_declare_test

import traceback
from solnlib.modular_input import checkpointer
from infoblox_helpers.constants import APP_NAME, INTERNAL_VERIFY_SSL
from solnlib.splunkenv import get_splunkd_uri


def get_checkpoint(key, session_key, sub_checkpoint, logger):
    """Get checkpoint."""
    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            key, session_key, APP_NAME
        )
        if checkpoint_collection.get(key) and checkpoint_collection.get(key).get(sub_checkpoint):
            return checkpoint_collection.get(key).get(sub_checkpoint)
        else:
            return None
    except Exception:
        logger.error("message=checkpoint_error |"
                     " Error occured while Getting Checkpoint.\n{}".format(traceback.format_exc()))
        raise


def save_checkpoint(key, session_key, sub_checkpoint, value, logger):
    """Get checkpoint."""
    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            key, session_key, APP_NAME
        )
        ckpt_dict = checkpoint_collection.get(key) or {}
        ckpt_dict[sub_checkpoint] = value
        checkpoint_collection.update(key, ckpt_dict)
    except Exception:
        logger.error("message=checkpoint_error |"
                     " Error occured while Updating Checkpoint.\n{}".format(traceback.format_exc()))
        raise


def disable_input(input_name, session_key, logger):
    """Disable Input."""
    try:
        input_name = input_name.split("://")
        logger.info("Disabling input: {}".format(input_name[1]))
        body = {"disabled": 1}

        headers = {
            "Authorization": "Splunk {}".format(session_key),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        requests.post(
            "{}/servicesNS/nobody/{}/{}_{}/{}".format(
                get_splunkd_uri(),
                APP_NAME,
                APP_NAME,
                input_name[0],
                input_name[1]
            ),
            headers=headers,
            data=body,
            verify=INTERNAL_VERIFY_SSL
        )
    except Exception:
        logger.error("message=disable_input_error |"
                     " Error occured while disabling input.\n{}".format(traceback.format_exc()))
        raise
