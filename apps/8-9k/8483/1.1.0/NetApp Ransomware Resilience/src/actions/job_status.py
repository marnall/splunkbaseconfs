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
"""Job status action for NetApp RPS SOAR app."""

from soar_sdk.abstract import SOARClient
from soar_sdk.logging import getLogger
from soar_sdk.exceptions import ActionFailure

from asset import Asset
from models.job_status.JobStatusParams import JobStatusParams
from models.job_status.JobStatusOutput import JobStatusOutput
from services.auth_service_api import get_oauth_token_api
from services.job_status_api import get_job_status_api

logger = getLogger()


def job_status_handler(
    params: JobStatusParams, soar: SOARClient[JobStatusOutput], asset: Asset
) -> JobStatusOutput:
    """
    Check the status of a job by calling the job status API.

    This action retrieves the current status and details of a job
    by its job ID.

    Args:
        params: Job status parameters containing job_id
        soar: SOAR client for setting summary and messages
        asset: Asset configuration

    Returns:
        JobStatusOutput with job details including status and records
    """
    logger.info(f"job_status_handler: Checking status for job_id: {params.job_id}")

    try:
        # Get OAuth token
        token = get_oauth_token_api(asset)
        logger.debug("job_status_handler: OAuth token retrieved successfully")

        # Call the job status service
        response = get_job_status_api(params, asset, token)

        logger.debug(f"job_status_handler: Job status response: {response}")

        soar.set_summary(response)
        soar.set_message(
            f"Job '{params.job_id}' status retrieved successfully: {response.status}"
        )

        logger.info(
            f"job_status_handler: Job {params.job_id} status: {response.status}"
        )

        return response

    except Exception as e:
        error_msg = f"Failed to get job status: {e!s}"
        logger.error(f"job_status_handler: {error_msg}")
        raise ActionFailure(error_msg) from e
