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
"""Storage enrichment service for calling RPS storage enrichment API."""

import httpx
from soar_sdk.logging import getLogger

from models.enrich_storage.EnrichStorageParams import EnrichStorageParams
from models.enrich_storage.EnrichStorageOutput import EnrichStorageOutput, VolumeInfo
from asset import Asset
from config.constants import DEFAULT_TIMEOUT, ENDPOINT_ENRICH_STORAGE, SSL_VERIFY
from utils.url_builder import build_rr_saas_url

logger = getLogger()


def enrich_storage_api(
    params: EnrichStorageParams, asset: Asset, token: str
) -> EnrichStorageOutput:
    """
    Call the storage enrichment API to get storage data for an agent and system.

    Args:
        params: Storage enrichment parameters containing agent_id and system_id
        asset: Asset configuration containing domain
        token: OAuth Bearer token for authentication

    Returns:
        EnrichStorageOutput with volume information

    Raises:
        Exception: If the API call fails

    Example:
        >>> token = get_oauth_token_api(asset)
        >>> params = EnrichStorageParams(agent_id="agent-123", system_id="sys-456")
        >>> response = enrich_storage_api(params, asset, token)
        >>> print(response.volumes)
    """
    logger.info(
        f"enrich_storage_api: Enriching storage for agent_id: {params.agent_id}, system_id: {params.system_id}"
    )

    # Convert Pydantic model to dict for query parameters
    query_params = params.model_dump()

    # Build full URL
    url = f"{build_rr_saas_url(asset)}{ENDPOINT_ENRICH_STORAGE}"

    # Prepare headers
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    logger.debug(f"enrich_storage_api: URL: {url}")
    logger.debug(f"enrich_storage_api: Query params: {query_params}")

    try:
        # Make API call (verify=False to allow self-signed certificates)
        with httpx.Client(timeout=DEFAULT_TIMEOUT, verify=SSL_VERIFY) as client:
            response = client.get(url, params=query_params, headers=headers)

            # Check if request was successful
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            logger.info(
                f"enrich_storage_api: API call successful. Status: {response.status_code}"
            )
            logger.debug(f"enrich_storage_api: Response data: {response_data}")

            # Create EnrichStorageOutput from response
            # The API returns a list of volumes directly
            volumes = [VolumeInfo(**volume) for volume in response_data]
            output = EnrichStorageOutput(volumes=volumes)

            logger.info(
                f"enrich_storage_api: Storage enrichment completed, found {len(volumes)} volumes"
            )

            return output

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(f"enrich_storage_api: {error_msg}")
        raise Exception(error_msg) from e

    except httpx.RequestError as e:
        error_msg = f"Request error occurred: {e!s}"
        logger.error(f"enrich_storage_api: {error_msg}")
        raise Exception(error_msg) from e

    except Exception as e:
        error_msg = f"Unexpected error: {e!s}"
        logger.error(f"enrich_storage_api: {error_msg}")
        raise Exception(error_msg) from e
