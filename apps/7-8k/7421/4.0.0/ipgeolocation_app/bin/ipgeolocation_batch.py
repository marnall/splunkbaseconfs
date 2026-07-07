#!/usr/bin/env python
# Splunk specific dependencies
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators
)

# Command specific dependencies
import json

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from app_utils import get_logger
from app_utils import get_config
from app_utils import get_mmdb_lookup_reader
from lookup_mmdb import read_geolocation_mmdb
from lookup_mmdb import read_security_mmdb
from lookup_mmdb import merge_mmdb_responses
from api_request import query_ipgeolocation_api
from parse_api_response import fill_null_ip_geolocations_for_api
from parse_api_response import parse_ipgeolocation_api_response


logger = get_logger("ipgeolocation_batch")

method = get_config("method")
api_subscription_plan = get_config("api_subscription_plan")
db_std_ip_country_enabled = get_config("db_std_ip_country_enable") == "Yes"
db_std_ip_city_enabled = get_config("db_std_ip_city_enable") == "Yes"
db_std_ip_isp_enabled = get_config("db_std_ip_isp_enable") == "Yes"
db_std_ip_city_isp_enabled = get_config("db_std_ip_city_isp_enable") == "Yes"
db_advanced_ip_city_enabled = get_config("db_advanced_ip_city_enable") == "Yes"
db_advanced_ip_abuse_enabled = get_config("db_advanced_ip_abuse_enable") == "Yes"
db_advanced_ip_asn_enabled = get_config("db_advanced_ip_asn_enable") == "Yes"
db_advanced_ip_asn_ext_enabled = get_config("db_advanced_ip_asn_ext_enable") == "Yes"
db_advanced_ip_company_enabled = get_config("db_advanced_ip_company_enable") == "Yes"
db_advanced_ip_whois_enabled = get_config("db_advanced_ip_whois_enable") == "Yes"
db_advanced_ip_city_company_asn_enabled = get_config("db_advanced_ip_city_company_asn_enable") == "Yes"
db_advanced_ip_city_company_asn_abuse_enabled = get_config("db_advanced_ip_city_company_asn_abuse_enable") == "Yes"
db_advanced_ip_company_asn_enabled = get_config("db_advanced_ip_company_asn_enable") == "Yes"
db_advanced_ip_city_company_asn_abuse_security_enabled = get_config("db_advanced_ip_city_company_asn_abuse_security_enable") == "Yes"
db_sec_pro_ip_security_enabled = get_config("db_sec_pro_ip_security_enable") == "Yes"
db_sec_pro_ip_residential_proxy_enabled = get_config("db_sec_pro_ip_residential_proxy_enable") == "Yes"
db_sec_pro_ip_hosting_enabled = get_config("db_sec_pro_ip_hosting_enable") == "Yes"
db_sec_pro_ip_city_security_enabled = get_config("db_sec_pro_ip_city_security_enable") == "Yes"
db_sec_pro_ip_city_isp_security_enabled = get_config("db_sec_pro_ip_city_isp_security_enable") == "Yes"


@Configuration(type="reporting")
class IPGeolocationBatch(GeneratingCommand):
    ips = Option(doc='''
                     **Syntax:** **ips=***ip1,ip2,ip3,..,ipn*
                     **Description:** Comma-separated list of IP addresses to search IP information for.''',
                 require=True)
    liveHostname = Option(
        doc='''
            **Syntax:** **liveHostname=***<true|false>*
            **Description:** Lookup live hostname for the IP address. Supported on lookup from ipgeolocation.io API only.''',
        default=False, require=False, validate=validators.Boolean())
    hostnameFallbackLive = Option(
        doc='''
            **Syntax:** **hostnameFallbackLive=***<true|false>*
            **Description:** Lookup hostname for the IP address from database and fallback to live lookup if not in the database. Supported on lookup from ipgeolocation.io API only.''',
        default=False, require=False, validate=validators.Boolean())
    abuseContact = Option(
        doc='''
            **Syntax:** **abuseContact=***<true|false>*
            **Description:** Lookup abuse contact details for an IP address.''',
        default=False, require=False, validate=validators.Boolean())
    dma = Option(
        doc='''
            **Syntax:** **dma=***<true|false>*
            **Description:** Lookup DMA (Designated Market Area) Code for the location of IP address.''',
        default=False, require=False, validate=validators.Boolean())
    security = Option(
        doc='''
            **Syntax:** **security=***<true|false>*
            **Description:** Lookup security information for an IP address.''',
        default=False, require=False, validate=validators.Boolean())
    language = Option(
        doc='''
        **Syntax:** **language=***<en|de|ru|ja|fr|cn|es|cs|it|ko|fa|pt>*
        **Description:** Set the response language for search results. Default response language is 'en'.''',
        default="en", require=False)
    geoAccuracy = Option(
        doc='''
        **Syntax:** **geoAccuracy=***<true|false>*
        **Description:** Lookup geo accuracy for the location of IP Address. It includes locality, accuracy_radius and confidence level in the response. Supported on PAID API only.''',
        default=False, require=False, validate=validators.Boolean())
    allinfo = Option(
        doc='''
            **Syntax:** **allinfo=***<true|false>*
            **Description:** Lookup abuse contact, DMA (Designated Market Area) code, IP-Security and time zone details for the provided IP address.''',
        default=False, require=False, validate=validators.Boolean())

    def generate(self):
        ip_address_list = list(self.ips.split(","))
        lookup_live_hostname = self.liveHostname
        lookup_hostname_fallback_live = self.hostnameFallbackLive
        lookup_dma = self.dma
        lookup_abuse_contact = self.abuseContact
        lookup_security = self.security
        lookup_geo_accuracy = self.geoAccuracy
        language = self.language
        lookup_allinfo = self.allinfo

        if lookup_allinfo:
            lookup_live_hostname = True
            lookup_hostname_fallback_live = False
            lookup_dma = True
            lookup_abuse_contact = True
            lookup_security = True
            lookup_geo_accuracy = True

        ip_geolocations = dict()

        if method == "MMDB":
            geolocation_log_path, security_log_path = get_mmdb_readers(self)

            ip_geolocations = lookup_ip_addresses_from_mmdb(
                self,
               ip_address_list,
               geolocation_log_path,
               security_log_path,
               language,
               lookup_dma,
               lookup_geo_accuracy,
               lookup_abuse_contact,
               lookup_security
            )
        else:
            try:
                if api_subscription_plan == "FREE" or api_subscription_plan == "PAID":
                    api_lookup_response = query_ipgeolocation_api(
                        self,
                        splunk_lib_util,
                        ip_address_list,
                        lookup_live_hostname,
                        lookup_hostname_fallback_live,
                        lookup_dma,
                        lookup_security,
                        lookup_abuse_contact,
                        lookup_geo_accuracy,
                        language
                    )

                    if api_lookup_response is None:
                        self.write_warning("Got no response from ipgeolocation.io API")
                        logger.error("Got none response from query_ipgeolocation_api")
                        ip_geolocations = fill_null_ip_geolocations_for_api(
                            ip_address_list,
                            lookup_live_hostname,
                            lookup_hostname_fallback_live,
                            lookup_dma,
                            lookup_security,
                            lookup_abuse_contact,
                            lookup_geo_accuracy
                        )
                    else:
                        ip_geolocations = parse_ipgeolocation_api_response(
                            api_lookup_response,
                            lookup_live_hostname,
                            lookup_hostname_fallback_live,
                            lookup_dma,
                            lookup_security,
                            lookup_abuse_contact,
                            lookup_geo_accuracy
                        )
                else:
                    self.write_warning(
                        "Your subscription plan must be 'FREE' or 'PAID' to search IP geolocation using `ipgeolocationbatch` command.")
            except Exception as e:
                self.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
                self.write_warning(str(e))
                logger.error(e)
                logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

        for keys, values in ip_geolocations.items():
            yield values

    def parseHeaders(self, headers):
        # Replace single quotes with double quotes for valid json
        return json.loads(headers.replace("'", '"'))

    def parseData(self, data):
        data = '["' + data + '"]'
        return data.replace(",", '","')


def get_mmdb_readers(object):
    geolocation_mmdb_reader = None
    security_mmdb_reader = None

    if db_std_ip_country_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-country")
    if db_std_ip_city_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-location")
    if db_std_ip_isp_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-isp")
    if db_std_ip_city_isp_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-city-isp")
    if db_advanced_ip_city_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-location")
    if db_advanced_ip_abuse_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-abuse")
    if db_advanced_ip_asn_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-asn")
    if db_advanced_ip_asn_ext_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-asn")
    if db_advanced_ip_company_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-company")
    if db_advanced_ip_whois_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-whois")
    if db_advanced_ip_city_company_asn_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-city-company-asn")
    if db_advanced_ip_city_company_asn_abuse_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-city-company-asn-abuse")
    if db_advanced_ip_company_asn_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-company-asn")
    if db_advanced_ip_city_company_asn_abuse_security_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-city-company-asn-abuse")
        security_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-security")
    if db_sec_pro_ip_security_enabled:
        security_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-security")
    if db_sec_pro_ip_residential_proxy_enabled:
        security_mmdb_reader = get_mmdb_lookup_reader(object, "db-residential-proxy")
    if db_sec_pro_ip_hosting_enabled:
        security_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-hosting")
    if db_sec_pro_ip_city_security_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-city")
        security_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-security")
    if db_sec_pro_ip_city_isp_security_enabled:
        geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-city-isp")
        security_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-security")

    return geolocation_mmdb_reader, security_mmdb_reader


def lookup_ip_addresses_from_mmdb(object,
                                  ip_address_list,
                                  geolocation_mmdb_reader,
                                  security_mmdb_reader,
                                  language,
                                  lookup_dma,
                                  lookup_geo_accuracy,
                                  lookup_abuse_contact,
                                  lookup_security):
    lookup_response = dict()

    if geolocation_mmdb_reader is not None:
        lookup_response = read_geolocation_mmdb(
            object,
            geolocation_mmdb_reader,
            ip_address_list,
            language,
            lookup_dma,
            lookup_geo_accuracy,
            lookup_abuse_contact
        )

    if security_mmdb_reader is not None:
        security_results = read_security_mmdb(object, security_mmdb_reader, ip_address_list, lookup_security)
        lookup_response = merge_mmdb_responses(lookup_response, security_results)

    return lookup_response


dispatch(IPGeolocationBatch, sys.argv, sys.stdin, sys.stdout, __name__)
