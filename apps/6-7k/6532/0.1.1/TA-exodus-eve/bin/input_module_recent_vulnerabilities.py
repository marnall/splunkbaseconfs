# encoding = utf-8

import sys
import datetime
import requests
import dateutil.parser

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input,
# uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza
    configurations"""
    # This example accesses the modular input variable
    # email = definition.parameters.get('email', None)
    # password = definition.parameters.get('password', None)
    # reset = definition.parameters.get('reset', None)
    # splunk_token = definition.parameters.get('splunk_token', None)
    pass


def collect_events(helper, ew):

    APP_NAME = "TA-exodus-eve"
    SPLUNK_BASE_URL = "https://localhost:8089/servicesNS/nobody"
    KV_STORE_URL = f"{SPLUNK_BASE_URL}/{APP_NAME}/storage/collections"

    def handle_reset_option(reset):
        if reset is None:
            return None

        # First, try to load reset as an integer indicating the number
        # of days in the past to reset to
        try:
            reset = int(reset)
            return datetime.datetime.utcnow() - datetime.timedelta(days=reset)
        except TypeError as e:
            helper.log_error(f"{str(e)}")

        # Try to load reset as a ISO8601 datetime
        try:
            reset = dateutil.parser.isoparse(reset)
        except ValueError:
            helper.log_error(
                f"Did not recognize '{reset}' as a legitimate ISO8601 datetime"
            )
            sys.exit()

    def get_vulns(session, xi_reset=None):
        exodus_url = "https://vpx.exodusintel.com/"
        if xi_reset is None:
            response = session.get(exodus_url + "vpx-api/v1/vulns/recent")
            try:
                vulns = response.json()["data"]["items"]
                return vulns
            except KeyError as e:
                helper.log_error(f"Something went wrong. {e}")
                return None

        if type(xi_reset) is int:
            reset = handle_reset_option(xi_reset)
        else:
            reset = handle_reset_option(10)

        params = {"reset": reset.isoformat()}
        response = session.get(
            exodus_url + "vpx-api/v1/vulns/recent", params=params
        )
        try:
            vulns = response.json()["data"]["items"]
            return vulns
        except KeyError as e:
            logger.error(f"Something went  wrong. {e}")
            return None

    def create_kvstore(kv_store_name, headers):
        helper.log_info(f"Collection {kv_store_name} was not found!")
        # Lets create and define the collection.
        data = f"name={kv_store_name}"
        try:
            helper.log_info(
                f"Trying to create a new KVStore Collection {kv_store_name}."
            )
            response = requests.post(
                f"{KV_STORE_URL}/config",
                headers=headers,
                verify=False,
                data=data,
            )
            helper.log_info(f"This was the response {response.status_code}")
        except Exception as e:
            helper.log_error(
                f"Unable to create the KVStore Collection. ERROR: {e}"
            )
            raise ValueError(f"There was a problem. Check the splunk token {e}")

        data = "field.id=string&field.value=string"
        helper.log_info(f'Lets create the lookup definition {kv_store_name}')
        define = requests.post(
            f"{KV_STORE_URL}/config/{kv_store_name}",
            headers=headers,
            verify=False,
            data=data,
        )
        if define.status_code != 200:
            raise requests.exceptions.ConnectionError(
                f"Could not define the KVstore Collection."
            )
        return True

    def store_to_kvstore(kvstore_name, vulns, headers):
        url = f"{KV_STORE_URL}/data/{kvstore_name}"
        # STORE vulns in Collection
        for item in vulns:
            try:
                cve = item["cves"][0]
                payload = {"id": cve, "value": item}
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    verify=False,
                )
            except IndexError as e:
                helper.log_info(f"Didn't find the cve... Skipped. {e}")

    def retrive_kvstore_list(headers):
        # Get list of Collections
        kvstore_url = f"{KV_STORE_URL}/config"
        data = "output_mode=json"
        response = requests.get(
            kvstore_url,
            headers=headers,
            verify=False,
            data=data,
        )
        helper.log_info(f'Value of response.status_code')
        if response.status_code != 200:
            raise requests.exceptions.ConnectionError(
                f"There was a problem! Error."
            )
        return response.json()["entry"]

    email = helper.get_arg("email")
    password = helper.get_arg("password")
    reset = helper.get_arg("reset")
    splunk_token = helper.get_arg("splunk_token")
    kv_store_name = helper.get_arg("kv_store_name")

    # Splunk Rest API headers
    headers = dict()
    headers["Content-Type"] = "application/json"
    headers["Authorization"] = f"Bearer {splunk_token}"

    # Login to Exodus
    exodus_url = "https://vpx.exodusintel.com/"
    session = requests.Session()
    exodus_auth = {"email": email, "password": password}
    xi_response = session.post(
        exodus_url + "vpx-api/v1/login", json=exodus_auth
    )
    if xi_response.status_code != 200:
        raise requests.exceptions.ConnectionError(
            "Could not authenticate. ERROR: {response.status_code}"
        )
    # access_token = xi_response.json()["access_token"]

    collection_list = list()

    for items in retrive_kvstore_list(headers):
        helper.log_info(items["name"])
        collection_list.append(items["name"])

    # raise ValueError(f'Collections found: {collection_list}')
    if kv_store_name in collection_list:
        helper.log_info("Retrieving new vulnerabilities.")
        vulns = get_vulns(session)
        if vulns:
            store_to_kvstore(kv_store_name, vulns, headers)
    else:
        created = create_kvstore(kv_store_name, headers)

        if created:
            # Lets call VMS and reset datastream
            vulns = get_vulns(session, 1000)
            helper.log_info("Resetting Exodus Intelligence datastream.")

            # Lets populate the KV Store with Data
            store_to_kvstore(kv_store_name, vulns, headers)
            vulns = get_vulns(session)
            helper.log_info(f"Obtaining new vulnerabilities")
