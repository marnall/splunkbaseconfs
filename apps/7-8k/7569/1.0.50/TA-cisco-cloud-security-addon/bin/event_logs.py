"""This module contains the EventLogs class and its methods."""

from typing import Dict, List, Optional, Union
import event_logs_models
from service_base import ServiceBase
from utils import make_splunk_request, str_to_boolean


class EventLogs(ServiceBase):
    """A class to represent the event logs."""

    ENDPOINT = "TA_cisco_cloud_security_addon_event_logs"

    def __init__(self, name: str, session_key: str, initialize: bool = True):
        """Initialize the event logs with a name and session key."""
        super().__init__(name, session_key, initialize)
        self._session_key = session_key
        self.name = name
        self.aws_account = None
        self.bucket_name = None
        self.dir_prefix = None
        self.auto_discovery_enabled = None
        self.event_mapping = {
            "all_events": event_logs_models.AllEvent(),
            "dns_events": event_logs_models.DnsEvent(),
            "dlp_events": event_logs_models.DlpEvent(),
            "audit_events": event_logs_models.AuditEvent(),
            "proxy_events": event_logs_models.ProxyEvent(),
            "firewall_events": event_logs_models.FirewallEvent(),
            "intrusion_events": event_logs_models.IntrusionEvent(),
            "ravpn_events": event_logs_models.RavpnEvent(),
            "ztna_events": event_logs_models.ZtnaEvent(),
            "ztnaflow_events": event_logs_models.ZtnaflowEvent(),
            "fileevent_events": event_logs_models.FileeventEvent(),
            "ztnaenrollment_events": event_logs_models.ZtnaenrollmentEvent(),
            "ntg_events": event_logs_models.NtgEvent(),
        }
        self.input_names = None
        if initialize:
            self._init_properties()

    @classmethod
    def get_all(cls, session_key: str) -> List["EventLogs"]:
        """
        Get all event logs from Splunk.

        Args:
            session_key (str): The Splunk session key for authentication

        Returns:
            list: List of EventLogs instances

        Raises:
            Exception: If the Splunk request fails
        """
        try:
            response = make_splunk_request(
                "GET",
                cls.ENDPOINT,
                session_key,
                use_json_output=True,
                addon_namespace=True,
                count=-1,
            )

            event_logs = []
            for event_log in response["entry"]:
                event_log_instance = cls(event_log["name"], session_key, False)
                content = event_log.get("content", {})
                event_log_instance.aws_account = content.get("aws_account")
                event_log_instance.bucket_name = content.get("bucket_name")
                event_log_instance.dir_prefix = content.get("dir_prefix")
                event_log_instance.input_names = content.get("input_names")
                event_log_instance.auto_discovery_enabled = str_to_boolean(content.get("auto_discovery_enabled", "0"))
                for event_type, event_model in event_log_instance.event_mapping.items():
                    if content.get(event_type):
                        setattr(
                            event_model,
                            "selected",
                            str_to_boolean(content.get(event_type)),
                        )
                        setattr(
                            event_model, "index", content.get(f"{event_type}_index")
                        )
                        setattr(
                            event_model,
                            "interval",
                            content.get(f"{event_type}_interval"),
                        )
                        setattr(
                            event_model,
                            "start_date",
                            content.get(f"{event_type}_start_date"),
                        )
                        setattr(
                            event_model,
                            "disabled",
                            str_to_boolean(content.get(f"{event_type}_disabled")),
                        )
                event_logs.append(event_log_instance)
            return event_logs
        except Exception as e:
            raise Exception(f"Failed to get event logs: {str(e)}") from e

    @classmethod
    def get_by_dir_prefixes(
        cls, session_key: str, prefixes: Union[str, List[str]]
    ) -> List["EventLogs"]:
        """
        Get event logs by directory prefix.

        Args:
            session_key (str): The Splunk session key for authentication
            prefixes (Union[str, List[str]]): A single prefix or a list of prefixes to filter event logs
        Returns:
            list: List of EventLogs instances that match the prefix(es)

        Raises:
            Exception: If the Splunk request fails
        """
        try:
            all_event_logs = cls.get_all(session_key)

            # Convert single prefix to list for uniform handling
            prefixes = [prefixes] if isinstance(prefixes, str) else prefixes

            return [
                event_log
                for event_log in all_event_logs
                if f"{event_log.bucket_name}/{event_log.dir_prefix}" in prefixes
            ]
        except Exception as e:
            raise Exception(f"Failed to get event logs by prefix: {str(e)}") from e

    @classmethod
    def create(
        cls,
        name: str,
        aws_account: str,
        session_key: str,
        bucket_name: str,
        dir_prefix: str,
        event_mapping: Dict[str, event_logs_models.EventLog],
        input_names: str,
        auto_discovery_enabled: bool = False,  # Add this parameter
    ) -> "EventLogs":
        """
        Create a new event log in Splunk.

        Args:
            name (str): The name of the event log
            aws_account (str): The AWS account name
            session_key (str): The Splunk session key for authentication
            bucket_name (str): The S3 bucket name
            dir_prefix (str): The directory prefix in the S3 bucket
            event_mapping (Dict[str, event_logs_models.EventLog]): A dictionary mapping event types to their models
            input_names (str): Comma-separated list of input names
        Returns:
            EventLogs: The created EventLogs instance
        """
        params = {}
        # create a data dictionary to be sent to Splunk
        data = {
            "name": name,
            "aws_account": aws_account,
            "bucket_name": bucket_name,
            "dir_prefix": dir_prefix,
            "input_names": input_names,
            "auto_discovery_enabled": auto_discovery_enabled,  # Add this line
        }
        for event_type, event_model in event_mapping.items():
            data[event_type] = getattr(event_model, "selected")
            index = getattr(event_model, "index", None)
            if index is not None:
                data[f"{event_type}_index"] = index
            interval = getattr(event_model, "interval", None)
            if interval is not None:
                data[f"{event_type}_interval"] = interval
            start_date = getattr(event_model, "start_date", None)
            if start_date is not None:
                data[f"{event_type}_start_date"] = start_date
            disabled = getattr(event_model, "disabled", None)
            if disabled is not None:
                data[f"{event_type}_disabled"] = disabled
        try:
            response = make_splunk_request(
                "POST",
                cls.ENDPOINT,
                session_key,
                data=data,
                params=params,
                use_json_output=True,
                addon_namespace=True,
            )
            event_log_instance = cls(name, session_key, False)
            content = response.get("entry", [{}])[0].get("content", {})
            event_log_instance.aws_account = content.get("aws_account")
            event_log_instance.bucket_name = content.get("bucket_name")
            event_log_instance.dir_prefix = content.get("dir_prefix")
            event_log_instance.input_names = content.get("input_names")
            event_log_instance.auto_discovery_enabled = str_to_boolean(content.get("auto_discovery_enabled", False))  # Add this line
            for event_type, event_model in event_log_instance.event_mapping.items():
                if content.get(event_type):
                    setattr(
                        event_model,
                        "selected",
                        str_to_boolean(content.get(event_type)),
                    )
                    setattr(event_model, "index", content.get(f"{event_type}_index"))
                    setattr(
                        event_model, "interval", content.get(f"{event_type}_interval")
                    )
                    setattr(
                        event_model,
                        "start_date",
                        content.get(f"{event_type}_start_date"),
                    )
                    setattr(
                        event_model,
                        "disabled",
                        str_to_boolean(content.get(f"{event_type}_disabled")),
                    )
            return event_log_instance
        except Exception as e:
            raise Exception(f"Failed to create event log: {str(e)}") from e

    def delete(self):
        """
        Delete the event log from Splunk.

        Raises:
            Exception: If the Splunk request fails
        """
        try:
            make_splunk_request(
                "DELETE",
                f"{self.ENDPOINT}/{self.name}",
                self._session_key,
                use_json_output=True,
                addon_namespace=True,
            )
        except Exception as e:
            raise Exception(f"Failed to delete event log: {str(e)}") from e

    def update(
        self,
        aws_account: Optional[str] = None,
        bucket_name: Optional[str] = None,
        dir_prefix: Optional[str] = None,
        event_logs: Optional[Dict[str, event_logs_models.EventLog]] = None,
        input_names: Optional[str] = None,
        auto_discovery_enabled: Optional[bool] = None,
    ) -> None:
        """
        Update the event log with new parameters.

        Args:
            aws_account (str, optional): The AWS account name
            bucket_name (str, optional): The S3 bucket name
            dir_prefix (str, optional): The directory prefix in the S3 bucket
            event_logs (Dict[str, event_logs_models.EventLog], optional): Event log models to update
            input_names (str, optional): Comma-separated list of input names

        Raises:
            Exception: If the Splunk request fails
        """
        data = {}

        # Only add parameters that were provided
        if aws_account is not None:
            data["aws_account"] = aws_account
        if bucket_name is not None:
            data["bucket_name"] = bucket_name
        if dir_prefix is not None:
            data["dir_prefix"] = dir_prefix
        if input_names is not None:
            data["input_names"] = input_names
        if auto_discovery_enabled is not None:
            data["auto_discovery_enabled"] = auto_discovery_enabled

        # Process event log models
        if event_logs:
            for event_type, event_model in event_logs.items():
                if event_type in self.event_mapping:
                    data[event_type] = getattr(event_model, "selected", False)
                    data[f"{event_type}_index"] = getattr(event_model, "index", None)
                    data[f"{event_type}_interval"] = getattr(
                        event_model, "interval", None
                    )
                    data[f"{event_type}_start_date"] = getattr(
                        event_model, "start_date", None
                    )
                    data[f"{event_type}_disabled"] = getattr(
                        event_model, "disabled", None
                    )

        try:
            response = make_splunk_request(
                "POST",
                f"{self.ENDPOINT}/{self.name}",
                self._session_key,
                data=data,
                use_json_output=True,
                addon_namespace=True,
            )
            content = response.get("entry", [{}])[0].get("content", {})
            self.aws_account = content.get("aws_account")
            self.bucket_name = content.get("bucket_name")
            self.dir_prefix = content.get("dir_prefix")
            self.input_names = content.get("input_names")
            self.auto_discovery_enabled = str_to_boolean(content.get("auto_discovery_enabled", "0"))  # Add this line
            for event_type, event_model in self.event_mapping.items():
                if content.get(event_type):
                    setattr(
                        event_model, "selected", str_to_boolean(content.get(event_type))
                    )
                    setattr(event_model, "index", content.get(f"{event_type}_index"))
                    setattr(
                        event_model, "interval", content.get(f"{event_type}_interval")
                    )
                    setattr(
                        event_model,
                        "start_date",
                        content.get(f"{event_type}_start_date"),
                    )
                    setattr(
                        event_model,
                        "disabled",
                        str_to_boolean(content.get(f"{event_type}_disabled")),
                    )
        except Exception as e:
            raise Exception(f"Failed to update event log: {str(e)}") from e

    def _init_properties(self):
        """Initialize properties of the EventLogs instance.

        Raises:
            Exception: If the Splunk request fails
        """
        try:
            response = make_splunk_request(
                "GET",
                f"{self.ENDPOINT}/{self.name}",
                self._session_key,
                use_json_output=True,
                addon_namespace=True,
            )
            content = response.get("entry", [{}])[0].get("content", {})
            self.aws_account = content.get("aws_account")
            self.bucket_name = content.get("bucket_name")
            self.dir_prefix = content.get("dir_prefix")
            self.input_names = content.get("input_names")
            self.auto_discovery_enabled = str_to_boolean(content.get("auto_discovery_enabled", "0"))
            for event_type, event_model in self.event_mapping.items():
                if content.get(event_type):
                    setattr(
                        event_model, "selected", str_to_boolean(content.get(event_type))
                    )
                    setattr(event_model, "index", content.get(f"{event_type}_index"))
                    setattr(
                        event_model, "interval", content.get(f"{event_type}_interval")
                    )
                    setattr(
                        event_model,
                        "start_date",
                        content.get(f"{event_type}_start_date"),
                    )
                    setattr(
                        event_model,
                        "disabled",
                        str_to_boolean(content.get(f"{event_type}_disabled")),
                    )
        except Exception as e:
            raise Exception(f"Failed to initialize properties: {str(e)}") from e
