import time
import import_declare_test
import logging
import sys
import os
from typing import Dict, List
from common import Common
from splunklib.modularinput import Script, Scheme
from splunklib.modularinput.input_definition import InputDefinition
from logging.handlers import RotatingFileHandler
from solnlib.conf_manager import ConfManager, ConfManagerException
from inputs import Inputs
from aws_accounts import AWSAccount
from event_logs import EventLogs
from utils import send_ui_notification, get_dir_prefix

EVENT_LOGS_CONF_NAME = "ta_cisco_cloud_security_addon_event_logs"
ADDON_NAME = import_declare_test.ta_name


def get_logger(log_name, log_level=logging.INFO):
    log_file = os.path.join(Common().log_path, f"{log_name}.log")
    logger = logging.getLogger(log_name)

    handler_exists = any(
        [True for item in logger.handlers if item.baseFilename == log_file]
    )

    if not handler_exists:
        file_handler = RotatingFileHandler(
            log_file, mode="a", maxBytes=25000000, backupCount=5
        )
        format_string = (
            "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%("
            "funcName)s:%(lineno)d | %(message)s "
        )
        formatter = logging.Formatter(format_string)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(log_level)
        logger.propagate = False

    return logger


logger = get_logger(
    f"{import_declare_test.ta_name}_{os.path.basename(__file__).split('.')[0]}"
)


class MigrationScript(Script):
    def __init__(self):
        super().__init__()
        self.logger = logger
        self._session_key: str = None
        self._inputs: List[Inputs] = []
        self._accounts: List[AWSAccount] = []
        self._event_logs: List[str] = []
        self._cfm = None
        self._event_log_conf_mgr = None

    def get_scheme(self):
        scheme = Scheme("Cisco Secure Access Add-on for Splunk: Accounts and Event Logs Script")
        scheme.description = "This script migrates AWS accounts and event logs for the Cisco Secure Access Add-on for Splunk."
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        return scheme

    def validate_input(self, validation):
        pass

    def stream_events(self, inputs: InputDefinition, ew):
        self._session_key = inputs.metadata.get("session_key")
        try:
            self._cfm = ConfManager(session_key=self._session_key, app=ADDON_NAME)
            self._initialize_event_log_conf_mgr()
            self.perform_migration()
            if not self._event_logs:
                return
            send_ui_notification(
                self._session_key,
                "Accounts and Event Logs creation completed successfully.",
            )
        except Exception as e:
            self.logger.error(f"Error during migration: {e}")
            send_ui_notification(
                self._session_key,
                "Failed to create Accounts and Event Logs. Please check the logs in TA-cisco-cloud-security-addon_migration.log for details.",
                severity="error",
            )
            raise

    def perform_migration(self):
        self.logger.info("Starting migration process")
        # Get inputs to migrate
        self._get_inputs()
        if not self._inputs:
            self.logger.warning("No inputs found for migration")
            return
        self._generate_accounts()
        if not self._accounts:
            self.logger.warning(
                "All inputs already have associated accounts and event logs. Skipping migration."
            )
            return
        self.logger.info(f"Generated {len(self._accounts)} accounts for migration")
        self._generate_event_logs()
        self.logger.info(f"Generated {len(self._event_logs)} event logs for migration")

    def _get_inputs(self):
        self._inputs = Inputs.get_all(self._session_key, clear_credentials=True)

    def _generate_accounts(self):
        self.logger.info("Generating accounts for inputs")
        seen_access_keys = set()
        for input_item in self._inputs:
            if input_item.account_name:
                continue
            if input_item.access_key_id in seen_access_keys:
                continue
            aws_account = self._get_aws_account(input_item.access_key_id)
            if aws_account:
                self.logger.info(
                    f"Account with access key ID '****{input_item.access_key_id[-4:]}' already exists. Skipping account creation."
                )
                self._accounts.append(aws_account)
                seen_access_keys.add(input_item.access_key_id)
                continue
            account_name = f"account_{input_item.access_key_id[-4:]}"
            try:
                account = self._create_account(
                    name=account_name,
                    region=input_item.region,
                    access_key_id=input_item.access_key_id,
                    secret_access_key=input_item.secret_access_key,
                )
                self._accounts.append(account)
            except Exception as e:
                self.logger.error(
                    f"Failed to create account for access key ID '****{input_item.access_key_id[-4:]}'. Continuing with next input."
                )
                continue
            seen_access_keys.add(input_item.access_key_id)

    def _generate_event_logs(self):
        self.logger.info("Generating event logs for accounts")
        for account in self._accounts:
            # Get respective inputs for the account
            account_inputs = list(
                filter(
                    lambda x: (
                        x.access_key_id == account.access_key_id and not x.account_name
                    ),
                    self._inputs,
                )
            )
            prefix_map = self._build_account_prefix_map(account_inputs)
            self._create_event_logs(prefix_map, account)

    def _build_account_prefix_map(self, account_inputs: List[Inputs]):
        """
        Builds a map of prefixes to event types for the given account inputs.
        """
        prefix_type_map = {}
        for input_item in account_inputs:
            dir_prefix = get_dir_prefix(input_item.prefix)
            prefix_with_bucket = f"{input_item.bucket_name}/{dir_prefix}"
            if (
                prefix_with_bucket in prefix_type_map
                and input_item.event_type in prefix_type_map[prefix_with_bucket]
            ):
                self.logger.warning(
                    f"Duplicate event type '{input_item.event_type}' for prefix '{prefix_with_bucket}'. Skipping."
                )
                continue
            if prefix_with_bucket not in prefix_type_map:
                prefix_type_map[prefix_with_bucket] = {}
            prefix_type_map[prefix_with_bucket][input_item.event_type] = input_item
        return prefix_type_map

    def _create_event_logs(
        self, prefix_map: Dict[str, Inputs], account: AWSAccount
    ) -> None:
        """
        Creates event logs for the given account based on the prefix map.
        """
        associated_inputs = []
        # Check for the prefix, already event logs created for the account
        existing_event_logs = self._get_event_logs_with_prefixes(
            list(prefix_map.keys())
        )
        if existing_event_logs:
            associated_prefixes = self._associate_prefixes_with_event_logs(
                prefix_map, existing_event_logs, account.name
            )
            for prefix in associated_prefixes:
                event_inputs = prefix_map.pop(prefix, None)
                if event_inputs:
                    associated_inputs.extend(event_inputs.values())

        for prefix, event_map in prefix_map.copy().items():
            bucket_name, dir_prefix = prefix.split("/", 1)
            event_log_suffix = (
                bucket_name if dir_prefix == "/" else dir_prefix.rstrip("/")[-4:]
            )
            kwargs = {
                "name": f"Event_Log_{event_log_suffix}",
                "aws_account": account.name,
                "bucket_name": bucket_name,
                "dir_prefix": dir_prefix,
                "all_events": False,
                "input_names": "",
            }
            for event_type, input_item in event_map.items():
                kwargs[f"{event_type}_events"] = True
                kwargs[f"{event_type}_events_index"] = input_item.index
                kwargs[f"{event_type}_events_interval"] = input_item.interval
                kwargs[f"{event_type}_events_start_date"] = input_item.start_date
                kwargs[f"{event_type}_events_disabled"] = input_item.disabled
                kwargs["input_names"] += f"{input_item.name},"
            kwargs["input_names"] = kwargs["input_names"].rstrip(",")
            try:
                self._create_event_log_stanza(**kwargs)
            except Exception as e:
                # Remove the respective prefix from the prefix map
                # To prevent account inputs mapping
                prefix_map.pop(prefix, None)
                self.logger.error(f"Failed to create event log stanza '{kwargs['name']}': {e}")
                continue
            # Store the account name and event log name in the inputs
            self._store_account_event_logs_to_inputs(
                list(event_map.values()), account.name, kwargs["name"]
            )
            self._event_logs.append(kwargs["name"])
        # Store the account inputs from event map which is in prefix map
        account_inputs = self._get_account_inputs_from_prefix_map(prefix_map)
        if account_inputs or associated_inputs:
            self._store_account_inputs(account, account_inputs + associated_inputs)

    def _get_aws_account(self, access_key_id: str) -> AWSAccount:
        """
        Retrieves an AWS account by its access key ID.

        Args:
            access_key_id (str): The access key ID of the AWS account.

        Returns:
            AWSAccount: The AWS account object if found, otherwise None.
        """
        return AWSAccount.get_by_access_key_id(self._session_key, access_key_id)

    def _create_account(
        self, name: str, region: str, access_key_id: str, secret_access_key: str
    ) -> AWSAccount:
        """
        Creates an AWS account in the configuration.
        """
        try:
            account = AWSAccount.create(
                name=name,
                session_key=self._session_key,
                region=region,
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
            )
            self.logger.info(f"Created account: {name}")
            return account
        except Exception as e:
            self.logger.error(f"Failed to create account '{name}': {e}")
            raise

    def _create_event_log_stanza(
        self,
        name: str,
        aws_account: str,
        bucket_name: str,
        dir_prefix: str,
        all_events: bool = False,
        **kwargs,
    ):
        """
        Creates an event log stanza in the configuration.
        """
        self._update_event_log_stanza(
            name,
            aws_account=aws_account,
            bucket_name=bucket_name,
            dir_prefix=dir_prefix,
            all_events=all_events,
            **kwargs,
        )

    def _update_event_log_stanza(
        self,
        name: str,
        **kwargs,
    ):
        """
        Updates an existing event log stanza in the configuration.
        """
        if not name:
            raise ValueError("Stanza name cannot be empty.")
        self._event_log_conf_mgr.update(
            name,
            {
                **kwargs,
            },
            None,
        )

    def _associate_prefixes_with_event_logs(
        self,
        prefix_map: Dict[str, Dict[str, Inputs]],
        event_logs: List[EventLogs],
        account_name: str,
    ) -> List[str]:
        """
        Associates the given prefixes with the specified event log name.

        Args:
            prefix_map (Dict[str, Dict[str, Inputs]]): A map of prefixes to event types and their inputs.
            event_logs (List[EventLogs]): A list of EventLogs objects to associate with the prefixes.
            account_name (str): The name of the AWS account associated with the event logs.

        Returns:
            List[str]: A list of prefixes associated with the event logs.
        """
        associated_prefixes = set()
        for event_log in event_logs:
            prefix = f"{event_log.bucket_name}/{event_log.dir_prefix}"
            if prefix in associated_prefixes:
                continue
            event_map = prefix_map.get(prefix, {})
            if not event_map:
                continue
            try:
                self._update_event_log(event_log, event_map)
            except Exception as e:
                self.logger.error(
                    f"Failed to update event log '{event_log.name}' with prefix '{prefix}': {e}"
                )
                prefix_map.pop(prefix, None)
                continue
            self._store_account_event_logs_to_inputs(
                list(event_map.values()), account_name, event_log.name
            )
            associated_prefixes.add(prefix)
        return associated_prefixes

    def _get_account_inputs_from_prefix_map(
        self, prefix_map: Dict[str, Dict[str, Inputs]]
    ) -> List[Inputs]:
        """
        Retrieves the inputs associated with a account from the prefix map.

        Args:
            prefix_map (Dict[str, Dict[str, Inputs]]): A map of prefixes to event types and their inputs.

        Returns:
            List[Inputs]: A list of Inputs objects associated with the account.
        """
        return [
            event_input
            for event_map in prefix_map.values()
            if isinstance(event_map, dict)
            for event_input in event_map.values()
        ]

    def _store_account_inputs(self, account: AWSAccount, inputs: List[Inputs]):
        """
        Stores the inputs associated with the given account name.
        """
        input_names = [input_item.name for input_item in inputs]
        account.update(
            input_names=(
                account.input_names + f",{','.join(input_names)}"
                if account.input_names
                else ",".join(input_names)
            ),
        )

    def _store_account_event_logs_to_inputs(
        self, inputs: List[Inputs], account_name: str, event_log_name: str
    ):
        """
        Store the associated event log and account name in the inputs.
        """
        for input in inputs:
            try:
                input.update(
                account_name=account_name,
                event_log_name=event_log_name,
            )
            except Exception as e:
                self.logger.error(
                    f"Failed to update input '{input.name}' with account '{account_name}' and event log '{event_log_name}': {e}"
                )

    def _get_event_logs_with_prefixes(self, prefixes: List[str]) -> List[EventLogs]:
        """
        Retrieves event logs that match the given prefix.

        Args:
            prefixes (List[str]): A list of prefixes to filter the event logs.
        Returns:
            List[EventLogs]: A list of EventLogs objects that match the prefix.
        """
        return EventLogs.get_by_dir_prefixes(self._session_key, prefixes)

    def _is_event_type_present_in_event_log(
        self, event_log: EventLogs, event_type: str
    ) -> bool:
        """
        Checks if the specified event type exists in the given event log.

        Args:
            event_log (EventLogs): The event log to check.
            event_type (str): The event type to check for.

        Returns:
            bool: True if the event type exists, False otherwise.
        """
        if getattr(event_log.event_mapping["all_events"], "selected"):
            return event_type in [
                input_item.event_type
                for input_item in self._get_input_by_names(
                    event_log.input_names.split(",")
                )
            ]
        return getattr(event_log.event_mapping[f"{event_type}_events"], "selected")

    def _get_input_by_names(self, input_names: List[str]) -> List[Inputs]:
        """
        Retrieves inputs by their names.

        Args:
            input_names (List[str]): A list of input names to retrieve.

        Returns:
            List[Inputs]: A list of Inputs objects that match the provided names.
        """
        if not input_names:
            return []
        return list(
            filter(
                lambda x: x.name in input_names,
                self._inputs,
            )
        )

    def _update_event_log(self, event_log: EventLogs, event_map: Dict[str, Inputs]):
        """
        Updates the event log stanza with the provided event map.

        Args:
            event_log (EventLogs): The event log to update.
            event_map (Dict[str, Inputs]): A map of event types to their corresponding input items.
        """
        if not event_log:
            raise ValueError("Event log cannot be None.")
        if not event_map:
            raise ValueError("Event map cannot be empty.")
        update_kwargs = {}
        # Update the event log stanza with the new event type
        for event_type, input_item in event_map.copy().items():
            if self._is_event_type_present_in_event_log(event_log, event_type):
                self.logger.info(
                    f"Event type '{event_type}' already exists in event log '{event_log.name}'. Skipping update."
                )
                event_map.pop(event_type)
                continue
            if not getattr(event_log.event_mapping["all_events"], "selected"):
                update_kwargs[f"{event_type}_events"] = True
                update_kwargs[f"{event_type}_events_index"] = input_item.index
                update_kwargs[f"{event_type}_events_interval"] = input_item.interval
                update_kwargs[f"{event_type}_events_start_date"] = input_item.start_date
                update_kwargs[f"{event_type}_events_disabled"] = input_item.disabled
            update_kwargs["input_names"] = (
                f"{update_kwargs['input_names']},{input_item.name}"
                if "input_names" in update_kwargs
                else f"{event_log.input_names},{input_item.name}"
            )
        if update_kwargs:
            self._update_event_log_stanza(
                event_log.name,
                **update_kwargs,
            )

    def _initialize_event_log_conf_mgr(self):
        """
        Initializes the configuration manager for event logs.
        """
        try:
            self._event_log_conf_mgr = self._cfm.get_conf(EVENT_LOGS_CONF_NAME)
            # Observed after the upgrade, the splunk is triggering the script two times. To prevent any issues related to this behavior, adding a sleep of 60 seconds.
            self.logger.info(
                "Sleep for 60 seconds to ensure the configuration is ready."
            )
            time.sleep(60)
        except ConfManagerException as e:
            try:
                self._event_log_conf_mgr = self._cfm.create_conf(
                    EVENT_LOGS_CONF_NAME,
                )
            except Exception as e:
                # Occasionally, create_conf() raises an exception with status code 200. To prevent script failure, check for the error message and try to get the configuration.
                if "Unexpected status code 200" not in str(e):
                    self.logger.error(f"Failed to get/create event log configuration: {e}")
                    raise
                self._event_log_conf_mgr = self._cfm.get_conf(EVENT_LOGS_CONF_NAME)


if __name__ == "__main__":
    logger.info(f"Migration script started: {sys.argv}")
    exit_code = MigrationScript().run(sys.argv)
    logger.info("Migration script finished")
    sys.exit(exit_code)
