"""Utility module for the XM Cyber Splunk app.

This module contains various utility functions used throughout the XM Cyber Splunk app
for tasks such as handling configurations, managing checkpoints, and processing data.
"""
import os
import json
import import_declare_test    # noqa: F401
from requests.compat import quote_plus
from import_declare_test import ta_name, ta_prefix
import splunk.rest as rest
from solnlib.utils import is_true
from solnlib import conf_manager
from xmcyber_constants import AUTH_TYPE_OAUTH, OAUTH_PREFIX, PAGE_SIZE, AUTH_ERROR_MESSAGE, VRM_PAGE_SIZE
from solnlib.modular_input import checkpointer


def get_proxy_info(session_key, logger):
    """Get proxy information.

    Args:
        session_key: Splunk session key
        logger: Logger Object

    Returns:
        dictionary containing proxy details or None
    """
    proxy_info_dict = {}
    # Retrieve proxy configurations
    _, content = rest.simpleRequest(
        f"/servicesNS/nobody/{ta_name}/{ta_prefix}_settings/proxy",
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json", "--cred--": "1"},
        raiseAllErrors=True,
    )
    # Parse response
    content = json.loads(content)

    for item in content["entry"]:
        proxy_info_dict = item["content"]
        break

    # Return None if proxy_enabled is false or proxy hostname or proxy port is not found
    if (
        not is_true(proxy_info_dict.get("proxy_enabled"))
        or not proxy_info_dict.get("proxy_port")    # noqa: W503
        or not proxy_info_dict.get("proxy_url")    # noqa: W503
    ):
        logger.info("Proxy is disabled")
        return None

    proxy_user_pass = ""
    # Quote username and password if available
    if proxy_info_dict.get("proxy_username") and proxy_info_dict.get("proxy_password"):
        proxy_username = quote_plus(proxy_info_dict["proxy_username"], safe="")
        proxy_password = quote_plus(proxy_info_dict["proxy_password"], safe="")
        proxy_user_pass = f"{proxy_username}:{proxy_password}@"

    logger.info("Proxy is enabled")

    # Prepare proxy string
    proxy = "{proxy_type}://{proxy_user_pass}{proxy_host}:{proxy_port}".format(
        proxy_type=proxy_info_dict["proxy_type"],
        proxy_user_pass=proxy_user_pass,
        proxy_host=proxy_info_dict["proxy_url"],
        proxy_port=proxy_info_dict["proxy_port"],
    )
    proxies = {
        "http": proxy,
        "https": proxy,
    }

    return proxies


def get_account(account_name, session_key):
    """
    Get credentials from API Query.

    Args:
        account_name: Account name to fetch credentials for.
        session_key: Splunk session key

    Returns:
        Dictionary of given account details.
    """
    _, content = rest.simpleRequest(
        f"/servicesNS/nobody/{ta_name}/{ta_prefix}_account/{account_name}",
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json", "--cred--": "1"},
        raiseAllErrors=True,
    )
    content = json.loads(content)
    return content["entry"][0]["content"]


def get_version():
    """Get the current version of the XM Cyber Splunk app."""
    try:
        version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")
        with open(version_file, "r") as vf:
            return vf.readline().strip()
    except Exception:
        return "unknown"


def get_xmcyber_session_headers(account):
    """
    Get the headers for XM Cyber API session.

    Args:
        account: Account to use to set Session headers.

    Returns:
        Dictionary of headers.
    """
    headers = {
        "Content-type": "application/json",
        "accept": "application/json",
        "X-XMCYBER-CONNECTOR-NAME-VERSION": f"Splunk-v{get_version()}",
    }

    # OAuth-only: do not allow falling back to legacy x-api-key auth headers.
    if account.get("auth_type") != AUTH_TYPE_OAUTH:
        raise ValueError(
            "Account authentication type is not supported. Please reconfigure the account to use OAuth."
        )

    access_token = account.get("access_token")
    if not access_token:
        raise ValueError(
            "OAuth account is missing an access token. Please reconfigure the account."
        )

    headers["Authorization"] = f"{OAUTH_PREFIX} {access_token}"
    return headers


def update_access_token(session_key, account_name, api_key, new_access_token, new_refresh_token):
    """
    Update the token values in the account configuration file.

    Args:
        session_key: Session Key.
        account_name: Account Name.
        api_key: API Key.
        new_access_token: Regenerated access token.
        new_access_token: Regenerated refresh token.
    """
    account_cfm = conf_manager.ConfManager(
        session_key,
        ta_name,
        realm=f"__REST_CREDENTIAL__#{ta_name}#configs/conf-{ta_prefix.lower()}_account"
    )
    encrypt_fields = {
        "api_key": api_key,
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }
    account_conf = account_cfm.get_conf(f"{ta_prefix.lower()}_account", refresh=True)
    account_conf.update(
        account_name, encrypt_fields, encrypt_fields.keys()
    )


def get_parameters(input_type, inputs):
    """
    Get parameter details for making API call.

    Args:
        input_type: Input type.
        inputs: Input details.

    Returns:
        Dictionary of XMCyber API parameters.
    """
    parameters = {}
    if input_type == "security_risk_score":
        parameters["timeId"] = inputs.get("time_id")
    elif input_type in ("audit_trail"):
        parameters["timeId"] = inputs.get("time_id")
        parameters["page"] = 1
        parameters["pageSize"] = PAGE_SIZE
    elif input_type in ("all_entities", "findings_exposures", "scenario"):
        parameters["page"] = 1
        parameters["pageSize"] = PAGE_SIZE
    elif input_type == "vrm_data":
        parameters["pageSize"] = VRM_PAGE_SIZE

    return parameters


def get_checkpoint(session_key, checkpoint_key, logger):
    """
    Get KV Store checkpoint for the provided key.

    Args:
        session_key: Session Key.
        checkpoint_key: Checkpoint Key value.
        logger: Logger object.

    Returns:
        Checkpoint Value.
    """
    logger.info(f"input_name={checkpoint_key} Getting the checkpoint.")
    checkpoint_value = None
    try:
        checkpoint_object = checkpointer.KVStoreCheckpointer(
            f"{checkpoint_key}_checkpointer", session_key, ta_name
        )
        checkpoint_value = checkpoint_object.get(checkpoint_key)
        logger.info(f"input_name={checkpoint_key} Successfully retrieved the checkpoint.")
    except Exception as e:
        logger.error(
            f"input_name={checkpoint_key} Error occured while getting the checkpoint value: {e}"
        )
        raise e
    return checkpoint_value


def update_checkpoint(session_key, checkpoint_key, checkpoint_value, logger):
    """
    Update the KV Store checkpoint with the key value provided.

    Args:
        session_key: Session Key.
        checkpoint_key: Checkpoint Key value.
        checkpoint_value: Checkpoint value.
        logger: Logger object.

    Returns:
        Checkpoint Value.
    """
    logger.info(f"input_name={checkpoint_key} Updating checkpoint.")
    try:
        checkpoint_object = checkpointer.KVStoreCheckpointer(
            f"{checkpoint_key}_checkpointer", session_key, ta_name
        )
        checkpoint_object.update(checkpoint_key, checkpoint_value)
        logger.debug(f"input_name={checkpoint_key} Checkpoint value {checkpoint_value}.")
        logger.info(f"input_name={checkpoint_key} Checkpoint updated successfully.")
    except Exception as e:
        logger.error(
            f"input_name={checkpoint_key}  Error occured while updating the checkpoint: {e}"
        )
        raise e


def delete_checkpoint(session_key, checkpoint_key):
    """
    Delete the KV Store checkpoint for the given key.

    Args:
        session_key: Splunk session key
        checkpoint_key: Key of the checkpoint to be deleted
    """
    kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
        f"{checkpoint_key}_checkpointer",
        session_key,
        ta_name,
    )
    kvstore_checkpointer.delete(checkpoint_key)


def extract_input_context(inputs):
    """Extract common input parameters from the inputs object.

    This function extracts the session key, input name, input parameters,
    account, account details, auth type, and normalized input name that
    are commonly used across all helper modules.

    Args:
        inputs: Input object from the modular input containing metadata and inputs

    Returns:
        dict: Dictionary containing:
            - session_key: Splunk session key
            - input_name: Full input name
            - input_params: Input parameters dictionary
            - account: Account name
            - account_details: Account details dictionary
            - auth_type: Authentication type
            - normalized_input_name: Normalized input name (last part of input_name)
    """
    # Get the session key from metadata
    session_key = inputs.metadata.get("session_key")

    # Get the input parameters
    input_name = list(inputs.inputs.keys())[0]
    input_params = inputs.inputs[input_name]

    # Get the account name from input parameters
    account = input_params.get("account")

    # Get account details including auth_type
    account_details = get_account(account, session_key)
    auth_type = account_details.get("auth_type")
    normalized_input_name = input_name.split("/")[-1]

    return {
        "session_key": session_key,
        "input_name": input_name,
        "input_params": input_params,
        "account": account,
        "account_details": account_details,
        "auth_type": auth_type,
        "normalized_input_name": normalized_input_name,
    }


def validate_oauth_authentication(definition, service_name, logger):
    """Validate that the account uses OAuth authentication.

    Args:
        definition: Input definition object containing metadata and parameters
        service_name: Name of the service being validated
        logger: Logger instance for the service

    Returns:
        dict: Account details if validation passes

    Raises:
        ValueError: If account uses basic authentication
    """
    session_key = definition.metadata.get("session_key")
    account = definition.parameters.get("account")
    account_details = get_account(account, session_key)

    if account_details.get("auth_type") == "basic":
        error_msg = AUTH_ERROR_MESSAGE.format(service_name=service_name, account=account)
        logger.error(f"input_name={definition.metadata.get('name')} {error_msg}")
        raise ValueError(error_msg)

    return account_details
