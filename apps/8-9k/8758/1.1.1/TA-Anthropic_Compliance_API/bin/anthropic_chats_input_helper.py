"""Modular input helper for Anthropic Compliance API — Chats.

The Compliance API spec lists ``user_ids[]`` as optional on
``/v1/compliance/apps/chats`` but the endpoint rejects calls without
it (``400 invalid_request_error: user_ids[]: Field required``) AND
caps the array at 10 entries per call (``List should have at most 10
items after validation``). Neither limit is documented in the spec
PDF. This helper satisfies both by discovering every member of every
organization via ``/v1/compliance/organizations`` and
``/v1/compliance/organizations/{uuid}/users`` on every poll, then
fanning out across the discovered user_ids in batches of
``USER_BATCH_SIZE``.

For ad-hoc, user-scoped chat retrieval (no full-tenant fan-out) use the
``claudechats`` streaming search command instead.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import import_declare_test  # noqa: F401  UCC sys.path bootstrap
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "TA-Anthropic_Compliance_API"
SOURCETYPE_CHAT = "anthropic:compliance:apps:chat"
SOURCETYPE_CHAT_MESSAGE = "anthropic:compliance:apps:chat_message"
API_BASE_URL = "https://api.anthropic.com/v1/compliance"
API_VERSION = "2026-03-29"
# Per Compliance API spec: chats list caps at 1000; org users list caps at 1000.
CHATS_PAGE_LIMIT = 1000
ORG_USERS_PAGE_LIMIT = 1000
# Maximum user_ids per /apps/chats call. Empirically the API caps
# user_ids[] at 10 per request — HTTP 400 "user_ids[]: List should have
# at most 10 items after validation". The spec PDF (page 23-24) does
# not document this cap; do not raise this value without re-checking
# the API.
USER_BATCH_SIZE = 10
DEFAULT_LOOKBACK_HOURS = 168
# Chunk size for slicing the (chats_since -> now) lookback window into
# sequential half-open intervals. Checkpoint advances after each slice
# completes, so a mid-run failure only replays one slice. 24h is a
# sensible balance between recovery granularity and the per-slice
# overhead of N (users / batch_size) /apps/chats calls.
SLICE_HOURS = 24
MAX_RETRIES = 5
REQUEST_TIMEOUT = 30


def get_logger() -> logging.Logger:
    """Return the shared logger for the Chats input type."""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_chats")


def get_account_config(session_key: str, account_name: str) -> dict:
    """Look up the named account stanza from the UCC credential store."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta-anthropic_compliance_api_account",
    )
    account_conf_file = cfm.get_conf("ta-anthropic_compliance_api_account")
    return account_conf_file.get(account_name)


def _load_checkpoint(checkpoint_dir: str, input_name: str) -> dict:
    path = os.path.join(checkpoint_dir, f"{input_name}_chats.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_checkpoint(checkpoint_dir: str, input_name: str, data: dict) -> None:
    """Atomically persist the checkpoint via write-to-temp then rename.

    Per-slice flushing means we touch this file many times per backfill
    run; a crash mid-write would leave the JSON truncated and trip
    ``_load_checkpoint`` on next start, so the rename guards against that.
    """
    path = os.path.join(checkpoint_dir, f"{input_name}_chats.json")
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, path)


def _build_headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
    }


def _get_with_retry(
    logger: logging.Logger,
    url: str,
    headers: dict,
    params: list[tuple[str, str]] | dict,
    label: str,
) -> dict:
    """GET with retry on transient failures.

    Retries with backoff on:
    - HTTP 429: honors ``Retry-After``, falls back to ``2 ** (attempt + 1)``.
    - HTTP 5xx: exponential backoff.
    - ``requests.RequestException`` (connection reset, DNS, timeout, etc.):
      exponential backoff.

    Hard-fails (no retry) on:
    - HTTP 401: surfaces a scopes-aware error message.
    - Other 4xx: logs the response body and raises.

    Params may be a list of ``(name, value)`` tuples so repeatable
    parameters like ``user_ids[]`` can be encoded correctly.
    """
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                url, headers=headers, params=params, timeout=REQUEST_TIMEOUT
            )
        except requests.exceptions.RequestException as exc:
            backoff = 2 ** (attempt + 1)
            logger.warning(
                "Network error on %s: %s; sleeping %ds (attempt %d)",
                label,
                exc,
                backoff,
                attempt + 1,
            )
            time.sleep(backoff)
            continue
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
        if resp.status_code >= 500:
            backoff = 2 ** (attempt + 1)
            logger.warning(
                "HTTP %d on %s: %s; sleeping %ds (attempt %d)",
                resp.status_code,
                label,
                resp.text[:500],
                backoff,
                attempt + 1,
            )
            time.sleep(backoff)
            continue
        if resp.status_code == 401:
            logger.error(
                "HTTP 401 fetching %s — Admin Keys are not supported for the "
                "Chats input. Use a Compliance Access Key (sk-ant-api01-...) "
                "with scopes: read:compliance_org_data, read:compliance_user_data.",
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
    """Paginate using ``next_page`` token (used by /organizations/{uuid}/users)."""
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

    The Compliance API spec states ``/organizations`` does not support
    pagination and errors above 1,000 organizations, so this helper sends
    no limit or page parameter.
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
        logger,
        url,
        headers,
        {"limit": ORG_USERS_PAGE_LIMIT},
        f"org_users[{org_uuid}]",
    )


def _build_chats_params(
    user_ids: list[str],
    updated_at_gt: str | None,
    updated_at_lte: str | None,
    after_id: str | None,
) -> list[tuple[str, str]]:
    """Build the query string for a /apps/chats call.

    Returns a list of tuples so the repeatable ``user_ids[]`` parameter
    is encoded with one entry per user. ``updated_at.gt`` /
    ``updated_at.lte`` together form a half-open ``(gt, lte]`` slice.
    """
    params: list[tuple[str, str]] = [("user_ids[]", uid) for uid in user_ids]
    params.append(("limit", str(CHATS_PAGE_LIMIT)))
    if updated_at_gt:
        params.append(("updated_at.gt", updated_at_gt))
    if updated_at_lte:
        params.append(("updated_at.lte", updated_at_lte))
    if after_id:
        params.append(("after_id", after_id))
    return params


def iter_chats(
    logger: logging.Logger,
    api_key: str,
    user_ids: list[str],
    updated_at_gt: str | None,
    updated_at_lte: str | None = None,
) -> Generator[dict, None, None]:
    """Yield chats across batched, paginated ``/apps/chats`` calls.

    The /apps/chats endpoint sorts results time-ascending by created_at;
    ``after_id=last_id`` advances the cursor forward toward newer entries.
    Batch size is the module-level ``USER_BATCH_SIZE`` constant — the
    API enforces a hard ceiling of 10, so it is not operator-tunable.
    """
    url = f"{API_BASE_URL}/apps/chats"
    headers = _build_headers(api_key)
    for start in range(0, len(user_ids), USER_BATCH_SIZE):
        batch = user_ids[start : start + USER_BATCH_SIZE]
        batch_label = (
            f"chats[batch {start // USER_BATCH_SIZE + 1}, {len(batch)} user(s)]"
        )
        after_id: str | None = None
        while True:
            params = _build_chats_params(batch, updated_at_gt, updated_at_lte, after_id)
            data = _get_with_retry(logger, url, headers, params, batch_label)
            items: list[dict] = data.get("data", [])
            for chat in items:
                yield chat
            if not data.get("has_more") or not items:
                break
            after_id = items[-1].get("id")
            if not after_id:
                logger.warning(
                    "%s: has_more=true but last item missing id; stopping pagination.",
                    batch_label,
                )
                break


def fetch_chat_messages(
    logger: logging.Logger, api_key: str, chat_id: str
) -> dict | None:
    """Fetch the full message thread for a single chat. Returns None on failure."""
    url = f"{API_BASE_URL}/apps/chats/{chat_id}/messages"
    headers = _build_headers(api_key)
    try:
        return _get_with_retry(logger, url, headers, {}, f"chat_messages[{chat_id}]")
    except Exception as exc:
        logger.error("Failed to fetch messages for chat %s: %s", chat_id, exc)
        return None


def _discover_user_ids(logger: logging.Logger, api_key: str) -> list[str]:
    """Discover the distinct ``user_id`` set across every organization.

    A user can hold membership in more than one organization under a
    parent; deduplicate so the chats fan-out doesn't issue overlapping
    calls.
    """
    orgs = fetch_organizations(logger, api_key)
    logger.info("Discovered %d organizations", len(orgs))
    seen: set[str] = set()
    user_ids: list[str] = []
    for org in orgs:
        org_uuid = org.get("uuid") or org.get("id")
        if not org_uuid:
            logger.warning("Skipping org with no uuid: %s", org)
            continue
        users = fetch_org_users(logger, api_key, org_uuid)
        logger.info("Discovered %d users in org %s", len(users), org_uuid)
        for user in users:
            uid = user.get("id")
            if uid and uid not in seen:
                seen.add(uid)
                user_ids.append(uid)
    return user_ids


def _format_lookback(lookback_hours: int) -> str:
    """Return an RFC 3339 ``YYYY-MM-DDTHH:MM:SSZ`` string ``lookback_hours`` ago."""
    lookback_ts = datetime.now(timezone.utc).timestamp() - (lookback_hours * 3600)
    return datetime.fromtimestamp(lookback_ts, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _parse_rfc3339(value: str) -> datetime:
    """Parse an RFC 3339 ``YYYY-MM-DDTHH:MM:SSZ`` string into a tz-aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iter_slices(
    start: datetime, end: datetime, slice_hours: int
) -> Generator[tuple[datetime, datetime], None, None]:
    """Yield consecutive half-open ``(slice_start, slice_end]`` windows.

    Each yielded pair satisfies ``slice_start < slice_end <= end``. The
    final slice's ``slice_end`` is exactly ``end``. Empty range (start
    >= end) yields nothing.
    """
    if start >= end:
        return
    cur = start
    delta = timedelta(hours=slice_hours)
    while cur < end:
        nxt = min(cur + delta, end)
        yield cur, nxt
        cur = nxt


def _emit_chat(event_writer: smi.EventWriter, chat: dict, index: str | None) -> None:
    event_writer.write_event(
        smi.Event(
            data=json.dumps(chat, ensure_ascii=False, default=str),
            index=index,
            sourcetype=SOURCETYPE_CHAT,
        )
    )


def _emit_messages(
    event_writer: smi.EventWriter,
    chat_detail: dict,
    chat_id: str,
    index: str | None,
    min_created_at: datetime | None = None,
) -> int:
    """Emit one event per message; return the count emitted.

    Each message event is enriched with ``chat_id``,
    ``chat_organization_uuid``, ``chat_user_id``, and
    ``chat_user_email_address`` so events can be correlated with their
    parent chat without a join.

    When ``min_created_at`` is supplied, messages whose ``created_at``
    is at or before that timestamp are skipped. Used in incremental
    polling so that a chat whose ``updated_at`` advances does not cause
    its entire historical thread to be re-emitted on every run; only
    genuinely new messages are emitted. ``None`` disables the filter
    (initial-lookback mode — capture the full thread once).
    """
    user = chat_detail.get("user") or {}
    correlation = {
        "chat_id": chat_id,
        "chat_organization_uuid": chat_detail.get("organization_uuid"),
        "chat_organization_id": chat_detail.get("organization_id"),
        "chat_project_id": chat_detail.get("project_id"),
        "chat_user_id": user.get("id"),
        "chat_user_email_address": user.get("email_address"),
    }
    emitted = 0
    for message in chat_detail.get("chat_messages") or []:
        if min_created_at is not None:
            msg_created_at = message.get("created_at")
            if msg_created_at:
                try:
                    if _parse_rfc3339(msg_created_at) <= min_created_at:
                        continue
                except ValueError:
                    # Unparseable timestamp — emit rather than silently drop.
                    pass
        enriched = {**correlation, **message}
        event_writer.write_event(
            smi.Event(
                data=json.dumps(enriched, ensure_ascii=False, default=str),
                index=index,
                sourcetype=SOURCETYPE_CHAT_MESSAGE,
            )
        )
        emitted += 1
    return emitted


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

            do_messages = input_item.get("fetch_chat_messages") == "1"
            lookback_hours = int(
                input_item.get("lookback_hours") or DEFAULT_LOOKBACK_HOURS
            )
            default_since = _format_lookback(lookback_hours)

            # Initial-lookback semantics: on the very first run for this
            # input (no checkpoint), capture the full message thread for
            # every chat whose updated_at falls in the lookback window so
            # historical context for long-running conversations is
            # preserved. Once the final slice of that run completes, the
            # flag flips to True and subsequent runs emit only messages
            # created after the previous slice boundary.
            #
            # Legacy migration: an existing checkpoint that predates this
            # flag (chats_max_updated_at present, flag absent) was written
            # by the prior all-messages-every-run code. Treat it as
            # already past the initial lookback so an upgrade does not
            # trigger a surprise full re-ingest of every active chat's
            # history.
            chats_max_updated_at = checkpoint.get("chats_max_updated_at")
            if chats_max_updated_at:
                first_lookback_complete = checkpoint.get(
                    "first_lookback_complete", True
                )
                chats_since = chats_max_updated_at
            else:
                first_lookback_complete = False
                chats_since = default_since

            user_ids = _discover_user_ids(logger, api_key)
            if not user_ids:
                logger.info("No org users discovered; skipping /apps/chats fan-out.")
                log.modular_input_end(logger, normalized_input_name)
                continue

            window_start = _parse_rfc3339(chats_since)
            window_end = datetime.now(timezone.utc)
            slices = list(_iter_slices(window_start, window_end, SLICE_HOURS))

            logger.info(
                "Backfill plan: %d slice(s) of <=%dh between %s and %s "
                "for %d user(s) (messages=%s, mode=%s).",
                len(slices),
                SLICE_HOURS,
                chats_since,
                _format_rfc3339(window_end),
                len(user_ids),
                do_messages,
                "incremental" if first_lookback_complete else "initial-lookback",
            )

            chat_events = 0
            message_events = 0

            # In incremental mode, only emit messages created after the
            # previous run's boundary (== window_start, == chats_since).
            # This is invariant across slices in the same run: slicing
            # exists for API-call resilience, not to narrow the
            # emit-eligibility boundary. Using slice_start here would
            # silently drop a message created during slice N-1's window
            # on a chat whose updated_at landed in slice N (the trigger
            # case is a >24h gap between runs with a chat that gets a
            # new message early in the gap and another update late in
            # it). During the initial lookback, pass None so the full
            # thread is captured once.
            message_min = window_start if first_lookback_complete else None

            for idx, (slice_start, slice_end) in enumerate(slices, start=1):
                slice_gt = _format_rfc3339(slice_start)
                slice_lte = _format_rfc3339(slice_end)
                logger.info(
                    "Slice %d/%d: updated_at gt=%s lte=%s",
                    idx,
                    len(slices),
                    slice_gt,
                    slice_lte,
                )

                for chat in iter_chats(
                    logger,
                    api_key,
                    user_ids,
                    slice_gt,
                    slice_lte,
                ):
                    _emit_chat(event_writer, chat, index)
                    chat_events += 1

                    if do_messages:
                        chat_id = chat.get("id")
                        if not chat_id:
                            continue
                        chat_detail = fetch_chat_messages(logger, api_key, chat_id)
                        if chat_detail is None:
                            continue
                        message_events += _emit_messages(
                            event_writer,
                            chat_detail,
                            chat_id,
                            index,
                            message_min,
                        )

                # Slice completed successfully — advance the checkpoint to
                # its upper bound so a failure in a later slice replays at
                # most this slice's window on next run. Flush the event
                # writer first so any events still in stdout's block buffer
                # reach splunkd before the checkpoint is durable; otherwise
                # a hard crash (SIGKILL, host loss) between checkpoint
                # write and buffer flush would silently drop them on the
                # next run.
                #
                # The flag flips to True only when the LAST slice of an
                # initial-lookback run completes. Earlier slices keep it
                # False so a mid-run failure resumes in initial-lookback
                # mode and continues capturing full threads through the
                # remaining gap.
                event_writer._out.flush()
                slice_flag = first_lookback_complete or idx == len(slices)
                _save_checkpoint(
                    checkpoint_dir,
                    normalized_input_name,
                    {
                        "chats_max_updated_at": slice_lte,
                        "first_lookback_complete": slice_flag,
                    },
                )

            logger.info(
                "Run complete: %d chat events, %d chat_message events across "
                "%d slice(s).",
                chat_events,
                message_events,
                len(slices),
            )
            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_CHAT,
                chat_events,
                index,
                account=input_item.get("account"),
            )
            if do_messages:
                log.events_ingested(
                    logger,
                    input_name,
                    SOURCETYPE_CHAT_MESSAGE,
                    message_events,
                    index,
                    account=input_item.get("account"),
                )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            logger.error(
                "Exception raised while ingesting Chats data: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,
            )
