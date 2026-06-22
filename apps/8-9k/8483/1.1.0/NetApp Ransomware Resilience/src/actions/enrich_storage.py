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
"""Storage enrichment actions for NetApp RPS SOAR app."""

from soar_sdk.abstract import SOARClient
from soar_sdk.logging import getLogger
from soar_sdk.exceptions import ActionFailure

from asset import Asset
from models.enrich_storage.EnrichStorageParams import EnrichStorageParams
from models.enrich_storage.EnrichStorageOutput import EnrichStorageOutput
from services.auth_service_api import get_oauth_token_api
from services.enrich_storage_api import enrich_storage_api

logger = getLogger()


def enrich_storage_handler(
    params: EnrichStorageParams, soar: SOARClient[EnrichStorageOutput], asset: Asset
) -> EnrichStorageOutput:
    """
    Enrich storage information for a given agent and system.

    This action receives agent_id and system_id as input and returns volume details.

    Args:
        params: Storage enrichment parameters containing agent_id and system_id
        soar: SOAR client for setting summary and messages
        asset: Asset configuration

    Returns:
        Storage enrichment output with volume information

    Raises:
        ActionFailure: If the enrichment fails
    """
    logger.debug(
        f"enrich_storage_handler: agent_id={params.agent_id}, system_id={params.system_id}"
    )

    try:
        # Get OAuth token
        token = get_oauth_token_api(asset)
        logger.debug("enrich_storage_handler: OAuth token retrieved successfully")

        # Call the enrichment service
        logger.info("enrich_storage_handler: calling enrich_storage_api")
        output = enrich_storage_api(params, asset, token)

        soar.set_summary(output)
        soar.set_message(
            f"Storage enriched successfully for agent '{params.agent_id}' and system '{params.system_id}'"
        )

        logger.info(
            f"enrich_storage_handler: Storage enrichment completed, found {len(output.volumes)} volumes"
        )

        return output

    except Exception as e:
        error_msg = f"Failed to enrich storage: {e!s}"
        logger.error(f"enrich_storage_handler: {error_msg}")
        raise ActionFailure(error_msg) from e
