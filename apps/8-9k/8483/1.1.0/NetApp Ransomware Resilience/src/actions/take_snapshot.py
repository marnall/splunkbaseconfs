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
from models.take_snapshot.TakeSnapshotParams import TakeSnapshotParams
from models.take_snapshot.TakeSnapshotOutput import TakeSnapshotOutput
from services.auth_service_api import get_oauth_token_api
from services.take_snapshot_api import take_snapshot_api

logger = getLogger()


def take_snapshot_handler(
    params: TakeSnapshotParams, soar: SOARClient[TakeSnapshotOutput], asset: Asset
) -> TakeSnapshotOutput:
    """
    Take a snapshot of a volume by calling the REST API.

    This action posts snapshot data to the API and returns the created snapshot details.

    Args:
        params: TakeSnapshot parameters containing volume ID and working environment details
        soar: SOAR client for setting summary and messages
        asset: Asset configuration

    Returns:
        TakeSnapshotOutput with the created snapshot details including ID and timestamp
    """
    logger.info(
        f"take_snapshot_handler: Starting snapshot creation: {params=}, Account: {asset.account_id}"
    )

    try:
        # Get OAuth token
        token = get_oauth_token_api(asset)
        logger.debug("take_snapshot_handler: OAuth token retrieved successfully")

        # Call the snapshot service
        response_data = take_snapshot_api(params, asset, token)

        soar.set_summary(response_data)
        soar.set_message(f"Snapshot for volume '{params.volume_id}' taken successfully")

        logger.info(
            f"take_snapshot_handler: Snapshot creation completed for volume {params.volume_id} - Response: {response_data}"
        )

        return response_data

    except Exception as e:
        error_msg = f"Failed to take snapshot: {e!s}"
        logger.error(f"take_snapshot_handler: {error_msg}")
        raise ActionFailure(error_msg) from e
