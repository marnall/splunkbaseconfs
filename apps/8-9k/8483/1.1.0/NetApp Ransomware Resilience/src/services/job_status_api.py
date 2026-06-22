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
"""Job status service for checking RPS job status."""

import httpx
from soar_sdk.logging import getLogger

from asset import Asset
from config.constants import DEFAULT_TIMEOUT, ENDPOINT_JOB_STATUS, SSL_VERIFY
from utils.url_builder import build_rr_saas_url
from models.job_status.JobStatusParams import JobStatusParams
from models.job_status.JobStatusOutput import JobStatusOutput

logger = getLogger()


def get_job_status_api(
    params: JobStatusParams, asset: Asset, token: str
) -> JobStatusOutput:
    """
    Get the status of a job by calling the job status API.

    Args:
        job_id: The UUID of the job to check
        asset: Asset configuration containing domain
        token: OAuth Bearer token for authentication
        endpoint: API endpoint path for job status (e.g., "/job-status")

    Returns:
        JobStatusResponse with job details including status and records

    Raises:
        Exception: If the API call fails

    Example:
        >>> token = get_oauth_token(asset)
        >>> response = get_job_status(
        ...     JobStatusParams(job_id="cf4790b1dfdd90464c611b5a6c5318c7::job-1"),
        ...     asset,
        ...     token,
        ... )
        >>> print(response.status)  # "success"
    """
    logger.info(f"get_job_status: Checking status for job_id: {params.job_id}")

    # Build full URL
    url = f"{build_rr_saas_url(asset)}{ENDPOINT_JOB_STATUS}"

    # Prepare headers
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Convert Pydantic model to dict for query parameters
    query_params = params.model_dump()

    logger.debug(f"get_job_status: URL: {url}")
    logger.debug(f"get_job_status: Query params: {query_params}")

    try:
        # Make API call (verify=False to allow self-signed certificates)
        with httpx.Client(timeout=DEFAULT_TIMEOUT, verify=SSL_VERIFY) as client:
            response = client.get(url, params=query_params, headers=headers)

            # Check if request was successful
            response.raise_for_status()

            # Parse response
            response_data = response.json()
            logger.info(
                f"get_job_status: API call successful. Status: {response.status_code}"
            )
            logger.debug(f"get_job_status: Response data: {response_data}")

            # Convert to Pydantic model
            job_status_response = JobStatusOutput(**response_data)

            logger.info(
                f"get_job_status: Job {params.job_id} status: {job_status_response}"
            )

            return job_status_response

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        logger.error(f"get_job_status: {error_msg}")
        raise Exception(error_msg) from e

    except httpx.RequestError as e:
        error_msg = f"Request error occurred: {e!s}"
        logger.error(f"get_job_status: {error_msg}")
        raise Exception(error_msg) from e

    except Exception as e:
        error_msg = f"Unexpected error: {e!s}"
        logger.error(f"get_job_status: {error_msg}")
        raise Exception(error_msg) from e
