import json
import requests
import urllib
from typing import Union
import logging


class ManagementConnection:
    def __init__(
        self,
        logger: logging.Logger,
        base_url: str,
        auth_url: str,
        client_id: str,
        client_secret: str,
    ):
        self.base_url = base_url
        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.logger = logger
        self.verify = True
        self.headers = self.get_headers()

    def get_headers(self) -> dict:
        """Create header with OAuth 2.0 authentication information.

        Raises:
            Exception: Error response message.

        Returns:
            dict: Requests header with authentication bearer token.
        """
        response = requests.post(
            url=self.auth_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "api.organization",
                "grant_type": "client_credentials",
            },
            # headers = {"Content-Type": "x-www-form-urlencoded"},
            timeout=30,
        )
        if response.status_code != 200:
            self.logger.error(
                "Unable to get token from authentication endpoint: status code {}".format(
                    response.status_code
                )
            )
            raise ConnectionError

        response_data = response.json()
        if "access_token" not in response_data:
            self.logger.error("Authentication endpoint response does not contain an access token")
            raise ValueError

        return {
            "Authorization": "Bearer {}".format(response_data["access_token"]),
            "Content-Type": "application/json",
        }


class Request:
    def __init__(
        self,
        management_connection: ManagementConnection,
        endpoint: str,
        http_request: str,
        input_params: dict = {},
        body_params: Union[dict, str] = None,
        stream: bool = False,
    ):
        self.management_connection = management_connection
        self.url = f"{management_connection.base_url}/{endpoint}"
        self.mode = http_request
        self.input_params = input_params
        self.data = body_params
        self.stream = stream

    def execute(self):
        """_summary_

        Args:
            paging_index (int, optional): _description_. Defaults to 0.
            only_current_page (bool, optional): _description_. Defaults to False.
            items_per_page (int, optional): _description_. Defaults to 1000.

        Yields:
            _type_: _description_
        """
        should_continue = True
        while should_continue:
            response = requests.Session().request(
                method=self.mode.upper(),
                headers=self.management_connection.headers,
                verify=self.management_connection.verify,
                url=self.url,
                params=self.input_params,
                data=self.data,
                stream=self.stream,
            )
            if response is None or not 200 <= response.status_code < 300:
                http_code_str = requests.status_codes._codes[response.status_code][0]
                error_dict = json.loads(response.text)
                self.management_connection.logger.error(
                    f"Failed to request {urllib.parse.unquote(response.request.url)}. Got status code {response.status_code}: {http_code_str}."
                )
                raise ConnectionError(
                    f"Error: HTTP status {response.status_code} - {http_code_str}, response error {error_dict}"
                )
            response_data = response.json()
            if (
                isinstance(response_data, dict)
                and "data" in response_data.keys()
                and isinstance(response_data["data"], list)
            ):
                for item in response_data["data"]:
                    yield item
            elif isinstance(response_data, list):
                for item in response_data:
                    yield item
            else:
                return response
            should_continue = (
                isinstance(response_data, dict)
                and "continuationToken" in response_data.keys()
                and response_data["continuationToken"] is not None
            )
            if should_continue:
                self.input_params = {"continuationToken": response_data["continuationToken"]}
