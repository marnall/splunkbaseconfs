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

from soar_sdk.params import Param, Params


class BlockUserParams(Params):
    """
    Parameters for block user action.

    Attributes:
        user_id: User ID to block
        user_ips: Client IPs to block as comma-separated string (required for NFS; optional for CIFS)
        duration: Block duration - permanent or hours (1, 2, 4, 8, 12, 24)
    """

    user_id: str = Param(description="User ID to block")
    user_ips: str = Param(
        default=None,
        allow_list=True,
        description="Client IPs to block (required for NFS; optional for CIFS). Comma-separated.",
    )
    duration: str = Param(
        default=None,
        description="Block duration - permanent or hours (1, 2, 4, 8, 12, 24)",
        value_list=["permanent", "1", "2", "4", "8", "12", "24"],
    )
