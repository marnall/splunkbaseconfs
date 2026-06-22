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
"""IP enrichment actions for NetApp RPS SOAR app."""

from soar_sdk.abstract import SOARClient
from soar_sdk.logging import getLogger
from soar_sdk.exceptions import ActionFailure
from asset import Asset
from models.enrich_ip.EnrichIpOutput import EnrichIpOutput
from models.enrich_ip.EnrichIpParams import EnrichIpParams
from services.auth_service_api import get_oauth_token_api
from services.enrich_ip_api import enrich_ip_api


logger = getLogger()


def enrich_ip_address_handler(
    params: EnrichIpParams, soar: SOARClient[EnrichIpOutput], asset: Asset
) -> EnrichIpOutput:
    """
    Enrich IP address with additional information.

    This action receives an IP as input and returns details regarding that IP.

    Args:
        params: IP enrichment parameters
        soar: SOAR client for setting summary and messages
        asset: Asset configuration

    Returns:
        IP enrichment output with system, network, city, and country information
    """
    logger.debug(f"enrich_ip_address_handler: IP Address: {params.ip_address}")

    try:
        # Get OAuth token
        token = get_oauth_token_api(asset)
        logger.debug("enrich_ip_address_handler: OAuth token retrieved successfully")

        # Call the enrichment service
        logger.info("enrich_ip_address_handler: calling enrich_ip_api")
        output = enrich_ip_api(params, asset, token)

        soar.set_summary(output)
        soar.set_message(f"IP address '{params.ip_address}' enriched successfully")

        logger.info(
            f"enrich_ip_address_handler: IP enrichment completed for {params.ip_address} - Response: {output.jobs}"
        )

        return output

    except Exception as e:
        error_msg = f"Failed to enrich IP address: {e!s}"
        logger.error(f"enrich_ip_address_handler: {error_msg}")
        raise ActionFailure(error_msg) from e
