# This is the list of known and supported MMDB files from the app.
# We keep track of them here so that we can delete unknown files
# from the lookup folder without deleting these.
LIST_OF_FILES_TO_EXCLUDE = [
    "ipinfo_lite.mmdb",
    "ipinfo_core.mmdb",
    "ipinfo_plus.mmdb",
    "asn.mmdb",
    "carrier.mmdb",
    "company.mmdb",
    "iplocation.mmdb",
    "privacy.mmdb",
    "privacy_extended.mmdb",
    "domains.mmdb",
    "abuse.mmdb",
    "iplocation_ext.mmdb",
    "privacy_ext.mmdb",
    "country_asn.mmdb",
    "iplocation_ext_labels.mmdb",
    "resproxy_30d.mmdb",
    "resproxy_7d.mmdb",
]

RESPROXY_LOOKBACK_DAYS = ["7", "30"]

# The MMDB file names that the Splunk expects are different from the
# actual name of the files as we store them.
# This dictionary maps the name of the file as saved locally to its
# download URL.
# I'm not sure what led to this choice but it seems useful as we
# can change the download URL without having to change the name of the file.
FILE_NAME_URLS_MAPPING = {
    "ipinfo_lite": "https://ipinfo.io/data/ipinfo_lite.mmdb",
    "ipinfo_core": "https://ipinfo.io/data/ipinfo_core.mmdb",
    "ipinfo_plus": "https://ipinfo.io/data/ipinfo_plus.mmdb",
    "company": "https://ipinfo.io/data/standard_company.mmdb",
    "asn": "https://ipinfo.io/data/asn.mmdb",
    "carrier": "https://ipinfo.io/data/carrier.mmdb",
    "iplocation": "https://ipinfo.io/data/standard_location.mmdb",
    "privacy": "https://ipinfo.io/data/standard_privacy.mmdb",
    "privacy_extended": "https://ipinfo.io/data/ipinfo_privacy_extended.mmdb",
    "domains": "https://ipinfo.io/data/standard_ip_hosted_domains.mmdb",
    "abuse": "https://ipinfo.io/data/standard_abuse.mmdb",
    "iplocation_ext": "https://ipinfo.io/data/location_extended_v2.mmdb",
    "iplocation_ext_labels": "https://ipinfo.io/data/location_extended_v2_conf_labels.mmdb",
    "privacy_ext": "https://ipinfo.io/data/privacy_extended.mmdb",
    "country_asn": "https://ipinfo.io/data/free/country_asn.mmdb",
    "resproxy_30d": "https://ipinfo.io/data/resproxy_30d.mmdb",
    "resproxy_7d": "https://ipinfo.io/data/resproxy_7d.mmdb",
}

# These are all the fields from each MMDB that we support.
# We store them here to make it easier to update the first record
# when running a command.
# The fields in the first record define the header of the search
# table and all the following records.
LOCATION_FIELDS = {
    "city": "",
    "country": "",
    "lat": "",
    "lon": "",
    "postal": "",
    "region": "",
    "region_code": "",
    "timezone": "",
    "geoname_id": "",
}
EXTENDED_LOCATION_FIELDS = {
    "city": "",
    "country": "",
    "country_name": "",
    "lat": "",
    "lon": "",
    "postal": "",
    "radius": "",
    "region": "",
    "region_code": "",
    "timezone": "",
    "geoname_id": "",
}
EXTENDED_LABEL_LOCATION_FIELDS = {
    "city": "",
    "city_confidence": "",
    "country": "",
    "country_confidence": "",
    "country_name": "",
    "lat": "",
    "lon": "",
    "postal": "",
    "radius": "",
    "region": "",
    "region_confidence": "",
    "region_code": "",
    "timezone": "",
    "geoname_id": "",
}
ASN_FIELDS = {"asn_asn": "", "asn_name": "", "asn_domain": "", "asn_route": "", "asn_type": ""}
CARRIER_FIELDS = {"carrier_name": "", "carrier_mcc": "", "carrier_mnc": "", "carrier_cc": "", "carrier_network": ""}
COMPANY_FIELDS = {
    "company_name": "",
    "company_domain": "",
    "company_type": "",
    "asn": "",
    "asn_name": "",
    "asn_domain": "",
    "asn_type": "",
}
PRIVACY_FIELDS = {"vpn": "", "proxy": "", "tor": "", "hosting": "", "relay": "", "service": ""}
PRIVACY_EXTENDED_FIELDS = {
    "vpn": "",
    "proxy": "",
    "tor": "",
    "relay": "",
    "hosting": "",
    "service": "",
    "confidence": "",
    "coverage": "",
    "census": "",
    "census_ports": "",
    "device_activity": "",
    "inferred": "",
    "vpn_config": "",
    "whois": "",
    "first_seen": "",
    "last_seen": "",
}
LEGACY_EXTENDED_PRIVACY_FIELDS = {
    "anycast": "",
    "census": "",
    "census_port": "",
    "device_activity": "",
    "hosting": "",
    "network": "",
    "proxy": "",
    "relay": "",
    "tor": "",
    "vpn": "",
    "vpn_config": "",
    "vpn_name": "",
    "whois": "",
}
DOMAINS_FIELDS = {"domains": "", "total_domains": ""}
ABUSE_FIELDS = {
    "abuse_name": "",
    "abuse_email": "",
    "abuse_address": "",
    "abuse_country": "",
    "abuse_phone": "",
    "abuse_network": "",
}
COUNTRY_ASN_FIELDS = {
    "country_asn_domain": "",
    "country_asn_name": "",
    "country_asn_asn": "",
    "country_continent": "",
    "country_continent_name": "",
    "country_country": "",
    "country_country_name": "",
}
RESPROXY_FIELDS = {
    "resproxy_last_seen": "",
    "resproxy_percent_days_seen": "",
    "resproxy_service": "",
}
