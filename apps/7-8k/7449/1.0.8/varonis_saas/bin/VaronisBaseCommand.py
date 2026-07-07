import os
import sys

from Constants import app_name, THREAT_MODEL_ENUM_ID
from SplunkSettings import SplunkSettings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from HttpClient import HttpClient
from splunklib.searchcommands import StreamingCommand, Configuration, Option, GeneratingCommand
import splunklib.client as client

from SplunkLogging import setup_logging

log = setup_logging("varonis_command.log")


class VaronisBaseCommand(StreamingCommand):

    def __init__(self):
        super().__init__()
        self.api_key = None
        self.url = None
        self.client = None
        self.log = log

    def get_service(self):
        service = None
        if hasattr(self, '_metadata') and self._metadata:
            session_key = self._metadata.searchinfo.session_key
            service = client.connect(token=session_key)
        return service

    def get_client(self):
        service = self.get_service()
        if service:
            url, api_key, log_level = SplunkSettings.get_app_settings(service)
            self.log.debug('end of get_app_settings')
            return HttpClient(url, api_key)
        else:
            return HttpClient(self.url, self.api_key)

    def get_threat_model_ids(self, threat_model_names):
        if threat_model_names:
            threat_model_enum_id = THREAT_MODEL_ENUM_ID
            threat_models = self.client.get_enum(threat_model_enum_id)
            threat_model_ids = [threat_model["dataField"] for threat_model in threat_models
                                if any(
                    threat_model_name.lower() in threat_model["displayField"].lower() for threat_model_name in
                    threat_model_names)]
            return threat_model_ids
        else:
            return None


