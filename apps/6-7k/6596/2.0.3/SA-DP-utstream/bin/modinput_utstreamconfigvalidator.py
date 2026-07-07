#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: modinput_utstreamconfigvalidator.py - Version 2.0.3
# Copyright (c) Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import *
from splunklib import client

from utstream_template.factory_dataset import DatasetFactory

from utstream.service_cribl_replay import CriblReplayService
from utstream_template.factory_logger import Logger


from _env import CONFIG

class UTStreamConfigValidator(Script):

    # Constants: so static that not kept in a config file
    app_owner = "admin"

    # Changed
    changed = False

    def get_scheme(self):
        scheme = Scheme("UTStream Config Validator")
        scheme.description = ("Ensures that the host has active inputs.conf configuration based on the config found in utstream_inputs.conf")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        return scheme


    def validate_input(self, validation_definition):
        pass # passing as there is no input provided to this modular input


    def stream_events(self, inputs, ew):
        try:
            global logger
            self.uuid = str(uuid.uuid4())
            logger = Logger( logname="modinput", uuid=self.uuid )

            # Get server instance
            self.input_name, self.input_items = inputs.inputs.popitem()
            self.session_key = self._input_definition.metadata["session_key"]

            dataset_factory = DatasetFactory( uuid=self.uuid, client=client, session_key = self.session_key, user="splunk-system-user" )
            self.dataset_confs = dataset_factory.get_dataset_service( "confs" )

            # Run license checks
            
            cribl_replay_service = CriblReplayService( uuid=self.uuid, client=client, session_key=self.session_key, user="splunk-system-user" )
            # Get instances runs __license_ok which will update the license status
            replay, license_ok = cribl_replay_service.get_replays()

            self.utstream_inputs_collection = self.dataset_confs.get("utstream_inputs")
            self.inputs_collection_list = self.dataset_confs.get("inputs")
            self.inputs_collection = self.dataset_confs.splunk_service.confs["inputs"]

            if license_ok:
                logger.info("action=\"license_ok\"")
                # Get all Stanzas from utstream_inputs.conf
                for utstream_inputs_stanza in self.utstream_inputs_collection:
                    logger.debug(f"action=read_utstream_inputs_stanza,stanza_name={utstream_inputs_stanza.name},stanza_content={utstream_inputs_stanza.content}")

                    # Replay stanza to inputs.conf
                    input_stanza = next((x for x in self.inputs_collection_list if x.name == f"modinput_criblreplay://{utstream_inputs_stanza.name}"), None)
                    if input_stanza is None:
                        self._create_replay_stanza(utstream_inputs_stanza)
                    else:
                        self._check_replay_stanza(utstream_inputs_stanza, input_stanza)

                    # Discovery stanza to inputs.conf
                    input_stanza = next((x for x in self.inputs_collection_list if x.name == f"modinput_cribldiscovery://{utstream_inputs_stanza.name}"), None)
                    if input_stanza is None:
                        self._create_discovery_stanza(utstream_inputs_stanza)
                    else:
                        self._check_discovery_stanza(utstream_inputs_stanza, input_stanza)
            else:
                logger.info("action=\"license_not_ok\"")
                # Only handle one stanza and remove all others
                sorted_utstream_inputs_collection = sorted(self.utstream_inputs_collection, key=lambda x: x.name)
                if len(sorted_utstream_inputs_collection) > 0:
                    logger.info("action=\"excess_stanzas_found\"")

                    utstream_inputs_stanza = sorted_utstream_inputs_collection[0]
                    logger.info(f"action=\"excess_stanzas_found\",stanza_name=\"{utstream_inputs_stanza.name}\",result=\"handle\"")
                    # Replay stanza to inputs.conf
                    input_stanza = next((x for x in self.inputs_collection_list if x.name == f"modinput_criblreplay://{utstream_inputs_stanza.name}"), None)
                    if input_stanza is None:
                        self._create_replay_stanza(utstream_inputs_stanza)
                    else:
                        self._check_replay_stanza(utstream_inputs_stanza, input_stanza)

                    # Discovery stanza to inputs.conf
                    input_stanza = next((x for x in self.inputs_collection_list if x.name == f"modinput_cribldiscovery://{utstream_inputs_stanza.name}"), None)
                    if input_stanza is None:
                        self._create_discovery_stanza(utstream_inputs_stanza)
                    else:
                        self._check_discovery_stanza(utstream_inputs_stanza, input_stanza)

                    # Remove all other stanzas
                    for input_stanza in self.inputs_collection_list:
                        if input_stanza.name.startswith("modinput_cribldiscovery://") or input_stanza.name.startswith("modinput_criblreplay://"):
                            if input_stanza.name != f"modinput_cribldiscovery://{utstream_inputs_stanza.name}" and input_stanza.name != f"modinput_criblreplay://{utstream_inputs_stanza.name}":
                                logger.info(f"action=\"excess_stanzas_found\",stanza_name=\"{input_stanza.name}\",result=\"remove\"")
                                self._remove_discovery_stanza(input_stanza)
                                self._remove_replay_stanza(input_stanza) 


            # Go over all stanzas in inputs.conf and remove any that are not in utstream_inputs.conf
            self.utstream_inputs_collection = self.dataset_confs.get("utstream_inputs")
            utstream_inputs_names = []
            
            for utstream_inputs_stanza in self.utstream_inputs_collection:
                utstream_inputs_names.append(f"modinput_cribldiscovery://{utstream_inputs_stanza.name}")
                utstream_inputs_names.append(f"modinput_criblreplay://{utstream_inputs_stanza.name}")

            for input_stanza in self.inputs_collection_list:
                if input_stanza.name.startswith("modinput_cribldiscovery://") or input_stanza.name.startswith("modinput_criblreplay://"):
                    if input_stanza.name not in utstream_inputs_names:
                        self._remove_discovery_stanza(input_stanza)
                        self._remove_replay_stanza(input_stanza)

            if self.changed:
                applications = self.dataset_confs.splunk_service.apps
                app = applications[CONFIG["APP_NAME"]]
                app.reload()

        except Exception as e:
            logger.exception("action=\"utstreamconfigvalidator\",error=\"exception\",exception_type={},exception_message={}".format(type(e).__name__, str(e)))
            raise e


    def _create_discovery_stanza(self, utstream_inputs_stanza):
        self.inputs_collection.create(
            name=f"modinput_cribldiscovery://{utstream_inputs_stanza.name}",
            interval=utstream_inputs_stanza.content["interval"],
            cribl_collector=utstream_inputs_stanza.content["cribl_collector"],
            cribl_instance=utstream_inputs_stanza.content["cribl_instance"],
            cribl_max_jobs=utstream_inputs_stanza.content["cribl_max_jobs"],
            cribl_inform_user=utstream_inputs_stanza.content["cribl_inform_user"],
        )
        stanza = self.inputs_collection[f"modinput_cribldiscovery://{utstream_inputs_stanza.name}"]
        logger.info(f"action=create_discovery_stanza,stanza_name={stanza.name},stanza_content={stanza.content}")
        self.changed = True


    def _check_discovery_stanza(self, utstream_inputs_stanza, input_stanza):
        keys = ["interval", "cribl_collector", "cribl_instance", "cribl_max_jobs", "cribl_inform_user"]
        updated_keys = []
        for key in keys:
            if key not in input_stanza:
                updated_keys.append({"key": key, "old_value": "", "new_value": utstream_inputs_stanza.content[key]})
                input_stanza.update(**{key: utstream_inputs_stanza.content[key]})
            elif input_stanza[key] != utstream_inputs_stanza.content[key]:
                updated_keys.append({"key": key, "old_value": input_stanza[key], "new_value": utstream_inputs_stanza.content[key]})
                input_stanza.update(**{key: utstream_inputs_stanza.content[key]})
        if len(updated_keys) > 0:
            self.changed = True
            logger.info(f"action=update_discovery_stanza,stanza_name={input_stanza.name},updated_keys={updated_keys}")
        else:
            logger.debug(f"action=update_discovery_stanza,stanza_name={input_stanza.name},updated_keys=[]")
        

    def _remove_discovery_stanza(self, utstream_inputs_stanza):
        if utstream_inputs_stanza.name in self.inputs_collection:
            self.inputs_collection.delete(utstream_inputs_stanza.name)
            logger.info(f"action=remove_discovery_stanza,stanza_name={utstream_inputs_stanza.name}")
        self.changed = True


    def _create_replay_stanza(self, utstream_inputs_stanza):
        self.inputs_collection.create(
            name=f"modinput_criblreplay://{utstream_inputs_stanza.name}",
            interval=utstream_inputs_stanza.content["interval"],
            cribl_collector=utstream_inputs_stanza.content["cribl_collector"],
            cribl_instance=utstream_inputs_stanza.content["cribl_instance"],
            cribl_max_jobs=utstream_inputs_stanza.content["cribl_max_jobs"],
            cribl_destination=utstream_inputs_stanza.content["cribl_destination"],
            cribl_max_optimize=utstream_inputs_stanza.content["cribl_max_optimize"],
            cribl_pipeline=utstream_inputs_stanza.content["cribl_pipeline"],
            cribl_use_optimized=utstream_inputs_stanza.content["cribl_use_optimized"],
            cribl_inform_user=utstream_inputs_stanza.content["cribl_inform_user"],
        )
        stanza = self.inputs_collection[f"modinput_criblreplay://{utstream_inputs_stanza.name}"]
        logger.info(f"action=create_replay_stanza,stanza_name={stanza.name},stanza_content={stanza.content}")
        self.changed = True


    def _check_replay_stanza(self, utstream_inputs_stanza, input_stanza):
        keys = ["interval", "cribl_collector", "cribl_instance", "cribl_max_jobs", "cribl_destination", "cribl_max_optimize", "cribl_pipeline", "cribl_use_optimized", "cribl_inform_user"]
        updated_keys = []
        for key in keys:
            if key not in input_stanza:
                updated_keys.append({"key": key, "old_value": "", "new_value": utstream_inputs_stanza.content[key]})
                input_stanza.update(**{key: utstream_inputs_stanza.content[key]})
            elif input_stanza[key] != utstream_inputs_stanza.content[key]:
                updated_keys.append({"key": key, "old_value": input_stanza[key], "new_value": utstream_inputs_stanza.content[key]})
                input_stanza.update(**{key: utstream_inputs_stanza.content[key]})
        if len(updated_keys) > 0:
            self.changed = True
            logger.info(f"action=update_discovery_stanza,stanza_name={input_stanza.name},updated_keys={updated_keys}")
        else:
            logger.debug(f"action=update_discovery_stanza,stanza_name={input_stanza.name},updated_keys=[]")


    def _remove_replay_stanza(self, utstream_inputs_stanza):
        if utstream_inputs_stanza.name in self.inputs_collection:
            self.inputs_collection.delete(utstream_inputs_stanza.name)
            logger.info(f"action=remove_replay_stanza,stanza_name={utstream_inputs_stanza.name}")
        self.changed = True


if __name__ == "__main__":
    exitcode = UTStreamConfigValidator().run(sys.argv)
    sys.exit(exitcode)
