#!/bin/python
# -*- coding: utf-8 -*-

import sys
import json
import re
import logging
import html
from typing import Dict, Any, Optional, List

import requests

try:
    from splunk.clilib import cli_common as cli
except Exception:
    cli = None


LOG = logging.getLogger("telegram_app")
if not LOG.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s telegram_app [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    LOG.addHandler(handler)
LOG.setLevel(logging.INFO)


TELEGRAM_MAX_MESSAGE_LENGTH = 4096
DEFAULT_TIMEOUT = 10


def str_to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default

    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def safe_int(value: Any, default: int, minimum: int = 1, maximum: int = 120) -> int:
    try:
        number = int(str(value).strip())
    except Exception:
        return default

    if number < minimum or number > maximum:
        return default

    return number


def load_connection_settings() -> Dict[str, Any]:
    defaults = {
        "verify_ssl": "true",
        "proxy_enabled": "false",
        "proxy_scheme": "http",
        "proxy_host": "",
        "proxy_ip": "",
        "proxy_port": "",
        "request_timeout": str(DEFAULT_TIMEOUT),
    }

    if cli is None:
        LOG.warning("telegram_app: cannot import Splunk cli_common, using default connection settings")
        return defaults

    try:
        stanza = cli.getConfStanza("telegram", "connection")
    except Exception as e:
        LOG.warning("telegram_app: cannot read telegram.conf: %s", e)
        return defaults

    cfg = defaults.copy()
    cfg.update(stanza or {})

    return cfg


def build_proxies(conn: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if not str_to_bool(conn.get("proxy_enabled"), default=False):
        return None

    scheme = str(conn.get("proxy_scheme", "http")).strip().lower() or "http"

    if scheme not in ("http", "https"):
        LOG.warning("telegram_app: unsupported proxy_scheme=%s, fallback to http", scheme)
        scheme = "http"

    host = str(conn.get("proxy_host") or conn.get("proxy_ip") or "").strip()
    port = str(conn.get("proxy_port", "")).strip()

    if not host or not port:
        LOG.warning("telegram_app: proxy is enabled, but proxy host or port is empty; using direct connection")
        return None

    proxy_url = f"{scheme}://{host}:{port}"

    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def parse_message_thread_id(topic_id_or_link: Optional[str]) -> Optional[int]:
    if not topic_id_or_link:
        return None

    value = str(topic_id_or_link).strip()

    if not value:
        return None

    if value.isdigit():
        return int(value)

    match = re.search(r"t\.me/c/\d+/(\d+)(?:/\d+)?", value)
    if match:
        return int(match.group(1))

    match = re.search(r"[?&](thread|topic)=(\d+)", value)
    if match:
        return int(match.group(2))

    return None


def read_payload() -> Dict[str, Any]:
    raw = sys.stdin.read()

    if not raw:
        raise ValueError("No stdin payload received from Splunk")

    try:
        return json.loads(raw)
    except Exception as e:
        raise ValueError(f"Cannot parse JSON payload: {e}") from e


def split_chat_ids(raw_chat_id: Any) -> List[str]:
    value = str(raw_chat_id or "").strip()

    if not value:
        return []

    return [item.strip() for item in re.split(r"[,;\n]+", value) if item.strip()]


def extract_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    config = payload.get("configuration") or {}

    title = config.get("title") or "Splunk alert"
    message = config.get("message") or ""
    severity = config.get("severity") or "info"
    bot_id = str(config.get("bot_id") or "").strip()
    result_link = config.get("result_link")
    chat_mode = str(config.get("chat_mode") or "regular").strip().lower()
    topic_id_or_link = config.get("topic_id_or_link")
    raw_chat_id = config.get("chat_id") or config.get("chat_ids")
    chat_ids = split_chat_ids(raw_chat_id)

    if not bot_id:
        raise ValueError("bot_id is not configured")

    if not chat_ids:
        raise ValueError("chat_id is not configured")

    if chat_mode not in ("regular", "super"):
        chat_mode = "regular"

    return {
        "title": title,
        "message": message,
        "severity": severity,
        "bot_id": bot_id,
        "result_link": result_link,
        "chat_mode": chat_mode,
        "topic_id_or_link": topic_id_or_link,
        "chat_ids": chat_ids,
    }


def split_telegram_message(text: str) -> List[str]:
    if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
        return [text]

    limit = TELEGRAM_MAX_MESSAGE_LENGTH - 40
    chunks = []
    remaining = text

    while remaining:
        chunk = remaining[:limit]
        split_at = max(chunk.rfind("\n"), chunk.rfind(" "))

        if split_at > 500:
            chunk = chunk[:split_at]

        chunks.append(chunk.strip())
        remaining = remaining[len(chunk):].strip()

    total = len(chunks)

    return [
        f"<b>Part {index}/{total}</b>\n{chunk}"
        for index, chunk in enumerate(chunks, start=1)
    ]


def build_body(config: Dict[str, Any], payload: Dict[str, Any]) -> str:
    title = html.escape(str(config["title"]))
    message = html.escape(str(config["message"]))
    severity = html.escape(str(config["severity"]))
    result_link_flag = config["result_link"]

    results_url = ""

    if str_to_bool(result_link_flag, default=False):
        results_url = html.escape(str(payload.get("results_link") or ""))

    body = (
        f"<b>{title}</b>\n"
        f"<b>SEVERITY:</b> {severity}\n"
        f"<b>MESSAGE:</b> {message}"
    )

    if results_url:
        body += f"\n<b>RESULT LINK:</b> {results_url}"

    return body


def send_alert(
    text: str,
    bot_id: str,
    chat_id: str,
    *,
    message_thread_id: Optional[int] = None,
    verify_ssl: bool = True,
    proxies: Optional[Dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> None:
    url = f"https://api.telegram.org/bot{bot_id}/sendMessage"

    data: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    if message_thread_id is not None:
        data["message_thread_id"] = message_thread_id

    LOG.info(
        "telegram_app: sending alert to chat_id=%s thread=%s proxy=%s timeout=%s",
        chat_id,
        message_thread_id,
        bool(proxies),
        timeout,
    )

    response = requests.post(
        url,
        json=data,
        timeout=timeout,
        verify=verify_ssl,
        proxies=proxies,
    )

    if response.status_code != 200:
        LOG.error(
            "telegram_app: Telegram API error for chat_id=%s: %s %s",
            chat_id,
            response.status_code,
            response.text,
        )
        response.raise_for_status()


def main() -> None:
    try:
        payload = read_payload()
        cfg = extract_config(payload)

        conn = load_connection_settings()

        verify_ssl = str_to_bool(conn.get("verify_ssl"), default=True)
        timeout = safe_int(conn.get("request_timeout"), DEFAULT_TIMEOUT)
        proxies = build_proxies(conn)

        body = build_body(cfg, payload)
        message_parts = split_telegram_message(body)

        thread_id: Optional[int] = None

        if cfg["chat_mode"] == "super":
            thread_id = parse_message_thread_id(cfg["topic_id_or_link"])

            if thread_id is None:
                raise ValueError(
                    "Chat mode 'super' is selected but message_thread_id is not defined. "
                    "Provide a numeric topic ID or supported Telegram topic link."
                )

        for chat_id in cfg["chat_ids"]:
            for part in message_parts:
                send_alert(
                    part,
                    cfg["bot_id"],
                    chat_id,
                    message_thread_id=thread_id,
                    verify_ssl=verify_ssl,
                    proxies=proxies,
                    timeout=timeout,
                )

    except Exception as e:
        LOG.exception("telegram_app: failed to process alert: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
