# File: xforce.py
#
# Copyright (c) 2021-2025 Splunk Inc.
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

import base64

import requests


class XForceError(Exception):
    """Base Exception raised by this module."""

    def __init__(self, message="There was an ambiguous exception that occurred while using the API.", url=None, details=None):
        super().__init__(f"{message} | URL: {url} | Details: {details}")


class XForceConnectionError(XForceError):
    """Exception raised when a connection error occured with the API."""

    def __init__(self, url, details, note=None):
        message = "Error connecting to the API."
        if note:
            message = f"{message} | Note: {note}"
        super().__init__(message, url, details)


class XForceApiError(XForceError):
    """Raised when the API returns an HTTP error"""

    def __init__(self, url, response, details):
        message = f"HTTP status code: {response.status_code}. Reason: {response.reason}."
        try:
            response_data = response.json()
            if not isinstance(response_data, dict):
                response_data = {}
        except requests.exceptions.InvalidJSONError:
            response_data = {}
        details = response_data.get("message", details)
        super().__init__(message, url, details)


class xforce:
    def __init__(self, api_key, api_password, base_url="https://api.xforce.ibmcloud.com", verify_cert=False):
        self.base_url = base_url
        self.api_key = api_key
        self.api_password = api_password
        self.auth_token = api_key + ":" + api_password
        self.header = {"Authorization": ("Basic " + base64.b64encode(self.auth_token.encode("utf-8")).decode("utf-8"))}
        self.verify_cert = verify_cert

    def _send_request(self, url, method, payload=None, content_type=None):
        url = self.base_url + url
        request_func = getattr(requests, method)

        if request_func is None:
            raise ValueError("Incorrect requests action specified")

        try:
            r = request_func(url, headers=self.header, data=payload, verify=self.verify_cert)

            r.raise_for_status()
        except requests.exceptions.SSLError as err:
            raise XForceConnectionError(
                url=url,
                details=str(err),
                note='Likely due to the "validate server certificate" option.',
            )
        except requests.exceptions.ConnectionError as err:
            raise XForceConnectionError(
                url=url,
                details=str(err),
            )
        except requests.exceptions.HTTPError as err:
            raise XForceApiError(
                url=url,
                response=r,
                details=str(err),
            )
        except requests.exceptions.RequestException as err:
            raise XForceError(
                url=url,
                details=str(err),
            )

        try:
            results = r.json()
        except ValueError:
            results = r.text

        return results

    def get_dns(self, query_value):
        response = self._send_request("/resolve/" + query_value, "get")
        json_response = {"xforce_dns": response}

        return json_response

    def get_ip_report(self, ip):
        response = self._send_request("/ipr/" + ip, "get")
        json_response = {"xforce_ip_report": response}

        return json_response

    def get_ip_reputation(self, ip):
        response = self._send_request("/ipr/history/" + ip, "get")
        json_response = {"xforce_ip_reputation": response}

        return json_response

    def get_ip_malware(self, ip):
        response = self._send_request("/ipr/malware/" + ip, "get")
        json_response = {"xforce_ip_malware": response}

        return json_response

    def get_malware_report(self, file_hash):
        response = self._send_request("/malware/" + file_hash, "get")
        json_response = {"xforce_malware_report": response}

        return json_response

    def get_malware_family(self, family):
        response = self._send_request("/malware/family/" + family, "get")
        json_response = {"xforce_malware_family": response}

        return json_response

    def get_url_report(self, url):
        response = self._send_request("/url/" + url, "get")
        json_response = {"xforce_url_report": response}

        return json_response

    def get_url_malware(self, url):
        response = self._send_request("/url/malware/" + url, "get")
        json_response = {"xforce_url_malware": response}

        return json_response

    def get_whois(self, query_data):
        response = self._send_request("/whois/" + query_data, "get")
        json_response = {"xforce_whois": response}

        return json_response
