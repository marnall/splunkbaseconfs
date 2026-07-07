from __future__ import annotations

import os
import traceback
from glob import glob
from typing import Dict, List, Union, cast

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from typing_extensions import TypedDict

import maxminddb
from ipinfo.logging import get_logger
from ipinfo.utils import stringify_bools
from maxminddb.reader import Reader
from maxminddb.types import RecordDict
from splunklib.searchcommands.search_command import SearchCommand


logger = get_logger(__file__)


def get_mmdb_reader(
    self,
    asn: bool,
    company: bool,
    carrier: bool,
    privacy: bool,
    domains: bool,
    abuse: bool,
    country_asn: bool,
    resproxy: bool,
    resproxy_lookback: str,
):
    ext_label_iplocation_reader = open_mmdb(self, "iplocation_ext_labels")
    if ext_label_iplocation_reader == None:
        ext_iplocation_reader = open_mmdb(self, "iplocation_ext")
        if ext_iplocation_reader == None:
            iplocation_reader = open_mmdb(self, "iplocation")
        else:
            iplocation_reader = None
    else:
        ext_iplocation_reader = None
        iplocation_reader = None

    asn_reader = open_mmdb(self, "asn") if asn else None
    company_reader = open_mmdb(self, "company") if company else None
    carrier_reader = open_mmdb(self, "carrier") if carrier else None

    privacy_extended_reader = open_mmdb(self, "privacy_extended") if privacy else None
    legacy_ext_privacy_reader = None
    if privacy_extended_reader == None:
        legacy_ext_privacy_reader = open_mmdb(self, "privacy_ext") if privacy else None
    if privacy_extended_reader == None or legacy_ext_privacy_reader == None:
        privacy_reader = open_mmdb(self, "privacy") if privacy else None
    else:
        privacy_reader = None

    domains_reader = open_mmdb(self, "domains") if domains else None
    abuse_reader = open_mmdb(self, "abuse") if abuse else None
    country_asn_reader = open_mmdb(self, "country_asn") if country_asn else None
    resproxy_lookup_file = f"resproxy_{resproxy_lookback}d"
    resproxy_reader = open_mmdb(self, resproxy_lookup_file) if resproxy else None

    if ext_label_iplocation_reader is None and ext_iplocation_reader is None and iplocation_reader is None:
        logger.error(
            "No location file exist. Please ensure Ipinfo app is configured or if you have just configured the app, use Manual Refresh Dashboard or wait till next schedule run."
        )

    return (
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


def open_mmdb(self, lookupfile_name: str):
    try:
        ipinfo_searchpeer = [
            filename
            for filename in glob(
                splunk_lib_util.make_splunkhome_path(
                    [
                        "var",
                        "run",
                        "searchpeers",
                        "*",
                        "apps",
                        "ipinfo_app",
                        "lookups",
                        lookupfile_name + ".mmdb",
                    ]
                ),
                recursive=True,
            )
        ]
        mmdb_location = ""
        lookup_reader = None
        if len(ipinfo_searchpeer) > 0:
            mmdb_location = max(
                [
                    filename
                    for filename in glob(
                        splunk_lib_util.make_splunkhome_path(
                            [
                                "var",
                                "run",
                                "searchpeers",
                                "*",
                                "apps",
                                "ipinfo_app",
                                "lookups",
                                lookupfile_name + ".mmdb",
                            ]
                        ),
                        recursive=True,
                    )
                ],
                key=os.path.getmtime,
            )
        else:
            mmdb_location = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "lookups", lookupfile_name + ".mmdb"])
        if os.path.exists(mmdb_location):
            try:
                lookup_reader = maxminddb.open_database(mmdb_location)
            except Exception as e:
                self.write_warning("Error During Fetching Data from " + lookupfile_name + " MMDB Lookup. Check Log Dashboard")
                logger.error(e)
                logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        elif lookupfile_name not in ["iplocation_ext_labels", "iplocation_ext", "iplocation"]:
            logger.error(
                lookupfile_name
                + " file doesn't exist. Please ensure Ipinfo app is configured or if you have just configured the app, use Manual Refresh Dashboard or wait till next schedule run."
            )
        return lookup_reader
    except Exception as e:
        logger.error(e)
        logger.error("Error while reading file " + lookupfile_name)
        return lookup_reader


def get_ipinfo_mmdb_result(
    self,
    list_of_ips,
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
):
    response_result = {}
    mmdb_readers = {
        "ext_label_iplocation": ext_label_iplocation_reader,
        "ext_iplocation": ext_iplocation_reader,
        "iplocation": iplocation_reader,
        "asn": asn_reader,
        "carrier": carrier_reader,
        "company": company_reader,
        "legacy_ext_privacy_reader": legacy_ext_privacy_reader,
        "privacy": privacy_reader,
        "privacy_extended": privacy_extended_reader,
        "domains": domains_reader,
        "abuse": abuse_reader,
        "country_asn": country_asn_reader,
        "resproxy": resproxy_reader,
    }
    for reader_name, reader in mmdb_readers.items():
        if reader is not None:
            results = read_mmdb(self, reader_name, reader, list_of_ips)
            response_result = parse_mmdb_result(response_result, results)

    return response_result


def read_mmdb(self, reader_name: str, reader: Reader, list_of_ips: List[str]):
    if reader_name == "ext_label_iplocation":
        return read_extended_label_location_mmdb(self, reader, list_of_ips)
    elif reader_name == "ext_iplocation":
        return read_extended_location_mmdb(self, reader, list_of_ips)
    elif reader_name == "iplocation":
        return read_location_mmdb(self, reader, list_of_ips)
    elif reader_name == "asn":
        return read_asn_mmdb(self, reader, list_of_ips)
    elif reader_name == "carrier":
        return read_carrier_mmdb(self, reader, list_of_ips)
    elif reader_name == "company":
        return read_company_mmdb(self, reader, list_of_ips)
    elif reader_name == "legacy_ext_privacy_reader":
        return read_legacy_extended_privacy_mmdb(self, reader, list_of_ips)
    elif reader_name == "privacy":
        return read_privacy_mmdb(self, reader, list_of_ips)
    elif reader_name == "privacy_extended":
        return read_privacy_extended_mmdb(self, reader, list_of_ips)
    elif reader_name == "domains":
        return read_domains_mmdb(self, reader, list_of_ips)
    elif reader_name == "abuse":
        return read_abuse_mmdb(self, reader, list_of_ips)
    elif reader_name == "country_asn":
        return read_country_asn_mmdb(self, reader, list_of_ips)
    elif reader_name == "resproxy":
        return read_resproxy_mmdb(self, reader, list_of_ips)


def read_location_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "city": response.get("city", ""),
                "country": response.get("country", ""),
                "lat": response.get("lat", ""),
                "lon": response.get("lng", ""),
                "postal": response.get("postal_code", ""),
                "region": response.get("region", ""),
                "region_code": response.get("region_code", ""),
                "timezone": response.get("timezone", ""),
                "geoname_id": response.get("geoname_id", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from IP MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    return response_result


def read_extended_location_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "city": response.get("city", ""),
                "country": response.get("country", ""),
                "country_name": response.get("country_name", ""),
                "lat": response.get("latitude", ""),
                "lon": response.get("longitude", ""),
                "postal": response.get("postal_code", ""),
                "radius": response.get("radius", ""),
                "region": response.get("region_name", ""),
                "region_code": response.get("region", ""),
                "timezone": response.get("timezone", ""),
                "geoname_id": response.get("geoname_id", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from EXTENDED IP MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    return response_result


def read_extended_label_location_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "city": response.get("city", ""),
                "city_confidence": response.get("city_confidence", ""),
                "country": response.get("country", ""),
                "country_confidence": response.get("country_confidence", ""),
                "country_name": response.get("country_name", ""),
                "lat": response.get("latitude", ""),
                "lon": response.get("longitude", ""),
                "postal": response.get("postal_code", ""),
                "radius": response.get("radius", ""),
                "region": response.get("region_name", ""),
                "region_confidence": response.get("region_confidence", ""),
                "region_code": response.get("region", ""),
                "timezone": response.get("timezone", ""),
                "geoname_id": response.get("geoname_id", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from EXTENDED IP MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    return response_result


def read_asn_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "asn_asn": response.get("asn", ""),
                "asn_name": response.get("name", ""),
                "asn_domain": response.get("domain", ""),
                "asn_route": response.get("route", ""),
                "asn_type": response.get("type", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from ASN MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}
    return response_result


def read_carrier_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "carrier_name": response.get("carrier", ""),
                "carrier_mcc": response.get("mcc", ""),
                "carrier_mnc": response.get("mnc", ""),
                "carrier_cc": response.get("cc", ""),
                "carrier_network": response.get("network", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from CARRIER MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    return response_result


def read_company_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "company_name": response.get("name", ""),
                "company_domain": response.get("domain", ""),
                "company_type": response.get("type", ""),
                "asn": response.get("asn", ""),
                "asn_name": response.get("as_name", ""),
                "asn_domain": response.get("as_domain", ""),
                "asn_type": response.get("as_type", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from COMPANY MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    return response_result


def read_privacy_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "vpn": response.get("vpn", ""),
                "proxy": response.get("proxy", ""),
                "tor": response.get("tor", ""),
                "hosting": response.get("hosting", ""),
                "relay": response.get("relay", ""),
                "service": response.get("service", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from PRIVACY MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    return {ip: stringify_bools(row) for ip, row in response_result.items()}


class PrivacyExtendedRecord(TypedDict):
    """
    Type definition for privacy extended record data structure.

    Attributes:
        ip: IP address
        vpn: Whether the IP is associated with a VPN
        proxy: Whether the IP is associated with a proxy
        tor: Whether the IP is associated with Tor
        relay: Whether the IP is a relay
        hosting: Whether the IP is associated with hosting services
        service: Service name or identifier
        confidence: Confidence score for the privacy detection
        coverage: Coverage metric for the detection
        census: Whether the IP appears in census data
        census_ports: Comma-separated list of census ports
        device_activity: Whether device activity was detected
        inferred: Whether the data was inferred
        vpn_config: Whether VPN configuration was detected
        whois: Whether WHOIS data is available
        first_seen: First seen timestamp
        last_seen: Last seen timestamp
    """

    ip: str
    vpn: bool
    proxy: bool
    tor: bool
    relay: bool
    hosting: bool
    service: str
    confidence: int
    coverage: int
    census: bool
    census_ports: str
    device_activity: bool
    inferred: bool
    vpn_config: bool
    whois: bool
    first_seen: str
    last_seen: str


def read_privacy_extended_mmdb(command: SearchCommand, reader: Reader, ips: list[str]) -> dict[str, PrivacyExtendedRecord]:
    """
    Read privacy extended data from MMDB for given IP addresses.

    Args:
        command: Splunk search command instance for writing warnings
        reader: MMDB reader instance for privacy extended database
        ips: List of IP addresses to lookup

    Returns:
        Dictionary mapping IP addresses to their privacy extended data,
        or empty dict if error occurs
    """
    result: dict[str, PrivacyExtendedRecord] = {}
    try:
        for ip in ips:
            ip = ip.strip()
            response = cast(dict[str, Union[str, bool, int]], reader.get(ip) or {})
            result[ip] = {
                "ip": ip,
                "vpn": cast(bool, response.get("vpn", False)),
                "proxy": cast(bool, response.get("proxy", False)),
                "tor": cast(bool, response.get("tor", False)),
                "relay": cast(bool, response.get("relay", False)),
                "hosting": cast(bool, response.get("hosting", False)),
                "service": cast(str, response.get("service", "")),
                "confidence": cast(int, response.get("confidence", 0)),
                "coverage": cast(int, response.get("coverage", 0)),
                "census": cast(bool, response.get("census", False)),
                "census_ports": cast(str, response.get("census_ports", "")),
                "device_activity": cast(bool, response.get("device_activity", False)),
                "inferred": cast(bool, response.get("inferred", False)),
                "vpn_config": cast(bool, response.get("vpn_config", False)),
                "whois": cast(bool, response.get("whois", False)),
                "first_seen": cast(str, response.get("first_seen", "")),
                "last_seen": cast(str, response.get("last_seen", "")),
            }
    except Exception as exc:
        command.write_warning("Error During Fetching Data from PRIVACY_EXTENDED MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(exc)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}
    return {ip: stringify_bools(row) for ip, row in result.items()}


def read_legacy_extended_privacy_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "anycast": response.get("anycast", ""),
                "census": response.get("census", ""),
                "census_port": response.get("census_port", ""),
                "device_activity": response.get("device_activity", ""),
                "hosting": response.get("hosting", ""),
                "network": response.get("network", ""),
                "proxy": response.get("proxy", ""),
                "relay": response.get("relay", ""),
                "tor": response.get("tor", ""),
                "vpn": response.get("vpn", ""),
                "vpn_config": response.get("vpn_config", ""),
                "vpn_name": response.get("vpn_name", ""),
                "whois": response.get("whois", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from PRIVACY MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    return {ip: stringify_bools(row) for ip, row in response_result.items()}


def read_domains_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "domains": response.get("domains", "").split(",")[:5],
                "total_domains": response.get("total", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from DOMAINS MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}
    return response_result


def read_abuse_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "abuse_name": response.get("name", ""),
                "abuse_email": response.get("email", ""),
                "abuse_address": response.get("address", ""),
                "abuse_country": response.get("country", ""),
                "abuse_phone": response.get("phone", ""),
                "abuse_network": response.get("network", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from ABUSE MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}
    return response_result


def read_country_asn_mmdb(self, reader, list_of_ips):
    response_result = {}
    try:
        for ip in list_of_ips:
            ip = ip.strip()
            response = reader.get(ip) or {}
            response_result[ip] = {
                "ip": ip,
                "country_asn_domain": response.get("as_domain", ""),
                "country_asn_name": response.get("as_name", ""),
                "country_asn_asn": response.get("asn", ""),
                "country_continent": response.get("continent", ""),
                "country_continent_name": response.get("continent_name", ""),
                "country_country": response.get("country", ""),
                "country_country_name": response.get("country_name", ""),
            }
    except Exception as e:
        self.write_warning("Error During Fetching Data from COUNTRY_ASN MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}
    return response_result


class ResProxyRecord(TypedDict):
    """
    Type definition for residential proxy record data structure.

    Attributes:
        ip: IP address
        last_seen: Date when IP was last seen as residential proxy
        percent_days_seen: Percentage of days IP was seen as residential proxy
        service: Service provider name
    """

    ip: str
    resproxy_last_seen: str
    resproxy_percent_days_seen: Union[int, str]
    resproxy_service: str


def read_resproxy_mmdb(command: SearchCommand, reader: Reader, ips: list[str]) -> dict[str, ResProxyRecord]:
    """
    Read residential proxy data from MMDB for given IP addresses.

    Args:
        command: Splunk search command instance for writing warnings
        reader: MMDB reader instance for residential proxy database
        ips: List of IP addresses to lookup

    Returns:
        Dictionary mapping IP addresses to their residential proxy data,
        or empty dict if error occurs
    """
    result = {}
    try:
        for ip in ips:
            ip = ip.strip()
            # We're assuming this will be a dictionary
            response = cast(dict[str, str], reader.get(ip) or {})
            data = {
                "ip": ip,
                "resproxy_last_seen": response.get("last_seen", ""),
                "resproxy_percent_days_seen": response.get("percent_days_seen", ""),
                "resproxy_service": response.get("service", ""),
            }
            result[ip] = data
    except Exception as exc:
        command.write_warning("Error During Fetching Data from RESIDENTIAL_PROXY MMDB Lookup. Check Logs dashboard for troubleshooting.")
        logger.error(exc)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}
    return result


def parse_mmdb_result(response_result, result):
    for ip, value in result.items():
        if ip in response_result:
            temp = response_result[ip]
            temp.update(value)
            response_result[ip] = temp
        else:
            response_result[ip] = value
    return response_result
