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
"""View handler for volume offline action results."""

from soar_sdk.logging import getLogger

from models.volume_offline.VolumeOfflineOutput import VolumeOfflineOutput

logger = getLogger()


def render_volume_offline_handler(output: VolumeOfflineOutput) -> dict:
    """
    View handler for rendering volume offline results.

    Transforms the VolumeOfflineOutput model into a dictionary for template rendering.

    Args:
        output: The VolumeOfflineOutput model containing job information

    Returns:
        dict: Dictionary representation of the output for template rendering
    """
    logger.info(
        f"render_volume_offline_handler: Processing offline job {output.job_id}"
    )
    return output.model_dump()
