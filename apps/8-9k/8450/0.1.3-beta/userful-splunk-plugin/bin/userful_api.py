"""
Userful helper REST endpoints to expose dashboard embed URLs for the proxy.

This handler is intentionally read-only: it enumerates configured modular
inputs and returns pre-built embed links for every visible dashboard so a
downstream system can consume them programmatically.
"""

from __future__ import absolute_import

import json
import logging
import socket
import os
from typing import Dict, List

try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser

import splunk.entity as entity
import splunk.rest as rest

LOG = logging.getLogger(__name__)
if not LOG.handlers:
    LOG.addHandler(logging.StreamHandler())
LOG.setLevel(logging.INFO)


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return default
    return str(value).lower() in ("1", "true", "t", "yes", "on")

def _get_arg(args, name, default=None):
    value = (args or {}).get(name, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value


def _extract_host(request_headers: Dict[str, str]) -> str:
    """
    Pick a host to build embed URLs.
    We strip the port because the proxy port is appended later.
    """
    host_header = (request_headers or {}).get("host", "")
    hostname = host_header.split(":")[0]
    return hostname or socket.getfqdn() or "localhost"


def _load_dashboards(session_key: str, app_filter: str) -> List[Dict[str, str]]:
    """Return dashboards visible to the caller, optionally filtered by app."""
    _, content = rest.simpleRequest(
        "/servicesNS/-/-/data/ui/views",
        sessionKey=session_key,
        getargs={"output_mode": "json", "count": -1},
        raiseAllErrors=True,
    )
    payload = json.loads(content)
    dashboards = []
    for entry in payload.get("entry", []):
        entry_content = entry.get("content", {}) or {}
        if str(entry_content.get("isDashboard", "0")).lower() not in ("1", "true"):
            continue
        app = entry.get("acl", {}).get("app")
        if app_filter not in (None, "", "*") and app != app_filter:
            continue
        dashboards.append(
            {
                "name": entry.get("name"),
                "label": entry_content.get("label"),
                "app": app,
                "version": entry_content.get("version"),
            }
        )
    return dashboards


APP_NAMESPACE = os.path.basename(os.path.dirname(os.path.dirname(__file__))) or "Userful"


MODINPUT_KIND = "userful_proxy"

PLATFORM_SERVER_REQUIRED_TRUSTED_IPS = ["127.0.0.1"]
PLATFORM_WEB_REQUIRED_TRUSTED_IPS = ["127.0.0.1", "192.168.127.0/24"]
PLATFORM_SERVER_TRUSTED_IP = ", ".join(PLATFORM_SERVER_REQUIRED_TRUSTED_IPS)
PLATFORM_WEB_TRUSTED_IP = ", ".join(PLATFORM_WEB_REQUIRED_TRUSTED_IPS)

REQUIRED_WEB_SETTINGS = {
    "SSOMode": None,
    "trustedIP": PLATFORM_WEB_TRUSTED_IP,
    "remoteUser": None,
    "remoteUserMatchExact": None,
    "tools.proxy.on": None,
}

REQUIRED_SERVER_SETTINGS = {
    "trustedIP": PLATFORM_SERVER_TRUSTED_IP,
}

WEB_SETTINGS_DEFAULTS = {
    "SSOMode": "permissive",
    "trustedIP": PLATFORM_WEB_TRUSTED_IP,
    "remoteUser": "Remote-User",
    "remoteUserMatchExact": "false",
    "tools.proxy.on": "false",
}

SERVER_SETTINGS_DEFAULTS = {
    "trustedIP": PLATFORM_SERVER_TRUSTED_IP,
}


def _stringify(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_token(value):
    return _stringify(value).lower()


def _split_csv_values(value):
    if value is None:
        return []
    parts = [part.strip() for part in str(value).split(",")]
    return [part for part in parts if part]


def _csv_contains_values(value, required_values):
    current_values = {_normalize_token(item) for item in _split_csv_values(value)}
    for required in required_values:
        if _normalize_token(required) not in current_values:
            return False
    return True


def _merge_csv_values(existing_value, required_values):
    merged = _split_csv_values(existing_value)
    seen = {_normalize_token(item) for item in merged}

    for required in required_values:
        normalized_required = _normalize_token(required)
        if normalized_required and normalized_required not in seen:
            merged.append(_stringify(required))
            seen.add(normalized_required)

    return ", ".join(merged)


def _new_conf_parser():
    parser = ConfigParser.RawConfigParser()
    parser.optionxform = str
    return parser


def _load_conf(path):
    if not os.path.isfile(path):
        return None
    parser = _new_conf_parser()
    with open(path, "r") as handle:
        if hasattr(parser, "read_file"):
            parser.read_file(handle)
        else:
            parser.readfp(handle)
    return parser


def _ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)


def _write_conf(parser, path):
    _ensure_parent_dir(path)
    with open(path, "w") as handle:
        parser.write(handle)


def _upsert_conf_section(
    path, section, updates, merge_csv_values=None, set_if_missing=None
):
    parser = _load_conf(path)
    if parser is None:
        parser = _new_conf_parser()

    if not parser.has_section(section):
        parser.add_section(section)

    merge_csv_values = merge_csv_values or {}
    set_if_missing = set_if_missing or set()
    for key, value in updates.items():
        required_csv_values = merge_csv_values.get(key)
        if required_csv_values is not None:
            existing_value = ""
            if parser.has_option(section, key):
                existing_value = parser.get(section, key)
            parser.set(
                section,
                key,
                _merge_csv_values(existing_value, required_csv_values),
            )
        elif key in set_if_missing:
            existing_value = ""
            if parser.has_option(section, key):
                existing_value = _stringify(parser.get(section, key))
            if not existing_value:
                parser.set(section, key, _stringify(value))
        else:
            parser.set(section, key, _stringify(value))

    _write_conf(parser, path)


def _section_options(parser, section):
    options = {}
    if parser is None or not parser.has_section(section):
        return options
    for key, value in parser.items(section):
        options[key.lower()] = _stringify(value)
    return options


def _check_required(option_map, required, required_csv_contains=None):
    checks = []
    missing = []
    mismatched = []
    required_csv_contains = required_csv_contains or {}

    for key, expected in required.items():
        actual = option_map.get(key.lower())
        present = actual not in (None, "")
        required_csv_values = required_csv_contains.get(key.lower())

        ok = present
        if required_csv_values is not None and present:
            ok = _csv_contains_values(actual, required_csv_values)
        elif expected is not None and present:
            ok = actual.lower() == expected.lower()

        if not present:
            missing.append(key)
        elif required_csv_values is not None and not _csv_contains_values(
            actual, required_csv_values
        ):
            mismatched.append(
                {
                    "key": key,
                    "expected": expected,
                    "actual": actual,
                }
            )
        elif expected is not None and actual.lower() != expected.lower():
            mismatched.append(
                {
                    "key": key,
                    "expected": expected,
                    "actual": actual,
                }
            )

        checks.append(
            {
                "key": key,
                "expected": expected,
                "actual": actual if present else None,
                "ok": ok,
            }
        )

    return checks, missing, mismatched


def _build_file_status(path, section, required, required_csv_contains=None):
    parser = _load_conf(path)
    exists = parser is not None
    section_exists = exists and parser.has_section(section)
    options = _section_options(parser, section)
    checks, missing, mismatched = _check_required(
        options, required, required_csv_contains
    )
    configured = bool(exists and section_exists and not missing and not mismatched)

    return {
        "path": path,
        "section": section,
        "exists": exists,
        "section_exists": section_exists,
        "configured": configured,
        "checks": checks,
        "missing": missing,
        "mismatched": mismatched,
    }


def _build_platform_config_status():
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    if not splunk_home:
        raise EnvironmentError("SPLUNK_HOME is not set")
    base_path = os.path.join(splunk_home, "etc", "system", "local")
    web_path = os.path.join(base_path, "web.conf")
    server_path = os.path.join(base_path, "server.conf")

    web_status = _build_file_status(
        web_path,
        "settings",
        REQUIRED_WEB_SETTINGS,
        required_csv_contains={"trustedip": PLATFORM_WEB_REQUIRED_TRUSTED_IPS},
    )
    server_status = _build_file_status(
        server_path,
        "general",
        REQUIRED_SERVER_SETTINGS,
        required_csv_contains={"trustedip": PLATFORM_SERVER_REQUIRED_TRUSTED_IPS},
    )
    configured = bool(web_status["configured"] and server_status["configured"])

    return {
        "configured": configured,
        "files": {
            "web_conf": web_status,
            "server_conf": server_status,
        },
        "snippets": {
            "web_conf": (
                "[settings]\n"
                "SSOMode = permissive\n"
                "trustedIP = 127.0.0.1, 192.168.127.0/24\n"
                "remoteUser = Remote-User\n"
                "remoteUserMatchExact = false\n"
                "tools.proxy.on = false"
            ),
            "server_conf": "[general]\ntrustedIP = 127.0.0.1",
        },
        "commands": {
            "web_conf": (
                "cat > \"$SPLUNK_HOME/etc/system/local/web.conf\" <<'EOF'\n"
                "[settings]\n"
                "SSOMode = permissive\n"
                "trustedIP = 127.0.0.1, 192.168.127.0/24\n"
                "remoteUser = Remote-User\n"
                "remoteUserMatchExact = false\n"
                "tools.proxy.on = false\n"
                "EOF"
            ),
            "server_conf": (
                "cat > \"$SPLUNK_HOME/etc/system/local/server.conf\" <<'EOF'\n"
                "[general]\n"
                "trustedIP = 127.0.0.1\n"
                "EOF"
            ),
        },
        "restart_command": "$SPLUNK_HOME/bin/splunk restart",
    }


def _upsert_platform_config():
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    if not splunk_home:
        raise EnvironmentError("SPLUNK_HOME is not set")
    base_path = os.path.join(splunk_home, "etc", "system", "local")
    web_path = os.path.join(base_path, "web.conf")
    server_path = os.path.join(base_path, "server.conf")

    web_updates = dict(WEB_SETTINGS_DEFAULTS)
    web_updates["trustedIP"] = PLATFORM_WEB_TRUSTED_IP

    server_updates = dict(SERVER_SETTINGS_DEFAULTS)
    server_updates["trustedIP"] = PLATFORM_SERVER_TRUSTED_IP

    _upsert_conf_section(
        web_path,
        "settings",
        web_updates,
        merge_csv_values={"trustedIP": PLATFORM_WEB_REQUIRED_TRUSTED_IPS},
        set_if_missing={
            "SSOMode",
            "remoteUser",
            "remoteUserMatchExact",
            "tools.proxy.on",
        },
    )
    _upsert_conf_section(
        server_path,
        "general",
        server_updates,
        merge_csv_values={"trustedIP": PLATFORM_SERVER_REQUIRED_TRUSTED_IPS},
    )

    return {
        "trusted_ips": {
            "web_conf": PLATFORM_WEB_TRUSTED_IP,
            "server_conf": PLATFORM_SERVER_TRUSTED_IP,
        },
        "files": {
            "web_conf": web_path,
            "server_conf": server_path,
        },
    }


def _load_modinputs(session_key: str) -> Dict[str, Dict[str, str]]:
    """Fetch configured modular inputs."""
    return entity.getEntities(
        f"data/inputs/{MODINPUT_KIND}",
        sessionKey=session_key,
        namespace=APP_NAMESPACE,
        owner="nobody",
        count=-1,
    )


class UserfulDashboardsHandler(rest.BaseRestHandler):
    """
    GET /services/userful/embeds
    Optional query params:
      - app: limit to a specific app (defaults to all)
      - stanza: limit to a specific modular input name
      - host: override host used in embed URLs
      - include_disabled: whether to include disabled inputs (default false)
    """

    def handle_GET(self):
        app_filter = _get_arg(self.args, "app")
        stanza_filter = _get_arg(self.args, "stanza")
        include_disabled = _as_bool(self.args.get("include_disabled"), default=False)
        debug = _as_bool(self.args.get("debug"), default=False)

        try:
            dashboards = _load_dashboards(self.sessionKey, app_filter)
            inputs = _load_modinputs(self.sessionKey)
            headers = {}
            try:
                headers = self.request["headers"]
            except Exception:
                headers = {}

            if debug:
                LOG.info("Userful embeds args: %s", self.args)

            host = _get_arg(self.args, "embed_host") or _get_arg(self.args, "host") or _extract_host(headers)

            embeds = []
            for name, cfg in inputs.items():
                if stanza_filter and stanza_filter != name:
                    continue
                disabled = _as_bool(cfg.get("disabled"))
                if disabled and not include_disabled:
                    continue

                port = cfg.get("port")
                if not port:
                    LOG.warning("Skipping stanza %s because no port is set", name)
                    continue

                base_url = f"http://{host}:{port}"
                for dash in dashboards:
                    embed_url = (
                        f"{base_url}/en-US/app/{dash['app']}/{dash['name']}"
                        "?display.page.embed=true"
                    )
                    embeds.append(
                        {
                            "app": dash["app"],
                            "dashboard": dash["name"],
                            "label": dash.get("label"),
                            "embed_url": embed_url,
                            "stanza": name,
                            "port": port,
                            "connect_from": cfg.get("connect_from"),
                            "username": cfg.get("username"),
                            "disabled": disabled,
                        }
                    )

            response = {
                "embeds": embeds,
                "filters": {
                    "app": app_filter or "*",
                    "stanza": stanza_filter or "*",
                    "include_disabled": include_disabled,
                    "host": host,
                },
                "counts": {"dashboards": len(dashboards), "embeds": len(embeds)},
            }

            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps(response, sort_keys=True))
        except Exception as exc:
            LOG.exception("Failed to build embed list")
            self.response.setStatus(500)
            self.response.write(
                json.dumps(
                    {"error": str(exc), "message": "Failed to build embed list"}
                )
            )


class UserfulPlatformConfigStatusHandler(rest.BaseRestHandler):
    def handle_GET(self):
        try:
            payload = _build_platform_config_status()
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps(payload, sort_keys=True))
        except Exception as exc:
            LOG.exception("Failed to inspect platform config")
            self.response.setStatus(500)
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(
                json.dumps(
                    {
                        "error": str(exc),
                        "message": "Failed to inspect platform configuration",
                    }
                )
            )


class UserfulPlatformConfigHandler(rest.BaseRestHandler):
    def handle_POST(self):
        try:
            update_result = _upsert_platform_config()
            payload = _build_platform_config_status()
            payload["updated"] = update_result
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(json.dumps(payload, sort_keys=True))
        except Exception as exc:
            LOG.exception("Failed to update platform config")
            self.response.setStatus(500)
            self.response.setHeader("Content-Type", "application/json")
            self.response.write(
                json.dumps(
                    {
                        "error": str(exc),
                        "message": "Failed to update platform configuration",
                    }
                )
            )
