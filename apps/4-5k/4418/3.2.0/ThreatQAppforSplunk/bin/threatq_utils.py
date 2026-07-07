# Python imports
import os
import sys
import json
import random
import base64
import socket
import traceback
import time
import io
import re
from splunklib import six
from requests.compat import quote_plus
import itertools

import logger_manager as log
import requests

# Splunk imports
import splunk
import splunklib.client as client
import splunk.clilib.cli_common
import splunk.entity as entity
import splunk.rest as rest
from splunk import ResourceNotFound
from splunk.util import normalizeBoolean
from six.moves import configparser
from splunk.clilib.bundle_paths import make_splunkhome_path
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE,"threatqappforsplunk","aob_py3"))
from solnlib import conf_manager
from solnlib.splunkenv import get_splunkd_uri
from threatq_const import VERIFY_SSL_KVSTORE, CERT_FILE_LOC, KEY_FILE_LOC


from threatq_const import VERIFY_SSL

logger = log.setup_logging("threatquotient_app_utils")
addon_name = "ThreatQAppforSplunk"
APP_NAME = __file__.split(os.sep)[-3]


class UnauthorizedRequestException(Exception):
    """Raised when access token is invalid."""

    pass


def set_log_level(log_level):
    global logger
    logger.setLevel(log_level)


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

def process_multi_lookup_events(events):
    for event in events:
        event["ioc_id"] = event.pop("id", None)
        event["ioc_value"] = event.pop("value", None)
        try:
            if event.get("attributes"):
                for attr in event["attributes"]:
                    if attr["name"] == "Malware Family":
                        event["malware_family"] = attr["value"]
                        break
            event.pop("attributes", None)
        except Exception as err:
            logger.error("Error while fetching Malware family data. Error: {}".format(err))
            event["malware_family"] = None
            event.pop("attributes", None)


def get_indicator_from_value(auth_type, access_token, server_url, proxies, indicator_value, verify_cert):

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
        if auth_type == "cac_auth":
            request_response = requests.get(
                request_url,
                headers=request_headers,
                params=request_params,
                cert=_get_cac_cert_tuple(logger),
                verify=verify_cert,
                proxies=proxies,
            )
        else:
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



def is_iterator_empty(iterable):
    """Return None if iterator is empty else return iterator as is."""
    try:
        first = next(iterable)
        if first is None:
            return None
        return itertools.chain([first], iterable)
    except StopIteration:
        return None


def is_true(val):
    """Decide if `val` is true.

    :param val: Value to check.
    :type val: ``(integer, string)``
    :returns: True or False.
    :rtype: ``bool``
    """
    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False


def get_conf_info(session_key, confname, stanzaname, stanzafield):
    """Get conf file information."""
    splunkrc = {
        "host": splunk.getDefault("host"),
        "port": splunk.getDefault("port"),
        "app": APP_NAME,
        "owner": "nobody",
    }
    try:
        service = create_service(session_key)
        response = service.get(
            "properties/{}/{}/{}".format(confname, stanzaname, stanzafield)
        )
        if response["status"] != 200:
            raise Exception(
                "Got response with status_code={}, response={}".format(
                    response["status"], str(response)
                )
            )
        definitaion = str(response["body"].read().decode())
        return definitaion
    except Exception as err:
        ERR_MSG = "error occurred while getting '{}' field".format(
            stanzafield
        )
        logger.error(ERR_MSG)
        logger.exception(err)


def get_splunk_web_url(session_key, include_port, host_name=None):
    """Get Splunk Web Url."""
    try:
        ent = entity.getEntity("server/settings", "settings", sessionKey=session_key)
        port = ent["httpport"]
        scheme = "https" if normalizeBoolean(ent["enableSplunkWebSSL"]) else "http"
        hostname = host_name if host_name else socket.gethostname()
        if include_port:
            return "{}://{}:{}".format(scheme, hostname, port)
        return "{}://{}".format(scheme, hostname)
    except Exception as e:
        raise Exception("Not able to create Splunk web URL. Error: {}".format(str(e)))

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
                "ThreatQuotient Error: Could not get {} credentials from " "splunk.".format(addon_name)
            )
            raise Exception(
                "ThreatQuotient Error: Could not get {} credentials from " "splunk.".format(addon_name)
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
            get_splunkd_uri() + "/servicesNS/nobody/" + addon_name + "/properties/threatquotient_app_settings/additional_parameters",  # noqa: E501
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
                "ThreatQuotient Error: Could not get {} credentials from " "splunk.".format(addon_name)
            )
            raise Exception(
                "ThreatQuotient Error: Could not get {} credentials from " "splunk.".format(addon_name)
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
                get_splunkd_uri() + "/servicesNS/nobody/" + addon_name + "/properties/threatquotient_app_settings/proxy",  # noqa: E501
                headers=headers,
                params=params,
                verify=VERIFY_SSL_KVSTORE
            )

            # Parse response
            content = content.json()
        except Exception:
            logger.exception("ThreatQuotient Error: Error while fetching proxy configurations")
            return None

        for item in content["entry"]:
            if item["name"] == "proxy_password":
                continue

            proxy_info_dict[item["name"]] = item["content"]

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
                request_url, data=json.dumps(request_data), headers=headers, cert=(CERT_FILE_LOC, KEY_FILE_LOC), verify=verify_cert, proxies=proxies
            )
        else:
            response = requests.post(
                request_url, data=request_data, headers=headers, verify=verify_cert, proxies=proxies
            )

    except Exception as e:
        logger.error(e)
        return None

    # If response is not success
    if response.status_code != 200:
        logger.error(
            "message=get_access_token_response_error | "
            "Response status code = {} Response text = {}".format(response.status_code, response.text))
        return None

    try:
        response = response.json()
    except Exception as e:
        logger.error("Threatquotient Error: while converting response to JSON")
        logger.error(e)
        return None

    access_token = response["access_token"]
    return access_token


def create_events(
    events, server_url, verify_cert, account_info, proxies, session_key, logger,
):
    """Create event on the threatq platform."""
    max_events = 1000
    endpoint = "/api/events/consume"
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    access_token = get_access_token(account_info=account_info, proxies=proxies)

    if not access_token:
        logger.error("ThreatQuotient Error: Error while generating token")
        raise ValueError("Error while generating token. Please check the configuration")
    request_headers = {
        "Authorization": "Bearer {}".format(access_token),
        "Content-Type": "application/json",
    }
    auth_type = account_info.get('authorization_type', 'basic_auth')

    def create_indicator_event(events, request_url, verify_cert, proxies, request_headers, auth_type):
        if auth_type == "cac_auth":
            response = requests.post(
                request_url,
                data=json.dumps(events),
                headers=request_headers,
                verify=verify_cert,
                cert=_get_cac_cert_tuple(logger),
                proxies=proxies,
            )
        else:
            response = requests.post(
                request_url,
                data=json.dumps(events),
                headers=request_headers,
                verify=verify_cert,
                proxies=proxies,
            )

        # If response is not success
        if response.status_code not in (200, 201):
            if response.status_code == 401:
                raise UnauthorizedRequestException()
            try:
                response_json = response.json()
                errors = ", ".join(response_json.get("data").get("errors").get("value"))
            except Exception:
                raise Exception(str(response.text))
            raise Exception(str(errors))

    for i in range(0, len(events), max_events):
        try:
            try:
                create_indicator_event(
                    events[i: i + max_events], request_url, verify_cert, proxies, request_headers, auth_type
                )
            except UnauthorizedRequestException:
                access_token = get_access_token(account_info=account_info, proxies=proxies)
                request_headers.update({"Authorization": "Bearer {}".format(access_token)})
                create_indicator_event(
                    events[i: i + max_events], request_url, verify_cert, proxies, request_headers, auth_type
                )
        except Exception as err:
            logger.exception(err)


def update_indicator_object(
    indicator_id, indicator_data, server_url, verify_cert, proxies, request_headers, auth_type
):
    """Update Indicator Object."""
    endpoint = "/api/indicators/{ind_id}".format(ind_id=indicator_id)
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    if auth_type == "cac_auth":
        response = requests.put(
            request_url,
            data=json.dumps(indicator_data),
            headers=request_headers,
            verify=verify_cert,
            cert=_get_cac_cert_tuple(logger),
            proxies=proxies,
        )
    else:
        response = requests.put(
            request_url,
            data=json.dumps(indicator_data),
            headers=request_headers,
            verify=verify_cert,
            proxies=proxies,
        )

    # If response is not success
    if response.status_code not in (200, 201):
        try:
            response_json = response.json()
            errors = ", ".join(response_json.get("data").get("errors").get("value"))
        except Exception:
            raise Exception(str(response.text))
        raise Exception(str(errors))


def delete_indicator_attribute(
    indicator_id, attribute_id, server_url, verify_cert, proxies, request_headers, auth_type
):
    """Delete indicator attribute."""
    endpoint = "/api/indicators/{ind_id}/attributes/{attr_id}".format(
        ind_id=indicator_id, attr_id=attribute_id
    )
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    if auth_type == "cac_auth":
        response = requests.delete(
            request_url, headers=request_headers, verify=verify_cert, cert=_get_cac_cert_tuple(logger), proxies=proxies,
        )
    else:
        response = requests.delete(
            request_url, headers=request_headers, verify=verify_cert, proxies=proxies,
        )

    # If response is not success
    if response.status_code not in (204,):
        if response.status_code == 401:
            raise UnauthorizedRequestException()
        try:
            response_json = response.json()
            errors = ", ".join(response_json.get("data").get("errors").get("value"))
        except Exception:
            raise Exception(str(response.text))
        raise Exception(str(errors))


def get_indicator_attributes(
    indicator_id, server_url, verify_cert, proxies, request_headers, request_params, auth_type
):
    """Get Indicator Attribute."""
    endpoint = "/api/indicators/{ind_id}/attributes".format(ind_id=indicator_id)
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    if auth_type == "cac_auth":
        response = requests.get(
            request_url,
            params=request_params,
            headers=request_headers,
            verify=verify_cert,
            cert=_get_cac_cert_tuple(logger),
            proxies=proxies,
        )
    else:
        response = requests.get(
            request_url,
            params=request_params,
            headers=request_headers,
            verify=verify_cert,
            proxies=proxies,
        )

    # If response is not success
    if response.status_code not in (200, 201):
        if response.status_code == 401:
            raise UnauthorizedRequestException()
        try:
            response_json = response.json()
            errors = ", ".join(response_json.get("data", {}).get("errors", {}).get("value", ""))
        except Exception:
            raise Exception(str(response.text))
        raise Exception(str(errors))

    response = response.json()

    return response["data"]


def update_indicators(
    indicators,
    server_url,
    verify_cert,
    account_info,
    proxies,
    session_key,
    logger,
    splunk_source
):
    """Update attributes and source of indicator object."""
    data = {
        "sources": splunk_source,
        "attributes": [
            {"name": "Splunk Sighting Timestamp", "value": "", "sources": splunk_source, },
            {"name": "Match Count", "value": "", "sources": splunk_source},
        ],
    }

    ERR_MSG = (
        "Failed to update indicator object details for indicator object"
        " with ioc_id={} and ioc_value={}"
    )
    access_token = get_access_token(account_info=account_info, proxies=proxies)
    auth_type = account_info.get('authorization_type', 'basic_auth')
    if not access_token:
        logger.error("ThreatQuotient Error: Error while generating token")
        raise ValueError("Error while generating token. Please check the configuration")
    request_headers = {
        "Authorization": "Bearer {}".format(access_token),
        "Content-Type": "application/json",
    }
    for indicator in indicators:
        data["attributes"][0]["value"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime(int(indicator.get("last_seen")))
        )
        data["attributes"][1]["value"] = indicator.get("match_count")

        ind_id, ind_val = indicator.get("ioc_id"), indicator.get("ioc_value")

        try:
            attribute_data = []
            limit = 1000
            total = 0
            while True:
                request_params = {
                    "limit": limit,
                    "offset": total,
                }
                try:
                    # Get attributes data
                    results = get_indicator_attributes(
                        ind_id, server_url, verify_cert, proxies, request_headers, request_params, auth_type
                    )
                    if len(results) == 0:
                        break
                    attribute_data.extend(results)
                except UnauthorizedRequestException:
                    access_token = get_access_token(account_info=account_info, proxies=proxies)
                    request_headers.update({"Authorization": "Bearer {}".format(access_token)})
                    results = get_indicator_attributes(
                        ind_id, server_url, verify_cert, proxies, request_headers, request_params, auth_type
                    )
                    if len(results) == 0:
                        break
                    attribute_data.extend(results)
                total = len(attribute_data)
            logger.info(
                "message=update_indicator_total_indicator_found | "
                "Found total {} attributes for ioc id - {}".format(total, ind_id)
            )

            # Delete all the Match Count and Splunk Sighting Timestamp attributes
            for attr in attribute_data:
                if attr["name"] in ("Match Count", "Splunk Sighting Timestamp"):
                    try:
                        delete_indicator_attribute(
                            ind_id, attr["id"], server_url, verify_cert, proxies, request_headers, auth_type
                        )
                    except UnauthorizedRequestException:
                        access_token = get_access_token(account_info=account_info, proxies=proxies)
                        request_headers.update({"Authorization": "Bearer {}".format(access_token)})
                        delete_indicator_attribute(
                            ind_id, attr["id"], server_url, verify_cert, proxies, request_headers, auth_type
                        )

            try:
                # Update
                update_indicator_object(
                    ind_id, data, server_url, verify_cert, proxies, request_headers, auth_type
                )
            except UnauthorizedRequestException:
                access_token = get_access_token(account_info=account_info, proxies=proxies)
                request_headers.update({"Authorization": "Bearer {}".format(access_token)})
                update_indicator_object(
                    ind_id, data, server_url, verify_cert, proxies, request_headers, auth_type
                )
        except Exception as err:
            logger.error(ERR_MSG.format(ind_id, ind_val))
            logger.exception(err)


# Get matching variants for an indicator (IP/URL only, IP/URL:PORT)
def get_indicator_matching_variants(indicator):
    """Get all matching variants for an indicator including port-based matches.
    
    Port comes from the "port" field in master_lookup (populated by another application).
    Port field can be:
    - Single value (string): e.g., "8000"
    - Multi-valued (list): e.g., ["8000", "443", "8080"]
    - Not present (None/empty): No port-based matching
    
    Creates variants:
    1. Original ioc_value (as stored)
    2. Base IP/URL (without port) - matches events with IP/URL regardless of port
    3. IP/URL:PORT (concatenated) - matches events with exact IP/URL:PORT combination for each port
    
    Note: We do NOT match on "Port only" as that would cause false positives.
    """
    ioc_value = indicator.get("ioc_value", "")
    port = indicator.get("port")
    indicator_type = indicator.get("type", "")
    
    variants = set()
    
    # Always add the original ioc_value
    variants.add(ioc_value)
    
    # Collect all port values (handle multi-valued)
    all_ports = []
    
    # Port from master_lookup field (could be string or list)
    if port:
        if isinstance(port, list):
            all_ports.extend([str(p) for p in port if p])
        else:
            all_ports.append(str(port))
    
    # Only process IP Address, IPv6 Address, and URL types
    if indicator_type in ["IP Address", "IPv6 Address", "URL"]:
        if all_ports:
            # Add base value (IP/URL without port) - allows matching on IP/URL regardless of port
            variants.add(ioc_value)
            # Add concatenated value (ioc_value:port) for each port - matches exact IP/URL:PORT combination
            for port_val in all_ports:
                variants.add("{}:{}".format(ioc_value, port_val))
        else:
            # No port, just use the ioc_value as is
            variants.add(ioc_value)
    
    return variants


# Get query to filter indicators
def get_kv_store_query(field, values):
    """Get query to filter indicators."""
    if not field or not values:
        return None

    query = [{field: value} for value in values]
    return json.dumps({"$or": query})


# Get indicators from specified lookup
def get_indicators(splunkd_uri, session_key, app_name, lookup, query=None, limit=25000):
    """Get indicators from specified lookup."""
    rest_endpoint = (
        splunkd_uri + "/servicesNS/nobody/" + app_name + "/storage/collections/data/" + lookup
    )
    try:
        indicators = []
        get_args = {"limit": limit}
        if query:
            get_args["query"] = query

        while True:
            get_args["skip"] = len(indicators)

            for count in range(3):
                try:
                    get_args["output_mode"] = "json"

                    headers = {
                        "Authorization": "Splunk {}".format(session_key),
                        "Content-Type": "application/json",
                    }

                    content = requests.get(
                        rest_endpoint,
                        headers=headers,
                        params=get_args,
                        verify=VERIFY_SSL_KVSTORE
                    )
                    break
                except Exception as e:
                    logger.error("ThreatQ error: Getting indicators, %s" % str(e))

                    if count == 2:
                        raise

                    time.sleep(5)

            content = content.json()

            if len(content) == 0:
                return indicators

            indicators += content

    except Exception as e:
        logger.error("ThreatQ error: Getting indicators, %s" % str(e))
        raise


# Get indicators which are matched
def get_matched_indicators(splunkd_uri, session_key, app_name, query=None):
    """Get indicators which are matched."""
    return get_indicators(
        splunkd_uri, session_key, app_name, "threatq_matched_indicators", query=query,
    )


# Get all the master_lookup indicators
def get_all_indicators(splunkd_uri, session_key, app_name, query=None):
    """Get indicators which are matched."""
    return get_indicators(
        splunkd_uri, session_key, app_name, "master_lookup", query=query,
    )


# Get indicators which are not matched
def get_unmatched_indicators(splunkd_uri, session_key, app_name, query=None):
    """Get indicators which are not matched."""
    matched_indicators = {
        ind["ioc_value"]: True
        for ind in get_matched_indicators(splunkd_uri, session_key, app_name, query=query)
    }
    all_indicators = get_indicators(
        splunkd_uri, session_key, app_name, "master_lookup", query=query
    )
    unmatched_indicators = [
        ind for ind in all_indicators if not matched_indicators.get(ind["ioc_value"], False)
    ]
    return unmatched_indicators


# Save indicators in threatq_matched_indicators lookup
def put_indicators(splunkd_uri, session_key, app_name, indicators):
    """Save indicators in threatq_matched_indicators lookup."""
    rest_endpoint = (
        splunkd_uri
        + "/servicesNS/nobody/"
        + app_name
        + "/storage/collections/data/threatq_matched_indicators/batch_save"
    )
    for count in range(3):
        try:
            params = {"output_mode": "json"}

            headers = {
                "Authorization": "Splunk {}".format(session_key),   
                "Content-Type": "application/json",
            }

            requests.post(
                rest_endpoint,
                headers=headers,
                params=params,
                data=json.dumps(indicators),
                verify=VERIFY_SSL_KVSTORE
            )
            break
        except Exception as e:
            logger.error("ThreatQ error: Putting indicators, %s" % str(e))

            if count == 2:
                raise

            time.sleep(5)


# Put lock entry in threatq_master_lookup_lock
def put_lock(splunkd_uri, session_key, app_name):
    """Put lock entry in threatq_master_lookup_lock."""
    lock_field = {"lock_time": time.time()}
    rest_endpoint = (
        splunkd_uri
        + "/servicesNS/nobody/"
        + app_name
        + "/storage/collections/data/threatq_master_lookup_lock"
    )
    try:
        params = {"output_mode": "json"}
        headers = {
            "Authorization": "Splunk {}".format(session_key),   
            "Content-Type": "application/json",
        }

        content =requests.post(
            rest_endpoint,
            headers=headers,
            params=params,
            data=json.dumps(lock_field),
            verify=VERIFY_SSL_KVSTORE
        )
        return content.json()["_key"]
    except Exception as e:
        logger.error("ThreatQ error: Putting lock, %s" % str(e))
        raise


# Get lock entries from threatq_master_lookup_lock
def get_locks(splunkd_uri, session_key, app_name):
    """Get lock entries from threatq_master_lookup_lock."""
    rest_endpoint = (
        splunkd_uri
        + "/servicesNS/nobody/"
        + app_name
        + "/storage/collections/data/threatq_master_lookup_lock"
    )
    try:
        lock_fields = []

        while True:
            params = {"output_mode": "json", "skip": len(lock_fields)}
            
            headers = {
                "Authorization": "Splunk {}".format(session_key),
                "Content-Type": "application/json",
            }
            content = requests.get(
                rest_endpoint,
                headers=headers,
                params=params,
                verify=VERIFY_SSL_KVSTORE
            )
            
            content = content.json()

            if len(content) == 0:
                return lock_fields

            lock_fields += content

    except Exception as e:
        logger.error("ThreatQ error: Getting locks, %s" % str(e))
        raise


# Delete lock entry from threatq_master_lookup_lock
def delete_lock(splunkd_uri, session_key, app_name, lock_key):
    """Delete lock entry from threatq_master_lookup_lock."""
    rest_endpoint = (
        splunkd_uri
        + "/servicesNS/nobody/"
        + app_name
        + "/storage/collections/data/threatq_master_lookup_lock/"
        + lock_key
    )
    try:
        headers = {
            "Authorization": "Splunk {}".format(session_key),
            "Content-Type": "application/json",
        }

        requests.delete(
            rest_endpoint,
            headers=headers,
            verify=VERIFY_SSL_KVSTORE
        )
    except ResourceNotFound as rnf:
        logger.info("ThreatQ error: Deleting lock, %s" % str(rnf))
    except Exception as e:
        logger.error("ThreatQ error: Deleting lock, %s" % str(e))
        raise


# Lock threatq_matched_indicators lookup
def lock_lookup(splunkd_uri, session_key, app_name):
    """Lock threatq_matched_indicators lookup."""
    while True:
        try:
            lock_fields = get_locks(splunkd_uri, session_key, app_name)
            t_lock_fields = []

            for lock_field in lock_fields:

                # If lock is there for more than 300 seconds remove it
                if float(lock_field["lock_time"]) < time.time() - 300:
                    unlock_lookup(splunkd_uri, session_key, app_name, lock_field["_key"])
                else:
                    t_lock_fields.append(lock_field["_key"])

        except Exception:
            t_lock_fields = []

        if len(t_lock_fields) != 0:
            time.sleep(5)
            continue

        lock_key = put_lock(splunkd_uri, session_key, app_name)
        try:
            lock_fields = get_locks(splunkd_uri, session_key, app_name)
        except Exception:
            lock_fields = []

        if len(lock_fields) != 1:
            unlock_lookup(splunkd_uri, session_key, app_name, lock_key)
            time.sleep(random.randint(1, 5))
            continue

        return lock_key


# Unlock threatq_matched_indicators lookup
def unlock_lookup(splunkd_uri, session_key, app_name, lock_key):
    """Unlock threatq_matched_indicators lookup."""
    for _ in range(3):
        try:
            delete_lock(splunkd_uri, session_key, app_name, lock_key)
            break
        except Exception:
            time.sleep(5)


# py2-3 compatibility method to return utf-8 encoded str for hashlib
def get_encoded_str(a_string):
    """py2-3 compatibility method to return utf-8 encoded str for hashlib."""
    a_string = str(a_string)
    if not isinstance(a_string, six.binary_type):
        return a_string.encode("utf-8")
    else:
        return a_string


def get_conf_file(session_key, app_name, conf_file):
    """This method returns content present in conf file."""
    try:
        conf_file = conf_manager.ConfManager(
            session_key,
            app_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(app_name, conf_file),
        ).get_conf(conf_file)
        file_content = conf_file.get_all(only_current_app=True)
        return file_content
    except Exception:
        return None


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


def create_service(sessionkey):
    """Create Service to communicate with splunk."""
    try:
        mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
        hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
        mgmt_port = mgmt_uri.split(":")[-1]

        # Resolve hostname to IPv4 address
        ip_address = resolve_host(hostname)
        if not ip_address:
            raise Exception("Failed to resolve Splunk management URI to an IP address.")

        service = client.connect(
            host=ip_address,
            port=mgmt_port,
            token=sessionkey,
            app="ThreatQAppforSplunk",
            owner="nobody"
        )
        return service
    except Exception as e:
        logger.error("Error while creating Splunk service: {}. "
                     "Traceback: {}".format(e, traceback.format_exc()))
        return None

def _get_cac_cert_tuple(logger):
    if not CERT_FILE_LOC or not os.path.isfile(CERT_FILE_LOC):
        logger.error(
            "message=cac_auth_cert_error |"
            " Client certificate file not found at cert_file_path={}".format(CERT_FILE_LOC)
        )
        raise Exception("Client certificate file not found")
    if not KEY_FILE_LOC or not os.path.isfile(KEY_FILE_LOC):
        logger.error(
            "message=cac_auth_cert_error |"
            " Client key file not found at key_file_path={}".format(KEY_FILE_LOC)
        )
        raise Exception("Client key file not found")
    return (CERT_FILE_LOC, KEY_FILE_LOC)