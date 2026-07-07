import traceback

from app_utils import get_logger
from app_utils import get_config


logger = get_logger("lookup_mmdb")
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
on_advance_plan = db_advanced_ip_city_enabled \
    or db_advanced_ip_abuse_enabled \
    or db_advanced_ip_asn_enabled \
    or db_advanced_ip_asn_ext_enabled \
    or db_advanced_ip_company_enabled \
    or db_advanced_ip_whois_enabled \
    or db_advanced_ip_city_company_asn_enabled \
    or db_advanced_ip_city_company_asn_abuse_enabled \
    or db_advanced_ip_company_asn_enabled \
    or db_advanced_ip_city_company_asn_abuse_security_enabled
on_security_pro_plan = db_sec_pro_ip_security_enabled \
                  or db_sec_pro_ip_residential_proxy_enabled \
                  or db_sec_pro_ip_hosting_enabled \
                  or db_sec_pro_ip_city_security_enabled \
                  or db_sec_pro_ip_city_isp_security_enabled
on_standard_plan = db_std_ip_country_enabled \
    or db_std_ip_city_enabled \
    or db_std_ip_isp_enabled \
    or db_std_ip_city_isp_enabled

def read_geolocation_mmdb(object,
                          mmdb_reader,
                          ip_address_list,
                          language,
                          lookup_dma,
                          lookup_geo_accuracy,
                          lookup_abuse_contact,
                          ):
    ip_geolocations = dict()

    if lookup_abuse_contact is False and db_advanced_ip_abuse_enabled:
        lookup_abuse_contact = True

    try:
        for ip in ip_address_list:
            ip = ip.strip()
            mmdb_response = mmdb_reader.get(ip)

            if mmdb_response is not None and isinstance(mmdb_response, dict):
                ip_geolocation = dict()
                ip_geolocation["ip"] = ip
                location_obj = mmdb_response.get("location")

                if location_obj is not None and isinstance(location_obj, dict):
                    country_obj = location_obj.get("country")

                    if country_obj is not None and isinstance(country_obj, dict):
                        continent_obj = country_obj.get("continent")

                        if continent_obj is not None and isinstance(continent_obj, dict):
                            ip_geolocation["location.continent_code"] = continent_obj.get("code", "")

                            continent_name_obj = continent_obj.get("name")

                            ip_geolocation["location.continent_name"] = continent_name_obj.get(
                                language,
                                continent_name_obj.get("en", "")
                            ) if continent_name_obj is not None and isinstance(continent_name_obj, dict) else ""

                        ip_geolocation["location.country_code2"] = country_obj.get("code2", "")
                        ip_geolocation["location.country_code3"] = country_obj.get("code3", "")
                        ip_geolocation["location.country_code_ioc"] = country_obj.get("code_ioc", "")

                        country_name_obj = country_obj.get("name")
                        country_name_official_obj = country_obj.get("name_official")

                        ip_geolocation["location.country_name"] = country_name_obj.get(
                            language,
                            country_name_obj.get("en", "")
                        ) if country_name_obj is not None and isinstance(country_name_obj, dict) else ""

                        ip_geolocation["location.country_name_official"] = country_name_official_obj.get(
                            language,
                            country_name_official_obj.get("en", "")
                        ) if country_name_official_obj is not None and isinstance(country_name_official_obj, dict) else ""

                        country_capital_obj = country_obj.get("capital")

                        ip_geolocation["location.country_capital"] = country_capital_obj.get(
                            language,
                            country_capital_obj.get("en", "")
                        ) if country_capital_obj is not None and isinstance(country_capital_obj, dict) else ""

                    state_obj = location_obj.get("state")

                    if state_obj is not None and isinstance(state_obj, dict):
                        state_name_obj = state_obj.get("name")

                        ip_geolocation["location.state_prov"] = state_name_obj.get(
                            language,
                            state_name_obj.get("en", "")) if state_name_obj is not None and isinstance(state_name_obj, dict) \
                            else ""

                        ip_geolocation["location.state_code"] = state_obj.get("code", "")

                    district_obj = location_obj.get("district")

                    if district_obj is not None and isinstance(district_obj, dict):
                        district_name_obj = district_obj.get("name", None)

                        ip_geolocation["location.district"] = district_name_obj.get(
                            language,
                            district_name_obj.get("en", "")) if district_name_obj is not None and isinstance(district_name_obj, dict) \
                            else ""

                    city_obj = location_obj.get("city")

                    if city_obj is not None and isinstance(city_obj, dict):
                        city_name_obj = city_obj.get("name", None)

                        ip_geolocation["location.city"] = city_name_obj.get(
                            language,
                            city_name_obj.get("en", "")
                        ) if city_name_obj is not None and isinstance(city_name_obj, dict) else ""

                    if on_advance_plan:
                        if lookup_geo_accuracy:
                            ip_geolocation["location.accuracy_radius"] = location_obj.get("accuracy_radius", "")
                            ip_geolocation["location.confidence"] = location_obj.get("confidence", "")

                        if lookup_dma:
                            ip_geolocation["location.dma_code"] = location_obj.get("dma_code", "")

                    zipcode = location_obj.get("zipcode")

                    if zipcode is not None:
                        ip_geolocation["location.zipcode"] = zipcode

                    coordinates_obj = location_obj.get("coordinates")

                    if coordinates_obj is not None and isinstance(coordinates_obj, dict):
                        ip_geolocation["location.latitude"] = coordinates_obj.get("latitude", "")
                        ip_geolocation["location.longitude"] = coordinates_obj.get("longitude", "")
                    else:
                        ip_geolocation["location.latitude"] = ""
                        ip_geolocation["location.longitude"] = ""

                    ip_geolocation["location.geoname_id"] = location_obj.get("geoname_id", "")

                    if country_obj is not None and isinstance(country_obj, dict):
                        country_metadata_obj = country_obj.get("metadata")

                        if country_metadata_obj is not None and isinstance(country_metadata_obj, dict):
                            ip_geolocation["country.calling_code"] = country_metadata_obj.get("calling_code", "")
                            ip_geolocation["country.tld"] = country_metadata_obj.get("tld", "")
                            ip_geolocation["country.languages"] = country_metadata_obj.get("languages", "")
                        else:
                            ip_geolocation["country.calling_code"] = ""
                            ip_geolocation["country.tld"] = ""
                            ip_geolocation["country.languages"] = ""

                        country_currency_obj = country_obj.get("currency")

                        if country_currency_obj is not None and isinstance(country_currency_obj, dict):
                            ip_geolocation["currency.code"] = country_currency_obj.get("code", "")

                            currency_name_obj = country_currency_obj.get("name")

                            ip_geolocation["currency.name"] = currency_name_obj.get("en", "") \
                                if currency_name_obj is not None and isinstance(currency_name_obj, dict) else ""

                            ip_geolocation["currency.symbol"] = country_currency_obj.get("symbol", "")
                        else:
                            ip_geolocation["currency.code"] = ""
                            ip_geolocation["currency.name"] = ""
                            ip_geolocation["currency.symbol"] = ""

                asn_obj = mmdb_response.get("asn")

                if asn_obj is not None and isinstance(asn_obj, dict):
                    ip_geolocation["asn.as_number"] = asn_obj.get("as_number", "")
                    ip_geolocation["asn.country"] = asn_obj.get("country_code", "")
                    ip_geolocation["asn.organization"] = asn_obj.get("organization", "")
                    ip_geolocation["asn.type"] = asn_obj.get("type", "")
                    ip_geolocation["asn.domain"] = asn_obj.get("domain", "")

                    if db_advanced_ip_asn_ext_enabled or db_advanced_ip_city_company_asn_enabled:
                        ip_geolocation["asn.asn_name"] = asn_obj.get("as_name", "")
                        ip_geolocation["asn.allocation_status"] = asn_obj.get("allocation_status", "")
                        ip_geolocation["asn.downstreams"] = asn_obj.get("downstreams", "")
                        ip_geolocation["asn.upstreams"] = asn_obj.get("upstreams", "")
                        ip_geolocation["asn.peers"] = asn_obj.get("peers", "")
                        ip_geolocation["asn.routes"] = asn_obj.get("routes", "")
                        ip_geolocation["asn.date_allocated"] = asn_obj.get("date_allocated", "")
                        ip_geolocation["asn.rir"] = asn_obj.get("whois_host", "")
                elif db_std_ip_isp_enabled or db_std_ip_city_isp_enabled or db_sec_pro_ip_city_isp_security_enabled:
                    ip_geolocation["asn.as_number"] = mmdb_response.get("asn", "")
                    ip_geolocation["asn.country"] = mmdb_response.get("as_country", "")
                    ip_geolocation["asn.organization"] = mmdb_response.get("as_organization", "")
                    ip_geolocation["company.name"] = mmdb_response.get("isp", "")
                    
                    country_obj = mmdb_response.get("country")

                    if country_obj is not None and isinstance(country_obj, dict):
                        continent_obj = country_obj.get("continent")

                        if continent_obj is not None and isinstance(continent_obj, dict):
                            ip_geolocation["location.continent_code"] = continent_obj.get("code", "")

                            continent_name_obj = continent_obj.get("name")

                            ip_geolocation["location.continent_name"] = continent_name_obj.get(
                                language,
                                continent_name_obj.get("en", "")
                            ) if continent_name_obj is not None and isinstance(continent_name_obj, dict) else ""

                        ip_geolocation["location.country_code2"] = country_obj.get("code2", "")
                        ip_geolocation["location.country_code3"] = country_obj.get("code3", "")
                        ip_geolocation["location.country_code_ioc"] = country_obj.get("code_ioc", "")

                        country_name_obj = country_obj.get("name")
                        country_name_official_obj = country_obj.get("name_official")

                        ip_geolocation["location.country_name"] = country_name_obj.get(
                            language,
                            country_name_obj.get("en", "")
                        ) if country_name_obj is not None and isinstance(country_name_obj, dict) else ""

                        ip_geolocation["location.country_name_official"] = country_name_official_obj.get(
                            language,
                            country_name_official_obj.get("en", "")
                        ) if country_name_official_obj is not None and isinstance(country_name_official_obj, dict) else ""

                        country_capital_obj = country_obj.get("capital")

                        ip_geolocation["location.country_capital"] = country_capital_obj.get(
                            language,
                            country_capital_obj.get("en", "")
                        ) if country_capital_obj is not None and isinstance(country_capital_obj, dict) else ""
                        
                        country_metadata_obj = country_obj.get("metadata")

                        if country_metadata_obj is not None and isinstance(country_metadata_obj, dict):
                            ip_geolocation["country.calling_code"] = country_metadata_obj.get("calling_code", "")
                            ip_geolocation["country.tld"] = country_metadata_obj.get("tld", "")
                            ip_geolocation["country.languages"] = country_metadata_obj.get("languages", "")
                        else:
                            ip_geolocation["country.calling_code"] = ""
                            ip_geolocation["country.tld"] = ""
                            ip_geolocation["country.languages"] = ""

                        country_currency_obj = country_obj.get("currency")

                        if country_currency_obj is not None and isinstance(country_currency_obj, dict):
                            ip_geolocation["currency.code"] = country_currency_obj.get("code", "")

                            currency_name_obj = country_currency_obj.get("name")

                            ip_geolocation["currency.name"] = currency_name_obj.get("en", "") \
                                if currency_name_obj is not None and isinstance(currency_name_obj, dict) else ""

                            ip_geolocation["currency.symbol"] = country_currency_obj.get("symbol", "")
                        else:
                            ip_geolocation["currency.code"] = ""
                            ip_geolocation["currency.name"] = ""
                            ip_geolocation["currency.symbol"] = ""
                        
                    

                company_obj = mmdb_response.get("company")

                if company_obj is not None and isinstance(company_obj, dict):
                    company_name_obj = company_obj.get("name")

                    ip_geolocation["company.name"] = company_name_obj.get("en", "") \
                        if company_name_obj is not None and isinstance(company_name_obj, dict) else ""

                    ip_geolocation["company.type"] = company_obj.get("type", "")
                    ip_geolocation["company.domain"] = company_obj.get("domain", "")

                connection_type = mmdb_response.get("connection_type")

                if connection_type is not None:
                    ip_geolocation["network.connection_type"] = connection_type

               
                timezone = mmdb_response.get("time_zone")

                if timezone is not None:
                    ip_geolocation["timezone.name"] = timezone

                if lookup_abuse_contact:
                    abuse_obj = mmdb_response.get("abuse")

                    if abuse_obj is not None and isinstance(abuse_obj, dict):
                        ip_geolocation["abuse.route"] = abuse_obj.get("route", "")
                        ip_geolocation["abuse.country"] = abuse_obj.get("country_code", "")

                        abuse_name_obj = abuse_obj.get("name")

                        ip_geolocation["abuse.name"] = abuse_name_obj.get("en", "") \
                            if abuse_name_obj is not None and isinstance(abuse_name_obj, dict) else ""
                            
                        ip_geolocation["abuse.organization"] = abuse_obj.get("organization", "")
                        ip_geolocation["abuse.kind"] = abuse_obj.get("kind", "")
                        ip_geolocation["abuse.address"] = abuse_obj.get("address", "")
                        ip_geolocation["abuse.emails"] = abuse_obj.get("emails", "")
                        ip_geolocation["abuse.phone_numbers"] = abuse_obj.get("phone_numbers", "")

                whois_obj = mmdb_response.get("whois")

                if whois_obj is not None and isinstance(whois_obj, dict):
                    ip_geolocation["whois.name"] = whois_obj.get("name", "")
                    ip_geolocation["whois.country"] = whois_obj.get("country", "")
                    ip_geolocation["whois.domain"] = whois_obj.get("domain", "")
                    ip_geolocation["whois.date_created"] = whois_obj.get("date_created", "")
                    ip_geolocation["whois.date_updated"] = whois_obj.get("date_updated", "")
                    ip_geolocation["whois.rir"] = whois_obj.get("rir", "")

                    i = 1
                    irt_handles = whois_obj.get("irt_handles", [])

                    for irt in irt_handles:
                        ip_geolocation["whois.irt_{}.handle".format(i)] = irt.get("handle", "")
                        ip_geolocation["whois.irt_{}.name".format(i)] = irt.get("name", "")
                        ip_geolocation["whois.irt_{}.address".format(i)] = irt.get("address", "")
                        ip_geolocation["whois.irt_{}.country".format(i)] = irt.get("country", "")
                        ip_geolocation["whois.irt_{}.email".format(i)] = irt.get("email", "")
                        ip_geolocation["whois.irt_{}.phone".format(i)] = irt.get("phone", "")
                        ip_geolocation["whois.irt_{}.fax".format(i)] = irt.get("fax", "")
                        ip_geolocation["whois.irt_{}.date_updated".format(i)] = irt.get("date_updated", "")
                        ip_geolocation["whois.irt_{}.source".format(i)] = irt.get("source", "")
                        i += 1

                    i = 1
                    admin_handles = whois_obj.get("admin_handles", [])

                    for admin in admin_handles:
                        ip_geolocation["whois.admin_{}.handle".format(i)] = admin.get("handle", "")
                        ip_geolocation["whois.admin_{}.name".format(i)] = admin.get("name", "")
                        ip_geolocation["whois.admin_{}.address".format(i)] = admin.get("address", "")
                        ip_geolocation["whois.admin_{}.country".format(i)] = admin.get("country", "")
                        ip_geolocation["whois.admin_{}.email".format(i)] = admin.get("email", "")
                        ip_geolocation["whois.admin_{}.phone".format(i)] = admin.get("phone", "")
                        ip_geolocation["whois.admin_{}.fax".format(i)] = admin.get("fax", "")
                        ip_geolocation["whois.admin_{}.date_updated".format(i)] = admin.get("date_updated", "")
                        ip_geolocation["whois.admin_{}.source".format(i)] = admin.get("source", "")
                        i += 1

                    i = 1
                    abuse_handles = whois_obj.get("abuse_handles", [])

                    for abuse in abuse_handles:
                        ip_geolocation["whois.abuse_{}.handle".format(i)] = abuse.get("handle", "")
                        ip_geolocation["whois.abuse_{}.name".format(i)] = abuse.get("name", "")
                        ip_geolocation["whois.abuse_{}.address".format(i)] = abuse.get("address", "")
                        ip_geolocation["whois.abuse_{}.country".format(i)] = abuse.get("country", "")
                        ip_geolocation["whois.abuse_{}.email".format(i)] = abuse.get("email", "")
                        ip_geolocation["whois.abuse_{}.phone".format(i)] = abuse.get("phone", "")
                        ip_geolocation["whois.abuse_{}.fax".format(i)] = abuse.get("fax", "")
                        ip_geolocation["whois.abuse_{}.date_updated".format(i)] = abuse.get("date_updated", "")
                        ip_geolocation["whois.abuse_{}.source".format(i)] = abuse.get("source", "")
                        i += 1

                    i = 1
                    tech_handles = whois_obj.get("tech_handles", [])

                    for tech in tech_handles:
                        ip_geolocation["whois.tech_{}.handle".format(i)] = tech.get("handle", "")
                        ip_geolocation["whois.tech_{}.name".format(i)] = tech.get("name", "")
                        ip_geolocation["whois.tech_{}.address".format(i)] = tech.get("address", "")
                        ip_geolocation["whois.tech_{}.country".format(i)] = tech.get("country", "")
                        ip_geolocation["whois.tech_{}.email".format(i)] = tech.get("email", "")
                        ip_geolocation["whois.tech_{}.phone".format(i)] = tech.get("phone", "")
                        ip_geolocation["whois.tech_{}.fax".format(i)] = tech.get("fax", "")
                        ip_geolocation["whois.tech_{}.date_updated".format(i)] = tech.get("date_updated", "")
                        ip_geolocation["whois.tech_{}.source".format(i)] = tech.get("source", "")
                        i += 1

                    organization = whois_obj.get("organization", {})

                    if isinstance(organization, dict):
                        ip_geolocation["whois.organization.handle"] = organization.get("handle", "")
                        ip_geolocation["whois.organization.name"] = organization.get("name", "")
                        ip_geolocation["whois.organization.address"] = organization.get("address", "")
                        ip_geolocation["whois.organization.country"] = organization.get("country", "")
                        ip_geolocation["whois.organization.email"] = organization.get("email", "")
                        ip_geolocation["whois.organization.phone"] = organization.get("phone", "")
                        ip_geolocation["whois.organization.fax"] = organization.get("fax", "")
                        ip_geolocation["whois.organization.type"] = organization.get("type", "")
                        ip_geolocation["whois.organization.date_updated"] = organization.get("date_updated", "")
                        ip_geolocation["whois.organization.source"] = organization.get("source", "")

                    ip_geolocation["whois.raw_whois"] = whois_obj.get("raw_whois", "")

                ip_geolocations[ip] = ip_geolocation
    except Exception as e:
        object.write_warning(
            "Error during fetching data from IP MMDB lookup. Check $SPLUNK_HOME/var/log/splunk/ipgeolocation/ipgeolocation.log file for troubleshooting"
        )
        logger.error(e)
        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
        ip_geolocations = dict()

    return ip_geolocations


def read_security_mmdb(object, mmdb_reader, ip_address_list, lookup_security):
    ip_securities = dict()

    if lookup_security is False and (
            db_sec_pro_ip_security_enabled or db_sec_pro_ip_hosting_enabled or db_sec_pro_ip_residential_proxy_enabled):
        lookup_security = True

    try:
        for ip in ip_address_list:
            ip = ip.strip()

            if lookup_security:
                mmdb_response = mmdb_reader.get(ip)

                if mmdb_response is not None and isinstance(mmdb_response, dict):
                    ip_security = dict()
                    ip_security["ip"] = ip

                    if db_sec_pro_ip_security_enabled \
                            or db_sec_pro_ip_city_security_enabled \
                            or db_sec_pro_ip_city_isp_security_enabled:
                                
                # -------------------------- v2 Fields -------------------------- #
                        # ip_security["security.threat_score"] = mmdb_response.get("threat_score", 0)
                        # ip_security["security.is_tor"] = mmdb_response.get("is_tor", False)
                        # ip_security["security.is_proxy"] = mmdb_response.get("is_proxy", False)
                        # ip_security["security.proxy_type"] = mmdb_response.get("proxy_type", False)
                        # ip_security["security.proxy_provider"] = mmdb_response.get("proxy_provider", False)
                        # ip_security["security.is_anonymous"] = mmdb_response.get("is_anonymous", False)
                        # ip_security["security.is_known_attacker"] = mmdb_response.get("is_known_attacker", False)
                        # ip_security["security.is_spam"] = mmdb_response.get("is_spam", False)
                        # ip_security["security.is_bot"] = mmdb_response.get("is_bot", False)
                        # ip_security["security.is_cloud_provider"] = mmdb_response.get("is_cloud_provider", False)
                        # ip_security["security.cloud_provider"] = mmdb_response.get("cloud_provider", False)
                        
                # -------------------------------- v3 Security Fields now ------------------------------- #
                        ip_security["security.threat_score"] = mmdb_response.get("threat_score", 0)
                        ip_security["security.is_residential_proxy"] = mmdb_response.get("is_residential_proxy", False)
                        ip_security["security.is_vpn"] = mmdb_response.get("is_vpn", False)
                        ip_security["security.is_relay"] = mmdb_response.get("is_relay", False)
                        ip_security["security.relay_provider_name"] = mmdb_response.get("relay_provider_name", False)
                        ip_security["proxy_confidence_score"] = mmdb_response.get("proxy_confidence_score", 0)
                        ip_security["vpn_confidence_score"] = mmdb_response.get("vpn_confidence_score", 0)
                        ip_security["proxy_last_seen"] = mmdb_response.get("proxy_last_seen", "")
                        ip_security["vpn_last_seen"] = mmdb_response.get("vpn_last_seen", "")
                        ip_security["vpn_provider_names"] = ", ".join(mmdb_response.get("vpn_provider_names", []))
                        ip_security["proxy_provider_names"] = ", ".join(mmdb_response.get("proxy_provider_names", []))
                        ip_security["security.is_tor"] = mmdb_response.get("is_tor", False)
                        ip_security["security.is_proxy"] = mmdb_response.get("is_proxy", False)
                        ip_security["security.is_anonymous"] = mmdb_response.get("is_anonymous", False)
                        ip_security["security.is_known_attacker"] = mmdb_response.get("is_known_attacker", False)
                        ip_security["security.is_spam"] = mmdb_response.get("is_spam", False)
                        ip_security["security.is_bot"] = mmdb_response.get("is_bot", False)
                        ip_security["security.is_cloud_provider"] = mmdb_response.get("is_cloud_provider", False)
                        ip_security["security.cloud_provider_name"] = mmdb_response.get("cloud_provider_name", False)

                    if db_sec_pro_ip_hosting_enabled:
                        ip_security["security.hosting_provider"] = mmdb_response.get("hosting_provider", "")

                    if db_sec_pro_ip_residential_proxy_enabled:
                        ip_security["security.residential_proxy.provider"] = mmdb_response.get("proxy_provider", "")
                        ip_security["security.residential_proxy.last_seen"] = mmdb_response.get("last_seen", "")

                    ip_securities[ip] = ip_security
                    
                    logger.info("Fetched Security Data is" + str(ip_securities))
    except Exception as e:
        object.write_warning(
            "Error During Fetching Data from Security MMDB Lookup. Check $SPLUNK_HOME/var/log/splunk/ipgeolocation/ipgeolocation.log file for troubleshooting"
        )
        logger.error(e)
        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
        ip_securities = dict()

    return ip_securities


def merge_mmdb_responses(mmdb_response1: dict, mmdb_response2: dict):
    for ip, value in mmdb_response2.items():
        if ip in mmdb_response1:
            r1 = mmdb_response1[ip]
            r1.update(value)
            mmdb_response1[ip] = r1
        else:
            mmdb_response1[ip] = value

    return mmdb_response1

