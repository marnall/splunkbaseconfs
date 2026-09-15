"""
Factory module for creating a configured FlareApiClient (official flareio SDK).

This replaces the custom api_client.py. The SDK handles:
  - JWT token generation and auto-refresh
  - Retry with exponential backoff (5 retries, urllib3 Retry)
  - Rate limiting awareness

Proxy and SSL settings are applied via a custom requests.Session
passed to FlareApiClient(session=...).
"""

import logging
import os
import sys


# Ensure the vendored lib directory is on the path
_LIB_DIR = os.path.join(os.path.dirname(__file__), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import requests

from flare_ssl import UnverifiedHTTPAdapter
from flareio import FlareApiClient
from requests.adapters import HTTPAdapter
from typing import Optional
from urllib3.util import Retry


logger = logging.getLogger("flare_cron_job")


def _build_session(
    proxies: Optional[dict] = None,
    ssl_verify: bool = True,
) -> requests.Session:
    """
    Create a requests.Session pre-configured with:
      - Proxy settings
      - SSL verification preference
      - Retry policy with backoff (mirrors SDK defaults for consistency)
    """
    session = requests.Session()

    if proxies:
        session.proxies.update(proxies)

    session.verify = ssl_verify

    # Retry policy: 5 attempts, backoff x2, retry on 429/5xx
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 502, 503, 504],
        allowed_methods={"GET", "POST"},
    )
    if hasattr(retry, "backoff_max"):
        retry.backoff_max = 15

    adapter = (
        HTTPAdapter(max_retries=retry)
        if ssl_verify
        else UnverifiedHTTPAdapter(max_retries=retry)
    )
    session.mount("https://", adapter)

    return session


def create_flare_client(
    api_key: str,
    proxies: Optional[dict] = None,
    ssl_verify: bool = True,
) -> FlareApiClient:
    """
    Create and return a FlareApiClient instance configured with the given
    API key, proxy settings, and SSL verification preference.
    """
    session = _build_session(proxies=proxies, ssl_verify=ssl_verify)
    return FlareApiClient(api_key=api_key, session=session)
