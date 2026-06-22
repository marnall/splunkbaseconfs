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
"""Take snapshot service for calling RPS snapshot API."""

import httpx
from soar_sdk.logging import getLogger

from models.take_snapshot.TakeSnapshotParams import TakeSnapshotParams
from models.take_snapshot.TakeSnapshotOutput import TakeSnapshotOutput
from asset import Asset
from config.constants import DEFAULT_TIMEOUT, ENDPOINT_TAKE_SNAPSHOT, SSL_VERIFY
from utils.url_builder import build_rr_saas_url

logger = getLogger()


def take_snapshot_api(
    params: TakeSnapshotParams, asset: Asset, token: str
) -> TakeSnapshotOutput:
    """
    Call the take snapshot API to create a snapshot of a volume.

    Args:
        params: TakeSnapshot parameters containing volume ID and working environment details
        asset: Asset configuration containing domain
        token: OAuth Bearer token for authentication

    Returns:
        dict with snapshot creation response data

    Raises:
        Exception: If the API call fails

    Example:
        >>> token = get_oauth_token(asset)
        >>> params = TakeSnapshotParams(
        ...     volume_id="vol-123", we_id="we-456", we_type="aws"
        ... )
        >>> response = take_snapshot_api(params, asset, token)
        >>> print(response)
    """
    logger.info(f"take_snapshot_api: Creating snapshot for volume: {params.volume_id}")

    # Convert Pydantic model to request payload
    request_payload = params.model_dump()

    # Build full URL
    url = f"{build_rr_saas_url(asset)}{ENDPOINT_TAKE_SNAPSHOT}"

    # Prepare headers
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    logger.debug(f"take_snapshot_api: URL: {url}")
    logger.debug(f"take_snapshot_api: Payload: {request_payload}")

    try:
        # Make API call (verify=False to allow self-signed certificates)
        with httpx.Client(timeout=DEFAULT_TIMEOUT, verify=SSL_VERIFY) as client:
            response = client.post(url, json=request_payload, headers=headers)

            # Check if request was successful
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            logger.info(
                f"take_snapshot_api: API call successful. Status: {response.status_code}"
            )
            logger.debug(f"take_snapshot_api: Response data: {response_data}")

            logger.info(
                f"take_snapshot_api: Snapshot creation completed for volume {params.volume_id}"
            )

            return TakeSnapshotOutput(**response_data)

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(f"take_snapshot_api: {error_msg}")
        raise Exception(error_msg) from e

    except httpx.RequestError as e:
        error_msg = f"Request error occurred: {e!s}"
        logger.error(f"take_snapshot_api: {error_msg}")
        raise Exception(error_msg) from e

    except Exception as e:
        error_msg = f"Unexpected error: {e!s}"
        logger.error(f"take_snapshot_api: {error_msg}")
        raise Exception(error_msg) from e
