import import_declare_test
import json
from typing import List, Optional, Tuple, Dict, Any
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from inputs import Inputs
from aws_accounts import AWSAccount
from utils import str_to_boolean, SSEUtility, S3Utility
from exceptions import S3ValidationError
from data_input_manager import DataInputManager

class AWSAccountsValidator(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self._s3_utility = S3Utility(self.getSessionKey())

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        aws_account_name = str(self.callerArgs.id)
        auto_rotate_key = str_to_boolean(self.payload.get("auto_rotate_key"))
        s3_updated = self._is_s3_credentials_updated()
        
        secure_access_updated = self._is_secure_access_credentials_updated()
        if s3_updated and not secure_access_updated:
            self.payload.pop("auto_rotate_key", None)
            self.payload.pop("secure_access_client_id", None)
            self.payload.pop("secure_access_client_secret", None)
        
        if secure_access_updated:
            self._validate_secure_access_credentials()

        current_aws_account = self._get_current_aws_account_fields(aws_account_name)
        current_auto_rotate_key = current_aws_account.auto_rotate_key if current_aws_account else None
        data_input_manager = DataInputManager(self.getSessionKey())

        if auto_rotate_key and secure_access_updated:
            data = {"name": aws_account_name, "interval": "60", "handler": "ACCOUNT"}
            try:
                data_input_manager.create(input_name=aws_account_name, data=data)
            except Exception as e:
                pass
        else:
                if current_auto_rotate_key and secure_access_updated:
                    # If auto_rotate_key is set to false, current auto_rotate_key is True then delete the data input
                    data_input_manager.delete(input_name=aws_account_name)

        if not s3_updated:
            AdminExternalHandler.handleEdit(self, confInfo)
            return

        if s3_updated:
            self._validate_s3_credentials()

        self._handle_edit_aws_accounts(aws_account_name)
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        self._validate_s3_credentials()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        aws_account_name = str(self.callerArgs.id)
        current_aws_account = self._get_current_aws_account_fields(aws_account_name)
        current_auto_rotate_key = current_aws_account.auto_rotate_key if current_aws_account else None
        data_input_manager = DataInputManager(self.getSessionKey())

        if current_auto_rotate_key:
            data_input_manager.delete(input_name=aws_account_name)

        self._handle_remove_aws_account(aws_account_name)
        AdminExternalHandler.handleRemove(self, confInfo)

    def _validate_secure_access_credentials(self) -> None:
        access_client_id = self.payload.get("secure_access_client_id")
        access_client_secret = self.payload.get("secure_access_client_secret")
        if not access_client_id or not access_client_secret:
            raise RestError(
                status=400, message="Secure Access key and secret key are required."
            )
        try:
            SSEUtility().generate_access_token(access_client_id, access_client_secret)
        except Exception as e:
            raise RestError(
                status=400,
                message="Invalid Secure Access Client Id or Secure Access Client Secret",
            )

    def _validate_s3_credentials(self) -> None:
        """
        Validates the provided AWS S3 credentials.

        This function checks the validity of the given AWS S3 credentials (access key,
        secret key). If the credentials are invalid, it raises
        a `RestError`. If the credentials are valid, the function completes successfully
        and returns `None`.

        Raises:
            RestError: If the provided AWS S3 credentials are invalid.

        Returns:
            None: If the credentials are successfully validated.
        """
        access_key = self.payload.get("access_key_id")
        secret_key = self.payload.get("secret_access_key")
        region = self.payload.get("region")
        if not access_key or not secret_key:
            raise RestError(
                status=400, message="Access key and secret key are required."
            )
        if not region:
            raise RestError(status=400, message="Region is required.")
        try:
            self._s3_utility.validate_keys(
                access_key_id=access_key,
                secret_access_key=secret_key,
                region=region,
            )
        except S3ValidationError as e:
            raise RestError(
                status=400,
                message=e.message,
            )

    def _handle_edit_aws_accounts(self, aws_account_name: str) -> None:
        """
        Handles the editing of AWS accounts.

        Args:
            aws_account_name (str): The name of the AWS account to edit.

        Raises:
            RestError: If the AWS account name is not provided or if the credentials are invalid.
        """
        region = self.payload.get("region")
        access_key_id = self.payload.get("access_key_id")
        secret_access_key = self.payload.get("secret_access_key")
        aws_account_inputs = self._get_aws_account_inputs(aws_account_name)
        if aws_account_inputs:
            self._update_aws_account_inputs(
                aws_account_inputs, region, access_key_id, secret_access_key
            )

    def _handle_remove_aws_account(self, aws_account_name: str) -> None:
        """
        Handles the removal of an AWS account.

        Args:
            aws_account_name (str): The name of the AWS account to remove.

        Raises:
            RestError: If the AWS account does not exist or if there is an error removing it.
        """
        if not aws_account_name:
            raise ValueError("AWS account name must be provided.")
        if self._has_input_names_in_aws_account(aws_account_name):
            raise RestError(
                status=400,
                message=f"Cannot remove AWS account '{aws_account_name}' as it has associated inputs.",
            )

    def _get_aws_account_inputs(self, aws_account_name: str) -> List[Inputs]:
        """
        Retrieves the AWS account inputs from the payload. If payload does not contain inputs,
        it retrieves the inputs based on the aws account name.

        Args:
            aws_account_name (str): The name of the AWS account to retrieve inputs for.

        Returns:
            dict: A dictionary containing the AWS account inputs.
        """
        input_names = self.payload.get("input_names")
        if not input_names:
            input_names = self._get_aws_account_input_names(aws_account_name)
        if isinstance(input_names, str):
            input_names = input_names.split(",")
        try:
            return Inputs.get_inputs_with_filters(
                session_key=self.getSessionKey(),
                name=input_names,
            )
        except Exception as e:
            raise RestError(status=400, message=f"Failed to retrieve inputs: {str(e)}")

    def _get_current_aws_account(self, aws_account_name: str) -> List[AWSAccount]:
        """
        Retrieves the current AWS accounts from the session.

        Args:
            aws_account_name (str): The name of the AWS account to retrieve.

        Returns:
            List[AWSAccount]: A list of AWSAccount objects representing the current AWS accounts.
        """
        try:
            return AWSAccount(aws_account_name, self.getSessionKey())
        except Exception as e:
            raise RestError(
                status=400, message=f"Failed to retrieve AWS accounts: {str(e)}"
            )

    def _get_aws_account_input_names(
        self, aws_account_name: str, aws_account: Optional[AWSAccount] = None
    ) -> List[str]:
        """
        Retrieves the input names associated with the given AWS account.

        Args:
            aws_account_name (str): The name of the AWS account.
            aws_account (Optional[AWSAccount]): The AWS account object from which to retrieve input names.
                If not provided, it will use the current AWS account.

        Returns:
            List[str]: A list of input names associated with the AWS account.
        """
        if aws_account is None and not aws_account_name:
            raise ValueError("AWS account name must be provided.")
        if aws_account is None:
            aws_account = self._get_current_aws_account(aws_account_name)
        return aws_account.input_names.split(",") if aws_account.input_names else []

    def _update_aws_account_inputs(
        self,
        inputs: List[Inputs],
        region: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ) -> None:
        """
        Updates the AWS account inputs with the provided inputs.

        Args:
            inputs (List[Inputs]): The list of Inputs to update.
            region (Optional[str]): The AWS region to update.
            access_key_id (Optional[str]): The AWS access key ID to update.
            secret_access_key (Optional[str]): The AWS secret access key to update.

        Raises:
            RestError: If the AWS account does not exist or if there is an error updating the inputs.
        """
        if not inputs:
            raise ValueError("Inputs must be provided to update AWS account inputs.")
        if not region and not access_key_id and not secret_access_key:
            raise ValueError(
                "Region or access key ID, and secret access key must be provided."
            )
        kwargs = {
            "region": region,
            "access_key_id": access_key_id,
            "secret_access_key": secret_access_key,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        try:
            for input_item in inputs:
                input_item.update(**kwargs)
        except Exception as e:
            raise RestError(
                status=400, message=f"Failed to update AWS account inputs: {str(e)}"
            )

    def _is_s3_credentials_updated(self) -> bool:
        """
        Checks if the S3 credentials have been updated.

        Returns:
            bool: True if the S3 credentials have been updated, False otherwise.
        """

        return all(
            self.payload.get(key) 
            for key in ("access_key_id", "secret_access_key", "region")
        ) and  all(
            key in self.payload
            for key in ("access_key_id", "secret_access_key", "region")     )

    def _has_input_names_in_aws_account(self, aws_account_name: str) -> bool:
        """
        Checks if the AWS account contains input names.

        Args:
            aws_account_name (str): The name of the AWS account to check.

        Returns:
            bool: True if the AWS account contains input names, False otherwise.
        """
        if not aws_account_name:
            raise ValueError("AWS account name must be provided.")
        aws_account = self._get_current_aws_account(aws_account_name)
        return bool(aws_account.input_names)

    def _get_current_aws_account_fields(self, aws_account_name: str) -> Dict[str, Any]:
        """
        Retrieve the AWS account fields for a given account name.

        aws_account_name (str): The name of the AWS account whose fields are to be retrieved.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the current fields, or None if not found.

        Raises:
            RestError: If there is an error retrieving the AWS account fields.
        """
        try:
            return AWSAccount(aws_account_name, self.getSessionKey())
        except Exception as e:
            raise RestError(
                status=400, message=f"Failed to retrieve AWS account fields: {str(e)}"
            )

    def _is_secure_access_credentials_updated(self) -> bool:
        """
        Checks if any secure access credential fields have been updated in the payload.
        Returns:
            bool: True if at least one of 'secure_access_client_id', 'secure_access_client_secret',
             is present in the payload; False otherwise.
        """

        return all(
            self.payload.get(key) 
            for key in (
                "secure_access_client_id",
                "secure_access_client_secret"
            )
        ) and  all(
            key in self.payload
            for key in (
                "auto_rotate_key",
                "secure_access_client_id",
                "secure_access_client_secret"
            )        )