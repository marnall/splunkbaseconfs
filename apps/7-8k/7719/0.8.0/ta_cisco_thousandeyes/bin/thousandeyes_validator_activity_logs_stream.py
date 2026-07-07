import copy
import json

import import_declare_test  # noqa: F401
from solnlib.hec_config import HECConfig
from solnlib.utils import is_false
from thousandeyes_client import ThousandEyesClient
from thousandeyes_constant import (
    THOUSANDEYES_ACTIVITY_LOGS_PAYLOAD,
)
from thousandeyes_utils import get_account_id, get_hec_tokens


class ActivityLogsStreamInputValidator:
    """ThousandEyes Activity Logs Stream Input Validator."""

    def __init__(self, session_key, logger):
        """
        Initialize object.

        :param session_key: session key.
        :param logger: logger object

        :return: ThousandEyesActivityLogsStreamInputValidator Object
        """
        self.session_key = session_key
        self.logger = logger

    def init_payload(self):
        """
        Return static payload for activity logs stream.

        :return: Payload Dictionary.
        """
        return THOUSANDEYES_ACTIVITY_LOGS_PAYLOAD

    def add_url(self, stream_endpoint_url):
        """
        Add streaming url to stream payload.

        :param stream_endpoint_url :  streaming url to add to payload.

        """
        self.payload["streamEndpointUrl"] = stream_endpoint_url

    def add_export_config(self, index, token):
        """
        Add splunk index and HEC token to stream endpoint payload.

        :param index :  index to add to payload.
        :param token :  HEC token for payload.
        """
        self.payload["exporterConfig"]["splunkHec"]["index"] = index
        self.payload["exporterConfig"]["splunkHec"]["token"] = token

    def get_update_payload(self):
        """
        Get the stream endpoint payload.

        :return: Update payload dictionary.
        """
        payload = {}
        payload["exporterConfig"] = self.payload.get("exporterConfig")
        payload["testMatch"] = self.payload.get("testMatch")
        payload["streamEndpointUrl"] = self.payload.get("streamEndpointUrl")
        return payload

    def check_hec_token_valid(self, data, hec_list):
        """
        Check if HEC token is valid.

        :param data :  input configuration data.
        :param hec_list : list of HECs configured.
        """
        if data.get("hec_token") not in hec_list.keys():
            self.logger.error(
                f"Configured HEC token: {data.get('hec_token')} is not valid. Please verify."
            )
            raise Exception(
                f"Configured HEC token: {data.get('hec_token')} is not valid. Please verify."
            )

    def check_hec_ssl_enabled(self, hec_ssl):
        """
        Check if HEC is SSL enabled.

        :param hec_ssl :  HEC SSL setting.
        """
        if is_false(hec_ssl):
            self.logger.error(
                "SSL for HTTP Event Collector not enabled. Hence cannot create the input."
                " Please enable SSL for HTTP Event Collector."
            )
            raise Exception(
                "SSL for HTTP Event Collector not enabled. Hence cannot create the input."
                " Please enable SSL for HTTP Event Collector."
            )

    def create_new_stream(self, aid):
        """
        Create a new Thousandeyes activity logs stream.

        :param aid : Account Group Id for Stream creation.

        :return : Response dictionary
        """
        log_payload = copy.deepcopy(self.payload)
        del log_payload["exporterConfig"]["splunkHec"]["token"]
        self.logger.info(
            f"Creating new ThousandEyes activity logs stream using {self.payload.get('streamEndpointUrl')}."
        )
        self.logger.debug(f"Stream payload without HEC detail {log_payload}.")

        stream_response = self.client.add_new_stream(aid, json.dumps(self.payload))
        self.logger.info(
            f"Successfully created new ThousandEyes activity logs stream using {self.payload.get('streamEndpointUrl')}."
        )

        return stream_response

    def validate(self, data):
        """
        Validate the input configurations.

        :param data :  input configuration data.
        """
        self.logger.info("Validating the Activity Logs Stream Input Configuration.")

        hec_list = get_hec_tokens(self.session_key)
        self.check_hec_token_valid(data, hec_list)
        hec_settings = HECConfig(session_key=self.session_key).get_settings()

        self.check_hec_ssl_enabled(hec_settings.get("enableSSL"))
        self.logger.info("Successfully validated the provided HEC Token.")

        self.client = ThousandEyesClient(
            self.session_key, data.get("thousandeyes_user"), self.logger
        )
        self.payload = self.init_payload()

        self.add_url(data.get("hec_target"))

        aid = get_account_id(data.get("thousandeyes_acc_group"))
        self.add_export_config(
            data.get("activity_index"), hec_list.get(data.get("hec_token"))
        )

        if data.get("thousandeyes_stream_id", None) in (None, ""):
            stream_response = self.create_new_stream(aid)
            data["thousandeyes_stream_id"] = stream_response.get("id")
        else:
            update_payload = self.get_update_payload()
            log_payload = copy.deepcopy(update_payload)
            del log_payload["exporterConfig"]["splunkHec"]["token"]
            self.logger.info(
                f"Updating ThousandEyes activity logs stream: {data.get('thousandeyes_stream_id')}."
            )
            self.logger.debug(f"Stream payload without HEC detail {log_payload}.")
            stream_response = self.client.update_stream(
                aid,
                data.get("thousandeyes_stream_id"),
                json.dumps(self.get_update_payload()),
            )
            data["thousandeyes_stream_id"] = stream_response.get("id")
            self.logger.info(
                f"Successfully updated ThousandEyes activity logs stream {stream_response.get('id')}."
            )
