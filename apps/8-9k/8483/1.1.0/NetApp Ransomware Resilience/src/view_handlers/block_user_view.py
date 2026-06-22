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
"""View handler for block user results."""

from soar_sdk.logging import getLogger

from models.block_user.BlockUserOutput import BlockUserOutput

logger = getLogger()


def render_block_user_handler(output: BlockUserOutput) -> dict:
    """
    View handler for rendering block user results.

    Transforms the BlockUserOutput model into a dictionary for template rendering.

    Args:
        output: The BlockUserOutput model containing result message

    Returns:
        dict: Dictionary representation of the output for template rendering
    """
    logger.info("render_block_user_handler: Processing block user output")
    return output.model_dump()
