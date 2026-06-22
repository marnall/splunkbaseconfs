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
from soar_sdk.app import App
from soar_sdk.logging import getLogger
from soar_sdk.exceptions import ActionFailure, AssetMisconfiguration
from .apivoid_consts import *
from .asset import Asset
from .actions.get_cert_info import (
    get_cert_info as get_cert_info_action,
    CertificateDetails,
    CertificateSummary,
    GetCertInfoParams,
)
from .actions.domain_reputation import (
    domain_reputation as domain_reputation_action,
    DomainReputationDetails,
    DomainReputationParams,
    DomainReputationSummary,
)
from .actions.ip_reputation import (
    ip_reputation as ip_reputation_action,
    IpReputationDetails,
    IpReputationParams,
    IpReputationSummary,
)
from .rest_api_client import _make_api_request


logger = getLogger()


app = App(
    name="APIvoid v2",
    app_type="reputation",
    logo="logo_apivoid.svg",
    logo_dark="logo_apivoid_dark.svg",
    product_vendor="APIVoid",
    product_name="APIVoid v2",
    publisher="Splunk",
    appid="a1066f2e-bd10-4607-bb3d-e4df99fe6d7f",
    fips_compliant=False,
    asset_cls=Asset,
)


# Test Connectivity Action
@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    """Test connectivity to APIVoid v2 API"""
    logger.progress(MSG_CONNECTING_TO_SERVER)

    try:
        # Test API connectivity with SSL Info endpoint
        params = {"host": TEST_DOMAIN}
        data = _make_api_request(ENDPOINT_SSL_INFO, asset, params)

        # Validate response structure
        if not data.get(KEY_CERTIFICATE):
            raise AssetMisconfiguration(ERROR_UNEXPECTED_RESPONSE)

        logger.progress(MSG_TEST_CONNECTIVITY_PASSED)

    except Exception as e:
        logger.error(MSG_TEST_CONNECTIVITY_FAILED)
        raise ActionFailure(
            f"{MSG_TEST_CONNECTIVITY_FAILED}: {e!s}",
            action_name="test connectivity",
        ) from e


# Register actions (callables so runtime import works on Phantom)
app.register_action(
    get_cert_info_action,
    description="Query certificate information for a domain",
    action_type="investigate",
    params_class=GetCertInfoParams,
    output_class=CertificateDetails,
    summary_type=CertificateSummary,
    render_as="table",
)
app.register_action(
    ip_reputation_action,
    description="Check IP address reputation against blacklists",
    action_type="investigate",
    params_class=IpReputationParams,
    output_class=IpReputationDetails,
    summary_type=IpReputationSummary,
    render_as="table",
)
app.register_action(
    domain_reputation_action,
    description="Check domain reputation against blacklists",
    action_type="investigate",
    params_class=DomainReputationParams,
    output_class=DomainReputationDetails,
    summary_type=DomainReputationSummary,
    render_as="table",
)


if __name__ == "__main__":
    app.cli()
