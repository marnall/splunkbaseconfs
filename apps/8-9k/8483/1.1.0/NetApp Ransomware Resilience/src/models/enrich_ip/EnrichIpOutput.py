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
from soar_sdk.action_results import ActionOutput


class JobItem(ActionOutput):
    """
    Individual job item in the response.

    Attributes:
        job_id: Unique identifier for the job
        status: Current status of the job (e.g., 'queued', 'running', 'completed')
    """

    job_id: str
    status: str
    source: str
    agent_id: str


class EnrichIpOutput(ActionOutput):
    """
    Output data for IP enrichment action.

    Returns a list of job items with their status.

    Attributes:
        items: List of job items containing job_id and status
    """

    jobs: list[JobItem]
