import datetime
import os
import traceback
import zipfile

import requests

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
import splunk.clilib.cli_common as scc

from shutil import copyfileobj

from app_utils import get_logger


try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

logger = get_logger("download_mmdb")


def download_mmdb_file(session_key, bearer_token, database_name):
    mmdb_databases = dict()
    mmdb_databases["db_std_ip_country"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-std/ip-country?format=mmdb",
        "files": [
            "db-ip-country.mmdb"
        ]
    }
    mmdb_databases["db_std_ip_city"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-std/ip-city?format=mmdb",
        "files": [
            "db-ip-location.mmdb"
        ]
    }
    mmdb_databases["db_std_ip_isp"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-std/ip-isp?format=mmdb",
        "files": [
            "db-ip-isp.mmdb"
        ]
    }
    mmdb_databases["db_std_ip_city_isp"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-std/ip-city-isp?format=mmdb",
        "files": [
            "db-ip-city-isp.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_abuse"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-abuse?format=mmdb",
        "files": [
            "db-ip-abuse.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_asn_ext"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-asn-ext?format=mmdb",
        "files": [
            "db-ip-asn.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_asn"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-asn?format=mmdb",
        "files": [
            "db-ip-asn.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_city_company_asn_abuse"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-city-company-asn-abuse?format=mmdb",
        "files": [
            "db-ip-city-company-asn-abuse.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_city_company_asn"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-city-company-asn?format=mmdb",
        "files": [
            "db-ip-city-company-asn.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_city"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-city?format=mmdb",
        "files": [
            "db-ip-location.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_company_asn"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-company-asn?format=mmdb",
        "files": [
            "db-ip-company-asn.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_company"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-company?format=mmdb",
        "files": [
            "db-ip-company.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_whois"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-whois?format=mmdb",
        "files": [
            "db-ip-whois.mmdb"
        ]
    }
    mmdb_databases["db_advanced_ip_city_company_asn_abuse_security"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/geo-max/ip-city-company-asn-abuse-security-v3?format=mmdb",
        "files": [
            "db-ip-city-company-asn-abuse.mmdb",
            "db-ip-security.mmdb"
        ]
    }
    mmdb_databases["db_sec_pro_ip_city_isp_security"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/security-pro/ip-city-isp-security-v3?format=mmdb",
        "files": [
            "db-ip-security.mmdb",
            "db-ip-city-isp.mmdb"
        ]
    }
    mmdb_databases["db_sec_pro_ip_city_security"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/security-pro/ip-city-security-v3?format=mmdb",
        "files": [
            "db-ip-city.mmdb",
            "db-ip-security.mmdb"
        ]
    }
    mmdb_databases["db_sec_pro_ip_hosting"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/security-pro/ip-hosting?format=mmdb",
        "files": [
            "db-ip-hosting.mmdb"
        ]
    }
    mmdb_databases["db_sec_pro_ip_residential_proxy"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/security-pro/ip-residential-proxy?format=mmdb",
        "files": [
            "db-residential-proxy.mmdb"
        ]
    }
    mmdb_databases["db_sec_pro_ip_security"] = {
        "download_url": "https://database.ipgeolocation.io/v2/download/security-pro/ip-security-v3?format=mmdb",
        "files": [
            "db-ip-security.mmdb"
        ]
    }

    selected_mmdb_database = mmdb_databases.get(database_name, None)

    if selected_mmdb_database is None:
        logger.error(f"Selected database version '{database_name}' is not supported or does not exist.")
        return 1

    list_of_files_to_exclude = selected_mmdb_database.get("files", [])

    old_zip_file = "{}.zip".format(database_name)
    new_zip_file = "{}-{}.zip".format(database_name, datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))
    path = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipgeolocation_app", "lookups"])

    for path, folders, files in os.walk(path):
        for file in files:
            if file in list_of_files_to_exclude:
                continue
            elif file.startswith(database_name):
                file_to_remove = os.path.join(path, file)
                os.remove(file_to_remove)
                logger.debug("File Removed: {}".format(file_to_remove))

    splunkd_uri = scc.getMgmtUri()
    headers = {}

    if bearer_token != "":
        headers = {
            "Authorization": "Bearer " + bearer_token,
            "Content-Type": "application/json",
        }
    else:
        headers = {
            "Authorization": "Splunk " + session_key,
            "Content-Type": "application/json",
        }
    url = splunkd_uri + "/services/search/jobs"

    data = {
        "search": "| rest /servicesNS/-/-/storage/passwords splunk_server=local | table realm username clear*",
        "exec_mode": "oneshot",
        "output_mode": "json",
    }

    disable_splunk_local_ssl_request = False
    passwords_response = requests.request("POST", url, headers=headers, verify=disable_splunk_local_ssl_request, data=data)
    passwords_response_json = passwords_response.json()
    passwords_results = passwords_response_json.get("results", [])
    api_key = ""

    for item in passwords_results:
        if item["username"] == "{}_key".format(database_name) and item["realm"] == "ipgeolocation":
            api_key = item["clear_password"]

    if api_key != "":
        local_conf = splunk_lib_util.make_splunkhome_path(
            ["etc", "apps", "ipgeolocation_app", "local", "ipgeolocation_setup.conf"]
        )
        default_conf = splunk_lib_util.make_splunkhome_path(
            ["etc", "apps", "ipgeolocation_app", "default", "ipgeolocation_setup.conf"]
        )
        config = ConfigParser()

        with open(default_conf, "r", encoding="utf-8-sig") as default_file, open(local_conf, "r", encoding="utf-8-sig") as local_file:
            config.read_file(default_file)
            config.read_file(local_file)

        if not os.path.exists(path):
            os.makedirs(path)
        
        old_file_path = os.path.join(path, old_zip_file)
        new_file_path = os.path.join(path, new_zip_file)

        logger.info("Started Downloading the File " + database_name)
        database_download_url = selected_mmdb_database.get("download_url")
        method = "GET"
        proxy_enable = config.get("ipgeolocation_configuration", "proxy_enable")
        proxy_type = ""
        proxy_host = ""
        proxy_port = ""
        proxy_username = ""
        proxy_password = ""
        
        if proxy_enable == "Yes":
            proxy_type = config.get("ipgeolocation_configuration", "proxy_type")
            proxy_host = config.get("ipgeolocation_configuration", "proxy_host")
            proxy_port = config.get("ipgeolocation_configuration", "proxy_port")
            proxy_username = config.get("ipgeolocation_configuration", "proxy_username", fallback="")
        
        for item in passwords_results:
            if item["username"] == "proxy_password" and item["realm"] == "ipgeolocation":
                proxy_password = item["clear_password"]

        try:
            params = {
                "apiKey": api_key
            }
            headers = {
                "User-Agent": "IPGeolocationApp/Splunk/3.0.0"
            }
            proxies = {}

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

            database_download_response = requests.request(method=method, url=database_download_url, params=params, headers=headers, proxies=proxies, stream=True)
            database_download_response.raise_for_status()
            
            with open(new_file_path, "wb") as output_file:
                copyfileobj(database_download_response.raw, output_file)

            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            os.rename(new_file_path, old_file_path)

            with zipfile.ZipFile(old_file_path, "r") as db_zip:
                zip_members = db_zip.namelist()

                for database_file in list_of_files_to_exclude:
                    if database_file in zip_members:
                        db_zip.extract(database_file, path)

                db_zip.close()
            
            logger.info("Files Downloaded Successfully for " + database_name)
            
            return 0
        except Exception as e:
            logger.error("Error while downloading " + database_name)
            logger.error(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

            return 1
    else:
        logger.error("Error while downloading " + database_name)
        logger.error("You might don't have access to retrive API Key or API Key is not set yet.")

        return 1
