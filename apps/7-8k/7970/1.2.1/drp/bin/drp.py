import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import datetime



import urllib3
from cyberintegrations import DRPPoller
from cyberintegrations.utils import ParserHelper
from splunklib import client
from splunklib.modularinput import Argument, Event, Scheme, Script
from state_store import Credentials, FileStateStore
from constants import AppConsts
from utils import Utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SkipCollectionException(Exception):
    pass


class ScriptValidation:
    def __init__(self, validation_definition, logger):
        self.logger = logger
        self.logger.info("Initializing ScriptValidation")
        self.validation_definition = validation_definition
        self.session_key = self.get_parameters("session_key")
        self.logger.debug(f"Retrieved session key: {self.session_key}")
        self.username = self.get_parameters("gib_username")
        self.logger.debug(f"Retrieved username: {self.username}")
        self.api_key = Credentials.get_api_key(
            self.session_key, self.username, self.logger
        )
        self.logger.debug("API key retrieved successfully")

    def get_parameters(self, key):
        self.logger.debug(f"Retrieving parameter: {key}")
        if key == "session_key":
            value = self.validation_definition.__dict__.get("metadata").get(key)
        else:
            value = self.validation_definition.parameters[key]
        self.logger.debug(f"Parameter {key} value: {value}")
        return value

    def validate_collections(self):
        """
        Validate date fields set correctly.
        """
        self.logger.info("Starting collection validation")
        for collection in list(AppConsts.COLLECTION_LIST.keys()):
            self.logger.info(f"Validating collection: {collection}")
            collection_name = collection.replace("/", "_")
            date_field_name = collection_name + "_date"
            self.logger.debug(f"Checking if collection {collection_name} is enabled")
            if self.get_parameters(collection_name) == "1":
                self.logger.debug(
                    f"Collection {collection_name} is enabled, validating date"
                )
                date_value = self.get_parameters(date_field_name)
                if not date_value:
                    self.logger.error(
                        f"Initial date not provided for collection: {collection}"
                    )
                    raise ValueError(
                        f"Please provide an initial date value for {AppConsts.COLLECTION_LIST.get(collection)} collection."
                    )
                try:
                    self.logger.debug(
                        f"Validating date format for {date_field_name}: {date_value}"
                    )
                    datetime.datetime.strptime(date_value, "%Y-%m-%d")
                    self.logger.debug(f"Date format validated for {collection}")
                except ValueError as e:
                    self.logger.error(
                        f"Invalid date format for {collection}: {date_value}"
                    )
                    raise ValueError(
                        f"Please, provide initial date for {AppConsts.COLLECTION_LIST.get(collection)} collection in the following format: YYYY-mm-dd"
                    )
        self.logger.info("Collection validation completed")

    def set_proxy(self, poller: DRPPoller):
        self.logger.info("Setting up proxy configuration")
        if self.get_parameters("enable_proxy") == "1":
            self.logger.debug("Proxy is enabled, configuring proxy settings")
            poller.set_proxies(
                proxy_protocol=self.get_parameters("proxy_protocol"),
                proxy_ip=self.get_parameters("proxy_address"),
                proxy_port=self.get_parameters("proxy_port"),
            )
            self.logger.debug("Proxy settings applied")
        else:
            self.logger.debug("Proxy is disabled")

    def validate_connection(self):
        """
        Validate connection and available collections.
        """
        self.logger.info("Validating connection")
        poller = DRPPoller(
            username=self.username,
            api_key=self.api_key,
            api_url="https://drp.group-ib.com/client_api/",
        )
        self.logger.debug("DRPPoller initialized")
        poller.set_verify(True)
        self.logger.debug("SSL verification set to True")
        poller.set_product(**AppConsts.PRODUCT_DATA_FOR_POLLER)
        self.logger.debug("Product data set for poller")
        self.set_proxy(poller)
        try:
            self.logger.debug("Attempting to get available collections")
            brands = poller.get_brands()
            if len(brands) > 0:
                self.logger.info("Connection validated successfully")
            
        except Exception as e:
            self.logger.error(f"Connection validation failed: {str(e)}")
            raise ValueError(f"ERROR. {str(e)}")

    def run_validate(self):
        self.logger.info("Running full validation process")
        self.validate_collections()
        self.validate_connection()
        self.logger.info("Validation process completed")
 


class SeqUpdateLogicStream:
    def __init__(
        self,
        state_store,
        collection,
        input_item,
        poller,
        ew,
        use_additional_accounts,
        username,
        service,
        logger,
        brand_for_filtering,
        approve_state_for_filtering,
        sub_types_for_filtering,
        violation_section_for_filtering,
        only_typosquatting,
    ):
        self.logger = logger
        self.logger.info(
            f"Initializing SeqUpdateLogicStream for collection: {collection}"
        )
        self.state_store = state_store
        self.collection = collection
        self.input_item = input_item
        self.poller: DRPPoller  = poller
        self.ew = ew
        self.use_additional_accounts = use_additional_accounts
        self.username = username
        self.service = service
        # Currently, filtering by brand, approve_state, and sub_types only works for 
        # the first value in the provided list. This is due to a limitation in the 
        # library; support for multiple values is planned for future updates.
        self.brand_for_filtering = brand_for_filtering.split(",") if brand_for_filtering else brand_for_filtering
        self.approve_state_for_filtering = approve_state_for_filtering.split(",") if approve_state_for_filtering else approve_state_for_filtering
        self.sub_types_for_filtering = sub_types_for_filtering.split(",") if sub_types_for_filtering else sub_types_for_filtering
        self.violation_section_for_filtering = violation_section_for_filtering
        self.only_typosquatting = only_typosquatting
        self.logger.debug("SeqUpdateLogicStream initialized")
        self.logger.debug(
            (
                f"brand_for_filtering: {self.brand_for_filtering} (type: {type(self.brand_for_filtering).__name__}), "
                f"violation_section_for_filtering: {self.violation_section_for_filtering} (type: {type(self.violation_section_for_filtering).__name__}), "
                f"only_typosquatting: {self.only_typosquatting} (type: {type(self.only_typosquatting).__name__})"
            )
        )


    def check_sequence_update(self):
        """
        If no seqUpdate file -> get this value from server
        """
        self.logger.info(f"Checking sequence update for collection: {self.collection}")
        seqUpdate = Utils.get_current_sequpdates(self.state_store, self.collection, self.username)
        if seqUpdate is None:
            self.logger.info(
                f"seqUpdate is None for {self.collection}, retrieving from server"
            )
            configured_date = self.input_item.get(
                self.collection.replace("/", "_") + "_date"
            )
            self.logger.debug(f"Using configured date: {configured_date}")
            try:
                self.logger.debug("Fetching seqUpdate from server")
                seqUpdate = self.poller.get_seq_update_dict(date=configured_date).get(
                    self.collection
                )
                self.logger.info(f"Retrieved seqUpdate from server: {seqUpdate}")
                Utils.save_checkpoint(self.state_store, self.collection, seqUpdate, self.username)
            except Exception as e:
                self.logger.error(
                    f"Failed to retrieve seqUpdate for {self.collection}: {str(e)}"
                )
                raise SkipCollectionException()
        else:
            self.logger.debug(f"seqUpdate already exists: {seqUpdate}")
        return seqUpdate

    def start_stream(self):
        self.logger.info(f"Starting stream for collection: {self.collection}")
        seqUpdate = self.check_sequence_update()
        self.logger.info(f"Stream starting with seqUpdate: {seqUpdate}")
        feeds_iterator = self.poller.create_update_generator(
            collection_name=self.collection,
            sequpdate=seqUpdate,
            limit=100,
            brands=self.brand_for_filtering,
            subtypes=self.sub_types_for_filtering,
            section=self.violation_section_for_filtering,
            use_typo_squatting=self.only_typosquatting
            
        )
        self.logger.debug("Feeds iterator created")
        try:
            for response in feeds_iterator:
                self.logger.info(
                    f"Processing response with seqUpdate: {response.sequpdate} . Collection {self.collection}"
                )
                for item in response.raw_dict.get("items", []):
                    self.logger.debug(f"Processing item: {item.get('id')}")
                    self.logger.debug("Configuring event for item")
                    event = Utils.configure_event(
                        self.service,
                        self.collection,
                        item,
                        self.use_additional_accounts,
                        self.username,
                        logger=self.logger,
                    )
                    self.logger.debug("Writing event")
                    self.ew.write_event(event)
                    self.logger.debug(f"Event written for item: {item.get('id')}")
                Utils.save_checkpoint(
                    self.state_store, self.collection, response.sequpdate, self.username
                )
                self.logger.info(
                    f"Checkpoint saved with seqUpdate: {response.sequpdate}"
                )
        except Exception as e:
            self.logger.error(f"Stream failed for {self.collection}: {str(e)}")
            raise

class GIBDRP(Script):
    def __init__(self):
        super().__init__()
        self.session_key = None
        self.validation_definition = None
        self.logger = Utils.get_logger(use_small_log_size=False, use_debug_log_level=False)
        self.logger.debug("GIBDRP initialized")

    def create_scheme_argument(
        self,
        name,
        title,
        data_type,
        description="",
        required_on_create=False,
        required_on_edit=False,
    ):
        self.logger.debug(f"Creating scheme argument: {name}")
        argument = Argument(
            name=name,
            title=title,
            data_type=data_type,
            description=description,
            required_on_create=required_on_create,
            required_on_edit=required_on_edit,
        )
        self.logger.debug(f"Scheme argument created: {name}")
        return argument

    def get_scheme(self):
        self.logger.info("Generating scheme for GIB Digital Risk Protection")
        scheme = Scheme("GIB Digital Risk Protection")
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.description = "GIB Digital Risk Protection"
        self.logger.debug("Scheme basic settings applied")
        for common_setting in AppConsts.DATA_INPUTS_ARGUMENTS_SCHEMA:
            argument = self.create_scheme_argument(**common_setting)
            scheme.add_argument(argument)
            self.logger.debug(
                f"Added common setting argument: {common_setting['name']}"
            )
        for collection_tech_name, collection_name in AppConsts.COLLECTION_LIST.items():
            temp_scheme_argument = self.create_scheme_argument(
                name=collection_tech_name.replace("/", "_"),
                title=collection_name,
                data_type=Argument.data_type_boolean,
            )
            scheme.add_argument(temp_scheme_argument)
            self.logger.debug(f"Added collection argument: {collection_tech_name}")
            temp_scheme_date_argument = self.create_scheme_argument(
                name=collection_tech_name.replace("/", "_") + "_date",
                title="Initial Date",
                data_type=Argument.data_type_string,
            )
            scheme.add_argument(temp_scheme_date_argument)
            self.logger.debug(f"Added date argument for: {collection_tech_name}")
        self.logger.info("Scheme generation completed")
        return scheme

    def validate_input(self, validation_definition):
        self.logger.info("Validating input")
        self.validation_definition = validation_definition
        ScriptValidation(
            validation_definition=validation_definition, logger=self.logger
        ).run_validate()
        self.logger.info("Input validation completed")
        
    def get_collections(self, input_item):
        self.logger.info("Retrieving enabled and disabled collections")
        enabled_keys = {
            key.replace("/", "_") for key, value in input_item.items() if value == "1"
        }
        disabled_keys = {
            key.replace("/", "_") for key, value in input_item.items() if value == "0"
        }
        self.logger.debug(
            f"Enabled keys: {enabled_keys}, Disabled keys: {disabled_keys}"
        )
        collections = AppConsts.COLLECTION_LIST.keys()
        enabled = [key for key in collections if key.replace("/", "_") in enabled_keys]
        disabled = [
            key for key in collections if key.replace("/", "_") in disabled_keys
        ]
        self.logger.info(
            f"Enabled collections: {enabled}, Disabled collections: {disabled}"
        )
        return enabled, disabled

    def set_proxy(self, poller: DRPPoller, input_item):
        self.logger.info("Configuring proxy settings")
        PROXY_ENABLED = input_item["enable_proxy"]
        if PROXY_ENABLED == "1":
            self.logger.debug("Proxy enabled, setting proxy details")
            PROXY_ADDRESS = input_item.get("proxy_address", None)
            PROXY_PORT = input_item.get("proxy_port", None)
            PROXY_PROTOCOL = input_item.get("proxy_protocol", None)
            poller.set_proxies(PROXY_PROTOCOL, PROXY_ADDRESS, PROXY_PORT)
            self.logger.debug("Proxy configured")
        else:
            self.logger.debug("Proxy disabled")

    def stream_events(self, inputs, ew):
        self.logger.info("Starting event streaming process")
        for input_name, input_item in inputs.inputs.items():
            self.logger = Utils.get_logger(
                use_small_log_size=input_item["limit_the_size_of_logs_to_100_mb"],
                use_debug_log_level=input_item["use_debug_log_level"],
            )
            self.logger.info(f"Processing input: {input_name}")
            state_store = FileStateStore(inputs.metadata, input_name)
            self.logger.debug("State store initialized")
            USERNAME = input_item["gib_username"]
            self.session_key = inputs.metadata.get("session_key")
            self.logger.debug(f"Retrieved username: {USERNAME}")
            API_KEY = Credentials.get_api_key(self.session_key, USERNAME, self.logger)
            self.logger.debug("API key retrieved")
            USE_ADDITIONAL_ACCOUNTS = input_item.get("use_additional_accounts", None)
            self.logger.debug(
                f"Use additional accounts: {USE_ADDITIONAL_ACCOUNTS}"
            )
            poller = DRPPoller(
                username=USERNAME,
                api_key=API_KEY,
                api_url="https://drp.group-ib.com/client_api/",
            )
            self.logger.debug("DRPPoller initialized")
            poller.set_product(**AppConsts.PRODUCT_DATA_FOR_POLLER)
            poller.set_verify(True)
            self.set_proxy(poller, input_item)
            enabled_collections, disabled_collections = self.get_collections(input_item)
            for collection in disabled_collections:
                self.logger.info(f"Disabling collection: {collection}")
                Utils.delete_sequpdate(state_store, collection, USERNAME)
            for collection in enabled_collections:
                self.logger.info(f"Processing enabled collection: {collection}")
                self.logger.debug(f"Using sequence update logic for {collection}")
                try:
                    self.logger.info(
                        f"Streaming events for collection {collection} using sequence update logic"
                    )
                    SeqUpdateLogicStream(
                        state_store=state_store,
                        collection=collection,
                        input_item=input_item,
                        poller=poller,
                        ew=ew,
                        use_additional_accounts=USE_ADDITIONAL_ACCOUNTS,
                        username=USERNAME,
                        service=self.service,
                        logger=self.logger,
                        brand_for_filtering=input_item.get("brand_for_filtering", None),
                        approve_state_for_filtering=input_item.get("approve_state_for_filtering", None),
                        sub_types_for_filtering=input_item.get("sub_types_for_filtering", None),
                        violation_section_for_filtering=input_item.get("violation_section_for_filtering", None),
                        only_typosquatting=input_item.get("only_typosquatting", None),
                    ).start_stream()
                    self.logger.info(f"Streaming completed for {collection}")
        
                except SkipCollectionException:
                    self.logger.info(
                        f"Skipping collection {collection} due to exception"
                    )
                    continue
        self.logger.info("Event streaming process completed")


if __name__ == "__main__":
    sys.exit(GIBDRP().run(sys.argv))


