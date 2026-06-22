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


class GetCertInfoParams(Params):
    """Parameters for get_cert_info action input"""

    domain: str = Param(
        description="Domain to query (e.g., google.com)",
        primary=True,
        cef_types=["domain", "url"],
        column_name="Domain",
    )


class CertificateDetails(ActionOutput):
    """Certificate information output"""

    # Basic Info
    certificate_found: bool = OutputField(
        cef_types=["certificate"],
        column_name="Certificate Found",
    )
    host: str = OutputField(cef_types=["domain", "host name"], column_name="Host")
    elapsed_ms: int | None = OutputField(
        column_name="Response Time (ms)",
    )

    # Certificate Status
    expired: bool | None = OutputField(
        column_name="Certificate Expired",
    )
    valid: bool | None = None
    valid_peer: bool | None = None
    name_match: bool | None = None
    blacklisted: bool | None = None
    revoked: bool | None = None

    # Certificate Metadata
    certificate_type: str | None = None
    fingerprint_sha1: str | None = None
    fingerprint_sha256: str | None = None
    deprecated_issuer: bool | None = None

    # Certificate Details Hash
    certificate_hash: str | None = None

    # Certificate Version
    certificate_version: str | None = None

    # Subject Details
    subject_name: str | None = None
    subject_common_name: str | None = None
    subject_alternative_names: str | None = None
    subject_organization: str | None = None
    subject_organization_unit: str | None = None
    subject_category: str | None = None
    subject_country: str | None = None
    subject_state: str | None = None
    subject_location: str | None = None
    subject_postal_code: str | None = None
    subject_street: str | None = None
    subject_serial_number: str | None = None
    subject_inc_country: str | None = None
    subject_inc_state: str | None = None

    # Issuer Details
    issuer_common_name: str | None = OutputField(
        column_name="Issuer Name",
    )
    issuer_organization: str | None = OutputField(
        column_name="Issuer Organization",
    )
    issuer_organization_unit: str | None = None
    issuer_country: str | None = None
    issuer_state: str | None = None
    issuer_location: str | None = None

    # Public Key
    public_key_algorithm: str | None = None
    public_key_size: int | None = None

    # Signature Details
    signature_serial: str | None = None
    signature_serial_hex: str | None = None
    signature_type: str | None = None

    # Validity Details
    valid_from: str | None = OutputField(
        column_name="Valid From",
    )
    valid_to: str | None = OutputField(
        column_name="Valid To",
    )
    valid_from_timestamp: int | None = None
    valid_to_timestamp: int | None = None
    days_left: int | None = None

    # Extensions (flattened from nested structure)
    extensions_authority_info_access: str | None = None
    extensions_authority_key_identifier: str | None = None
    extensions_subject_key_identifier: str | None = None
    extensions_basic_constraints: str | None = None
    extensions_certificate_policies: str | None = None
    extensions_crl_distribution_points: str | None = None
    extensions_key_usage: str | None = None
    extensions_extended_key_usage: str | None = None

    # Certificate Authority Info
    certificate_authority: bool | None = None
    authority_key_id: str | None = None
    subject_key_id: str | None = None

    # Key Usages (comma-separated)
    key_usages: str | None = None
    extended_key_usages: str | None = None
    crl_endpoints: str | None = None

    # Authority Info (formatted string from array)
    authority_info: str | None = None


class CertificateSummary(ActionOutput):
    """Summary for certificate info action"""

    certificate_found: bool = None
    domain: str = None

    def get_message(self) -> str:
        """Generate summary message following official SOAR SDK pattern"""
        return f"Received Certificate information for domain {self.domain}"


def get_cert_info(
    param: GetCertInfoParams,
    soar: SOARClient[CertificateSummary],
    asset: Asset,
) -> CertificateDetails:
    """Get certificate information for a domain."""
    logger.progress(MSG_QUERYING_CERT_INFO.format(param.domain))

    params = {"host": param.domain}
    data = _make_api_request(ENDPOINT_SSL_INFO, asset, params)

    cert = data.get(KEY_CERTIFICATE)
    if not cert:
        raise ActionFailure(ERROR_NO_CERT_DATA)

    cert_found = cert.get("found", False)
    details = cert.get("details", {})
    subject = details.get("subject", {})
    issuer = details.get("issuer", {})
    public_key = details.get("public_key", {})
    signature = details.get("signature", {})
    validity = details.get("validity", {})
    extensions = details.get("extensions", {})

    key_usages_str = (
        ", ".join(details.get("key_usages", [])) if details.get("key_usages") else None
    )
    extended_key_usages_str = (
        ", ".join(details.get("extended_key_usages", []))
        if details.get("extended_key_usages")
        else None
    )
    crl_endpoints_str = (
        ", ".join(details.get("crl_endpoints", []))
        if details.get("crl_endpoints")
        else None
    )

    subject_org_unit_str = (
        ", ".join(subject.get("organization_unit", []))
        if subject.get("organization_unit")
        else None
    )
    issuer_org_unit_str = (
        ", ".join(issuer.get("organization_unit", []))
        if issuer.get("organization_unit")
        else None
    )

    subject_street_str = (
        ", ".join(subject.get("street", [])) if subject.get("street") else None
    )

    authority_info_list = details.get("authority_info", [])
    authority_info_str = None
    if authority_info_list:
        authority_info_parts = [
            f"{item.get('method')}: {item.get('location')}"
            for item in authority_info_list
        ]
        authority_info_str = ", ".join(authority_info_parts)

    result = CertificateDetails(
        certificate_found=cert_found,
        host=data.get("host", param.domain),
        elapsed_ms=data.get("elapsed_ms"),
        expired=cert.get("expired"),
        valid=cert.get("valid"),
        valid_peer=cert.get("valid_peer"),
        name_match=cert.get("name_match"),
        blacklisted=cert.get("blacklisted"),
        revoked=cert.get("revoked"),
        certificate_type=cert.get("type"),
        fingerprint_sha1=cert.get("fingerprint_sha1"),
        fingerprint_sha256=cert.get("fingerprint_sha256"),
        deprecated_issuer=cert.get("deprecated_issuer"),
        certificate_hash=details.get("hash"),
        certificate_version=details.get("version"),
        subject_name=subject.get("name"),
        subject_common_name=subject.get("common_name"),
        subject_alternative_names=subject.get("alternative_names"),
        subject_organization=subject.get("organization"),
        subject_organization_unit=subject_org_unit_str,
        subject_category=subject.get("category"),
        subject_country=subject.get("country"),
        subject_state=subject.get("state"),
        subject_location=subject.get("location"),
        subject_postal_code=subject.get("postal_code"),
        subject_street=subject_street_str,
        subject_serial_number=subject.get("serial_number"),
        subject_inc_country=subject.get("inc_country"),
        subject_inc_state=subject.get("inc_state"),
        issuer_common_name=issuer.get("common_name"),
        issuer_organization=issuer.get("organization"),
        issuer_organization_unit=issuer_org_unit_str,
        issuer_country=issuer.get("country"),
        issuer_state=issuer.get("state"),
        issuer_location=issuer.get("location"),
        public_key_algorithm=public_key.get("algorithm"),
        public_key_size=public_key.get("size"),
        signature_serial=signature.get("serial"),
        signature_serial_hex=signature.get("serial_hex"),
        signature_type=signature.get("type"),
        valid_from=validity.get("valid_from"),
        valid_to=validity.get("valid_to"),
        valid_from_timestamp=validity.get("valid_from_timestamp"),
        valid_to_timestamp=validity.get("valid_to_timestamp"),
        days_left=validity.get("days_left"),
        extensions_authority_info_access=extensions.get("authority_info_access"),
        extensions_authority_key_identifier=extensions.get("authority_key_identifier"),
        extensions_subject_key_identifier=extensions.get("subject_key_identifier"),
        extensions_basic_constraints=extensions.get("basic_constraints"),
        extensions_certificate_policies=extensions.get("certificate_policies"),
        extensions_crl_distribution_points=extensions.get("crl_distribution_points"),
        extensions_key_usage=extensions.get("key_usage"),
        extensions_extended_key_usage=extensions.get("extended_key_usage"),
        certificate_authority=details.get("certificate_authority"),
        authority_key_id=details.get("authority_key_id"),
        subject_key_id=details.get("subject_key_id"),
        key_usages=key_usages_str,
        extended_key_usages=extended_key_usages_str,
        crl_endpoints=crl_endpoints_str,
        authority_info=authority_info_str,
    )

    summary = CertificateSummary(certificate_found=cert_found, domain=param.domain)
    soar.set_summary(summary)
    soar.set_message(summary.get_message())
    return result
