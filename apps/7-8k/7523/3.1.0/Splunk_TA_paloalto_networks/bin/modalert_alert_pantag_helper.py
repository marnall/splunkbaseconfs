#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

# encoding = utf-8
from typing import OrderedDict, Any, Tuple, Dict
from firewall_client import FirewallClient
from alert_pantag import AlertActionWorkeralert_pantag
from palo_utils import get_proxy_settings, get_account_credentials

IP_FIELDS = ["src_ip", "dest_ip", "ip"]
USER_FIELDS = ["src_user", "dest_user", "user"]


def preproccess_event(event: OrderedDict[str, Any], action: str) -> str:
    """
    Extracts the value from the event based on the action.

    :param event: The event to extract the value from.
    :param action: The action to perform.

    :returns: The extracted value.
    """
    if action in ("add_user", "remove_user"):
        FIELDS = USER_FIELDS
    else:
        FIELDS = IP_FIELDS
    extracted_value = None

    for field in FIELDS:
        if field in event:
            extracted_value = event[field]
            break
    return extracted_value


def process_event(
    helper: AlertActionWorkeralert_pantag, *args: Tuple[Any], **kwargs: Dict[str, Any]
) -> int:
    """
    Processes the event and performs the action.

    :param helper: The alert action helper object.
    :param args: The arguments.
    :param kwargs: The keyword arguments.

    :returns: The status code.
    """
    helper.set_log_level(helper.log_level)
    helper.log_info("Alert action alert_pantag started.")
    proxies = get_proxy_settings(helper.logger, helper.settings["session_key"])
    firewall_credentials = get_account_credentials(
        helper.settings["session_key"],
        helper.settings["configuration"]["hostname"],
        "firewall_account",
        helper.logger,
    )
    firewall = FirewallClient(
        helper.settings["configuration"]["hostname"],
        firewall_credentials.get("username"),
        firewall_credentials.get("password"),
        helper.logger,
        proxies,
    )
    events = helper.get_events()
    ip_or_users_to_tag = []
    for event in events:
        extracted_value = preproccess_event(
            event, helper.settings["configuration"]["action"]
        )
        if extracted_value not in ip_or_users_to_tag:
            ip_or_users_to_tag.append(extracted_value)
    if helper.settings["configuration"]["action"] == "add_ip":
        helper.log_info(f"Event: {event}")
        firewall.tag_ip(
            ip_or_users_to_tag,
            helper.settings["configuration"]["tags"].split(" "),
            helper.settings["configuration"].get("timeout", None),
        )
    elif helper.settings["configuration"]["action"] == "remove_ip":
        firewall.untag_ip(
            ip_or_users_to_tag,
            helper.settings["configuration"]["tags"].split(" "),
        )
    elif helper.settings["configuration"]["action"] == "add_user":
        firewall.tag_user(
            ip_or_users_to_tag,
            helper.settings["configuration"]["tags"].split(" "),
            helper.settings["configuration"].get("timeout", None),
        )
    elif helper.settings["configuration"]["action"] == "remove_user":
        firewall.untag_user(
            ip_or_users_to_tag,
            helper.settings["configuration"]["tags"].split(" "),
        )
    return 0
