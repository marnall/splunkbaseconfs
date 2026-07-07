import requests
import json
import urllib


class ManagementConnection:
    BASE_PATH = "/admin"
    OAUTH_EXT = "protocol/openid-connect/token"
    REALM = "master"

    def __init__(self, logger, base_url, client_id, client_secret):
        host = base_url if base_url.startswith("https://") else "https://" + base_url
        self.host = host[-1:] if host.endswith("/") else host
        self.base_url = host + self.BASE_PATH
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
        auth_response = requests.post(
            url=f"{self.host}/realms/{self.REALM}/{self.OAUTH_EXT}",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            verify=self.verify,
            timeout=30,
        )
        if auth_response.status_code == 404:
            # Compatibility for old keycloak version
            auth_response = requests.post(
                url=f"{self.host}/auth/realms/{self.REALM}/{self.OAUTH_EXT}",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
                verify=self.verify,
                timeout=30,
            )
        if auth_response.status_code != 200:
            self.logger.error(
                "Unable to get token from IAM: status code {}".format(auth_response.status_code)
            )
            raise ConnectionError

        response_data = auth_response.json()
        if "access_token" not in response_data:
            helper.log_error("Authentication endpoint response does not contain an access token")
            raise ValueError

        return {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(response_data["access_token"]),
        }


class Request:
    def __init__(
        self,
        management_connection: ManagementConnection,
        endpoint: str,
        http_request: str = "GET",
        input_params: dict = {},
        body_params=None,
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
        response = requests.Session().request(
            method=self.mode.upper(),
            headers=self.management_connection.get_headers(),
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
