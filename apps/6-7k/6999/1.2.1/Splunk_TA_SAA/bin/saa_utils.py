"""This module contains utilities supporting the SAA input and alert action"""

import sys
import traceback
from typing import Optional
from urllib import parse
from dataclasses import dataclass
from collections import defaultdict

import import_declare_test  # noqa: F401
from solnlib import conf_manager
from saa_consts import ADDON_NAME
import structlog


def get_account_from_conf_file(session_key: str, account_name: str):
    """Returns a"""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-splunk_ta_saa_account",
    )
    account_conf_file = cfm.get_conf("splunk_ta_saa_account")
    return account_conf_file.get(account_name)


def get_proxy_settings(logger: structlog.stdlib.BoundLogger, session_key: str) -> Optional[dict]:
    """
    This function reads proxy settings if any, otherwise returns None.
    Only HTTPS proxies are supported.
    """
    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            ADDON_NAME,
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-splunk_ta_saa_settings",
        )
        proxy_conf = settings_cfm.get_conf("splunk_ta_saa_settings").get_all()

        logger.info("retrieved proxy settings")

        proxy_stanza = {}
        for key, value in proxy_conf["proxy"].items():
            proxy_stanza[key] = value

        if proxy_stanza.get("proxy_enabled") is None or int(proxy_stanza.get("proxy_enabled", 0)) == 0:
            logger.info("Proxy is disabled")
            return None
        proxy_type = "http"
        proxy_url = proxy_stanza.get("host")
        proxy_port = proxy_stanza.get("port")
        proxy_username = proxy_stanza.get("username", "")
        proxy_password = proxy_stanza.get("password", "")

        if proxy_username and proxy_password:
            proxy_username = parse.quote_plus(proxy_username)
            proxy_password = parse.quote_plus(proxy_password)
            proxy_uri = f"{proxy_type}://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}"
        else:
            proxy_uri = f"{proxy_type}://{proxy_url}:{proxy_port}"
        logger.info(f"Successfully fetched configured proxy details. {proxy_uri}")
        return {
            "http://": proxy_uri,
            "https://": proxy_uri,
        }
    except Exception:  # pylint: disable=broad-exception-caught
        logger.critical(f"Failed to fetch proxy details from configuration. {traceback.format_exc()}")
        sys.exit(1)


def redact_token_for_logging(token):
    return token[-4:].rjust(len(token), "*")


def dict_to_markdown_table(d):
    max_key_length = max(len(str(key)) for key in d.keys())
    max_value_length = max(len(str(value)) for value in d.values())

    table_str = f"| {'Field'.ljust(max_key_length)} | {'Value'.ljust(max_value_length)} |\n"

    table_str += f"| {'-' * max_key_length} | {'-' * max_value_length} |\n"

    for key, value in d.items():
        key_str = str(key)
        value_str = str(value)
        table_str += f"| {key_str.ljust(max_key_length)} | {value_str.ljust(max_value_length)} |\n"

    return table_str + "\n"


@dataclass
class Resource:
    id: str
    name: str
    injection_metadata: str
    parent_id: str
    score: int

    def __str__(self):
        return (
            f"{self.injection_metadata['AddedBecause']} -> {self.name}"
            if self.injection_metadata.get("AddedBecause")
            else f"{self.name}"
        )


class ResourceTree:
    SPACE = "    "
    BRANCH = "│   "
    # pointers:
    TEE = "├── "
    LAST = "└── "

    def __init__(self, resources):
        self.tree = defaultdict(list)
        self.resources = {res.id: res for res in resources}
        for res in resources:
            self.tree[res.parent_id].append(res)

    def get_children(self, parent_id):
        return self.tree[parent_id]

    def __str__(self):
        return self._build_tree_str()

    def _build_tree_str(self, parent_id="", prefix=""):
        children = self.get_children(parent_id)
        output = ""
        count = len(children)
        for i, child in enumerate(children):
            if parent_id == "":
                connector = ""
            else:
                connector = self.TEE if i < count - 1 else self.LAST

            resource_content = str(child)
            line_content = prefix + connector + resource_content
            if len(line_content) > 150:
                line_content = line_content[:150] + "..."

            output += f"{line_content} [{child.score}]\n"

            if i < count - 1:
                ext_prefix = prefix + self.BRANCH
            else:
                ext_prefix = prefix + self.SPACE
            output += self._build_tree_str(child.id, ext_prefix)
        return output
