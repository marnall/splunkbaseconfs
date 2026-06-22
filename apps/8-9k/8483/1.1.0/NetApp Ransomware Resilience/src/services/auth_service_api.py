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
"""Authentication service for OAuth token management."""

from soar_sdk.logging import getLogger
from soar_sdk.auth import ClientCredentialsFlow

from asset import Asset
from config.constants import OAUTH_CONFIG

logger = getLogger()


def get_oauth_token_api(asset: Asset) -> str:
    """
    Get OAuth access token using client credentials flow.

    This function handles OAuth authentication with Auth0 using the
    client credentials grant type. It returns the access token that
    can be used for subsequent API calls.

    Args:
        asset: Asset configuration containing client_id, client_secret, and auth_state

    Returns:
        str: OAuth access token

    Raises:
        Exception: If token retrieval fails

    Example:
        >>> token = get_oauth_token(asset)
        >>> headers = {"Authorization": f"Bearer {token}"}
    """
    logger.info("get_oauth_token: Retrieving OAuth token using client credentials flow")

    try:
        flow = ClientCredentialsFlow(
            auth_state=asset.auth_state,
            client_id=asset.client_id,
            client_secret=asset.client_secret,
            token_endpoint=OAUTH_CONFIG["ENDPOINT"],
            extra_params={
                "audience": OAUTH_CONFIG["AUDIENCE"],
                "grant_type": OAUTH_CONFIG["GRANT_TYPE"],
            },
        )

        token = flow.get_token().access_token

        logger.info("get_oauth_token: Successfully retrieved OAuth token")
        logger.debug(f"get_oauth_token: access_token: {token}")

        return token

    except Exception as e:
        error_msg = f"Failed to retrieve OAuth token: {e!s}"
        logger.error(f"get_oauth_token: {error_msg}")
        raise Exception(error_msg) from e
