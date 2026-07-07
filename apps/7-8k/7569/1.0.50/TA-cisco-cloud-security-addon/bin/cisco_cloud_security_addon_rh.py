import import_declare_test
from solnlib.modular_input import checkpointer
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from utils import get_dir_prefix, S3Utility
from exceptions import S3ValidationError


class ModInputRestHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self._s3_utility = S3Utility(self.getSessionKey())

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        # Only perform S3 validation if input is not disabled/enabled
        # and S3 details have changed
        if "disabled" not in self.payload and self._has_s3_details_changed():
            self._verify_s3_access()
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        self._verify_s3_access()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        """
        Handles the removal of a configuration entry and its associated checkpoint.
        This method deletes the checkpoint data from the KVStore for the specified input,
        identified by the input name extracted from the caller arguments. If the checkpoint
        cannot be deleted, a RestError is raised with an appropriate message. After
        attempting to remove the checkpoint, the base class's handleRemove method is called
        to complete the removal process.
        Args:
            confInfo: The configuration information object provided by the REST handler framework.
        Raises:
            RestError: If there is an error deleting the checkpoint from the KVStore.
        """

        addon_name = import_declare_test.ta_name
        input_name = str(self.callerArgs.id)
        checkpointer_key_name = input_name.split("/")[-1]
        try:
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                f"{addon_name}_checkpointer", self.getSessionKey(), addon_name
            )
            response = kvstore_checkpointer.get(checkpointer_key_name)
            if "can_delete" not in response:
                kvstore_checkpointer.delete(checkpointer_key_name)
            elif response and response.get("can_delete", False):
                # If the checkpoint can be deleted, proceed with deletion
                kvstore_checkpointer.delete(checkpointer_key_name)
            else:
                # If the checkpoint cannot be deleted, raise an error
                raise RestError(
                    status=400,
                    message=f"Input '{input_name}' is currently pushing events to the index. Please try deleting the input after some time.",
                )
        except RestError:
            # Re-raise RestError to allow proper REST error handling
            raise
        except Exception as e:
            raise RestError(
                status=400,
                message=f"Unable to delete checkpoint for input '{input_name}': {str(e)}",
            )
        AdminExternalHandler.handleRemove(self, confInfo)

    def _verify_s3_access(self) -> None:
        """
        Validates the provided S3 credentials and checks if the S3 bucket is accessible.

        This function checks the validity of the given S3 credentials (access key, secret key, and bucket name).
        If the credentials are invalid or the bucket is not accessible, it raises a `RestError`.

        Raises:
            RestError: If the provided S3 credentials are invalid or if the bucket is not accessible.

        Returns:
            None: If the credentials are successfully validated and the bucket is accessible.
        """
        access_key_id = self.payload.get("access_key_id")
        secret_access_key = self.payload.get("secret_access_key")
        bucket_name = self.payload.get("bucket_name")
        region = self.payload.get("region")
        prefix = self.payload.get("prefix")
        if (
            not access_key_id
            or not secret_access_key
            or not bucket_name
            or not region
            or not prefix
        ):
            raise RestError(
                status=400,
                message="Invalid S3 credentials. Please provide valid access key, secret key, bucket name, region, and prefix.",
            )
        prefix = prefix if prefix.endswith("/") else prefix + "/"
        dir_prefix = get_dir_prefix(prefix)
        dir_prefix = "" if dir_prefix == "/" else dir_prefix
        try:
            prefixes = self._s3_utility.get_event_type_prefixes(
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                bucket_name=bucket_name,
                region=region,
                prefix=dir_prefix,
            )
            if not prefixes or prefix not in prefixes:
                raise RestError(
                    status=400,
                    message=f"The specified directory '{prefix}' does not exist in the S3 bucket '{bucket_name}'.",
                )
        except S3ValidationError as e:
            raise RestError(
                status=400,
                message=e.message,
            )

    def _has_s3_details_changed(self) -> bool:
        """
        Checks if the S3-related details in the payload are updated.

        This function checks if the S3-related details (access key, secret key, bucket name, region, and prefix)
        in the payload are updated. If all of these details are present in the payload, it returns `True`.
        Otherwise, it returns `False`.

        Returns:
            bool: True if all S3-related details are present, False otherwise.
        """
        return (
            "access_key_id" in self.payload
            and "secret_access_key" in self.payload
            and "bucket_name" in self.payload
            and "region" in self.payload
            and "prefix" in self.payload
        )
