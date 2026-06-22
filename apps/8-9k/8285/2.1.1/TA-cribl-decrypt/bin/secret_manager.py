from httplib2 import Response
from splunk import rest  # type: ignore
from splunk import ResourceNotFound  # type: ignore

from key import Key
from handler_utils import APP_NAME


class SecretManager:
    PASSWORD_ENDPOINT = f'/servicesNS/nobody/{APP_NAME}/storage/passwords'

    """
    Management class for dealing with Splunk's secret store.
    """    
    def __init__(self, token):
        self.token = token

    def get_key(self, key_id: str) -> Response:
        """
        Get a key from the Splunk secret store for this app.

        Args:
            key_id (str): The ID of the key to pull from the secret store.

        Returns:
            Response: a reponse object to be handled by calling process.
        """        
        response, _ = rest.simpleRequest(
            f"{self.PASSWORD_ENDPOINT}/{key_id}",
            method="GET",
            headers={
                "Content-Type": "application/json",
            },
            sessionKey=self.token,
        )

        return response

    def key_exists(self, key_id: str) -> bool:
        """
        Returns true if a key exists, false otherwise.

        Args:
            key_id (str): The ID to check for existence

        Returns:
            bool: whether the key exists in this store or not
        """        
        try:
            self.get_key(key_id)
        except ResourceNotFound:
            # Not loving exception handling as logic flow but... The Splunk REST util throws this on 404 instead of just returning the 404.
            return False
        return True

    def add_key(self, key: Key) -> Response:
        """
        Adding a new key to the secret store.

        Args:
            key (Key): The key object to serialize and send.

        Returns:
            Response: the HTTP response from the add for the caller to handle
        """        
        payload = {"password": key.to_json(), "name": key.key_id}
        response, _ = rest.simpleRequest(
            self.PASSWORD_ENDPOINT,
            method="POST",
            postargs=payload,
            headers={
                "Content-Type": "application/json",
            },
            sessionKey=self.token,
        )

        return response

    def update_key(self, key: Key) -> Response:
        """
        Updating an existing key

        Args:
            key (Key):  The key object to serialize and send

        Returns:
            Response: the HTTP response from the update for the caller to handle
        """        
        payload = {"password": key.to_json()}
        response, _ = rest.simpleRequest(
            f"{self.PASSWORD_ENDPOINT}/{key.key_id}",
            method="POST",
            postargs=payload,
            headers={
                "Content-Type": "application/json",
            },
            sessionKey=self.token,
        )

        return response

    def delete_key(self, key_id: str) -> Response:
        """
        Delete an existing key

        Args:
            key (Key):  The key object to serialize and send

        Returns:
            Response: the HTTP response from the delete for the caller to handle
        """      
        response, _ = rest.simpleRequest(
            f"{self.PASSWORD_ENDPOINT}/{key_id}",
            method="DELETE",
            headers={
                "Content-Type": "application/json",
            },
            sessionKey=self.token,
        )

        return response
