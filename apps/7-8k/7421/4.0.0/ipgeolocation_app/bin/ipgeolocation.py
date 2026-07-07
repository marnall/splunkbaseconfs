import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Option,
    Configuration,
    validators
)

from api_request import query_ipgeolocation_api
from lookup_mmdb import read_geolocation_mmdb
from lookup_mmdb import read_security_mmdb
from lookup_mmdb import merge_mmdb_responses
from parse_api_response import parse_ipgeolocation_api_response, fill_null_ip_geolocations_for_api
from app_utils import get_null_ip_geolocation, get_null_ip_geolocation_for_api
from app_utils import get_config
from app_utils import get_current_api_usage
from app_utils import get_mmdb_lookup_reader
from app_utils import get_logger
from app_utils import is_indexers


logger = get_logger("ipgeolocation")

replicate_lookup = get_config("replicate_lookup") == "Yes"
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


@Configuration(distributed=replicate_lookup)
class IPGeolocationLookup(StreamingCommand):
    liveHostname = Option(
        doc='''
        **Syntax:** **liveHostname=***<true|false>*
        **Description:** Lookup live hostname for the IP address. Supported on lookup from ipgeolocation.io PAID API only.''',
        default=False, require=False, validate=validators.Boolean())
    hostnameFallbackLive = Option(
        doc='''
        **Syntax:** **hostnameFallbackLive=***<true|false>*
        **Description:** Lookup hostname for the IP address from database and fallback to live lookup if not in the database. Supported on lookup from ipgeolocation.io PAID API only.''',
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
    geoAccuracy = Option(
        doc='''
        **Syntax:** **geoAccuracy=***<true|false>*
        **Description:** Lookup geo accuracy for the location of IP Address. It includes locality, accuracy_radius and confidence level in the response. Supported on PAID API only.''',
        default=False, require=False, validate=validators.Boolean())
    security = Option(
        doc='''
        **Syntax:** **security=***<true|false>*
        **Description:** Lookup security information for an IP address.''',
        default=False, require=False, validate=validators.Boolean())
    allinfo = Option(
        doc='''
        **Syntax:** **allinfo=***<true|false>*
        **Description:** Lookup abuse contact, DMA (Designated Market Area) code, IP-Security and time zone details for the provided IP address.''',
        default=False, require=False, validate=validators.Boolean())
    prefix = Option(
        doc='''
        **Syntax:** **prefix=***<true|false>*
        **Description:** Prefix query name to all fields in the response.''',
        default=False, require=False, validate=validators.Boolean())
    language = Option(
        doc='''
        **Syntax:** **language=***<en|de|ru|ja|fr|cn|es|cs|it|ko|fa|pt>*
        **Description:** Set the response language for search results. Default response language is 'en'.''',
        default="en", require=False)

    def stream(self, records):
        lookup_live_hostname = self.liveHostname
        lookup_hostname_fallback_live = self.hostnameFallbackLive
        lookup_abuse_contact = self.abuseContact
        lookup_geo_accuracy = self.geoAccuracy
        lookup_dma = self.dma
        lookup_security = self.security
        lookup_allinfo = self.allinfo
        prefix = self.prefix
        language = self.language
        fields = self.fieldnames

        if lookup_allinfo:
            lookup_live_hostname = True
            lookup_abuse_contact = True
            lookup_dma = True
            lookup_geo_accuracy = True
            lookup_security = True
        
        if len(fields) > 1:
            prefix = True
        
        count = 0
        ip_addresses = []

        try:
            if method == "MMDB":
                geolocation_log_path, security_log_path = get_mmdb_readers(self)

                # TODO
                # options to configure the lookup options:
                # 1. abuse_contact
                # 2. dma
                # 3. security
                # 4. timezone

                for record in records:
                    new_counter = 0

                    for field in fields:
                        if record.get(field):
                            ip_value = record.get(field).strip()

                            if ip_value != "":
                                new_counter += 1
                                ip_addresses.append(ip_value)
                                count += 1

                    if new_counter >= 1:
                        ip_geolocations = lookup_ip_addresses_from_mmdb(
                            self,
                            ip_addresses,
                            geolocation_log_path,
                            security_log_path,
                            language,
                            lookup_dma,
                            lookup_abuse_contact,
                            lookup_geo_accuracy,
                            lookup_security
                        )
                        ip_addresses = []

                        if bool(ip_geolocations):
                            try:
                                for field in fields:
                                    ip_value = record.get(field).strip()

                                    if ip_value != "":
                                        ip_geolocation = ip_geolocations.get(ip_value)

                                        if ip_geolocation is not None:
                                            if prefix:
                                                record.update(prefix_keys(ip_geolocation, field))
                                            else:
                                                record.update(ip_geolocation)
                            except Exception as e:
                                logger.error(e)
                                logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

                            yield record
                        else:
                            self.write_warning("Something went wrong. Please check ipgeolocation.log for more information.")
                            
                            null_ip_geolocation = get_null_ip_geolocation(lookup_security, lookup_live_hostname, lookup_hostname_fallback_live)
                            
                            for field in fields:
                                if prefix:
                                    record.update(prefix_keys(null_ip_geolocation, field))
                                else:
                                    record.update(null_ip_geolocation)
                            
                            yield record
                    else:
                        null_ip_geolocation = get_null_ip_geolocation(lookup_security, lookup_live_hostname, lookup_hostname_fallback_live)

                        for field in fields:
                            if prefix:
                                record.update(prefix_keys(null_ip_geolocation, field))
                            else:
                                record.update(null_ip_geolocation)
                        
                        yield record
            else:
                if api_subscription_plan != "FREE" and api_subscription_plan != "PAID":
                    self.write_warning("Your subscription plan must be 'Free', or 'Paid' to search IP geolocation through `ipgeolocation` command.")
                else:
                    record_list = {}
                    total_requests = 0
                    current_api_usage_before_command = 0

                    if not is_indexers():
                        current_api_usage_before_command = get_current_api_usage(self)
                        logger.info("Used before running command : " + str(current_api_usage_before_command))

                    for record in records:
                        new_counter = 0

                        for field in fields:
                            if record.get(field):
                                ip_value = record.get(field).strip()

                                if ip_value != "":
                                    new_counter += 1
                                    ip_addresses.append(ip_value)
                                    count += 1
                                    total_requests += 1

                        if new_counter >= 1:
                            record_list[str(count)] = record
                        else:
                            null_ip_geolocation = get_null_ip_geolocation_for_api(
                                lookup_live_hostname,
                                lookup_hostname_fallback_live,
                                lookup_dma,
                                lookup_security,
                                lookup_abuse_contact,
                                lookup_geo_accuracy
                            )

                            for field in fields:
                                if prefix:
                                    record.update(prefix_keys(null_ip_geolocation, field))
                                else:
                                    record.update(null_ip_geolocation)

                            yield record

                        if count > 750:
                            count = 0

                            ip_geolocations = lookup_ip_geolocations_from_api(
                                self,
                                ip_addresses,
                                lookup_live_hostname,
                                lookup_hostname_fallback_live,
                                lookup_dma,
                                lookup_security,
                                lookup_abuse_contact,
                                lookup_geo_accuracy,
                                language
                            )
                            ip_addresses = []

                            if bool(ip_geolocations):
                                temp = record_list
                                record_list = {}

                                for key, record_v1 in temp.items():
                                    try:
                                        for field in fields:
                                            if record_v1.get(field):
                                                if ip_geolocations[record_v1.get(field)]:
                                                    if prefix:
                                                        record_v1.update(prefix_keys(ip_geolocations[record_v1.get(field)], field))
                                                    else:
                                                        record_v1.update(ip_geolocations[record_v1.get(field)])
                                    except Exception as e:
                                        logger.error(e)
                                        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

                                    yield record_v1
                            else:
                                self.write_warning("Something went wrong. Please check ipgeolocation.log for more information.")

                                temp = record_list
                                record_list = {}

                                for key, record_v1 in temp.items():
                                    yield record_v1

                    if count < 750:
                        ip_geolocations = lookup_ip_geolocations_from_api(
                            self,
                            ip_addresses,
                            lookup_live_hostname,
                            lookup_hostname_fallback_live,
                            lookup_dma,
                            lookup_security,
                            lookup_abuse_contact,
                            lookup_geo_accuracy,
                            language
                        )

                        if bool(ip_geolocations):
                            temp = record_list
                            record_list = {}

                            for key, record_v1 in temp.items():
                                try:
                                    for field in fields:
                                        if record_v1.get(field):
                                            if ip_geolocations[record_v1.get(field)]:
                                                if prefix:
                                                    record_v1.update(prefix_keys(ip_geolocations[record_v1.get(field)], field))
                                                else:
                                                    record_v1.update(ip_geolocations[record_v1.get(field)])
                                except Exception as e:
                                    logger.error(e)
                                    logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

                                yield record_v1
                        else:
                            self.write_warning("Something went wrong. Please check ipgeolocation.log for more information.")
                            temp = record_list
                            record_list = {}

                            for key, record_v1 in temp.items():
                                yield record_v1

                    if not is_indexers():
                        current_api_usage_after_command = get_current_api_usage(self)
                        logger.info("API usage after running command : " + str(current_api_usage_after_command))
                        diff = current_api_usage_after_command - current_api_usage_before_command
                        logger.info("API usage by command as per ipgeolocation.io " + str(diff))
                        logger.info("API usage by command as per app " + str(total_requests))
                        logger.info(
                            "API usage in ipgeolocation.io is updated in about 20 minutes. So, the usage as per ipgeolocation.io might be less than the usage as per command."
                        )
        except Exception as e:
            logger.error(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))


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
                                  lookup_abuse_contact,
                                  lookup_geo_accuracy,
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
            lookup_abuse_contact)

    if security_mmdb_reader is not None:
        security_results = read_security_mmdb(object, security_mmdb_reader, ip_address_list, lookup_security)
        lookup_response = merge_mmdb_responses(lookup_response, security_results)

    return lookup_response


def prefix_keys(ip_geolocation, prefix):
    prefixed_ip_geolocation = dict()

    for key, value in ip_geolocation.items():
        prefixed_ip_geolocation[prefix + "_" + key] = value
    
    return prefixed_ip_geolocation


def lookup_ip_geolocations_from_api(
        object,
        ip_address_list: list,
        lookup_live_hostname: bool,
        lookup_hostname_fallback_live: bool,
        lookup_dma: bool,
        lookup_security: bool,
        lookup_abuse_contact: bool,
        lookup_geo_accuracy: bool,
        language: str
    ):
    ip_geolocations = dict()

    try:
        response = query_ipgeolocation_api(
            object,
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
        
        if response is None:
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
                response,
                lookup_live_hostname,
                lookup_hostname_fallback_live,
                lookup_dma,
                lookup_security,
                lookup_abuse_contact,
                lookup_geo_accuracy
            )
    except Exception as e:
        object.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
        object.write_warning(str(e))
        logger.error(e)
        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
    
    return ip_geolocations


if __name__ == "__main__":
    dispatch(IPGeolocationLookup, sys.argv, sys.stdin, sys.stdout, __name__)
