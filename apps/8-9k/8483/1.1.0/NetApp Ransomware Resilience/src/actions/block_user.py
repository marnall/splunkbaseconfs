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
"""Block user action for NetApp RPS SOAR app."""

from soar_sdk.abstract import SOARClient
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from asset import Asset
from models.block_user.BlockUserOutput import BlockUserOutput
from models.block_user.BlockUserParams import BlockUserParams
from services.auth_service_api import get_oauth_token_api
from services.block_user_api import block_user_api

logger = getLogger()


def block_user_handler(
    params: BlockUserParams, soar: SOARClient[BlockUserOutput], asset: Asset
) -> BlockUserOutput:
    """
    Block a user from accessing storage resources.

    This action blocks a user based on user_id and/or client IPs for a specified duration.

    Args:
        params: Block user parameters including user_id, user_ips, and duration
        soar: SOAR client for setting summary and messages
        asset: Asset configuration

    Returns:
        Block user output with status message
    """
    logger.debug(
        f"block_user_handler: User ID: {params.user_id}, IPs: {params.user_ips}"
    )

    try:
        # Get OAuth token
        token = get_oauth_token_api(asset)
        logger.debug("block_user_handler: OAuth token retrieved successfully")

        # Call the block user service
        logger.info("block_user_handler: calling block_user_api")
        output = block_user_api(params, asset, token)

        soar.set_summary(output)
        soar.set_message(
            f"User '{params.user_id or params.user_ips}' blocked successfully"
        )

        logger.info(
            f"block_user_handler: Block user completed for {params.user_id or params.user_ips}"
        )

        return output

    except Exception as e:
        error_msg = f"Failed to block user: {e!s}"
        logger.error(f"block_user_handler: {error_msg}")
        raise ActionFailure(error_msg) from e
