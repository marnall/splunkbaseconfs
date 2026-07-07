import logging

import import_declare_test  # type: ignore
from solnlib import conf_manager, log  # type: ignore
from splunklib import modularinput as smi  # type: ignore

from ta_proxmox_helper import get_log_level, create_proxmox_api, logger_for_input, write_events, cluster_lookup, \
    get_empty_cluster_lockup


# Get Data
def get_data_from_api(logger: logging.Logger, session_key: str, input_name: str, input_item: dict):
    logger.info("Getting data from Proxmox Node API")

    proxmox = create_proxmox_api(logger, session_key, input_item)

    node_lookup = cluster_lookup(proxmox)

    resources = proxmox.cluster.resources.get()
    cluster_resources = []

    for resource in resources:
        node_info = node_lookup.get(resource.get("node"), get_empty_cluster_lockup())
        enriched = {**resource, **node_info}
        cluster_resources.append(enriched)

    return cluster_resources


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

            sourcetype = "pve:cluster:resources"

            write_events(logger, data, event_writer, input_name, input_item, sourcetype)

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "proxmox_input_cluster_resources",
                              msg_before="Exception raised while ingesting data for Node Status Input: ")
