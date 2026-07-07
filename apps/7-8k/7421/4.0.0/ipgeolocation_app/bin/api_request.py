import json
import traceback

import requests
import requests.exceptions

from app_utils import get_logger, get_config

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


logger = get_logger("api_request")


def query_ipgeolocation_api(
        object,
        splunk_lib_util,
        ip_addresses: list,
        lookup_live_hostname: bool,
        lookup_hostname_fallback_live: bool,
        lookup_dma: bool,
        lookup_security: bool,
        lookup_abuse_contact: bool,
        lookup_geo_accuracy: bool,
        language: str
):
    response = None

    local_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "local", "ipgeolocation_setup.conf"])
    default_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "default", "ipgeolocation_setup.conf"])
    config = ConfigParser()

    with open(default_conf, "r", encoding="utf-8-sig") as default_file, open(local_conf, "r", encoding="utf-8-sig") as local_file:
        config.read_file(default_file)
        config.read_file(local_file)

    # api_url = config.get("ipgeolocation_configuration", "api_url")
    proxy_enable = config.get("ipgeolocation_configuration", "proxy_enable")
    proxy_host = ""
    proxy_password = ""
    proxy_username = ""
    proxy_type = ""
    proxy_port = ""
    api_subscription_plan = config.get("ipgeolocation_configuration", "api_subscription_plan")

    if proxy_enable == "Yes":
        proxy_host = config.get("ipgeolocation_configuration", "proxy_host")
        proxy_port = config.get("ipgeolocation_configuration", "proxy_port")
        proxy_username = config.get("ipgeolocation_configuration", "proxy_username", fallback="")
        proxy_type = config.get("ipgeolocation_configuration", "proxy_type")

    api_key = ""
    storage_passwords = object.service.storage_passwords

    for storage_password in storage_passwords.list():
        if storage_password.content.username == "proxy_password" and storage_password.content.realm == "ipgeolocation":
            proxy_password = storage_password.content.clear_password
        if storage_password.content.username == "api_key" and storage_password.content.realm == "ipgeolocation":
            api_key = storage_password.content.clear_password

    if api_key != "":
        if language is None or language not in ["en", "de", "ru", "ja", "fr", "cn", "es", "cs", "it", "ko", "fa", "pt"]:
            language = "en"

        url = f"https://api.ipgeolocation.io/v3/ipgeo-bulk"
        method = "POST"
        params = dict()

        if api_subscription_plan == "PAID":
            params["lang"] = language
            if lookup_dma:
                if "include" in params:
                    current_include = params.get("include")

                    params.update({
                        "include": f"{current_include},dma_code"
                    })
                else:
                    params.update({
                        "include": "dma_code"
                    })

            if lookup_abuse_contact:
                if "include" in params:
                    current_include = params.get("include")

                    params.update({
                        "include": f"{current_include},abuse"
                    })
                else:
                    params.update({
                        "include": "abuse"
                    })

            if lookup_geo_accuracy:
                if "include" in params:
                    current_include = params.get("include")

                    params.update({
                        "include": f"{current_include},geo_accuracy"
                    })
                else:
                    params.update({
                        "include": "geo_accuracy"
                    })

            if lookup_security:
                if "include" in params:
                    current_include = params.get("include")

                    params.update({
                        "include": f"{current_include},security"
                    })
                else:
                    params.update({
                        "include": "security"
                    })

            hostname_lookup_param = "liveHostname" if lookup_live_hostname else "hostnameFallbackLive" if lookup_hostname_fallback_live else None

            if hostname_lookup_param is not None:
                if "include" in params:
                    current_include = params.get("include")

                    params.update({
                        "include": f"{current_include},{hostname_lookup_param}"
                    })
                else:
                    params.update({
                        "include": hostname_lookup_param
                    })
            
        
        data = json.dumps({"ips": ip_addresses})
        headers = {
            "User-Agent": "IPGeolocationApp/Splunk/2.0.5",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-IPGeolocation-API-Key": api_key
        }
        proxies = {}

        try:
            if proxy_enable == "Yes":
                try:
                    proxy_port = int(proxy_port)
                except:
                    raise ValueError("Port is not an integer")

                proxy_url = "{}://{}:{}".format(proxy_type, proxy_host, proxy_port)

                if proxy_username:
                    logger.debug("Connecting Proxy with Authentication")
                    proxy_url = "{}://{}:{}@{}:{}".format(proxy_type, proxy_username, proxy_password, proxy_host, proxy_port)

                proxies = { proxy_type.lower(): proxy_url }

            response = requests.request(method=method, url=url, params=params, data=data, headers=headers, proxies=proxies)
            response.raise_for_status()
        except requests.exceptions.HTTPError as he:
            object.write_warning(f"Error during lookup from ipgeolocation.io API. Check ipgeolocation.log file for more information.")
            logger.error(f"ipgeolocation.io API response error: status_code = {response.status_code}, json = {response.json()}")
            response = None
        except Exception as e:
            object.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
            logger.error(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
    else:
        object.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
        logger.error("You might don't have access to retrive API key or API key is not set yet.")

    return response


def query_ipsecurity_api(
        object,
        splunk_lib_util,
        ip_addresses: list,
):
    local_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "local", "ipgeolocation_setup.conf"])
    default_conf = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "default", "ipgeolocation_setup.conf"])
    config = ConfigParser()

    with open(default_conf, "r", encoding="utf-8-sig") as default_file, open(local_conf, "r", encoding="utf-8-sig") as local_file:
        config.read_file(default_file)
        config.read_file(local_file)

    # api_url = config.get("ipgeolocation_configuration", "api_url")
    proxy_enable = config.get("ipgeolocation_configuration", "proxy_enable")
    proxy_host = ""
    proxy_password = ""
    proxy_username = ""
    proxy_type = ""
    proxy_port = ""

    if proxy_enable == "Yes":
        proxy_host = config.get("ipgeolocation_configuration", "proxy_host")
        proxy_port = config.get("ipgeolocation_configuration", "proxy_port")
        proxy_username = config.get("ipgeolocation_configuration", "proxy_username", fallback="")
        proxy_type = config.get("ipgeolocation_configuration", "proxy_type")

    api_key = ""
    storage_passwords = object.service.storage_passwords

    for storage_password in storage_passwords.list():
        if storage_password.content.username == "proxy_password" and storage_password.content.realm == "ipgeolocation":
            proxy_password = storage_password.content.clear_password
        if storage_password.content.username == "api_key" and storage_password.content.realm == "ipgeolocation":
            api_key = storage_password.content.clear_password

    response = None

    if api_key != "":
       
        url = f"https://api.ipgeolocation.io/v3/security-bulk"
        method = "POST"
        params = dict()

        data = json.dumps({"ips": ip_addresses})
        headers = {
            "User-Agent": "IPGeolocationApp/Splunk/2.0.5",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-IPGeolocation-API-Key": api_key
        }
        proxies = {}

        try:
            if proxy_enable == "Yes":
                try:
                    proxy_port = int(proxy_port)
                except:
                    raise ValueError("Port is not an integer")

                proxy_url = "{}://{}:{}".format(proxy_type, proxy_host, proxy_port)

                if proxy_username:
                    logger.debug("Connecting Proxy with Authentication")
                    proxy_url = "{}://{}:{}@{}:{}".format(proxy_type, proxy_username, proxy_password, proxy_host, proxy_port)

                proxies = { proxy_type.lower(): proxy_url }

            response = requests.request(method=method, url=url, params=params, data=data, headers=headers, proxies=proxies)
            response.raise_for_status()
        except requests.exceptions.HTTPError as he:
            object.write_warning(f"Error during lookup from ipgeolocation.io API. Check ipgeolocation.log file for more information.")
            logger.error(f"ipgeolocation.io API response error: status_code = {response.status_code}, json = {response.json()}")
            response = None
        except Exception as e:
            object.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
            logger.error(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
    else:
        object.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
        logger.error("You might don't have access to retrieve API key or API key is not set yet.")

    return response
