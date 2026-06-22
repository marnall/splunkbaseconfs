"""Modular input helper for Anthropic Compliance API — Projects.

Chat retrieval lives in the ``claudechats`` custom search command, not in
this modular input: ``/v1/compliance/apps/chats`` requires ``user_ids[]`` as
a filter, which is a poor fit for scheduled polling but fine for targeted
investigative searches.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone

import import_declare_test  # noqa: F401  UCC sys.path bootstrap
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "TA-Anthropic_Compliance_API"
SOURCETYPE_PROJECT = "anthropic:compliance:apps:project"
SOURCETYPE_PROJECT_ATTACHMENTS = "anthropic:compliance:apps:project_attachments"
API_BASE_URL = "https://api.anthropic.com/v1/compliance"
API_VERSION = "2026-03-29"
# Per Compliance API spec: projects list and project attachments cap at 100.
PROJECTS_PAGE_LIMIT = 100
DEFAULT_LOOKBACK_HOURS = 168


def get_logger() -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_apps")


def get_account_config(session_key: str, account_name: str) -> dict:
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta-anthropic_compliance_api_account",
    )
    account_conf_file = cfm.get_conf("ta-anthropic_compliance_api_account")
    return account_conf_file.get(account_name)


def _load_checkpoint(checkpoint_dir: str, input_name: str) -> dict:
    path = os.path.join(checkpoint_dir, f"{input_name}_apps.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_checkpoint(checkpoint_dir: str, input_name: str, data: dict) -> None:
    path = os.path.join(checkpoint_dir, f"{input_name}_apps.json")
    with open(path, "w") as f:
        json.dump(data, f)


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
                "HTTP 401 fetching %s — Admin Keys are not supported for Apps inputs. "
                "Use a Compliance Access Key (sk-ant-api01-...) with scope: "
                "read:compliance_user_data.",
                label,
            )
            resp.raise_for_status()
        if 400 <= resp.status_code < 500:
            logger.error(
                "HTTP %d fetching %s — response: %s",
                resp.status_code,
                label,
                resp.text[:500],
            )
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
    """Paginate using page token (next_page field) for projects and attachments."""
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


def fetch_projects(
    logger: logging.Logger,
    api_key: str,
    params: dict,
) -> list[dict]:
    """Fetch projects with the given filter params."""
    url = f"{API_BASE_URL}/apps/projects"
    headers = _build_headers(api_key)
    return _paginate_page_token(
        logger, url, headers, {**params, "limit": PROJECTS_PAGE_LIMIT}, "projects"
    )


def fetch_project_attachments(
    logger: logging.Logger,
    api_key: str,
    project_id: str,
) -> list[dict]:
    """Fetch all attachments for a single project."""
    url = f"{API_BASE_URL}/apps/projects/{project_id}/attachments"
    headers = _build_headers(api_key)
    return _paginate_page_token(
        logger,
        url,
        headers,
        {"limit": PROJECTS_PAGE_LIMIT},
        f"project_attachments[{project_id}]",
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
            checkpoint_dir = inputs.metadata.get("checkpoint_dir", "/tmp")
            checkpoint = _load_checkpoint(checkpoint_dir, normalized_input_name)
            index = input_item.get("index")

            do_project_attachments = input_item.get("fetch_project_attachments") == "1"

            lookback_hours = int(
                input_item.get("lookback_hours") or DEFAULT_LOOKBACK_HOURS
            )
            lookback_ts = datetime.now(timezone.utc).timestamp() - (
                lookback_hours * 3600
            )
            default_since = datetime.fromtimestamp(
                lookback_ts, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

            projects_since = checkpoint.get("projects_max_created_at") or default_since

            total_events = 0
            new_projects_max_created_at: str | None = checkpoint.get(
                "projects_max_created_at"
            )

            logger.info("Fetching projects created after %s", projects_since)
            projects = fetch_projects(
                logger, api_key, {"created_at.gt": projects_since}
            )
            logger.info("Fetched %d projects", len(projects))

            for project in projects:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(project, ensure_ascii=False, default=str),
                        index=index,
                        sourcetype=SOURCETYPE_PROJECT,
                    )
                )
                total_events += 1

                created_at = project.get("created_at")
                if created_at and (
                    new_projects_max_created_at is None
                    or created_at > new_projects_max_created_at
                ):
                    new_projects_max_created_at = created_at

                if do_project_attachments:
                    project_id = project.get("id")
                    if project_id:
                        attachments = fetch_project_attachments(
                            logger, api_key, project_id
                        )
                        for attachment in attachments:
                            enriched = dict(attachment)
                            enriched["_project_id"] = project_id
                            event_writer.write_event(
                                smi.Event(
                                    data=json.dumps(
                                        enriched, ensure_ascii=False, default=str
                                    ),
                                    index=index,
                                    sourcetype=SOURCETYPE_PROJECT_ATTACHMENTS,
                                )
                            )
                            total_events += 1

            _save_checkpoint(
                checkpoint_dir,
                normalized_input_name,
                {"projects_max_created_at": new_projects_max_created_at},
            )

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_PROJECT,
                total_events,
                index,
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            logger.error(
                "Exception raised while ingesting Apps data: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,
            )
