# Python imports
import ta_threatquotient_add_on_declare
import json
import requests
from requests.auth import HTTPBasicAuth
import os
import base64
import io
import socket
import traceback
from six.moves import configparser
from solnlib.splunkenv import get_splunkd_uri
from requests.compat import quote_plus
from xml.etree.ElementTree import XML
from threatq_const import VERIFY_SSL, VERIFY_SSL_KVSTORE, CERT_FILE_LOC, KEY_FILE_LOC

import logger_manager as log

# Splunk imports
import splunk.entity as entity
import splunk.rest as rest
from solnlib.utils import is_true
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunklib.client as client
import splunk.clilib.cli_common

logger = log.setup_logging("ta_threatquotient_add_on_utils")
APP_NAME = "threatqappforsplunk"

addon_name = "TA-threatquotient-add-on"


def set_log_level(log_level):
    global logger
    logger.setLevel(log_level)


def update_pagination_config(session_key, input_name, pull_all_iocs):
    """Update the pull_all_iocs value in provided input's config.

    Args:
        session_key (str): Splunk session key
        input_name (str): input name
        pull_all_iocs (bool): Flag value indicating way to import data
    """
    input_name = quote_plus("threatq_indicators://{}".format(input_name))

    params = {"output_mode": "json"}
    body = {"pull_all_iocs": pull_all_iocs}

    headers = {
        "Authorization": "Splunk {}".format(session_key),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    requests.post(
        get_splunkd_uri() + "/servicesNS/nobody/" + addon_name + "/configs/conf-inputs/" + input_name,
        headers=headers,
        params=params,
        data=body,
        verify=VERIFY_SSL_KVSTORE
    )


def get_import_timout(session_key):
    """Get server read timeout.

    :param session_key: Splunk session key
    :return: int timeout value
    """
    try:
        params = {"output_mode": "json"}

        headers = {
            "Authorization": "Splunk {}".format(session_key),
            "Content-Type": "application/json",
        }
        content = requests.get(
            get_splunkd_uri() + "/services/configs/conf-ta_threatquotient_add_on_settings/import_timeout",
            headers=headers,
            params=params,
            verify=VERIFY_SSL_KVSTORE
        )

        timeout = int(content.json()["entry"][0]["content"].get("timeout_value"))
        logger.info("import time out value : {}".format(timeout))
        return timeout
    except ValueError:
        logger.error(
            "message=get_import_timeout_value_error |"
            " ThreatQuotient Error: Error parsing the timeout value, timeout value should be an integer."
        )
        logger.info("Proceeding further for the data collection with the default 900 timeout value")
        return 900
    except Exception:
        logger.error(
            "message=get_import_timeout_error |"
            " ThreatQuotient Error: Error while fetching timeout value : {}".format(
                str(traceback.format_exc())
            )
        )
        logger.info("Proceeding further for the data collection with the default 900 timeout value")
        return 900


def wait_for_kvstore(helper, splunkserver, splunk_server_port):
    """Wait for KV store to initialize.

    KVStore is used for storing flag pull_all_iocs which affects the data import technique.

    Raises:
        Exception: when kv store is not in ready state
    """

    def get_status(uri):

        splunk_account_info = get_splunk_credentials(helper.context_meta["session_key"])
        splunk_verify_cert = is_true(VERIFY_SSL_KVSTORE)
        if splunkserver in ["127.0.0.1", "localhost"]:
            splunk_verify_cert = False
        params = {"output_mode": "json"}

        if splunkserver not in ["127.0.0.1", "localhost"]:
            splunk_password = splunk_account_info.get("splunk_password", "")
            splunk_username = splunk_account_info.get("splunk_username", "")
            content = requests.get(
                uri,
                auth=HTTPBasicAuth(splunk_username, splunk_password),
                params=params,
                verify=splunk_verify_cert,
            )
        else:
            headers = {
                "Authorization": "Splunk {}".format(helper.context_meta["session_key"]),
                "Content-Type": "application/json",
            }
            content = requests.get(
                uri,
                headers=headers,
                params=params,
                verify=splunk_verify_cert,
            )
        data = content.json()["entry"]
        return data[0]["content"]["current"].get("status")

    uri = "".join(["https://", splunkserver, ":", splunk_server_port, "/services/kvstore/status"])
    status = get_status(uri)
    if status != "ready":
        if status == "starting":
            raise Exception(
                "KV store is starting. Please try after sometime when its in " "ready state"
            )
        else:
            raise Exception("KV store is not in ready state. Current state: " + str(status))


def validate_existence_of_lookup(helper, session_key):
    try:
        splunkserver = helper.get_global_setting("splunk_rest_host_url") or "localhost"
        splunk_server_port = helper.get_global_setting("splunk_rest_port") or "8089"
        wait_for_kvstore(helper, splunkserver, splunk_server_port)
        kvstore_collections = [
            "master_lookup",
            "threatq_indicator_types",
            "threatq_indicator_status",
        ]
        if splunkserver in ['127.0.0.1', 'localhost']:
            splunk_service = create_service(session_key, splunkserver, splunk_server_port)
        else:
            user_name = helper.get_global_setting("splunk_username")
            pwd = helper.get_global_setting("splunk_password")
            splunk_service = create_service(session_key, splunkserver, splunk_server_port, user_name, pwd)

        # Check if KVStore collection exists
        for destcollection in kvstore_collections:
            if destcollection not in splunk_service.kvstore:
                raise Exception(
                    "KVStore collection {0} not on {1} Splunk instance".format(
                        destcollection, splunkserver
                    )
                )
    except Exception:
        raise Exception(traceback.format_exc())


def get_macro_definition(serviceobj, macro_name):
    """Fetch macro definition."""
    response = serviceobj.get("properties/macros/{}/definition".format(macro_name))
    if response["status"] != 200:
        raise Exception(
            "Got response with status_code={}, response={}".format(
                response["status"], str(response)
            )
        )
    definitaion = str(response["body"].read().decode())
    return definitaion


def get_session_key(helper, session_key=None):
    """Validate the Splunk credentials."""
    try:
        splunkserver = helper.get_global_setting("splunk_rest_host_url") or "localhost"
        if not session_key:
            session_key = helper.context_meta["session_key"]
        splunk_account_info = get_splunk_credentials(session_key)
        splunk_password = splunk_account_info.get("splunk_password", "")
        splunk_username = splunk_account_info.get("splunk_username", "")
        if splunkserver not in ["127.0.0.1", "localhost"] or splunk_password or splunk_username:
            payload = "username={}&password={}".format(
                quote_plus(splunk_username), quote_plus(splunk_password)
            )
            splunk_server_port = splunk_account_info.get("splunk_rest_port") or "8089"
            splunk_verify_cert = is_true(VERIFY_SSL_KVSTORE)
            if splunkserver in ["127.0.0.1", "localhost"]:
                splunk_verify_cert = False
            splunk_url = "".join(
                ["https://", splunkserver, ":", splunk_server_port, "/services/auth/login"]
            )
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            response = requests.post(
                splunk_url,
                headers=headers,
                data=payload,
                verify=splunk_verify_cert,
            )
            session = XML(response.text).findtext("./sessionKey")
            session_key = "%s" % session
            if response.status_code == 401:
                logger.error(
                    " message=get_session_key_response_error | Please check the Splunk KVStore Rest credentials."
                    "| Response code = {} |".format(response.status_code)
                )
                return False
            if not response.status_code == requests.codes.ok:
                logger.error(
                    "message=get_session_key_response_error |"
                    " Error occurred while configuring the Splunk KVStore rest."
                    " Response code = {} Response text = {} |".format(
                        response.status_code, response.text
                    )
                )
                return False
    except requests.exceptions.SSLError as se:
        logger.error(
            "message=get_session_key_ssl_error |"
            " Please verify the SSL certificate for the Splunk KVStore rest configuration : {}".format(
                se
            )
        )
        return False
    except Exception:
        logger.error(
            "message=get_session_key_error |"
            " Error occurred while configuring the Splunk KVStore rest.\nError: {}".format(
                traceback.format_exc()
            )
        )
        return False
    return session_key


def validate_configured_input(session_key):
    """Raise exception when user try to.

    create more than one input from UI
    """
    uri = "/servicesNS/nobody/" + addon_name + "/data/inputs/threatq_indicators/"

    params = {"output_mode": "json"}

    headers = {
        "Authorization": "Splunk {}".format(session_key),
        "Content-Type": "application/json",
    }
    resp = requests.get(
        get_splunkd_uri() + uri,
        headers=headers,
        params=params,
        verify=VERIFY_SSL_KVSTORE,
    )

    if resp.status_code == 200:
        if len(resp.json()["entry"]) > 0:
            logger.error("Only one input is allowed to configure.")
            raise Exception("Only one input is allowed to configure.")
    else:
        logger.error(
            "message=validate_configured_input_error |"
            " Error occured while validating inputs : {}".format(resp)
        )
        raise Exception(resp)


def get_credentials_from_conf_file():
    """Read the credentials from the credentials_storage.conf."""
    account_info = {}
    config = configparser.ConfigParser()
    account_information_conf = os.path.join(
        make_splunkhome_path(["etc", "apps", addon_name, "local", "credentials_storage.conf"])
    )
    if os.path.isfile(account_information_conf):
        with io.open(account_information_conf, "r", encoding="utf_8_sig") as inputconffp:
            config.readfp(inputconffp)
        if config.has_section("credentials"):
            if config.has_option("credentials", "password"):
                account_info["password"] = config.get("credentials", "password")
            account_info["client_id"] = config.get("credentials", "client_id")
            if config.has_option("credentials", "client_secret"):
                account_info["client_secret"] = config.get("credentials", "client_secret")
            account_info["server_url"] = config.get("credentials", "server_url")
            account_info["username"] = config.get("credentials", "username")
            account_info["verify_cert"] = VERIFY_SSL

    return account_info


def get_credentials(session_key, conf_parse=False):
    """Get credentials of Query API.

    :param session_key: Splunk session key
    :return: Dictionary containing config details
    """
    if not conf_parse:
        try:
            # list all credentials
            entities = entity.getEntities(
                ["admin", "passwords"],
                namespace=addon_name,
                owner="nobody",
                sessionKey=session_key,
                count=-1,
                search=addon_name,
            )
        except Exception:
            logger.exception(
                "message=get_credentials_error |"
                "ThreatQuotient Error: Could not get {} credentials from splunk. Error :{}".format(
                    addon_name, traceback.format_exc()
                )
            )
            raise Exception(
                "ThreatQuotient Error: Could not get {} credentials from splunk.".format(addon_name)
            )

        # Collect secrets from credential storage (supports both 'password' and 'client_secret')
        secrets = {}
        for stanza, value in entities.items():
            try:
                cp = value.get("clear_password")
                parsed = json.loads(cp)
                if isinstance(parsed, dict):
                    for k in ("password", "client_secret"):
                        if k in parsed and parsed[k]:
                            secrets[k] = parsed[k]
            except Exception:
                continue
        params = {"output_mode": "json"}
        headers = {
            "Authorization": "Splunk {}".format(session_key),
            "Content-Type": "application/json",
        }
        content = requests.get(
            get_splunkd_uri() + "/servicesNS/nobody/" + addon_name + "/properties/ta_threatquotient_add_on_settings/additional_parameters",  # noqa: E501
            headers=headers,
            params=params,
            verify=VERIFY_SSL_KVSTORE
        )

        response_dict = {}
        if secrets:
            response_dict.update(secrets)

        content = content.json()

        for item in content["entry"]:
            if item["name"] in ("password", "client_secret"):
                continue
            response_dict[item["name"]] = item["content"]

        return response_dict
    else:
        return get_credentials_from_conf_file()


def get_splunk_credentials(session_key):
    """Get credentials of Query API.

    :param session_key: Splunk session key
    :return: Dictionary containing config details
    """
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=addon_name,
            owner="nobody",
            sessionKey=session_key,
            count=-1,
            search=addon_name,
        )
    except Exception:
        logger.exception(
            "message=get_splunk_credentials_error |"
            " ThreatQuotient Error: Could not get {} credentials from "
            "splunk.".format(addon_name)
        )
        raise Exception(
            "ThreatQuotient Error: Could not get {} credentials from " "splunk.".format(addon_name)
        )

    clear_password = None
    response_dict = {}
    for stanza, value in entities.items():
        try:
            password = value["clear_password"]
            password = json.loads(password)
            clear_password = password["splunk_password"]
            break
        except Exception:
            continue

    params = {"output_mode": "json"}
    headers = {
        "Authorization": "Splunk {}".format(session_key),
        "Content-Type": "application/json",
    }
    content = requests.get(
        get_splunkd_uri() + "/servicesNS/nobody/" + addon_name + "/properties/ta_threatquotient_add_on_settings/splunk_rest_host",  # noqa: E501
        headers=headers,
        params=params,
        verify=VERIFY_SSL_KVSTORE
    )

    if clear_password:
        response_dict = {"splunk_password": clear_password}

    content = content.json()

    for item in content["entry"]:
        if item["name"] == "splunk_password":
            continue
        response_dict[item["name"]] = item["content"]

    return response_dict


def get_proxy_from_config_parse():
    """Get Proxy information from the credentials.conf."""
    config = configparser.ConfigParser()
    proxy_info_dict = {}
    proxy_settings_conf = os.path.join(
        make_splunkhome_path(["etc", "apps", addon_name, "local", "credentials_storage.conf"])
    )
    if os.path.isfile(proxy_settings_conf):
        with io.open(proxy_settings_conf, "r", encoding="utf_8_sig") as inputconffp:
            config.readfp(inputconffp)
        if config.has_section("proxy_credentials"):
            proxy_info_dict["proxy_enabled"] = config.get("proxy_credentials", "proxy_enabled")
            proxy_info_dict["proxy_port"] = config.get("proxy_credentials", "proxy_port")
            proxy_info_dict["proxy_url"] = config.get("proxy_credentials", "proxy_url")
            proxy_info_dict["proxy_type"] = config.get("proxy_credentials", "proxy_type")
            proxy_info_dict["proxy_username"] = config.get("proxy_credentials", "proxy_username")
            proxy_info_dict["proxy_password"] = config.get("proxy_credentials", "proxy_password")
    return proxy_info_dict


def get_proxy_info(session_key, proxy_config_parse=False):
    """Get proxy information.

    :param session_key: Splunk session key
    :return: dictionary containing proxy details or None
    """
    if not proxy_config_parse:
        try:
            # list all credentials
            entities = entity.getEntities(
                ["admin", "passwords"],
                namespace=addon_name,
                owner="nobody",
                sessionKey=session_key,
                count=-1,
                search=addon_name,
            )
        except Exception:
            logger.exception(
                "message=get_proxy_info_response_error |"
                " ThreatQuotient Error: Could not get {} credentials from "
                "splunk.".format(addon_name)
            )
            raise Exception(
                "ThreatQuotient Error: Could not get {} credentials from "
                "splunk.".format(addon_name)
            )

        proxy_info_dict = {}
        clear_password = None
        for stanza, value in entities.items():
            try:
                password = value["clear_password"]
                password = json.loads(password)
                clear_password = password["proxy_password"]
                proxy_info_dict = {"proxy_password": clear_password}
                break
            except Exception:
                continue

        # Retrieve proxy configurations
        try:
            params = {"output_mode": "json", "--get-clear-credential--": "1"}
            headers = {
                "Authorization": "Splunk {}".format(session_key),
                "Content-Type": "application/json",
            }
            content = requests.get(
                get_splunkd_uri() + "/servicesNS/nobody/" + addon_name + "/properties/ta_threatquotient_add_on_settings/proxy",  # noqa: E501
                headers=headers,
                params=params,
                verify=VERIFY_SSL_KVSTORE
            )
            # Parse response
            content = content.json()
        except Exception:
            logger.exception(
                "message=get_proxy_info_fetching_proxy_error |"
                " ThreatQuotient Error: Error while fetching proxy configurations"
            )
            return None

        for item in content["entry"]:
            if item["name"] == "proxy_password":
                continue

            proxy_info_dict[item["name"]] = item["content"]
    else:
        proxy_info_dict = get_proxy_from_config_parse()

    # Return None if proxy_enabled is false or proxy hostname or proxy port is
    # not found
    if (
        not is_true(proxy_info_dict.get("proxy_enabled"))
        or not proxy_info_dict.get("proxy_port")
        or not proxy_info_dict.get("proxy_url")
    ):
        return None

    # Quote username and password if available
    user_pass = ""
    if proxy_info_dict.get("proxy_username") and proxy_info_dict.get("proxy_password"):
        username = quote_plus(proxy_info_dict["proxy_username"], safe="")
        password = quote_plus(proxy_info_dict["proxy_password"], safe="")
        user_pass = "{user}:{password}@".format(user=username, password=password)

    # Prepare proxy string
    proxy = "{proxy_type}://{user_pass}{host}:{port}".format(
        proxy_type=proxy_info_dict["proxy_type"],
        user_pass=user_pass,
        host=proxy_info_dict["proxy_url"],
        port=proxy_info_dict["proxy_port"],
    )
    proxies = {
        "http": proxy,
        "https": proxy,
    }

    return proxies


def get_access_token(account_info, proxies):
    """Get the access token to use in the authentication of indicators API."""
    try:
        auth_type = account_info.get('authorization_type', 'basic_auth')
        server_url = account_info["server_url"].strip("/")
        client_id = account_info["client_id"]
        if auth_type == "basic_auth":
            username = account_info["username"]
            password = account_info["password"]
            request_data = {
                "email": username,
                "password": password,
                "grant_type": "password",
                "client_id": client_id,
            }
            request_data = json.dumps(request_data)
            headers = {
                'Content-Type': 'application/json'
            }
        elif auth_type == "oauth":
            client_secret = account_info["client_secret"]
            request_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            auth_str = f"{client_id}:{client_secret}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            headers = {
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        elif auth_type == "cac_auth":
            request_data = {"grant_type": "ssl_certificate", "client_id": client_id}
            headers = {
                'Content-Type': 'application/json'
            }
        else:
            return None
        verify_cert = is_true(VERIFY_SSL)
    except Exception as err:
        logger.error(
            "message=get_access_token_error |"
            " Failed to get account info. {}".format(str(err)))
        return None

    endpoint = "/api/token"
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )

    try:
        if auth_type == "cac_auth":
            if not CERT_FILE_LOC or not os.path.isfile(CERT_FILE_LOC):
                logger.error(
                    "message=get_access_token_error |"
                    " Client certificate file not found at cert_file_path={}".format(CERT_FILE_LOC)
                )
                return None
            if not KEY_FILE_LOC or not os.path.isfile(KEY_FILE_LOC):
                logger.error(
                    "message=get_access_token_error |"
                    " Client key file not found at key_file_path={}".format(KEY_FILE_LOC)
                )
                return None
            response = requests.post(
                request_url,
                data=json.dumps(request_data),
                headers=headers,
                cert=(CERT_FILE_LOC, KEY_FILE_LOC),
                verify=verify_cert,
                proxies=proxies,
            )
        else:
            response = requests.post(
                request_url, data=request_data, headers=headers, verify=verify_cert, proxies=proxies
            )
    except Exception:
        logger.error(traceback.format_exc())
        return None

    # If response is not success
    if response.status_code != 200:
        logger.error(response.text)
        return None

    try:
        response = response.json()
    except Exception as e:
        logger.error("Error while converting response to JSON")
        logger.error(e)
        return None

    access_token = response["access_token"]
    return access_token


def get_indicator_from_value(access_token, server_url, proxies, indicator_value, verify_cert):

    endpoint = "/api/indicators"
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )

    request_headers = {"Authorization": "Bearer {}".format(access_token)}
    request_params = {
        "with": "type,status,score,adversaries,sources,attributes",
        "value": indicator_value,
    }

    try:
        request_response = requests.get(
            request_url,
            headers=request_headers,
            params=request_params,
            verify=verify_cert,
            proxies=proxies,
        )
    except Exception:
        logger.error(traceback.format_exc())
        return None

    # If response is not success
    if request_response.status_code != 200:
        logger.error(request_response.text)
        return None

    try:
        request_response = request_response.json()
    except Exception as e:
        logger.error("Error while converting response to JSON")
        logger.error(e)
        return None

    return request_response["data"]


def get_indicator_url(server_url, indicator_id):
    return "https://{}/indicators/{}/details".format(server_url.strip("/"), indicator_id)


def process_events(events):
    for event in events:
        event["type"] = event.get("type", {}).get("name")
        event["status"] = event.get("status", {}).get("name")
        event["score"] = int(
            float(
                event.get("score", {}).get("manual_score")
                if event.get("score", {}).get("manual_score")
                else event.get("score", {}).get("generated_score")
            )
        )
        event["adversaries"] = [adv.get("name") for adv in event.get("adversaries", []) if adv]
        event["sources"] = [
            "name: {}, tlp_id: {}".format(src.get("name"), src.get("tlp_id"))
            for src in event.get("sources", [])
            if src
        ]
        event["attributes"] = [
            "name: {}, value: {}".format(attr.get("name"), attr.get("value"))
            for attr in event.get("attributes", [])
            if attr
        ]


def resolve_host(hostname):
    """Resolve hostname to IPv4/IPv6 address."""
    try:
        # This returns a list of (family, type, proto, canonname, sockaddr) tuples
        infos = socket.getaddrinfo(hostname, None)

        # Filter for IPv4 and IPv6 addresses
        ipv4_addresses = [info for info in infos if info[0] == socket.AF_INET]
        ipv6_addresses = [info for info in infos if info[0] == socket.AF_INET6]

        # Prefer IPv4, but fallback to IPv6 if necessary
        if ipv4_addresses:
            address = ipv4_addresses[0][4][0]
        elif ipv6_addresses:
            address = ipv6_addresses[0][4][0]
        else:
            return None  # No suitable address found
        return address
    except socket.gaierror:
        return None


def create_service(sessionkey, splunkserver, mgm_port, uname=None, psswrd=None):
    """Create Service to communicate with splunk."""
    try:
        # Resolve hostname to IPv4 address
        ip_address = resolve_host(splunkserver)
        if not ip_address:
            raise Exception("Failed to resolve Splunk management URI to an IP address.")

        if uname and psswrd:
            service = client.connect(
                host=ip_address,
                port=mgm_port,
                username=uname,
                password=psswrd,
                app="ThreatQAppforSplunk",
                owner="nobody"
            )
        else:
            service = client.connect(
                host=ip_address,
                port=mgm_port,
                token=sessionkey,
                app="ThreatQAppforSplunk",
                owner="nobody"
            )
        return service
    except Exception as e:
        logger.error("Error while creating Splunk service: {}. "
                     "Traceback: {}".format(e, traceback.format_exc()))
        return None
