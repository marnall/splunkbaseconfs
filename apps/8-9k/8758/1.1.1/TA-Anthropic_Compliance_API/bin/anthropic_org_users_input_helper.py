"""Modular input helper for Anthropic Compliance API - Organizations, Users, Groups, and Roles."""

from __future__ import annotations

import json
import logging
import time

import import_declare_test  # noqa: F401  UCC sys.path bootstrap
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "TA-Anthropic_Compliance_API"
SOURCETYPE_ORG = "anthropic:compliance:organization"
SOURCETYPE_USER = "anthropic:compliance:org_user"
SOURCETYPE_GROUP = "anthropic:compliance:group"
SOURCETYPE_GROUP_MEMBER = "anthropic:compliance:group_member"
SOURCETYPE_ORG_ROLE = "anthropic:compliance:org_role"
API_BASE_URL = "https://api.anthropic.com/v1/compliance"
API_VERSION = "2026-03-29"
PAGE_LIMIT = 1000


def get_logger() -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_org_users")


def get_account_config(session_key: str, account_name: str) -> dict:
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta-anthropic_compliance_api_account",
    )
    account_conf_file = cfm.get_conf("ta-anthropic_compliance_api_account")
    return account_conf_file.get(account_name)


def _build_headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
    }


def _get_with_retry(
    logger: logging.Logger,
    url: str,
    headers: dict,
    params: dict,
    label: str,
) -> dict:
    """GET with exponential backoff on 429 and explicit 401 error message."""
    for attempt in range(5):
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("retry-after", 2 ** (attempt + 1)))
            logger.warning(
                "Rate limited on %s; sleeping %ds (attempt %d)",
                label,
                retry_after,
                attempt + 1,
            )
            time.sleep(retry_after)
            continue
        if resp.status_code == 401:
            logger.error(
                "HTTP 401 from %s — Use a Compliance Access Key (sk-ant-api01-...) with scopes: "
                "read:compliance_org_data, read:compliance_user_data.",
                label,
            )
            resp.raise_for_status()
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Exceeded retry limit fetching {label}")


def _paginate_page_token(
    logger: logging.Logger,
    url: str,
    headers: dict,
    initial_params: dict,
    label: str,
) -> list[dict]:
    """Paginate using page token (next_page field)."""
    all_items: list[dict] = []
    params = dict(initial_params)

    while True:
        data = _get_with_retry(logger, url, headers, params, label)
        items: list[dict] = data.get("data", [])
        all_items.extend(items)
        logger.debug(
            "Fetched %d %s items (total: %d)", len(items), label, len(all_items)
        )

        next_page = data.get("next_page")
        if not next_page:
            break
        params["page"] = next_page

    return all_items


def fetch_organizations(logger: logging.Logger, api_key: str) -> list[dict]:
    """Fetch all organizations.

    Per the Compliance API spec, /organizations does not support pagination
    and errors out when the response would exceed 1,000 organizations —
    so no limit/page parameters are sent.
    """
    url = f"{API_BASE_URL}/organizations"
    headers = _build_headers(api_key)
    data = _get_with_retry(logger, url, headers, {}, "organizations")
    orgs: list[dict] = data.get("data", [])
    if data.get("has_more") or data.get("next_page"):
        logger.warning(
            "Organizations response indicated more pages exist; only first %d orgs fetched.",
            len(orgs),
        )
    return orgs


def fetch_org_users(logger: logging.Logger, api_key: str, org_uuid: str) -> list[dict]:
    """Fetch all users for a given organization UUID."""
    url = f"{API_BASE_URL}/organizations/{org_uuid}/users"
    headers = _build_headers(api_key)
    return _paginate_page_token(
        logger, url, headers, {"limit": PAGE_LIMIT}, f"org_users[{org_uuid}]"
    )


def fetch_org_roles(logger: logging.Logger, api_key: str, org_uuid: str) -> list[dict]:
    """Fetch all roles for a given organization UUID."""
    url = f"{API_BASE_URL}/organizations/{org_uuid}/roles"
    headers = _build_headers(api_key)
    return _paginate_page_token(
        logger, url, headers, {"limit": PAGE_LIMIT}, f"org_roles[{org_uuid}]"
    )


def fetch_groups(logger: logging.Logger, api_key: str) -> list[dict]:
    """Fetch all groups."""
    url = f"{API_BASE_URL}/groups"
    headers = _build_headers(api_key)
    return _paginate_page_token(logger, url, headers, {"limit": PAGE_LIMIT}, "groups")


def fetch_group_members(
    logger: logging.Logger, api_key: str, group_id: str
) -> list[dict]:
    """Fetch all members for a given group."""
    url = f"{API_BASE_URL}/groups/{group_id}/members"
    headers = _build_headers(api_key)
    return _paginate_page_token(
        logger, url, headers, {"limit": PAGE_LIMIT}, f"group_members[{group_id}]"
    )


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    logger = get_logger()
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="ta-anthropic_compliance_api_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            account_config = get_account_config(session_key, input_item.get("account"))
            api_key = account_config.get("api_key")
            index = input_item.get("index")
            total_events = 0

            do_groups = input_item.get("fetch_groups") == "1"
            do_org_roles = input_item.get("fetch_org_roles") == "1"

            # --- Organizations + Users ---
            orgs = fetch_organizations(logger, api_key)
            logger.info("Fetched %d organizations", len(orgs))

            for org in orgs:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(org, ensure_ascii=False, default=str),
                        index=index,
                        sourcetype=SOURCETYPE_ORG,
                    )
                )
                total_events += 1

                # uuid is the primary identifier per ComplianceOrganizationInfo schema
                org_uuid = org.get("uuid") or org.get("id")
                if not org_uuid:
                    logger.warning("Could not determine UUID for org: %s", org)
                    continue

                org_name = org.get("name", org_uuid)

                users = fetch_org_users(logger, api_key, org_uuid)
                logger.info("Fetched %d users for org %s", len(users), org_name)

                for user in users:
                    enriched = dict(user)
                    enriched["_org_id"] = org_uuid
                    enriched["_org_name"] = org_name
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(enriched, ensure_ascii=False, default=str),
                            index=index,
                            sourcetype=SOURCETYPE_USER,
                        )
                    )
                    total_events += 1

                # --- Org Roles ---
                if do_org_roles:
                    roles = fetch_org_roles(logger, api_key, org_uuid)
                    logger.info("Fetched %d roles for org %s", len(roles), org_name)
                    for role in roles:
                        enriched = dict(role)
                        enriched["_org_id"] = org_uuid
                        enriched["_org_name"] = org_name
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(
                                    enriched, ensure_ascii=False, default=str
                                ),
                                index=index,
                                sourcetype=SOURCETYPE_ORG_ROLE,
                            )
                        )
                        total_events += 1

            # --- Groups + Members ---
            if do_groups:
                groups = fetch_groups(logger, api_key)
                logger.info("Fetched %d groups", len(groups))

                for group in groups:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(group, ensure_ascii=False, default=str),
                            index=index,
                            sourcetype=SOURCETYPE_GROUP,
                        )
                    )
                    total_events += 1

                    group_id = group.get("id")
                    if group_id:
                        members = fetch_group_members(logger, api_key, group_id)
                        for member in members:
                            enriched = dict(member)
                            enriched["_group_id"] = group_id
                            enriched["_group_name"] = group.get("name", group_id)
                            event_writer.write_event(
                                smi.Event(
                                    data=json.dumps(
                                        enriched, ensure_ascii=False, default=str
                                    ),
                                    index=index,
                                    sourcetype=SOURCETYPE_GROUP_MEMBER,
                                )
                            )
                            total_events += 1

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_USER,
                total_events,
                index,
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            logger.error(
                "Exception raised while ingesting Org Users data: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,
            )
