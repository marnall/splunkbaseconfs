import os
import sys
import urllib.parse

from state_store import Credentials

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import logging
import sys

import validators
from cyberintegrations import TIPoller
from cyberintegrations.utils import ParserHelper
from splunk.clilib import cli_common as cli
from splunklib.modularinput import *
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch


class AppConsts:
    APP_NAME = "gib_tia"
    LOG_FILE_DIRECTORY = os.environ["SPLUNK_HOME"] + "/var/log/splunk/" + APP_NAME
    PRODUCT_DATA_FOR_POLLER = {
        "product_type": "SIEM",
        "product_name": "Splunk",
        "integration_name": "Group-IB Threat Intelligence",
        "integration_version": "1.9.0",
    }
    PATH_LIST = [
        "malware/cnc",
        "malware/malware",
        "attacks/ddos",
        "attacks/deface",
        "attacks/phishing_kit",
        "attacks/phishing_group",
        "common/threat",
        "apt/threat",
        "hi/threat",
        "osi/public_leak",
        "suspicious_ip/tor_node",
        "suspicious_ip/socks_proxy",
        "suspicious_ip/open_proxy",
        "suspicious_ip/scanner",
        "suspicious_ip/vpn",
        "ioc/common",
    ]
    IP = {
        "Attribution": {
            "Collection name": "api.collection",
            "Threat actor": "api.threatActor.name",
        },
        "Details": {"Source": "api.source", "Categories": "api.categories"},
        "Activity Dates": {
            "dateFirstSeen": "api.dateFirstSeen",
            "dateLastSeen": "api.dateLastSeen",
            "dateBegin": "api.dateBegin",
            "dateEnd": "api.dateEnd",
            "dateReg": "api.dateReg",
            "dateAdd": "api.dateAdd",
            "dateIncident": "api.dateIncident",
            "dateDetected": "api.dateDetected",
            "dataCompromised": "api.dataCompromised",
        },
        "Graph whois data": "graph",
        "credibility/reliability/admiraltyCode": {
            "credibility": "api.evaluation.credibility",
            "reliability": "api.evaluation.reliability",
            "admiraltyCode": "api.evaluation.admiraltyCode",
        },
        "TLP": "api.evaluation.tlp",
    }
    DOMAIN = {
        "Attribution": {
            "Collection name": "api.collection",
            "Threat actor": "api.threatActor.name",
        },
        "Activity Dates": {
            "dateFirstSeen": "api.dateFirstSeen",
            "dateLastSeen": "api.dateLastSeen",
            "dateBegin": "api.dateBegin",
            "dateEnd": "api.dateEnd",
            "dateReg": "api.dateReg",
            "dateAdd": "api.dateAdd",
            "dateIncident": "api.dateIncident",
            "dateDetected": "api.dateDetected",
            "dataCompromised": "api.dataCompromised",
        },
        "Graph whois data": {
            "createdAt": "graph.createdAt",
            "updatedAt": "graph.updatedAt",
            "Zone": "graph.zone",
            "Domain Name": "graph.whois.domain_name",
            "Registrar": "graph.whois.registrar",
            "Creation Date": "graph.whois.creation_date",
            "Expiration Date": "graph.whois.expiration_date",
            "Updated Date": "graph.whois.updated_date",
            "Status": "graph.whois.status",
            "Name Servers": "graph.whois.name_servers",
        },
        "credibility/reliability/admiraltyCode": {
            "credibility": "api.evaluation.credibility",
            "reliability": "api.evaluation.reliability",
            "admiraltyCode": "api.evaluation.admiraltySCode",
        },
        "TLP": "api.evaluation.tlp",
        "Related  URLs": "api.url",
    }
    HASH = {
        "Attribution": {
            "Collection name": "api.collection",
            "Threat actor": "api.threatActor.name",
            "Threat actor list": "api.threatActorList.name",
            "TA list": "api.threatList.name",
            "Title": "api.threatList.title",
        },
        "Name/Aliases": {
            "Name": "api.name",
            "Malware list": "api.malwareList.name",
            "Aliases": "api.aliases",
            "Aliases list": "api.malwareAliasList",
            "Category": "api.category",
        },
        "Activity Dates": {
            "createdAt": "graph.created_at",
            "updatedAt": "graph.updated_at",
            "dateFirstSeen": "api.dateFirstSeen",
            "dateLastSeen": "api.dateLastSeen",
            "dateBegin": "api.dateBegin",
            "dateEnd": "api.dateEnd",
            "dateReg": "api.dateReg",
            "dateAdd": "api.dateAdd",
            "dateIncident": "api.dateIncident",
            "dateDetected": "api.dateDetected",
            "dataCompromised": "api.dataCompromised",
        },
        "File details": {
            "Author": "contacts.account",
            "Country": "threatActor.sourceCountry",
            "Type": "api.type",
        },
        "Info": {
            "Credibility": "api.evaluation.credibility",
            "Reliability": "api.evaluation.reliability",
            "AdmiraltyCode": "api.evaluation.admiraltyCode",
            "Threat level": "api.threatLevel",
        },
        "CVE": {
            "name": "api.cveList.name",
            "vendor": "api.cveList.products.vendor",
            "product": "api.cveList.products.product",
        },
        "Tags": "api.expertise",
        "Hashes": {
            "md5": "api.params.hashes.md5",
            "sha1": "api.params.hashes.sha1",
            "sha256": "api.params.hashes.sha256",
        },
    }
    IP_GRAPH = {
        "Graph whois data": {
            "created": "valuesRaw.created",
            "modified": "valuesRaw.modified",
            "org": "values.org",
            "organisation": "values.organisation",
            "org-name": "valuesRaw.org-name",
            "address": "values.address",
            "addr": "valuesRaw.address",
            "contact": "values.contact",
            "country": "values.country",
            "descr": "values.descr",
            "email": "values.email",
            "inetnum": "values.inetnum",
            "nethandle": "values.nethandle",
            "netname": "values.netname",
            "origin": "values.origin",
            "parent": "values.parent",
            "phone": "values.phone",
            "role": "values.role",
            "source": "values.source",
            "status": "values.status",
            "type": "values.type",
        }
    }


class Utils:
    log_sizes = {
        "small": 100 * 1024 * 1024,  # 100 MB
        "normal": 2 * 1024 * 1024 * 1024,  # 2 GB
    }
    
    @staticmethod
    def get_logger(use_small_log_size = False, use_debug_log_level = False):
        """
        Returns a logger instance with the specified configuration.
        """
        logger = logging.getLogger(AppConsts.APP_NAME)
        logging.propagate = False
        logger.setLevel(logging.DEBUG if bool(int(use_debug_log_level)) == True else logging.INFO)
        if not os.path.exists(AppConsts.LOG_FILE_DIRECTORY):
            os.makedirs(AppConsts.LOG_FILE_DIRECTORY)
        log_path = os.path.join(AppConsts.LOG_FILE_DIRECTORY, "modinput_search.log")
        
        if logger.hasHandlers():
            logger.handlers.clear()
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=(
                Utils.log_sizes["small"]
                if bool(int(use_small_log_size)) is True
                else Utils.log_sizes["normal"]
            ),
            backupCount=1,
        )
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug("Logger Initialized")

        return logger

    @staticmethod
    def select_mask(tip):
        tips = {
            "domain": AppConsts.DOMAIN,
            "ip": AppConsts.IP,
            "hash": AppConsts.HASH,
            "ip_graph": AppConsts.IP_GRAPH,
        }
        return tips[tip]

    @staticmethod
    def read_conf(path):
        with open("../local/inputs.conf") as conf:
            for item in conf:
                if path in item:
                    c = item.split("=")
                    return c[1].strip()





@Configuration(type="reporting")
class gibsearch(GeneratingCommand):
    search = Option(require=True)
    username = Option(require=False)

    def reform_data(self, item, logger):
        logger.info("Reforming data for item")
        for key, value in item.items():
            if isinstance(value, dict):
                logger.debug(f"Reforming dictionary field: {key}")
                reform = item[key]
                item[key] = ""
                _ = {k: v for k, v in reform.items() if v}
                for k, v in _.items():
                    if isinstance(v, list):
                        if isinstance(v[0], list):
                            if any(i for i in v[0] if i):
                                item[key] += f'{k}: {", ".join(i for i in v[0] if i)}\n'
                        else:
                            if any(i for i in v if i):
                                item[key] += f'{k}: {", ".join(i for i in v if i)}\n'
                    else:
                        item[key] += f"{k}: {v}\n"
            elif isinstance(value, list):
                logger.debug(f"Reforming list field: {key}")
                item[key] = "\n".join(value)
            elif value is None:
                item[key] = ""
        logger.debug("Data reformation completed")
        return item

    def reform_graph_domain(self, item, logger):
        logger.info("Reforming graph domain data")

        whois_entries = ParserHelper.find_element_by_key(item, "whois")
        logger.debug(f"Raw whois entries: {whois_entries}")

        if not whois_entries:
            item["whois"] = {}
            logger.debug("No whois data found")
            return item

        best_entry = None
        max_fields = 0

        for entry in whois_entries:
            parsed = entry.get("parsed", [])
            non_empty_fields = sum(1 for field in parsed if field.get("value"))
            if non_empty_fields > max_fields:
                max_fields = non_empty_fields
                best_entry = entry

        if not best_entry or "parsed" not in best_entry:
            item["whois"] = {}
            logger.debug("No valid parsed data in whois entries")
            return item

        parsed_data = best_entry["parsed"]
        simplified_whois = {}

        for field_entry in parsed_data:
            field_name = field_entry.get("field")
            values = field_entry.get("value", [])

            if not values:
                continue

            normalized_key = field_name.lower()
            normalized_key = normalized_key.replace("nameservers", "name_servers")
            normalized_key = normalized_key.replace("phonenumber", "phone")
            normalized_key = normalized_key.replace("domainname", "domain_name")
            normalized_key = normalized_key.replace("whoisserver", "whois_server")
            normalized_key = normalized_key.replace("registrar", "registrar")
            normalized_key = normalized_key.replace("status", "status")
            normalized_key = normalized_key.replace("creationdate", "creation_date")
            normalized_key = normalized_key.replace("expirationdate", "expiration_date")
            normalized_key = normalized_key.replace("updateddate", "updated_date")

            simplified_whois[normalized_key] = ", ".join(values)

        item["whois"] = simplified_whois
        logger.debug(f"Reformed whois data: {simplified_whois}")

        return item

    def reform_graph_ip(self, item, tip, logger):
        logger.info("Reforming graph IP data")
        parse_item = ""
        whois_summary = ParserHelper.find_element_by_key(item, "whois_summary")
        for key, value in whois_summary.items():
            parse_item += f"{key}: {value}\n"

        logger.debug("IP graph data reformed")
        return parse_item

    def search_data(
        self, poller: TIPoller, tip, api_update_response, graph_response, search_value, logger
    ):
        logger.info(f"Searching data for tip: {tip}, search_value: {search_value}")
        main_response = []
        comb_response = {"api": "", "graph": graph_response}
        if api_update_response:
            for response in api_update_response:
                api_path = response["apiPath"]
                label = response["label"]
                logger.debug(f"Processing API path: {api_path}, label: {label}")
                generation = poller.create_update_generator(
                    api_path, query=f"{tip}:{search_value}"
                )
                for portion in generation:
                    for item in portion.raw_dict["items"]:
                        comb_response["api"] = item
                        result = ParserHelper.find_by_template(
                            comb_response, Utils.select_mask(tip)
                        )
                        if api_path == "ioc/common" and tip == "hash":
                            result["Hashes"] = {
                                "md5": item["hash"][0],
                                "sha1": item["hash"][1],
                                "sha256": item["hash"][2],
                            }
                        result["Attribution"]["Collection name"] = label
                        main_response.append(self.reform_data(result, logger=logger))
                        logger.debug(f"Added item to main_response: {item}")
            logger.info("Data search completed with API responses")
        else:
            result = ParserHelper.find_by_template(
                comb_response, Utils.select_mask(tip)
            )
            main_response.append(self.reform_data(result, logger=logger))
            logger.info("Data search completed without API responses")
        return main_response

    def create_comb_response(self, poller: TIPoller, search_value, graph_response, tip, logger):
        logger.info(
            f"Creating combined response for search_value: {search_value}, tip: {tip}"
        )
        api_response = poller.global_search(search_value)
        logger.debug(f"API response from global search: {api_response}")
        api_update_response = [
            response
            for response in api_response
            if response["apiPath"] in AppConsts.PATH_LIST
        ]
        logger.debug(f"Filtered API update response: {api_update_response}")
        result = self.search_data(
            poller, tip, api_update_response, graph_response, search_value, logger=logger
        )
        logger.info("Combined response created")
        return result

    def generate(self):
        logger = Utils.get_logger(
            use_small_log_size=Utils.read_conf("limit_the_size_of_logs_to_100_mb"),
            use_debug_log_level=Utils.read_conf("use_debug_log_level"),
        )
        logger.info("Starting generate method")
        session_key = super().service.__dict__.get("token")
        provided_username = getattr(self, "username", None)
        if provided_username:
            USERNAME = provided_username
            logger.info(f"Using provided username: {USERNAME}")
        else:
            USERNAME = Credentials.get_username(session_key, logger)
            logger.info(f"Retrieved username from storage_passwords: {USERNAME}")
        API_KEY = Credentials.get_api_key(session_key, USERNAME, logger)
        logger.debug("API key retrieved")
        PROXY_ENABLED = Utils.read_conf("enable_proxy")
        logger.debug(f"Proxy enabled: {PROXY_ENABLED}")
        SEARCH_VALUE = self.search
        logger.info(f"Search value: {SEARCH_VALUE}")
        try:
            poller = TIPoller(
                username=USERNAME,
                api_key=API_KEY,
                api_url="https://tap.group-ib.com/api/v2/",
            )
            logger.debug("TIPoller initialized")
            poller.set_verify(True)
            poller.set_product(**AppConsts.PRODUCT_DATA_FOR_POLLER)
            if PROXY_ENABLED == "1":
                PROXY_ADDRESS = Utils.read_conf("proxy_address")
                PROXY_PORT = Utils.read_conf("proxy_port")
                PROXY_PROTOCOL = Utils.read_conf("proxy_protocol")
                poller.set_proxies(PROXY_PROTOCOL, PROXY_ADDRESS, PROXY_PORT)
                logger.debug("Proxy settings applied")
            else:
                logger.debug("Proxy not enabled")

            if validators.domain(SEARCH_VALUE):
                logger.info(f"Processing domain: {SEARCH_VALUE}")
                graph_response = self.reform_graph_domain(
                    poller.graph_domain_search(SEARCH_VALUE), logger=logger
                )
                response = self.create_comb_response(
                    poller, SEARCH_VALUE, graph_response, "domain", logger=logger
                )
                for item in response:
                    yield item
            elif validators.ipv4(SEARCH_VALUE):
                logger.info(f"Processing IP: {SEARCH_VALUE}")
                graph_response = self.reform_graph_ip(
                    poller.graph_ip_search(SEARCH_VALUE), "ip_graph", logger=logger
                )
                response = self.create_comb_response(
                    poller, SEARCH_VALUE, graph_response, "ip", logger=logger
                )
                for item in response:
                    yield item
            elif (
                validators.sha256(SEARCH_VALUE)
                or validators.sha1(SEARCH_VALUE)
                or validators.md5(SEARCH_VALUE)
            ):
                logger.info(f"Processing hash: {SEARCH_VALUE}")
                response = self.create_comb_response(poller, SEARCH_VALUE, "", "hash")
                for item in response:
                    yield item
            elif validators.url(SEARCH_VALUE):
                logger.info(f"Processing URL: {SEARCH_VALUE}")
                parsed_url = urllib.parse.urlsplit(SEARCH_VALUE)
                SEARCH_VALUE = parsed_url.netloc
                logger.debug(f"Extracted netloc: {SEARCH_VALUE}")
                if validators.domain(SEARCH_VALUE):
                    logger.info(f"Netloc is domain: {SEARCH_VALUE}")
                    graph_response = self.reform_graph_domain(
                        poller.graph_domain_search(SEARCH_VALUE), logger=logger
                    )
                    response = self.create_comb_response(
                        poller, SEARCH_VALUE, graph_response, "domain", logger=logger
                    )
                    for item in response:
                        yield item
                elif validators.ipv4(SEARCH_VALUE):
                    logger.info(f"Netloc is IP: {SEARCH_VALUE}")
                    graph_response = self.reform_graph_ip(
                        poller.graph_ip_search(SEARCH_VALUE), "ip_graph", logger=logger
                    )
                    response = self.create_comb_response(
                        poller, SEARCH_VALUE, graph_response, "ip", logger=logger
                    )
                    for item in response:
                        yield item
            else:
                logger.warning(f"Unsupported search value: {SEARCH_VALUE}")
                yield {"message": "Our team is working on adding new fields"}

        except Exception as e:
            logger.error(f"Error during generate: {str(e)}")
            yield {"error": str(e)}
        finally:
            poller.close_session()
            logger.info("Session closed")


dispatch(gibsearch, sys.argv, sys.stdin, sys.stdout, __name__)
