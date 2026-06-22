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
"""View handler for IP enrichment results."""

from soar_sdk.logging import getLogger

from models.enrich_ip.EnrichIpOutput import EnrichIpOutput

logger = getLogger()


def render_enrich_ip_jobs_handler(output: EnrichIpOutput) -> dict:
    """
    View handler for rendering IP enrichment job results.

    Transforms the EnrichIpOutput model into a dictionary for template rendering.

    Args:
        output: The EnrichIpOutput model containing job results

    Returns:
        dict: Dictionary representation of the output for template rendering
    """
    logger.info(
        f"render_enrich_ip_jobs_handler: Processing output with {len(output.jobs)} jobs"
    )
    return output.model_dump()
