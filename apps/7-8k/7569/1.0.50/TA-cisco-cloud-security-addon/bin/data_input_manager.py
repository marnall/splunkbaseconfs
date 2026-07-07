import import_declare_test
from typing import Dict
from utils import make_splunk_request


class DataInputManager:
    """
    A class to manage CRUD operations for Splunk data inputs.
    """


    BASE_ENDPOINT = f"/servicesNS/nobody/{import_declare_test.ta_name}/data/inputs/s3_auto_cronjob"


    def __init__(self, session_key: str):
        """
        Initialize the DataInputManager with a Splunk session key.

        Args:
            session_key (str): The Splunk session key for authentication.
        """
        self.session_key = session_key


    def create(self, input_name: str, data: Dict[str, str]) -> Dict:
        """
        Create a new data input.

        Args:
            input_name (str): The name of the account.
            data (Dict[str, str]): The data input configuration.

        Returns:
            Dict: The response from Splunk.
        """
        endpoint = f"{self.BASE_ENDPOINT}/{input_name}"
        try:
            response = make_splunk_request(
                method="POST",
                endpoint=endpoint,
                session_key=self.session_key,
                data=data,
                use_json_output=True,
            )
        except Exception as e:
            raise Exception(f"Failed to create data input: {str(e)}") from e
        return response

    def delete(self, input_name: str) -> None:
        """
        Delete a data input.

        Args:
            input_name (str): The name of the account.
        Args:
            input_name (str): The name of the account.

        Raises:
            Exception: If the deletion fails.
        """
        endpoint = f"{self.BASE_ENDPOINT}/{input_name}"
        try:
            make_splunk_request(
                method="DELETE",
                endpoint=endpoint,
                session_key=self.session_key,
                use_json_output=True,
            )
        except Exception as e:
            if "HTTP 404" in str(e):
                return
            raise Exception(f"Failed to delete data input: {str(e)}") from e
        

    def get(self, input_name: str) -> Dict:
        """
        Get a data input configuration.

        Args:
            input_name (str): The name of the input.

        Returns:
            Dict: The data input configuration.
        
        Raises:
            Exception: If the input is not found.
        """
        endpoint = f"{self.BASE_ENDPOINT}/{input_name}"
        try:
            response = make_splunk_request(
                method="GET",
                endpoint=endpoint,
                session_key=self.session_key,
                use_json_output=True,
            )
        except Exception as e:
            raise Exception(f"Failed to get data input: {str(e)}") from e
        return response
