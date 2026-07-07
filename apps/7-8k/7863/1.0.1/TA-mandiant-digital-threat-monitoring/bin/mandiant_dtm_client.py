"""Mandiant DTM client."""

import requests

from datetime import datetime
from mandiant_dtm_constants import ALERT_PAGE_SIZE, APP_NAME, BASE_URL
from typing import Generator

# List of alert attributes to exclude if index_sensitive_information is false.
# This list is intentionally empty for now as per the requirement.
SENSITIVE_ATTRIBUTES_TO_EXCLUDE = [
    'doc.payment_card',
    'doc.service_account',
    'topics',
]


def _remove_nested_key(data_dict, key_path):
  """
  Removes a key from a nested dictionary based on a dot-separated path.

  Args:
      data_dict (dict): The dictionary to modify.
      key_path (str): A dot-separated string representing the path to the key.
                      Example: 'doc.payment_card'
  """
  keys = key_path.split('.')
  current_level = data_dict

  for i, key in enumerate(keys):
    if not isinstance(current_level, dict):
      return  # Path is invalid or attribute doesn't exist at this level

    if i == len(keys) - 1:  # Last key in the path
      current_level.pop(key, None)  # Remove the key if it exists
    elif key in current_level:
      current_level = current_level[key]
    else:
      return  # Path is invalid or attribute doesn't exist


class DtmClient:
  """
  Creates a session to the DTM API,
  """

  def __init__(
      self,
      key_id: str,
      key_secret: str,
      proxies: dict = None,
      index_sensitive_information: bool = True,
      helper=None,  # pylint: disable=unused-argument
  ):
    """
    Initializes the API client.

    Args:
        key_id: DTM Key ID
        key_secret: DTM  Key Secret
        proxies (dict, optional): A dictionary of proxy settings
        (e.g., {'http': 'http://10.10.1.10:3128',
                'https': 'http://10.10.1.10:1080'}).
        index_sensitive_information (bool):
            If True, sensitive attributes defined in
            SENSITIVE_ATTRIBUTES_TO_EXCLUDE will be get from alerts.
            Defaults to False.
    """
    self.base_url = BASE_URL
    self.session = requests.Session()
    self.session.auth = (key_id, key_secret)
    self.session.headers.update(
        {'X-App-Name': APP_NAME, 'Accept': 'application/json'}
    )
    if proxies is None:
      proxies = {}
    self.session.proxies = proxies
    self.index_sensitive_information = index_sensitive_information

  def _get(self, endpoint: str, params: dict = None) -> requests.Response:
    """
    Performs a GET request to the REST API.

    Args:
        endpoint (str): The specific endpoint to call within the API.
        params (dict, optional): Query parameters to include in the request.

    Returns:
        requests.Response: The response object from the GET request.
    """
    url = f'{self.base_url}{endpoint}'
    if params is None:
      params = {}
    if getattr(self, 'helper', None):
      self.helper.log_debug(url)
    response = self.session.get(url, params=params)
    response.raise_for_status()
    return response

  def get_alerts(
      self,
      since: datetime,
      alert_type: list,
      alert_status: list,
      min_m_score: int,
      page_size: int = ALERT_PAGE_SIZE,
  ) -> Generator:
    """Get all alerts from DTM that meet the specified criteria

    Args:
        page_size (int): The number of alerts to return in each page.
        Max value of 25

    Yields:
        An alert dict
    """
    params = {
        'monitor_name': True,
        'replace_links': True,
        'sanitize': True,
        'since': since.isoformat(),
        'size': page_size,
        'alert_type': alert_type,
        'status': alert_status,
        'mscore_gte': min_m_score,
    }

    while True:
      api_response = self._get('/alerts', params=params)

      if not api_response.json():
        break

      alerts_from_api = api_response.json().get('alerts', [])
      for alert in alerts_from_api:
        if not self.index_sensitive_information:
          for path_to_remove in SENSITIVE_ATTRIBUTES_TO_EXCLUDE:
            _remove_nested_key(alert, path_to_remove)

        yield alert

      if not api_response.links.get('next', {}).get('url'):
        break

      params = {
          'page': api_response.links.get('next', {})
          .get('url')
          .split('?page=')[1]
      }

  def get_monitors(self) -> dict:
    return self._get('/monitors')
