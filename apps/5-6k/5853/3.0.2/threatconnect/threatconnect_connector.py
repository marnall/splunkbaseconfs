# File: threatconnect_connector.py
#
# Copyright (c) 2016-2025 Splunk Inc.
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
# Phantom imports
import base64
import hashlib
import hmac
import ipaddress
import time
from datetime import datetime, timedelta

import phantom.app as phantom

# library imports
import requests
import simplejson as json
from bs4 import BeautifulSoup
from django.utils.dateparse import parse_datetime
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from requests import Request

# App-specific imports
from threatconnect_consts import *


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class ThreatconnectConnector(BaseConnector):
    # List of all of the actions that are available for this app
    ACTION_ID_HUNT_FILE = "hunt_file"
    ACTION_ID_HUNT_HOST = "hunt_host"
    ACTION_ID_HUNT_URL = "hunt_url"
    ACTION_ID_HUNT_EMAIL = "hunt_email"
    ACTION_ID_HUNT_IP = "hunt_ip"
    ACTION_ID_LIST_OWNERS = "list_owners"
    ACTION_ID_POST_DATA = "post_data"
    ACTION_ID_ON_POLL = "on_poll"
    TEST_ASSET_CONNECTIVITY = "test_asset_connectivity"

    def __init__(self):
        super().__init__()
        self._state = {}

    def is_positive_int(self, value):
        try:
            value = int(value)
            return True if value >= 0 else False
        except Exception:
            return False

    def is_positive_non_zero_int(self, value):
        try:
            value = int(value)
            return True if value > 0 else False
        except Exception:
            return False

    def _test_connectivity(self, params):
        action_result = self.add_action_result(ActionResult(params))

        self.save_progress(f"Using base url: {self._get_url()}")

        self.save_progress("Requesting a list of all owners visible to this user...")

        ret_val, resp_json = self._make_rest_call(action_result, THREATCONNECT_ENDPOINT_TEST)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not resp_json["status"]:
            return action_result.set_status(phantom.APP_ERROR, "There was an error in parsing the response", resp_json)
        elif resp_json["status"] != "Success":
            return action_result.set_status(phantom.APP_ERROR, "Test Connectivity Failed", resp_json)

        self.save_progress("Test Connectivity Passed")

        return action_result.set_status(phantom.APP_SUCCESS, "Test Connectivity Passed")

    def _list_owners(self, params):
        action_result = self.add_action_result(ActionResult(params))

        self.save_progress(f"Using base url: {self._get_url()}")

        self.save_progress("Requesting a list of all owners visible to this user...")

        ret_val, resp_json = self._make_rest_call(action_result, THREATCONNECT_ENDPOINT_TEST)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not resp_json.get("status"):
            return action_result.set_status(phantom.APP_ERROR, "There was an error in parsing the response", resp_json)
        elif resp_json.get("status") != "Success":
            return action_result.set_status(phantom.APP_ERROR, "Unable to List Owners", resp_json)

        self.save_progress("List owners succeeded.")
        action_result.add_data(resp_json)
        total_objects = int(resp_json["count"])
        action_result.set_summary({"num_owners": total_objects})

        return action_result.set_status(phantom.APP_SUCCESS, "List owners succeeded")

    def _hunt_file(self, param):
        # _hunt_file action
        return self._hunt_indicator(param)

    def _hunt_ip(self, param):
        # _hunt_ip action
        return self._hunt_indicator(param)

    def _hunt_url(self, param):
        # _hunt_url action
        return self._hunt_indicator(param)

    def _hunt_email(self, param):
        # _hunt_email action
        return self._hunt_indicator(param)

    def _hunt_host(self, param):
        # _hunt_host action
        return self._hunt_indicator(param)

    def _create_payload_for_hunt_indicator(self, action_result, params):
        for key, indicator_type in INDICATOR_MAPPING_JSON_TO_FIELD.items():
            if indicator_to_hunt := params.get(key):
                break
        else:
            if indicator_to_hunt := params.get(THREATCONNECT_JSON_IP):
                try:
                    ipaddress.ip_address(indicator_to_hunt)
                    indicator_type = THREATCONNECT_INDICATOR_FIELD_ADDRESS
                except ValueError:
                    return action_result.set_status(phantom.APP_ERROR, "Parameter 'ip' failed validation"), None
            elif hunt_me := params.get(THREATCONNECT_JSON_DOMAIN):
                if phantom.is_domain(hunt_me):
                    indicator_to_hunt, indicator_type = (
                        hunt_me,
                        THREATCONNECT_INDICATOR_FIELD_HOST,
                    )
                elif phantom.is_url(hunt_me):
                    indicator_to_hunt, indicator_type = (
                        hunt_me,
                        THREATCONNECT_INDICATOR_FIELD_URL,
                    )
                else:
                    return action_result.set_status(phantom.APP_ERROR, "Could not resolve parameter type"), None

        payload = {
            "fields": [],
            "tql": f"typeName IN ('{indicator_type}') AND summary CONTAINS '{indicator_to_hunt}'",
        }

        # Append fields if parameters are present
        payload["fields"].extend(field for key, field in INDICATOR_ATTRIBUTE_MAPPING_JSON_TO_FIELD.items() if params.get(key))

        if owners := params.get(THREATCONNECT_JSON_OWNER):
            if isinstance(owners, list):
                owners_list = owners
            else:
                owners_list = [owner.strip() for owner in owners.replace(";", ",").split(",") if owner.strip()]

            payload["tql"] += f" and ownerName in ({', '.join(map(repr, owners_list))})"

        return phantom.APP_SUCCESS, payload

    def _hunt_indicator(self, params):
        action_result = self.add_action_result(ActionResult(params))

        ret_val, payload = self._create_payload_for_hunt_indicator(action_result, params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Make the rest call
        ret_val, response = self._make_rest_call(
            action_result,
            endpoint=THREATCONNECT_ENDPOINT_INDICATOR_BASE,
            params=payload,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if response["status"] == THREATCONNECT_STATUS_FAILURE:
            return action_result.set_status(phantom.APP_ERROR, "Response failed", response["message"])

        action_result.add_data(response)
        action_result.set_summary({"total_objects": len(response["data"])})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _create_payload_for_post_data(self, action_result, params):
        primary_field = params[THREATCONNECT_JSON_PRIMARY_FIELD]
        body = {}
        if params.get(THREATCONNECT_JSON_RATING):
            body["rating"] = params.get(THREATCONNECT_JSON_RATING)
        if params.get(THREATCONNECT_JSON_CONFIDENCE):
            body["confidence"] = params.get(THREATCONNECT_JSON_CONFIDENCE)

        # Process primary field(s)
        values = [v.strip() for v in primary_field.replace(";", ",").split(",") if v.strip()]
        if len(values) > 1:
            for value in values:
                value_type, indicator_type = self._check_hash_type(value)
                if phantom.is_fail(value_type):
                    return (
                        action_result.set_status(phantom.APP_ERROR, indicator_type),
                        None,
                        None,
                    )
                body[value_type] = value

            body["type"] = indicator_type
        elif values:
            value_type, indicator_type = self._get_data_type(values[0])
            if phantom.is_fail(value_type):
                return (
                    action_result.set_status(phantom.APP_ERROR, indicator_type),
                    None,
                    None,
                )
            body[value_type] = values[0]

            body["type"] = indicator_type
        else:
            return action_result.set_status(phantom.APP_ERROR, THREATCONNECT_NO_ENDPOINT_ERR), None, None

        # Add additional fields based on type
        if indicator_type == THREATCONNECT_INDICATOR_FIELD_HOST:
            body.update(
                {
                    "dnsActive": params.get(THREATCONNECT_JSON_DNSACTIVE),
                    "whoisActive": params.get(THREATCONNECT_JSON_WHOISACTIVE),
                }
            )
        elif indicator_type == THREATCONNECT_INDICATOR_FIELD_FILE:
            body["size"] = params.get(THREATCONNECT_JSON_SIZE)

        param = {"fields": []}

        if (attribute_name := params.get(THREATCONNECT_JSON_ATTRIBUTE_NAME)) and (
            attribute_value := params.get(THREATCONNECT_JSON_ATTRIBUTE_VALUE)
        ):
            body[THREATCONNECT_ATTRIBUTE] = {
                "data": [
                    {
                        "type": attribute_name,
                        "value": attribute_value,
                        "default": True,
                    }
                ]
            }
            param["fields"].append(THREATCONNECT_ATTRIBUTE)

        for key, value in INDICATOR_ATTRIBUTE_MAPPING_JSON_TO_FIELD.items():
            field_value = params.get(key)
            if field_value:
                body[value] = {"data": [{"name": field_value}]}
            param["fields"].append(value)

        return phantom.APP_SUCCESS, body, param

    def _post_data(self, params):
        action_result = self.add_action_result(ActionResult(params))

        endpoint = THREATCONNECT_ENDPOINT_INDICATOR_BASE
        ret_val, body, params = self._create_payload_for_post_data(action_result=action_result, params=params)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        if not params["fields"]:
            params = {}

        ret_val, response = self._make_rest_call(action_result, endpoint, body=body, params=params, rtype=THREATCONNECT_POST)

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, "Data successfully posted to ThreatConnect")

    def _on_poll(self, params):
        action_result = self.add_action_result(ActionResult(dict(params)))

        last_time = self._state.get(THREATCONNECT_JSON_LAST_DATE_TIME)

        config = self.get_config()

        if self.is_poll_now():
            num_of_days = int(config.get(THREATCONNECT_JSON_DEF_NUM_DAYS, THREATCONNECT_DAYS_TO_POLL))

            start_time = datetime.utcfromtimestamp(time.time() - (num_of_days * THREATCONNECT_SECONDS_IN_A_DAY)).strftime(DATETIME_FORMAT)

            self._container_limit = int(params[THREATCONNECT_CONFIG_POLL_NOW_CONTAINER_LIMIT])

        else:
            self._container_limit = int(
                config.get(
                    THREATCONNECT_JSON_CONTAINER_LIMIT,
                    THREATCONNECT_CONTAINER_LIMIT_DEFAULT,
                )
            )

            num_of_days = int(config.get(THREATCONNECT_JSON_DEF_NUM_DAYS, THREATCONNECT_DAYS_TO_POLL))

            if self._state.get("first_run", True):
                # Only goes here when its the first time polling with on_poll
                self._state["first_run"] = False

                start_time = self._first_poll(num_of_days)

            elif last_time:
                # Last polled time is taken here
                start_time = last_time
            else:
                # Fallback: use first_poll if no last_time is available
                start_time = self._first_poll(num_of_days)

        self.save_progress(f"Start time for polling: {start_time}")

        self.save_progress(f"Querying for Indicators created between {datetime.utcnow().strftime(DATETIME_FORMAT)} and {start_time}")

        self.save_progress("Making REST call for ingestion")

        endpoint = THREATCONNECT_ENDPOINT_INDICATOR_BASE

        ret_val, resp_json = self._make_rest_call(action_result, endpoint)

        if phantom.is_fail(ret_val):
            self.save_progress("REST Call failed during ingestion")

            return self.set_status(phantom.APP_ERROR)

        self.save_progress("Saving containers and artifacts")

        ret_val, message = self._create_containers(resp_json, start_time)

        if phantom.is_fail(ret_val):
            return action_result.set_status(phantom.APP_ERROR, message)

        return action_result.set_status(phantom.APP_SUCCESS, "Polling has succeeded")

    def _first_poll(self, number_of_days):
        """
        First poll will get the UNIX time for number_of_days ago and then convert it into zulu format
        """
        return datetime.utcfromtimestamp(time.time() - (number_of_days * THREATCONNECT_SECONDS_IN_A_DAY)).strftime(DATETIME_FORMAT)

    def _create_containers(self, resp_json, start_time):
        """Returns 2 values, use RetVal"""

        # List of indicators that have been passed over... To be reversed later when written yanno????
        possible_indicators = []

        # Convert the start_time determined by on_poll to UNIX timestamp to compare to the indicator
        start_time_unix = int(parse_datetime(start_time).strftime("%s"))

        # Iterate through all the indicators starting at the top of the list (which should be most recent)
        for indicator in resp_json["data"]:
            indicator["dateAdded"] = parse_datetime(indicator["dateAdded"]).strftime(DATETIME_FORMAT)

            # Convert the indicator's dateAdded string to a UNIX timestamp to make life easier for everyone
            indicator_date_added_unix = int(parse_datetime(indicator["dateAdded"]).strftime("%s"))

            # Add the indicator to save it for later because runtime is important!!!
            possible_indicators.append(indicator)

            # If the indicator is passed up and it's not the oldest possible one, save it for later
            if start_time_unix < indicator_date_added_unix:
                continue
            # Successfully found the indicator to stop at.
            elif start_time_unix > indicator_date_added_unix:
                ret_val, message = self._iterate_indicators(possible_indicators)
                if phantom.is_fail(ret_val):
                    return RetVal(phantom.APP_ERROR, message)

                return RetVal(phantom.APP_SUCCESS, message)

        if len(possible_indicators) == 0:
            return RetVal(phantom.APP_SUCCESS, "No new indicators")  # NO NEW INDICATORS

        ret_val, message = self._iterate_indicators(possible_indicators)

        if phantom.is_fail(ret_val):
            return RetVal(phantom.APP_ERROR, message)

        return RetVal(phantom.APP_SUCCESS, "Success")

    def _iterate_indicators(self, indicator_list):
        """
        Iterates through the recorded indicators in to ingest the correct containers count
        """
        container_limit = self._container_limit if self._container_limit < len(indicator_list) else len(indicator_list)

        successful_container_count = 0

        beginning_of_polling_date = indicator_list[-1]["dateAdded"]

        for indicator in reversed(indicator_list):
            # Required fields that are present in every Indicator
            required_fields = {
                "summary": str(indicator["summary"]),
                "indicator_type": str(indicator["type"]).lower(),
                "date_created": str(indicator["dateAdded"]),
                "date_modified": str(indicator["lastModified"]),
                "indicator_id": indicator["id"],
            }

            # Optional fields that are not present in every indicator but we want to ingest them anyways
            optional_cef_fields = {
                "rating": indicator.get("rating"),
                "confidence": indicator.get("confidence"),
                "threatAssessRating": indicator.get("threatAssessRating"),
                "threatAssessConfidence": indicator.get("threatAssessConfidence"),
                "md5": indicator.get("md5"),
                "sha1": indicator.get("sha1"),
                "sha256": indicator.get("sha256"),
            }

            # Get the needed artifact details
            cef_name, cef_field, cef_type = self._get_cef_details(required_fields)

            # Create the necessary container and artifact dicts with necessary fields
            container, artifact = self._get_base_dicts(required_fields, cef_name)

            # Add any additional CEF fields to the artifact
            artifact = self._get_optional_cef_fields(
                required_fields,
                artifact,
                optional_cef_fields,
                cef_name,
                cef_field,
                cef_type,
            )

            # Create the container
            ret_val, container_message, id = self.save_container(container)

            # Increment the container count if container not dupicate
            if "duplicate" not in container_message.lower():
                successful_container_count += 1

            # Pull the ID from the container and add it to the artifact
            artifact["container_id"] = id

            # Add the artifact to that container
            ret_val, artifact_message, id = self.save_artifact(artifact)

            # Break the loop when the container_limit set in the config is reached.
            if successful_container_count == container_limit:
                # Only update the state file if its not poll now
                if phantom.is_fail(self.is_poll_now()):
                    # Update the state in order to use the correct date for the next ingestion cycle.
                    date_to_use = self._state.get(THREATCONNECT_JSON_LAST_DATE_TIME)

                    if date_to_use is None:
                        self._state[THREATCONNECT_JSON_LAST_DATE_TIME] = beginning_of_polling_date
                    elif date_to_use == indicator["dateAdded"]:
                        start_time = (parse_datetime(indicator["dateAdded"]) + timedelta(seconds=1)).strftime(DATETIME_FORMAT)

                        self._state[THREATCONNECT_JSON_LAST_DATE_TIME] = start_time

                        return (
                            phantom.APP_ERROR,
                            "Some indicators may have been dropped due to max containers being "
                            "smaller than the amount of indicators in a given second.  Please increase "
                            "the max_containers in order to ensure no dropped indicators.",
                        )
                    else:
                        # As long as the indicator date and the date in the state are not the same then replace it
                        self._state[THREATCONNECT_JSON_LAST_DATE_TIME] = indicator["dateAdded"]
                break

        return phantom.APP_SUCCESS, ("Success" if successful_container_count else "No new indicators found")

    def _get_optional_cef_fields(
        self,
        required_fields,
        artifact_base,
        optional_cef_fields,
        cef_name,
        cef_field,
        cef_type,
    ):
        updated_artifact = artifact_base
        summary = required_fields["summary"]

        # Add the common optional fields first
        if optional_cef_fields["rating"]:
            updated_artifact["cef"].update({"rating": str(optional_cef_fields["rating"])})
        if optional_cef_fields["confidence"]:
            updated_artifact["cef"].update({"confidence": optional_cef_fields["confidence"]})
        if optional_cef_fields["threatAssessRating"]:
            updated_artifact["cef"].update({"threatAssessRating": optional_cef_fields["threatAssessRating"]})
        if optional_cef_fields["threatAssessConfidence"]:
            updated_artifact["cef"].update({"threatAssessConfidence": optional_cef_fields["threatAssessConfidence"]})
        if optional_cef_fields["md5"]:
            updated_artifact["cef"].update({"fileHashMd5": optional_cef_fields["md5"]})
            updated_artifact["cef_types"].update({"fileHashMd5": ["md5"]})
        if optional_cef_fields["sha1"]:
            updated_artifact["cef"].update({"fileHashSha1": optional_cef_fields["sha1"]})
            updated_artifact["cef_types"].update({"fileHashSha1": ["sha1"]})
        if optional_cef_fields["sha256"]:
            updated_artifact["cef"].update({"fileHashSha256": optional_cef_fields["sha256"]})
            updated_artifact["cef_types"].update({"fileHashSha256": ["sha256"]})

        # Add the indicator under the cef field cn1 if the type could not be determined
        if not cef_name and not cef_field and not cef_type:
            updated_artifact["cef"].update({"ioc": required_fields["summary"]})

        # Specific formatting for CIDR indicators
        elif cef_name == "CIDR Artifact":
            updated_artifact["cef"].update(
                {
                    cef_field[0]: required_fields["summary"].split("/")[0],
                    cef_field[1]: required_fields["summary"].split("/")[1],
                    cef_field[2]: required_fields["summary"],
                }
            )
            updated_artifact["cef_types"] = {
                cef_field[0]: [cef_type[0]],
                cef_field[2]: [cef_type[2]],
            }

        # Specific formatting for Registry Key indicators
        elif cef_name == "Registry Key Artifact":
            registry, value_name, value_type = required_fields["summary"].split(" : ")
            updated_artifact["cef"].update(
                {
                    "registryKey": registry,
                    "registryValue": value_name,
                    "registryType": value_type,
                }
            )

        # Final clause if the cef name is not listed above and if the indicator is not a file
        else:
            updated_artifact["cef"].update({cef_field: summary})
            if cef_type:
                updated_artifact["cef_types"].update({cef_field: [cef_type]})

        return updated_artifact

    def _get_base_dicts(self, required_fields, cef_name):
        """
        Creates the container and artifact dict with values that are absolutely required.
        :return: base container, base artifact
        """
        indicator_id = required_fields["indicator_id"]
        container = {
            "name": THREATCONNECT_INGEST_CONTAINER_NAME.format(summary=required_fields["summary"]),
            "description": "Ingested indicator from ThreatConnect",
            "source_data_identifier": indicator_id,
        }

        artifact = {
            "container_id": None,
            "label": "event",
            "type": "None",
            "name": cef_name,
            "source_data_identifier": indicator_id,
            "cef": {
                "deviceCustomDate1": required_fields["date_created"],
                "deviceCustomDate1Label": "Date Created",
                "deviceCustomDate2": required_fields["date_modified"],
                "deviceCustomDate2Label": "Last Modified",
            },
            "cef_types": {},
        }
        return container, artifact

    def _check_hash_type(self, primary_field):
        if phantom.is_md5(primary_field):
            return RetVal("md5", THREATCONNECT_INDICATOR_FIELD_FILE)
        elif phantom.is_sha1(primary_field):
            return RetVal("sha1", THREATCONNECT_INDICATOR_FIELD_FILE)
        elif phantom.is_sha256(primary_field):
            return RetVal("sha256", THREATCONNECT_INDICATOR_FIELD_FILE)
        return RetVal(phantom.APP_ERROR, THREATCONNECT_NO_ENDPOINT_ERR)

    def _get_data_type(self, primary_field):
        """Returns two Values, use RetVal"""

        try:
            ipaddress.ip_address(primary_field)
            return RetVal("ip", THREATCONNECT_INDICATOR_FIELD_ADDRESS)
        except ValueError:
            if phantom.is_email(primary_field):
                return RetVal("address", THREATCONNECT_INDICATOR_FIELD_EMAIL)
            elif phantom.is_md5(primary_field):
                return RetVal("md5", THREATCONNECT_INDICATOR_FIELD_FILE)
            elif phantom.is_sha1(primary_field):
                return RetVal("sha1", THREATCONNECT_INDICATOR_FIELD_FILE)
            elif phantom.is_sha256(primary_field):
                return RetVal("sha256", THREATCONNECT_INDICATOR_FIELD_FILE)
            elif phantom.is_url(primary_field):
                return RetVal("text", THREATCONNECT_INDICATOR_FIELD_URL)
            elif phantom.is_domain(primary_field):
                if "." in primary_field:
                    return RetVal("hostName", THREATCONNECT_INDICATOR_FIELD_HOST)
        return RetVal(phantom.APP_ERROR, THREATCONNECT_NO_ENDPOINT_ERR)

    def _get_cef_details(self, required_fields):
        #  Indicator types are value checked because the rest of the indicators, to check are ones with only one type.
        # Address indicators for example will have IPv4, IPv6, etc.
        indicator_type = required_fields["indicator_type"]
        summary = required_fields["summary"]
        if indicator_type == "mutex":
            return "Mutex Artifact", "mutex", None
        if indicator_type == "cidr":
            return (
                "CIDR Artifact",
                ["deviceAddress", "cidrPrefix", "cidr"],
                ["ip", None, "CIDR"],
            )
        elif indicator_type == "registry key":
            return "Registry Key Artifact", "registryKey", None
        elif indicator_type == "asn":
            return "ASN Artifact", "asn", None
        elif indicator_type == "user agent":
            return "User Agent Artifact", "requestClientApplication", None
        elif phantom.is_email(summary):
            return "Email Address Artifact", "emailAddress", "email"
        elif phantom.is_md5(summary):
            return "File Artifact", "fileHash", "md5"
        elif phantom.is_sha1(summary):
            return "File Artifact", "fileHash", "sha1"
        elif phantom.is_sha256(summary):
            return "File Artifact", "fileHash", "sha256"
        elif phantom.is_url(summary):
            return "URL Artifact", "requestURL", "url"
        elif phantom.is_ip(summary):
            return "IP Artifact", "deviceAddress", "ip"
        try:
            ipaddress.ip_address(summary)
            return "IP Artifact", "deviceCustomIPv6Address1", "ipv6"
        except Exception:
            if phantom.is_domain(summary):
                return "Domain Artifact", "deviceDnsDomain", "domain"
            return None, None, None

    def _create_header(self, endpoint, params={}, json={}, rtype=THREATCONNECT_GET):
        config = self.get_config()

        api_id = config[THREATCONNECT_CONFIG_ACCESS_ID]
        secret_key = config[THREATCONNECT_CONFIG_SECRET_KEY]
        url = self._get_url() + endpoint

        # ITS "TIME" TO AUTHENTICATE
        # ThreatConnect likes it in this format
        timestamp_nonce = str(int(time.time()))
        # Prepare the url in case there are params that need to be encoded
        encoded_url = Request(rtype, url, params=params, json=json).prepare().path_url
        # Prepare the signature to be signed by the HMAC
        signature_raw = f"{encoded_url}:{rtype.upper()}:{timestamp_nonce}"
        # Autograph time
        try:
            signature_hmac = hmac.new(str(secret_key), signature_raw, digestmod=hashlib.sha256).digest()
            authorization = f"TC {api_id}:{base64.b64encode(signature_hmac)}"
        except Exception:
            signature_hmac = hmac.new(secret_key.encode(), signature_raw.encode(), digestmod=hashlib.sha256).digest()
            authorization = f"TC {api_id}:{base64.b64encode(signature_hmac).decode()}"

        header = {
            "Content-Type": "application/json",
            "Timestamp": timestamp_nonce,
            "Authorization": authorization,
        }

        return header

    def _process_empty_reponse(self, response, action_result):
        if 200 <= response.status_code < 205:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, is bound to be an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except Exception:
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
                action_result.set_status(phantom.APP_ERROR, "Unable to parse response as JSON", e),
                None,
            )

        if 200 <= r.status_code < 205:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        action_result.add_data(resp_json)
        message = r.text.replace("{", "{{").replace("}", "}}")
        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR,
                f"Error from server, Status Code: {r.status_code} data returned: {message}",
            ),
            resp_json,
        )

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if an error occurs
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})
            action_result.add_debug_data({"r_status_code": r.status_code})

        # There are just too many differences in the response to handle all of them in the same function
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not an html or json, handle if it is a successfull empty reponse
        if (200 <= r.status_code < 205) and (not r.text):
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {} Data from server: {}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, action_result, endpoint, params={}, body={}, rtype=THREATCONNECT_GET):
        """Returns 2 values, use RetVal"""

        url = self._get_url() + endpoint

        config = self.get_config()

        try:
            headers = self._create_header(endpoint, params=params, rtype=rtype, json=body)
        except Exception as e:
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Handled exception: {e!s}"),
                None,
            )
        try:
            request_func = getattr(requests, rtype)
        except AttributeError:
            # Set the action_result status to error, the handler function will most probably return as is
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Unsupported method: {rtype}"),
                None,
            )
        except Exception as e:
            # Set the action_result status to error, the handler function will most probably return as is
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Handled exception: {e!s}"),
                None,
            )

        try:
            response = request_func(
                url,
                params=params,
                json=body,
                headers=headers,
                verify=config.get("verify_server_cert", False),
            )
        except Exception as e:
            # Set the action_result status to error, the handler function will most probably return as is
            return RetVal(
                action_result.set_status(phantom.APP_ERROR, f"Error connecting: {e!s}"),
                None,
            )

        # Added line
        try:
            self.debug_print("raw_response: ", response.json())
        except Exception:
            self.debug_print("text_raw_response: ", response.text)

        return self._process_response(response, action_result)

    def _get_url(self):
        config = self.get_config()
        if "sandbox.threatconnect.com" in config[THREATCONNECT_BASE_URL]:
            return THREATCONNECT_SANDBOX_API_URL.format(base=config[THREATCONNECT_BASE_URL]) + "/"
        else:
            return THREATCONNECT_API_URL.format(base=config[THREATCONNECT_BASE_URL]) + "/"

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        config[THREATCONNECT_BASE_URL] = config[THREATCONNECT_BASE_URL].rstrip("/")

        max_containers = config.get("max_containers", None)
        if not (max_containers is None or self.is_positive_non_zero_int(max_containers)):
            return self.set_status(
                phantom.APP_ERROR,
                'Please provide a positive, non zero integer in config parameter "max_containers"',
            )

        interval_days = config.get("interval_days", None)
        if not (interval_days is None or self.is_positive_non_zero_int(interval_days)):
            return self.set_status(
                phantom.APP_ERROR,
                'Please provide a positive, non zero integer in config parameter "interval_days"',
            )

        return phantom.APP_SUCCESS

    def finalize(self):
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        """
        This function handles all of the actions that the app can handle.

        """
        action = self.get_action_identifier()

        ret_val = phantom.APP_SUCCESS

        # Find the correct action to use
        if action == self.ACTION_ID_POST_DATA:
            ret_val = self._post_data(param)
        elif action == self.TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_connectivity(param)
        elif action == self.ACTION_ID_HUNT_IP:
            ret_val = self._hunt_ip(param)
        elif action == self.ACTION_ID_HUNT_FILE:
            ret_val = self._hunt_file(param)
        elif action == self.ACTION_ID_HUNT_HOST:
            ret_val = self._hunt_host(param)
        elif action == self.ACTION_ID_HUNT_EMAIL:
            ret_val = self._hunt_email(param)
        elif action == self.ACTION_ID_HUNT_URL:
            ret_val = self._hunt_url(param)
        elif action == self.ACTION_ID_LIST_OWNERS:
            ret_val = self._list_owners(param)
        elif action == self.ACTION_ID_ON_POLL:
            ret_val = self._on_poll(param)

        return ret_val


if __name__ == "__main__":
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="verify",
        required=False,
        default=False,
    )

    args = argparser.parse_args()
    session_id = None
    verify = args.verify

    if args.username and args.password:
        login_url = BaseConnector._get_phantom_base_url() + "login"
        try:
            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=THREATCONNECT_DEFAULT_TIMEOUT)
            csrftoken = r.cookies["csrftoken"]
            data = {
                "username": args.username,
                "password": args.password,
                "csrfmiddlewaretoken": csrftoken,
            }
            headers = {
                "Cookie": f"csrftoken={csrftoken}",
                "Referer": login_url,
            }

            print("Logging into Platform to get the session id")
            r2 = requests.post(
                login_url,
                verify=verify,
                data=data,
                timeout=THREATCONNECT_DEFAULT_TIMEOUT,
                headers=headers,
            )
            session_id = r2.cookies["sessionid"]

        except Exception as e:
            print(f"Unable to get session id from the platform. Error: {e!s}")
            sys.exit(1)

    if len(sys.argv) < 2:
        print("No test json specified as input")
        sys.exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ThreatconnectConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)
