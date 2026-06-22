# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""REST client for APIVoid v2 API call"""

import requests
from soar_sdk.exceptions import ActionFailure, AssetMisconfiguration
from soar_sdk.logging import getLogger

from .apivoid_consts import (
    CONTENT_TYPE_JSON,
    DEFAULT_TIMEOUT,
    HEADER_API_KEY,
    HEADER_CONTENT_TYPE,
)
from .asset import Asset

logger = getLogger()


def _make_api_request(endpoint: str, asset: Asset, params: dict) -> dict:
    """
    REST API call to APIVoid v2.

    :param endpoint: API endpoint (e.g., 'v2/ssl-info')
    :param asset: Asset instance (server_url, api_key)
    :param params: Request parameters to send as JSON body
    :return: Response JSON data
    :raises ActionFailure: If request fails or API returns an error
    :raises AssetMisconfiguration: If authentication fails (401/403)
    """
    url = f"{asset.server_url.rstrip('/')}/{endpoint}"
    headers = {
        HEADER_API_KEY: asset.api_key,
        HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
    }

    logger.progress("Making API request to: %s", url)

    try:
        response = requests.post(
            url, json=params, headers=headers, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        try:
            detail = e.response.json().get("error") or e.response.text
        except ValueError:
            detail = e.response.text
        if status in (401, 403):
            raise AssetMisconfiguration(
                f"Authentication failed (HTTP {status}). Check your API key. Detail: {detail}"
            ) from e
        raise ActionFailure(f"HTTP {status}: {detail}") from e
    except Exception as e:
        raise ActionFailure(str(e)) from e
    if (error_msg := data.get("error")) is not None:
        raise ActionFailure(str(error_msg))
    return data
