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
"""Enrich storage output model."""

from pydantic import ConfigDict, Field
from soar_sdk.action_results import ActionOutput


class VolumeInfo(ActionOutput):
    """Individual volume information."""

    model_config = ConfigDict(populate_by_name=True)

    volume_uuid: str
    volume_name: str
    svm_name: str


class EnrichStorageOutput(ActionOutput):
    """Output for enrich storage action."""

    model_config = ConfigDict(populate_by_name=True)

    volumes: list[VolumeInfo] = Field(default_factory=list)
