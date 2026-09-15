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
import re

from pydantic import field_validator
from soar_sdk.asset import BaseAsset, AssetField

_VANITY_DOMAIN_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


class Asset(BaseAsset):
    vanity_domain: str = AssetField(
        description=(
            "Zscaler OneAPI vanity-domain prefix, for example "
            "'dev-new-soar-splunk' rather than a full URL or email address"
        ),
        required=True,
    )
    client_id: str = AssetField(
        description="OAuth client ID for the Zscaler OneAPI API client",
        required=True,
    )
    client_secret: str = AssetField(
        description="OAuth client secret for the Zscaler OneAPI API client",
        required=True,
        sensitive=True,
    )
    cloud: str = AssetField(
        description=(
            "Zscaler OneAPI cloud environment used to derive OAuth and API endpoints"
        ),
        default="PRODUCTION",
        required=False,
    )

    @field_validator("vanity_domain")
    @classmethod
    def validate_vanity_domain(cls, value: str) -> str:
        if not _VANITY_DOMAIN_PATTERN.fullmatch(value):
            raise ValueError(
                "vanity_domain must be a domain prefix containing only letters, "
                "numbers, and internal hyphens"
            )
        return value
