import os
import sys

from SplunkSettings import SplunkSettings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from SplunkLogging import setup_logging

logger = setup_logging("varonis_modular_input.log")

from splunklib.modularinput import *
import splunklib.client as client


class VaronisModularInputBase(Script):

    def __init__(self):
        super().__init__()
        self.logger = logger

    def get_service(self):
        service = None
        if hasattr(self, '_input_definition'):
            session_key = self._input_definition.metadata["session_key"]
            service = client.connect(token=session_key)
        return service

    def get_input_name(self):
        name = None
        if hasattr(self, 'inputs'):
            for input_name, input_item in list(self.inputs.inputs.items()):
                kind, name = input_name.split("://")
        else:
            name = 'local_run'
        return name

    def get_input_param(self, key, default=None):
        value = None
        if hasattr(self, 'inputs'):
            for input_name, input_item in list(self.inputs.inputs.items()):
                value = input_item.get(key)
        else:
            if hasattr(self, key):
                value = self[key]

        if value is None:
            value = default

        return value

    def get_app_params(self):
        service = self.get_service()
        return SplunkSettings.get_app_settings(service)

    def get_checkpoint_file_location(self):
        if hasattr(self, 'inputs'):
            input_name = self.get_input_name()
            checkpoint_file_location = os.path.join(self._input_definition.metadata["checkpoint_dir"], input_name)
        else:
            checkpoint_file_location = os.path.join(os.path.abspath(os.getcwd()), "checkpoint")

        logger.debug(f'[{self.get_input_name()}][get_checkpoint_file_location] checkpoint_file_location = {checkpoint_file_location}')
        return checkpoint_file_location

    def stream_events(self, inputs, ew):
        pass

    def get_scheme(self):
        pass

