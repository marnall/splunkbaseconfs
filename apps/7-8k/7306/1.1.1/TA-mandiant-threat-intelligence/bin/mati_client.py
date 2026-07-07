import requests
from typing import Generator

import mati_constants as mc


class MatiApiClient:
    """Creates a session to the MATI API."""

    def __init__(self, key_id: str, key_secret: str, proxies: dict = None):
        """
        Initializes the API client.

        Args:
            key_id: MATI Key ID
            key_secret: MATI Key Secret
            proxies (dict, optional): A dictionary of proxy settings
            (e.g., {'http': 'http://10.10.1.10:3128', 'https': 'http://10.10.1.10:1080'}).
        """
        self.base_url = mc.BASE_URL
        self.session = requests.Session()
        self.session.auth = (key_id, key_secret)
        self.session.headers.update({"X-App-Name": mc.APP_NAME,
                                     "Accept": "application/json"})
        self.session.proxies = proxies

    def _get(self, endpoint: str, params: dict = None):
        """
        Performs a GET request to the REST API.

        Args:
            endpoint (str): The specific endpoint to call within the API.
            params (dict, optional): Query parameters to include in the request.

        Returns:
            requests.Response: The response object from the GET request.
        """
        return self.session.get(f"{self.base_url}{endpoint}", params=params)

    def get_entitlements(self) -> requests.Response:
        """Entitlements."""
        return self._get(mc.ENTITLEMENTS_PATH)

    def get_indicators(self, start_date: int, end_date: int, logger=None) -> Generator:
        """Get all Indicators from MATI that meet the specified criteria.

        Args:
            start_epoch (int): the start of the time range in epoch format
            end_epoch (int): the end of the time range in epoch format

        Yields:
            An Indicator dict
        """
        params = {
            "start_epoch": start_date,
            "end_epoch": end_date,
            "limit": mc.INDICATOR_PAGE_SIZE,
            "include_campaigns": True,
            "include_reports": True,
            "include_threat_rating": True,
            "include_misp": False,
            "include_category": True
        }

        while True:
            logger.debug(
                f"message=HttpRequest | type=Get, endpoint={mc.INDICATORS_PATH}, "
                f"params={params} initiating..."
            )
            api_response = self._get(
                mc.INDICATORS_PATH, params=params
            ).json()

            if not api_response:
                break

            indicators_from_api = api_response.get("indicators", [])
            for indicator in indicators_from_api:
                yield indicator

            if not api_response.get("next") or len(indicators_from_api) != mc.INDICATOR_PAGE_SIZE:
                break

            params = {"next": api_response.get("next"), "include_campaigns": True}
