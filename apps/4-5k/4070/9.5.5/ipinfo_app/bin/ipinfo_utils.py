import json
import os
from glob import glob
from urllib.parse import urlparse

import requests
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
import splunk.clilib.cli_common as scc

import splunklib.binding as binding
import splunklib.client as client
from ipinfo.bearer_token import create_bearer_token
from ipinfo.logging import get_logger


try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

logger = get_logger(__file__)
splunkd_uri = scc.getMgmtUri()


def get_management_uri():
    return splunkd_uri


def get_service(target_uri, bearer_token):
    connectionHandler = binding.handler(timeout=30)

    parsed_target = urlparse(target_uri)
    logger.debug("Creating service connection to %s:%s", parsed_target.hostname, parsed_target.port)
    service = client.connect(
        host=parsed_target.hostname, port=parsed_target.port, splunkToken=bearer_token, handler=connectionHandler, autologin=True
    )
    logger.debug("Service connection established")
    return service


def get_service_from_session_key(target_uri, session_key):
    parsed_target = urlparse(target_uri)
    logger.debug("Creating service connection from session key to %s:%s", parsed_target.hostname, parsed_target.port)
    service = client.connect(host=parsed_target.hostname, port=parsed_target.port, token=session_key, autologin=True)
    logger.debug("Service connection established from session key")
    return service


def fillnull():
    """
    Create a dictionary with all IPinfo fields set to empty strings.

    Used as fallback data when IP lookups fail or return no results,
    ensuring all expected fields are present in the output record.

    Returns:
        dict: Dictionary containing all IPinfo field names with empty string values
    """
    return {
        "ip": "",
        "city": "",
        "city_confidence": "",
        "region": "",
        "country": "",
        "country_name": "",
        "country_confidence": "",
        "loc": "",
        "lat": "",
        "lon": "",
        "hostname": "",
        "postal": "",
        "org": "",
        "region_code": "",
        "region_confidence": "",
        "timezone": "",
        "geoname_id": "",
        "asn_asn": "",
        "asn_name": "",
        "asn_domain": "",
        "asn_route": "",
        "asn_type": "",
        "abuse_address": "",
        "abuse_country": "",
        "abuse_email": "",
        "abuse_name": "",
        "abuse_network": "",
        "abuse_phone": "",
        "company_name": "",
        "company_domain": "",
        "company_type": "",
        "carrier_name": "",
        "carrier_mcc": "",
        "carrier_mnc": "",
        "carrier_cc": "",
        "carrier_network": "",
        "anycast": "",
        "census": "",
        "census_port": "",
        "device_activity": "",
        "hosting": "",
        "network": "",
        "proxy": "",
        "relay": "",
        "vpn": "",
        "tor": "",
        "service": "",
        "vpn_config": "",
        "vpn_name": "",
        "whois": "",
        "total_domains": "",
        "domains": "",
        "country_asn_domain": "",
        "country_asn_name": "",
        "country_asn_asn": "",
        "country_continent": "",
        "country_continent_name": "",
        "country_country": "",
        "country_country_name": "",
        "resproxy_last_seen": "",
        "resproxy_percent_days_seen": "",
        "resproxy_service": "",
    }


def get_config(parameter):
    # This function is only for getting custom config file ip_info_setup.conf
    local_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "local", "ip_info_setup.conf"])
    default_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "default", "ip_info_setup.conf"])
    config = ConfigParser()
    with open(default_conf, "r", encoding="utf-8-sig") as default_file:
        config.read_file(default_file)
    if os.path.exists(local_conf):
        with open(local_conf, "r", encoding="utf-8-sig") as local_file:
            config.read_file(local_file)
    try:
        logger.debug("Retrieving configuration parameter: %s", parameter)
        ipinfo_searchpeer = [
            filename
            for filename in glob(
                splunk_lib_util.make_splunkhome_path(["var", "run", "searchpeers", "*", "apps", "ipinfo_app", "local", "ip_info_setup.conf"]),
                recursive=True,
            )
        ]
        local_conf = ""
        default_conf = ""
        parameter_value = ""
        if len(ipinfo_searchpeer) > 0:
            logger.debug("Found %d search peer config files", len(ipinfo_searchpeer))
            local_conf = max(
                [
                    filename
                    for filename in glob(
                        splunk_lib_util.make_splunkhome_path(
                            ["var", "run", "searchpeers", "*", "apps", "ipinfo_app", "local", "ip_info_setup.conf"]
                        ),
                        recursive=True,
                    )
                ],
                key=os.path.getmtime,
            )
            default_conf = max(
                [
                    filename
                    for filename in glob(
                        splunk_lib_util.make_splunkhome_path(
                            ["var", "run", "searchpeers", "*", "apps", "ipinfo_app", "default", "ip_info_setup.conf"]
                        ),
                        recursive=True,
                    )
                ],
                key=os.path.getmtime,
            )
        else:
            logger.debug("Using default local configuration paths")
            local_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "local", "ip_info_setup.conf"])
            default_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "default", "ip_info_setup.conf"])

        config = ConfigParser()
        with open(default_conf, "r", encoding="utf-8-sig") as default_file:
            config.read_file(default_file)
        if os.path.exists(local_conf):
            with open(local_conf, "r", encoding="utf-8-sig") as local_file:
                config.read_file(local_file)
        parameter_value = config.get("ip_info_configuration", parameter)
        logger.debug("Retrieved parameter %s value: %s", parameter, parameter_value)
        return parameter_value
    except Exception as e:
        logger.error(e)
        logger.error("Error while reading from Ipinfo_setup.conf file.")
        logger.error("Exception: %s", str(e))
        return ""


def mmdb_usage(
    ext_label_iplocation_reader,
    ext_iplocation_reader,
    iplocation_reader,
    asn_reader,
    company_reader,
    carrier_reader,
    ext_privacy_reader,
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
    ip_counter,
    session_key,
):
    logger.debug("Updating MMDB usage counters: ip_counter=%d, lookback=%s", ip_counter, resproxy_lookback)
    try:
        # Get KV collection
        kv_store_endpoint = splunkd_uri + "/servicesNS/nobody/ipinfo_app/storage/collections/data/mmdb_collection"
        headers = {"Authorization": "Splunk " + session_key, "Content-Type": "application/json"}
        logger.debug("Fetching current MMDB usage from KV store")
        response = requests.get(kv_store_endpoint, headers=headers, verify=False)
        if response.status_code == 200:
            json_data = response.json()
            if json_data:
                collection_id = json_data[0]["_key"]
                existing_counts = json_data[0]
                logger.debug("Found existing collection record")
            else:
                collection_id = {}
                existing_counts = {}
                logger.debug("No existing collection records found")
        # Update the counts in the KV store
        update_data = {
            # The bundles are never updated in this function, though must still be present
            # since they're part of the KVStores collection schema.
            # If they're not here the data is not going to be shown correctly to the users.
            "ipinfo_lite": existing_counts.get("ipinfo_lite", 0),
            "ipinfo_core": existing_counts.get("ipinfo_core", 0),
            "ipinfo_plus": existing_counts.get("ipinfo_plus", 0),
            "ext_label_iplocation": existing_counts.get("ext_label_iplocation", 0) + (ip_counter if ext_label_iplocation_reader else 0),
            "ext_iplocation": existing_counts.get("ext_iplocation", 0) + (ip_counter if ext_iplocation_reader else 0),
            "iplocation": existing_counts.get("iplocation", 0) + (ip_counter if iplocation_reader else 0),
            "asn": existing_counts.get("asn", 0) + (ip_counter if asn and asn_reader else 0),
            "carrier": existing_counts.get("carrier", 0) + (ip_counter if carrier and carrier_reader else 0),
            "company": existing_counts.get("company", 0) + (ip_counter if company and company_reader else 0),
            "ext_privacy": existing_counts.get("ext_privacy", 0) + (ip_counter if privacy and ext_privacy_reader else 0),
            "privacy": existing_counts.get("privacy", 0) + (ip_counter if privacy and privacy_reader else 0),
            "privacy_extended": existing_counts.get("privacy_extended", 0) + (ip_counter if privacy and privacy_extended_reader else 0),
            "domains": existing_counts.get("domains", 0) + (ip_counter if domains and domains_reader else 0),
            "abuse": existing_counts.get("abuse", 0) + (ip_counter if abuse and abuse_reader else 0),
            "country_asn": existing_counts.get("country_asn", 0) + (ip_counter if country_asn and country_asn_reader else 0),
            "resproxy_30d": existing_counts.get("resproxy_30d", 0)
            + (ip_counter if resproxy and resproxy_reader and resproxy_lookback == "30" else 0),
            "resproxy_7d": existing_counts.get("resproxy_7d", 0)
            + (ip_counter if resproxy and resproxy_reader and resproxy_lookback == "7" else 0),
        }

        if not collection_id:
            update_endpoint = kv_store_endpoint
        else:
            update_endpoint = kv_store_endpoint + f"/{collection_id}"
        logger.debug("Posting updated MMDB counts")
        update_response = requests.post(update_endpoint, headers=headers, json=update_data, verify=False)
        update_response.raise_for_status()
        logger.info("MMDB usage counters updated successfully")
    except Exception as e:
        logger.error("Error updating MMDB counters in the KV store: %s", e)


def post_message(session_key, name, value, severity):
    # Post message on splunk bulletin message tab
    logger.debug("Posting message: name=%s, severity=%s", name, severity)
    message = {
        "name": name,
        "value": value,
        "severity": severity,
    }
    url = splunkd_uri + "/services/messages/new"
    headers = {"Authorization": "Splunk " + session_key}
    disable_splunk_local_ssl_request = False
    response = requests.request("POST", url, headers=headers, data=message, verify=disable_splunk_local_ssl_request)
    if response.status_code == 201:
        logger.info("Message posted successfully.")
    else:
        logger.warning("Failed to post message. Error: %s", response.text)
    return response


def get_shcluster_current_mgmt_uri(session_key):
    # Get current Search head managment uri
    logger.debug("Retrieving current search head cluster management URI")
    response = ""
    url = splunkd_uri + "/servicesNS/admin/search/search/jobs"
    data = {
        "search": "| rest /servicesNS/-/-/configs/conf-server splunk_server=local| search title=shclustering| table mgmt_uri title splunk_server | dedup splunk_server",
        "exec_mode": "oneshot",
        "output_mode": "json",
    }
    headers = {
        "Authorization": "Splunk " + session_key,
        "Content-Type": "application/json",
    }

    disable_splunk_local_ssl_request = False
    response = requests.request("POST", url, headers=headers, verify=disable_splunk_local_ssl_request, data=data)

    current_mgmt_uri = ""
    if response.status_code == 200:
        response_json = response.json()
        results = response_json.get("results")
        current_mgmt_uri = results[0].get("mgmt_uri")
        logger.debug("Retrieved current management URI: %s", current_mgmt_uri)
    else:
        logger.warning("Failed to retrieve search head cluster status: status=%d", response.status_code)

    return current_mgmt_uri


def get_shcluster_members(session_key, current_mgmt_uri):
    # Get managment uri of all search heads in serach head cluster
    logger.debug("Retrieving search head cluster members")
    url = splunkd_uri + "/services/shcluster/status?output_mode=json"
    headers = {
        "Authorization": "Splunk " + session_key,
        "Content-Type": "application/json",
    }
    disable_splunk_local_ssl_request = False
    response = requests.request("GET", url, headers=headers, verify=disable_splunk_local_ssl_request)
    list_of_peers = []
    if response.status_code == 200:
        response_json = response.json()
        for entry_object in response_json.get("entry"):
            peers = entry_object.get("content").get("peers")
            for key in peers:
                value = peers[key]
                peer = value.get("mgmt_uri")
                if peer == current_mgmt_uri:
                    logger.info("Skipping current peer: %s", peer)
                    continue
                list_of_peers.append(peer)
    else:
        logger.warning("Failed to retrieve search head cluster status: status=%d", response.status_code)
    logger.debug("Retrieved %d cluster members", len(list_of_peers))
    return list_of_peers


def get_bearer_token(session_key, check):
    """
    Get a bearer token for cluster communication.

    Creates a new short-lived token on demand. Tokens are not stored in
    password storage since they're only needed for the duration of MMDB downloads.

    Args:
        session_key: Splunk session key
        check: If True, create a new token if needed

    Returns:
        Bearer token string, or empty string if unable to create one
    """
    logger.debug("Getting bearer token (check=%s)", check)

    if not check:
        return ""

    service = get_service_from_session_key(splunkd_uri, session_key)
    token = create_bearer_token(service)

    if token:
        logger.info("Bearer token created successfully")
        return token

    logger.warning("Failed to create bearer token")
    return ""
