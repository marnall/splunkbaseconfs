# encoding = utf-8
import certifi
import sys
import datetime
import requests

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
EXODUS_URL = "https://eve.exodusintel.com/"
marker = []


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
    APP_NAME = "TA-eve-client-for-splunk"
    SPLUNK_BASE_URL = "https://localhost:8089/servicesNS/nobody"
    KV_STORE_URL = f"{SPLUNK_BASE_URL}/{APP_NAME}/storage/collections"

    def handle_reset_option(reset):
        pass

    def transform_data(vulns):
        keys_list = {
            "identifiers": "indicatoridentification",
            "published_on": "published",
            "modified_at": "cvemodified",
            "created_at": "creationdate",
            "cvss": "cvss3",
            "public_summary": "cvedescription",
            "title": "title",
            "vendors": "vendors",
            "impacts": "impacts",
            "products": "products",
            "xi_scores": "xiscores",
            "relevant_cpe_products": "relevantcpeproducts",
            "affected_cpes": "affectedcpes",
            "attack_vector": "attackvector",
            "external_links": "externallinks",
            "cwe": "cwe",
            "transport": "transport",
            "encryption": "encryption",
            "attachments": "attachments",
            "attack_delivery": "attackdelivery",
            "patch_available": "patchavailable",
            "deployment": "deployment",
            "mitigation": "mitigation",
            "spatial": "spatial",
            "detections": "detections",
            "related_identifiers": "feedrelatedindicators",
        }

        demisto_ready = {
            "affectedcpes": [],
            "externallinks": [],
            "detections": [],
            "feedrelatedindicators": [],
            "impacts": [],
        }
        for i in list(vulns.keys()):
            if i in keys_list:
                if i == "affected_cpes":
                    for v in list(vulns[i]):
                        demisto_ready["affectedcpes"].append(
                            {
                                "cpes": vulns[i][v].get("cpes"),
                            }
                        )
                elif i == "external_links":
                    for v in list(vulns[i]):
                        demisto_ready["externallinks"].append(
                            {"url": f"{vulns[i][v]['url']}"}
                        )
                elif i == "cvss":
                    demisto_ready["cvssscore"] = vulns[i]["score"]
                    demisto_ready["cvssvector"] = vulns[i]["vector"]
                elif i == "identifiers":
                    for v in vulns[i]:
                        if v[:3] == "CVE":
                            demisto_ready["cvss"] = v
                    demisto_ready["identifiers"] = vulns[i]
                elif i == "xi_scores":
                    for v in list(vulns[i]):
                        demisto_ready["xiscore"] = vulns[i][v]["score"]
                elif i == "detections":
                    for v in list(vulns[i]):
                        demisto_ready["detections"].append(
                            {
                                "det_type": vulns[i][v]["det_type"],
                                "contents": vulns[i][v]["contents"],
                            }
                        )
                elif i == "related_identifiers":
                    for v in list(vulns[i]):
                        demisto_ready["feedrelatedindicators"].append(
                            {
                                "value": v,
                            }
                        )
                elif i == "spatial":
                    demisto_ready["spatial"] = {
                        "funcs": vulns[i]["funcs"],
                    }
                elif i == "mitigation":
                    demisto_ready["mitigation"] = {
                        "author": vulns[i].get("author"),
                        "note": vulns[i].get("note"),
                        "created": vulns[i].get("ts_created"),
                        "vis": vulns[i].get("vis"),
                    }
                elif i == "attack_delivery":
                    demisto_ready["attack_delivery"] = {
                        "applayers": vulns[i].get("applayers"),
                        "encryption": vulns[i].get("encryption"),
                        "transports": vulns[i].get("transports"),
                    }
                elif i == "impacts":
                    for v in list(vulns[i]):
                        demisto_ready["impacts"].append(
                            {"cpe": vulns[i][v]["cpe"], "label": vulns[i][v]["label"]}
                        )
                else:
                    demisto_ready[keys_list[i]] = vulns.get(i)
        return demisto_ready

    def get_vulns(session, from_date=None, before=None, after=None):
        exodus_url = EXODUS_URL
        response = session.get(exodus_url + "vpx-api/v2/vulnerabilities")
        splunk_ready = []
        try:
            vulns = response.json()["vulnerabilities"]
            for i in vulns:
                splunk_ready.append(transform_data(i))
            return splunk_ready
        except KeyError as e:
            helper.log_error(f"Something went wrong. {e}")
            return None

    def get_test_vuln(session, cve):
        exodus_url = EXODUS_URL
        response = session.get(exodus_url + f"vpx-api/v2/vulnerabilities/{cve}")
        return response.json()

    def create_kvstore(kv_store_name, headers):
        helper.log_info(f"Collection {kv_store_name} was not found!")
        # Lets create and define the collection.
        data = f"name={kv_store_name}"
        try:
            helper.log_info(
                f"Trying to create a new KVStore Collection {kv_store_name}."
            )
            cert_path = certifi.where()
            response = requests.post(
                f"{KV_STORE_URL}/config",
                headers=headers,
                verify=cert_path,
                data=data,
            )
            helper.log_info(f"This was the response {response.status_code}")
        except Exception as e:
            helper.log_error(f"Unable to create the KVStore Collection. ERROR: {e}")
            raise ValueError(f"There was a problem. Check the splunk token {e}")

        data = "field.id=string&field.value=string"
        helper.log_info(f"Lets create the lookup definition {kv_store_name}")
        define = requests.post(
            f"{KV_STORE_URL}/config/{kv_store_name}",
            headers=headers,
            verify=certifi.where(),
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
        item = vulns
        # for item in vulns:
        try:
            cve = item.get("identifiers")[0]
            payload = {"id": cve, "value": item}
            requests.post(
                url,
                headers=headers,
                json=payload,
                verify=certifi.where(),
            )
        except IndexError as e:
            helper.log_info(f"Didn't find the cve... Skipped. {e}")

    def retrieve_kvstore_list(headers):
        # Get list of Collections
        kvstore_url = f"{KV_STORE_URL}/config"
        data = "output_mode=json"
        response = requests.get(
            kvstore_url,
            headers=headers,
            verify=certifi.where(),
            data=data,
        )
        if response.status_code != 200:
            raise requests.exceptions.ConnectionError("There was a problem! Error.")
        return response.json()["entry"]

    email = helper.get_arg("email")
    password = helper.get_arg("password")
    splunk_token = helper.get_arg("splunk_token")
    kv_store_name = "eve"
    from_date = helper.get_arg("from_date")

    if from_date != "2023-01-01" and from_date != "":
        from_date = from_date + " 00:00:00"
        from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
        try:
            from_date = datetime.datetime.isoformat(from_date)
        except:
            helper.log_error("Check the date format")
    else:
        from_date = None

    # Splunk Rest API headers
    headers = dict()
    headers["Content-Type"] = "application/json"
    headers["Authorization"] = f"Bearer {splunk_token}"

    # Login to Exodus
    exodus_url = EXODUS_URL
    session = requests.Session()
    exodus_auth = {"email": email, "password": password}
    xi_response = session.post(exodus_url + "vpx-api/v1/login", json=exodus_auth)
    if xi_response.status_code != 200:
        raise requests.exceptions.ConnectionError(
            f"Could not authenticate. ERROR: {xi_response.status_code}"
        )

    collection_list = list()

    for items in retrieve_kvstore_list(headers):
        helper.log_info(items["name"])
        collection_list.append(items["name"])

    if kv_store_name in collection_list:
        helper.log_info("Retrieving new vulnerabilities.")
        vulns = get_vulns(session, from_date)

        for i in vulns:
            store_to_kvstore(kv_store_name, i, headers)
    else:
        created = create_kvstore(kv_store_name, headers)

        if created:
            control = True
            # Lets call VMS and reset datastream
            if from_date:
                response = session.get(
                    exodus_url
                    + f"vpx-api/v2/vulnerabilities?since={from_date}&limit=250"
                )
            else:
                from_date = datetime.datetime.strptime(
                    "2023-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
                response = session.get(
                    exodus_url + f"vpx-api/v2/vulnerabilities?since={from_date}&limit=250"
                )

            try:
                vulns = response.json()["vulnerabilities"]
            except KeyError as e:
                helper.log_error(f"Something went wrong. {e}")
            try:
                after = response.json()["after_cursor"]
            except KeyError as e:
                helper.log_error(f"Something went wrong. {e}")
                after = None

            while len(vulns) and control:
                helper.log_info(f"FROM DATE {from_date}")
                helper.log_info(f"FROM CURSOR {after}")
                for i in vulns:
                    #helper.log_error(f"FROM STORETOKVSTORE {i}")
                    store_to_kvstore(kv_store_name, transform_data(i), headers)
                if after is None:
                    control = False
                helper.log_error(
                    f"THIS IS WHAT WE ARE LOOKING AT: vpx-api/v2/vulnerabilities?since={from_date}&after={after}&limit=250"
                )
                response = session.get(
                    exodus_url
                    + f"vpx-api/v2/vulnerabilities?since={from_date}&after={after}&limit=250"
                )
                try:
                    vulns = response.json()["vulnerabilities"]
                except KeyError as e:
                    helper.log_error(f"Something went wrong. {e}")
                try:
                    after = response.json()["after_cursor"]
                except KeyError as e:
                    helper.log_error(f"Data no more!!!. {e}")
                    after = None
                helper.log_info("Obtaining new vulnerabilities")
