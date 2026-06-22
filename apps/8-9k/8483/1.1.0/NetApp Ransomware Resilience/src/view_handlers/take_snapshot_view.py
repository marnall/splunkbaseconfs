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
"""View handler for take snapshot action results."""

from soar_sdk.logging import getLogger

from models.take_snapshot.TakeSnapshotOutput import TakeSnapshotOutput

logger = getLogger()


def render_take_snapshot_handler(output: TakeSnapshotOutput) -> dict:
    """
    View handler for rendering take snapshot results.

    Transforms the TakeSnapshotOutput model into a dictionary for template rendering.

    Args:
        output: The TakeSnapshotOutput model containing job information

    Returns:
        dict: Dictionary representation of the output for template rendering
    """
    logger.info(
        f"render_take_snapshot_handler: Processing snapshot job {output.job_id}"
    )
    return output.model_dump()
