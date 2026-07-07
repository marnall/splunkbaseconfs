import configparser
import re
from pathlib import Path
from typing import Any, Dict, Optional


def _read_app_version() -> str:
    try:
        conf = configparser.ConfigParser()
        conf.read(Path(__file__).parent.parent / "default" / "app.conf")
        return conf.get("launcher", "version")
    except (configparser.Error, OSError):
        return "unknown"


APP_VERSION = _read_app_version()

# Splunk SimpleXML dispatches each dashboard panel as a search whose SID
# embeds the panel identifier as `_searchN_`. Splunk Studio uses opaque UUIDs
# and is intentionally not matched; attribution is best-effort.
_PANEL_SID_RE = re.compile(r"_(search\d+)_")

# A value is emitted bare unless it contains whitespace, `"`, `:`, or `\`, in
# which case it is double-quoted with `\\`/`\"` escapes. `:` is the key/value
# delimiter, so any value containing it must be quoted to keep the comment
# unambiguous for a known-key consumer.
_VALUE_UNSAFE = re.compile(r"[\s\":\\]")

# Precautionary bound on saved-search names; Splunk-side length cap not verified.
_LABEL_MAX_LEN = 256


def _truncate(v: str, limit: int = _LABEL_MAX_LEN) -> str:
    return v if len(v) <= limit else v[: limit - 1] + "…"


def _str_attr(obj: Any, name: str) -> Optional[str]:
    if obj is None:
        return None
    value = getattr(obj, name, None)
    return value if isinstance(value, str) and value else None


def extract_attribution(searchinfo: Any, search_results_info: Any) -> Dict[str, str]:
    """Collect Splunk attribution metadata for forwarding on `hdx_query_admin_comment`.

    Returns the empty dict when `search_results_info` is None — that is how
    `hdxdescribe` opts out of attribution. Insertion order is the wire order.
    Pure: no Splunk REST or file I/O.
    """
    if search_results_info is None:
        return {}

    out: Dict[str, str] = {}

    if user := _str_attr(searchinfo, "username"):
        out["user"] = user

    if provenance := _str_attr(search_results_info, "provenance"):
        out["provenance"] = provenance
        # `UI:Dashboard:<view_id>` — surface the view id directly so log
        # consumers don't have to re-parse. maxsplit=2 keeps any inner `:`.
        parts = provenance.split(":", 2)
        if len(parts) == 3 and parts[0] == "UI" and parts[1] == "Dashboard" and parts[2]:
            out["dashboard"] = parts[2]

    if (sid := _str_attr(searchinfo, "sid")) and (m := _PANEL_SID_RE.search(sid)):
        out["panel"] = m.group(1)

    # Splunk alerts are saved searches, so the alert name is `label` (or
    # `savedsearch_label` on some dispatch paths).
    if label := _str_attr(search_results_info, "label") or _str_attr(search_results_info, "savedsearch_label"):
        out["saved_search"] = _truncate(label)

    return out


def _format_value(v: str) -> str:
    if v and not _VALUE_UNSAFE.search(v):
        return v
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_admin_comment(searchinfo: Any, search_results_info: Any = None) -> str:
    """Build the `hdx_query_admin_comment` value.

    Always emits the `User: Splunk <ver> / hdxsearch <ver>` prefix and a
    `sid:` token when known. Attribution fields are appended as `key:value`
    (values containing whitespace, `"`, `:`, or `\\` are double-quoted) only
    when `search_results_info` is provided.
    """
    splunk_version = _str_attr(searchinfo, "splunk_version") or "unknown"
    parts = [f"User: Splunk {splunk_version} / hdxsearch {APP_VERSION}"]
    if sid := _str_attr(searchinfo, "sid"):
        parts.append(f"sid:{_format_value(sid)}")
    for k, v in extract_attribution(searchinfo, search_results_info).items():
        parts.append(f"{k}:{_format_value(v)}")
    return " ".join(parts)
