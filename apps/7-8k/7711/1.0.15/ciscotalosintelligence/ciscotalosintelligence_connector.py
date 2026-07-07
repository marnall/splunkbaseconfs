# File: ciscotalosintelligence_connector.py
#
# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#

import ipaddress
import json
import os
import random
import re
import ssl
import tempfile
import textwrap
import time
from datetime import datetime
from urllib.parse import urlparse

import httpx

# Phantom App imports
import phantom.app as phantom
import requests
from bs4 import BeautifulSoup
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom_common.install_info import is_dev_env

from ciscotalosintelligence_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


SSL_REVOKED_REASON = "SSLV3_ALERT_CERTIFICATE_REVOKED"
STATE_KEY_INVALID_CERTIFICATES = "invalid_certificates"
SUPPORT_CASE_MESSAGE = "Please open a SOAR Cloud support case for assistance."


class TalosIntelligenceConnector(BaseConnector):
    def __init__(self):
        super().__init__()

        self._state = None

        self._base_url = None
        self._cert = None
        self._certificate = None
        self._certificate_serial_number = None
        self._key = None

        self._appinfo = None
        self._catalog_id = 2

    def _format_datetime(self, date_time):
        return f"{date_time.replace(microsecond=0).isoformat()}Z"

    def _get_invalid_certificates(self):
        if not isinstance(self._state, dict):
            self._state = {}

        invalid_certificates = self._state.get(STATE_KEY_INVALID_CERTIFICATES)
        if not isinstance(invalid_certificates, dict):
            invalid_certificates = {}
            self._state[STATE_KEY_INVALID_CERTIFICATES] = invalid_certificates

        return invalid_certificates

    def _remember_invalid_certificate(self, reason):
        if not self._certificate_serial_number:
            return

        invalid_certificate = {
            "reason": reason,
            "last_seen": self._format_datetime(datetime.utcnow()),
        }

        if self._certificate:
            invalid_certificate["not_before"] = self._format_datetime(self._certificate.not_valid_before)
            invalid_certificate["not_after"] = self._format_datetime(self._certificate.not_valid_after)

        self._get_invalid_certificates()[self._certificate_serial_number] = invalid_certificate

    def _forget_invalid_certificate(self):
        if not self._certificate_serial_number:
            return

        self._get_invalid_certificates().pop(self._certificate_serial_number, None)

    def _get_certificate_validity_error(self, now):
        if now > self._certificate.not_valid_after:
            return "expired"

        if now < self._certificate.not_valid_before:
            return "not_yet_valid"

        return None

    def _get_invalid_certificate_message(self, reason):
        serial_number = self._certificate_serial_number

        if reason == "expired" and self._certificate:
            return (
                f"Certificate serial number {serial_number} is expired as of {self._format_datetime(self._certificate.not_valid_after)}. "
                f"{SUPPORT_CASE_MESSAGE}"
            )

        if reason == "not_yet_valid" and self._certificate:
            return (
                f"Certificate serial number {serial_number} is not valid until {self._format_datetime(self._certificate.not_valid_before)}. "
                f"{SUPPORT_CASE_MESSAGE}"
            )

        if reason == "revoked":
            return f"Certificate serial number {serial_number} has been revoked. {SUPPORT_CASE_MESSAGE}"

        return f"Certificate serial number {serial_number} is known to be invalid. {SUPPORT_CASE_MESSAGE}"

    def _certificate_preflight(self):
        if not self._certificate or not self._certificate_serial_number:
            return None

        now = datetime.utcnow()
        invalid_certificate = self._get_invalid_certificates().get(self._certificate_serial_number)
        if invalid_certificate:
            reason = invalid_certificate.get("reason", "invalid")
            if reason == "not_yet_valid" and now >= self._certificate.not_valid_before:
                self._forget_invalid_certificate()
            else:
                return self._get_invalid_certificate_message(reason)

        reason = self._get_certificate_validity_error(now)
        if reason:
            self._remember_invalid_certificate(reason)
            return self._get_invalid_certificate_message(reason)

        return None

    def _is_revoked_certificate_ssl_error(self, error):
        current_error = error
        seen_error_ids = set()

        while current_error and id(current_error) not in seen_error_ids:
            seen_error_ids.add(id(current_error))

            if isinstance(current_error, ssl.SSLError):
                ssl_reason = str(getattr(current_error, "reason", "")).upper()
                if ssl_reason == SSL_REVOKED_REASON or SSL_REVOKED_REASON in str(current_error).upper():
                    return True

            current_error = current_error.__cause__ or current_error.__context__

        return False

    def _handle_revoked_certificate_error(self, action_result):
        self._remember_invalid_certificate("revoked")
        return RetVal(action_result.set_status(phantom.APP_ERROR, self._get_invalid_certificate_message("revoked")), None)

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = f"Status Code: {status_code}. Data from server:\n{error_text}\n"

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    f"Unable to parse JSON response. Error: {e!s}",
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {} Data from server: {}".format(r.status_code, r.text.replace("{", "{{").replace("}", "}}"))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result, retry=3):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        retryable_error_codes = {2, 4, 8, 9, 13, 14}

        if retry < MAX_REQUEST_RETRIES:
            if r.headers.get("grpc-status", 0) in retryable_error_codes:
                err_msg = r.headers.get("grpc-message", "Error")
                return (
                    action_result.set_status(
                        phantom.APP_ERROR,
                        f"Got retryable grpc-status of {r.headers['grpc-status']} with message {err_msg}",
                    ),
                    r,
                )

            if r.status_code == 503:
                return (
                    action_result.set_status(
                        phantom.APP_ERROR,
                        f"Got retryable http status code {r.status_code}",
                    ),
                    r,
                )

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, retry, endpoint, action_result, method="get", **kwargs):
        # **kwargs can be any additional parameters that requests.request accepts

        config = self.get_config()

        resp_json = None

        # Create a URL to connect to
        url = self._base_url + endpoint

        delay = 0.25
        for i in range(MAX_CONNECTION_RETIRIES):
            try:
                request_func = getattr(self.client, method)

                r = request_func(url, **kwargs)
                return self._process_response(r, action_result, retry)
            except ssl.SSLError as e:
                if self._is_revoked_certificate_ssl_error(e):
                    return self._handle_revoked_certificate_error(action_result)

                connection_error = e
            except Exception as e:
                if self._is_revoked_certificate_ssl_error(e):
                    return self._handle_revoked_certificate_error(action_result)

                connection_error = e

            self.debug_print(f"Retrying to establish connection to the server for the {i + 1} time")
            jittered_delay = random.uniform(delay * 0.9, delay * 1.1)
            time.sleep(jittered_delay)
            delay = min(delay * 2, 256)

            with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix="test") as temp_file:
                cert_string = f"-----BEGIN CERTIFICATE-----\n{self._cert}\n-----END CERTIFICATE-----"
                cert = (
                    f"{cert_string}\n"
                    "-----BEGIN RSA PRIVATE KEY-----\n"  # pragma: allowlist secret
                    f"{self._key}\n"
                    "-----END RSA PRIVATE KEY-----\n"  # pragma: allowlist secret
                )
                temp_file.write(cert)
                temp_file.seek(0)  # Move the file pointer to the beginning for reading
                temp_file_path = temp_file.name  # Get the name of the temporary file
            self.client = httpx.Client(
                http2=True,
                verify=config.get("verify_server_cert", False),
                cert=temp_file_path,
                timeout=MAX_REQUEST_TIMEOUT,
            )

            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            if i == MAX_CONNECTION_RETIRIES - 1:
                return RetVal(
                    action_result.set_status(
                        phantom.APP_ERROR,
                        f"Error Connecting to server. Details: {connection_error!s}",
                    ),
                    resp_json,
                )

    def _make_rest_call_helper(self, *args, **kwargs):
        request_delay = 0.25
        max_processing_time = time.time() + MAX_REQUEST_TIMEOUT
        for i in range(MAX_REQUEST_RETRIES + 1):
            if time.time() > max_processing_time:
                action_result = args[1]
                return (
                    action_result.set_status(
                        phantom.APP_ERROR,
                        f"Max request timeout of {MAX_REQUEST_TIMEOUT}s exceeded",
                    ),
                    None,
                )

            ret_val, response = self._make_rest_call(i, *args, **kwargs)
            if phantom.is_fail(ret_val) and response:
                time.sleep(request_delay)
                request_delay *= 2
            else:
                break

        return ret_val, response

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress("Connecting to endpoint")

        prev_perf_testing_val = self._appinfo["perf_testing"]
        self._appinfo["perf_testing"] = True

        payload = {"urls": [{"raw_url": "cisco.com"}], "app_info": self._appinfo}
        ret_val, response = self._make_rest_call_helper(ENDPOINT_QUERY_REPUTATION_V3, action_result, method="post", json=payload)

        self._appinfo["perf_testing"] = prev_perf_testing_val

        if phantom.is_fail(ret_val):
            self.save_progress("Test Connectivity Failed.")
            return action_result.get_status()

        self.save_progress("Received Metadata")
        self.save_progress("Test Connectivity Passed")

        invalid_certificates = self._get_invalid_certificates() or {}
        self._state = {STATE_KEY_INVALID_CERTIFICATES: invalid_certificates}

        return action_result.set_status(phantom.APP_SUCCESS)

    def format_ip_type(self, ip_addr):
        if isinstance(ip_addr, ipaddress.IPv4Address):
            return {"ipv4_addr": int(ip_addr)}
        elif isinstance(ip_addr, ipaddress.IPv6Address):
            return {"ipv6_addr": ip_addr.packed.hex()}
        else:
            raise Exception(f"{ip_addr} is not valid")

    def _handle_ip_reputation(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        ip = param["ip"]

        try:
            ip_addr = ipaddress.ip_address(ip)
            ip_request = self.format_ip_type(ip_addr)
        except Exception:
            return action_result.set_status(
                phantom.APP_ERROR,
                (
                    f"{ip} is not a valid IPv4 or IPv6 address. Perhaps you meant to use the 'domain reputation' "
                    "or 'url reputation' action instead of 'ip reputation'?"
                ),
            )

        payload = {"urls": {"endpoint": [ip_request]}, "app_info": self._appinfo}

        ret_val = self._query_reputation(action_result, payload, ip)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        summary = action_result.update_summary({})
        threat_level = action_result.get_data()[0]["Threat_Level"]
        summary["message"] = f"{ip} has a {threat_level} threat level"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _is_valid_domain(self, domain):
        regex = r"^(?!-)([A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,}$"
        return bool(re.match(regex, domain))

    def _handle_domain_reputation(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        domain = param["domain"]
        if not self._is_valid_domain(domain):
            return action_result.set_status(
                phantom.APP_ERROR,
                (
                    f"{domain} is not a valid domain name. Perhaps you meant to use the "
                    "'ip reputation' or 'url reputation' action instead of 'domain reputation'?"
                ),
            )

        url_entry = {"raw_url": domain}

        payload = {"urls": [], "app_info": self._appinfo}
        payload["urls"].append(url_entry)

        ret_val = self._query_reputation(action_result, payload, domain)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        summary = action_result.update_summary({})
        threat_level = action_result.get_data()[0]["Threat_Level"]
        summary["message"] = f"{domain} has a {threat_level} threat level"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _is_valid_url(self, url):
        parsed_url = urlparse(url)
        return bool(parsed_url.scheme and parsed_url.netloc)

    def _handle_url_reputation(self, param):
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        action_result = self.add_action_result(ActionResult(dict(param)))

        url = param["url"]
        if not self._is_valid_url(url):
            return action_result.set_status(
                phantom.APP_ERROR,
                (
                    f"{url} is not a valid URL. Perhaps you meant to use the 'ip reputation' "
                    "or 'domain reputation' action instead of 'url reputation'?"
                ),
            )

        url_entry = {"raw_url": url}

        payload = {"urls": [], "app_info": self._appinfo}
        payload["urls"].append(url_entry)

        ret_val = self._query_reputation(action_result, payload, url)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        summary = action_result.update_summary({})
        threat_level = action_result.get_data()[0]["Threat_Level"]
        summary["message"] = f"{url} has a {threat_level} threat level"
        return action_result.set_status(phantom.APP_SUCCESS)

    def _query_reputation(self, action_result, payload, observable=None):
        taxonomy_ret_val, taxonomy = self._fetch_taxonomy(action_result)

        if phantom.is_fail(taxonomy_ret_val):
            return action_result.get_status()
        # make rest call
        ret_val, response = self._make_rest_call_helper(ENDPOINT_QUERY_REPUTATION_V3, action_result, method="post", json=payload)
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        response_taxonomy_map_version = response["taxonomy_map_version"]
        if response_taxonomy_map_version > self._state["taxonomy_version"]:
            taxonomy_ret_val, taxonomy = self._fetch_taxonomy(action_result, allow_cache=False)

        if phantom.is_fail(ret_val) or "results" not in response:
            return action_result.get_status()

        threat_level = ""
        threat_categories = {}
        aup_categories = {}

        for result in response["results"]:
            for url_result in result["results"]:
                for tag in url_result["context_tags"]:
                    tax_id = str(tag["taxonomy_id"])
                    entry_id = str(tag["taxonomy_entry_id"])

                    if tax_id not in taxonomy["taxonomies"]:
                        continue

                    if not taxonomy["taxonomies"][tax_id]["is_avail"]:
                        continue

                    category = taxonomy["taxonomies"][tax_id]["name"]["en-us"]["text"]
                    name = taxonomy["taxonomies"][tax_id]["entries"][entry_id]["name"]["en-us"]["text"]
                    description = taxonomy["taxonomies"][tax_id]["entries"][entry_id]["description"]["en-us"]["text"]

                    if category == "Threat Levels":
                        threat_level = name
                    elif category == "Threat Categories":
                        threat_categories[name] = description
                    elif category == "Acceptable Use Policy Categories":
                        aup_categories[name] = description

            output = {}
            output["Observable"] = observable
            output["Threat_Level"] = threat_level
            output["Threat_Categories"] = ", ".join(list(threat_categories.keys()))
            output["AUP"] = ", ".join(list(aup_categories.keys()))

            action_result.add_data(output)

            return phantom.APP_SUCCESS

    def _fetch_taxonomy(self, action_result, allow_cache=True):
        payload = {"app_info": self._appinfo}

        if "taxonomy" in self._state and allow_cache:
            return 1, self._state["taxonomy"]

        ret_val, response = self._make_rest_call_helper(ENDPOINT_QUERY_TAXONOMIES, action_result, method="post", json=payload)
        self.debug_print("fetching taxonomy")
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        taxonomy = response["catalogs"][str(self._catalog_id)]

        self._state["taxonomy"] = taxonomy
        self._state["taxonomy_version"] = response["version"]

        return ret_val, taxonomy

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        preflight_error = self._certificate_preflight()
        if preflight_error:
            action_result = self.add_action_result(ActionResult(dict(param)))
            return action_result.set_status(phantom.APP_ERROR, preflight_error)

        if action_id == "ip_reputation":
            ret_val = self._handle_ip_reputation(param)

        if action_id == "domain_reputation":
            ret_val = self._handle_domain_reputation(param)

        if action_id == "url_reputation":
            ret_val = self._handle_url_reputation(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def fetch_crls(self, cert):
        try:
            crl_distribution_points = cert.extensions.get_extension_for_oid(x509.ExtensionOID.CRL_DISTRIBUTION_POINTS).value

            crl_urls = []

            for point in crl_distribution_points:
                for general_name in point.full_name:
                    if isinstance(general_name, x509.DNSName):
                        crl_urls.append(f"http://{general_name.value}")
                    elif isinstance(general_name, x509.UniformResourceIdentifier):
                        crl_urls.append(general_name.value)

            return crl_urls
        except x509.ExtensionNotFound:
            self.debug_print("CRL Distribution Points extension not found in the certificate.")
            return []

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state() or {}

        # get the asset config
        config = self.get_config()

        def insert_newlines(string, every=64):
            lines = []
            for i in range(0, len(string), every):
                lines.append(string[i : i + every])

            return "\n".join(lines)

        self._base_url = config["base_url"]
        self._cert = insert_newlines(config["certificate"])
        self._key = insert_newlines(config["key"])

        cert_string = f"-----BEGIN CERTIFICATE-----\n{textwrap.fill(self._cert, 64)}\n-----END CERTIFICATE-----"
        cert_pem_data = cert_string.encode("utf-8")
        try:
            cert = x509.load_pem_x509_certificate(cert_pem_data, default_backend())
        except Exception as e:
            self.debug_print(f"Error when loadig cert {e}")
            return phantom.APP_ERROR

        self._certificate = cert
        self._certificate_serial_number = format(cert.serial_number, "X")

        self._appinfo = {
            "product_family": "splunk",
            "product_id": "soar",
            "device_id": self.get_product_installation_id(),
            "product_version": self.get_app_json()["app_version"],
            "perf_testing": False,
        }
        if is_dev_env():
            self._appinfo["perf_testing"] = True

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix="test") as temp_file:
            cert = (
                f"{cert_string}\n"
                "-----BEGIN RSA PRIVATE KEY-----\n"  # pragma: allowlist secret
                f"{textwrap.fill(self._key, 64)}\n"
                "-----END RSA PRIVATE KEY-----\n"  # pragma: allowlist secret
            )

            temp_file.write(cert)
            temp_file.seek(0)  # Move the file pointer to the beginning for reading
            temp_file_path = temp_file.name  # Get the name of the temporary file

        # exceptions shouldn't really be thrown here because most network related disconnections will happen when a request is sent
        try:
            self.client = httpx.Client(
                http2=True,
                verify=config.get("verify_server_cert", False),
                cert=temp_file_path,
                timeout=MAX_REQUEST_TIMEOUT,
            )
        except Exception as e:
            self.debug_print(f"Could not connect to server because of {e}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return phantom.APP_ERROR

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = TalosIntelligenceConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = TalosIntelligenceConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
