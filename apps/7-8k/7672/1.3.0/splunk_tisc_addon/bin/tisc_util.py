import traceback
from typing import Dict
from solnlib import conf_manager
APP_NAME = "splunk_tisc_addon"

from typing import Dict, Optional
import traceback
import logging

def get_account_details(session_key: str, account_name: str) -> Optional[Dict[str, str]]:
    """
    Returns username, password, and instance_url for a specific account_name.

    :param session_key: session key for particular modular input.
    :param account_name: account name configured in the addon.
    :return: Dictionary containing username, password, and instance_url if found, else None.
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_tisc_addon_account",
        )
        account_conf_file = cfm.get_conf("splunk_tisc_addon_account")

        account_details = account_conf_file.get(account_name)
        if account_details is None:
            logging.warning(f"Account '{account_name}' not found in configuration.")
            return None

        return {
            "username": account_details.get("username"),
            "password": account_details.get("password"),
            "instance_url": account_details.get("instance_url"),
        }

    except KeyError as e:
        logging.error(f"KeyError while retrieving account details for '{account_name}': {e}")
    except Exception as e:
        logging.error(f"An error occurred while retrieving account details: {e}")
        traceback.print_exc()

    return None
