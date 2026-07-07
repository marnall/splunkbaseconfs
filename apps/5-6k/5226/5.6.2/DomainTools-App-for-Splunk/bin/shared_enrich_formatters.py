import json

from utils import convert_to_iso_format_date


def dt_value(item, key, default=""):
    """safely get values from Iris Enrich response e.g. {key: {value: <thevalue>} or {key: <thevalue>}"""
    component = item.get(key)

    return component.get("value", default) if isinstance(component, dict) else default


def dt_pop(item, key, default=None):
    """safely get first item from Iris Enrich"""
    return item[key].pop() if key in item and item[key] else default


def format_contact(result, type):
    """map fields from Iris Enrich contact to Splunk columns"""

    contact = result.get("{0}_contact".format(type))
    output = {}
    for field in [
        "city",
        "country",
        "fax",
        "name",
        "org",
        "phone",
        "postal",
        "state",
        "street",
    ]:
        output["en_{0}_contact_{1}".format(type, field)] = dt_value(contact, field)

    email = [x["value"] for x in contact.get("email", [])]
    output["en_{0}_contact_email".format(type)] = email

    return output


def format_ips(result):
    """map fields from Iris Enrich ips to Splunk columns"""
    output = {"en_additional_ips_raw": json.dumps(result["ip"])}

    for count in range(1, 3, 1):
        ip = dt_pop(result, "ip", {})
        output["en_ip_{0}_address".format(count)] = dt_value(ip, "address")
        output["en_ip_{0}_country_code".format(count)] = dt_value(ip, "country_code")
        output["en_ip_{0}_isp".format(count)] = dt_value(ip, "isp")

        asns = [x["value"] for x in ip.get("asn", [])]
        output["en_ip_{0}_asn".format(count)] = asns

    return output


def format_mx(result):
    """map fields from Iris Enrich mx records to Splunk columns"""
    output = {"en_additional_mx_raw": json.dumps(result["mx"])}

    mx = dt_pop(result, "mx", {})
    output["en_mx_1_domain"] = dt_value(mx, "domain")
    output["en_mx_1_host"] = dt_value(mx, "host")
    output["en_mx_1_priority"] = mx.get("priority", "")

    ips = [x["value"] for x in mx.get("ip", [])]
    output["en_mx_1_ip"] = ips

    return output


def format_ns(result):
    """map fields from Iris Enrich ns records to Splunk columns"""
    output = {"en_additional_name_servers_raw": json.dumps(result["name_server"])}

    for count in range(1, 3, 1):
        ns = dt_pop(result, "name_server", {})
        output["en_name_server_{0}_domain".format(count)] = dt_value(ns, "domain")
        output["en_name_server_{0}_host".format(count)] = dt_value(ns, "host")

        ips = [x["value"] for x in ns.get("ip", [])]
        output["en_name_server_{0}_ip".format(count)] = ips

    return output


def format_risk(result):
    """map fields from Iris Enrich risk components to Splunk columns"""
    domain_risk = result["domain_risk"]

    output = {
        "en_risk_score": domain_risk.get("risk_score", ""),
        "en_proximity_score": "",
        "en_threat_profile_type": "",
        "en_threat_profile_malware": "",
        "en_threat_profile_phishing": "",
        "en_threat_profile_spam": "",
        "en_threat_profile_evidence": "",
    }

    component_map = {
        "threat_profile_malware": "en_threat_profile_malware",
        "threat_profile_phishing": "en_threat_profile_phishing",
        "threat_profile_spam": "en_threat_profile_spam",
        "proximity": "en_proximity_score",
    }

    for component in domain_risk["components"]:
        name = component["name"]
        if name in component_map:
            output[component_map[name]] = int(component.get("risk_score"))
        if name == "threat_profile":
            output["en_threat_profile_evidence"] = component.get("evidence")
            output["en_threat_profile_type"] = component.get("threats")

    return output


def format_ssl(result):
    """map fields from Iris Enrich ssl records to Splunk columns"""
    output = {"en_additional_ssl_raw": json.dumps(result["ssl_info"])}

    ssl = dt_pop(result, "ssl_info", {})

    output["en_ssl_info_1_hash"] = dt_value(ssl, "hash")
    output["en_ssl_info_1_organization"] = dt_value(ssl, "organization")
    output["en_ssl_info_1_subject"] = dt_value(ssl, "subject")

    email = [x["value"] for x in ssl.get("email", [])]
    output["en_ssl_email"] = email

    output["en_ssl_info_issuer_common_name"] = dt_value(ssl, "issuer_common_name")
    output["en_ssl_info_common_name"] = dt_value(ssl, "common_name")
    output["en_ssl_info_not_after"] = convert_to_iso_format_date(
        dt_value(ssl, "not_after")
    )
    output["en_ssl_info_not_before"] = convert_to_iso_format_date(
        dt_value(ssl, "not_before")
    )
    output["en_ssl_info_duration"] = dt_value(ssl, "duration")

    alt_names = [x["value"] for x in ssl.get("alt_names", [])]
    output["en_ssl_info_alt_names"] = alt_names

    return output


def format_email(result):
    """map fields from Iris Enrich email records to Splunk columns"""
    whois_email = [x["value"] for x in result.get("additional_whois_email", [])]
    soa_email = [x["value"] for x in result.get("soa_email", [])]
    output = {
        "en_additional_whois_email": whois_email,
        "en_additional_soa_email": soa_email,
    }

    return output


def format_tags(result):
    """map fields from Iris Enrich tags to Splunk columns"""
    tags = [x["label"] for x in result.get("tags", [])]

    output = {
        # @todo: add en_iris_tags field when it's available through the dt api
        # @todo: add en_splunk_tags field when it's available through the dt api
        "en_tag": tags,
        "en_tag_raw": json.dumps(result.get("tags", [])),
    }

    return output


def format_top(result):
    """map fields from Iris Enrich top level values to Splunk columns"""
    output = {
        "key": result.get("domain"),
        "en_domain_name": result.get("domain"),
        "en_is_active": result.get("active"),
        "en_adsense_code": dt_value(result, "adsense"),
        "en_google_analytics_code": dt_value(result, "google_analytics"),
        "en_popularity_rank": result.get("popularity_rank", result.get("alexa")),
        "en_domain_create_date": dt_value(result, "create_date"),
        "en_domain_updated_timestamp": result.get("data_updated_timestamp"),
        "en_domain_expiration_date": dt_value(result, "expiration_date"),
        "en_first_seen": dt_value(result, "first_seen"),
        "en_server_type": dt_value(result, "server_type"),
        "en_website_title": dt_value(result, "website_title"),
        "en_tld": result.get("tld"),
        "en_website_response_code": result.get("website_response"),
        "en_redirect_url": dt_value(result, "redirect"),
        "en_registrant_name": dt_value(result, "registrant_name"),
        "en_registrant_org": dt_value(result, "registrant_org"),
        "en_registrar": dt_value(result, "registrar"),
        "en_spf_info": result.get("spf_info"),
    }

    return output


def format_codes(result):
    """map fields from Iris Enrich codes records to Splunk columns"""
    additional_codes_raw = []
    output = {"en_additional_codes_raw": []}

    for field in [
        "ga4",
        "gtm_codes",
        "fb_codes",
        "hotjar_codes",
        "baidu_codes",
        "yandex_codes",
        "matomo_codes",
        "statcounter_project_codes",
        "statcounter_security_codes",
    ]:
        code_values = result.get(field, [])
        if not code_values:
            continue

        additional_codes_raw.append({field: code_values})
        output[f"en_{field}"] = [code_value["value"] for code_value in code_values]

    output["en_additional_codes_raw"] = json.dumps(additional_codes_raw)

    return output


def update_row(row, result):
    row.update(format_contact(result, "admin"))
    row.update(format_contact(result, "billing"))
    row.update(format_contact(result, "technical"))
    row.update(format_contact(result, "registrant"))
    row.update(format_ips(result))
    row.update(format_mx(result))
    row.update(format_ns(result))
    row.update(format_risk(result))
    row.update(format_ssl(result))
    row.update(format_email(result))
    row.update(format_tags(result))
    row.update(format_codes(result))
    row.update(format_top(result))
