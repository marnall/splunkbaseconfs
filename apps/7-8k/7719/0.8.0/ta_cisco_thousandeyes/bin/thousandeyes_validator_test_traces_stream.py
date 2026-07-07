import json
import copy

from solnlib.hec_config import HECConfig
from solnlib.utils import is_false

import import_declare_test  # noqa: F401
from thousandeyes_client import ThousandEyesClient
from thousandeyes_constant import THOUSANDEYES_TRACE_PAYLOAD, DEFAULT_ENDPOINT_DYNAMIC_TEST_TYPE
from thousandeyes_utils import get_account_id, get_hec_tokens, get_test_id


class TraceInputValidator:
    """ThousandEyes Trace Input Validator."""

    def __init__(self, session_key, logger):
        """
        Initialize object.

        :param session_key: session key.
        :param logger: logger object

        :return: TraceInputValidator Object
        """
        self.session_key = session_key
        self.logger = logger

    def init_payload(self):  # flake8: noqa: E271, E126
        """
        Return static payload for trace stream.

        :return: Payload Dictionary.
        """
        return THOUSANDEYES_TRACE_PAYLOAD

    def add_url(self, stream_endpoint_url):
        """
        Add streaming url to trace stream payload.

        :param stream_endpoint_url :  streaming url to add to payload.

        """
        self.payload["streamEndpointUrl"] = stream_endpoint_url

    def add_tests(self, type, tests, account_group):
        """
        Add tests to trace stream payload - CEA page-load та web-transactions.

        :param type :  test type.
        :param tests :  selected tests.
        :param account_group :  account group selected.

        :return : combined tests
        """
        test_ids = []
        # Space added before the value All to order All always at the top.
        if tests.strip() == "All":
            all_tests = []
            aid = get_account_id(account_group)
            if aid and type == "cea":
                all_tests = self.client.get_cea_tests_for_traces(aid)
            test_values = []
            for test in all_tests.get("tests", []):
                test_ids.append({"id": test.get("testId"), "domain": type})
                test_type = test.get("type", DEFAULT_ENDPOINT_DYNAMIC_TEST_TYPE)
                test_values.append(
                    f"{test.get('testName')} ({test.get('testId')} | {test_type})"
                )
            tests = "~".join(test_values)
        else:
            tests_list = tests.split("~")
            for test in tests_list:
                test_id = get_test_id(test)
                test_ids.append({"id": test_id, "domain": type})

        self.payload["testMatch"].extend(test_ids)
        return tests

    def add_tags(self, tags, account_group):
        """
        Add tags to the trace stream payload.

        :param tags :  selected tags.
        :param account_group :  account group selected.

        :return : combined tags
        """
        tags_kv_pairs = []

        if tags.strip() == "All":
            aid = get_account_id(account_group)
            all_tags = self.client.get_all_tags(aid)

            tags_values = []
            for tag in all_tags.get("tags", []):
                tags_kv_pairs.append({"key": tag.get("key"), "value": tag.get("value")})
                tags_values.append(f"{tag.get('key')}:{tag.get('value')}")
            tags = "~".join(tags_values)

        else:
            tags_list = tags.split("~")
            for tag in tags_list:
                key, value = tag.split(":", 1)
                tags_kv_pairs.append({"key": key, "value": value})

        self.payload["tagMatch"].extend(tags_kv_pairs)

        return tags

    def add_export_config(self, index, token):
        """
        Add splunk index and HEC token to trace stream endpoint payload.

        :param index :  index to add to payload.
        :param token :  HEC token for payload.
        """
        self.payload["exporterConfig"]["splunkHec"]["index"] = index
        self.payload["exporterConfig"]["splunkHec"]["token"] = token

    def get_update_payload(self):
        """
        Get the trace stream endpoint payload.

        :return: Update payload dictionary.
        """
        payload = {}
        payload["exporterConfig"] = self.payload.get("exporterConfig")
        payload["testMatch"] = self.payload.get("testMatch")
        payload["tagMatch"] = self.payload.get("tagMatch")
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
                "SSL for HTTP Event Collector not enabled. Hence cannot create the trace input."
                " Please enable SSL for HTTP Event Collector."
            )
            raise Exception(
                "SSL for HTTP Event Collector not enabled. Hence cannot create the trace input."
                " Please enable SSL for HTTP Event Collector."
            )

    def create_new_trace_stream(self, aid):
        """
        Create a new Thousandeyes trace stream.

        :param aid : Account Group Id for Stream creation.

        :return : Response dictionary
        """
        log_payload = copy.deepcopy(self.payload)
        del log_payload["exporterConfig"]["splunkHec"]["token"]
        self.logger.info(
            f"Creating new ThousandEyes stream traces traces using {self.payload.get('streamEndpointUrl')}."
        )
        self.logger.debug(f"Stream payload without HEC detail {log_payload}.")

        stream_response = self.client.add_new_stream(aid, json.dumps(self.payload))
        self.logger.info(
            f"Successfully created new ThousandEyes stream traces traces using {self.payload.get('streamEndpointUrl')}."
        )

        return stream_response

    def validate(self, data):
        """
        Validate the input configurations.

        :param data :  input configuration data.
        """
        self.logger.info("Validating the Input Configuration.")

        aid = get_account_id(data.get("thousandeyes_acc_group"))

        hec_list = get_hec_tokens(self.session_key)
        self.check_hec_token_valid(data, hec_list)
        hec_settings = HECConfig(session_key=self.session_key).get_settings()

        self.check_hec_ssl_enabled(hec_settings.get("enableSSL"))
        self.logger.info(
            f"Successfully validated the provided HEC Token: {data.get('hec_token')}."
        )

        self.client = ThousandEyesClient(
            self.session_key,
            data.get("thousandeyes_user"),
            self.logger,
        )
        self.payload = self.init_payload()

        self.add_url(data.get("hec_target"))

        tests_cea = ""
        self.payload["testMatch"] = []
        if data.get("cea_tests", None) not in (None, ""):
            tests_cea = self.add_tests(
                "cea", data.get("cea_tests"), data.get("thousandeyes_acc_group")
            )
        self.add_export_config(
            data.get("test_index"), hec_list.get(data.get("hec_token"))
        )
        data["cea_tests"] = tests_cea

        tags = ""
        self.payload["tagMatch"] = []
        if data.get("tags") not in (None, ""):
            tags = self.add_tags(
                data.get("tags"),
                data.get("thousandeyes_acc_group"),
            )
        data["tags"] = tags

        if data.get("thousandeyes_stream_id", None) in (None, ""):
            stream_response = self.create_new_trace_stream(aid)
            data["thousandeyes_stream_id"] = stream_response.get("id")

        else:
            update_payload = self.get_update_payload()
            log_payload = copy.deepcopy(update_payload)
            del log_payload["exporterConfig"]["splunkHec"]["token"]
            self.logger.info(
                f"Updating ThousandEyes stream traces: {data.get('thousandeyes_stream_id')}."
            )
            self.logger.debug(f"Stream payload without HEC detail {log_payload}.")
            stream_response = self.client.update_stream(
                aid,
                data.get("thousandeyes_stream_id"),
                json.dumps(self.get_update_payload()),
            )
            data["thousandeyes_stream_id"] = stream_response.get("id")
            self.logger.info(
                f"Successfully updated ThousandEyes stream traces {stream_response.get('id')}."
            )
