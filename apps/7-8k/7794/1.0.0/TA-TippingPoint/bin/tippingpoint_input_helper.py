import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi


ADDON_NAME = "TA-TippingPoint"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def validate_input(definition: smi.ValidationDefinition):
    return