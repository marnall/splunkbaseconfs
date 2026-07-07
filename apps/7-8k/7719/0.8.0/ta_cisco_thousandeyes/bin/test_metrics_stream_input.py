import json
import traceback
import import_declare_test  # noqa: F401
from thousandeyes_constant import THOUSANDEYES_TA_NAME # noqa E402
from solnlib.utils import is_false
from log_helper import setup_logging
from splunklib import modularinput as smi

from thousandeyes_constant import ACCOUNT_GROUP_SOURCETYPE, PATH_VIS_SOURCETYPE
from thousandeyes_client import ThousandEyesClient
from solnlib.modular_input.checkpointer import KVStoreCheckpointer
from thousandeyes_utils import get_account_id, get_test_id, get_test_details


class ThousandEyesPathCollector:
    """ThousandEyes collector for path data collection."""

    def __init__(self, inputs, ew):
        """
        Initialize object.

        :param inputs: input details.
        :param ew: Event Writer object.

        :return: ThousandEyesPathCollector Object
        """
        self.ew = ew
        self.session_key = inputs.metadata["session_key"]

        self.input_name = list(inputs.inputs.keys())[0]
        self.input_item = inputs.inputs[self.input_name]
        self.normalized_input_name = self.input_name.split("/")[-1]

        self.test_index = self.input_item["test_index"]
        self.path_index = self.input_item["index"]
        self.logger = setup_logging(f"{THOUSANDEYES_TA_NAME}_stream_{self.normalized_input_name}")
        self.thousandeyes_account_group = self.input_item["thousandeyes_acc_group"]
        self.thousandeyes_account_group_id = get_account_id(
            self.thousandeyes_account_group
        )
        self.thousandeyes_account = self.input_item["thousandeyes_user"]
        self.cea_tests = self.input_item.get("cea_tests", "")
        self.endpoint_tests = self.input_item.get("endpoint_tests", "")

        self.interval = self.input_item.get("interval")
        self.path_selection = self.input_item.get("related_paths")

        self.thousandeyes_client = ThousandEyesClient(
            self.session_key, self.thousandeyes_account, self.logger
        )
        self.checkpoint = self.initialize_checkpoint()

    def initialize_checkpoint(self):
        """
        Initialize an checkpointer.

        :return: KVStoreCheckpointer Object
        """
        return KVStoreCheckpointer(
            collection_name=f"{THOUSANDEYES_TA_NAME}_checkpointer",
            session_key=self.session_key,
            app=THOUSANDEYES_TA_NAME,
        )

    def filter_test(self):
        """
        Get configured test Ids with their details.

        :return: Test Id dictionaries with type and optional endpoint_test_category
        """
        cea_test, endpoint_test = [], []
        
        for test in self.cea_tests.split("~"):
            test_details = get_test_details(test)
            if test_details and test_details.get("test_id"):
                cea_test.append({
                    "test_id": test_details["test_id"],
                    "type": "cea"
                })

        for test in self.endpoint_tests.split("~"):
            test_details = get_test_details(test)
            if test_details and test_details.get("test_id"):
                endpoint_test.append({
                    "test_id": test_details["test_id"],
                    "type": "endpoint",
                    # May be None for tests saved before the endpoint_test_category field was added
                    "endpoint_test_category": test_details.get("endpoint_test_category")
                })
        
        return cea_test, endpoint_test
    
    def build_endpoint_test_category_mapping(self):
        """
        Build a mapping of endpoint test IDs to their subtypes (scheduled/dynamic).
        
        :return: Dictionary mapping test_id to subtype
        """
        all_endpoint_tests = self.thousandeyes_client.get_all_endpoint_tests(
            self.thousandeyes_account_group_id
        )
        mapping = {}
        for test in all_endpoint_tests.get("tests", []):
            test_id = str(test.get("testId"))
            subtype = test.get("_endpointTestCategory")
            if not subtype:
                raise ValueError(
                    f"Endpoint test {test_id} is missing '_endpointTestCategory' field. "
                    "This indicates a problem with the endpoint test fetching logic."
                )
            mapping[test_id] = subtype
        
        self.logger.debug(
            f"{self.normalized_input_name}|Built endpoint test category mapping for {len(mapping)} tests."
        )
        return mapping

    def get_endpoint_test_category_mapping_if_needed(self, endpoint_test):
        """
        Check if endpoint tests need category information from API and fetch if needed.
        This handles backward compatibility for tests saved before category field was added.
        
        :param endpoint_test: List of endpoint test dictionaries
        :return: Dictionary mapping test_id to category, or empty dict if not needed
        """
        endpoint_test_category_mapping = {}
        needs_api_fetch = any(
            test.get("endpoint_test_category") is None 
            for test in endpoint_test
        )
        
        if needs_api_fetch:
            self.logger.info(
                f"{self.normalized_input_name}|Some endpoint tests are missing test category information. "
                "Fetching from API for backward compatibility."
            )
            endpoint_test_category_mapping = self.build_endpoint_test_category_mapping()
        else:
            self.logger.debug(
                f"{self.normalized_input_name}|All endpoint tests have subtype information from configuration."
            )
        
        return endpoint_test_category_mapping

    def determine_endpoint_test_category(self, test, endpoint_test_category_mapping):
        """
        Determine the endpoint test category for a test.
        Returns None for CEA tests, the category for endpoint tests.
        
        :param test: Test dictionary with test_id, type, and optional endpoint_test_category
        :param endpoint_test_category_mapping: Mapping of test_id to category for backward compatibility
        :return: endpoint_test_category string or None
        """
        test_type = test.get("type")
        if test_type != "endpoint":
            return None
        
        test_id = test.get("test_id")
        # First try to get from the test configuration
        endpoint_test_category = test.get("endpoint_test_category")
        
        # If not in config, try the API mapping (for backward compatibility)
        if not endpoint_test_category:
            endpoint_test_category = endpoint_test_category_mapping.get(str(test_id))
        
        # If still not found, fail explicitly
        if not endpoint_test_category:
            raise ValueError(
                f"Endpoint test {test_id} category not found. "
                "This test may have been deleted or is not accessible."
            )
        
        return endpoint_test_category

    def collect_and_ingest_paginated_path_data(self, test_id, test_type, endpoint_test_category, log_suffix):
        """
        Collect path data with pagination support and ingest all results.
        
        :param test_id: Test ID to collect data for
        :param test_type: Type of test (cea or endpoint)
        :param endpoint_test_category: Category for endpoint tests (None for CEA)
        :param log_suffix: Logging suffix for endpoint category info
        :return: Total count of results collected
        """
        test_count = 0
        
        # Get initial page
        path_info = self.thousandeyes_client.get_path_info(
            test_id, self.thousandeyes_account_group_id, test_type, endpoint_test_category
        )
        test_count += len(path_info.get("results"))
        self.ingest_path_info(path_info)
        self.logger.debug(
            f"{self.normalized_input_name}|Collected {len(path_info.get('results'))} Network Path Data results"
            f" for test type: {test_type}{log_suffix}, test Id : {test_id}."
        )
        
        # Handle pagination
        while (
            path_info.get("_links", {}).get("next")
            and len(path_info.get("results")) != 0
        ):
            path_info = self.thousandeyes_client.get_paginated_data(
                path_info.get("_links").get("next").get("href")
            )
            test_count += len(path_info.get("results"))
            self.ingest_path_info(path_info)
            self.logger.debug(
                f"{self.normalized_input_name}|Collected {len(path_info.get('results'))} Network Path Data "
                f"results for test type: {test_type}{log_suffix}, test Id : {test_id}."
            )
        
        return test_count

    def collect_path_data_for_test(self, test, endpoint_test_category_mapping):
        """
        Collect path data for a single test.
        
        :param test: Test dictionary with test_id, type, and optional endpoint_test_category
        :param endpoint_test_category_mapping: Mapping of test_id to category for backward compatibility
        :return: Total count of results collected for this test
        """
        test_id = test.get("test_id")
        test_type = test.get("type")
        
        endpoint_test_category = self.determine_endpoint_test_category(test, endpoint_test_category_mapping)
        log_suffix = f" (category: {endpoint_test_category})" if endpoint_test_category else ""
        
        self.logger.info(
            f"{self.normalized_input_name}|Collecting Network Path Data"
            f" for test type: {test_type}{log_suffix}, test Id : {test_id}."
        )
        
        test_count = self.collect_and_ingest_paginated_path_data(
            test_id, test_type, endpoint_test_category, log_suffix
        )
        
        self.logger.debug(
            f"{self.normalized_input_name}|Finished collecting total {test_count} Network Path Data"
            f" for test type: {test_type}{log_suffix}, test Id : {test_id}."
        )
        
        return test_count

    def ingest_account_group_details(self):
        """Collect and ingest account group results."""
        current_checkpoint = self.checkpoint.get(self.normalized_input_name)
        if current_checkpoint is None or not current_checkpoint.get(
            "first_run_completed"
        ):
            self.logger.info(
                f"{self.normalized_input_name}|Fetching all account group details."
            )
            acc_groups = self.thousandeyes_client.get_all_acc_groups()
            for acc in acc_groups.get("accountGroups"):
                event = smi.Event(
                    data=json.dumps(acc, ensure_ascii=False),
                    sourcetype=ACCOUNT_GROUP_SOURCETYPE,
                    index=self.test_index,
                )
                self.ew.write_event(event)
            self.logger.info(
                f"{self.normalized_input_name}|Successfuly fetched all account group details."
            )
            ckpt = {"first_run_completed": 1}
            self.checkpoint.update(self.normalized_input_name, ckpt)
            self.logger.info(
                f"{self.normalized_input_name}|Updated account group checkpoint."
            )

    def collect_events(self):
        """Collect Path information results."""
        try:
            count = 0
            self.logger.info(
                f"{self.normalized_input_name}|Starting Network Path Data collection."
            )
            self.ingest_account_group_details()

            if is_false(self.path_selection):
                self.logger.info(
                    f"{self.normalized_input_name}|Network Path Data collection is not enabled."
                )
                self.logger.info(
                    f"{self.normalized_input_name}|Exiting Network Path Data collection."
                )
                return

            cea_test, endpoint_test = self.filter_test()
            
            # Check if any endpoint tests are missing category information
            # If so, we need to fetch from API for backward compatibility
            endpoint_test_category_mapping = self.get_endpoint_test_category_mapping_if_needed(endpoint_test)

            if len(cea_test) > 0:
                self.logger.info(
                    f"{self.normalized_input_name}|Cloud & Enterprise Agent Test Ids configured"
                    f" for Network Path Data collection : {cea_test}."
                )
            else:
                self.logger.info(
                    f"{self.normalized_input_name}|No Cloud & Enterprise Agent Tests configured"
                    " for Network Path Data collection."
                )

            if len(endpoint_test) > 0:
                self.logger.info(
                    f"{self.normalized_input_name}|Endpoint Agent Test Ids configured"
                    f" for Network Path Data collection : {endpoint_test}."
                )
            else:
                self.logger.info(
                    f"{self.normalized_input_name}|No Endpoint Agent Tests configured"
                    " for Network Path Data collection."
                )

            for test in cea_test + endpoint_test:
                count += self.collect_path_data_for_test(test, endpoint_test_category_mapping)
        except Exception as e:
            self.logger.error(
                f"{self.normalized_input_name}|Error occurred during Network Path Data collection: {e}"
                f" {traceback.format_exc()}"
            )
        finally:
            self.logger.info(
                f"{self.normalized_input_name}|Collected total {count} Network Path Data results."
            )
            self.logger.info(
                f"{self.normalized_input_name}|Exiting Network Path Data collection."
            )

    def ingest_path_info(self, path_info):
        """Ingest path information into splunk."""
        for path in path_info.get("results"):
            event = smi.Event(
                data=json.dumps(path, ensure_ascii=False), stanza=self.input_name, sourcetype=PATH_VIS_SOURCETYPE
            )
            self.ew.write_event(event)
