import logging
import os
import sys
import traceback

# Extra API key
# URLs in use in the app to whitelist

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import maxminddb
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from glob import glob

from logging.handlers import RotatingFileHandler

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


local_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "local", "ipgeolocation_setup.conf"])
default_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "default", "ipgeolocation_setup.conf"])
config = ConfigParser()

with open(default_conf, "r", encoding="utf-8-sig") as default_file, open(local_conf, "r", encoding="utf-8-sig") as local_file:
    config.read_file(default_file)
    config.read_file(local_file)

api_subscription_plan = config.get("ipgeolocation_configuration", "api_subscription_plan")

def get_null_ip_geolocation(lookup_security: bool, lookup_live_hostname: bool, lookup_hostname_fallback_live: bool):
    record = {}
    record["ip"] = ""

    if lookup_live_hostname or lookup_hostname_fallback_live:
        record["hostname"] = ""

    record["continent_code"] = ""
    record["continent_name"] = ""
    record["country_code2"] = ""
    record["country_code3"] = ""
    record["country_name"] = ""
    record["state_prov"] = ""
    record["state_code"] = ""
    record["district"] = ""
    record["city"] = ""
    record["zip_code"] = ""
    record["latitude"] = ""
    record["longitude"] = ""
    record["calling_code"] = ""
    record["country_tld"] = ""
    record["languages"] = ""
    record["geoname_id"] = ""
    record["isp"] = ""
    record["connection_type"] = ""
    record["organization"] = ""
    record["as_number"] = ""
    record["currency_code"] = ""
    record["currency_name"] = ""
    record["currency_symbol"] = ""
    record["time_zone"] = ""

    if lookup_security:
        record["threat_score"] = ""
        record["is_tor"] = ""
        record["is_proxy"] = ""
        record["proxy_type"] = ""
        record["is_anonymous"] = ""
        record["is_known_attacker"] = ""
        record["is_spam"] = ""
        record["is_bot"] = ""
        record["is_cloud_provider"] = ""

    return record


def get_null_ip_geolocation_for_api(
        lookup_live_hostname: bool,
        lookup_hostname_fallback_live: bool,
        lookup_dma: bool,
        lookup_security: bool,
        lookup_abuse_contact: bool,
        lookup_geo_accuracy: bool
):
    record = dict()
    record["ip"] = ""

    if lookup_hostname_fallback_live or lookup_live_hostname:
        record["hostname"] = ""

    record.update(__get_null_location(on_paid_plan=api_subscription_plan == "PAID", dma=lookup_dma, geo_accuracy=lookup_geo_accuracy))
    record.update(__get_null_country_metadata())
    record.update(__get_null_asn(on_paid_plan=api_subscription_plan == "PAID"))
    

    if api_subscription_plan == "PAID":
        record.update(__get_null_network())
        record.update(__get_null_company())

    record.update(__get_null_currency())

    if api_subscription_plan == "PAID":
        if lookup_security:
            record.update(__get_null_ip_security())

        if lookup_abuse_contact:
            record.update(__get_null_abuse_contact())

    record.update(__get_null_timezone())

    return record


def get_null_ip_security_for_api(
):
    record = dict()
    record["ip"] = ""

    record.update(__get_null_ip_security())

    return record

def __get_null_location(on_paid_plan: bool, dma: bool, geo_accuracy: bool) -> dict:
    record = dict()

    # location object
    record["location.continent_code"] = ""
    record["location.continent_name"] = ""
    record["location.country_code2"] = ""
    record["location.country_code3"] = ""
    record["location.country_name"] = ""
    record["location.country_name_official"] = ""
    record["location.country_capital"] = ""
    record["location.state_prov"] = ""
    record["location.state_code"] = ""
    record["location.district"] = ""
    record["location.city"] = ""

    if on_paid_plan:
        if geo_accuracy:
            record["location.locality"] = ""
            record["location.accuracy_radius"] = ""
            record["location.confidence"] = ""

        if dma:
            record["location.dma_code"] = ""

    record["location.zipcode"] = ""
    record["location.latitude"] = ""
    record["location.longitude"] = ""
    record["location.is_eu"] = ""
    record["location.country_flag"] = ""
    record["location.geoname_id"] = ""
    record["location.country_emoji"] = ""

    return record

def __get_null_country_metadata() -> dict:
    record = dict()

    # country object
    record["country.calling_code"] = ""
    record["country.tld"] = ""
    record["country.languages"] = ""

    return record

def __get_null_network() -> dict:
    record = dict()

    record["network.connection_type"] = ""
    record["network.route"] = ""
    record["network.is_anycast"] = ""

    return record

def __get_null_asn(on_paid_plan: bool) -> dict:
    record = dict()

    record["asn.as_number"] = ""
    record["asn.organization"] = ""
    record["asn.country"] = ""
    
    if on_paid_plan:
        record["asn.type"] = ""
        record["asn.domain"] = ""
        record["asn.date_allocated"] = ""
        record["asn.rir"] = ""

    return record
def __get_null_currency() -> dict:
    record = dict()

    # currency object
    record["currency.code"] = ""
    record["currency.name"] = ""
    record["currency.symbol"] = ""

    return record

def __get_null_company() -> dict:
    record = dict()

    record["company.name"] = ""
    record["company.type"] = ""
    record["company.domain"] = ""

    return record
def __get_null_ip_security() -> dict:
    record = dict()

    record["security.threat_score"] = ""

    record["security.is_tor"] = ""

    record["security.is_proxy"] = ""

    record["security.proxy_provider_names"] = ", ".join([])

    record["security.proxy_confidence_score"] = ""
    record["security.proxy_last_seen"] = ""

    record["security.is_residential_proxy"] = ""

    record["security.is_vpn"] = ""

    # Convert array -> comma separated string
    record["security.vpn_provider_names"] = ", ".join([])

    record["security.vpn_confidence_score"] = ""

    record["security.vpn_last_seen"] = ""

    record["security.is_relay"] =  ""
    record["security.relay_provider_name"] = ""

    record["security.is_anonymous"] = ""

    record["security.is_known_attacker"] = ""

    record["security.is_bot"] = ""

    record["security.is_spam"] = ""

    record["security.is_cloud_provider"] = ""

    record["security.cloud_provider_name"] = ""

    return record


def __get_null_abuse_contact() -> dict:
    record = dict()

    # abuse object
    record["abuse.route"] = ""
    record["abuse.country"] = ""
    record["abuse.name"] = ""
    record["abuse.organization"] = ""
    record["abuse.kind"] = ""
    record["abuse.address"] = ""
    record["abuse.emails"] = ""
    record["abuse.phone_numbers"] = ""

    return record

def __get_null_timezone() -> dict:
    record = dict()

    # timezone object
    record["timezone.name"] = ""
    record["timezone.offset"] = ""
    record["timezone.offset_with_dst"] = ""
    record["timezone.current_time"] = ""
    record["timezone.current_time_unix"] = ""
    record["timezone.current_tz_abbreviation"] = ""
    record["timezone.current_tz_full_name"] = ""
    record["timezone.standard_tz_abbreviation"] = ""
    record["timezone.standard_tz_full_name"] = ""
    record["timezone.is_dst"] = ""
    record["timezone.dst_savings"] = ""
    record["timezone.dst_exists"] = ""
    record["timezone.dst_tz_abbreviation"] = ""
    record["timezone.dst_tz_full_name"] = ""
    record["timezone.dst_start.utc_time"] = ""
    record["timezone.dst_start.duration"] = ""
    record["timezone.dst_start.gap"] = ""
    record["timezone.dst_start.date_time_after"] = ""
    record["timezone.dst_start.date_time_before"] = ""
    record["timezone.dst_start.overlap"] = ""
    record["timezone.dst_end.utc_time"] = ""
    record["timezone.dst_end.duration"] = ""
    record["timezone.dst_end.gap"] = ""
    record["timezone.dst_end.date_time_after"] = ""
    record["timezone.dst_end.date_time_before"] = ""
    record["timezone.dst_end.overlap"] = ""

    return record


def get_logger(logger_id):
    maxbytes = 200000
    log_path = splunk_lib_util.make_splunkhome_path(["var", "log", "splunk", "ipgeolocation"])

    if not (os.path.isdir(log_path)):
        os.makedirs(log_path)

    handler = RotatingFileHandler(log_path + "/ipgeolocation.log", maxBytes=maxbytes, backupCount=20)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(logger_id)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    return logger


def get_separate_download_status():
    separate_download = 0

    if config.get("ipgeolocation_configuration", "separate_download") == "Yes":
        separate_download = 1
    else:
        separate_download = 0

    return separate_download


def get_current_api_usage(object):
    import requests

    logger = get_logger("get_current_api_usage")
    current_api_usage = 0

    try:
        api_key = ""
        storage_passwords = object.service.storage_passwords

        for storage_password in storage_passwords.list():
            if storage_password.content.username == "api_key" and storage_password.content.realm == "ipgeolocation":
                api_key = storage_password.content.clear_password

        if api_key != "":
            headers = {
                "apiKey": api_key
            }
            current_api_usage_response = requests.get("https://billing.ipgeolocation.io/apiUsage/getApiUsageForApiKey", headers=headers)

            if current_api_usage_response.status_code == requests.codes.ok:
                current_utilization_response_json = current_api_usage_response.json()
                current_api_usage = current_utilization_response_json.get("totalRequestsMadeToday", 0)
            else:
                logger.error("Error while fetching current API usage")
                logger.debug("Below is the response from billing.ipgeolocation.io :")
                logger.debug(f"{current_api_usage_response}")
    except Exception as e:
        logger.error(e)
        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
    
    return current_api_usage


def get_mmdb_lookup_reader(object, mmdb_file_name):
    logger = get_logger("get_mmdb_reader")
    mmdb_file_path = ""
    mmdb_file_reader = None

    try:
        ipgeolocation_searchpeer = [
            file_name
            for file_name in glob(
                splunk_lib_util.make_splunkhome_path(["var", "run", "searchpeers", "*", "apps", "ipgeolocation_app"]),
                recursive=True,
            )
        ]
        
        if len(ipgeolocation_searchpeer) > 0:
            mmdb_file_path = max(
                [
                    file_name
                    for file_name in glob(
                        splunk_lib_util.make_splunkhome_path(
                            [
                                "var",
                                "run",
                                "searchpeers",
                                "*",
                                "apps",
                                "ipgeolocation_app",
                                "lookups",
                                mmdb_file_name + ".mmdb",
                            ]
                        ),
                        recursive=True,
                    )
                ],
                key=os.path.getmtime,
            )
        else:
            mmdb_file_path = splunk_lib_util.make_splunkhome_path(
                ["etc", "apps", "ipgeolocation_app", "lookups", mmdb_file_name + ".mmdb"]
            )
    except Exception as e:
        logger.error(e)
        logger.error("Error while locating MMDB lookup file " + mmdb_file_name)
    

    if os.path.exists(mmdb_file_path):
        try:
            mmdb_file_reader = maxminddb.open_database(mmdb_file_path)
        except Exception as e:
            object.write_warning(
                "Error while opening MMDB lookup file "
                + mmdb_file_name
                + ". Check $SPLUNK_HOME/var/log/splunk/ipgeolocation/ipgeolocation.log file for troubleshooting"
            )
            logger.error(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
    else:
        logger.error(
            "'%s.mmdb' file doesn't exist. Please ensure ipgeolocation.io app is configured or if you have just configured the app, use Manual Refresh Dashboard or wait till next scheduled run." % mmdb_file_name
        )

    return mmdb_file_reader


def get_config(parameter_name):
    logger = get_logger("ipgeolocation_utils.get_config")

    parameter_value = ""

    try:
        ipgeolocation_searchpeer = [
            filename
            for filename in glob(
                splunk_lib_util.make_splunkhome_path(["var", "run", "searchpeers", "*", "apps", "ipgeolocation_app"]),
                recursive=True,
            )
        ]
        local_conf_path = ""
        default_conf_path = ""

        if len(ipgeolocation_searchpeer) > 0:
            local_conf_path = max(
                [
                    file_name
                    for file_name in glob(
                        splunk_lib_util.make_splunkhome_path(
                            ["var", "run", "searchpeers", "*", "apps", "ipgeolocation_app", "local", "ipgeolocation_setup.conf"]
                        ),
                        recursive=True,
                    )
                ],
                key=os.path.getmtime,
            )
            default_conf_path = max(
                [
                    filename
                    for filename in glob(
                        splunk_lib_util.make_splunkhome_path(
                            ["var", "run", "searchpeers", "*", "apps", "ipgeolocation_app", "default", "ipgeolocation_setup.conf"]
                        ),
                        recursive=True,
                    )
                ],
                key=os.path.getmtime,
            )
        else:
            local_conf_path = splunk_lib_util.make_splunkhome_path(
                ["etc", "apps", "ipgeolocation_app", "local", "ipgeolocation_setup.conf"]
            )
            default_conf_path = splunk_lib_util.make_splunkhome_path(
                ["etc", "apps", "ipgeolocation_app", "default", "ipgeolocation_setup.conf"]
            )

        config_parser = ConfigParser()

        with open(default_conf_path, "r", encoding="utf-8-sig") as default_conf_file, \
                open(local_conf_path, "r", encoding="utf-8-sig") as local_conf_file:
            config_parser.read_file(default_conf_file)
            config_parser.read_file(local_conf_file)
        
        parameter_value = config_parser.get("ipgeolocation_configuration", parameter_name)
    except Exception as e:
        logger.error(e)
        logger.error("Error while reading from ipgeolocation_setup.conf file.")

    return parameter_value


def is_indexers():
    indexers = False

    try:
        logger = get_logger("ipgeolocation_utils.is_indexers")
        ipgeolocation_searchpeer = [
            file_name
            for file_name in glob(
                splunk_lib_util.make_splunkhome_path(["var", "run", "searchpeers", "*", "apps", "ipgeolocation_app"]),
                recursive=True,
            )
        ]

        indexers = len(ipgeolocation_searchpeer) > 0
    except Exception as e:
        logger.error(e)
        logger.error("Error while reading from ipgeolocation_setup.conf file.")
    
    return indexers


