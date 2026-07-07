#!/usr/bin/env python

import sys
import os
import configparser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)
import splunklib.client as client
from solnlib import conf_manager, log
from splunk_http_event_collector import http_event_collector

ADDON_NAME = "ta_send_to_hec_command"


@Configuration(distributed=False)
class SendToHECCommand(StreamingCommand):
    """Sending Splunk Search Results as messages to a 2nd Splunk index via HEC.

    ##Syntax

    <SPL Search> | sendtohec traget=<Target Name>

    ##Description

    This command iterates over results of a Splunk search query,
    and sends the results one by one to a HEC of another Splunk instance (target).

    """

    # require hec targets from the user
    target = Option(
        doc="""
            **Syntax:** **target=***"<Target Name>"*
            **Description:** Name of the topic """,
        require=True,
        validate=validators.Fieldname(),
    )

    def setup_logger(self):
        return log.Logs().get_logger(f"{ADDON_NAME.lower()}")

    def get_session_key(self):
        return self._metadata.searchinfo.session_key

    def get_config(self, target_name):
        current_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        config = configparser.ConfigParser()
        config.read(
            os.path.join(
                current_directory[: len(current_directory) - 4],
                "local",
                "ta_send_to_hec_command_target.conf",
            )
        )
        if len(config.sections()) == 0:
            raise Exception(
                "Could not locate ta_send_to_hec_command_target.conf relative to the location of send_to_hec.py: "
                + current_directory
            )
        elif target_name not in config.sections():
            raise Exception(
                f"Missing {target_name} stanza from ta_send_to_hec_command_target.conf in local filesystem"
            )
        else:
            return dict(config.items(target_name))

    def remove_prefix(self, url, prefix):
        return url.replace(prefix, "")

    def get_and_verify_server_name(self, url, logger):
        ssl_enabed = None
        server_name = None
        ssl_enabed = True
        if url.startswith("https:"):
            server_name = self.remove_prefix(url, "https://")
        elif url.startswith("http:"):
            msg = "Connections via HTTP scheme are not allowed due to increased security risks."
            logger.error(msg)
            raise Exception(msg)

        if server_name.endswith("/"):
            server_name = server_name.rstrip(server_name[-1])

        return server_name, ssl_enabed

    def retrieve_token(self, target):
        cfm = conf_manager.ConfManager(
            self.get_session_key(),
            ADDON_NAME,
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_send_to_hec_command_target",
        )
        account_conf_file = cfm.get_conf("ta_send_to_hec_command_target")
        return account_conf_file.get(target).get("hec_token")

    def construct_headers(self, token):
        return {"Authorization": f"Splunk {token}"}

    def get_target_properties(self, target_name):
        config = self.get_config(target_name)
        url = config.get("base_url")
        port = config.get("port")
        if not port:
            port = "8088"
        hec_token = self.retrieve_token(target_name)
        return url, port, hec_token

    def get_fields_to_include(self, target_name):
        config = self.get_config(target_name)
        fields_to_include = config.get("fields_to_include")
        return fields_to_include.split("~") if fields_to_include else None

    def add_fields_to_event(self, event, data, fields_to_include):
        for field in fields_to_include:
            if field == "_time" and event.get("_time"):
                data["time"] = event["_time"]
            elif field == "index" and event.get("index"):
                data["index"] = event["index"]
            elif field == "sourcetype" and event.get("sourcetype"):
                data["sourcetype"] = event["sourcetype"]
            elif field == "source" and event.get("source"):
                data["source"] = event["source"]
            elif field == "host" and event.get("host"):
                data["host"] = event["host"]
        return data

    def stream(self, events):
        logger = self.setup_logger()
        hec_url, hec_port, hec_token = self.get_target_properties(self.target)

        if hec_url is None or hec_token is None:
            raise ValueError(
                "No HEC Base URL or HEC Token found. Did you configure a target?"
            )

        try:
            server_name, ssl_enabed = self.get_and_verify_server_name(hec_url, logger)
            fields_to_include = self.get_fields_to_include(self.target)

            logger.info(
                f"Starting to process events with the following configuration. Server Name: {server_name}, SSL Enabled: {ssl_enabed}, HEC Port: {hec_port}"
            )

            hec_event = http_event_collector(
                http_event_server=server_name,
                token=hec_token,
                logger=logger,
                http_event_port=hec_port,
                http_event_server_ssl=ssl_enabed,
            )

            is_connected = hec_event.check_connectivity()
            if not is_connected:
                msg = "The connection to the target could not be established. Please check if it is correctly configured in the app configurations page."
                logger.error(msg)
                raise Exception(msg)
            logger.info("Connection to target successfully established.")

            event_count = 0
            for event in events:
                event = dict(event)
                data = None
                if event.get("_raw"):
                    data = {"event": event["_raw"]}
                else:
                    data = {"event": event}
                if fields_to_include:
                    data = self.add_fields_to_event(event, data, fields_to_include)
                hec_event.batchEvent(data)
                logger.debug(f"Processed event: {data}")
                event_count += 1
                yield event

            hec_event.flushBatch()
        except Exception as e:
            raise e

        logger.info(
            f"sendtohec command terminated. {event_count} events have been processed."
        )


dispatch(SendToHECCommand, sys.argv, sys.stdin, sys.stdout, __name__)
