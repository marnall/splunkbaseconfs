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
from zscaler import ZscalerClient

from .asset import Asset

SPLUNK_ZSCALER_PARTNER_ID = "ptr_O9IXHIjxsno4dij0GSExUY"
DEFAULT_REQUEST_TIMEOUT = 240
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_RETRY_SECONDS = 60


def get_client(
    asset: Asset, *, request_timeout: int = DEFAULT_REQUEST_TIMEOUT
) -> ZscalerClient:
    """Create the official Zscaler client from an asset."""
    return ZscalerClient(
        {
            "clientId": asset.client_id,
            "clientSecret": asset.client_secret,
            "vanityDomain": asset.vanity_domain,
            "cloud": asset.cloud,
            "partnerId": SPLUNK_ZSCALER_PARTNER_ID,
            "requestTimeout": request_timeout,
            "rateLimit": {
                "maxRetries": DEFAULT_MAX_RETRIES,
                "maxRetrySeconds": DEFAULT_MAX_RETRY_SECONDS,
            },
        }
    )
