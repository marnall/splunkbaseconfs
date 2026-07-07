import traceback

from requests import Response

from app_utils import get_null_ip_geolocation, get_null_ip_geolocation_for_api, get_null_ip_security_for_api
from app_utils import get_logger, get_config


logger = get_logger("parse_response")
api_subscription_plan = get_config("api_subscription_plan")


def parse_ipgeolocation_api_response(
        response: Response,
        lookup_live_hostname: bool,
        lookup_hostname_fallback_live: bool,
        lookup_dma: bool,
        lookup_security: bool,
        lookup_abuse_contact: bool,
        lookup_geo_accuracy: bool
):
    ip_geolocations = {}
    response_json_array = response.json()

    try:
        for ip_geolocation in response_json_array:
            record = dict()
            record["ip"] = ip_geolocation.get("ip")

            if lookup_live_hostname or lookup_hostname_fallback_live:
                record.update(__parse_hostname(ip_geolocation))

            location_obj = ip_geolocation.get("location", None)

            if location_obj is not None:
                record.update(
                    __parse_location(location_obj, on_paid_plan=api_subscription_plan == "PAID", dma=lookup_dma, geo_accuracy=lookup_geo_accuracy))

            country_metadata_obj = ip_geolocation.get("country_metadata", None)

            if country_metadata_obj is not None:
                record.update(__parse_country_metadata(country_metadata_obj))

            network_obj = ip_geolocation.get("network", None)

            if (api_subscription_plan == "PAID") and network_obj is not None:
                record.update(__parse_network(network_obj))
            
            asn_obj = ip_geolocation.get("asn", None)

            if asn_obj is not None:
                record.update(__parse_asn(asn_obj, on_paid_plan=api_subscription_plan == "PAID"))
            
            company_obj = ip_geolocation.get("company", None)

            if (api_subscription_plan == "PAID") and company_obj is not None:
                record.update(__parse_company(company_obj))

            currency_obj = ip_geolocation.get("currency", None)

            if currency_obj is not None:
                record.update(__parse_currency(currency_obj))

            if api_subscription_plan == "PAID":
                if lookup_security:
                    security_obj = ip_geolocation.get("security", None)

                    if security_obj is not None:
                        record.update(__parse_security(security_obj))

                if lookup_abuse_contact:
                    abuse_contact_obj = ip_geolocation.get("abuse", None)

                    if abuse_contact_obj is not None:
                        record.update(__parse_abuse_contact(abuse_contact_obj))


    
            time_zone_obj = ip_geolocation.get("time_zone", None)
            
            if time_zone_obj is not None:
                record.update(__parse_time_zone(time_zone_obj))

            ip_geolocations[ip_geolocation.get("ip")] = record
    except Exception as e:
        logger.error(e)
        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

    return ip_geolocations


def parse_ipsecurity_api_response(
        response: Response,
):
    ip_securities = dict()
    response_json_array = response.json()

    try:
        for ip_security in response_json_array:
            record = dict()
            record["ip"] = ip_security.get("ip")

            # if lookup_live_hostname or lookup_hostname_fallback_live:
            #     record.update(__parse_hostname(ip_security))

            security_obj = ip_security.get("security", None)

            if security_obj is not None:
                record.update(__parse_security(security_obj))

            # if lookup_location:
            #     location_obj = ip_security.get("location", None)

            #     if location_obj is not None:
            #         record.update(__parse_location(location_obj, on_advance_plan=False, dma=False))

            # if lookup_country_metadata:
            #     country_metadata_obj = ip_security.get("country_metadata", None)

            #     if country_metadata_obj is not None:
            #         record.update(__parse_country_metadata(country_metadata_obj))

            # if lookup_network:
            #     network_obj = ip_security.get("network", None)

            #     if network_obj is not None:
            #         record.update(__parse_network(network_obj, on_advance_plan=False))

            # if lookup_currency:
            #     currency_obj = ip_security.get("currency", None)

            #     if currency_obj is not None:
            #         record.update(__parse_currency(currency_obj))

            # if lookup_timezone:
            #     time_zone_obj = ip_security.get("time_zone", None)

            #     if time_zone_obj is not None:
            #         record.update(__parse_time_zone(time_zone_obj))

            ip_securities[ip_security.get("ip")] = record
    except Exception as e:
        logger.error(e)
        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

    return ip_securities

def __parse_hostname(api_response: dict) -> dict:
    return { "hostname": api_response.get("hostname") }

def __parse_location(location_obj: dict, on_paid_plan: bool, dma: bool, geo_accuracy: bool) -> dict:
    record = dict()

    record["location.continent_code"] = location_obj.get("continent_code")
    record["location.continent_name"] = location_obj.get("continent_name")
    record["location.country_code2"] = location_obj.get("country_code2")
    record["location.country_code3"] = location_obj.get("country_code3")
    record["location.country_name"] = location_obj.get("country_name")
    record["location.country_name_official"] = location_obj.get("country_name_official")
    record["location.country_capital"] = location_obj.get("country_capital")
    record["location.state_prov"] = location_obj.get("state_prov")
    record["location.state_code"] = location_obj.get("state_code")
    record["location.district"] = location_obj.get("district")
    record["location.city"] = location_obj.get("city")

    if on_paid_plan:
        if geo_accuracy:
            record["location.locality"] = location_obj.get("locality")
            record["location.accuracy_radius"] = location_obj.get("accuracy_radius")
            record["location.confidence"] = location_obj.get("confidence")

        if dma:
            record["location.dma_code"] = location_obj.get("dma_code")

    record["location.zipcode"] = location_obj.get("zipcode")
    record["location.latitude"] = location_obj.get("latitude")
    record["location.longitude"] = location_obj.get("longitude")
    record["location.is_eu"] = location_obj.get("is_eu")
    record["location.country_flag"] = location_obj.get("country_flag")
    record["location.geoname_id"] = location_obj.get("geoname_id")
    record["location.country_emoji"] = location_obj.get("country_emoji")

    return record

def __parse_country_metadata(country_metadata_obj: dict) -> dict:
    record = dict()

    record["country.calling_code"] = country_metadata_obj.get("calling_code")
    record["country.tld"] = country_metadata_obj.get("tld")
    record["country.languages"] = ", ".join(country_metadata_obj.get("languages", []))

    return record

def __parse_network(network_obj: dict) -> dict:
    record = dict()

    # asn_obj = network_obj.get("asn", None)

    # if asn_obj is not None and isinstance(asn_obj, dict):
    #     record["network.asn.as_number"] = asn_obj.get("as_number")
    #     record["network.asn.organization"] = asn_obj.get("organization")
    #     record["network.asn.country"] = asn_obj.get("country")

    #     if on_advance_plan:
    #         record["network.asn.asn_name"] = asn_obj.get("asn_name")
    #         record["network.asn.type"] = asn_obj.get("type")
    #         record["network.asn.domain"] = asn_obj.get("domain")
    #         record["network.asn.date_allocated"] = asn_obj.get("date_allocated")
    #         record["network.asn.allocation_status"] = asn_obj.get("allocation_status")
    #         record["network.asn.num_of_ipv4_routes"] = asn_obj.get("num_of_ipv4_routes")
    #         record["network.asn.num_of_ipv6_routes"] = asn_obj.get("num_of_ipv6_routes")
    #         record["network.asn.rir"] = asn_obj.get("rir")

    # record["network.connection_type"] = network_obj.get("connection_type")

    # company_obj = network_obj.get("company", None)

    # if company_obj is not None and isinstance(company_obj, dict):
    #     record["network.company.name"] = company_obj.get("name")

    #     if on_advance_plan:
    #         record["network.company.type"] = company_obj.get("type")
    #         record["network.company.domain"] = company_obj.get("domain")
    record["network.connection_type"] = network_obj.get("connection_type")
    record["network.route"] = network_obj.get("route")
    record["network.is_anycast"] = network_obj.get("is_anycast")

    return record


def __parse_asn(asn_obj: dict, on_paid_plan: bool) -> dict:
    record = dict()

    record["asn.as_number"] = asn_obj.get("as_number")
    record["asn.organization"] = asn_obj.get("organization")
    record["asn.country"] = asn_obj.get("country")
    
    if on_paid_plan: 
        record["asn.type"] = asn_obj.get("type")
        record["asn.domain"] = asn_obj.get("domain")
        record["asn.date_allocated"] = asn_obj.get("date_allocated")
        record["asn.rir"] = asn_obj.get("rir")
    

    return record

def __parse_company(company_obj: dict) -> dict:
    record = dict()

    record["company.name"] = company_obj.get("name")
    record["company.type"] = company_obj.get("type")
    record["company.domain"] = company_obj.get("domain")

    return record

def __parse_currency(currency_obj: dict) -> dict:
    record = dict()

    record["currency.code"] = currency_obj.get("code")
    record["currency.name"] = currency_obj.get("name")
    record["currency.symbol"] = currency_obj.get("symbol")

    return record

def __parse_security(security_obj: dict) -> dict:
    record = dict()

    record["security.threat_score"] = security_obj.get("threat_score")

    record["security.is_tor"] = security_obj.get("is_tor")

    record["security.is_proxy"] = security_obj.get("is_proxy")

    # Convert array -> comma separated string
    record["security.proxy_provider_names"] = ", ".join(
        security_obj.get("proxy_provider_names", [])
    )

    record["security.proxy_confidence_score"] = (
        security_obj.get("proxy_confidence_score")
    )

    record["security.proxy_last_seen"] = (
        security_obj.get("proxy_last_seen")
    )

    record["security.is_residential_proxy"] = (
        security_obj.get("is_residential_proxy")
    )

    record["security.is_vpn"] = security_obj.get("is_vpn")

    # Convert array -> comma separated string
    record["security.vpn_provider_names"] = ", ".join(
        security_obj.get("vpn_provider_names", [])
    )

    record["security.vpn_confidence_score"] = (
        security_obj.get("vpn_confidence_score")
    )

    record["security.vpn_last_seen"] = (
        security_obj.get("vpn_last_seen")
    )

    record["security.is_relay"] = security_obj.get("is_relay")

    record["security.relay_provider_name"] = (
        security_obj.get("relay_provider_name")
    )

    record["security.is_anonymous"] = (
        security_obj.get("is_anonymous")
    )

    record["security.is_known_attacker"] = (
        security_obj.get("is_known_attacker")
    )

    record["security.is_bot"] = security_obj.get("is_bot")

    record["security.is_spam"] = security_obj.get("is_spam")

    record["security.is_cloud_provider"] = (
        security_obj.get("is_cloud_provider")
    )

    record["security.cloud_provider_name"] = (
        security_obj.get("cloud_provider_name")
    )

    return record

def __parse_abuse_contact(abuse_contact_obj: dict):
    record = dict()

    record["abuse.route"] = abuse_contact_obj.get("route")
    record["abuse.country"] = abuse_contact_obj.get("country")
    record["abuse.name"] = abuse_contact_obj.get("name")
    record["abuse.organization"] = abuse_contact_obj.get("organization")
    record["abuse.kind"] = abuse_contact_obj.get("kind")
    record["abuse.address"] = abuse_contact_obj.get("address")
    record["abuse.emails"] = ", ".join(abuse_contact_obj.get("emails", []))
    record["abuse.phone_numbers"] = ", ".join(abuse_contact_obj.get("phone_numbers", []))

    return record

def __parse_time_zone(time_zone_obj: dict):
    record = dict()

    record["timezone.name"] = time_zone_obj.get("name")
    record["timezone.offset"] = time_zone_obj.get("offset")
    record["timezone.offset_with_dst"] = time_zone_obj.get("offset_with_dst")
    record["timezone.current_time"] = time_zone_obj.get("current_time")
    record["timezone.current_time_unix"] = time_zone_obj.get("current_time_unix")
    record["timezone.current_tz_abbreviation"] = time_zone_obj.get("current_tz_abbreviation")
    record["timezone.current_tz_full_name"] = time_zone_obj.get("current_tz_full_name")
    record["timezone.standard_tz_abbreviation"] = time_zone_obj.get("standard_tz_abbreviation")
    record["timezone.standard_tz_full_name"] = time_zone_obj.get("standard_tz_full_name")
    record["timezone.is_dst"] = time_zone_obj.get("is_dst")
    record["timezone.dst_savings"] = time_zone_obj.get("dst_savings")
    record["timezone.dst_exists"] = time_zone_obj.get("dst_exists")
    record["timezone.dst_tz_abbreviation"] = time_zone_obj.get("dst_tz_abbreviation")
    record["timezone.dst_tz_full_name"] = time_zone_obj.get("dst_tz_full_name")

    dst_start_obj = time_zone_obj.get("dst_start", None)
    dst_end_obj = time_zone_obj.get("dst_end", None)

    if dst_start_obj is not None and isinstance(dst_start_obj, dict):
        record["timezone.dst_start.utc_time"] = dst_start_obj.get("utc_time")
        record["timezone.dst_start.duration"] = dst_start_obj.get("duration")
        record["timezone.dst_start.gap"] = dst_start_obj.get("gap")
        record["timezone.dst_start.date_time_after"] = dst_start_obj.get("date_time_after")
        record["timezone.dst_start.date_time_before"] = dst_start_obj.get("date_time_before")
        record["timezone.dst_start.overlap"] = dst_start_obj.get("overlap")

    if dst_end_obj is not None and isinstance(dst_end_obj, dict):
        record["timezone.dst_end.utc_time"] = dst_end_obj.get("utc_time")
        record["timezone.dst_end.duration"] = dst_end_obj.get("duration")
        record["timezone.dst_end.gap"] = dst_end_obj.get("gap")
        record["timezone.dst_end.date_time_after"] = dst_end_obj.get("date_time_after")
        record["timezone.dst_end.date_time_before"] = dst_end_obj.get("date_time_before")
        record["timezone.dst_end.overlap"] = dst_end_obj.get("overlap")

    return record


def fill_null_ip_geolocations(ip_address_list: list, lookup_security: bool, lookup_live_hostname: bool, lookup_hostname_fallback_live: bool):
    ip_geolocations = {}

    for ip_address in ip_address_list:
        null_ip_geolocation = get_null_ip_geolocation(lookup_security, lookup_live_hostname, lookup_hostname_fallback_live)
        null_ip_geolocation["ip"] = ip_address
        ip_geolocations[ip_address] = null_ip_geolocation

    return ip_geolocations


def fill_null_ip_geolocations_for_api(
        ip_address_list: list,
        lookup_live_hostname: bool,
        lookup_hostname_fallback_live: bool,
        lookup_dma: bool,
        lookup_security: bool,
        lookup_abuse_contact: bool,
        lookup_geo_accuracy: bool
):
    ip_geolocations = dict()

    for ip_address in ip_address_list:
        null_ip_geolocation = get_null_ip_geolocation_for_api(
            lookup_live_hostname,
            lookup_hostname_fallback_live,
            lookup_dma,
            lookup_security,
            lookup_abuse_contact,
            lookup_geo_accuracy
        )
        null_ip_geolocation.update({
            "ip": ip_address
        })
        ip_geolocations[ip_address] = null_ip_geolocation

    return ip_geolocations


def fill_null_ip_securities_for_api(
        ip_address_list: list,
):
    ip_securities = dict()

    for ip_address in ip_address_list:
        null_ip_security = get_null_ip_security_for_api(
           
        )
        null_ip_security.update({
            "ip": ip_address
        })
        ip_securities[ip_address] = null_ip_security

    return ip_securities


__package__: list[str] = [
    "parse_ipgeolocation_api_response",
    "parse_ipsecurity_api_response",
    "fill_null_ip_geolocations",
    "fill_null_ip_geolocations_for_api",
    "fill_null_ip_securities_for_api"
]