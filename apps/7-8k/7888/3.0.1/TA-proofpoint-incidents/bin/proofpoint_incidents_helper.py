import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi

import im_proofpoint_incidents as input_module
from dateutil import parser


ADDON_NAME = "TA-proofpoint-incidents"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def validate_input(definition: smi.ValidationDefinition):
    start_date = definition.parameters.get('start_date', None)
    if start_date is not None:
        try:
            parser.parse(start_date)
        except Exception as e:
            error_message = f"Invalid date format specified for 'Start Date={start_date}'"
            raise ValueError(error_message) 
    
    pass


def stream_events(self,inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="ta-proofpoint-incidents_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
            self.logger = logger
            self.session_key = session_key
            input_module.collect_events(self, input_name, input_item, event_writer) 

        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")
