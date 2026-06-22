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
from soar_sdk.abstract import SOARClient
from soar_sdk.logging import getLogger
from soar_sdk.exceptions import ActionFailure
from asset import Asset
from models.volume_offline.VolumeOfflineParams import VolumeOfflineParams
from models.volume_offline.VolumeOfflineOutput import VolumeOfflineOutput
from services.auth_service_api import get_oauth_token_api
from services.volume_offline_api import volume_offline_api

logger = getLogger()


def volume_offline_handler(
    params: VolumeOfflineParams, soar: SOARClient[VolumeOfflineOutput], asset: Asset
) -> VolumeOfflineOutput:
    """
    Take volume offline by calling the REST API.

    This action posts snapshot data to the API and returns the created snapshot details.

    Args:
        params: VolumeOffline parameters containing volume ID and working environment details
        soar: SOAR client for setting summary and messages
        asset: Asset configuration

    Returns:
        VolumeOfflineOutput with the created snapshot details including ID and timestamp
    """
    logger.info(
        f"volume_offline_handler: Starting volume offline process: {params=}, Account: {asset.account_id}"
    )

    try:
        # Get OAuth token
        token = get_oauth_token_api(asset)
        logger.debug("volume_offline_handler: OAuth token retrieved successfully")

        # Call the volume offline service
        response_data = volume_offline_api(params, asset, token)

        soar.set_summary(response_data)
        soar.set_message(f"Volume '{params.volume_id}' taken offline successfully")

        logger.info(
            f"volume_offline_handler: Volume offline process completed for volume {params.volume_id}"
        )

        return response_data

    except Exception as e:
        error_msg = f"Failed to take volume offline: {e!s}"
        logger.error(f"volume_offline_handler: {error_msg}")
        raise ActionFailure(error_msg) from e
