from __future__ import annotations

import json
import ssl
import traceback
import urllib.request

from ipinfo.logging import get_logger
from ipinfo.utils import get_config as get_conf, prefix_dict_keys, stringify_bools
from ipinfo_utils import fillnull, get_config


logger = get_logger(__file__)


def get_ipinfo_rest_result(
    self,
    ip_addresses,
    record_list,
    fields,
    asn: bool,
    abuse: bool,
    company: bool,
    carrier: bool,
    privacy: bool,
    domains: bool,
    resproxy: bool,
    prefix: dict[str, str],
):
    logger.debug("Processing %d IP addresses via REST API", len(ip_addresses))
    addresses = json.dumps(ip_addresses)
    list_of_ip_details = {}
    try:
        logger.debug("Making REST request for IP details")
        response = make_rest_request(self, addresses)
        if type(response) is dict and len(response) == 0:
            logger.error("Got Empty Response from make_rest_request")
            return {}

        logger.debug("REST request response received")
        resproxy_response = None
        if resproxy:
            logger.debug("Fetching residential proxy data for %d IPs", len(ip_addresses))
            resproxy_addresses = json.dumps([f"resproxy/{ip}" for ip in ip_addresses])
            resproxy_response = make_rest_request(self, resproxy_addresses)
            if len(resproxy_response) == 0:
                logger.error("Got Empty Residential proxy Response from make_rest_request")
        # If we call make_rest_request with data=None we get back the users features.
        # We use those to understand if the customer has access to privacy extended data, that
        # as of time of this writing is only accessible via the legacy batch API.
        # We don't need to call the legacy batch API if not to retrieve the privacy extended
        # dataset, so we do only if we know they have privacy extended enabled.
        user_features = json.loads(make_rest_request(self, None))
        privacy_extended_enabled = user_features.get("features", {}).get("privacy", {}).get("privacy_extended", False)
        logger.debug("Privacy extended feature is %s", "enable" if privacy_extended_enabled else "disabled")
        privacy_extended_response = None
        if privacy and privacy_extended_enabled:
            logger.debug("Fetch privacy extended data for %d IPs", len(ip_addresses))
            privacy_addresses = json.dumps([f"{ip}/privacy" for ip in ip_addresses])
            privacy_extended_response = make_rest_request(self, privacy_addresses, use_legacy_endpoint=True)
            if len(privacy_extended_response) == 0:
                logger.error("Got empty privacy extended reponse from make_rest_request")

        logger.debug("Parsing REST responses")
        list_of_ip_details = parse_rest_result(
            response, resproxy_response, privacy_extended_response, asn, abuse, company, carrier, privacy, domains, resproxy
        )

    except Exception as e:
        self.write_warning("Error During Fetching Data from ipinfo.io. Check Log Dashboard")
        self.write_warning(str(e))
        logger.error(e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}

    if bool(list_of_ip_details):
        logger.debug("Updating %d records with IP details", len(record_list))
        temp = record_list
        record_list = {}
        for key in temp.keys():
            try:
                record = temp[key]
                for field in fields:
                    if record.get(field):
                        details = list_of_ip_details.get(record.get(field))
                        if details is not None:
                            if prefix:
                                details = prefix_dict_keys(details, prefix[field])
                            record.update(details)
            except Exception as e:
                logger.error(e)
                logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
            yield record
    else:
        logger.warning("No IP details available for records")
        self.write_warning("Some Error Occured. Check Log Dashboard.")
        temp = record_list
        record_list = {}
        for key in temp.keys():
            record = temp[key]
            yield record


def make_rest_request(self, data, *, use_legacy_endpoint=False):
    logger.debug("Preparing REST request")
    proxy_enable = get_config("proxy_enable")
    if proxy_enable == "Yes":
        logger.debug("Proxy is enabled, retrieving proxy configuration")
        proxy_host = get_config("proxy_host")
        proxy_port = get_config("proxy_port")
        proxy_username = get_config("proxy_username")
        proxy_type = get_config("proxy_type")
        proxy_password = get_storage_password(self, "proxy_password")

    url = ""
    token = ""
    token = get_storage_password(self, "token")
    if token != "":
        logger.debug("Token retrieved successfully")
        response = ""
        url = "https://ipinfo.io/batch"
        if use_legacy_endpoint:
            url = "https://api.ipinfo.io/batch/legacy"
        if data == None:
            logger.debug("No data provided, using /me endpoint")
            url = "https://ipinfo.io/me"

        try:
            opener = None
            if proxy_enable == "No":
                logger.debug("Building opener without proxy")
                opener = urllib.request.build_opener()
            else:
                logger.debug("Building opener with proxy")
                try:
                    proxy_port = int(proxy_port)
                except:
                    logger.error("Invalid proxy port, raising ValueError")
                    raise ValueError("Port is not an int")

                proxy_url = "{}://{}:{}".format(proxy_type.lower(), proxy_host, proxy_port)
                if proxy_username:
                    logger.info("Connecting Proxy with Authentication")
                    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                    password_mgr.add_password(None, proxy_url, proxy_username, proxy_password)
                    proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
                    proxy_auth_handler = urllib.request.ProxyBasicAuthHandler(password_mgr)
                    opener = urllib.request.build_opener(proxy_handler, proxy_auth_handler)
                else:
                    logger.info("Connecting Proxy without Authentication")
                    proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
                    opener = urllib.request.build_opener(proxy_handler)

            if data != None:
                data = bytes(data, "utf-8")
                logger.debug("Request data encoded to bytes: %d bytes", len(data))

            opener.addheaders.append(("Authorization", "Bearer " + token))
            opener.addheaders.append(("User-Agent", "IPinfoClient/Splunk/9.5.5"))
            opener.addheaders.append(("Content-Type", "application/json"))
            logger.debug("Request headers configured")
            ca_cert_path = get_conf("ca_cert_path", self.service)
            ssl_context = None
            if ca_cert_path:
                ssl_context = ssl.create_default_context(cafile=ca_cert_path)

            urllib.request.install_opener(opener)
            logger.debug("Making request to: %s", url)
            request = urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(request, context=ssl_context)
            response = response.read().decode()
            logger.info("REST request successful, url: %s", url)
            return response

        except Exception as e:
            self.write_warning("Error During Fetching Data from ipinfo.io. Check Log Dashboard.")
            logger.error("REST request failed: %s", e)
            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
            return {}
    else:
        self.write_warning("Error During Fetching Data from ipinfo.io. Check Log Dashboard.")
        logger.error("You might don't have access to retrive token or token is not set yet.")
        return {}


def get_storage_password(self, username):
    logger.debug("Retrieving storage password for: %s", username)
    storage_passwords = self.service.storage_passwords
    for storage_password in storage_passwords.list():
        if storage_password.content.username == username and storage_password.content.realm == "ipinfo":
            logger.debug("Storage password found for: %s", username)
            return storage_password.content.clear_password
    logger.warning("Storage password not found for: %s", username)
    return None


def parse_rest_result(response, resproxy_response, privacy_extended_response, asn, abuse, company, carrier, privacy, domains, resproxy):
    logger.debug("Parsing REST result response")
    response_result = {}
    try:
        response_json_data = json.loads(response)
        logger.debug("Parsed %d IP records from response", len(response_json_data))
        resproxy_response_json_data = json.loads(resproxy_response) if resproxy_response else {}
        if resproxy_response:
            logger.debug("Parsed %d residential proxy records", len(resproxy_response_json_data))

        privacy_extended_json_data = json.loads(privacy_extended_response) if privacy_extended_response else {}
        if privacy_extended_response:
            logger.debug("Parsed %d privacy extended records", len(privacy_extended_json_data))

        for key, json_data in response_json_data.items():
            result = {}
            if json_data.get("status") not in (404, 403):
                if str(json_data.get("bogon")) != "True":
                    logger.debug("Processing IP: %s", key)
                    result["ip"] = json_data.get("ip", "")
                    result["city"] = json_data.get("city", "")
                    result["region"] = json_data.get("region", "")
                    result["country"] = json_data.get("country", "")
                    result["loc"] = json_data.get("loc", "")
                    result["lat"], result["lon"] = (
                        [float(coord) for coord in json_data.get("loc", "").split(",")] if "loc" in json_data else (None, None)
                    )
                    result["hostname"] = json_data.get("hostname", "")
                    result["postal"] = json_data.get("postal", "")
                    result["org"] = json_data.get("org", "")
                    result["region_code"] = json_data.get("region_code", "")
                    result["timezone"] = json_data.get("timezone", "")

                    if "asn" in json_data and asn:
                        logger.debug("Including ASN data for IP: %s", key)
                        result.update(
                            {
                                "asn_asn": json_data["asn"].get("asn", ""),
                                "asn_name": json_data["asn"].get("name", ""),
                                "asn_domain": json_data["asn"].get("domain", ""),
                                "asn_route": json_data["asn"].get("route", ""),
                                "asn_type": json_data["asn"].get("type", ""),
                            }
                        )
                    elif asn:
                        logger.debug("ASN data not available for IP: %s, filling with empty values", key)
                        result.update({"asn_asn": "", "asn_name": "", "asn_domain": "", "asn_route": "", "asn_type": ""})

                    if "abuse" in json_data and abuse:
                        logger.debug("Including abuse data for IP: %s", key)
                        result.update(
                            {
                                "abuse_address": json_data["abuse"].get("address", ""),
                                "abuse_country": json_data["abuse"].get("country", ""),
                                "abuse_email": json_data["abuse"].get("email", ""),
                                "abuse_name": json_data["abuse"].get("name", ""),
                                "abuse_network": json_data["abuse"].get("network", ""),
                                "abuse_phone": json_data["abuse"].get("phone", ""),
                            }
                        )
                    elif abuse:
                        logger.debug("Abuse data not available for IP: %s, filling with empty values", key)
                        result.update(
                            {
                                "abuse_address": "",
                                "abuse_country": "",
                                "abuse_email": "",
                                "abuse_name": "",
                                "abuse_network": "",
                                "abuse_phone": "",
                            }
                        )

                    if "company" in json_data and company:
                        logger.debug("Including company data for IP: %s", key)
                        result.update(
                            {
                                "company_name": json_data["company"].get("name", ""),
                                "company_domain": json_data["company"].get("domain", ""),
                                "company_type": json_data["company"].get("type", ""),
                            }
                        )
                    elif company:
                        logger.debug("Company data not available for IP: %s, filling with empty values", key)
                        result.update({"company_name": "", "company_domain": "", "company_type": ""})

                    if "carrier" in json_data and carrier:
                        logger.debug("Including carrier data for IP: %s", key)
                        result.update(
                            {
                                "carrier_name": json_data["carrier"].get("name", ""),
                                "carrier_mcc": json_data["carrier"].get("mcc", ""),
                                "carrier_mnc": json_data["carrier"].get("mnc", ""),
                            }
                        )
                    elif carrier:
                        logger.debug("Carrier data not available for IP: %s, filling with empty values", key)
                        result.update({"carrier_name": "", "carrier_mcc": "", "carrier_mnc": ""})

                    if "privacy" in json_data and privacy and not privacy_extended_json_data:
                        logger.debug("Including privacy data for IP: %s", key)
                        privacy_data = json_data["privacy"]
                        result.update(
                            {
                                "vpn": privacy_data.get("vpn", ""),
                                "proxy": privacy_data.get("proxy", ""),
                                "tor": privacy_data.get("tor", ""),
                                "hosting": privacy_data.get("hosting", ""),
                                "relay": privacy_data.get("relay", ""),
                                "service": privacy_data.get("service", ""),
                                "confidence": privacy_data.get("confidence", ""),
                                "coverage": privacy_data.get("coverage", ""),
                                "census": privacy_data.get("census", ""),
                                "census_ports": privacy_data.get("census_ports", ""),
                                "device_activity": privacy_data.get("device_activity", ""),
                                "inferred": privacy_data.get("inferred", ""),
                                "vpn_config": privacy_data.get("vpn_config", ""),
                                "whois": privacy_data.get("whois", ""),
                                "first_seen": privacy_data.get("first_seen", ""),
                                "last_seen": privacy_data.get("last_seen", ""),
                            }
                        )
                    elif privacy and not privacy_extended_json_data:
                        logger.debug("Privacy data not available for IP: %s, filling with empty values", key)
                        result.update(
                            {
                                "vpn": "",
                                "proxy": "",
                                "tor": "",
                                "hosting": "",
                                "relay": "",
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
                        )

                    if "domains" in json_data and domains:
                        logger.debug("Including domains data for IP: %s", key)
                        result.update(
                            {
                                "total_domains": str(json_data["domains"].get("total", "")),
                                "domains": json_data["domains"].get("domains", ""),
                            }
                        )
                    elif domains:
                        logger.debug("Domains data not available for IP: %s, filling with empty values", key)
                        result.update({"total_domains": "", "domains": ""})

                    if resproxy:
                        logger.debug("Including residential proxy data for IP: %s", key)
                        resproxy_data = resproxy_response_json_data.get(f"resproxy/{key}", {})
                        result.update(
                            {
                                "resproxy_last_seen": resproxy_data.get("last_seen", ""),
                                "resproxy_percent_days_seen": resproxy_data.get("percent_days_seen", ""),
                                "resproxy_service": resproxy_data.get("service", ""),
                            }
                        )

                    if privacy_extended_json_data:
                        logger.debug("Including privacy extended data for IP: %s", key)
                        privacy_extended_data = privacy_extended_json_data.get(f"{key}/privacy", {})
                        result.update(
                            {
                                "vpn": privacy_extended_data.get("vpn", ""),
                                "proxy": privacy_extended_data.get("proxy", ""),
                                "tor": privacy_extended_data.get("tor", ""),
                                "relay": privacy_extended_data.get("relay", ""),
                                "hosting": privacy_extended_data.get("hosting", ""),
                                "service": privacy_extended_data.get("service", ""),
                                "confidence": privacy_extended_data.get("confidence", ""),
                                "coverage": privacy_extended_data.get("coverage", ""),
                                "census": privacy_extended_data.get("census", ""),
                                "census_ports": privacy_extended_data.get("census_ports", ""),
                                "device_activity": privacy_extended_data.get("device_activity", ""),
                                "inferred": privacy_extended_data.get("inferred", ""),
                                "vpn_config": privacy_extended_data.get("vpn_config", ""),
                                "whois": privacy_extended_data.get("whois", ""),
                                "first_seen": privacy_extended_data.get("first_seen", ""),
                                "last_seen": privacy_extended_data.get("last_seen", ""),
                            }
                        )

                    response_result[key] = result
                else:
                    logger.debug("IP %s is bogon, filling with null values", key)
                    response_result[key] = fillnull()
                    response_result[key]["ip"] = json_data.get("ip", "")

            if json_data.get("status") == 403:
                if json_data.get("error").get("title"):
                    logger.error("Token is incorrect. Response: %s", str(json_data))
                    return {}

            response_result[key] = result

        logger.debug("Parsed %d results from REST response", len(response_result))
        return {ip: stringify_bools(row) for ip, row in response_result.items()}

    except Exception as e:
        logger.error("Error parsing REST result: %s", e)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return {}
