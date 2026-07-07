import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import datetime
import json
import logging
import logging.handlers

import urllib3
import re
from cyberintegrations import TIPoller
from cyberintegrations.utils import ParserHelper
from splunk.clilib import cli_common as cli
from splunklib import client
from splunklib.modularinput import Argument, Event, Scheme, Script
from state_store import Credentials, FileStateStore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AppConsts:
    APP_NAME = "gib_tia"
    LOG_FILE_DIRECTORY = os.environ["SPLUNK_HOME"] + "/var/log/splunk/" + APP_NAME
   
    COLLECTION_LIST = {
        "compromised/account_group": "Compromised::Account",
        "compromised/bank_card_group": "Compromised::Group_Card",
        "compromised/masked_card": "Compromised::Masked Card",
        "compromised/spd": "Compromised::SPD",
        "compromised/breached": "Compromised::Brached DB",
        "compromised/reaper": "Compromised::Darkweb",
        "compromised/access": "Compromised::Access",
        "compromised/discord": "Compromised::Discord",
        "compromised/messenger": "Compromised::Messenger",
        "ioc/common": "IOC::Common",
        "attacks/ddos": "Attacks::DDoS",
        "attacks/deface": "Attacks::Deface",
        "attacks/phishing_kit": "Attacks::Phishing Kit",
        "attacks/phishing_group": "Attacks::Phishing Group",
        "hi/threat": "Cybercriminals::Threat Report",
        "hi/threat_actor": "Cybercriminals::Threat Actor",
        "apt/threat": "APT::Threat",
        "apt/threat_actor": "APT::Threat Actor",
        "osi/git_repository": "OSI::Git Repository",
        "osi/vulnerability": "OSI::Vulnerability",
        "osi/public_leak": "OSI::Public Leak",
        "suspicious_ip/tor_node": "Suspicious IP::Tor Node",
        "suspicious_ip/open_proxy": "Suspicious IP::Open Proxy",
        "suspicious_ip/socks_proxy": "Suspicious IP::Socks Proxy",
        "suspicious_ip/scanner": "Suspicious IP::Scanner",
        "suspicious_ip/vpn": "Suspicious IP::VPN",
        "malware/cnc": "Malware::C&C",
        "malware/config": "Malware::Config",
        "malware/signature": "Malware::Signature",
        "malware/malware": "Malware::Report",
        "malware/yara": "Malware::YARA",
    }

    MASKED_VALUE = {
        "compromised/breached": ["password"],
        "compromised/account_group": ["password"],
    }

    PRODUCT_DATA_FOR_POLLER = {
        "product_type": "SIEM",
        "product_name": "Splunk",
        "integration_name": "Group-IB Threat Intelligence",
        "integration_version": "1.9.0",
    }

    COLLECTIONS_NOT_SUPPORTING_SEQUPDATE = [
        "compromised/reaper",
        "compromised/breached",
    ]

    DATA_INPUTS_ARGUMENTS_SCHEMA = [
        {
            "name": "gib_username",
            "title": "Username",
            "data_type": Argument.data_type_string,
            "description": "Username",
            "required_on_create": True,
            "required_on_edit": True,
        },
        {
            "name": "enable_proxy",
            "title": "Enable Proxy?",
            "data_type": Argument.data_type_boolean,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "proxy_address",
            "title": "Proxy Address",
            "data_type": Argument.data_type_string,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "proxy_port",
            "title": "Proxy Port",
            "data_type": Argument.data_type_number,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "proxy_protocol",
            "title": "Proxy Protocol",
            "data_type": Argument.data_type_string,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "masking_type",
            "title": "Masking data type",
            "data_type": Argument.data_type_string,
            "description": "Input: 1 - Mask half of the field 2 - Mask all fild.",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "use_additional_accounts",
            "title": "Use additional accounts",
            "data_type": Argument.data_type_boolean,
            "description": "Allows to work with several accounts, otherwise the work is done with the main one and indexes are not added to events",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "limit_the_size_of_logs_to_100_mb",
            "title": "Limit the size of logs to 100 MB.",
            "data_type": Argument.data_type_boolean,
            "description": "When this parameter is enabled, the size of the collected logs is limited to 100 MB. If this parameter is disabled, the log size limit is 2 GB.",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "use_debug_log_level",
            "title": "Enable debug logging.",
            "data_type": Argument.data_type_boolean,
            "description": "Enabling this parameter allows you to collect debug logs of the application's operation.",
            "required_on_create": False,
            "required_on_edit": False,
        },
        
        
    ]

    COLLECTIONS_THAT_ARE_REQUIRED_HUNTING_RULES = [
        "osi/git_repository",
        "osi/public_leak",
        "compromised/breached",
    ]
    
    FIELDS_TO_EXCLUDE_BY_COLLECTIONS = {
        "malware/malware":["attachedFile", "history"]
    }


class Utils:
    log_sizes = {
        "small": 100 * 1024 * 1024,  # 100 MB
        "normal": 2 * 1024 * 1024 * 1024,  # 2 GB
    }
    @staticmethod
    def get_logger(use_small_log_size = False, use_debug_log_level = False):
        """
        Returns a logger instance with the specified configuration.
        """
        logger = logging.getLogger(AppConsts.APP_NAME)
        logging.propagate = False
        logger.setLevel(logging.DEBUG if bool(int(use_debug_log_level)) == True else logging.INFO)
        if not os.path.exists(AppConsts.LOG_FILE_DIRECTORY):
            os.makedirs(AppConsts.LOG_FILE_DIRECTORY)
        log_path = os.path.join(AppConsts.LOG_FILE_DIRECTORY, "modinput.log")
        
        if logger.hasHandlers():
            logger.handlers.clear()
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=(
                Utils.log_sizes["small"]
                if bool(int(use_small_log_size)) == True
                else Utils.log_sizes["normal"]
            ),
            backupCount=1,
        )
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug("Logger Initialized")

        return logger

    @staticmethod
    def sanitize_username_for_state(username: str) -> str:
        """
        Lowercase and replace any non-latin characters with underscore.
        Only [a-z] are preserved as-is; everything else becomes '_'.
        """
        if username is None:
            return "unknown"
        lowered = str(username).lower()
        sanitized = re.sub(r"[^a-zA-Z0-9]", "_", lowered)
        return sanitized if sanitized else "unknown"

    @staticmethod
    def generate_state_key(collection: str, username: str) -> str:
        sanitized_username = Utils.sanitize_username_for_state(username)
        collection_param_name = collection.replace("/", "_")
        return f"{sanitized_username}__{collection_param_name}"

    @staticmethod
    def get_current_sequpdates(state_store, collection, username):
        key = Utils.generate_state_key(collection, username)
        state = state_store.get_state(key)
        if state is not None:
            return state
        # Backward compatibility: try legacy key without username
        legacy_key = collection.replace("/", "_")
        legacy_state = state_store.get_state(legacy_key)
        if legacy_state is not None:
            # Migrate to new key
            state_store.update_state(key, legacy_state)
            return legacy_state
        return None

    @staticmethod
    def save_checkpoint(state_store, collection, checkpoint_date, username):
        # checkpoint_date can be either seqUpdate, update_time or datetime
        key = Utils.generate_state_key(collection, username)
        state_store.update_state(key, checkpoint_date)

    @staticmethod
    def delete_sequpdate(state_store, collection, username):
        key = Utils.generate_state_key(collection, username)
        state_store.update_state(key, None)

    @staticmethod
    def check_and_create_logger_dir():
        if not os.path.exists(AppConsts.LOG_FILE_DIRECTORY):
            os.makedirs(AppConsts.LOG_FILE_DIRECTORY)

    @staticmethod
    def definition_apply_hunting_rules(collection_name):
        if collection_name in AppConsts.COLLECTIONS_THAT_ARE_REQUIRED_HUNTING_RULES:
            return 1
        return 0


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

    def set_proxy(self, poller: TIPoller):
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
        poller = TIPoller(
            username=self.username,
            api_key=self.api_key,
            api_url="https://tap.group-ib.com/api/v2/",
        )
        self.logger.debug("TIPoller initialized")
        poller.set_verify(True)
        self.logger.debug("SSL verification set to True")
        poller.set_product(**AppConsts.PRODUCT_DATA_FOR_POLLER)
        self.logger.debug("Product data set for poller")
        self.set_proxy(poller)
        try:
            self.logger.debug("Attempting to get available collections")
            response = poller.get_available_collections()
            self.logger.info("Connection validated successfully")
        except Exception as e:
            self.logger.error(f"Connection validation failed: {str(e)}")
            raise ValueError(f"ERROR. {str(e)}")

    def run_validate(self):
        self.logger.info("Running full validation process")
        self.validate_collections()
        self.validate_connection()
        self.logger.info("Validation process completed")


class CommonLogic:
    @staticmethod
    def get_or_create_index(service, logger, index_name: str) -> str:
        logger.debug(f"Retrieving or creating index: {index_name}")
        try:
            service = service
            try:
                index_obj = service.indexes[index_name]
                logger.info(f"Index {index_name} found")
            except KeyError:
                logger.info(f"Index {index_name} not found, creating new index")
                index_obj = service.indexes.create(index_name)
                logger.info(f"Index {index_name} created")
            return index_obj.name
        except Exception as e:
            logger.error(f"Failed to get or create index {index_name}: {str(e)}")
            return None
        
    @staticmethod
    def preprocessing_event(collection, item, logger):
        logger.debug(
            f"Preprocessing event for collection {collection}, item {item.get('id')}"
        )
        filtered_item = item
        if collection in AppConsts.FIELDS_TO_EXCLUDE_BY_COLLECTIONS.keys():
            excluded_fields = AppConsts.FIELDS_TO_EXCLUDE_BY_COLLECTIONS[collection]
            filtered_item = {
                key: value
                for key, value in item.items()
                if key not in excluded_fields
            }
        return filtered_item

    @staticmethod
    def configure_event(
        service, collection, item, use_additional_accounts, username, logger
    ):
        item = CommonLogic.preprocessing_event(collection=collection, item=item, logger=logger)
        
        logger.debug(
            f"Configuring event for collection {collection}, item {item.get('id')}"
        )
        event = Event(
            stanza=collection.replace("/", "_"),
            data=json.dumps(item),
            source="gib_ti_" + collection.replace("/", "_"),
            sourcetype="gib_ti_" + collection.replace("/", "_"),
        )
        logger.debug("Event object created")
        if use_additional_accounts == "1":
            import re

            index = re.sub(r"[^a-zA-Z0-9]", "_", username)
            logger.debug(f"Setting index to: {index}")
            CommonLogic.get_or_create_index(
                service=service, index_name=index, logger=logger
            )
            event.index = index
            logger.debug(f"Index set for event: {index}")
        logger.debug("Event configuration completed")
        return event


class SeqUpdateLogicStream:
    def __init__(
        self,
        state_store,
        collection,
        input_item,
        poller,
        ew,
        mask_type,
        use_additional_accounts,
        username,
        service,
        logger,
    ):
        self.logger = logger
        self.logger.info(
            f"Initializing SeqUpdateLogicStream for collection: {collection}"
        )
        self.state_store = state_store
        self.collection = collection
        self.input_item = input_item
        self.poller = poller
        self.ew = ew
        self.mask_type = mask_type
        self.use_additional_accounts = use_additional_accounts
        self.username = username
        self.service = service
        self.logger.debug("SeqUpdateLogicStream initialized")

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

    def work_with_masked_collections(self, item):
        self.logger.info(
            f"Masking data for item {item.get('id')} in collection {self.collection}"
        )
        mask_state = self.input_item.get(
            self.collection.replace("/", "_") + "_mask_state"
        )
        self.logger.debug(f"mask_state: {mask_state}")
        if mask_state == "1":
            self.logger.debug("Masking enabled")
            for field in AppConsts.MASKED_VALUE.get(self.collection, []):
                self.logger.debug(f"Checking field: {field}")
                value_field = ParserHelper.find_element_by_key(item, field)
                if value_field:
                    if self.mask_type == "1":
                        self.logger.debug(f"Applying half masking to field {field}")
                        masked_value = value_field[: len(value_field) // 2] + "*" * (
                            len(value_field) // 2
                        )
                        ParserHelper.set_element_by_key(item, field, masked_value)
                        self.logger.debug(f"Field {field} masked: {masked_value}")
                    elif self.mask_type == "2":
                        self.logger.debug(f"Removing value from field {field}")
                        ParserHelper.set_element_by_key(item, field, "")
                        self.logger.debug(f"Field {field} cleared")
        else:
            self.logger.debug("Masking disabled")

    def start_stream(self):
        self.logger.info(f"Starting stream for collection: {self.collection}")
        seqUpdate = self.check_sequence_update()
        self.logger.info(f"Stream starting with seqUpdate: {seqUpdate}")
        apply_hunting_rules = Utils.definition_apply_hunting_rules(
            collection_name=self.collection
        )
        feeds_iterator = self.poller.create_update_generator(
            self.collection,
            sequpdate=seqUpdate,
            limit=100,
            apply_hunting_rules=apply_hunting_rules,
        )
        self.logger.debug("Feeds iterator created")
        try:
            for response in feeds_iterator:
                self.logger.info(
                    f"Processing response with seqUpdate: {response.sequpdate} . Collection: {self.collection}"
                )
                for item in response.raw_dict.get("items", []):
                    self.logger.debug(f"Processing item: {item.get('id')}")
                    if self.collection in AppConsts.MASKED_VALUE.keys():
                        self.work_with_masked_collections(item)
                    self.logger.debug("Configuring event for item")
                    event = CommonLogic.configure_event(
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


class StandartIterationLogicStream:
    outstanding_collections = ["compromised/breached", "compromised/reaper"]

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
    ):
        self.logger = logger
        self.logger.info(
            f"Initializing StandartIterationLogicStream for collection: {collection}"
        )
        self.state_store = state_store
        self.collection = collection
        self.input_item = input_item
        self.poller = poller
        self.ew = ew
        self.use_additional_accounts = use_additional_accounts
        self.username = username
        self.service = service
        self.logger.debug("StandartIterationLogicStream initialized")

    def get_dates(self):
        self.logger.info(f"Retrieving dates for collection: {self.collection}")
        start_date = Utils.get_current_sequpdates(self.state_store, self.collection, self.username)
        if start_date is None:
            self.logger.debug("No existing start date, using configured date")
            start_date = self.input_item.get(
                self.collection.replace("/", "_") + "_date"
            )
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").strftime(
                "%Y-%m-%d"
            )
            self.logger.info(f"Using configured start date: {start_date}")
        else:
            self.logger.debug(f"Existing start date found: {start_date}")
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.logger.info(
            f"Dates retrieved - Start: {start_date}, Current: {current_date}"
        )
        return start_date, current_date

    def start_stream(self):
        self.logger.info(f"Starting stream for collection: {self.collection}")
        try:
            start_date, current_date = self.get_dates()
            self.logger.debug(
                f"Creating search generator from {start_date} to {current_date}"
            )
            apply_hunting_rules = Utils.definition_apply_hunting_rules(
                collection_name=self.collection
            )
            feeds_iterator = self.poller.create_search_generator(
                self.collection,
                date_from=start_date,
                date_to=current_date,
                apply_hunting_rules=apply_hunting_rules,
            )
            for response in feeds_iterator:
                self.logger.info(f"Processing response for {self.collection}")
                for item in response.raw_dict.get("items", []):
                    self.logger.debug(f"Processing item: {item.get('id')}")
                    event = CommonLogic.configure_event(
                        service=self.service,
                        collection=self.collection,
                        item=item,
                        use_additional_accounts=self.use_additional_accounts,
                        username=self.username,
                        logger=self.logger,
                    )
                    self.logger.debug("Writing event")
                    self.ew.write_event(event)
                    self.logger.debug(f"Event written for item: {item.get('id')}")
                if self.collection in self.outstanding_collections:
                    if self.collection == "compromised/breached":
                        checkpoint_date = response.raw_dict.get("items", [])[-1].get(
                            "updateTime"
                        )
                    elif self.collection == "compromised/reaper":
                        checkpoint_date = response.raw_dict.get("items", [])[-1].get(
                            "datetime"
                        )
                    self.logger.info(f"Saving checkpoint date: {checkpoint_date}")
                Utils.save_checkpoint(
                    self.state_store, self.collection, checkpoint_date, self.username
                )
            self.logger.debug(
                f"Saving final checkpoint with current date: {current_date}"
            )
            Utils.save_checkpoint(self.state_store, self.collection, current_date, self.username)
            self.logger.info("Stream completed successfully")
        except Exception as e:
            self.logger.error(f"Stream failed for {self.collection}: {str(e)}")
            raise


class GIBTIA(Script):
    def __init__(self):
        super().__init__()
        self.session_key = None
        self.validation_definition = None
        self.logger = Utils.get_logger(use_small_log_size=False, use_debug_log_level=False)
        self.logger.debug("GIBTIA initialized")

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
        self.logger.info("Generating scheme for GIB Threat Intelligence")
        scheme = Scheme("GIB Threat Intelligence")
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.description = "GIB Threat Intelligence"
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
            if collection_tech_name in AppConsts.MASKED_VALUE.keys():
                temp_scheme_argument = self.create_scheme_argument(
                    name=collection_tech_name.replace("/", "_") + "_mask_state",
                    title="Mask confidential data",
                    data_type=Argument.data_type_boolean,
                )
                scheme.add_argument(temp_scheme_argument)
                self.logger.debug(
                    f"Added mask state argument for: {collection_tech_name}"
                )
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

    def stream_events_for_df_dt_collections(
        self,
        state_store,
        collection,
        input_item,
        poller,
        ew,
        use_additional_accounts,
        username,
    ):
        self.logger.info(
            f"Streaming events for collection {collection} using standard logic"
        )
        StandartIterationLogicStream(
            state_store=state_store,
            collection=collection,
            input_item=input_item,
            poller=poller,
            ew=ew,
            use_additional_accounts=use_additional_accounts,
            username=username,
            service=self.service,
            logger=self.logger,
        ).start_stream()
        self.logger.info(f"Streaming completed for {collection}")

    def stream_events_for_seq_update_collections(
        self,
        state_store,
        collection,
        input_item,
        poller,
        ew,
        mask_type,
        use_additional_accounts,
        username,
    ):
        self.logger.info(
            f"Streaming events for collection {collection} using sequence update logic"
        )
        SeqUpdateLogicStream(
            state_store=state_store,
            collection=collection,
            input_item=input_item,
            poller=poller,
            ew=ew,
            mask_type=mask_type,
            use_additional_accounts=use_additional_accounts,
            username=username,
            service=self.service,
            logger=self.logger,
        ).start_stream()
        self.logger.info(f"Streaming completed for {collection}")

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

    def set_proxy(self, poller: TIPoller, input_item):
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
            MASK_TYPE = input_item.get("masking_type", None)
            USE_ADDITIONAL_ACCOUNTS = input_item.get("use_additional_accounts", None)
            self.logger.debug(
                f"Mask type: {MASK_TYPE}, Use additional accounts: {USE_ADDITIONAL_ACCOUNTS}"
            )
            poller = TIPoller(
                username=USERNAME,
                api_key=API_KEY,
                api_url="https://tap.group-ib.com/api/v2/",
            )
            self.logger.debug("TIPoller initialized")
            poller.set_product(**AppConsts.PRODUCT_DATA_FOR_POLLER)
            poller.set_verify(True)
            self.set_proxy(poller, input_item)
            enabled_collections, disabled_collections = self.get_collections(input_item)
            for collection in disabled_collections:
                self.logger.info(f"Disabling collection: {collection}")
                Utils.delete_sequpdate(state_store, collection, USERNAME)
            for collection in enabled_collections:
                self.logger.info(f"Processing enabled collection: {collection}")
                if collection in AppConsts.COLLECTIONS_NOT_SUPPORTING_SEQUPDATE:
                    self.logger.debug(f"Using standard iteration for {collection}")
                    self.stream_events_for_df_dt_collections(
                        state_store,
                        collection,
                        input_item,
                        poller,
                        ew,
                        use_additional_accounts=USE_ADDITIONAL_ACCOUNTS,
                        username=USERNAME,
                    )
                else:
                    self.logger.debug(f"Using sequence update logic for {collection}")
                    try:
                        self.stream_events_for_seq_update_collections(
                            state_store,
                            collection,
                            input_item,
                            poller,
                            ew,
                            mask_type=MASK_TYPE,
                            use_additional_accounts=USE_ADDITIONAL_ACCOUNTS,
                            username=USERNAME,
                        )
                    except SkipCollectionException:
                        self.logger.info(
                            f"Skipping collection {collection} due to exception"
                        )
                        continue
        self.logger.info("Event streaming process completed")


if __name__ == "__main__":
    sys.exit(GIBTIA().run(sys.argv))
