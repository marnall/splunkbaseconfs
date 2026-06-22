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
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.exceptions import ActionFailure
from soar_sdk.logging import getLogger
from soar_sdk.params import Param, Params

from ..apivoid_consts import *
from ..asset import Asset
from ..rest_api_client import _make_api_request

logger = getLogger()


class IpReputationParams(Params):
    """Parameters for IP reputation action"""

    ip: str = Param(
        description="IP address to check reputation",
        primary=True,
        cef_types=["ip"],
        column_name="IP Address",
    )


class IpBlacklistEngine(ActionOutput):
    """Individual blacklist engine result for IP"""

    name: str | None = OutputField(
        column_name="Engine",
    )
    detected: bool | None = OutputField(
        column_name="Detected",
    )
    reference: str | None = OutputField(
        cef_types=["url"],
        column_name="Reference",
    )
    elapsed_ms: int | None = None


class IpReputationDetails(ActionOutput):
    """IP reputation check details and results"""

    # Basic IP Info
    ip: str | None = OutputField(cef_types=["ip"])
    version: str | None = None

    # Blacklist Scan Results
    detections: int | None = None
    engines_count: int | None = None
    detection_rate: str | None = None
    scan_time_ms: int | None = None
    elapsed_ms: int | None = None
    engines: list[IpBlacklistEngine] | None = None

    # Geolocation Information
    reverse_dns: str | None = OutputField(cef_types=["host name"])
    continent_code: str | None = None
    continent_name: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    isp: str | None = None

    # Bot & Service Detection
    is_bogon: bool | None = None
    is_spamhaus_drop: bool | None = None
    is_fake_bot: bool | None = None
    is_google_bot: bool | None = None
    is_search_engine_bot: bool | None = None
    is_public_dns: bool | None = None
    cloud_provider: str | None = None
    aws_service: str | None = None
    is_google_service: bool | None = None
    is_satellite: bool | None = None

    # ASN Details
    asn: str | None = None
    asname: str | None = None
    asn_route: str | None = None
    asn_org: str | None = None
    asn_country_code: str | None = None
    abuse_email: str | None = OutputField(cef_types=["email"])
    asn_domain: str | None = OutputField(cef_types=["domain"])
    asn_type: str | None = None

    # Anonymity Detection
    is_proxy: bool | None = None
    is_webproxy: bool | None = None
    is_residential_proxy: bool | None = None
    is_vpn: bool | None = None
    is_hosting: bool | None = None
    is_relay: bool | None = None
    is_tor: bool | None = None

    # Risk Score
    risk_score: int | None = None


class IpReputationSummary(ActionOutput):
    """Summary information for IP reputation check"""

    detections: int | None = None
    engines_count: int | None = None
    detection_rate: str | None = None

    def get_message(self) -> str:
        """Generate formatted summary message"""
        if self.detections is not None and self.engines_count is not None:
            return f"Detections: {self.detections}, Engines count: {self.engines_count}"
        elif self.detection_rate is not None:
            return f"Detection rate: {self.detection_rate}"
        else:
            return "IP reputation check completed (no detection data)"


def ip_reputation(
    param: IpReputationParams,
    soar: SOARClient[IpReputationSummary],
    asset: Asset,
) -> IpReputationDetails:
    """Check IP address reputation against multiple blacklist engines."""
    logger.progress(MSG_QUERYING_IP_REP.format(param.ip))

    params = {"ip": param.ip}
    data = _make_api_request(ENDPOINT_IP_REPUTATION, asset, params)

    blacklists = data.get(KEY_BLACKLISTS)
    if not blacklists:
        raise ActionFailure(ERROR_NO_BLACKLIST_DATA)

    engines_list = []
    engines_data = blacklists.get(KEY_ENGINES, {})
    for engine_name, engine_info in engines_data.items():
        engines_list.append(
            IpBlacklistEngine(
                name=engine_info.get("name", engine_name),
                detected=engine_info.get("detected"),
                reference=engine_info.get("reference"),
                elapsed_ms=engine_info.get("elapsed_ms"),
            )
        )

    information = data.get("information", {})
    asn_data = data.get("asn", {})
    anonymity = data.get("anonymity", {})
    risk_score = data.get("risk_score", {})

    result = IpReputationDetails(
        ip=data.get("ip"),
        version=data.get("version"),
        detections=blacklists.get("detections"),
        engines_count=blacklists.get("engines_count"),
        detection_rate=blacklists.get("detection_rate"),
        scan_time_ms=blacklists.get("scan_time_ms"),
        elapsed_ms=data.get("elapsed_ms"),
        engines=engines_list,
        reverse_dns=information.get("reverse_dns"),
        continent_code=information.get("continent_code"),
        continent_name=information.get("continent_name"),
        country_code=information.get("country_code"),
        country_name=information.get("country_name"),
        region_name=information.get("region_name"),
        city_name=information.get("city_name"),
        latitude=information.get("latitude"),
        longitude=information.get("longitude"),
        isp=information.get("isp"),
        is_bogon=information.get("is_bogon"),
        is_spamhaus_drop=information.get("is_spamhaus_drop"),
        is_fake_bot=information.get("is_fake_bot"),
        is_google_bot=information.get("is_google_bot"),
        is_search_engine_bot=information.get("is_search_engine_bot"),
        is_public_dns=information.get("is_public_dns"),
        cloud_provider=information.get("cloud_provider"),
        aws_service=information.get("aws_service"),
        is_google_service=information.get("is_google_service"),
        is_satellite=information.get("is_satellite"),
        asn=asn_data.get("asn"),
        asname=asn_data.get("asname"),
        asn_route=asn_data.get("route"),
        asn_org=asn_data.get("org"),
        asn_country_code=asn_data.get("country_code"),
        abuse_email=asn_data.get("abuse_email"),
        asn_domain=asn_data.get("domain"),
        asn_type=asn_data.get("type"),
        is_proxy=anonymity.get("is_proxy"),
        is_webproxy=anonymity.get("is_webproxy"),
        is_residential_proxy=anonymity.get("is_residential_proxy"),
        is_vpn=anonymity.get("is_vpn"),
        is_hosting=anonymity.get("is_hosting"),
        is_relay=anonymity.get("is_relay"),
        is_tor=anonymity.get("is_tor"),
        risk_score=risk_score.get("result"),
    )

    summary = IpReputationSummary(
        detections=result.detections,
        engines_count=result.engines_count,
        detection_rate=result.detection_rate,
    )
    soar.set_summary(summary)
    soar.set_message(summary.get_message())
    return result
