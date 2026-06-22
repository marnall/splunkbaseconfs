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
"""IP enrichment service for calling RPS IP enrichment API."""

import httpx
from soar_sdk.logging import getLogger

from models.enrich_ip.EnrichIpParams import EnrichIpParams
from models.enrich_ip.EnrichIpOutput import EnrichIpOutput
from asset import Asset
from config.constants import DEFAULT_TIMEOUT, ENDPOINT_ENRICH_IP, SSL_VERIFY
from utils.url_builder import build_rr_saas_url

logger = getLogger()


def enrich_ip_api(params: EnrichIpParams, asset: Asset, token: str) -> EnrichIpOutput:
    """
    Call the IP enrichment API to get enrichment data for an IP address.

    Args:
        params: IP enrichment parameters containing the IP address to enrich
        asset: Asset configuration containing domain
        token: OAuth Bearer token for authentication

    Returns:
        EnrichIpOutput with enrichment jobs data

    Raises:
        Exception: If the API call fails

    Example:
        >>> token = get_oauth_token(asset)
        >>> params = EnrichIpParams(ip_address="192.168.1.1")
        >>> response = enrich_ip_api(params, asset, token)
        >>> print(response.jobs)
    """
    logger.info(f"enrich_ip_api: Enriching IP address: {params.ip_address}")

    # Convert Pydantic model to dict
    request_payload = params.model_dump()

    # Build full URL
    url = f"{build_rr_saas_url(asset)}{ENDPOINT_ENRICH_IP}"

    # Prepare headers
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    logger.debug(f"enrich_ip_api: URL: {url}")
    logger.debug(f"enrich_ip_api: Payload: {request_payload}")

    try:
        # Make API call (verify=False to allow self-signed certificates)
        with httpx.Client(timeout=DEFAULT_TIMEOUT, verify=SSL_VERIFY) as client:
            response = client.post(url, json=request_payload, headers=headers)

            # Check if request was successful
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            logger.info(
                f"enrich_ip_api: API call successful. Status: {response.status_code}"
            )
            logger.debug(f"enrich_ip_api: Response data: {response_data}")

            # Create EnrichIpOutput from response
            output = EnrichIpOutput(jobs=response_data)

            logger.info(
                f"enrich_ip_api: IP enrichment completed for {params.ip_address}"
            )

            return output

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(f"enrich_ip_api: {error_msg}")
        raise Exception(error_msg) from e

    except httpx.RequestError as e:
        error_msg = f"Request error occurred: {e!s}"
        logger.error(f"enrich_ip_api: {error_msg}")
        raise Exception(error_msg) from e

    except Exception as e:
        error_msg = f"Unexpected error: {e!s}"
        logger.error(f"enrich_ip_api: {error_msg}")
        raise Exception(error_msg) from e
