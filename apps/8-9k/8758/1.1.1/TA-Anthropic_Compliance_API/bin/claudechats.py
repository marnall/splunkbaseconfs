"""Streaming command to retrieve Claude.ai chat history for a set of user_ids.

Usage::

    <search producing events with an Anthropic user_id field>
    | claudechats userid_field=<field>
                  [account=<account>] [messages=true|false]

``account`` is optional: when only one add-on account is configured
it is auto-discovered. Specify it explicitly when more than one
account exists.

Examples::

    index=anthropic_compliance sourcetype="anthropic:compliance:apps:project"
    | stats count by user.id
    | claudechats userid_field=user.id

    index=anthropic_compliance sourcetype="anthropic:compliance:activity"
        "actor.user_id"=user_01ATBWH52UNYC2pzqaFvomA1
    | claudechats userid_field="actor.user_id" messages=false

Emits flat pipeline rows (no synthetic ``_raw``/``sourcetype``):

* ``messages=false`` — one row per chat. Chat columns are prefixed
  ``chat.``: ``chat.id``, ``chat.user.id``, ``chat.user.email_address``,
  ``chat.created_at``, ``chat.updated_at``, ``chat.name``.
* ``messages=true`` (default) — one row per message. Each row carries
  the ``chat.``-prefixed columns above plus message columns:
  ``message_id``, ``message_created_at``, ``role``, ``text``,
  ``content_types``. The two underscore-prefixed names disambiguate
  from ``chat.id``/``chat.created_at``; the rest stay terse since they
  can't collide with chat fields. Chats with zero messages or a failed
  message fetch yield no rows in this mode (logged).

The Compliance API ``content`` field is normalized into two columns:

* ``text`` — message text as a single string. Legacy string content
  passes through. Modern block-list content concatenates all
  ``type=text`` blocks with a blank line between them.
* ``content_types`` — multi-value list of all block types in the
  original message (``["text"]``, ``["text","image"]``, etc.). Use it
  to filter multimodal messages, e.g.
  ``| where mvfind(content_types, "image") >= 0``.

The ``/v1/compliance/apps/chats`` endpoint requires ``user_ids[]`` as a
mandatory filter even though the published spec lists it as optional. This
command enforces that by collecting distinct user_ids from upstream events
before issuing API calls.

Requirements:

* The running user must hold the ``list_storage_passwords`` capability to
  read the stored API key. This is granted to the ``admin`` role by default.
* The configured account's API key must be a Compliance Access Key
  (``sk-ant-api01-...``) with ``read:compliance_user_data`` scope.

Limits:

* ``MAX_USERS`` (500) distinct user_ids per invocation. Split larger lists
  across multiple searches.
* ``USER_BATCH_SIZE`` (10) user_ids per ``/apps/chats`` call — the API
  caps user_ids[] at 10 per request (HTTP 400 "List should have at most
  10 items after validation"). The spec PDF does not document this.
* API 429 responses honor ``retry-after``; 5xx responses and transient
  network errors (``requests.RequestException``) are retried with
  exponential backoff. Other 4xx errors hard-fail with the response body
  logged.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from typing import Any, Generator

import import_declare_test  # noqa: F401  UCC sys.path bootstrap
import requests
from solnlib import conf_manager
from solnlib.conf_manager import ConfStanzaNotExistException
from splunklib.searchcommands import (
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
    validators,
)

ADDON_NAME = "TA-Anthropic_Compliance_API"
API_BASE_URL = "https://api.anthropic.com/v1/compliance"
API_VERSION = "2026-03-29"

CHATS_PAGE_LIMIT = 1000
# The API caps user_ids[] at 10 per /apps/chats call — see module
# docstring. Do not raise without re-validating against the API.
USER_BATCH_SIZE = 10
MAX_USERS = 500
MAX_RETRIES = 5
REQUEST_TIMEOUT = 30


def _iso_to_epoch(iso: str | None) -> float | None:
    """Return ``iso`` as POSIX epoch seconds, or ``None`` if unparseable."""
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _extract_content(content: Any) -> tuple[str | None, list[str] | None]:
    """Normalize a Compliance API message ``content`` field.

    Returns ``(text, content_types)``:

    * Legacy string content → ``(content, ["text"])``.
    * Modern list-of-blocks content → text from all ``type=text`` blocks
      joined with a blank line, plus an MV of every block's ``type``.
    * Anything else → ``(None, None)``.
    """
    if content is None:
        return None, None
    if isinstance(content, str):
        return content, ["text"]
    if not isinstance(content, list):
        return None, None
    types: list[str] = []
    text_parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype:
            types.append(str(btype))
        if btype == "text":
            btext = block.get("text")
            if btext:
                text_parts.append(str(btext))
    text = "\n\n".join(text_parts) if text_parts else None
    return text, (types or None)


_MESSAGE_FIELD_RENAMES = {
    "id": "message_id",
    "created_at": "message_created_at",
}


def _normalize_message(message: dict) -> dict:
    """Prepare a message dict for flattening into a pipeline row.

    Renames ``id``/``created_at`` to ``message_id``/``message_created_at``
    so they don't visually collide with the row's ``chat.id``/
    ``chat.created_at`` columns, and replaces ``content`` with
    ``text``/``content_types`` via :func:`_extract_content`.
    """
    out: dict[str, Any] = {}
    for key, value in message.items():
        if key == "content":
            continue
        out[_MESSAGE_FIELD_RENAMES.get(key, key)] = value
    text, types = _extract_content(message.get("content"))
    if text is not None:
        out["text"] = text
    if types:
        out["content_types"] = types
    return out


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested dict into dot-notated keys for a Splunk pipeline row.

    Scalars pass through. Nested dicts recurse under ``prefix.key``. Lists
    of scalars become multi-value fields. Lists containing dicts/lists are
    JSON-stringified per element (Splunk would otherwise render them as
    ``[object Object]``). ``None`` values are dropped.
    """
    if not isinstance(obj, dict):
        return {prefix: obj} if prefix else {}
    out: dict[str, Any] = {}
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if value is None:
            continue
        if isinstance(value, dict):
            out.update(_flatten(value, full_key))
        elif isinstance(value, list):
            if any(isinstance(v, (dict, list)) for v in value):
                out[full_key] = [
                    json.dumps(v, ensure_ascii=False, default=str)
                    if isinstance(v, (dict, list))
                    else v
                    for v in value
                ]
            else:
                out[full_key] = value
        else:
            out[full_key] = value
    return out


@Configuration()
class ClaudeChatsCommand(StreamingCommand):
    """Retrieve Claude.ai chats for the distinct user_ids in upstream events."""

    userid_field = Option(
        doc="Name of the upstream field containing Anthropic user_ids "
        "(values beginning with ``user_...``).",
        require=True,
        validate=validators.Fieldname(),
    )

    account = Option(
        doc="Name of the add-on account that supplies the API key. "
        "Optional when exactly one account is configured (auto-discovered); "
        "required when multiple accounts exist so the command can pick "
        "between them.",
        require=False,
    )

    messages = Option(
        doc="Fetch message bodies for each chat via "
        "/v1/compliance/apps/chats/{id}/messages (default: true). "
        "Disable to return chat metadata only.",
        require=False,
        default=True,
        validate=validators.Boolean(),
    )

    def stream(self, records):
        user_ids: list[str] = []
        seen: set[str] = set()

        for record in records:
            raw = record.get(self.userid_field)
            if raw is None:
                continue
            for uid in self._split_multivalue(raw):
                if not uid or uid in seen:
                    continue
                if len(user_ids) >= MAX_USERS:
                    raise RuntimeError(
                        f"claudechats: upstream events contain more than "
                        f"{MAX_USERS} distinct user_ids in field "
                        f"'{self.userid_field}'. Narrow the search or split "
                        f"into smaller batches."
                    )
                seen.add(uid)
                user_ids.append(uid)

        if not user_ids:
            self.logger.info(
                "claudechats: no values in field '%s'; nothing to fetch.",
                self.userid_field,
            )
            return

        session_key = self._metadata.searchinfo.session_key
        account_name, api_key = self._resolve_account(session_key, self.account)
        headers = self._build_headers(api_key)

        self.logger.info(
            "claudechats: account='%s', fetching chats for %d user(s), messages=%s",
            account_name,
            len(user_ids),
            self.messages,
        )

        for chat in self._iter_chats(headers, user_ids):
            if not self.messages:
                yield self._chat_row(chat)
                continue
            chat_id = chat.get("id")
            if not chat_id:
                continue
            chat_detail = self._fetch_chat_messages(headers, chat_id)
            if chat_detail is None:
                continue
            chat_messages = chat_detail.get("chat_messages") or []
            if not chat_messages:
                self.logger.info(
                    "claudechats: chat %s has no messages; skipping in "
                    "messages=true mode.",
                    chat_id,
                )
                continue
            yield from self._message_rows(chat_detail)

    @staticmethod
    def _split_multivalue(raw: Any) -> list[str]:
        """Return ``raw`` as a list of string user_ids.

        Handles scalar strings and Splunk multi-value fields (which
        searchcommands surfaces as lists) uniformly.
        """
        if isinstance(raw, list):
            return [str(v).strip() for v in raw if v is not None]
        return [str(raw).strip()]

    def _resolve_account(
        self, session_key: str, requested: str | None
    ) -> tuple[str, str]:
        """Return ``(account_name, api_key)`` for the account to use.

        If ``requested`` is provided, that specific stanza is loaded.
        Otherwise the conf file is enumerated: exactly one configured
        account is auto-selected; zero or many raise with a remediation
        hint so the operator knows whether to add an account or pick
        between existing ones.
        """
        cfm = conf_manager.ConfManager(
            session_key,
            ADDON_NAME,
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/"
            "conf-ta-anthropic_compliance_api_account",
        )
        conf_file = cfm.get_conf("ta-anthropic_compliance_api_account")

        if requested:
            try:
                account = conf_file.get(requested)
            except ConfStanzaNotExistException as exc:
                configured = self._list_account_names(conf_file)
                if configured:
                    hint = f" Configured accounts: {', '.join(configured)}."
                else:
                    hint = (
                        " No accounts are configured — add one in 'Apps → "
                        "TA-Anthropic_Compliance_API → Configuration → "
                        "Account'."
                    )
                raise RuntimeError(
                    f"claudechats: account '{requested}' is not configured." + hint
                ) from exc
            except Exception as exc:
                raise RuntimeError(
                    f"claudechats: unable to read account '{requested}'. "
                    f"The running user must hold the 'list_storage_passwords' "
                    f"capability (granted to 'admin' by default). Underlying "
                    f"error: {exc}"
                ) from exc
            api_key = account.get("api_key")
            if not api_key:
                raise RuntimeError(
                    f"claudechats: account '{requested}' has no api_key set."
                )
            return requested, api_key

        try:
            all_accounts = conf_file.get_all()
        except Exception as exc:
            raise RuntimeError(
                f"claudechats: unable to enumerate configured accounts. "
                f"The running user must hold the 'list_storage_passwords' "
                f"capability (granted to 'admin' by default). Underlying "
                f"error: {exc}"
            ) from exc

        names = sorted(all_accounts.keys())
        if not names:
            raise RuntimeError(
                "claudechats: no account is configured. Add one in "
                "'Apps → TA-Anthropic_Compliance_API → Configuration → "
                "Account' before running this command."
            )
        if len(names) > 1:
            raise RuntimeError(
                f"claudechats: {len(names)} accounts configured "
                f"({', '.join(names)}). Specify which to use with "
                f"account=<name>."
            )

        name = names[0]
        api_key = all_accounts[name].get("api_key")
        if not api_key:
            raise RuntimeError(f"claudechats: account '{name}' has no api_key set.")
        return name, api_key

    @staticmethod
    def _list_account_names(conf_file: Any) -> list[str]:
        """Return sorted account stanza names; ``[]`` on enumeration failure.

        Used to enrich the "account not configured" error so the operator
        can see what they meant to type. Swallows enumeration errors
        because the caller is already in an error path.
        """
        try:
            return sorted((conf_file.get_all() or {}).keys())
        except Exception:
            return []

    @staticmethod
    def _build_headers(api_key: str) -> dict:
        return {
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
        }

    def _get_with_retry(
        self,
        url: str,
        headers: dict,
        params: list[tuple[str, str]] | dict,
        label: str,
    ) -> dict:
        """GET with retry on transient failures.

        Retries with backoff on:

        * HTTP 429: honors ``Retry-After`` header, falls back to
          ``2 ** (attempt + 1)`` seconds.
        * HTTP 5xx: exponential backoff.
        * ``requests.RequestException``: exponential backoff. Covers
          connection resets, timeouts, DNS, SSL — every transient
          network failure under one umbrella.

        Hard-fails (no retry) on:

        * HTTP 401: surfaces a scopes-aware error message.
        * Other 4xx: logs the response body and raises.
        """
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(
                    url, headers=headers, params=params, timeout=REQUEST_TIMEOUT
                )
            except requests.exceptions.RequestException as exc:
                backoff = 2 ** (attempt + 1)
                self.logger.warning(
                    "claudechats: network error on %s: %s; sleeping %ds (attempt %d)",
                    label,
                    exc,
                    backoff,
                    attempt + 1,
                )
                time.sleep(backoff)
                continue
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", 2 ** (attempt + 1)))
                self.logger.warning(
                    "claudechats: rate limited on %s; sleeping %ds (attempt %d)",
                    label,
                    retry_after,
                    attempt + 1,
                )
                time.sleep(retry_after)
                continue
            if resp.status_code >= 500:
                backoff = 2 ** (attempt + 1)
                self.logger.warning(
                    "claudechats: HTTP %d on %s: %s; sleeping %ds (attempt %d)",
                    resp.status_code,
                    label,
                    resp.text[:500],
                    backoff,
                    attempt + 1,
                )
                time.sleep(backoff)
                continue
            if resp.status_code == 401:
                self.logger.error(
                    "claudechats: HTTP 401 fetching %s — requires a "
                    "Compliance Access Key (sk-ant-api01-...) with scope "
                    "read:compliance_user_data.",
                    label,
                )
                resp.raise_for_status()
            if 400 <= resp.status_code < 500:
                self.logger.error(
                    "claudechats: HTTP %d fetching %s — response: %s",
                    resp.status_code,
                    label,
                    resp.text[:500],
                )
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"claudechats: exceeded retry limit fetching {label}")

    def _iter_chats(
        self, headers: dict, user_ids: list[str]
    ) -> Generator[dict, None, None]:
        """Yield chat dicts across batched, paginated ``/apps/chats`` calls."""
        url = f"{API_BASE_URL}/apps/chats"
        for start in range(0, len(user_ids), USER_BATCH_SIZE):
            batch = user_ids[start : start + USER_BATCH_SIZE]
            batch_label = (
                f"chats[batch {start // USER_BATCH_SIZE + 1}, {len(batch)} user(s)]"
            )
            params = self._build_chat_params(batch)
            while True:
                data = self._get_with_retry(url, headers, params, batch_label)
                items: list[dict] = data.get("data", [])
                for chat in items:
                    yield chat
                if not data.get("has_more") or not items:
                    break
                params = self._build_chat_params(
                    batch, after_id=items[-1].get("id", "")
                )

    @staticmethod
    def _build_chat_params(
        user_ids: list[str], after_id: str | None = None
    ) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = [("user_ids[]", uid) for uid in user_ids]
        params.append(("limit", str(CHATS_PAGE_LIMIT)))
        if after_id:
            params.append(("after_id", after_id))
        return params

    def _fetch_chat_messages(self, headers: dict, chat_id: str) -> dict | None:
        url = f"{API_BASE_URL}/apps/chats/{chat_id}/messages"
        try:
            return self._get_with_retry(url, headers, {}, f"chat_messages[{chat_id}]")
        except Exception as exc:
            self.logger.error(
                "claudechats: failed to fetch messages for %s: %s",
                chat_id,
                exc,
            )
            return None

    @staticmethod
    def _chat_row(chat: dict) -> dict:
        """Flatten a chat into a pipeline row with ``chat.``-prefixed columns."""
        row = _flatten(chat, prefix="chat")
        ts = _iso_to_epoch(chat.get("updated_at") or chat.get("created_at"))
        if ts is not None:
            row["_time"] = ts
        return row

    @staticmethod
    def _message_rows(chat_detail: dict) -> Generator[dict, None, None]:
        """Yield one row per message with ``chat.``-prefixed chat context.

        Message fields are emitted via :func:`_normalize_message`:
        ``message_id``, ``message_created_at``, ``role``, ``text``,
        ``content_types``.
        """
        chat_only = {k: v for k, v in chat_detail.items() if k != "chat_messages"}
        chat_context = _flatten(chat_only, prefix="chat")
        for message in chat_detail.get("chat_messages") or []:
            row = {**chat_context, **_flatten(_normalize_message(message))}
            ts = _iso_to_epoch(message.get("created_at"))
            if ts is not None:
                row["_time"] = ts
            yield row


dispatch(ClaudeChatsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
