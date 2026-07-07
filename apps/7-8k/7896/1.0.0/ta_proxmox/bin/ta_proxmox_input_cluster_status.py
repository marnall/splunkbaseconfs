import logging
from datetime import datetime

import import_declare_test # type: ignore
from solnlib import conf_manager, log # type: ignore
from splunklib import modularinput as smi # type: ignore

from ta_proxmox_helper import logger_for_input, get_log_level, create_proxmox_api, write_events


#Get Data
def get_data_from_api(logger: logging.Logger, session_key: str, input_name: str, input_item: dict):
    logger.info("Getting data from Proxmox Cluster API")

    proxmox = create_proxmox_api(logger, session_key, input_item)

    cluster_status = proxmox.cluster.status.get()

    cluster_info = next(
        (item for item in cluster_status if item.get("type") == "cluster"),
        {"name": "standalone"}
    )
    cluster_name = cluster_info["name"]

    node_data = [
        {
            "cluster": cluster_name,
            "node_name": node["name"],
            "node_ip": node["ip"],
        }
        for node in cluster_status if node.get("type") == "node"
    ]

    return node_data


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = get_log_level(session_key, logger)
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            data = get_data_from_api(logger, session_key, input_name, input_item)

            sourcetype = "pve:cluster:status"

            write_events(logger, data, event_writer, input_name, input_item, sourcetype)

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "proxmox_input_cluster_status", msg_before="Exception raised while ingesting data for Cluster Status Input: ")
