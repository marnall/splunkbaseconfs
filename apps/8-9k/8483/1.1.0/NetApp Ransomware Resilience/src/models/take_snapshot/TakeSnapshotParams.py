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
"""Parameters for take snapshot action."""

from soar_sdk.params import Params


class TakeSnapshotParams(Params):
    """
    Parameters for taking a snapshot of a volume.

    Attributes:
        volume_id: UUID of the volume to snapshot
        working_environment: Working environment details containing we_id and we_type
    """

    volume_id: str
    agent_id: str
    system_id: str
