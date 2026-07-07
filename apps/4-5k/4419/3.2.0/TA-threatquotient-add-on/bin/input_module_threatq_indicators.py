
# encoding = utf-8
import ta_threatquotient_add_on_declare
import os
import sys
import time
import datetime
import json
import requests
import threading
from itertools import islice
from functools import partial
from requests.compat import quote_plus
from requests.auth import HTTPBasicAuth
import re
import traceback

import threatq_utils as tq_utils
import splunklib.client as splunkClient
from six.moves import queue as Queue
import logger_manager as log
from splunk.auth import getSessionKey
from solnlib.utils import is_true
from six import text_type
from threatq_const import VERIFY_SSL_KVSTORE, VERIFY_SSL, CERT_FILE_LOC, KEY_FILE_LOC

logger = log.setup_logging("ta_threatquotient_add_on_threatq_indicators")

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning

    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    # handle for upgrade case
    import urllib3
    from urllib3.exceptions import InsecureRequestWarning

    urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass


def validate_input(helper, definition):
    pass


def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = tuple(islice(it, size))
        if not chunk:
            break
        yield chunk


def _get_cac_cert_tuple():
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


def send_to_kvstore(session_key, endpoint_flag, helper, data_filter, data, index_time):
    class KVStoreClient:
        _max_content_bytes = 100000
        _max_content_records = 1000
        _number_of_threads = 5

        def __init__(
            self,
            splunk_server,
            splunk_server_port,
            splunk_app,
            splunk_collection,
            session_key,
            splunk_username,
            splunk_password,
            splunk_server_verify,
            operation_flag,
        ):
            self.splunk_server = splunk_server
            self.splunk_server_port = splunk_server_port
            self.splunk_app = splunk_app
            self.splunk_collection = splunk_collection
            self.session_key = session_key
            self.splunk_username = splunk_username
            self.splunk_password = splunk_password
            self.post_data_queue = Queue.Queue(0)
            self.delete_data_queue = Queue.Queue(0)
            self.operation_flag = operation_flag
            for x in range(self._number_of_threads):
                t = threading.Thread(target=self.batch_thread)
                t.daemon = True
                t.start()

        def post_data_to_splunk(self, data):
            if len(data) > 0:
                self.post_data_queue.put(data)

        def delete_data_from_splunk(self, data):
            if len(data) > 0:
                self.delete_data_queue.put(data)

        def write_data_to_kvstore(self, data, splunk_url, operation_to_perform):
            splunkserver = helper.get_global_setting("splunk_rest_host_url") or 'localhost'
            if splunkserver in ['127.0.0.1', 'localhost']:
                auth = None
                headers = {
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                    "Authorization": "Splunk {}".format(self.session_key)
                }
            else:
                auth = HTTPBasicAuth(self.splunk_username, self.splunk_password)
                headers = {
                    "Content-type": "application/json"
                }
            try:
                if operation_to_perform == "post":
                    response = requests.post(
                        splunk_url,
                        verify=splunk_server_verify,
                        auth=auth,
                        headers=headers,
                        data=json.dumps(data),
                    )
                elif operation_to_perform == "delete":
                    response = requests.delete(
                        splunk_url,
                        verify=splunk_server_verify,
                        headers=headers,
                        auth=auth,
                    )
                return response
            except Exception:
                logger.error(
                    "message=write_data_to_kvstore_error | Error while performing kvstore operations,"
                    " Error: {}".format(traceback.format_exc())
                )

        def batch_thread(self):
            while True:
                data = (
                    self.post_data_queue.get()
                    if self.operation_flag == "batch_save"
                    else self.delete_data_queue.get()
                )
                if self.operation_flag == "batch_save" and len(data) > 0:
                    splunk_url = "".join(
                        [
                            "https://",
                            self.splunk_server,
                            ":",
                            self.splunk_server_port,
                            "/servicesNS/nobody/",
                            self.splunk_app,
                            "/storage/collections/data/",
                            self.splunk_collection,
                            "/",
                            "batch_save",
                        ]
                    )
                    payload_length = sum(len(json.dumps(item)) for item in data)
                    logger.info("message=total_payload_length | posting payload with length: {}".format(
                        payload_length
                    )
                    )
                    try:
                        response = self.write_data_to_kvstore(data, splunk_url, operation_to_perform="post")
                        if not response.status_code == requests.codes.ok:
                            if response.status_code == 401:
                                session_key = tq_utils.get_session_key(helper)
                                if session_key:
                                    self.session_key = session_key
                                    response = self.write_data_to_kvstore(data, splunk_url, operation_to_perform="post")
                            else:
                                logger.error(
                                    "message=batch_thread_post_batch_save_error | API POST response:"
                                    " status_code={} response={}".format(response.status_code, response.text)
                                )
                    except Exception:
                        logger.error(
                            "message=batch_thread_post_error | Error while writing indicators to the {}".format(
                                self.splunk_collection
                            )
                        )
                    self.post_data_queue.task_done()
                elif self.operation_flag == "delete" and len(data) > 0:
                    for ioc in data:
                        try:
                            ioc_data_value = ioc.get("ioc_value") or ioc.get("value")
                            if ioc_data_value and ioc_data_value != "":
                                splunk_delete_ioc_url = "".join(
                                    [
                                        "https://",
                                        self.splunk_server,
                                        ":",
                                        self.splunk_server_port,
                                        "/servicesNS/nobody/",
                                        self.splunk_app,
                                        "/storage/collections/data/",
                                        self.splunk_collection,
                                        "/",
                                        quote_plus(ioc_data_value),
                                    ]
                                )

                                response = self.write_data_to_kvstore(
                                    ioc, splunk_delete_ioc_url, operation_to_perform="delete"
                                )
                                if (
                                    response.status_code != requests.codes.ok
                                    and response.status_code != 404  # noqa: W503
                                ):
                                    if response.status_code == 401:
                                        session_key = tq_utils.get_session_key(helper)
                                        if session_key:
                                            self.session_key = session_key
                                            response = self.write_data_to_kvstore(
                                                data, splunk_delete_ioc_url, operation_to_perform="delete"
                                            )
                                    else:
                                        logger.error(
                                            "batch_thread_post_batch_save_error | API POST response:"
                                            " status_code={} response={}".format(response.status_code, response.text)
                                        )
                            else:
                                logger.error(
                                    "message=batch_thread_null_indicator_error | Error While Deleting indicator:"
                                    " Indicator having null value. Skipping this indicator."
                                )
                        except Exception:
                            logger.error(
                                "message=batch_thread_delete_error |"
                                " Error while deleting the indicators from the {}.".format(
                                    self.splunk_collection
                                )
                            )
                    self.delete_data_queue.task_done()

        def wait_until_done(self):
            self.post_data_queue.join()
            return

        def wait_until_deletion_done(self):
            self.delete_data_queue.join()
            return

    # Define my own class to put data into KVStore.
    # The Splunk Python SDK is not threaded for KVStore operations

    logger.info("Posting to kvstore...")
    splunkserver = helper.get_global_setting("splunk_rest_host_url") or 'localhost'
    destappname = "ThreatQAppforSplunk"
    if endpoint_flag == "indicators":
        destcollection = "master_lookup"
    elif endpoint_flag == "indicators_type":
        destcollection = "threatq_indicator_types"
    elif endpoint_flag == "indicators_status":
        destcollection = "threatq_indicator_status"

    threatqserver = helper.get_global_setting("server_url")
    if not threatqserver:
        logger.error("message=send_to_kvstore_error | No server configured")
        return 1
    logger.info("message=server_found | splunkserver={}".format(splunkserver))
    local_session_key = helper.context_meta.get("session_key")
    splunk_account_info = tq_utils.get_splunk_credentials(local_session_key)

    splunk_server_verify = is_true(VERIFY_SSL_KVSTORE)
    # To populate lookup in localmachine SSLcertification
    # is not needed
    splunk_server_port = splunk_account_info.get("splunk_rest_port") or "8089"
    if splunkserver in ['127.0.0.1', 'localhost']:
        splunk_server_verify = False
        dest_splunk_service = tq_utils.create_service(
            session_key,
            splunkserver,
            splunk_server_port
        )
    else:
        dest_splunk_service = tq_utils.create_service(
            session_key,
            splunkserver,
            splunk_server_port,
            helper.get_global_setting("splunk_username"),
            helper.get_global_setting("splunk_password"),
        )
    logger.info("message=verify_splunk_server | splunk_server_verify={}".format(splunk_server_verify))
    logger.info("message=splunk_server_port | splunk_server_port={}".format(splunk_server_port))

    # TODO: check for kvstore status first though error is self-explaining
    # Check if KVStore collection exists
    if destcollection not in dest_splunk_service.kvstore:
        logger.error(
            "message=send_to_kvstore_collection_error |"
            " KVStore collection {0} not on {1} Splunk instance".format(destcollection, splunkserver)
        )
        raise Exception(
            "KVStore collection {0} not on {1} Splunk instance".format(destcollection, splunkserver)
        )

    # Define our threaded class for KVStore data submission
    if splunkserver in ['127.0.0.1', 'localhost']:
        username = None
        passwd = None
    else:
        username = helper.get_global_setting("splunk_username")
        passwd = helper.get_global_setting("splunk_password")
    dest_kvstore = KVStoreClient(
        splunkserver,
        splunk_server_port,
        destappname,
        destcollection,
        session_key,
        username,
        passwd,
        splunk_server_verify,
        "batch_save",
    )

    delete_indicator_kvstore = KVStoreClient(
        splunkserver,
        splunk_server_port,
        destappname,
        destcollection,
        session_key,
        username,
        passwd,
        splunk_server_verify,
        "delete",
    )

    start_rest = time.time()
    if endpoint_flag == "indicators":
        for chunk in chunked_iterable(data, KVStoreClient._max_content_records):
            filter_data, deleted_data = (data_filter(chunk, index_time))
            dest_kvstore.post_data_to_splunk(filter_data)
            delete_indicator_kvstore.delete_data_from_splunk(deleted_data)
        delete_indicator_kvstore.wait_until_deletion_done()
    else:
        dest_kvstore.post_data_to_splunk(data)
    dest_kvstore.wait_until_done()
    end_rest = time.time()
    logger.info(
        "message=send_to_kvstore_time_taken |"
        " Post to kvstore time took: {}".format(end_rest - start_rest)
    )

    logger.info("message=send_to_kvstore_completed | Modular Input pullkvtokv completed.")


def process_attributes(indicator):
    """Convert attributes into uniform structure.

    Args:
        indicator (dict): one ioc
    """
    regex = re.compile('[.$]')
    attributes = indicator.get("attributes")
    processed_attributes = []
    if attributes:
        for attribute in attributes:
            if attribute:
                key = list(attribute.keys())[0]
            else:
                key = ""
            isname = attribute.get("name")
            if (isname) and (regex.search(isname) is not None):
                logger.info(
                    "message=process_attributes_invalid_attribute_name | Skipping attribute |"
                    "Attribute Name {} contains . or $".format(isname)
                )
                continue
            elif (isname):
                temp = {}
                temp[isname] = attribute.get("value")
                processed_attributes.append(temp)
            elif (regex.search(key) is not None):
                logger.info(
                    "message=process_attributes_invalid_attribute_name | Skipping attribute |"
                    "Attribute Name {} contains . or $".format(key)
                )
                continue
            else:
                processed_attributes.append(attribute)
    indicator["attributes"] = processed_attributes
    return indicator


def extract_port_field(indicator, ioc_value):
    """Extract port values from multiple sources and return as string or array.

    Checks for port in priority order:
    1. First-level "port" field
    2. Attributes with name="port" (handles both original and processed format)
    3. Extracted from ioc_value (IP:PORT or URL:PORT format) - only if not found in 1 or 2

    Args:
        indicator (dict): indicator object
        ioc_value (str): the ioc_value to extract port from

    Returns:
        str|list: single port as string if one value, list of strings if multiple,
                 empty string if no ports found
    """
    ports = []

    # Case 1: Check first-level "port" field
    if indicator.get("port"):
        port_value = indicator.get("port")
        if isinstance(port_value, list):
            ports.extend([str(p) for p in port_value if p])
        else:
            ports.append(str(port_value))

    # Case 2: Check attributes for "port"
    # Handle both original format: {"name": "port", "value": "443"}
    # and processed format: {"port": "443"}
    if indicator.get("attributes"):
        for attr in indicator["attributes"]:
            if isinstance(attr, dict):
                # Check original format first
                if attr.get("name") and attr.get("name").lower() == "port":
                    attr_value = attr.get("value")
                    if attr_value:
                        if isinstance(attr_value, list):
                            ports.extend([str(p) for p in attr_value if p])
                        else:
                            ports.append(str(attr_value))
                # Check processed format
                else:
                    for attr_name, attr_value in attr.items():
                        if attr_name.lower() == "port" and attr_value:
                            if isinstance(attr_value, list):
                                ports.extend([str(p) for p in attr_value if p])
                            else:
                                ports.append(str(attr_value))

    # Case 3: Extract port from ioc_value (IP:PORT or URL:PORT format)
    # Only extract from ioc_value if port was not found in first-level field or attributes
    if ioc_value and len(ports) == 0:
        ioc_str = str(ioc_value)
        found_ports = set()

        # Pattern 1: IPv4 address followed by port (e.g., 192.168.1.1:443)
        # Matches 4 groups of 1-3 digits separated by dots, followed by :PORT
        ipv4_port_pattern = r'(?:\d{1,3}\.){3}\d{1,3}:(\d{1,5})(?:/|$|\?|#)'
        ipv4_matches = re.findall(ipv4_port_pattern, ioc_str)
        found_ports.update(ipv4_matches)

        # Pattern 2: IPv6 address in brackets followed by port (e.g., [2001:db8::1]:443)
        # Matches [IPv6]:PORT format - IPv6 addresses should be in brackets when specifying port
        ipv6_port_pattern = r'\[[^\]]+\]:(\d{1,5})(?:/|$|\?|#)'
        ipv6_matches = re.findall(ipv6_port_pattern, ioc_str)
        found_ports.update(ipv6_matches)

        # Pattern 3: URL or hostname with port (e.g., https://example.com:443 or example.com:443)
        # Match :PORT after hostname, before /, ?, #, or end of string
        # More restrictive to avoid matching ports in paths or query strings
        url_port_pattern = r'(?:://[^/?#:]+|^[^:/?#]+):(\d{1,5})(?:/|$|\?|#)'
        url_matches = re.findall(url_port_pattern, ioc_str)

        # Filter URL matches: exclude if already found, and validate context
        for match in url_matches:
            if match not in found_ports:
                # Validate port number is in valid range (1-65535)
                try:
                    port_num = int(match)
                    if 1 <= port_num <= 65535:
                        # Check if this might be part of an IPv6 address (has multiple colons before it)
                        match_pos = ioc_str.find(':' + match)
                        if match_pos > 0:
                            before = ioc_str[:match_pos]
                            # If there are 2+ colons before and no brackets, likely IPv6 (skip it)
                            # IPv6 in brackets is already handled by Pattern 2
                            if before.count(':') >= 2 and '[' not in before[-50:]:
                                continue
                        found_ports.add(match)
                except ValueError:
                    continue

        if found_ports:
            ports.extend(found_ports)

    # Remove duplicates and empty values, convert to strings
    unique_ports = []
    seen = set()
    for port in ports:
        port_str = str(port).strip()
        if port_str and port_str not in seen:
            unique_ports.append(port_str)
            seen.add(port_str)

    # Return string if single value, list if multiple values, empty string if none
    if len(unique_ports) == 0:
        return ""
    elif len(unique_ports) == 1:
        return unique_ports[0]
    else:
        return unique_ports


def indicator_filter(helper, indicator_status_list, threshold_score, all_flag, custom_attributes, custom_fields,
                     indicators, index_time):
    """Pipeline method for indexing indicators.

    Args:
        indicators (list[dict]): list of iocs
    """
    def validate_indicators(indicator, custom_attributes, custom_fields):
        if not indicator.get("updated_at"):
            logger.error(
                "message=validate_indicators_updated_at_error |"
                " Error getting updated_at for indicator: {}".format(indicator))
            return False
        current_indicator_status = indicator.get("status")
        current_indicator_score = 0
        try:
            current_indicator_score = int(float(indicator.pop("score")))
            indicator["score"] = 10 if current_indicator_score > 10 else current_indicator_score
        except Exception:
            logger.error(
                "message=validate_indicators_score_error |"
                "Error getting score for indicator: {}".format(indicator))
            return False

        if (current_indicator_status not in indicator_status_list and all_flag) or (
            current_indicator_score < threshold_score
        ):
            return False

        if not is_true(helper.get_arg("checkbox_for_index")):
            indicator["updated_at"] = indicator["updated_at"] + " UTC"

            # Changing Sources to sources and Adversaries to adversaries
            if "Sources" in indicator:
                indicator["sources"] = indicator.pop("Sources")

            if "Adversaries" in indicator:
                indicator["adversaries"] = indicator.pop("Adversaries")

            if indicator["value"]:
                indicator_enc = indicator["value"].encode("utf-8")
                indicator_enc = indicator_enc[:950] if len(indicator_enc) > 950 else indicator_enc
                indicator["value"] = indicator_enc.decode("utf-8", "ignore")

        # modify dict for lookup
        indicator["index_time"] = index_time
        indicator["ioc_id"] = indicator.pop("id")
        if indicator.get("value") and indicator.get("value") != "":
            indicator["ioc_value"] = indicator.pop("value")
            # avoids duplication in SHC with multiple running inputs or in case of
            # multiple forwarders
            indicator["_key"] = indicator["ioc_value"]
            if indicator.get("sources"):
                indicator["sources"] = [source["value"] for source in indicator["sources"]]

            # Extract port field from multiple sources (before processing attributes to check original format)
            indicator["port"] = extract_port_field(indicator, indicator["ioc_value"])

            # Changing Attributes to attributes
            # Changing dictionary format of attributes from {"name":"attr1", "value":"val"} to {"attr1":"val"}
            indicator = process_attributes(indicator)
            indicator["malware_family"] = []
            if indicator.get("attributes"):
                for mf_attribute in indicator["attributes"]:
                    mf_upper_case = mf_attribute.get("Malware Family")
                    mf_lower_case = mf_attribute.get("malware family")
                    if mf_upper_case:
                        indicator["malware_family"].append(mf_upper_case)
                    elif mf_lower_case:
                        indicator["malware_family"].append(mf_lower_case)
                for custom_attr in custom_attributes:
                    if (custom_attr != ""):
                        custom_attr_underscore = custom_attr.replace(" ", "_")
                        indicator[custom_attr_underscore] = [
                            mf_attribute.get(custom_attr) for mf_attribute in indicator["attributes"]
                        ]
            for custom_field in custom_fields:
                if (custom_field != ""):
                    custom_field_underscore = custom_field.replace(" ", "_")
                    indicator[custom_field_underscore] = indicator.get(custom_field)
            if indicator.get("adversaries"):
                indicator["adversaries"] = [
                    adversary["value"] for adversary in indicator["adversaries"]
                ]
            return True
        else:
            raise Exception("Indicator having null value.")

    should_post_data = []
    deleted_indicators = []
    for indicator in indicators:
        indicator = {key.lower(): value for key, value in indicator.items()}
        try:
            if validate_indicators(indicator, custom_attributes, custom_fields):
                if indicator.get("deleted_at"):
                    deleted_indicators.append(indicator)
                else:
                    should_post_data.append(indicator)
            else:
                deleted_indicators.append(indicator)
        except Exception as e:
            logger.error(
                "message=indicator_filter_validation_error |"
                " Error while validating an Indicator: {}".format(str(e)))
    return should_post_data, deleted_indicators


def filter_indicators(indicators):
    """Filter the indicators so that indicators prior to 90 days are not collected.

    Args:
        indicators (list[dict]): list of iocs
    """
    indicator_to_ingest = []
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    last_date = today - datetime.timedelta(days=90)
    epoch_last_date = last_date.timestamp()

    for indicator in indicators:
        indicator = {key.lower(): value for key, value in indicator.items()}
        epoch_for_updated_date = datetime.datetime.strptime(indicator["updated_at"], "%Y-%m-%d %H:%M:%S").timestamp()
        if epoch_for_updated_date > epoch_last_date:
            indicator_to_ingest.append(indicator)
    return indicator_to_ingest


# Get indicators from ThreatQ
def _get_indicators(auth_type, helper, ew, server_url, verify_cert, use_proxy, proxies, timeout_value, session_key,
                    custom_attributes, custom_fields):
    input_name = helper.get_input_stanza_names()
    index_checkbox = is_true(helper.get_arg("checkbox_for_index"))
    export_token = helper.get_arg("export_token")
    export_id = helper.get_arg("export_id")
    export_hash = helper.get_arg("export_hash")
    page_limit = helper.get_arg("response_page_size")

    indicator_status = helper.get_arg("indicator_status").strip()
    indicator_status_list = list(
        map(text_type.strip, indicator_status.split(",")),
    )
    # check 'All' is not in indicator_status_list
    all_flag = "All" not in indicator_status_list

    threshold_score = helper.get_arg("threshold_score")
    try:
        threshold_score = int(threshold_score)
    except Exception:
        logger.error(
            "message=get_indicators_score_error |"
            " Error getting threshold_score: {}".format(threshold_score))
        threshold_score = 0

    if not export_token:
        msg = "Not able to get export token"
        logger.error(msg)
        raise Exception(msg)

    if not export_id:
        msg = "Not able to get export id"
        logger.error(msg)
        raise Exception(msg)

    if not export_hash:
        msg = "Not able to get export hash"
        logger.error(msg)
        raise Exception(msg)

    def index_indicators(indicators, index_time):
        """Pipeline method for indexing indicators.

        Args:
            indicators (list[dict]): list of iocs
        """
        indexed_indicators = 0
        for i in range(len(indicators)):
            indicator = indicators[i]
            indicator = {key.lower(): value for key, value in indicator.items()}
            if indicator.get("value") is None or indicator.get("value") == "":
                continue
            if not indicator.get("updated_at"):
                logger.error(
                    "message=index_indicators_updated_at_error |"
                    " Error getting updated_at for indicator: {}".format(indicator))
                continue
            current_indicator_status = indicator.get("status")
            current_indicator_score = 0
            try:
                current_indicator_score = int(float(indicator.pop("score")))
                indicator["score"] = 10 if current_indicator_score > 10 else current_indicator_score
            except Exception:
                logger.error(
                    "message=index_indicators_score_error |"
                    " Error getting score for indicator: {}".format(indicator))
                continue

            if (current_indicator_status not in indicator_status_list and all_flag) or (
                current_indicator_status == "Active" and current_indicator_score < threshold_score
            ):
                continue

            indicator["updated_at"] = indicator["updated_at"] + " UTC"

            # Changing Sources to sources and Adversaries to adversaries
            if "Sources" in indicators[i]:
                indicator["sources"] = indicators[i].pop("Sources")

            if "Adversaries" in indicators[i]:
                indicator["adversaries"] = indicators[i].pop("Adversaries")

            # Changing Attributes to attributes
            # Changing dictionary format of attributes from {"name":"attr1", "value":"val"} to {"attr1":"val"}
            indicator = process_attributes(indicator)

            if indicator["value"]:
                indicator_enc = indicator["value"].encode("utf-8")
                indicator_enc = indicator_enc[:950] if len(indicator_enc) > 950 else indicator_enc
                indicator["value"] = indicator_enc.decode("utf-8", "ignore")

            event = helper.new_event(
                source=helper.get_input_type(),
                time=index_time,
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                data=json.dumps(indicator),
            )
            ew.write_event(event)
            indexed_indicators += 1
            indicators[i] = indicator

        logger.info("Indexed {} indicators".format(indexed_indicators))

    endpoint = "/api/export/{export_id}".format(export_id=export_id)
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )

    # pull_all_iocs default conf value is false which handles upgrade scenario
    # on handleCreate we are forcing users to enable this checkbox
    input_state = helper.get_check_point(input_name) or {}
    logger.debug(
        "message=get_indicators_get_checkpoint |"
        " Checkpoint Value is {}".format(input_state)
    )
    pull_all_iocs = helper.get_arg("pull_all_iocs") or False

    indicator_should_post = partial(
        indicator_filter, helper, indicator_status_list, threshold_score, all_flag, custom_attributes, custom_fields
    )
    send_to_kvstore_partial = partial(
        send_to_kvstore, session_key, "indicators", helper, indicator_should_post
    )
    if is_true(pull_all_iocs):
        # pull all iocs in chunks
        logger.info("Performing all ioc import with pagination")
        limit = int(page_limit)
        lastid = input_state.get("last_id") or 0
        start = time.time()
        while True:
            input_state.update({"last_id": lastid})
            request_params = {
                "token": export_token,
                "limit": limit,
                "sort": "id",
                "id": ">" + str(lastid),
            }

            if not is_true(verify_cert):
                logger.warning(
                    "message=get_indicators_verify_certificate_warning |"
                    " InsecureRequestWarning: Unverified HTTPS request is being made."
                )

            try:
                start_get = time.time()
                if auth_type == "cac_auth":
                    cac_cert = _get_cac_cert_tuple()
                    request_response = requests.get(
                        request_url,
                        params=request_params,
                        verify=verify_cert,
                        cert=cac_cert,
                        proxies=proxies,
                        timeout=(300, timeout_value),
                    )
                else:
                    request_response = helper.send_http_request(
                        request_url,
                        "get",
                        verify=verify_cert,
                        parameters=request_params,
                        use_proxy=use_proxy,
                        timeout=(300, timeout_value),
                    )
                end_get = time.time()
                logger.info(
                    "message=get_indicators_time |"
                    " got data in: {}".format(end_get - start_get)
                )
            except Exception:
                logger.error(
                    "message=get_indicators_error | {}".format(traceback.format_exc()))
                raise

            if request_response.status_code != 200:
                logger.error(
                    "message=get_indicators_response_error |"
                    " Error while getting indicators, Response code: {},"
                    " Response text: {}".format(request_response.status_code, request_response.text)
                )
                raise Exception("Error while getting indicators")

            try:
                indicators = request_response.json()
            except Exception as e:
                logger.error(
                    "message=get_indicators_json_decode_error | {}".format(str(e)))
                raise
            # break if reached end
            if len(indicators) == 0:
                logger.info(
                    "message=get_indicators_reached_last_page |"
                    " Reached last page. Finishing ioc data collection.")
                break
            lastres = indicators[-1]["id"]
            logger.info(
                "Got {} indicators, between id from(exclusive): {} to(inclusive): {}".format(
                    len(indicators), lastid, lastres
                )
            )
            index_time = time.time()
            indicator_to_ingest = filter_indicators(indicators)
            if index_checkbox:
                index_indicators(indicator_to_ingest, index_time)
                post_end = time.time()
                logger.info(
                    "index indicator method time took: {}".format(
                        post_end - index_time
                    )
                )
            # get last id
            if lastid == lastres:
                logger.info("got to last page")
                break
            # index indicators into Splunk
            post_start = time.time()
            try:
                send_to_kvstore_partial(indicator_to_ingest, index_time)
                post_end = time.time()
                logger.info(
                    "message=get_indicators_write_to_kvstore_time |"
                    " Time took to write into kvstore: {}".format(post_end - post_start)
                )
                helper.save_check_point(input_name, input_state)
                lastid = lastres
            except Exception:
                logger.error(
                    "message=get_indicators_send_to_kvstore_error | {}".format(traceback.format_exc()))
                logger.error("Terminating the collection for indicators")
                return 1
        end = time.time()
        logger.info(
            "message=get_indicators_page_data_collection_time |"
            " Time took for paginated collection: {}".format(end - start))
        # make api call with export hash to avoid duplication on next input invoc
        request_params = {
            "token": export_token,
            "differential": export_hash,
            "limit": 1,
        }
        cac_cert = None
        if auth_type == "cac_auth":
            cac_cert = _get_cac_cert_tuple()
        try:
            if auth_type == "cac_auth":
                request_response = requests.get(
                    request_url,
                    params=request_params,
                    verify=verify_cert,
                    cert=cac_cert,
                    proxies=proxies,
                    timeout=(300, timeout_value),
                )
            else:
                request_response = helper.send_http_request(
                    request_url,
                    "get",
                    verify=verify_cert,
                    parameters=request_params,
                    use_proxy=use_proxy,
                    timeout=(300, timeout_value),
                )
        except requests.exceptions.ConnectionError as err:
            # Executing another query on the last id to send export hash to
            # threatq so it doesnt send duplicate data on next differential
            # call
            logger.error(
                "message=get_indicators_connect_error |"
                " Connect error occured: {}".format(err))
            pass
        end_get = time.time()
        logger.info(
            "message=get_indicators_total_pagination_data_collection_time |"
            " Total time took with pagination: {}".format(end_get - start_get))
        # Remove input entry from checkpoint
        helper.delete_check_point(input_name)
        # Revert pull_all_iocs conf value to False so next invocation uses differential technique
        logger.info("Reverting flag value to do the differential import on next invocation")
        tq_utils.update_pagination_config(
            helper.context_meta["session_key"], input_name, "false"
        )
    else:
        request_params = {"token": export_token, "differential": export_hash}
        try:
            if auth_type == "cac_auth":
                cac_cert = _get_cac_cert_tuple()
                request_response = requests.get(
                    request_url,
                    params=request_params,
                    verify=verify_cert,
                    cert=cac_cert,
                    proxies=proxies,
                    timeout=(300, timeout_value),
                )
            else:
                request_response = helper.send_http_request(
                    request_url,
                    "get",
                    verify=verify_cert,
                    parameters=request_params,
                    use_proxy=use_proxy,
                    timeout=(300, timeout_value),
                )
        except Exception:
            logger.error(
                "message=get_indicators_differntial_call_request_error |"
                " {}".format(traceback.format_exc()))
            raise
        if request_response.status_code != 200:
            logger.error(
                "message=get_indicators_differntial_call_response_error |"
                " Error while getting indicators, Response code: {},"
                " Response text: {}".format(request_response.status_code, request_response.text)
            )
            raise Exception("Error while getting indicators")

        try:
            indicators = request_response.json()
        except Exception:
            logger.error(traceback.format_exc())
            raise

        logger.info("Got {} indicators".format(len(indicators)))

        indicator_to_ingest = filter_indicators(indicators)
        # index indicators into Splunk
        index_time = time.time()
        if index_checkbox:
            index_indicators(indicator_to_ingest, index_time)
            post_end = time.time()
            logger.info(
                "message=get_indicators_differntial_time_taken |"
                " indicator index differential took: {}".format(
                    post_end - index_time
                )
            )
        post_start = time.time()
        try:
            send_to_kvstore_partial(indicator_to_ingest, index_time)
            post_end = time.time()
            logger.info(
                "message=get_indicators_differntial_time_taken |"
                " Time took to write into kvstore in differential call: {}".format(
                    post_end - post_start
                )
            )
        except Exception:
            logger.error(
                "message=get_indicators_differntial_call_write_to_kvstore error |"
                " {}".format(traceback.format_exc()))
            logger.error("Terminating the collection for indicators")
            return 1
    logger.info("Finished ioc data collection in kvstore.")


# Get the indicator statuses
def _get_indicator_statuses(auth_type, helper, ew, server_url, headers, verify_cert, use_proxy, proxies, session_key):
    endpoint = "/api/indicator/statuses"
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    if not is_true(verify_cert):
        logger.warning(
            "message=get_indicator_types_verify_certificate_warning |"
            " InsecureRequestWarning: Unverified HTTPS request is being made.")

    try:
        if auth_type == "cac_auth":
            cac_cert = _get_cac_cert_tuple()
            request_response = requests.get(
                request_url,
                verify=verify_cert,
                cert=cac_cert,
                headers=headers,
                proxies=proxies,
            )
        else:
            request_response = helper.send_http_request(
                request_url, "get", verify=verify_cert, headers=headers, use_proxy=use_proxy,
            )
    except Exception:
        logger.error("message=get_indicator_statuses_error | {}".format(traceback.format_exc()))
        raise

    if request_response.status_code != 200:
        logger.error(
            "message=get_indicator_statuses_send_to_response_error |"
            "Error while getting indicator statuses, Response code: {},"
            " Response text: {}".format(request_response.status_code, request_response.text)
        )
        raise Exception("Error while getting indicator status")

    try:
        indicator_statuses = request_response.json()
    except Exception:
        logger.error(traceback.format_exc())
        raise

    logger.info("Got {} indicator statuses".format(indicator_statuses.get("total", "")))
    indicators_status_data = []
    for items in indicator_statuses["data"]:
        items["_key"] = str(items["id"])
        indicators_status_data.append(items)
    send_to_kvstore_partial = partial(
        send_to_kvstore, session_key, "indicators_status", helper, True
    )
    try:
        send_to_kvstore_partial(indicators_status_data, index_time=None)
        logger.info("Indicator statuses are collected into Kvstore")
    except Exception:
        logger.error(traceback.format_exc())
        logger.error(
            "message=get_indicator_statuses_send_to_kv_store_error |"
            " Terminating the collection for indicator status")
        return 1


# Get the indicator types
def _get_indicator_types(auth_type, helper, ew, server_url, headers, verify_cert, use_proxy, proxies, session_key):
    endpoint = "/api/indicator/types"
    request_url = "{scheme}{url}{endpoint}".format(
        scheme="https://", url=server_url, endpoint=endpoint
    )
    if not is_true(verify_cert):
        logger.warning(
            "message=get_indicator_types_verify_certificate_warning |"
            " InsecureRequestWarning: Unverified HTTPS request is being made.")

    try:
        if auth_type == "cac_auth":
            cac_cert = _get_cac_cert_tuple()
            request_response = requests.get(
                request_url,
                verify=verify_cert,
                cert=cac_cert,
                headers=headers,
                proxies=proxies,
            )
        else:
            request_response = helper.send_http_request(
                request_url, "get", verify=verify_cert, headers=headers, use_proxy=use_proxy,
            )
    except Exception:
        logger.error("message=get_indicator_types_error | {}".format(traceback.format_exc()))
        raise

    if request_response.status_code != 200:
        logger.error(
            "message=get_indicator_types_response_error |"
            " Error while getting indicator types, Response code: {},"
            " Response text: {}".format(request_response.status_code, request_response.text)
        )
        raise Exception("Error while getting indicator types")

    try:
        indicator_types = request_response.json()
    except Exception:
        logger.error(
            "message=get_indicator_types_json_convert_error | {}".format(traceback.format_exc()))
        raise

    logger.info("Got {} indicator types".format(indicator_types.get("total", "")))

    indicators_types_data = []
    for items in indicator_types["data"]:
        items["_key"] = str(items["id"])
        indicators_types_data.append(items)
    send_to_kvstore_partial = partial(
        send_to_kvstore, session_key, "indicators_type", helper, True
    )
    try:
        send_to_kvstore_partial(indicators_types_data, index_time=None)
        logger.info("Indicator types are collected into KVstore")
    except Exception:
        logger.error(traceback.format_exc())
        logger.error(
            "message=get_indicator_types_send_to_kv_store_error |"
            " Terminating the collection for indicator types")
        return 1


def get_custom_fields_from_conf(helper, conf_name, session_key, splunk_url, splunk_server_verify):
    headers = {
        "Content-type": "application/json",
        "Authorization": "Splunk {}".format(session_key),
    }
    try:
        response = requests.get(
            splunk_url, verify=splunk_server_verify, headers=headers
        )
        custom_fields = response.content.decode().split(",")
        return custom_fields
    except Exception:
        logger.error(
            "message=get_custom_fields_from_conf_error |"
            " Error getting custom fields to be ingested from conf: {}".format(conf_name))


def get_kvstore_rest_details(helper):
    splunkserver = (
        helper.get_global_setting("splunk_rest_host_url") or 'localhost'
    )
    splunk_server_port = (
        helper.get_global_setting('splunk_rest_port') or '8089'
    )
    splunk_server_verify = is_true(VERIFY_SSL_KVSTORE)
    if splunkserver in ['localhost', '127.0.0.1']:
        splunk_server_verify = False
    splunk_app = "ThreatQAppforSplunk"

    return [splunkserver, splunk_server_port, splunk_server_verify, splunk_app]


def _cleanup_kvstore_lookup(helper, session_key):

    deleted_enpoints_queries = []
    indicator_status = helper.get_arg("indicator_status").strip()
    indicator_score = int(helper.get_arg("threshold_score"))
    score_list = []
    for i in range(0, indicator_score):
        score_list.append({"score": str(i)})

    if len(score_list) > 0:
        score_query = ''.join(
            [
                '{ "$or":',
                json.dumps(score_list),
                '}',
            ]
        )
        deleted_enpoints_queries.append(score_query)

    indicator_status_list = list(
        map(text_type.strip, indicator_status.split(",")),
    )

    # check 'All' is in indicator_status_list
    all_flag = ("All" in indicator_status_list)
    status_list = []

    if not all_flag:
        for status in indicator_status_list:
            status_dict = {"status": {"$ne": status}}
            status_list.append(status_dict)

        if len(status_list) > 0:
            status_query = ''.join(
                [
                    '{ "$and":',
                    json.dumps(status_list),
                    '}',
                ]
            )
            deleted_enpoints_queries.append(status_query)

    if len(deleted_enpoints_queries) > 0:
        splunk_collection = "master_lookup"
        [splunkserver, splunk_server_port, splunk_server_verify, splunk_app] = get_kvstore_rest_details(helper)
        for endpoint_query in deleted_enpoints_queries:
            splunk_delete_ioc_url = "".join(
                [
                    "https://",
                    splunkserver,
                    ":",
                    splunk_server_port,
                    "/servicesNS/nobody/",
                    splunk_app,
                    "/storage/collections/data/",
                    splunk_collection,
                    "/?query=",
                    quote_plus(endpoint_query),

                ]
            )
            headers = {
                "Content-type": "application/json",
                "Accept": "text/plain",
                "Authorization": "Splunk {}".format(session_key),
            }
            for i in range(4):
                try:
                    response = requests.delete(  # noqa: F841
                        splunk_delete_ioc_url,
                        verify=splunk_server_verify,
                        headers=headers,
                    )
                except Exception:
                    if i == 3:
                        logger.error(
                            "message=cleanup_kvstore_delete_error |"
                            "Failed delete due to the Error: {}".format(traceback.format_exc())
                        )
                    else:
                        logger.info(
                            "message=cleanup_kvstore_request_retry |"
                            " Failed delete. Retrying in 5 seconds... "
                            "Attempt({})".format(i + 1)
                        )
                    time.sleep(5)
                else:
                    break


def create_url(splunkserver, splunk_server_port, splunk_app, conf_name, stanza_name, key_name):
    url = "".join(
        [
            "https://",
            splunkserver,
            ":",
            splunk_server_port,
            "/servicesNS/nobody/",
            splunk_app,
            "/properties/",
            conf_name,
            "/",
            stanza_name,
            "/",
            key_name,
        ]
    )
    return url


def validate_attributes(custom_list):
    custom_list = custom_list.lower()
    unsupported_attributes = ["attributes", "adversaries", "sources", ".", "$"]
    if any(word in custom_list for word in unsupported_attributes):
        raise Exception(
            "Invalid word entered (\"attributes, sources, adversaries, ., $\") in custom attributes/fields."
        )


def collect_events(helper, ew):
    """Implement your data collection logic here."""
    proxy_settings = helper.get_proxy()
    use_proxy = True if proxy_settings else False
    verify_cert = VERIFY_SSL
    verify_cert = is_true(verify_cert)
    server_url = helper.get_global_setting("server_url")
    if not server_url:
        logger.error(
            "message=collect_events_server_url_error |"
            " Server URL not found. Please check account configuration")
        raise Exception("Server URL not found. Please check account configuration")

    session_key = helper.context_meta["session_key"]
    proxies = tq_utils.get_proxy_info(session_key)
    account_info = tq_utils.get_credentials(session_key)
    auth_type = account_info.get("authorization_type")
    access_token = tq_utils.get_access_token(account_info, proxies)
    headers = {"Authorization": "Bearer {}".format(access_token)}
    session_key = tq_utils.get_session_key(helper, session_key)
    if not session_key:
        return
    try:
        tq_utils.validate_existence_of_lookup(helper, session_key)
    except Exception as e:
        logger.error(
            "message=collect_events_lookup_existance_error | {}".format(str(e)))
        return

    _get_indicator_types(auth_type, helper, ew, server_url, headers, verify_cert, use_proxy, proxies, session_key)
    _get_indicator_statuses(auth_type, helper, ew, server_url, headers, verify_cert, use_proxy, proxies, session_key)
    timeout = tq_utils.get_import_timout(helper.context_meta["session_key"])
    conf_name = "threatquotient_app_settings"
    stanza_name = "match_algo_detail"
    [splunkserver, splunk_server_port, splunk_server_verify, splunk_app] = get_kvstore_rest_details(helper)
    splunk_get_custom_attributes_url = create_url(splunkserver, splunk_server_port, splunk_app, conf_name, stanza_name,
                                                  "custom_attributes")
    splunk_get_custom_fields_url = create_url(splunkserver, splunk_server_port, splunk_app, conf_name, stanza_name,
                                              "custom_fields")
    custom_attributes = get_custom_fields_from_conf(
        helper, conf_name, session_key, splunk_get_custom_attributes_url, splunk_server_verify
    )
    custom_attributes = [attr.strip() for attr in custom_attributes]
    custom_list = ''.join(custom_attributes)
    try:
        validate_attributes(custom_list)
    except Exception as e:
        logger.error(
            "message=collect_events_custom_attribute_validation_error |"
            " Error while validating custom attributes. {}".format(str(e)))
        return
    custom_fields = get_custom_fields_from_conf(
        helper, conf_name, session_key, splunk_get_custom_fields_url, splunk_server_verify
    )
    custom_fields = [field.strip().lower() for field in custom_fields]
    custom_list = ''.join(custom_fields)
    try:
        validate_attributes(custom_list)
    except Exception as e:
        logger.error(
            "message=collect_events_custom_field_validation_error |"
            " Error while validating custom fields. {}".format(str(e)))
        return
    _get_indicators(
        auth_type,
        helper,
        ew,
        server_url,
        verify_cert,
        use_proxy,
        proxies,
        timeout,
        session_key,
        custom_attributes,
        custom_fields,
    )
    _cleanup_kvstore_lookup(helper, session_key)
