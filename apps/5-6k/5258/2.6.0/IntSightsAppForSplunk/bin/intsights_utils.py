# Python imports
import json
import requests
from requests.compat import quote_plus
from base64 import b64encode
import hashlib
import math
import socket

# Splunk imports
import splunk.clilib.cli_common
import splunk.entity as entity
import splunk.rest as rest
from solnlib.utils import is_true
from splunklib.client import connect

from ta_intsights_declare import ta_name
import constants as const

# Global varibles
NO_OF_BATCH_DELETE_IOCS = 22
IOC_LIMIT = 1000
LIMIT = 10000
BACKOFF_FACTOR = 30
PRODUCT_VENDOR_FILTER_STANZA_KEY = "product_vendor_list"


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
    mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
    hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
    mgmt_port = mgmt_uri.split(":")[-1]

    # Resolve hostname to IPv4 address
    ip_address = resolve_host(hostname)
    if not ip_address:
        raise Exception("Failed to resolve Splunk management URI to an IP address.")

    service = connect(host=ip_address, port=mgmt_port, token=sessionkey, app=ta_name, owner="nobody")
    return service


def get_proxy_info(session_key):
    """Get proxy information.

    :param session_key: Splunk session key
    :return: dictionary containing proxy details or None
    """
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=ta_name,
            owner="nobody",
            sessionKey=session_key,
            count=-1,
            search=ta_name,
        )
    except Exception:
        raise Exception(
            "IntSigts Error: Could not get {} credentials from splunk.".format(ta_name)
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
        resp, content = rest.simpleRequest(
            "/servicesNS/nobody/{}/properties/ta_intsights_settings/proxy".format(ta_name),
            sessionKey=session_key,
            getargs={"output_mode": "json", "--get-clear-credential--": "1"},
        )
        # Parse response
        content = json.loads(content)
    except Exception:
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


def get_credentials(account_name, session_key):
    """Get credentials of Query API."""
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=ta_name,
            owner="nobody",
            sessionKey=session_key,
            count=-1,
            search=ta_name,
        )
    except Exception:
        raise Exception(
            "IntSights Error: Could not get {} credentials from "
            "splunk.".format(ta_name)
        )

    api_key = None
    response_dict = {}
    for stanza, value in entities.items():
        try:
            password = value["clear_password"]
            password = json.loads(password)
            api_key = password["api_key"]
            break
        except Exception:
            continue

    resp, content = rest.simpleRequest(
        "/servicesNS/nobody/{}/properties/ta_intsights_settings/{}".format(ta_name, account_name),
        sessionKey=session_key,
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    if api_key:
        response_dict = {"api_key": api_key}

    content = json.loads(content)

    for item in content["entry"]:
        if item["name"] == "api_key":
            continue
        response_dict[item["name"]] = item["content"]

    return response_dict


def build_query_for_lookups(data=[]):
    """Create a lookup queries."""
    formed_list = []
    for value in data:
        formed_list.append({"_key": hashlib.md5(value.encode()).hexdigest()})
    query_dict = {"$or": formed_list}
    return query_dict


def generate_query_list_for_lookups(data=[]):
    """Create a query to operate with lookups."""
    formed_list = []
    if len(data) > 0:

        # We cannot pass the more than 1024 characters in querystring
        # so we using the md5 hash value of every iocs value and maximum
        # we can only afford 22 iocs when the query is build up. it reaches
        # to 1021 with the 22 iocs.
        total_queries = int(math.ceil(float(len(data)) / NO_OF_BATCH_DELETE_IOCS))
        for n in range(total_queries):
            if (
                len(
                    data[
                        n * NO_OF_BATCH_DELETE_IOCS: (n + 1) * NO_OF_BATCH_DELETE_IOCS
                    ]
                )
                > 0
            ):
                formed_list.append(
                    build_query_for_lookups(
                        data[
                            n
                            * NO_OF_BATCH_DELETE_IOCS: (n + 1)
                            * NO_OF_BATCH_DELETE_IOCS
                        ]
                    )
                )
    return formed_list


def build_url(server_address, api_url):
    """Builds the url.

    :param server_address: Server Address
    :param api_url: endpoint url
    :return: URL with the scheme
    """
    url = "".join(["https://", server_address, api_url])
    return url


def get_start_date(helper, start_date, file_name_suffix):
    """Get the start date."""
    input_name = "{}{}".format(helper.get_input_stanza_names(), file_name_suffix)
    input_state = helper.get_check_point(input_name) or {}
    last_updated_time = input_state.get("last_updated_time") or start_date
    return last_updated_time


def feed_report_to_server(
    helper,
    account_info,
    proxies,
    header,
    sync_endpoint,
    sync_json
):
    """Sending report to the server."""
    helper.log_info("input_name = {} | Sending report to the intsights".format(helper.get_input_stanza_names()))
    verify_cert = const.VERIFY_SSL
    url = build_url(account_info.get("server_address"), sync_endpoint)

    response = requests.post(
        url, verify=verify_cert, headers=header, proxies=proxies, json=sync_json
    )

    if response.status_code == 200 or response.status_code == 201:
        helper.log_info("input_name = {} | Report has been sent to the InSights server successfully."
                        .format(helper.get_input_stanza_names()))
    else:
        helper.log_error("input_name = {} | Error occurred while sending report to the IntSights."
                         .format(helper.get_input_stanza_names()))


def verify_authentication(account_info, proxies):
    """Verifying authentication."""
    encoded_cred = b64encode(
        "{}:{}".format(
            account_info.get("account_id"), account_info.get("api_key")
        ).encode()
    ).decode()
    header = {
        "Content-type": "application/json",
        "Accept": "application/json",
        "Authorization": "Basic {}".format(encoded_cred),
    }
    api_url = "/public/v1/test-credentials"
    url = build_url(account_info.get("server_address"), api_url)
    verify_cert = const.VERIFY_SSL
    try:
        response = requests.head(
            url, verify=verify_cert, headers=header, proxies=proxies
        )
        if response.status_code != 200:
            raise Exception("Please verify the provided credentials.")
    except requests.exceptions.ProxyError:
        raise Exception("Please verify the provided proxy credentials.")
    except requests.exceptions.SSLError:
        raise Exception(
            "Please verify the SSL certificate for the provided configuration."
        )
    except Exception:
        raise Exception("Please verify the provided credentials.")


def get_ioc_sources(
    header, proxies, sync_id, encoded_cred, server_address, verify_cert
):
    """Get ioc sources information."""
    payload = {"syncId": sync_id}
    api_url = "/public/v1/apps/splunk/iocs/sources"
    try:
        url = build_url(server_address, api_url)
        response = requests.get(
            url, verify=verify_cert, headers=header, proxies=proxies, params=payload
        )
        return (json.loads(response.content)).get("content")
    except Exception:
        return False


def get_macro_definition(serviceobj, macro_name):
    """Fetch macro definition."""
    response = serviceobj.get(
        "properties/macros/{}/definition".format(macro_name)
    )
    if response["status"] != 200:
        raise Exception(
            "Got response with status_code={}, response={}".format(
                response["status"], str(response)
            )
        )
    definitaion = str(response["body"].read().decode())
    return definitaion


def is_system_module_enable(helper, account_info, proxies, sync_id, encoded_cred, header, key):
    """Checking if ioc system module is enable or not."""
    helper.log_info("input_name = {} | Checking system module".format(helper.get_input_stanza_names()))
    api_url = "/public/v1/apps/splunk/system-modules"
    url = build_url(account_info.get("server_address"), api_url)
    payload = {"syncId": sync_id}
    try:
        response = requests.get(
            url,
            verify=const.VERIFY_SSL,
            headers=header,
            proxies=proxies,
            params=payload,
        )
        if response.status_code == 200:
            data = json.loads(response.content)
            return data["content"][key]
        else:
            raise Exception("Not able to connect IntSights system-module")
    except Exception as e:
        helper.log_error("input_name = {} | Error occurred while checking system module, Error : {}"
                         .format(helper.get_input_stanza_names(), e))


def is_macro_definition_true(session_key, macro_name):
    """Fetch and check if macro definition is True or False."""
    splunk_service = create_service(session_key)
    macro_definition = get_macro_definition(splunk_service, macro_name)
    macro_definition = is_true(macro_definition)
    return macro_definition


def get_action_fields_list(session_key, macro_name):
    """Fetch list of action fields for IOCs correlation."""
    splunk_service = create_service(session_key)
    macro_definition = get_macro_definition(splunk_service, macro_name)
    action_fields_list = []
    macro_definition = macro_definition.strip()
    if macro_definition == ",":
        # If macro value is a comma , it means that the no action fields are used
        return action_fields_list
    else:
        fields_list = macro_definition.split(",")
        for each in fields_list:
            # Handling cases where quotes used within macro definition.
            field = each.strip().replace("'", "").replace("\"", "")
            action_fields_list.append(field)
    return action_fields_list


def product_vendor_list_from_Filter(session_key, product_vendor_filter, helper):
    """Get the product and vendor values list from the filtername."""
    try:
        resp, content = rest.simpleRequest(
            "/servicesNS/nobody/{}/properties/ta_intsights_products_vendors_filters/{}/{}".format(
                ta_name, product_vendor_filter, PRODUCT_VENDOR_FILTER_STANZA_KEY
            ),
            sessionKey=session_key,
            getargs={"output_mode": "json"},
        )
        if resp.status in [200, 201]:
            content = content.decode()
            product_vendor_list = content.split(",")
            return product_vendor_list
        else:
            raise Exception("Response stataus : {}".format(resp.status))
    except Exception as e:
        raise Exception("Error while fetching Product and Vendor Filter details: {}".format(e))
