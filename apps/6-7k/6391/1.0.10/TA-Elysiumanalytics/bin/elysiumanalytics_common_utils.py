import ta_elysiumanalytics_declare  # noqa: F401
import json
import requests
import elysiumanalytics_const as const
from log_manager import setup_logging

import splunk.rest as rest
from six.moves.urllib.parse import quote
from splunk.clilib import cli_common as cli
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true

_LOGGER = setup_logging("elysiumanalytics_utils")
APP_NAME = const.APP_NAME


def get_elysiumanalytics_configs():
    
    
    configs = cli.getConfStanza("ta_elysiumanalytics_settings", "elysiumanalytics_credentials")
    return configs

def get_elysiumanalytics_oauth_configs():
    
    
    configs = cli.getConfStanza("access_token", "oauth_credentials")
    
    return configs    


def get_elysiumanalytics_clear_token(session_key):
    
    
    manager = CredentialManager(
        session_key,
        app=APP_NAME,
        realm="__REST_CREDENTIAL__#{0}#{1}".format(APP_NAME, "configs/conf-ta_elysiumanalytics_settings"),
    )

    access_token = None

    tokens_list = []

    try:
        snowflake_refresh_token = json.loads(manager.get_password("elysiumanalytics_credentials")).get(
            "snowflake_refresh_token"
        )
        client_id = json.loads(manager.get_password("elysiumanalytics_credentials")).get(
            "client_id"
        )
        client_secret = json.loads(manager.get_password("elysiumanalytics_credentials")).get(
            "client_secret"
        )
        tokens_list.append(snowflake_refresh_token)
        tokens_list.append(client_id)
        tokens_list.append(client_secret)

    except Exception as e:
        _LOGGER.error(str(e))


    return tokens_list



def update_kv_store_collection(splunkd_uri, kv_collection_name, session_key, kv_log_info):
    
    header = {
        "Authorization": "Bearer {}".format(session_key),
        "Content-Type": "application/json",
    }

    # Add the log of record into the KV Store
    _LOGGER.info(
        "Adding the command log info to KV Store. Command Log Info: {}".format(kv_log_info)
    )

    kv_update_url = "{}/servicesNS/nobody/{}/storage/collections/data/{}".format(
        splunkd_uri,
        const.APP_NAME,
        kv_collection_name,
    )

    _LOGGER.info(
        "Executing REST call, URL: {}, Payload: {}.".format(kv_update_url, str(kv_log_info))
    )
    response = requests.post(
        kv_update_url, headers=header, data=json.dumps(kv_log_info), verify=True
    )

    if response.status_code in {200, 201}:
        _LOGGER.info("KV Store updated successfully.")
        kv_log_info.update({"kv_status": "KV Store updated successfully"})
    else:
        _LOGGER.info("Error occurred while updating KV Store.")
        kv_log_info.update({"kv_status": "Error occurred while updating KV Store"})

    return kv_log_info


def format_to_json_parameters(params):
    
    output_json = {}

    try:
        if params:
            lst = params.split("||")
            for item in lst:
                kv = item.split("=")
                output_json[kv[0].strip()] = kv[1].strip()
    except Exception:
        raise Exception(
            "Invalid format for parameter notebook_params. Provide the value in 'param1=val1||param2=val2' format."
        )

    return output_json

