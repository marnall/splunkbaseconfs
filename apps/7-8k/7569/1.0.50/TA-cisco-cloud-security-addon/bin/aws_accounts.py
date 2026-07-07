"""This module contains the AWS Account class and its methods."""

from typing import List, Optional
from utils import make_splunk_request, str_to_boolean
from service_base import ServiceBase


class AWSAccount(ServiceBase):
    """A class to represent an AWS account."""

    ENDPOINT = "TA_cisco_cloud_security_addon_aws_account"

    def __init__(self, name: str, session_key: str, initialize: bool = True):
        """Initialize the account with a name and session key."""
        super().__init__(name, session_key, initialize)
        self._session_key = session_key
        self.name = name
        self.region = None
        self.access_key_id = None
        self.secret_access_key = None
        self.auto_rotate_key = None
        self.secure_access_client_id = None
        self.secure_access_client_secret = None
        self.input_names = None
        if initialize:
            self._init_properties()

    @classmethod
    def get_all(cls, session_key: str) -> List["AWSAccount"]:
        """
        Get all AWS accounts from Splunk.

        Args:
            session_key (str): The Splunk session key for authentication

        Returns:
            list: List of AWSAccount instances

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
                clear_credentials=False,
                count=-1,
            )

            accounts = []
            for account in response.get("entry", [{}]):
                aws_account = cls(account["name"], session_key, False)
                content = account.get("content", {})
                aws_account.region = content.get("region")
                aws_account.access_key_id = content.get("access_key_id")
                aws_account.secret_access_key = content.get("secret_access_key")
                aws_account.input_names = content.get("input_names")
                accounts.append(aws_account)
            return accounts
        except Exception as e:
            raise Exception(f"Failed to get AWS accounts: {str(e)}") from e

    @classmethod
    def create(
        cls,
        name: str,
        session_key: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> "AWSAccount":
        """
        Create a new AWS account in Splunk.

        Args:
            name (str): The name of the AWS account
            session_key (str): The Splunk session key for authentication
            region (str): The AWS region
            access_key_id (str): The AWS access key ID
            secret_access_key (str): The AWS secret access key

        Returns:
            AWSAccount: The created AWSAccount instance

        Raises:
            Exception: If the Splunk request fails
        """
        data = {
            "name": name,
            "region": region,
            "access_key_id": access_key_id,
            "secret_access_key": secret_access_key,
        }
        try:
            response = make_splunk_request(
                "POST",
                cls.ENDPOINT,
                session_key,
                data=data,
                use_json_output=True,
                addon_namespace=True,
            )
            account_instance = cls(name, session_key, False)
            content = response.get("entry", [{}])[0].get("content", {})
            account_instance.region = content.get("region")
            account_instance.access_key_id = content.get("access_key_id")
            account_instance.secret_access_key = content.get("secret_access_key")
            account_instance.input_names = content.get("input_names")
            return account_instance
        except Exception as e:
            raise Exception(f"Failed to create AWS account: {str(e)}") from e

    def delete(self):
        """
        Delete the AWS account from Splunk.

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
            raise Exception(f"Failed to delete AWS account: {str(e)}") from e

    def update(
        self,
        region: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
        input_names: str = None,
    ):
        """
        Update the AWS account in Splunk.

        Args:
            region (str, optional): The AWS region. If not provided, the region will remain unchanged.
            access_key_id (str, optional): The AWS access key ID. If not provided, the access key ID will remain unchanged.
            secret_access_key (str, optional): The AWS secret access key. If not provided, the secret access key will remain unchanged.
            input_names (str, optional): The names of the inputs associated with this account. If not provided, the inputs will remain unchanged.
        Raises:
            Exception: If the Splunk request fails
        """
        data = {}
        if region:
            data["region"] = region
        if access_key_id:
            data["access_key_id"] = access_key_id
        if secret_access_key:
            data["secret_access_key"] = secret_access_key
        if input_names:
            data["input_names"] = input_names
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
            self.region = content.get("region")
            self.access_key_id = content.get("access_key_id")
            self.secret_access_key = content.get("secret_access_key")
            self.input_names = content.get("input_names")
        except Exception as e:
            raise Exception(f"Failed to update AWS account: {str(e)}") from e

    @classmethod
    def has_accounts(cls, session_key: str) -> bool:
        """
        Check if atleast one AWS account exists.
        Args:
            session_key (str): The Splunk session key for authentication
        Returns:
            bool: True if atleast one AWS account exists, False otherwise
        """
        try:
            response = make_splunk_request(
                "GET",
                cls.ENDPOINT,
                session_key,
                use_json_output=True,
                addon_namespace=True,
                count=1,
            )
            return bool(response.get("entry"))
        except Exception as e:
            raise Exception(f"Failed to check AWS accounts: {str(e)}") from e

    @classmethod
    def get_by_access_key_id(
        cls, session_key: str, access_key_id: str
    ) -> "Optional[AWSAccount]":
        """
        Get an AWS account by its access key ID.

        Args:
            session_key (str): The Splunk session key for authentication
            access_key_id (str): The AWS access key ID to search for

        Returns:
            Optional[AWSAccount]: The AWSAccount instance if found, None otherwise
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
            for account in response.get("entry", []):
                content = account.get("content", {})
                if content.get("access_key_id") != access_key_id:
                    continue
                aws_account = cls(account["name"], session_key, False)
                aws_account.region = content.get("region")
                aws_account.access_key_id = content.get("access_key_id")
                aws_account.secret_access_key = content.get("secret_access_key")
                aws_account.input_names = content.get("input_names")
                return aws_account
            return None
        except Exception as e:
            raise Exception(f"Failed to check AWS account: {str(e)}") from e

    def _init_properties(self):
        """Initialize the properties of the account."""
        try:
            response = make_splunk_request(
                "GET",
                f"{self.ENDPOINT}/{self.name}",
                self._session_key,
                use_json_output=True,
                addon_namespace=True,
            )
            content = response["entry"][0]["content"]
            self.region = content.get("region")
            self.access_key_id = content.get("access_key_id")
            self.secret_access_key = content.get("secret_access_key")
            self.input_names = content.get("input_names")
            self.auto_rotate_key = str_to_boolean(content.get("auto_rotate_key"))
            self.secure_access_client_id = content.get("secure_access_client_id")
            self.secure_access_client_secret = content.get("secure_access_client_secret")
        except Exception as e:
            raise Exception(f"Failed to initialize AWS account: {str(e)}") from e
