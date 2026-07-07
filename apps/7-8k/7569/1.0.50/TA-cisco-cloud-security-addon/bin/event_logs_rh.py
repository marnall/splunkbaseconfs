import import_declare_test
from typing import Dict, List, Optional, Tuple, Union
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from solnlib import conf_manager
from solnlib.soln_exceptions import ConfManagerException
from inputs import Inputs
from event_logs import EventLogs as EventLog
from utils import str_to_boolean, send_ui_notification, S3Utility
from exceptions import S3ValidationError
from data_input_manager import DataInputManager
import re

class EventLogs(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self._ta_name = import_declare_test.ta_name
        self._aws_account_conf_name = "ta_cisco_cloud_security_addon_aws_account"
        self._cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            app=self._ta_name,
            realm=f"__REST_CREDENTIAL__#{self._ta_name}#configs/conf-{self._aws_account_conf_name}",
        )
        self._aws_account_conf = self._get_aws_account_conf()
        self._s3_utility = S3Utility(self.getSessionKey())
        self._event_types = (
            "audit",
            "dns",
            "firewall",
            "proxy",
            "dlp",
            "intrusion",
            "ravpn",
            "ztna",
            "ztnaflow",
            "fileevent",
            "ztnaenrollment",
            "ntg",
        )

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        try:
            event_log_name = str(self.callerArgs.id)
            current_event_log_fields = self._get_current_event_log_fields(event_log_name)
            self.payload["input_names"] = current_event_log_fields.input_names
            # Identify the changes done in the payload by comparing with existing event log field values
            changes = self._get_changes_from_payload(current_event_log_fields)
            # If no changes are detected, raise an error
            if not changes:
                raise RestError(
                    status=400,
                    message="No changes detected in the event log configuration.",
                )
            self._handle_edit_event_log(event_log_name, current_event_log_fields, changes)
            
            # Handle data input management
            data_input_manager = DataInputManager(self.getSessionKey())
            
            # Check if auto_discovery_enabled status changed
            # auto_discovery_enabled = str(self.payload.get("auto_discovery_enabled", "0")) == "1"
            new_auto_discovery = str_to_boolean(self.payload.get("auto_discovery_enabled", "0"))
            
            # Check if data input already exists
            input_exists = False
            try:
                # Try to get the existing data input to check if it exists
                data_input_manager.get(input_name=event_log_name)
                input_exists = True
            except Exception:
                input_exists = False
            
            if new_auto_discovery and not input_exists:
                # Auto discovery is enabled and input doesn't exist - create it
                data = {
                    "name": str(event_log_name),
                    "interval": "86400",
                    "handler": "EVENT_LOG"
                }
                data_input_manager.create(
                    input_name=event_log_name,
                    data=data
                )
            elif not new_auto_discovery and input_exists:
                # Auto discovery is disabled and input exists - delete it
                data_input_manager.delete(
                    input_name=event_log_name
                )
            
            AdminExternalHandler.handleEdit(self, confInfo)
        except RestError as e:
            raise
        except Exception as e:
            raise RestError(status=500, message=f"An unexpected error occurred while editing the event log. {str(e)}")
    
    def handleCreate(self, confInfo):

        data_input_manager = DataInputManager(self.getSessionKey())
        event_log_name = str(self.callerArgs.id)
        self._handle_create_event_log(event_log_name)
        new_auto_discovery = str_to_boolean(self.payload.get("auto_discovery_enabled", "0"))

        if new_auto_discovery:
            data = {
                "name": str(event_log_name),
                "interval": "86400",
                "handler": "EVENT_LOG"
            }
            data_input_manager.create(
                input_name=event_log_name,
                data=data
            )
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        event_log_name = str(self.callerArgs.id)
        current_event_log_fields = self._get_current_event_log_fields(event_log_name)
        self._handle_remove_event_log(event_log_name, current_event_log_fields)
        if str_to_boolean(current_event_log_fields.auto_discovery_enabled):
            data_input_manager = DataInputManager(self.getSessionKey())
            data_input_manager.delete(
                input_name=event_log_name
            )
        AdminExternalHandler.handleRemove(self, confInfo)

    def _get_aws_account_conf(self):
        """
        Retrieves the AWS account configuration from the configuration manager.
        """
        try:
            return self._cfm.get_conf(self._aws_account_conf_name)
        except ConfManagerException:
            # If the configuration does not exist, create it
            return self._create_aws_account_conf()

    def _create_aws_account_conf(self):
        """
        Creates a new AWS account configuration in the configuration manager.
        """
        try:
            return self._cfm.create_conf(self._aws_account_conf_name)
        except Exception:
            raise RestError(
                status=400, message="Unable to get/create AWS account configuration."
            )

    def _get_account(
        self,
        account: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Retrieves AWS account information from the configuration file.

        Args:
            account (Optional[str]): The name of the AWS account to retrieve. If None, the account
                                     is taken from the payload.

        Returns:
            Dict[str, str]: A dictionary containing AWS account information.
        """
        if account is None:
            account = self.payload.get("aws_account")
        if not account:
            raise RestError(status=400, message="AWS account is required.")

        return self._aws_account_conf.get(account)

    def _get_dir_prefixes(
        self,
        aws_account: Dict[str, str],
        bucket_name: Optional[str] = None,
        dir_prefix: Optional[str] = None,
    ) -> List[str]:
        """
        Retrieves directory prefixes from the s3 bucket.

        Args:
            aws_account (Dict[str, str]): AWS account information.
            bucket_name (Optional[str]): The name of the S3 bucket. If None, it is taken from the payload.
            dir_prefix (Optional[str]): The directory prefix to list. If None, it is taken from the payload.

        Returns:
            List[str]: A list of directory prefixes in the S3 bucket.

        Raises:
            RestError: If the AWS account is not provided or if the bucket does not exist.
        """
        if not aws_account:
            raise ValueError("AWS account is required.")
        if bucket_name is None:
            bucket_name = self.payload.get("bucket_name")
        if not bucket_name:
            raise RestError(status=400, message="Bucket name is required.")
        if dir_prefix is None:
            dir_prefix = self.payload.get("dir_prefix")
        if not dir_prefix:
            raise RestError(status=400, message="Directory prefix is required.")
        prefix = (
            ""
            if dir_prefix == "/"
            else dir_prefix if dir_prefix.endswith("/") else dir_prefix + "/"
        )
        try:
            prefixes = self._s3_utility.get_event_type_prefixes(
                access_key_id=aws_account.get("access_key_id", ""),
                secret_access_key=aws_account.get("secret_access_key", ""),
                bucket_name=bucket_name,
                region=aws_account.get("region", ""),
                prefix=prefix,
            )
            return prefixes

        except S3ValidationError as e:
            raise RestError(
                status=400,
                message=e.message,
            )
        
    def _auto_extracted_prefix_to_event_type_mapping(
        self, dir_prefixes: List[str], current_event_log_fields: EventLog
    ) -> Dict[str, str]:
        """
        Generates a mapping of event types to directory prefixes for auto-extracted event types
        based on the provided directory prefixes and the current event log's input names.

        Args:
            dir_prefixes (List[str]): List of directory prefixes to evaluate.
            current_event_log_fields (List[str]): The current event log fields containing input names.

        Returns:
            Dict[str, str]: Dictionary mapping event types (auto-extracted from prefix) to their normalized directory prefixes.
        """
        mapping = {}
        for prefix in dir_prefixes:
            # Normalize the directory prefix to ensure it ends with a slash
            norm_prefix = prefix if prefix.endswith("/") else f"{prefix}/"

            event_type = re.search(r'\b(\w+)logs\b', norm_prefix).group(1) 
            if event_type in (i.split("_")[-1] for i in current_event_log_fields.input_names.split(",")):
                mapping[event_type] = norm_prefix   
            
        return mapping  

    def _get_prefix_to_event_type_mapping(
        self, dir_prefixes: List[str]
    ) -> Dict[str, str]:
        """
        Retrieves a mapping of event types to directory prefixes for a list of directory prefixes.

        Args:
            dir_prefixes (List[str]): The list of directory prefixes to check for event types.

        Returns:
            Dict[str, str]: A dictionary mapping event types to directory prefixes.
        """
        mapping = {}
        for prefix in dir_prefixes:
            # Normalize the directory prefix to ensure it ends with a slash
            norm_prefix = prefix if prefix.endswith("/") else f"{prefix}/"

            event_type = re.search(r'\b(\w+)logs\b', norm_prefix).group(1) 
            if event_type in self._event_types:
                mapping[event_type] = norm_prefix  

        if not mapping:
            raise RestError(
                status=400,
                message="No directory prefixes found for the specified event types.",
            )
        return mapping

    def _handle_create_event_log(self, event_log_name: str) -> None:
        """
        Handles the creation of an event log by creating inputs for all or selected event types.

        Args:
            event_log_name (str): The name of the event log to be created.

        Raises:
            RestError: If an error occurs while creating the event log.
        """
        aws_account_name = self.payload.get("aws_account")
        aws_account = self._get_account()
        dir_prefixes = self._get_dir_prefixes(aws_account)
        event_type_to_dir_mapping = self._get_prefix_to_event_type_mapping(dir_prefixes)

        if self._is_all_events():
            new_inputs, failed_event_types = self._create_all_event_inputs(
                event_log_name, event_type_to_dir_mapping, aws_account_name, aws_account
            )
        else:
            new_inputs, failed_event_types = self._create_selected_event_inputs(
                event_log_name, event_type_to_dir_mapping, aws_account_name, aws_account
            )
            self._set_event_types_disabled_false(
                [new_inputs.event_type for new_inputs in new_inputs]
            )
            if failed_event_types:
                self._reset_selected_event_type_fields(failed_event_types)

        if not new_inputs:
            raise RestError(status=400, message="No inputs were created.")

        if failed_event_types:
            send_ui_notification(
                self.getSessionKey(),
                f"Failed to create inputs for event types: {', '.join(failed_event_types)} in event log '{event_log_name}'. Please retry by editing the event log.",
                "error",
            )

        input_names = [input_instance.name for input_instance in new_inputs]
        self._update_event_log_input_names(input_names)
        self._update_aws_account_input_names(
            aws_account_name,
            input_names,
            aws_account_input_names=aws_account.get("input_names", ""),
        )

    def _create_all_event_inputs(
        self,
        event_log_name: str,
        event_type_to_dir_mapping: Dict[str, str],
        aws_account_name: str,
        aws_account: Dict[str, str],
    ) -> Tuple[List[Inputs], List[str]]:
        """
        Creates inputs for all event types based on the provided mapping.

        Args:
            event_log_name (str): The name of the event log.
            event_type_to_dir_mapping (Dict[str, str]): A mapping of event types to directory prefixes.
            aws_account_name (str): The name of the AWS account.
            aws_account (Dict[str, str]): AWS account information.

        Returns:
            Tuple[List[Inputs], List[str]]: A tuple containing a list of created Inputs instances and a list of failed event types.

        Raises:
            RestError: If an error occurs while creating inputs.
        """
        new_inputs = []
        failed_event_types = []
        for event_type, dir_prefix in event_type_to_dir_mapping.items():
            try:
                input_instance = Inputs.create(
                    session_key=self.getSessionKey(),
                    name=f"{event_log_name}_{event_type}",
                    interval=self.payload.get("all_events_interval", 60),
                    index=self.payload.get("all_events_index", "default"),
                    region=aws_account.get("region", ""),
                    access_key_id=aws_account.get("access_key_id", ""),
                    secret_access_key=aws_account.get("secret_access_key", ""),
                    bucket_name=self.payload.get("bucket_name", ""),
                    prefix=dir_prefix,
                    start_date=self.payload.get("all_events_start_date", ""),
                    event_type=event_type,
                    account_name=aws_account_name,
                    event_log_name=event_log_name,
                )
                new_inputs.append(input_instance)
            except Exception:
                failed_event_types.append(event_type)

        return new_inputs, failed_event_types

    def _create_selected_event_inputs(
        self,
        event_log_name: str,
        event_type_to_dir_mapping: Dict[str, str],
        aws_account_name: str,
        aws_account: Dict[str, str],
    ) -> Tuple[List[Inputs], List[str]]:
        """
        Creates inputs for selected event types based on the provided mapping.

        Args:
            event_log_name (str): The name of the event log.
            event_type_to_dir_mapping (Dict[str, str]): A mapping of event types to directory prefixes.
            aws_account_name (str): The name of the AWS account.
            aws_account (Dict[str, str]): AWS account information.

        Returns:
            Tuple[List[Inputs], List[str]]: A tuple containing a list of created Inputs instances and a list of failed event types.
        Raises:
            RestError: If an error occurs while creating inputs.
        """
        # the selected event types have a boolean field. For example dns, dns_events = True
        selected_event_types = [
            event_type
            for event_type in self._event_types
            if str_to_boolean(self.payload.get(f"{event_type}_events"))
        ]
        if not selected_event_types:
            raise RestError(
                status=400, message="At least one event type must be selected."
            )
        # Ensure that the selected event types are in the mapping
        for event_type in selected_event_types:
            if event_type not in event_type_to_dir_mapping:
                raise RestError(
                    status=400,
                    message=f"Directory prefix for {event_type} not found.",
                )
        # Create inputs for each selected event type
        new_inputs = []
        failed_event_types = []
        for event_type in selected_event_types:
            dir_prefix = event_type_to_dir_mapping.get(event_type)
            try:
                input_instance = Inputs.create(
                    session_key=self.getSessionKey(),
                    name=f"{event_log_name}_{event_type}",
                    interval=self.payload.get(f"{event_type}_events_interval", 60),
                    index=self.payload.get(f"{event_type}_events_index", "default"),
                    region=aws_account.get("region", ""),
                    access_key_id=aws_account.get("access_key_id", ""),
                    secret_access_key=aws_account.get("secret_access_key", ""),
                    bucket_name=self.payload.get("bucket_name", ""),
                    prefix=dir_prefix,
                    start_date=self.payload.get(f"{event_type}_events_start_date", ""),
                    event_type=event_type,
                    account_name=aws_account_name,
                    event_log_name=event_log_name,
                )
                new_inputs.append(input_instance)
            except Exception as e:
                failed_event_types.append(event_type)
        return new_inputs, failed_event_types

    def _handle_remove_event_log(self, event_log_name: str, current_event_log_fields: EventLog) -> None:
        """
        Deletes inputs associated with the specified event log name.

        Args:
            event_log_name (str): The name of the event log whose inputs should be deleted.
            current_event_log_fields (EventLog): The current event log fields.

        Raises:
            RestError: If an error occurs while deleting inputs.
        """
        if not current_event_log_fields.input_names:
            return
        input_names = self._get_event_log_input_names(current_event_log_fields)
        event_log_inputs = self._get_event_log_inputs(input_names=input_names)
        failed_input_names = self._delete_inputs(event_log_inputs)
        if failed_input_names:
            input_names = [
                input_name
                for input_name in input_names
                if input_name not in failed_input_names
            ]
        if not input_names:
            raise RestError(
                status=400, message=f"Failed to delete inputs. Please retry."
            )
        self._remove_inputs_from_aws_account(
            current_event_log_fields.aws_account, input_names
        )
        if failed_input_names:
            raise RestError(
                status=400,
                message=f"Failed to delete inputs: {', '.join(failed_input_names)}. Please retry.",
            )

    def _get_event_log_inputs(
        self,
        event_log_name: Optional[str] = None,
        input_names: Optional[List[str]] = None,
    ) -> List[Inputs]:
        """
        Retrieves Inputs instances associated with the specified event log name.

        Args:
            event_log_name (Optional[str]): The name of the event log whose inputs are being retrieved.
            input_names (Optional[List[str]]): A list of input names to filter by.
        Returns:
            List[Inputs]: A list of Inputs instances containing input information.

        Raises:
            ValueError: If event_log_name is not provided.
            RestError: If an error occurs while retrieving inputs.
        """
        if input_names is None and not event_log_name:
            raise ValueError("Event log name is required.")
        if not input_names:
            current_event_log_fields = self._get_current_event_log_fields(
                event_log_name
            )
            input_names = self._get_event_log_input_names(current_event_log_fields)
        if not input_names:
            raise RestError(
                status=400, message=f"No inputs found for event log: {event_log_name}"
            )
        try:
            return Inputs.get_inputs_with_filters(
                session_key=self.getSessionKey(),
                name=input_names,
            )
        except Exception as e:
            raise RestError(status=400, message=f"Failed to retrieve inputs: {str(e)}")

    def _get_current_event_log_fields(self, event_log_name: str) -> Optional[EventLog]:
        """
        Retrieve the current event log fields for the specified event log name.

        Args:
            event_log_name (str): The name of the event log whose fields are being retrieved.

        Returns:
            Optional[EventLog]: An instance of EventLog containing the current fields, or None if not found.
        """
        try:
            return EventLog(event_log_name, self.getSessionKey())
        except Exception as e:
            raise RestError(
                status=400, message=f"Failed to retrieve event log fields: {str(e)}"
            )

    def _get_changes_from_payload(
        self, current_event_log_fields: EventLog
    ) -> Dict[str, str]:
        """
        Compare the provided payload with the existing event log configuration and identify any changes.

        Args:
            current_event_log_fields (EventLog): The current event log fields to compare against.

        Returns:
            Dict[str, str]: A dictionary containing the fields that have changed and their new values.

        Raises:
            RestError: If the event log fields cannot be retrieved due to an exception.
        """
        changes = {}
        # Top-level fields
        for field in self._get_common_fields():
            new_value = self.payload.get(field)
            if (
                new_value is not None
                and getattr(current_event_log_fields, field, None) != new_value
            ):
                changes[field] = new_value

        # Check auto_discovery_enabled separately
        if "auto_discovery_enabled" in self.payload:
            new_auto_discovery = str_to_boolean(self.payload.get("auto_discovery_enabled", "0"))
            current_auto_discovery = getattr(current_event_log_fields, 'auto_discovery_enabled', False)
            if current_auto_discovery != new_auto_discovery:
                changes["auto_discovery_enabled"] = new_auto_discovery

        # Event type fields
        for event_type, event_model in current_event_log_fields.event_mapping.items():
            for attr in self._get_field_suffixes():
                payload_key = (
                    f"{event_type}" if attr == "selected" else f"{event_type}_{attr}"
                )
                if payload_key in self.payload:
                    new_value = self.payload.get(payload_key)
                    old_value = getattr(event_model, attr, None)
                    if attr in ("selected", "disabled"):
                        new_value = str_to_boolean(new_value)
                        old_value = str_to_boolean(old_value)
                    if old_value != new_value:
                        changes[payload_key] = new_value
        return changes

    def _get_event_log_input_names(self, event_log_fields: EventLog) -> List[str]:
        """
        Get the input names from the event log fields.

        Args:
            event_log_fields (EventLog): The event log fields containing input names.

        Returns:
            List[str]: A list of input names.
        """
        return (
            event_log_fields.input_names.split(",")
            if event_log_fields.input_names
            else []
        )

    def _handle_edit_event_log(
        self,
        event_log_name: str,
        current_event_log_fields: EventLog,
        changes: Dict[str, str],
    ) -> None:
        """
        Handle the changes made to the event log configuration.

        Args:
            event_log_name (str): The name of the event log being modified.
            current_event_log_fields (EventLog): The current event log fields.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.

        Raises:
            RestError: If an error occurs while updating the event log configuration.
        """
        account_name = self.payload.get("aws_account")
        account = self._get_account()
        dir_prefixes = self._get_dir_prefixes(account)
        event_type_to_dir_mapping = self._get_prefix_to_event_type_mapping(dir_prefixes)
        auto_extracted_event_type_to_dir_mapping = self._auto_extracted_prefix_to_event_type_mapping(dir_prefixes, current_event_log_fields)
        event_type_to_dir_mapping.update(auto_extracted_event_type_to_dir_mapping) 

        if "all_events" in changes and not changes.get("all_events"):
            self._handle_all_events_to_selected_events(
                event_log_name, current_event_log_fields, changes
            )
        elif self._is_all_events():
            self._update_all_event_inputs(
                event_log_name,
                event_type_to_dir_mapping,
                changes,
                current_event_log_fields,
                account_name,
                account,
            )
        else:
            self._update_selected_event_inputs(
                event_log_name,
                event_type_to_dir_mapping,
                current_event_log_fields,
                changes,
                account_name,
                account,
            )

    def _handle_all_events_to_selected_events(
        self,
        event_log_name: str,
        current_event_log_fields: EventLog,
        changes: Dict[str, str],
    ) -> None:
        """
        Handle the transition from all events to selected events in the event log configuration.

        Args:
            event_log_name (str): The name of the event log being modified.
            current_event_log_fields (EventLog): The current event log fields.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.

        Raises:
            RestError: If an error occurs while updating the event log configuration.
        """
        selected_event_types = [
            event_type
            for event_type in self._event_types
            if str_to_boolean(self.payload.get(f"{event_type}_events"))
        ]
        if selected_event_types:
            raise RestError(
                status=400,
                message="Selecting event types is not allowed when transitioning from all events.",
            )
        if self._is_common_fields_changed(changes):
            raise RestError(
                status=400,
                message="Changing AWS account, bucket name and dir prefix fields are not allowed when transitioning from all events to selected events.",
            )
        # Get the existing inputs for the event log
        event_log_inputs = self._get_event_log_inputs(
            event_log_name=event_log_name,
            input_names=self._get_event_log_input_names(current_event_log_fields),
        )
        if not event_log_inputs:
            raise RestError(
                status=400,
                message=f"No inputs found for event log: {event_log_name}",
            )
        # Update the event log fields to reflect the transition from all events to selected events
        self._populate_event_log_fields_from_all_events(
            event_log_inputs, current_event_log_fields
        )

    def _update_all_event_inputs(
        self,
        event_log_name: str,
        event_type_to_dir_mapping: Dict[str, str],
        changes: Dict[str, str],
        current_event_log_fields: EventLog,
        account_name: str,
        aws_account: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Update inputs for all event types based on the provided mapping.

        Args:
            event_log_name (str): The name of the event log.
            event_type_to_dir_mapping (Dict[str, str]): A mapping of event types to directory prefixes.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.
            current_event_log_fields (EventLog): The current event log fields.
            account_name (str): The name of the AWS account.
            aws_account (Optional[Dict[str, str]]): AWS account information.

        Raises:
            RestError: If an error occurs while updating inputs.
        """
        is_aws_account_changed = self._is_aws_account_changed(changes)
        if is_aws_account_changed and not aws_account:
            aws_account = self._get_account()
        input_names = self._get_event_log_input_names(current_event_log_fields)
        event_log_inputs = self._get_event_log_inputs(input_names=input_names)
        if not event_log_inputs:
            raise RestError(
                status=400,
                message=f"No inputs found for event log: {event_log_name}",
            )
        # Identify if a respective input doesnot exist for the event type
        existing_event_types = [
            input_instance.event_type for input_instance in event_log_inputs
        ]
        # If directory prefixes for the existing event types are not in the mapping, raise an error
        for input_instance in event_log_inputs:
            # Skip validation for auto-discovered event types that might not be in the predefined mapping
            if input_instance.event_type not in self._event_types:
                continue
            if input_instance.event_type not in event_type_to_dir_mapping:
                raise RestError(
                    status=400,
                    message=f"Directory prefix for {input_instance.event_type} not found in the mapping.",
                )
        if self._is_transitioning_to_all_events(changes):
            self._apply_all_event_disabled_changes(changes)
        # First, create inputs for event types that do not exist
        new_inputs, failed_event_types = self._create_all_events_missing_inputs(
            event_log_name,
            existing_event_types,
            event_type_to_dir_mapping,
            account_name,
            aws_account,
        )
        # Update existing inputs with the changes
        failed_input_updates = self._update_existing_inputs(
            event_log_inputs,
            event_type_to_dir_mapping,
            changes,
            account_name,
            aws_account,
            all_events=True,
        )
        failed_input_disabling = None
        # If all events are disabled, disable the newly created inputs
        if new_inputs and changes.get("all_events_disabled"):
            failed_input_disabling = self._disable_inputs(new_inputs)

        if failed_input_updates or failed_input_disabling:
            self._restore_all_events_field_values(current_event_log_fields)
            if self._is_common_fields_changed(changes):
                self._restore_common_field_values(current_event_log_fields)

        # Handle different failure scenarios with appropriate messages
        error_message = self._build_failure_message(
            failed_event_types, failed_input_updates, failed_input_disabling
        )

        if error_message:
            combined_message = f"{error_message} in event log '{event_log_name}'. Please refresh the page and retry making the changes."
            send_ui_notification(
                self.getSessionKey(),
                combined_message,
                "error",
            )

        # If transitioning from selected events to all events, uncheck the selected event types
        if "all_events" in changes:
            self._uncheck_selected_event_types(existing_event_types)
            for event_type in existing_event_types:
                self._clear_event_log_field_value(f"{event_type}_events_start_date")

        if not new_inputs and not is_aws_account_changed:
            return

        new_inputs = [new_input.name for new_input in new_inputs]
        if is_aws_account_changed and failed_input_updates:
            current_account_fields = self._get_account(
                current_event_log_fields.aws_account
            )
        # If aws_account is changed, remove the input names from the current aws_account and add them to the new aws_account
        if is_aws_account_changed and not failed_input_updates:
            self._remove_inputs_from_aws_account(
                current_event_log_fields.aws_account, input_names
            )
        self._update_aws_account_input_names(
            (
                current_event_log_fields.aws_account
                if (is_aws_account_changed and failed_input_updates)
                else account_name
            ),
            (
                (input_names + new_inputs)
                if (is_aws_account_changed and not failed_input_updates)
                else new_inputs
            ),
            aws_account_input_names=(
                current_account_fields.get("input_names", "")
                if (is_aws_account_changed and failed_input_updates)
                else aws_account.get("input_names", "")
            ),
        )
        self._update_event_log_input_names(input_names + new_inputs)

    def _update_selected_event_inputs(
        self,
        event_log_name: str,
        event_type_to_dir_mapping: Dict[str, str],
        current_event_log_fields: EventLog,
        changes: Dict[str, str],
        account_name: str,
        aws_account: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Update inputs for selected event types based on the provided mapping.

        Args:
            event_log_name (str): The name of the event log.
            event_type_to_dir_mapping (Dict[str, str]): A mapping of event types to directory prefixes.
            current_event_log_fields (EventLog): The current event log fields.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.
            account_name (str): The name of the AWS account.
            aws_account (Optional[Dict[str, str]]): AWS account information.

        Raises:
            RestError: If an error occurs while updating inputs.
        """
        is_aws_account_changed = self._is_aws_account_changed(changes)
        if is_aws_account_changed and not aws_account:
            aws_account = self._get_account()
        # Get existing inputs for the event log
        input_names = self._get_event_log_input_names(current_event_log_fields)
        event_log_inputs = self._get_event_log_inputs(input_names=input_names)
        if not event_log_inputs:
            raise RestError(
                status=400,
                message=f"No inputs found for event log: {event_log_name}",
            )
        # Identify if a new input needs to be created for the event type
        new_inputs, failed_event_types = self._create_new_selected_inputs(
            event_log_name,
            event_type_to_dir_mapping,
            changes,
            account_name,
            aws_account,
        )
        self._set_event_types_disabled_false(
            [new_input.event_type for new_input in new_inputs]
        )
        # Delete inputs if the selected event type is False in the changes
        inputs_to_delete, unsuccessful_deletes = self._delete_unselected_inputs(
            event_log_inputs, changes
        )
        deleted_inputs = (
            [
                input_instance.name
                for input_instance in inputs_to_delete
                if input_instance.name not in unsuccessful_deletes
            ]
            if inputs_to_delete
            else []
        )
        # If inputs were deleted, remove them from the event_log_inputs list
        if deleted_inputs:
            event_log_inputs = [
                input_instance
                for input_instance in event_log_inputs
                if input_instance.name not in deleted_inputs
            ]
        # Update existing inputs with the changes
        input_update_failures = self._update_existing_inputs(
            event_log_inputs,
            event_type_to_dir_mapping,
            changes,
            account_name,
            aws_account,
        )

        if failed_event_types:
            self._uncheck_selected_event_types(failed_event_types)
            for event_type in failed_event_types:
                self._clear_event_log_field_value(f"{event_type}_events_start_date")

        if input_update_failures:
            changed_fields = [
                f"{input_instance.event_type}_events_{suffix}"
                for input_instance in event_log_inputs
                if input_instance.name in input_update_failures
                for suffix in self._get_field_suffixes()[1:]
            ]
            self._restore_selected_event_field_values(
                current_event_log_fields, changed_fields
            )
            if self._is_common_fields_changed(changes):
                self._restore_common_field_values(current_event_log_fields)

        if unsuccessful_deletes:
            self._check_selected_event_types(
                [
                    input_instance.event_type
                    for input_instance in inputs_to_delete
                    if input_instance.name in unsuccessful_deletes
                ]
            )

        error_message = self._build_failure_message(
            failed_event_types,
            input_update_failures,
            failed_input_deletes=unsuccessful_deletes,
        )
        if error_message:
            combined_message = f"{error_message} in event log '{event_log_name}'. Please refresh the page and retry making the changes."
            send_ui_notification(
                self.getSessionKey(),
                combined_message,
                "error",
            )
        if not new_inputs and not deleted_inputs and not is_aws_account_changed:
            return
        # Update the input names in the event log fields
        event_log_inputs = [input_instance.name for input_instance in event_log_inputs]
        new_inputs = [new_input.name for new_input in new_inputs]
        # If aws_account is changed, remove the input names from the current aws_account and add them to the new aws_account
        if is_aws_account_changed and input_update_failures:
            current_account_fields = self._get_account(
                current_event_log_fields.aws_account
            )
        if is_aws_account_changed and not input_update_failures:
            self._remove_inputs_from_aws_account(
                current_event_log_fields.aws_account, input_names
            )
        # If aws_account is not changed, just update the input names in the event log fields
        self._update_aws_account_input_names(
            (
                current_event_log_fields.aws_account
                if (is_aws_account_changed and input_update_failures)
                else account_name
            ),
            (
                (event_log_inputs + new_inputs)
                if (is_aws_account_changed and not input_update_failures)
                else new_inputs
            ),
            deleted_inputs if (not is_aws_account_changed and deleted_inputs) else None,
            aws_account_input_names=(
                current_account_fields.get("input_names", "")
                if (is_aws_account_changed and input_update_failures)
                else aws_account.get("input_names", "")
            ),
        )
        self._update_event_log_input_names(event_log_inputs + new_inputs)

    def _create_all_events_missing_inputs(
        self,
        event_log_name: str,
        existing_event_types: List[str],
        event_type_to_dir_mapping: Dict[str, str],
        account_name: str,
        aws_account: Dict[str, str],
    ) -> Tuple[List[Inputs], List[str]]:
        """
        Create inputs for any missing event types based on the provided mapping.

        Args:
            event_log_name (str): The name of the event log.
            existing_event_types (List[str]): A list of existing event types for which inputs have already been created.
            event_type_to_dir_mapping (Dict[str, str]): A mapping of event types to directory prefixes.
            account_name (str): The name of the AWS account.
            aws_account (Dict[str, str]): AWS account information.

        Returns:
            Tuple[List[Inputs], List[str]]: A tuple containing a list of created Inputs instances and a list of failed event types.

        Raises:
            RestError: If an error occurs while creating inputs.
        """
        inputs = []
        failed_event_types = []
        for event_type, dir_prefix in event_type_to_dir_mapping.items():
            if event_type in existing_event_types:
                continue
            try:
                new_input_instance = Inputs.create(
                    session_key=self.getSessionKey(),
                    name=f"{event_log_name}_{event_type}",
                    interval=self.payload.get("all_events_interval", 600),
                    index=self.payload.get("all_events_index", "default"),
                    region=aws_account.get("region", ""),
                    access_key_id=aws_account.get("access_key_id", ""),
                    secret_access_key=aws_account.get("secret_access_key", ""),
                    bucket_name=self.payload.get("bucket_name", ""),
                    prefix=dir_prefix,
                    start_date=self.payload.get("all_events_start_date", ""),
                    event_type=event_type,
                    account_name=account_name,
                    event_log_name=event_log_name,
                )
                inputs.append(new_input_instance)
            except Exception:
                failed_event_types.append(event_type)
        return inputs, failed_event_types

    def _create_new_selected_inputs(
        self,
        event_log_name: str,
        event_type_to_dir_mapping: Dict[str, str],
        changes: Dict[str, str],
        aws_account_name: str,
        aws_account: Dict[str, str],
    ) -> Tuple[List[Inputs], List[str]]:
        """
        Create inputs for selected event types based on the provided mapping.

        Args:
            event_log_name (str): The name of the event log.
            event_type_to_dir_mapping (Dict[str, str]): A mapping of event types to directory prefixes.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.
            aws_account_name (str): The name of the AWS account.
            aws_account (Dict[str, str]): AWS account information.

        Returns:
            Tuple[List[Inputs], List[str]]: A tuple containing a list of created Inputs instances and a list of failed event types.

        Raises:
            RestError: If an error occurs while creating inputs.
        """
        inputs = []
        failed_event_types = []
        # Identify the inputs that need to be created based on the changes
        new_event_types = [
            event_type
            for event_type in self._event_types
            if changes.get(f"{event_type}_events")
        ]
        for event_type in new_event_types:
            if event_type not in event_type_to_dir_mapping:
                raise RestError(
                    status=400,
                    message=f"Directory prefix for {event_type} not found.",
                )
        for event_type in new_event_types:
            dir_prefix = event_type_to_dir_mapping[event_type]
            try:
                new_input_instance = Inputs.create(
                    session_key=self.getSessionKey(),
                    name=f"{event_log_name}_{event_type}",
                    interval=changes.get(f"{event_type}_events_interval", 600),
                    index=changes.get(f"{event_type}_events_index", "default"),
                    region=aws_account.get("region", ""),
                    access_key_id=aws_account.get("access_key_id", ""),
                    secret_access_key=aws_account.get("secret_access_key", ""),
                    bucket_name=self.payload.get("bucket_name", ""),
                    prefix=dir_prefix,
                    start_date=changes.get(f"{event_type}_events_start_date", ""),
                    event_type=event_type,
                    account_name=aws_account_name,
                    event_log_name=event_log_name,
                )
                inputs.append(new_input_instance)
            except Exception:
                failed_event_types.append(event_type)

        return inputs, failed_event_types

    def _update_existing_inputs(
        self,
        event_log_inputs: List[Inputs],
        event_type_to_dir_mapping: Dict[str, str],
        changes: Dict[str, str],
        account_name: str,
        aws_account: Optional[Dict[str, str]] = None,
        all_events: bool = False,
    ) -> List[str]:
        """
        Update existing inputs based on the provided changes.

        Args:
            event_log_inputs (List[Inputs]): A list of existing Inputs instances to be updated.
            event_type_to_dir_mapping (Dict[str, str]): A mapping of event types to directory prefixes.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.
            account_name (str): The name of the AWS account.
            aws_account (Optional[Dict[str, str]]): AWS account information.
            all_events (bool): Whether to update all events or only selected ones.

        Returns:
            List[str]: A list of input names that failed to update.

        Raises:
            ValueError: If the AWS account is required but not provided.
            RestError: If an error occurs while updating inputs.
        """
        is_aws_account_changed = self._is_aws_account_changed(changes)
        if is_aws_account_changed and not aws_account:
            raise ValueError("AWS account is required for updating inputs.")
        is_common_fields_changed = self._is_common_fields_changed(changes)
        input_update_failures = []
        for input_instance in event_log_inputs:
            event_type = input_instance.event_type
            key_prefix = "all_events" if all_events else f"{event_type}_events"
            field_prefixes = [
                f"{key_prefix}_interval",
                f"{key_prefix}_index",
                f"{key_prefix}_start_date",
                f"{key_prefix}_disabled",
            ]
            # If not all events and there are no changes to common fields (aws_account, dir prefix & bucket name) and  no changes for this event type, skip updating
            if (
                not all_events
                and not is_common_fields_changed
                and not any(prefix in changes for prefix in field_prefixes)
            ):
                continue
            
            dir_prefix = event_type_to_dir_mapping[event_type]
            try:
                # If the disabled field is in changes along with other field changes, Splunk wont update other fields along with disabled field.
                # If disabled=True, first toggle the input state, then update other fields. This will prevent unnecessary restarts of the modular input.
                if f"{key_prefix}_disabled" in changes and changes.get(
                    f"{key_prefix}_disabled"
                ):
                    self._disable_input(input_instance)
                    # Reuse field_prefixes, just remove the disabled field for update check
                    field_prefixes.remove(f"{key_prefix}_disabled")
                    # Skip if only the disabled field is changed for particular event type
                    if (
                        not any(prefix in changes for prefix in field_prefixes)
                        and not is_common_fields_changed
                    ):
                        continue
                self._apply_changes_to_input_fields(
                    input_instance,
                    changes,
                    key_prefix=key_prefix,
                    account_name=account_name,
                    aws_account=aws_account,
                    dir_prefix=dir_prefix,
                )
                # If disabled=False, update other fields first, then toggle the input state. This will prevent unnecessary restarts of the modular input.
                if f"{key_prefix}_disabled" in changes and not changes.get(
                    f"{key_prefix}_disabled"
                ):
                    self._enable_input(input_instance)
            except Exception:
                input_update_failures.append(input_instance.name)
        return input_update_failures

    def _apply_changes_to_input_fields(
        self,
        input_instance: Inputs,
        changes: Dict[str, str],
        key_prefix: str = "all_events",
        account_name: str = "",
        aws_account: Optional[Dict[str, str]] = None,
        dir_prefix: Optional[str] = None,
    ) -> None:
        """
        Apply changes to the input fields based on the provided changes dictionary.

        Args:
            input_instance (Inputs): The Inputs instance to be updated.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.
            key_prefix (str): The prefix to be used for identifying the respective input changes. Default is "all_events".
            account_name (str): The name of the AWS account to be set for the input.
            aws_account (Optional[Dict[str, str]]): AWS account information.
            dir_prefix (Optional[str]): The directory prefix to be used for the input.

        Raises:
            RestError: If an error occurs while updating the input fields.
        """
        is_aws_account_changed = self._is_aws_account_changed(changes)
        if is_aws_account_changed and not aws_account:
            raise ValueError("AWS account is required for updating inputs.")
        if "dir_prefix" in changes and not dir_prefix:
            raise ValueError("Directory prefix is required for updating inputs.")
        try:
            update_kwargs = {
                "interval": changes.get(f"{key_prefix}_interval", None),
                "index": changes.get(f"{key_prefix}_index", None),
                "start_date": changes.get(f"{key_prefix}_start_date", None),
                "prefix": dir_prefix if "dir_prefix" in changes else None,
                "bucket_name": changes.get("bucket_name", None),
            }
            # Check if account-related fields have changed
            if is_aws_account_changed:
                update_kwargs.update(
                    {
                        "region": aws_account.get("region", ""),
                        "access_key_id": aws_account.get("access_key_id", ""),
                        "secret_access_key": aws_account.get("secret_access_key", ""),
                        "account_name": account_name,
                    }
                )
            input_instance.update(**update_kwargs)
        except Exception as e:
            raise RestError(
                status=400,
                message=f"Failed to update input fields for {input_instance.name}: {str(e)}",
            )

    def _delete_unselected_inputs(
        self, event_log_inputs: List[Inputs], changes: Dict[str, str]
    ) -> Tuple[List[Inputs], List[str]]:
        """
        Delete inputs for event types that are no longer selected.

        Args:
            event_log_inputs (List[Inputs]): A list of existing Inputs instances to be checked for deletion.
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.

        Returns:
            Tuple[List[Inputs], List[str]]: A tuple containing a list of Inputs instances that were deleted and a list of failed deletions.
        """
        inputs_to_delete = [
            input_instance
            for input_instance in event_log_inputs
            if changes.get(f"{input_instance.event_type}_events") == False
        ]
        failed_input_deletes = self._delete_inputs(
            inputs_to_delete, clear_event_type_start_date_field=True
        )
        return inputs_to_delete, failed_input_deletes

    def _disable_input(self, input_instance: Inputs) -> None:
        """
        Disable a specific input.

        Args:
            input_instance (Inputs): The Inputs instance to be disabled.

        Raises:
            RestError: If an error occurs while disabling the input.
        """
        try:
            input_instance.update(disabled=True)
        except Exception as e:
            raise RestError(status=400, message=f"Failed to disable input: {str(e)}")

    def _enable_input(self, input_instance: Inputs) -> None:
        """
        Enable a specific input.

        Args:
            input_instance (Inputs): The Inputs instance to be enabled.

        Raises:
            RestError: If an error occurs while enabling the input.
        """
        try:
            input_instance.update(disabled=False)
        except Exception as e:
            raise RestError(status=400, message=f"Failed to enable input: {str(e)}")

    def _disable_inputs(
        self,
        inputs: List[Inputs],
    ) -> List[str]:
        """
        Disable inputs if required.

        Args:
            inputs (List[Inputs]): A list of Inputs instances.

        Returns:
            List[str]: A list of input names that failed to disable.

        Raises:
            RestError: If an error occurs while disabling inputs.
        """
        failed_input_updates = []
        for input_instance in inputs:
            try:
                self._disable_input(input_instance)
            except Exception as e:
                failed_input_updates.append(input_instance.name)
        return failed_input_updates

    def _delete_inputs(
        self, inputs: List[Inputs], clear_event_type_start_date_field: bool = False
    ) -> List[str]:
        """
        Delete inputs.

        Args:
            inputs (List[Inputs]): A list of Inputs instances.
        clear_event_type_start_date_field (bool): If True, clears the start date field for event types.

        Returns:
            List[str]: A list of input names that failed to delete.

        Raises:
            RestError: If an error occurs while deleting inputs.
        """
        failed_input_deletions = []
        for input in inputs:
            try:
                input.delete()
                if clear_event_type_start_date_field:
                    self._clear_event_log_field_value(
                        f"{input.event_type}_events_start_date"
                    )
            except Exception:
                failed_input_deletions.append(input.name)
        return failed_input_deletions

    def _get_common_fields(self) -> Tuple[str]:
        """
        Get the common fields used in the event log configuration.

        Returns:
            Tuple[str]: A tuple containing the common fields.
        """
        return ("aws_account", "bucket_name", "dir_prefix")

    def _is_common_fields_changed(self, changes: Dict[str, str]) -> bool:
        """
        Check if any common fields have changed in the provided changes dictionary.

        Args:
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.

        Returns:
            bool: True if any common fields have changed, False otherwise.
        """
        return any(field in changes for field in self._get_common_fields())

    def _get_field_suffixes(self) -> Tuple[str]:
        """
        Get the suffixes used for event type fields in the event log configuration.

        Returns:
            Tuple[str]: A tuple containing the suffixes used for event type fields.
        """
        return ("selected", "index", "interval", "start_date", "disabled")

    def _is_aws_account_changed(self, changes: Dict[str, str]) -> bool:
        """
        Check if the AWS account has changed in the provided changes dictionary.

        Args:
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.

        Returns:
            bool: True if the AWS account has changed, False otherwise.
        """
        return "aws_account" in changes and changes["aws_account"] != ""

    def _is_transitioning_to_all_events(self, changes: Dict[str, str]) -> bool:
        """
        Check if the event log is transitioning from selected events to all events.

        Args:
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.

        Returns:
            bool: True if transitioning from selected to all events, False otherwise.
        """
        return "all_events" in changes and changes["all_events"]

    def _is_all_events(self) -> bool:
        """
        Check if all events is selected in the event log configuration.

        Returns:
            bool: True if all events is selected, False otherwise.
        """
        return str_to_boolean(self.payload.get("all_events"))

    def _apply_all_event_disabled_changes(self, changes: Dict[str, str]) -> None:
        """
        Apply changes related to disabling all events in the event log configuration.

        Args:
            changes (Dict[str, str]): A dictionary containing the fields that have changed and their new values.
        """
        if "all_events_disabled" in self.payload:
            changes["all_events_disabled"] = str_to_boolean(
                self.payload.get("all_events_disabled", False)
            )

    def _clear_event_log_field_value(self, field: str) -> None:
        """
        Clear the field value.

        Args:
            field (str): The field to clear.
        """
        self.payload[field] = ""

    def _get_selected_event_types(
        self, current_event_log_fields: EventLog
    ) -> List[str]:
        """
        Get the selected event types from the current event log fields.

        Args:
            current_event_log_fields (EventLog): The current event log fields.

        Returns:
            List[str]: A list of selected event types.
        """
        return [
            field.split("_events")[0]
            for field in current_event_log_fields.event_mapping.keys()
            if field != "all_events"
            and getattr(current_event_log_fields.event_mapping[field], "selected")
        ]

    def _uncheck_selected_event_types(self, event_types: Union[str, List[str]]) -> None:
        """
        Uncheck the selected event types in the payload.

        Args:
            event_types (Union[str, List[str]]): The event type(s) to uncheck.
        """
        if isinstance(event_types, str):
            event_types = [event_types]
        for event_type in event_types:
            if f"{event_type}_events" in self.payload:
                self.payload[f"{event_type}_events"] = "0"

    def _check_selected_event_types(self, event_types: Union[str, List[str]]) -> None:
        """
        Check the selected event types in the payload.

        Args:
            event_types (Union[str, List[str]]): The event type(s) to check.
        """
        if isinstance(event_types, str):
            event_types = [event_types]
        for event_type in event_types:
            self.payload[f"{event_type}_events"] = "1"

    def _set_event_log_field_value(self, field: str, value: str) -> None:
        """
        Set the field value.

        Args:
            field (str): The field to set.
            value (str): The value to set for the field.
        """
        self.payload[field] = value

    def _restore_common_field_values(self, current_event_log_fields: EventLog) -> None:
        """
        Revert the common field values to the current event log fields.

        Args:
            current_event_log_fields (EventLog): The current event log fields to revert to.
        """
        for field in self._get_common_fields():
            self._set_event_log_field_value(
                field, getattr(current_event_log_fields, field)
            )

    def _restore_selected_event_field_values(
        self,
        current_event_log_fields: EventLog,
        changed_fields: List[str],
    ) -> None:
        """
        Revert the selected event field values to the current event log fields.

        Args:
            current_event_log_fields (EventLog): The current event log fields to revert to.
            changed_fields (List[str]): A list of fields that have changed and need to be reverted.
        """
        for field in changed_fields:
            event_type, suffix = field.split("_events_")
            self._set_event_log_field_value(
                field,
                getattr(
                    current_event_log_fields.event_mapping[f"{event_type}_events"],
                    suffix,
                ),
            )

    def _restore_all_events_field_values(
        self, current_event_log_fields: EventLog
    ) -> None:
        """
        Revert the all events field values to the current event log fields.

        Args:
            current_event_log_fields (EventLog): The current event log fields to revert to.
        """
        for suffix in self._get_field_suffixes()[1:]:
            self._set_event_log_field_value(
                f"all_events_{suffix}",
                getattr(current_event_log_fields.event_mapping["all_events"], suffix),
            )

    def _populate_event_log_fields_from_all_events(
        self, event_log_inputs: List[Inputs], current_event_log_fields: EventLog
    ) -> None:
        """
        Update the event log fields from all events to selected events.

        Args:
            event_log_inputs (List[Inputs]): The event log inputs to update.
            current_event_log_fields (EventLog): The current event log fields to update.
        """
        for input_instance in event_log_inputs:
            event_type = input_instance.event_type
            self._set_event_log_field_value(f"{event_type}_events", "1")
            for suffix in self._get_field_suffixes()[1:]:
                field_name = f"{event_type}_events_{suffix}"
                self._set_event_log_field_value(
                    field_name,
                    getattr(
                        current_event_log_fields.event_mapping["all_events"], suffix
                    ),
                )
        self._reset_all_events_field_values()

    def _reset_all_events_field_values(self) -> None:
        """
        Reset the all events field values to their default state.
        This method sets the 'all_events' field to False and clears all other related fields.
        """
        self._set_event_log_field_value("all_events", "0")
        self._set_event_log_field_value("all_events_index", "default")
        self._set_event_log_field_value("all_events_interval", "600")
        self._set_event_log_field_value("all_events_start_date", "")

    def _reset_selected_event_type_fields(
        self, event_types: Union[str, List[str]]
    ) -> None:
        """
        Reset the selected event type fields to their default state.

        Args:
            event_types (Union[str, List[str]]): The event type(s) to reset.
        """
        if isinstance(event_types, str):
            event_types = [event_types]
        self._uncheck_selected_event_types(event_types)
        for event_type in event_types:
            self._set_event_log_field_value(f"{event_type}_events_index", "default")
            self._set_event_log_field_value(f"{event_type}_events_interval", "600")
            self._set_event_log_field_value(f"{event_type}_events_start_date", "")

    def _set_event_types_disabled_false(self, event_types: List[str]) -> None:
        """
        Set the disabled field to False for the specified event types in the payload.

        Args:
            event_types (List[str]): A list of event types for which the disabled field should be set to False.
        """
        for event_type in event_types:
            self._set_event_log_field_value(f"{event_type}_events_disabled", "0")

    def _build_failure_message(
        self,
        failed_event_types: Optional[List[str]] = None,
        failed_input_updates: Optional[List[str]] = None,
        failed_input_disabling: Optional[List[str]] = None,
        failed_input_deletes: Optional[List[str]] = None,
    ) -> str:
        """
        Build a formatted error message summarizing the failures encountered during input creation and updates.

        Args:
            failed_event_types (Optional[List[str]]): A list of event types for which input creation failed.
            failed_input_updates (Optional[List[str]]): A list of input names that failed to update.
            failed_input_disabling (Optional[List[str]]): A list of input names that failed to disable.
            failed_input_deletes (Optional[List[str]]): A list of input names that failed

        Returns:
            str: A formatted error message summarizing the failures.
        """
        error_messages = []
        if failed_event_types:
            error_messages.append(
                f"Failed to create inputs for event types: {', '.join(failed_event_types)}"
            )
        if failed_input_updates:
            error_messages.append(
                f"Failed to update inputs: {', '.join(failed_input_updates)}"
            )
        if failed_input_disabling:
            error_messages.append(
                f"Failed to disable inputs: {', '.join(failed_input_disabling)}"
            )
        if failed_input_deletes:
            error_messages.append(
                f"Failed to delete inputs: {', '.join(failed_input_deletes)}"
            )
        return "; ".join(error_messages) if error_messages else ""

    def _update_event_log_input_names(self, input_names: Optional[List[str]]) -> None:
        """
        Update the input names in the event log.

        Args:
            input_names (Optional[List[str]]): A list of input names to be updated in the event log. If None, it will set an empty string.
        """
        self._set_event_log_field_value(
            "input_names", ",".join(input_names) if input_names else ""
        )

    def _add_aws_account_input_names(
        self, aws_account_name: str, input_names: str
    ) -> None:
        """
        Update the AWS account input names.

        Args:
            aws_account_name (str): The name of the AWS account.
            input_names (str): A comma-separated string of input names.
        """
        if not aws_account_name or input_names is None:
            raise ValueError("AWS account name and input names are required.")
        input_names_data = {"input_names": input_names}
        self._aws_account_conf.update(aws_account_name, input_names_data, None)

    def _remove_inputs_from_aws_account(
        self,
        aws_account_name: str,
        input_names: List[str],
        current_account_input_names: Optional[Union[str, List[str]]] = None,
    ) -> None:
        """
        Remove inputs from the specified AWS account.

        Args:
            aws_account_name (str): The name of the AWS account.
            input_names (List[str]): A list of input names to be removed from the AWS account.
            current_account_input_names (Optional[Union[str, List[str]]]): Current input names associated with the AWS account.

        Raises:
            ValueError: If aws_account_name or input_names are not provided.
        """
        if not aws_account_name or not input_names:
            raise ValueError("AWS account name and input names are required.")
        if current_account_input_names is None:
            aws_account_fields = self._get_account(aws_account_name)
            current_account_input_names = aws_account_fields.get("input_names", "")
        if isinstance(current_account_input_names, str):
            current_account_input_names = current_account_input_names.split(",")
        aws_account_input_names = [
            name for name in current_account_input_names if name not in input_names
        ]
        self._add_aws_account_input_names(
            aws_account_name,
            ",".join(aws_account_input_names),
        )

    def _update_aws_account_input_names(
        self,
        aws_account_name: str,
        input_names_to_add: Optional[List[str]] = None,
        input_names_to_remove: Optional[List[str]] = None,
        aws_account_input_names: Optional[Union[str, List[str]]] = None,
    ) -> None:
        """
        Update the AWS account input names.

        Args:
            aws_account_name (str): The name of the AWS account.
            input_names_to_add (List[str]): Input names to be added to the AWS account.
            input_names_to_remove (Optional[List[str]]): Input names to be removed from the AWS account.
            aws_account_input_names (Optional[Union[str, List[str]]]): Input names associated with the AWS account.
        """
        if not aws_account_name:
            raise ValueError("AWS account name is required.")
        if input_names_to_add is None and input_names_to_remove is None:
            raise ValueError(
                "At least one of input_names_to_add or input_names_to_remove must be provided."
            )
        if aws_account_input_names is None:
            aws_account_fields = self._get_account(aws_account_name)
            aws_account_input_names = aws_account_fields.get("input_names", "")
        if input_names_to_remove:
            aws_account_input_names = ",".join(
                [
                    name
                    for name in aws_account_input_names.split(",")
                    if name not in input_names_to_remove
                ]
            )
        if isinstance(aws_account_input_names, list):
            aws_account_input_names = ",".join(aws_account_input_names)
        if isinstance(input_names_to_add, list):
            input_names_to_add = ",".join(input_names_to_add)
        self._add_aws_account_input_names(
            aws_account_name,
            (
                f"{aws_account_input_names},{input_names_to_add}"
                if aws_account_input_names and input_names_to_add
                else (aws_account_input_names or input_names_to_add)
            ),
        )
