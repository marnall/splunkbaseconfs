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
"""Test connectivity action for NetApp RPS SOAR app."""

from soar_sdk.logging import getLogger
from soar_sdk.exceptions import ActionFailure

from asset import Asset
from services.auth_service_api import get_oauth_token_api

logger = getLogger()


def test_connectivity_handler(asset: Asset) -> None:
    """
    Test connectivity to the NetApp RPS API using OAuth authentication.

    This action verifies that the configured asset can successfully
    authenticate and obtain an OAuth token.

    Args:
        asset: Asset configuration containing client_id and client_secret

    Raises:
        ActionFailure: If connectivity test fails
    """
    logger.info(
        "test_connectivity_handler: Testing connectivity with OAuth authentication"
    )

    try:
        # Get OAuth token using auth service
        get_oauth_token_api(asset)

        logger.info("test_connectivity_handler: Connectivity test succeeded")

    except Exception as e:
        logger.error(f"test_connectivity_handler: {e!s}")
        raise ActionFailure(f"{e!s}") from e
