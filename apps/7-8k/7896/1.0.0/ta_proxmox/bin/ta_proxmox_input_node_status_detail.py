import logging

import import_declare_test  # type: ignore
from solnlib import conf_manager, log  # type: ignore
from splunklib import modularinput as smi  # type: ignore

from ta_proxmox_helper import logger_for_input, create_proxmox_api, get_log_level, write_events, cluster_lookup, \
    get_empty_cluster_lockup


# Get Data
def get_data_from_api(logger: logging.Logger, session_key: str, input_name: str, input_item: dict):
    logger.info("Getting data from Proxmox Node API")

    node_status = []

    proxmox = create_proxmox_api(logger, session_key, input_item)

    node_lookup = cluster_lookup(proxmox)

    for node in proxmox.nodes.get():
        node_info = node_lookup.get(node["node"], get_empty_cluster_lockup())

        status : dict = proxmox.nodes(node["node"]).status.get()

        status["loadavg"] = dict(zip(["min_1", "min_5", "min_15"], status["loadavg"]))
        enriched = {**status, **node_info}
        node_status.append(enriched)

    return node_status


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

            sourcetype = "pve:node:status:detail"

            write_events(logger, data, event_writer, input_name, input_item, sourcetype)

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "proxmox_input_node_status_detail",
                              msg_before="Exception raised while ingesting data for Node Status Input: ")
