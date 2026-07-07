"""This module contains the inputs and their methods."""

from typing import List
from service_base import ServiceBase
from utils import make_splunk_request, str_to_boolean


class Inputs(ServiceBase):
    """A class to represent the inputs."""

    ENDPOINT = "TA_cisco_cloud_security_addon_cisco_cloud_security_addon"

    def __init__(self, name: str, session_key: str, initialize: bool = True):
        """Initialize the inputs with a name and session key."""
        super().__init__(name, session_key, initialize)
        self._session_key = session_key
        self.name = name
        self.interval = None
        self.index = None
        self.region = None
        self.acess_key_id = None
        self.secret_access_key = None
        self.bucket_name = None
        self.prefix = None
        self.start_date = None
        self.event_type = None
        self.disabled = None
        self.account_name = None
        self.event_log_name = None
        if initialize:
            self._init_properties()

    @classmethod
    def get_all(
        cls, session_key: str, clear_credentials: bool = False
    ) -> List["Inputs"]:
        """
        Get all inputs from Splunk.

        Args:
            session_key (str): The Splunk session key for authentication
            clear_credentials (bool): Whether to get inputs with cleared credentials

        Returns:
            list: List of Inputs instances

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
                clear_credentials=clear_credentials,
                count=-1,
            )

            inputs = []
            for input in response["entry"]:
                input_instance = cls(input["name"], session_key, False)
                content = input.get("content", {})
                input_instance.interval = content.get("interval")
                input_instance.index = content.get("index")
                input_instance.region = content.get("region")
                input_instance.access_key_id = content.get("access_key_id")
                input_instance.secret_access_key = content.get("secret_access_key")
                input_instance.bucket_name = content.get("bucket_name")
                input_instance.prefix = content.get("prefix")
                input_instance.start_date = content.get("start_date")
                input_instance.event_type = content.get("event_type")
                input_instance.disabled = str_to_boolean(content.get("disabled", False))
                input_instance.account_name = content.get("account_name")
                input_instance.event_log_name = content.get("event_log_name")
                inputs.append(input_instance)
            return inputs
        except Exception as e:
            raise Exception(f"Failed to get inputs: {str(e)}") from e

    @classmethod
    def get_inputs_with_filters(cls, session_key: str, **filters) -> List["Inputs"]:
        """
        Get inputs from Splunk and return only those matching the provided filters.
        Supports filtering by multiple values for any field (e.g., name=["org1_dns", "org1_proxy"]).

        Args:
            session_key (str): The Splunk session key for authentication
            **filters: Field-value pairs or lists to filter inputs

        Returns:
            list: List of Inputs instances matching the filters

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
            filtered_inputs = []
            for entry in response["entry"]:
                content = entry.get("content", {})
                match = True
                for field, value in filters.items():
                    # Support filtering by list of values or single value
                    if isinstance(value, (list, tuple, set)):
                        # Check both top-level and content fields
                        field_value = (
                            entry.get(field) if field == "name" else content.get(field)
                        )
                        if field_value not in value:
                            match = False
                            break
                    else:
                        field_value = (
                            entry.get(field) if field == "name" else content.get(field)
                        )
                        if field_value != value:
                            match = False
                            break
                if match:
                    input_instance = cls(entry["name"], session_key, False)
                    input_instance.interval = content.get("interval")
                    input_instance.index = content.get("index")
                    input_instance.region = content.get("region")
                    input_instance.access_key_id = content.get("access_key_id")
                    input_instance.secret_access_key = content.get("secret_access_key")
                    input_instance.bucket_name = content.get("bucket_name")
                    input_instance.prefix = content.get("prefix")
                    input_instance.start_date = content.get("start_date")
                    input_instance.event_type = content.get("event_type")
                    input_instance.disabled = str_to_boolean(
                        content.get("disabled", False)
                    )
                    input_instance.account_name = content.get("account_name")
                    input_instance.event_log_name = content.get("event_log_name")
                    filtered_inputs.append(input_instance)
            return filtered_inputs
        except Exception as e:
            raise Exception(f"Failed to get filtered inputs: {str(e)}") from e

    @classmethod
    def create(
        cls,
        name: str,
        session_key: str,
        interval: int,
        index: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        prefix: str,
        start_date: str,
        event_type: str,
        account_name: str = None,
        event_log_name: str = None,
    ) -> "Inputs":
        """
        Create a new input in Splunk.

        Args:
            name (str): The name of the input
            session_key (str): The Splunk session key for authentication
            interval (int): The interval for the input
            index (str): The index for the input
            region (str): The AWS region
            access_key_id (str): The AWS access key ID
            secret_access_key (str): The AWS secret access key
            bucket_name (str): The S3 bucket name
            prefix (str): The directory prefix in the S3 bucket
            start_date (str): The start date for the input
            event_type (str): The event type for the input
            account_name (str, optional): The AWS account name
            event_log_name (str, optional): The event log name

        Returns:
            Inputs: An instance of the Inputs class

        Raises:
            Exception: If the Splunk request fails
        """
        try:
            data = {
                "name": name,
                "interval": interval,
                "index": index,
                "region": region,
                "access_key_id": access_key_id,
                "secret_access_key": secret_access_key,
                "bucket_name": bucket_name,
                "prefix": prefix,
                "start_date": start_date,
                "event_type": event_type,
            }
            if account_name:
                data["account_name"] = account_name
            if event_log_name:
                data["event_log_name"] = event_log_name

            response = make_splunk_request(
                "POST",
                cls.ENDPOINT,
                session_key,
                use_json_output=True,
                addon_namespace=True,
                data=data,
            )
            input_instance = cls(name, session_key, False)
            content = response.get("entry", [{}])[0].get("content", {})
            input_instance.interval = content.get("interval")
            input_instance.index = content.get("index")
            input_instance.region = content.get("region")
            input_instance.access_key_id = content.get("access_key_id")
            input_instance.secret_access_key = content.get("secret_access_key")
            input_instance.bucket_name = content.get("bucket_name")
            input_instance.prefix = content.get("prefix")
            input_instance.start_date = content.get("start_date")
            input_instance.event_type = content.get("event_type")
            input_instance.disabled = str_to_boolean(content.get("disabled", False))
            input_instance.account_name = content.get("account_name")
            input_instance.event_log_name = content.get("event_log_name")
            return input_instance

        except Exception as e:
            raise Exception(f"Failed to create input: {str(e)}") from e

    def delete(self):
        """
        Delete the input from Splunk.

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
            raise Exception(f"Failed to delete input: {str(e)}") from e

    def update(self, **kwargs):
        """
        Update the input in Splunk.

        Args:
            **kwargs: The fields to update

        Raises:
            Exception: If the Splunk request fails
        """
        try:
            data = {k: v for k, v in kwargs.items() if v is not None}
            response = make_splunk_request(
                "POST",
                f"{self.ENDPOINT}/{self.name}",
                self._session_key,
                use_json_output=True,
                addon_namespace=True,
                data=data,
            )
            # Reinitialize properties after update using the updated values from the response
            content = response.get("entry", [{}])[0].get("content", {})
            self.interval = content.get("interval")
            self.index = content.get("index")
            self.region = content.get("region")
            self.access_key_id = content.get("access_key_id")
            self.secret_access_key = content.get("secret_access_key")
            self.bucket_name = content.get("bucket_name")
            self.prefix = content.get("prefix")
            self.start_date = content.get("start_date")
            self.event_type = content.get("event_type")
            self.disabled = str_to_boolean(content.get("disabled", False))
            self.account_name = content.get("account_name")
            self.event_log_name = content.get("event_log_name")
        except Exception as e:
            raise Exception(f"Failed to update input: {str(e)}") from e

    def _init_properties(self):
        """
        Initialize the properties of the input.

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
            self.interval = content.get("interval")
            self.index = content.get("index")
            self.region = content.get("region")
            self.access_key_id = content.get("access_key_id")
            self.secret_access_key = content.get("secret_access_key")
            self.bucket_name = content.get("bucket_name")
            self.prefix = content.get("prefix")
            self.start_date = content.get("start_date")
            self.event_type = content.get("event_type")
            self.disabled = str_to_boolean(content.get("disabled", False))
            self.account_name = content.get("account_name")
            self.event_log_name = content.get("event_log_name")
        except Exception as e:
            raise Exception(f"Failed to initialize properties: {str(e)}") from e
