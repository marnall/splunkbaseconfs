import json
import logging
import time

from proxmoxer import ProxmoxAPI
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer, KVStoreCheckpointer

ADDON_NAME = "ta_proxmox"
CONF_NAME_ACCOUNT = "account"
CONF_NAME_PVESERVER = "pveserver"
CONF_NAME_SETTINGS = "settings"
CONF_SEPERATOR = "_"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME}_{input_name}")


def get_config_property(
        session_key: str, conf_name: str, realm_suffix: str, item_name: str, property_name: str
):
    """
    General helper function to fetch a configuration property from a specific configuration file.
    """
    cfm = conf_manager.ConfManager(
        session_key, ADDON_NAME, realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/{realm_suffix}"
    )
    conf_file = cfm.get_conf(conf_name)
    return conf_file.get(item_name).get(property_name)


# Fetches the username for a specified account.
def get_account_user(session_key: str, account_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        item_name=account_name,
        property_name="acc_user",
    )


# Fetches the password for a specified account.
def get_account_password(session_key: str, account_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        item_name=account_name,
        property_name="acc_password",
    )

# Get account type to switch betweeen user/pass to api token
def get_account_type(session_key: str, account_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        item_name=account_name,
        property_name="acc_authtype",
    )

# Get account api token id
def get_account_api_name(session_key: str, account_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        item_name=account_name,
        property_name="acc_apiname",
    )

# Get account api key
def get_account_api_key(session_key: str, account_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_ACCOUNT,
        item_name=account_name,
        property_name="acc_apikey",
    )

# Retrieves the Proxmox VE server hostname for a particular PVE server.
def get_pve_hostname(session_key: str, pve_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_PVESERVER,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_PVESERVER,
        item_name=pve_name,
        property_name="pve_host",
    )


# Retrieves the Proxmox VE server port for a given PVE server.
def get_pve_port(session_key: str, pve_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_PVESERVER,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_PVESERVER,
        item_name=pve_name,
        property_name="pve_port",
    )


# Retrieves the Proxmox VE server ssl verify for a given PVE server.
def get_ssl_verify(session_key: str, pve_name: str):
    return get_config_property(
        session_key=session_key,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_PVESERVER,
        realm_suffix="conf-" + ADDON_NAME + CONF_SEPERATOR + CONF_NAME_PVESERVER,
        item_name=pve_name,
        property_name="ssl_verify",
    )

# Retrieves the Log Level for a given inputs.
def get_log_level(session_key: str, logger):
    return conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=ADDON_NAME,
        conf_name=ADDON_NAME + CONF_SEPERATOR + CONF_NAME_SETTINGS,
    )

# Prepare checkpoint object
def prepare_checkpoint(session_key: str) -> KVStoreCheckpointer:
    return checkpointer.KVStoreCheckpointer(
        collection_name="checkpoints",
        session_key=session_key,
        app=ADDON_NAME
    )

# Get saved checkpoint
def get_checkpoint(logger: logging.Logger, checkpoint: KVStoreCheckpointer, checkpoint_name: str) -> str:
    last_checkpoint = checkpoint.get(checkpoint_name)
    if last_checkpoint is None:
        last_checkpoint = int(time.time()) - 300
    logger.debug("last_checkpoint: " + str(last_checkpoint))
    return last_checkpoint


def create_proxmox_api(logger: logging.Logger, session_key: str, input_item) -> ProxmoxAPI:
    """
    A helper to initialize a `ProxmoxAPI` object by passing in server details like
    """
    account_type = get_account_type(session_key, input_item.get(CONF_NAME_ACCOUNT))
    logger.debug("account_type: " + str(account_type))

    user = get_account_user(session_key, input_item.get(CONF_NAME_ACCOUNT))
    logger.debug("user: " + str(user))

    pvehost = get_pve_hostname(session_key, input_item.get(CONF_NAME_PVESERVER))
    logger.debug("pvehost: " + str(pvehost))

    pveport : int = int(get_pve_port(session_key, input_item.get(CONF_NAME_PVESERVER)))
    logger.debug("pveport: " + str(pveport))

    ssl_verify : bool = bool(int(get_ssl_verify(session_key, input_item.get(CONF_NAME_PVESERVER))))
    logger.debug("ssl_verify: " + str(ssl_verify))

    if account_type == "usr":
        password = get_account_password(session_key, input_item.get(CONF_NAME_ACCOUNT))

        return ProxmoxAPI(
            host=pvehost,
            user=user,
            password=password,
            port=pveport,
            verify_ssl=ssl_verify
        )

    if account_type == "api":
        api_name = get_account_api_name(session_key, input_item.get(CONF_NAME_ACCOUNT))
        logger.debug("api_name: " + str(api_name))
        api_key = get_account_api_key(session_key, input_item.get(CONF_NAME_ACCOUNT))

        return ProxmoxAPI(
            host=pvehost,
            user=user,
            token_name=api_name,
            token_value=api_key,
            port=pveport,
            verify_ssl=ssl_verify
        )

def write_events(logger, data, event_writer, input_name, input_item, sourcetype):
    for line in data:
        event_writer.write_event(
            smi.Event(
                data=json.dumps(line, ensure_ascii=False, default=str),
                index=input_item.get("index"),
                sourcetype=sourcetype,
            )
        )
    log.events_ingested(
        logger,
        input_name,
        sourcetype,
        len(data),
        input_item.get("index"),
        account=input_item.get(CONF_NAME_ACCOUNT),
    )

def cluster_lookup(proxmox: ProxmoxAPI):
    cluster_status = proxmox.cluster.status.get()
    cluster_name = next(
        (item.get("name") for item in cluster_status if item.get("type") == "cluster"),
        "standalone"
    )

    return {
        node["name"]: {
            "cluster": cluster_name,
            "node_name": node["name"],
            "node_ip": node["ip"],
            "node_id": node["id"]
        }
        for node in cluster_status if node.get("type") == "node"
    }

def get_empty_cluster_lockup():
    return {
                "cluster": "",
                "node_name": "",
                "node_ip": "",
                "node_id": ""
            }