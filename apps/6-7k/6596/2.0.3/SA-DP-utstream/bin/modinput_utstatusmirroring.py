#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: modinput_utstatusmirroring.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import *
from splunklib import client

from utstream_template.factory_dataset import DatasetFactory
from utstream_template.service_proxy import ProxyService

from utstream.service_cribl_instance import CriblInstanceService
from utstream.helper_cribl_instance_interaction import HelperCriblInstanceInteraction

from utstream_template.factory_logger import Logger

class UTStatusMirroring(Script):

    # Constants: so static that not kept in a config file
    app_owner = "admin"

    # Cribl object
    cribl = None

    def get_scheme(self):

        scheme = Scheme("UTStream Status Mirroring")
        scheme.description = "Modular input to mirror input and output health from Cribl to Splunk"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        return scheme

    def validate_input(self, validation_definition):
        pass # passing as there is no input provided to this modular input

    def stream_events(self, inputs, events):
        
        try:
            self.uuid = str(uuid.uuid4())

            logger = Logger( logname="modinput", uuid=self.uuid )

            # Parse user provided inputs
            dataset_factory = DatasetFactory( uuid=self.uuid, client=client, session_key = self._input_definition.metadata["session_key"] )
            self.dataset_messages = dataset_factory.get_dataset_service( "messages" )
            self.dataset_environment = dataset_factory.get_dataset_service( "environment" )

            # Check if supposed to run on this host
            if not self.dataset_environment.get_shc_captain_or_standalone():
                logger.debug("action=\"applicability_check\",result=\"false\",reason=\"not_shc_captain\"")
                exit(0)
            logger.info("action=\"applicability_check\",result=\"true\",reason=\"standalone_or_captain\"")

            cribl_instance_service = CriblInstanceService( uuid=self.uuid, client=client, session_key=self._input_definition.metadata["session_key"], user="splunk-system-user" )
            proxy_service = ProxyService( uuid=self.uuid, client=client, session_key=self._input_definition.metadata["session_key"], user="splunk-system-user" )

            # Get configuration from Splunk API
            cribl_instances = cribl_instance_service.get_instances()

            # Get all messages from UTStream
            utstream_messages = [message for message in self.dataset_messages.list_all() if message.name.startswith("UTStreamStatusMirroring: ")]
            active_messages = []

            # Loop through all cribl_instances and create CriblInstance objects
            for cribl_instance in cribl_instances:

                logger.debug(f"action=\"instance_check\",instance=\"{cribl_instance['name']}\"")

                cribl = cribl_instance_service.get_instance( instance_name=cribl_instance["name"] )
                cribl_interaction_helper = HelperCriblInstanceInteraction(instance=cribl, uuid=self.uuid, proxy=proxy_service.get_httpx_info())

                inputs = cribl_interaction_helper.get_inputs()
                outputs = cribl_interaction_helper.get_outputs()

                # Loop through all inputs and outputs and write health status != Green to Splunk
                for input in inputs:
                    if "health" in input and input["health"] != 0:
                        self.dataset_messages.insert(
                            name=f"UTStreamStatusMirroring: {cribl.name}::{input['input']}",
                            value=f"UTStream: source \"{input['input']}\" unhealthy for \"{cribl.name}\"",
                            severity="error",
                            roles=["utstream_admin", "admin"]
                        )
                        active_messages.append(f"UTStreamStatusMirroring: {cribl.name}::{input['input']}")
                        logger.error(f"action=\"input_health\",result=\"unhealthy\",instance=\"{cribl.name}\",input=\"{input['input']}\"")
                    else:
                        logger.debug(f"action=\"input_health\",result=\"healthy\",instance=\"{cribl.name}\",input=\"{input['input']}\"")

                for output in outputs:
                    if "health" in output and output["health"] != 0:
                        self.dataset_messages.insert(
                            name=f"UTStreamStatusMirroring: {cribl.name}::{output['output']}",
                            value=f"UTStream: destination \"{output['output']}\" unhealthy for \"{cribl.name}\"",
                            severity="error",
                            roles=["utstream_admin", "admin"]
                        )
                        active_messages.append(f"UTStreamStatusMirroring: {cribl.name}::{output['output']}")
                        logger.info(f"action=\"output_health\",result=\"unhealthy\",instance=\"{cribl.name}\",output=\"{output['output']}\"")
                    else:
                        logger.debug(f"action=\"output_health\",result=\"healthy\",instance=\"{cribl.name}\",output=\"{output['output']}\"")

                # Check if all workers are healthy
                healthy, healthy_workers, unhealthy_workers, workers = cribl_interaction_helper.check_worker_health()
                if healthy is False:
                    for worker in unhealthy_workers:
                        self.dataset_messages.insert(
                            name=f"UTStreamStatusMirroring: {cribl.name}::{worker}",
                            value=f"UTStream: worker \"{worker}\" unhealthy for \"{cribl.name}\"",
                            severity="error",
                            roles=["utstream_admin", "admin"]
                        )
                        logger.info(f"action=\"worker_health\",result=\"unhealthy\",instance=\"{cribl.name}\",worker=\"{worker}\"")

                if len(workers) > 0:
                    cribl.cribl_stored_workers = workers
                    cribl_instance_service.update_instance(cribl.get_private_dict())
                
            # Loop through all messages and delete if not in active_messages
            remediated_messages = [message for message in utstream_messages if message.name not in active_messages]

            for message in remediated_messages:
                try:
                    self.dataset_messages.remove_by_id(message.name)
                    logger.info(f"action=\"message_remediated\",message=\"{message.name}\"")
                except Exception as e:
                    logger.error(f"action=\"message_remediation_failure\",message=\"{message.name}\",error=\"{e}\"")

        except Exception as e:
            logger.exception("action=\"utstatusmirroring\",status=\"error\",result=\"{}\"".format(str(e)))
            

if __name__ == "__main__":
    exitcode = UTStatusMirroring().run(sys.argv)
    sys.exit(exitcode)
