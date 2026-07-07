from __future__ import annotations

import os
import sys
import traceback
from typing import Optional, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

from ipinfo.logging import get_logger
from ipinfo.utils import calculate_prefix, prefix_dict_keys
from ipinfo.validators import ListOrBoolean
from ipinfo_constants import (
    ABUSE_FIELDS,
    ASN_FIELDS,
    CARRIER_FIELDS,
    COMPANY_FIELDS,
    COUNTRY_ASN_FIELDS,
    DOMAINS_FIELDS,
    LEGACY_EXTENDED_PRIVACY_FIELDS,
    LOCATION_FIELDS,
    PRIVACY_EXTENDED_FIELDS,
    PRIVACY_FIELDS,
    RESPROXY_FIELDS,
    RESPROXY_LOOKBACK_DAYS,
)
from ipinfo_MMDB import get_ipinfo_mmdb_result, get_mmdb_reader
from ipinfo_RestAPI import get_ipinfo_rest_result
from ipinfo_utils import fillnull, get_config, mmdb_usage
from splunklib.searchcommands import Configuration, Option, StreamingCommand, dispatch, validators


logger = get_logger(__file__)
replication = get_config("replicate_lookup")
if replication == "Yes":
    replication = True
else:
    replication = False


# Custom ipinfo command
@Configuration(distributed=replication)
class IpinfoCommand(StreamingCommand):
    prefix = Option(require=False, default=False, validate=ListOrBoolean())
    restapi = Option(require=False, default=False, validate=validators.Boolean())
    privacy = Option(require=False, default=False, validate=validators.Boolean())
    asn = Option(require=False, default=False, validate=validators.Boolean())
    company = Option(require=False, default=False, validate=validators.Boolean())
    abuse = Option(require=False, default=False, validate=validators.Boolean())
    domains = Option(require=False, default=False, validate=validators.Boolean())
    carrier = Option(require=False, default=False, validate=validators.Boolean())
    country_asn = Option(require=False, default=False, validate=validators.Boolean())
    resproxy = Option(require=False, default=False, validate=validators.Boolean())
    resproxy_lookback = Option(require=False, default="30", validate=validators.Set(*RESPROXY_LOOKBACK_DAYS))
    alltypes = Option(require=False, default=False, validate=validators.Boolean())

    def stream(self, records):
        session_key = self.service.token
        record_list = {}
        fields: list[str] = self.fieldnames or []

        # Available Flags
        prefix = self.prefix
        restapi = self.restapi
        privacy = self.privacy
        asn = self.asn
        company = self.company
        abuse = self.abuse
        domains = self.domains
        carrier = self.carrier
        country_asn = self.country_asn
        resproxy = self.resproxy
        resproxy_lookback = self.resproxy_lookback
        alltypes = self.alltypes

        logger.debug(
            "IpinfoCommand started with options: restapi=%s, privacy=%s, "
            "asn=%s, company=%s, abuse=%s, domains=%s, carrier=%s, "
            "country_asn=%s, resproxy=%s, alltypes=%s",
            restapi,
            privacy,
            asn,
            company,
            abuse,
            domains,
            carrier,
            country_asn,
            resproxy,
            alltypes,
        )

        if alltypes:
            logger.debug("alltypes enabled, setting all flags to True")
            asn = True
            company = True
            abuse = True
            domains = True
            carrier = True
            privacy = True
            country_asn = True
            resproxy = True

        method = get_config("method")
        if method == "MMDB" and restapi:
            logger.info("MMDB method forced to RESTAPI due to restapi flag")
            method = "RESTAPI"

        logger.debug("Using method: %s", method)

        prefix = calculate_prefix(prefix, fields)
        logger.debug("Fields to process: %s", fields)

        try:
            if method == "MMDB":
                logger.debug("Initializing MMDB readers")
                (
                    ext_label_iplocation_reader,
                    ext_iplocation_reader,
                    iplocation_reader,
                    asn_reader,
                    company_reader,
                    carrier_reader,
                    legacy_ext_privacy_reader,
                    privacy_reader,
                    privacy_extended_reader,
                    domains_reader,
                    abuse_reader,
                    country_asn_reader,
                    resproxy_reader,
                ) = get_mmdb_reader(self, asn, company, carrier, privacy, domains, abuse, country_asn, resproxy, resproxy_lookback)

                first_record = True
                total_ips = 0
                for record in records:
                    if first_record:
                        # The fields set in the first record determines the header of the table that we're going
                        # to show.
                        # So to make sure that all the necessary fields for the MMDBs that we're querying are present
                        # we fill them with an empty string. This way if the first record, by any chance, doesn't
                        # return any data we still show the columns for later ones.
                        #
                        # This behaviour is not explicitly documented by Splunk.
                        logger.debug("Filling first record with default fields")
                        include_location = (
                            ext_label_iplocation_reader is not None or ext_iplocation_reader is not None or iplocation_reader is not None
                        )
                        self._fill_record_fields(record, fields, prefix, include_location)
                        first_record = False

                    ip_addresses = []
                    for f in fields:
                        v = record.get(f)
                        if v and v.strip():
                            ip_addresses.append(v.strip())
                    if bool(ip_addresses):
                        logger.debug("Processing %d IP addresses", len(ip_addresses))
                        total_ips += len(ip_addresses)
                        list_of_ip_details = get_ipinfo_mmdb_result(
                            self,
                            ip_addresses,
                            ext_label_iplocation_reader,
                            ext_iplocation_reader,
                            iplocation_reader,
                            asn_reader,
                            company_reader,
                            carrier_reader,
                            legacy_ext_privacy_reader,
                            privacy_reader,
                            privacy_extended_reader,
                            domains_reader,
                            abuse_reader,
                            country_asn_reader,
                            resproxy_reader,
                        )
                        ip_addresses = []
                        if bool(list_of_ip_details):
                            try:
                                for field in fields:
                                    if record.get(field):
                                        details = list_of_ip_details.get(record.get(field))
                                        if details is not None:
                                            if prefix:
                                                details = prefix_dict_keys(
                                                    details,
                                                    prefix[field],
                                                )
                                            record.update(details)
                            except Exception as e:
                                logger.error(
                                    "Error updating record with IP details: %s",
                                    e,
                                )
                                logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
                        else:
                            logger.warning("No IP details returned from MMDB lookup")
                            self.write_warning("Some Error Occured. Check Logs dashboard for troubleshooting.")
                    yield record

                logger.info(
                    "MMDB processing complete, total IPs processed: %d",
                    total_ips,
                )
                mmdb_usage(
                    ext_label_iplocation_reader,
                    ext_iplocation_reader,
                    iplocation_reader,
                    asn_reader,
                    company_reader,
                    carrier_reader,
                    legacy_ext_privacy_reader,
                    privacy_reader,
                    privacy_extended_reader,
                    domains_reader,
                    abuse_reader,
                    country_asn_reader,
                    resproxy_reader,
                    resproxy_lookback,
                    asn,
                    carrier,
                    company,
                    privacy,
                    domains,
                    abuse,
                    country_asn,
                    resproxy,
                    total_ips,
                    session_key,
                )
            elif method == "RESTAPI":
                logger.debug("Processing records via RESTAPI")
                count = 0
                ip_addresses = []
                first_record = True
                for record in records:
                    if first_record:
                        # The fields set in the first record determines the header of the table that we're going
                        # to show.
                        # So to make sure that all the necessary fields for the MMDBs that we're querying are present
                        # we fill them with an empty string. This way if the first record, by any chance, doesn't
                        # return any data we still show the columns for later ones.
                        #
                        # This behaviour is not explicitly documented by Splunk.
                        logger.debug("Filling first record with default fields")
                        self._fill_record_fields(record, fields, prefix, include_location=True)
                        first_record = False

                    new_counter = 0
                    for field in fields:
                        if record.get(field):
                            ip_value = record.get(field).strip()
                            if ip_value != "":
                                new_counter += 1
                                ip_addresses.append(ip_value)
                                count += 1
                    if new_counter >= 1:
                        record_list[str(count)] = record
                    if count >= 1000:
                        logger.debug("Batch limit reached, submitting %d IPs", count)
                        count = 0
                        yield from get_ipinfo_rest_result(
                            self,
                            ip_addresses,
                            record_list,
                            fields,
                            asn,
                            abuse,
                            company,
                            carrier,
                            privacy,
                            domains,
                            resproxy,
                            prefix,
                        )
                        ip_addresses = []
                        record_list = {}
                if count < 1000:
                    logger.debug("Final batch submission with %d IPs", count)
                    yield from get_ipinfo_rest_result(
                        self, ip_addresses, record_list, fields, asn, abuse, company, carrier, privacy, domains, resproxy, prefix
                    )

        except Exception as e:
            logger.error("Fatal error in stream processing: %s", e)
            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))

    def _fill_record_fields(
        self, record: OrderedDict[str, str], fields: list[str], prefix: Optional[dict[str, str]], include_location: bool = False
    ):
        to_add = {}
        if include_location:
            to_add.update(LOCATION_FIELDS)
        if self.asn or self.alltypes:
            to_add.update(ASN_FIELDS)
        if self.company or self.alltypes:
            to_add.update(COMPANY_FIELDS)
        if self.abuse or self.alltypes:
            to_add.update(ABUSE_FIELDS)
        if self.domains or self.alltypes:
            to_add.update(DOMAINS_FIELDS)
        if self.carrier or self.alltypes:
            to_add.update(CARRIER_FIELDS)
        if self.privacy or self.alltypes:
            to_add.update(PRIVACY_FIELDS)
            to_add.update(PRIVACY_EXTENDED_FIELDS)
            to_add.update(LEGACY_EXTENDED_PRIVACY_FIELDS)
        if self.country_asn or self.alltypes:
            to_add.update(COUNTRY_ASN_FIELDS)
        if self.resproxy or self.alltypes:
            to_add.update(RESPROXY_FIELDS)

        logger.debug("Filling record fields with %d default fields", len(to_add))

        if prefix:
            for field in fields:
                field_prefix = prefix[field] if prefix else ""
                record.update(prefix_dict_keys(to_add, field_prefix))
        else:
            record.update(to_add)


if __name__ == "__main__":
    dispatch(IpinfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
