from datetime import datetime
import logging
from stairwell import Stairwell
from stairwelllib.client import StairwellAPI
import stairwelllib.stairwellapi
from stairwelllib.stairwell_appapi_client import *

logger = logging.getLogger("splunk.stairwell.test")


def get_test_opinion() -> Opinion:
    return Opinion(
        verdict="MALICIOUS",
        email="john.malware@escalator.corp",
        create_time=datetime.fromisocalendar(2025, 2, 2),
        environment="OPINION_ENV_ID",
    )


def get_test_comment() -> Comment:
    return Comment(
        body="Very very bad!",
        email="john.malware@escalator.corp",
        create_time=datetime.fromisocalendar(2025, 3, 3),
        environment="COMMENT_ENV_ID",
    )


class FakeStairwellClient(StairwellAPI):

    hash_data: dict[str, ObjectEventEnrichment] = {}
    hostname_data: dict[str, HostnameEventEnrichment] = {}
    ip_data: dict[str, IPEventEnrichment] = {}

    def get_object_event_enrichment(self, hash: str) -> ObjectEventEnrichment:
        res = self.hash_data.get(hash)
        if res == None:
            return ObjectEventEnrichment()
        return res

    def get_hostname_event_enrichment(self, hostname: str) -> HostnameEventEnrichment:
        res = self.hostname_data.get(hostname)
        if res == None:
            return HostnameEventEnrichment()
        return res

    def get_ip_event_enrichment(self, ip: str) -> IPEventEnrichment:
        res = self.ip_data.get(ip)
        if res == None:
            return IPEventEnrichment()
        return res


def test_search_stairwell_object_api():
    fake_client = FakeStairwellClient()
    fake_client.hash_data["sha256"] = ObjectEventEnrichment(
        opinions_most_recent=[get_test_opinion()],
        comments_most_recent=[get_test_comment()],
        file_size=10,
        file_entropy=6,
        file_hash_sha256="sha256",
        file_hash_sha1="sha1",
        file_hash_md5="md5",
        file_hash_imphash="imphash",
        file_hash_sorted_imphash="ahhimps",
        file_hash_tlsh="tlsh",
        file_magic="exe",
        file_mime_type="exe",
        signature=ObjectSignature(
            x509_certificates=[
                X509Certificate(
                    signature="sig",
                    issuer="some_issuer",
                    subject="the_subject",
                    earliest_valid_time=datetime.fromisocalendar(2025, 1, 1),
                    latest_valid_time=datetime.fromisocalendar(2025, 2, 2),
                ),
            ],
            pkcs7_verification_result="VALID",
        ),
        sightings_first=datetime.fromisocalendar(2025, 1, 1),
        sightings_prevalence=[
            Prevalence(
                asset_count=2, prevalence=0.1, environment_id="PREVALENCE_ENV_ID"
            )
        ],
        verdict_is_well_known=True,
        verdict_maleval_malicious_probability="MALICIOUS_PROBABILITY_LOW",
        verdict_maleval_labels=["label_a", "label_b"],
        verdict_yara_rule_matches=["rule_a", "rule_b"],
        indicators_ips_likely=["1.1.1.1", "2.2.2.2"],
        indicators_hostnames_likely=["downloadmoreram.com"],
        indicators_hostnames_private=["downloadmorecpu.com"],
        variants=["sha256otherhash"],
        summary_ai="blah blah blah 1",
        summary_rtg="blah blah blah 2",
    )

    command = Stairwell(client=fake_client, custom_logger=logger)
    res = stairwelllib.stairwellapi.search_stairwell_object_api(
        command.client, logger, "sha256"
    )

    assert res == {
        "stairwell_event_type": "object",
        "stairwell_resource_id": "sha256",
        "stairwell_resource_type": "object",
        "stairwell_object_size": 10,
        "stairwell_object_entropy": 6,
        "stairwell_object_sha256": "sha256",
        "stairwell_object_sha1": "sha1",
        "stairwell_object_md5": "md5",
        "stairwell_object_imp_hash": "imphash",
        "stairwell_object_sorted_imp_hash": "ahhimps",
        "stairwell_object_tlsh": "tlsh",
        "stairwell_object_magic": "exe",
        "stairwell_object_mime_type": "exe",
        "stairwell_object_signature": {
            "x509Certificates": [
                {
                    "signature": "sig",
                    "issuer": "some_issuer",
                    "subject": "the_subject",
                    "earliestValidTime": datetime.fromisocalendar(
                        2025, 1, 1
                    ).isoformat(),
                    "latestValidTime": datetime.fromisocalendar(2025, 2, 2).isoformat(),
                }
            ],
            "pkcs7VerificationResult": "VALID",
        },
        "stairwell_object_first_seen_time": datetime.fromisocalendar(
            2025, 1, 1
        ).isoformat(),
        "stairwell_object_prevalence": [
            {
                "assetCount": 2,
                "prevalence": 0.1,
                "environmentId": "PREVALENCE_ENV_ID",
            }
        ],
        "stairwell_object_is_well_known": True,
        "stairwell_object_mal_eval_probability": "MALICIOUS_PROBABILITY_LOW",
        "stairwell_object_mal_eval": ["label_a", "label_b"],
        "stairwell_object_yara_rule_matches": ["rule_a", "rule_b"],
        "stairwell_object_network_indicators_ip_addresses": ["1.1.1.1", "2.2.2.2"],
        "stairwell_object_network_indicators_hostnames": ["downloadmoreram.com"],
        "stairwell_object_network_indicators_hostnames_private": [
            "downloadmorecpu.com"
        ],
        "stairwell_object_variants": [
            "sha256otherhash",
        ],
        "stairwell_ai_assessment": "blah blah blah 1",
        "stairwell_object_run_to_ground": "blah blah blah 2",
        "stairwell_opinions_most_recent": [
            {
                "verdict": "MALICIOUS",
                "environment": "OPINION_ENV_ID",
            },
        ],
        "stairwell_comments_most_recent": [
            {
                "body": "Very very bad!",
                "environment": "COMMENT_ENV_ID",
            },
        ],
    }


def test_search_stairwell_hostname_api():
    fake_client = FakeStairwellClient()
    fake_client.hostname_data["downloadmoreram.com"] = HostnameEventEnrichment(
        opinions_most_recent=[get_test_opinion()],
        comments_most_recent=[get_test_comment()],
        lookup_a_records=[
            DNSLookupResult(
                state="NOERROR",
                address="10.100.100.100",
                lookup_time=datetime.fromisocalendar(2025, 1, 1),
            )
        ],
        lookup_aaaa_records=[
            DNSLookupResult(
                state="NOERROR",
                address="1000:f0b0:1000:c00::00",
                lookup_time=datetime.fromisocalendar(2025, 1, 1),
            )
        ],
        lookup_mx_records=[
            DNSLookupResult(
                state="NOERROR",
                address=".com.downloadmoreram.smtp",
                lookup_time=datetime.fromisocalendar(2025, 1, 1),
            )
        ],
    )

    command = Stairwell(client=fake_client, custom_logger=logger)
    res = stairwelllib.stairwellapi.search_stairwell_hostname_api(
        command.client, logger, "downloadmoreram.com"
    )

    assert res == {
        "stairwell_event_type": "hostname",
        "stairwell_resource_id": "downloadmoreram.com",
        "stairwell_resource_type": "hostname",
        "stairwell_hostname": "downloadmoreram.com",
        "stairwell_opinions_most_recent": [
            {
                "verdict": "MALICIOUS",
                "environment": "OPINION_ENV_ID",
            },
        ],
        "stairwell_comments_most_recent": [
            {
                "body": "Very very bad!",
                "environment": "COMMENT_ENV_ID",
            },
        ],
        "stairwell_hostname_a_records": [
            {
                "address": "10.100.100.100",
                "lookupTime": datetime.fromisocalendar(2025, 1, 1).isoformat(),
            },
        ],
        "stairwell_hostname_aaaa_records": [
            {
                "address": "1000:f0b0:1000:c00::00",
                "lookupTime": datetime.fromisocalendar(2025, 1, 1).isoformat(),
            },
        ],
        "stairwell_hostname_mx_records": [
            {
                "address": ".com.downloadmoreram.smtp",
                "lookupTime": datetime.fromisocalendar(2025, 1, 1).isoformat(),
            },
        ],
    }


def test_search_stairwell_ip_addresses_api():
    fake_client = FakeStairwellClient()
    fake_client.ip_data["1.1.1.1"] = IPEventEnrichment(
        opinions_most_recent=[get_test_opinion()],
        comments_most_recent=[get_test_comment()],
        uninteresting_addr=True,
    )

    command = Stairwell(client=fake_client, custom_logger=logger)
    res = stairwelllib.stairwellapi.search_stairwell_ip_addresses_api(
        command.client, logger, "1.1.1.1"
    )

    assert res == {
        "stairwell_event_type": "ipaddress",
        "stairwell_resource_id": "1.1.1.1",
        "stairwell_resource_type": "ipaddress",
        "stairwell_opinions_most_recent": [
            {
                "verdict": "MALICIOUS",
                "environment": "OPINION_ENV_ID",
            },
        ],
        "stairwell_comments_most_recent": [
            {
                "body": "Very very bad!",
                "environment": "COMMENT_ENV_ID",
            },
        ],
        "stairwell_uninteresting_addr": True,
    }


class ExceptionalStairwellClient(StairwellAPI):
    def get_object_event_enrichment(self, _hash: str) -> ObjectEventEnrichment:
        raise ApiException(status=500, reason="we messed up big time")

    def get_hostname_event_enrichment(self, _hostname: str) -> HostnameEventEnrichment:
        raise ApiException(status=400, reason="that's not a hostname buddy")

    def get_ip_event_enrichment(self, _ip: str) -> IPEventEnrichment:
        raise ApiException(status=301, reason="not here pal")


def test_stairwell_api_exceptions():
    logger = logging.getLogger("splunk.stairwell.test")
    client = ExceptionalStairwellClient()

    res = stairwelllib.stairwellapi.search_stairwell_object_api(client, logger, "blah")
    assert res.get("stairwell_status") == "500"
    assert res.get("stairwell_error") != None

    res = stairwelllib.stairwellapi.search_stairwell_hostname_api(
        client, logger, "blah"
    )
    assert res.get("stairwell_status") == "400"
    assert res.get("stairwell_error") != None

    res = stairwelllib.stairwellapi.search_stairwell_ip_addresses_api(
        client, logger, "blah"
    )
    assert res.get("stairwell_status") == "301"
    assert res.get("stairwell_error") != None
