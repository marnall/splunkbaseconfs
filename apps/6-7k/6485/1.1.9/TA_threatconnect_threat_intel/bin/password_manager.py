"""Password Manager Module"""

# standard library
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))
# third-party
from splunklib import client


class PasswordManager:
    """Password Manager Class"""

    MASK = "<nothing to see here>"

    def encrypt_and_mask_password(self, input_item, input_name, session_key):
        """Encrypt and mask the password if not already masked."""
        if input_item.get("api_secret_key") != self.MASK:
            self.encrypt_password(
                input_item.get("api_access_id"),
                input_item.get("api_secret_key"),
                session_key,
            )
            self.mask_password(session_key, input_name, input_item.get("api_access_id"))

    @staticmethod
    def encrypt_password(username, password, session_key):
        """Store the username-password combination in storage passwords."""

        service = client.connect(token=session_key)

        try:
            # If the credential already exists, delete it.
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(username=storage_password.username)
                    break

            # Create the credential.
            service.storage_passwords.create(password, username, realm="tcAPI")

        except Exception as exception:
            raise RuntimeError(
                "An error occurred updating credentials. Please ensure your user "
                "account has admin_all_objects and/or list_storage_passwords "
                f"capabilities. Details: {str(exception)}"
            ) from exception

    def mask_password(self, session_key, input_name, username):
        """Update the Data Input to mask the Password."""
        try:
            args = {"token": session_key}
            service = client.connect(**args)
            kind, input_name = input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))

            kwargs = {"api_access_id": username, "api_secret_key": self.MASK}
            item.update(**kwargs).refresh()

        except Exception as exception:
            raise Exception(
                f"Error updating inputs.conf: {str(exception)}"
            ) from exception

    @staticmethod
    def get_password(service, username):
        """Retrieve the password from the storage/passwords endpoint."""
        for storage_password in service.storage_passwords:
            if (
                storage_password.username == username
                and storage_password.realm == "tc_api"
            ):
                return storage_password.content.clear_password
        return None
