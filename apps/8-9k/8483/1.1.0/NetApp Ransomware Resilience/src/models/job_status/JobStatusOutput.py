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
from pydantic import ConfigDict


class JobRecord(ActionOutput):
    """Individual job record in the response."""

    system_id: str
    ip_address: str
    lif_type: str
    scope: str
    svm: str
    agent_id: str


class JobStatusOutput(ActionOutput):
    """Response model for job status."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: str
    source: str | None = None
    status: str
    records: list[
        JobRecord
    ]  # Use list[dict] instead of list[JobRecord] to avoid nesting issues
    message: str | None = None
