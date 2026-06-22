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
"""URL builder utility for constructing RR SaaS endpoints."""

from asset import Asset
from config.constants import RRS_SERVICE_URL


def build_rr_saas_url(asset: Asset) -> str:
    """
    Construct the RR SaaS API URL.

    Args:
        asset: The Asset object containing the RR account id

    Returns:
        Complete URL string in format: https://{domain}/rps/v1/account/{account_id}

    Example:
        >>> build_rr_saas_url("snapcenter.cloudmanager.cloud.netapp.com")
        'https://snapcenter.cloudmanager.cloud.netapp.com/rps/v1/account/{account_id}'
    """
    # Construct the URL
    url = f"{RRS_SERVICE_URL}/{asset.account_id}"

    return url
