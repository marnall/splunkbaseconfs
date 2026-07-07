import datetime
import logging
import re

import import_declare_test # type: ignore
from solnlib import conf_manager, log  # type: ignore
from splunklib import modularinput as smi  # type: ignore

from ta_proxmox_helper import get_log_level, create_proxmox_api, logger_for_input, write_events, cluster_lookup, \
    get_empty_cluster_lockup


# Get Data
def get_data_from_api(logger: logging.Logger, session_key: str, input_name: str, input_item: dict):
    logger.info("Getting data from Proxmox Node API")

    interval = int(input_item.get("interval"))
    since_time = (datetime.datetime.now() - datetime.timedelta(seconds=interval)).strftime('%Y-%m-%d %H:%M:%S')

    # Regex pattern to match log components
    log_pattern = re.compile(
        r'^(?P<timestamp>\w{3} \d{2} \d{2}:\d{2}:\d{2}) (?P<host>\S+) (?P<service>\S+): (?P<message>.*)$'
    )
    parsed_logs = []

    proxmox = create_proxmox_api(logger, session_key, input_item)
    node_lookup = cluster_lookup(proxmox)

    for node in proxmox.nodes.get():

        node_syslog_trunc = proxmox.nodes(node["node"]).syslog.get(since = since_time)
        node_info = node_lookup.get(node["node"], get_empty_cluster_lockup())

        for node_syslog in node_syslog_trunc:
            line = node_syslog["t"]

            match = log_pattern.match(line)
            if match:
                parsed_fields = match.groupdict()
                enriched = {**parsed_fields, **node_info}
                parsed_logs.append(enriched)
            else:
                if line.strip()!= "-- No entries --":
                    logger.error("NO MATCH for line: " + line)

    return parsed_logs


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

            sourcetype = "pve:node:syslog"

            write_events(logger, data, event_writer, input_name, input_item, sourcetype)

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "proxmox_input_node_syslog",
                              msg_before="Exception raised while ingesting data for Node Status Input: ")
