#!/usr/bin/env python3
#
# File: modinput_elasticspl_housekeeping.py - Version 1.3.3
# Copyright (c) Datapunctum AG 2026-2-11
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Splunk Enterprise SDK
import splunklib.client as client
from splunklib.modularinput import Script, Scheme


from elasticspl_template.factory_logger import Logger
from elasticspl_template.factory_dataset import DatasetFactory
from elasticspl.service_elastic_instance import ElasticInstanceService


class ElasticSPLHousekeeping(Script):
    def get_scheme(self):
        scheme = Scheme("ElasticSPL Housekeeping")

        scheme.description = "ElasticSPL Housekeeping"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        return scheme

    def validate_input(self, validation_definition):
        pass  # passing as there is no input provided to this modular input

    def stream_events(self, inputs, ew):
        self.uuid = str(uuid.uuid4())
        session_key = self._input_definition.metadata["session_key"]
        self.logger = Logger(logname="modinput", uuid=self.uuid)

        try:
            elastic_instance_service = ElasticInstanceService(uuid=self.uuid, client=client, session_key=session_key, user="splunk-system-user")
            message_roles = elastic_instance_service.message_roles

            # Get instances runs license_ok which will update the license status
            license_state, available_nodes = elastic_instance_service.license_ok()
            self.logger.debug({"action": "license_fetch", "status": "success", "license_state": license_state, "available_nodes": available_nodes})

            dataset_factory = DatasetFactory(uuid=self.uuid, client=client, session_key=session_key, user="splunk-system-user")
            dataset_search = dataset_factory.get_dataset_service("search")
            dataset_messages = dataset_factory.get_dataset_service("messages")

            node_search = '| tstats dc(PREFIX(node=)) AS node_count where index=_internal sourcetype="elasticspl:helper" TERM(node) TERM(connect) TERM(200)'
            node_count = 0

            for result in dataset_search.run_blocking_search(search=node_search, earliest="-24h@h", latest="now"):
                self.logger.debug({"action": "node_count", "status": "success", "node_count": result["node_count"]})
                node_count = result["node_count"]

            if int(node_count) > int(available_nodes) and int(available_nodes) != -1:
                self.logger.warn({"action": "node_count_violation", "status": "failed", "node_count": node_count, "available_nodes": available_nodes})
                dataset_messages.insert(
                    name="elastic_spl_node_violation",
                    value="ElasticSPL detected more distinct nodes used than licensed. [https://datapunctum.atlassian.net/servicedesk/customer/portal/3 Contact Datapunctum] (sales@datapunctum.com) for an icreased license.",
                    severity="error",
                    roles=message_roles,
                )

        except Exception as e:
            self.logger.exception("Failed to run modular input")


if __name__ == "__main__":
    exitcode = ElasticSPLHousekeeping().run(sys.argv)
    sys.exit(exitcode)
