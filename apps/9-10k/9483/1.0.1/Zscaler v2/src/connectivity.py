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
from soar_sdk.abstract import SOARClient
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger

from .asset import Asset
from .zscaler_client import get_client

logger = getLogger()


def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    """Authenticate through OneAPI and read the ZIA configuration activation status."""
    try:
        with get_client(asset) as client:
            activation, _response, error = client.zia.activate.status()
            if error is not None:
                raise RuntimeError(f"Zscaler API error: {error}")
            if activation is None:
                raise RuntimeError("Zscaler API returned no data")

            status = getattr(activation, "status", None)
            if not status:
                raise RuntimeError("Zscaler API returned no ZIA configuration status")
    except Exception as exc:
        message = f"Connectivity test failed: {exc}"
        soar.set_message(message)
        raise ActionFailure(message) from exc

    logger.info("Test connectivity passed. ZIA configuration status: %s", status)
    soar.set_message("Test connectivity passed")
