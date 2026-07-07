import hashlib
import json
import logging

import import_declare_test  # type: ignore
from solnlib import conf_manager, log  # type: ignore

from splunklib import modularinput as smi  # type: ignore

from ta_proxmox_helper import get_log_level, create_proxmox_api, logger_for_input, write_events, prepare_checkpoint, \
    get_checkpoint, cluster_lookup, get_empty_cluster_lockup


# Get Data
def get_data_from_api(logger: logging.Logger, session_key: str, input_name: str, input_item: dict):
    logger.info("Getting data from Proxmox Node API")

    max_fetch = input_item.get("max_fetch")

    checkpoint_name = "node_tasks_" + input_name.split("/")[-1] + "_last_start_time"
    checkpoint = prepare_checkpoint(session_key)
    last_checkpoint = get_checkpoint(logger, checkpoint, checkpoint_name)

    max_seen_time = last_checkpoint

    proxmox = create_proxmox_api(logger, session_key, input_item)

    node_lookup = cluster_lookup(proxmox)

    node_tasks = []
    for node in proxmox.nodes.get():
        node_task_trunk = proxmox.nodes(node["node"]).tasks.get(limit=max_fetch)

        node_info = node_lookup.get(node["node"], get_empty_cluster_lockup())

        for node_task in node_task_trunk:
            task_time = node_task["starttime"]
            if task_time > last_checkpoint:
                raw_string = json.dumps(node_task, sort_keys=True)
                event_hash = hashlib.md5(raw_string.encode("utf-8")).hexdigest()
                node_task["event_hash"] = event_hash

                enriched = {**node_task, **node_info}
                node_tasks.append(enriched)

                max_seen_time = max(max_seen_time, task_time)

    if max_seen_time > last_checkpoint:
        checkpoint.update(checkpoint_name, max_seen_time)
        logger.debug(f"Updated checkpoint to {max_seen_time}")

    return node_tasks


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

            sourcetype = "pve:node:tasks"

            write_events(logger, data, event_writer, input_name, input_item, sourcetype)

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "proxmox_input_node_tasks",
                              msg_before="Exception raised while ingesting data for Node Status Input: ")
