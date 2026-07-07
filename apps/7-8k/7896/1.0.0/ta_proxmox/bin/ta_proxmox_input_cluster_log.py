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

    checkpoint_name = "cluster_log_" + input_name.split("/")[-1] + "_last_start_time"
    checkpoint = prepare_checkpoint(session_key)
    last_checkpoint = get_checkpoint(logger, checkpoint, checkpoint_name)

    max_seen_time = last_checkpoint

    proxmox = create_proxmox_api(logger, session_key, input_item)

    node_lookup = cluster_lookup(proxmox)

    cluster_logs_raw = proxmox.cluster.log.get(max=max_fetch)

    cluster_logs = []

    for log_entry in cluster_logs_raw:
        task_time = log_entry["time"]
        if task_time > last_checkpoint:
            raw_string = json.dumps(log_entry, sort_keys=True)
            event_hash = hashlib.md5(raw_string.encode("utf-8")).hexdigest()
            log_entry["event_hash"] = event_hash

            node_info = node_lookup.get(log_entry["node"], get_empty_cluster_lockup())
            enriched = {**log_entry, **node_info}
            cluster_logs.append(enriched)

            max_seen_time = max(max_seen_time, task_time)

    if max_seen_time > last_checkpoint:
        checkpoint.update(checkpoint_name, max_seen_time)
        logger.debug(f"Updated checkpoint to {max_seen_time}")

    return cluster_logs


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

            sourcetype = "pve:cluster:log"

            write_events(logger, data, event_writer, input_name, input_item, sourcetype)

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "proxmox_input_cluster_log",
                              msg_before="Exception raised while ingesting data for Node Status Input: ")
