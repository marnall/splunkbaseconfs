# encoding = utf-8
import certifi
import datetime
from urllib.parse import urljoin
import re
import requests
import time
from typing import Union, List

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


def verify_email(email):
    """Verify email's format.

    Args:
        email: email address.

    Raises:
        ValueError: If `email` is not a string.
        ValueError: If `email` format is invalid.

    Returns:
        bool: True
    """
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if type(email) is not str:
        raise ValueError("Email is not a string.")
    if not re.fullmatch(regex, email):
        raise ValueError("Invalid email.")
    return True


def validate_input(helper, definition):
    pass


def primary_identifier(vuln_identifiers: List[str]) -> str:
    """The "most important" identifier associated with the vulnerability.

    :rtype: str
    """
    for i in vuln_identifiers:
        if i.lower().startswith("cve"):
            return i
        if i.lower().startswith("zdi"):
            return i
        if i.lower().startswith("eip"):
            return i
        if i.lower().startswith("exp"):
            return i
        if i.lower().startswith("exn"):
            return i
    return vuln_identifiers[0]


class ToKVStore:
    def __init__(self, splunk_token, certificate=False):
        self.app_name = "TA-exodusintelligence"
        self.splunk_token = splunk_token
        self.session = requests.Session()
        self.url = "https://localhost:8089/servicesNS/nobody/"
        self.kvstore_url = self.url + f"{self.app_name}/storage/collections"
        self.cert_verify = certificate
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {splunk_token}",
            }
        )

    def create_kvstore(self, helper, kv_store_name, fields):
        helper.log_debug(f"Creating collection {kv_store_name}")
        try:
            response = self.session.post(
                url=self.kvstore_url + "/config",
                data=f"name={kv_store_name}",
                verify=self.cert_verify,
            )
        except Exception as e:
            helper.log_debug(
                f"create_kvstore: Unable to create collection {kv_store_name}. {e} "
            )
            raise ValueError(f"There was an error {e}")

        response = self.session.post(
            url=self.kvstore_url + f"/config/{kv_store_name}",
            data=fields,
            verify=self.cert_verify,
        )
        helper.log_info(self.kvstore_url)

        if response.status_code != 200:
            raise requests.exceptions.ConnectionError(
                "Could not define the KVstore Collection."
            )
        return True

    def get_kvstore(self, helper, kvstorename):
        response = self.session.get(
            url=self.kvstore_url + f"/data/{kvstorename}",
            verify=self.cert_verify,
        )
        return response

    def get_all_kvstore(self, helper):
        data = "output_mode=json"
        helper.log_debug(self.kvstore_url)
        response = self.session.get(
            url=self.kvstore_url,
            data=data,
            verify=self.cert_verify,
        )
        if response.status_code != 200:
            raise requests.exceptions.ConnectionError("Error getting KV Store")
        return response.json().get("entry")

    def add_cve(self, helper, kv_store_name, vuln):
        # cve = vuln.get("identifiers")[0]
        cve = primary_identifier(vuln.get("identifiers"))
        modified_at = vuln.get("cvemodified")
        payload = {"_key": cve, "id": cve, "value": vuln}
        url = self.kvstore_url + f"/data/{kv_store_name}"
        try:
            response = self.session.post(
                url=url,
                json=payload,
                verify=self.cert_verify,
            )
            if response.status_code == 409:
                record = self.session.get(
                    url=f"{url}/{cve}",
                    verify=self.cert_verify,
                )
                if modified_at != record.json().get("cvemodified"):
                    self.session.post(
                        url=f"{url}/{cve}",
                        json=payload,
                        verify=self.cert_verify,
                    )
        except Exception as e:
            helper.log_debug(f"Skipped CVE {e}")

    def state_update(
        self,
        helper,
        collection,
        genesis,
        last_ingestion,
        pre_populated,
        status=None,
    ):
        context = {
            "_key": "config",
            "id": 0,
            "value": {
                "genesis": genesis,
                "last_ingestion": last_ingestion,
                "pre-populated": pre_populated,
            },
        }

        response = self.session.post(
            url=self.kvstore_url + f"/data/{collection}",
            json=context,
            verify=self.cert_verify,
        )
        if response.status_code == 409:
            url = self.kvstore_url + f"/data/{collection}/config"
            response = self.session.post(
                url=url,
                json=context,
                verify=self.cert_verify,
            )
        return response


class Eve:
    def __init__(self, helper, email, password) -> None:
        self.url = "https://eve.exodusintel.com/vpx-api/v2"
        self.helper = helper
        if verify_email(email):
            self.email = email
        self.session = requests.Session()
        self.password = password
        self.token = self.get_access_token()

        self.csrf_token = [
            c.value
            for c in self.session.cookies
            if c.name == "csrf_access_token"
        ][0]

    def get_access_token(self) -> str:
        """Obtain access token.

        :raises requests.exceptions.ConnectionError: API is Unavailable.
        :return: A token
        :rtype: str
        """
        url = urljoin("https://eve.exodusintel.com/", "vpx-api/v1/login")
        response = self.session.post(
            url,
            json={"email": self.email, "password": self.password},
        )
        if response.status_code != 200:
            raise requests.exceptions.ConnectionError("Could not authenticate")
        return response.json().get("access_token")

    def transform_data(self, vulns):
        anon_fields = {
            "published_on": "published",
            "modified_at": "cvemodified",
            # "created_at": "creationdate",
            "affected_cpes": "affectedcpes",
            "relevant_cpe_products": "relevantcpeproducts",
            "attack_vector": "attackvector",
            "cvss": "cvss3",
            "cwe": "cwe",
            "external_links": "externallinks",
            "identifiers": "indicatoridentification",
            "products": "products",
            "public_summary": "cvedescription",
            "title": "title",
            "vendors": "vendors",
            "enriched": "enriched",
        }
        silver_fields = {
            "patch_available": "patchavailable",
            "patch_timeline": "timeline",
            "spatial": "spatial",
            # "xi_scores": "*",
            # "current_xi_score": "currentXiScore",
            "vector": "vector",
            # "xi_summary": "xiSummary",
        }
        gold_fields = {
            "attachments": "*",
            "attack_delivery": "attackdelivery",
            "deployment": "deployment",
            "detections": "detections",
            "impacts": "impacts",
            "mitigation": "mitigation",
            "notes": "notes",
            "prod_background": "product_background",
            "related_identifiers": "feedrelatedindicators",
            "user_interaction": "user_interaction_required",
            "mitre_attack": "MitreAttack",
        }
        keys_list = {**anon_fields, **silver_fields, **gold_fields}

        splunk_ready = {
            "affectedcpes": [],
            "externallinks": [],
            "detections": [],
            "feedrelatedindicators": [],
            "impacts": [],
            "notes": [],
            "timeline": [],
            "mitreAttack": [],
            "vector": [],
            "files": [],
        }
        for i in list(vulns.keys()):
            if i in keys_list:
                if i == "affected_cpes":
                    for v in list(vulns[i]):
                        splunk_ready["affectedcpes"].append(
                            {
                                "cpes": vulns[i][v].get("cpes"),
                            }
                        )
                elif i == "external_links":
                    for v in list(vulns[i]):
                        splunk_ready["externallinks"].append(
                            {"url": f"{vulns[i][v]['url']}"}
                        )
                elif i == "cvss":
                    splunk_ready["cvssscore"] = vulns[i]["score"]
                    splunk_ready["cvssvector"] = vulns[i]["vector"]
                elif i == "identifiers":
                    splunk_ready["cveIdentifier"] = primary_identifier(
                        vulns[i]
                    )
                    splunk_ready["identifiers"] = vulns[i]
                elif i == "current_xi_score":
                    pass
                    # splunk_ready["currentXiScore"] = {
                        # "comment": vulns[i].get("comment", None),
                        # "score": vulns[i].get("score", None),
                        # "res_difficulty": vulns[i].get("res_difficulty", None),
                        # "attack_details": vulns[i].get("attack_details", None),
                        # "pub_knowledge": vulns[i].get("pub_knowledge", None),
                        # "poc_avail": vulns[i].get("poc_avail", None),
                        # "pub_velocity": vulns[i].get("pub_velocity", None),
                    # }
                elif i == "detections":
                    for v in list(vulns[i]):
                        splunk_ready["detections"].append(
                            {
                                "type": vulns[i][v]["det_type"],
                                "contents": vulns[i][v]["contents"],
                            }
                        )
                elif i == "related_identifiers":
                    for v in list(vulns[i]):
                        splunk_ready["feedrelatedindicators"].append(
                            {
                                "value": v,
                            }
                        )
                elif i == "notes":
                    for v in list(vulns[i]):
                        splunk_ready["notes"].append(
                            {
                                "note": vulns[i][v]["note"],
                            }
                        )
                elif i == "patch_timeline":
                    pass
                    # for v in list(vulns[i]):
                    #     splunk_ready["timeline"].append(
                    #         {
                    #             "date": vulns[i][v]["ts"],
                    #             "label": vulns[i][v]["label"],
                    #         }
                    #     )
                elif i == "xi_scores":
                    pass
                    # for v in list(vulns[i]):
                    #     splunk_ready["xiScores"].append(
                    #         {
                    #             "score": vulns[i][v]["score"],
                    #             "comment": vulns[i][v]["comment"],
                    #             "res_difficulty": vulns[i][v][
                    #                 "res_difficulty"
                    #             ],
                    #             "attack_details": vulns[i][v][
                    #                 "attack_details"
                    #             ],
                    #             "pub_knowledge": vulns[i][v]["pub_knowledge"],
                    #             "poc_avail": vulns[i][v]["poc_avail"],
                    #             "pub_velocity": vulns[i][v]["pub_velocity"],
                    #         }
                    #     )
                elif i == "spatial":
                    splunk_ready["spatial"] = {
                        "funcs": vulns[i]["funcs"]
                        if "funcs" in vulns[i]
                        else None,
                        "params": vulns[i]["params"]
                        if "params" in vulns[i]
                        else None,
                        "source_files": vulns[i]["source_files"]
                        if "source_files" in vulns[i]
                        else None,
                        "methods": vulns[i]["methods"]
                        if "methods" in vulns[i]
                        else None,
                        "miscellaneous": vulns[i]["miscellaneous"]
                        if "miscellaneous" in vulns[i]
                        else None,
                        "modules": vulns[i]["modules"]
                        if "modules" in vulns[i]
                        else None,
                    }
                elif i == "mitigation":
                    if "note" in vulns[i] and vulns[i]["note"] != "":
                        splunk_ready["mitigation"] = {
                            "note": vulns[i].get("note"),
                        }
                elif i == "attack_delivery":
                    splunk_ready["attack_delivery"] = {
                        "applayers": vulns[i].get("applayers"),
                        "encryption": vulns[i].get("encryption"),
                        "transports": vulns[i].get("transports"),
                        # "file_extensions": vulns[i].get("file_extensions"),
                        # "file_formats": vulns[i].get("file_formats"),
                        # "mime_types": vulns[i].get("mime_types"),
                    }
                elif i == "impacts":
                    for v in list(vulns[i]):
                        splunk_ready["impacts"].append(
                            {
                                "cpe": vulns[i][v]["cpe"],
                                "label": vulns[i][v]["label"],
                            }
                        )
                elif i == "mitre_attack":
                    if i in vulns and vulns[i]:
                        for v in list(vulns[i]):
                            splunk_ready["mitreAttack"].append(
                                {
                                    "identifier": vulns[i][v]["identifier"],
                                    "technique": vulns[i][v]["technique"],
                                    "sub_techniques": vulns[i][v][
                                        "sub_techniques"
                                    ],
                                    "tactics": vulns[i][v]["tactics"],
                                }
                            )
                elif i == "attachments":
                    pass
                    # if i in vulns and vulns[i]:
                    #     for v in list(vulns[i]):
                            # splunk_ready["files"].append(
                            #     {
                            #         "type": vulns[i][v]["type"],
                            #         "mimetype": vulns[i][v]["mimetype"],
                            #         "size": vulns[i][v]["size"],
                            #         "label": vulns[i][v]["label"],
                            #     }
                            # )
                            # TODO: This would actually be the pdf
                            # if vulns[i][v]["label"] == "contents.md":
                            #     key = PrivateKey.generate()
                            #     box = SealedBox(key)
                            #     pub_key = key.public_key.encode(
                            #         encoder=nacl.encoding.URLSafeBase64Encoder
                            #     ).decode()
                            #     single_vuln = splunk_ready["cveIdentifier"]
                            #     report_return = self.session.get(
                            #         f"{self.url}/vulnerabilities/{single_vuln}/report",
                            #         params={"pubkey": pub_key},
                            #     ).json()
                            #     splunk_ready["report"] = box.decrypt(
                            #         base64.b64decode(report_return["report"])
                            #     ).decode()
                elif i == "vector":
                    for v in list(vulns[i]):
                        splunk_ready["vector"].append(
                            {
                                "cpe": vulns[i][v]["cpe"],
                                "label": vulns[i][v]["label"],
                            }
                        )
                else:
                    splunk_ready[keys_list[i]] = vulns.get(i)
        return splunk_ready

    def get_vulns(
        self,
        reset: Union[str, None] = None,
        after: Union[str, None] = None,
        sort_field: str = "modified_at",
        direction: str = "descending",
        limit: int = 50,
        ingest_from_date: str = ""
    ) -> dict:
        params = {}
        if reset is not None:
            params["since"] = reset
        if after is not None:
            params["after"] = after
        params["limit"] = limit
        # TODO: sort_field and direction were removed to ingest everything, 
        #  might not be needed though
        self.helper.log_debug(f"URL: {self.url}, params: {params}")
        try:
            if(ingest_from_date):
                response = self.session.get(
                    url=self.url + "/vulnerabilities/search?since=" + ingest_from_date,
                    params=params,
                )
            else:
                response = self.session.get(
                    url=self.url + "/vulnerabilities/search",
                    params=params,
                )
        except ConnectionError as e:
            raise Exception(f"There was an error: {e}")

        return response.json()


class EveAnonymous(Eve):
    def __init__(self, helper, path):
        self.url = "https://eve.exodusintel.com/" + path
        self.session = requests.Session()
        self.helper = helper


def collect_events(helper, ew):
    anonymous = helper.get_arg("anonymous")
    certificate = False
    # certificate = helper.get_arg("valid_tls_certificate")
    ingest_from_date = helper.get_arg("ingest_from_date")
    email = helper.get_arg("email")
    password = helper.get_arg("password")
    splunk_token = helper.get_arg("splunk_token")
    kv_store_name = "eve_api"
    eve_app_config = "eve_config"
    reset = "1970-01-01T00:00:00"
    limit = 250
    grand_total = 0

    if not anonymous:
        exodus = Eve(helper, email, password)
    else:
        exodus = EveAnonymous(helper, "vpx-api/v2/anonymous/")

    mykvstore = ToKVStore(splunk_token=splunk_token, certificate=certificate)

    # Create a config kvstore if there is none
    try:
        state = (
            mykvstore.get_kvstore(helper, kv_store_name).json()[0].get("value")
        )
    except (requests.exceptions.JSONDecodeError, IndexError) as e:
        helper.log_debug(f"Collection {eve_app_config} not found")
        fields = {"field.id": "number", "field.value": "string"}
        mykvstore.create_kvstore(helper, eve_app_config, fields)
        mykvstore.state_update(
            helper,
            eve_app_config,
            genesis=reset,
            last_ingestion=None,
            pre_populated=False,
            status="reset",
        )

        state = (
            mykvstore.get_kvstore(helper, eve_app_config)
            .json()[0]
            .get("value")
        )

    vulns_collection = mykvstore.get_kvstore(helper, kv_store_name)

    if vulns_collection.status_code > 400:
        fields = {"field.id": "string", "field.value": "string"}
        mykvstore.create_kvstore(helper, kv_store_name, fields)
        vulns_collection = mykvstore.get_kvstore(helper, kv_store_name)

    if state.get("pre-populated"):
        command = "fetch"
        direction = "descending"
        sort_field = "modified_at"
        reset = (
            state.get("last_ingestion")
            if state.get("last_ingestion") is not None
            else reset
        )
    else:
        command = "reset"
        direction = "ascending"
        sort_field = "published_on"
        reset = (
            state.get("genesis") if state.get("genesis") is not None else reset
        )

    after_cursor = None
    control = True
    page = 1
    while control:
        response = exodus.get_vulns(
            reset=reset,
            limit=limit,
            direction=direction,
            sort_field=sort_field,
            after=after_cursor,
            ingest_from_date=ingest_from_date
        )
        vulns = response.get("vulnerabilities")
        after_cursor = response.get("after_cursor", None)
        count = response["count"]
        helper.log_debug(
            f"Page: {page} of {round(count / 250)}, Count: {count}, After: {after_cursor}"
        )

        if len(vulns) < 1:
            control = False
            if not state.get("pre-populated"):
                state["pre-populated"] = True

        for item in vulns:
            to_splunk = exodus.transform_data(item)
            mykvstore.add_cve(
                helper, kv_store_name=kv_store_name, vuln=to_splunk
            )

        if after_cursor is None:
            control = False
            if not state.get("pre-populated"):
                state["pre-populated"] = True

        if command == "reset":
            state["genesis"] = vulns[0].get("published_on")
        else:
            state["last_ingestion"] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            reset = state["last_ingestion"]

        mykvstore.state_update(
            helper,
            eve_app_config,
            genesis=state["genesis"],
            last_ingestion=state.get("last_ingestion"),
            pre_populated=state.get("pre-populated"),
            status=command,
        )

        page += 1
        grand_total += len(vulns)

    helper.log_info(f"Total vulnerabilities ingested {grand_total}")



