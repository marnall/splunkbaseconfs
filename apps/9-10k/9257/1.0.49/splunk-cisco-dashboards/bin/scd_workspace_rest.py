"""Validated custom REST persistence for shared dashboard configuration.

The browser reads merged configuration through Splunk's generic conf endpoints,
but all shared mutations use these capability-protected handlers. This lets a
custom role manage workspaces, topology, and bounded background uploads without
receiving the broad ``admin_all_objects`` capability or direct write access to
the relevant shared configuration objects.
"""

from __future__ import absolute_import

import base64
import json
import re
import urllib.parse
from datetime import datetime, timezone

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication


WORKSPACE_CONF = "insights_workspaces"
TOPOLOGY_CONF = "customer_topology"
TEMPLATES_CONF = "templates"
APP_NAME = "splunk-cisco-dashboards"
MAX_SCALAR_BYTES = 4096
MAX_LOGO_BYTES = 256 * 1024
MAX_LIST_BYTES = 64 * 1024
MAX_TOPOLOGY_PAYLOAD_BYTES = 128 * 1024
MAX_TEMPLATE_BACKGROUND_DATA_BYTES = 3 * 1024 * 1024
MAX_TEMPLATE_BACKGROUND_ENTRIES = 48
MAX_TEMPLATE_BACKGROUND_TOTAL_BYTES = 12 * 1024 * 1024
# Keep these admission limits in step with
# webapp/common/lib/customerTopologyBounds.ts. A byte cap alone still permits
# thousands of tiny objects that make every viewer's Leaflet map expensive.
MAX_TOPOLOGY_SITES = 250
MAX_TOPOLOGY_LINKS = 500
MAX_TOPOLOGY_SITE_ALIASES = 16
_SHARED_IMAGE_DATA_URI = re.compile(
    r"^data:image/(?:png|jpeg|gif|webp|svg\+xml)"
    r"(?:;(?:base64|utf8|charset=[A-Za-z0-9._-]+))*?,[^\r\n]*$",
    re.IGNORECASE,
)
_SHARED_APP_STATIC_IMAGE_PATH = re.compile(
    r"^/static/app/splunk-cisco-dashboards/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+$"
)
_TEMPLATE_BACKGROUND_DATA_URI = re.compile(
    r"^data:image/(png|jpeg|gif|webp);base64,([A-Za-z0-9+/]*={0,2})$",
    re.IGNORECASE,
)

_WORKSPACE_FIELDS = frozenset(
    (
        "label",
        "source_workspace",
        "sections",
        "default_visible_sections",
        "max_visible_sections",
        "min_tile_count",
        "max_tile_count",
        "default_tile_count",
        "header_title",
        "header_subtitle",
        "default_logo_src",
        "hide_default_logo",
        "legacy_view_names",
        "is_builtin",
        "enabled",
        "sort_order",
        "map_visible",
        "map_position",
        "regional_view",
        "updated_at",
        "updated_by",
    )
)
_LAYOUT_FIELDS = frozenset(
    ("tiles", "searchbase_additions", "visible_count", "updated_at", "updated_by")
)
_SIGNAL_ITEM_FIELDS = frozenset(
    (
        "search_name",
        "label",
        "value_field",
        "threshold_warning",
        "threshold_critical",
        "threshold_direction",
        "threshold_unit",
        "updated_at",
        "updated_by",
    )
)
_SIGNAL_RAIL_FIELDS = frozenset(
    (
        "enabled",
        "show_priority_drilldown",
        "rows",
        "speed",
        "density",
        "font_size",
        "items",
        "updated_at",
        "updated_by",
    )
)
_TOPOLOGY_FIELDS = frozenset(
    (
        "schema_version",
        "title",
        "description",
        "updated_at",
        "updated_by",
        "site_count",
        "link_count",
        "section_titles",
        "payload_json",
    )
)
_TEMPLATE_BACKGROUND_FIELDS = frozenset(("data",))

_STANZA_RULES = {
    WORKSPACE_CONF: (
        (re.compile(r"^workspace\.[a-z][a-z0-9_]{0,63}$"), _WORKSPACE_FIELDS),
        (
            re.compile(r"^layout\.[a-z][a-z0-9_]{0,63}\.[a-z][a-z0-9_]{0,63}$"),
            _LAYOUT_FIELDS,
        ),
        (re.compile(r"^signal_item\.[a-z][a-z0-9_]{0,127}$"), _SIGNAL_ITEM_FIELDS),
        (re.compile(r"^signal_rail\.[a-z][a-z0-9_]{0,63}$"), _SIGNAL_RAIL_FIELDS),
    ),
    TOPOLOGY_CONF: (
        (
            re.compile(r"^overview_customer_connectivity(?:_[a-z0-9_]{1,72})?$"),
            _TOPOLOGY_FIELDS,
        ),
    ),
    TEMPLATES_CONF: (
        (
            re.compile(r"^background://bg_[a-z0-9][a-z0-9_-]{0,63}$"),
            _TEMPLATE_BACKGROUND_FIELDS,
        ),
    ),
}

_LONG_FIELDS = frozenset(
    ("tiles", "searchbase_additions", "sections", "default_visible_sections", "items")
)
_JSON_FIELDS = frozenset(("section_titles", "payload_json"))
_CONTROL_FIELDS = frozenset(("output_mode",))


def allowed_fields(conf_name):
    """Return the union of fields supported by a configuration endpoint."""
    return frozenset(
        field
        for _pattern, fields in _STANZA_RULES.get(conf_name, ())
        for field in fields
    ) | _CONTROL_FIELDS


def fields_for_stanza(conf_name, stanza_name):
    """Resolve a stanza to its exact writable schema or reject it."""
    if not isinstance(stanza_name, str):
        raise ValueError("A valid configuration stanza name is required.")
    for pattern, fields in _STANZA_RULES.get(conf_name, ()):
        if pattern.fullmatch(stanza_name):
            return fields
    raise ValueError('Stanza "{}" is not writable through this endpoint.'.format(stanza_name))


def validate_topology_payload(payload):
    """Reject topology shapes that are too large to render safely for viewers."""
    topology = payload.get("topology")
    if not isinstance(topology, dict):
        raise ValueError('Field "payload_json" must contain a topology object.')
    sites = topology.get("sites")
    links = topology.get("links")
    if not isinstance(sites, list) or not isinstance(links, list):
        raise ValueError('Field "payload_json" topology must contain sites and links arrays.')
    if len(sites) > MAX_TOPOLOGY_SITES:
        raise ValueError(
            'Field "payload_json" topology exceeds its {}-site limit.'.format(
                MAX_TOPOLOGY_SITES
            )
        )
    if len(links) > MAX_TOPOLOGY_LINKS:
        raise ValueError(
            'Field "payload_json" topology exceeds its {}-link limit.'.format(
                MAX_TOPOLOGY_LINKS
            )
        )
    for site in sites:
        if not isinstance(site, dict):
            raise ValueError('Field "payload_json" topology sites must contain objects.')
        aliases = site.get("aliases")
        if aliases is not None and (
            not isinstance(aliases, list) or len(aliases) > MAX_TOPOLOGY_SITE_ALIASES
        ):
            raise ValueError(
                'Field "payload_json" topology sites exceed the {}-alias limit.'.format(
                    MAX_TOPOLOGY_SITE_ALIASES
                )
            )
    if not all(isinstance(link, dict) for link in links):
        raise ValueError('Field "payload_json" topology links must contain objects.')


def validate_shared_image_source(value):
    """Allow only bounded self-contained images or this app's static assets."""
    if value and not (
        _SHARED_IMAGE_DATA_URI.fullmatch(value)
        or _SHARED_APP_STATIC_IMAGE_PATH.fullmatch(value)
    ):
        raise ValueError(
            'Field "default_logo_src" must be an image data URI or this app\'s static image path.'
        )


def validate_template_background_data(value):
    """Allow bounded, verified raster data URIs for shared backgrounds."""
    match = _TEMPLATE_BACKGROUND_DATA_URI.fullmatch(value)
    if not match:
        raise ValueError(
            'Field "data" must be a base64-encoded PNG, JPEG, GIF, or WebP image.'
        )
    try:
        image_bytes = base64.b64decode(match.group(2), validate=True)
    except (TypeError, ValueError):
        raise ValueError('Field "data" must contain valid base64 image bytes.')
    media_type = match.group(1).lower()
    is_valid_image = (
        media_type == "png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    ) or (
        media_type == "jpeg" and image_bytes.startswith(b"\xff\xd8\xff")
    ) or (
        media_type == "gif"
        and (image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"))
    ) or (
        media_type == "webp"
        and image_bytes.startswith(b"RIFF")
        and image_bytes[8:12] == b"WEBP"
    )
    if not is_valid_image:
        raise ValueError('Field "data" does not match its declared image type.')


def validate_settings(conf_name, stanza_name, raw_settings):
    """Collapse form values and enforce field, size, and JSON boundaries."""
    permitted = fields_for_stanza(conf_name, stanza_name)
    settings = {}
    for key, raw in raw_settings.items():
        if key in _CONTROL_FIELDS:
            continue
        if key not in permitted:
            raise ValueError('Field "{}" is not valid for stanza "{}".'.format(key, stanza_name))
        value = raw[-1] if isinstance(raw, list) and raw else raw
        if value is None:
            value = ""
        if not isinstance(value, str):
            value = str(value)
        encoded_size = len(value.encode("utf-8"))
        limit = (
            MAX_TOPOLOGY_PAYLOAD_BYTES
            if key == "payload_json"
            else MAX_TEMPLATE_BACKGROUND_DATA_BYTES
            if conf_name == TEMPLATES_CONF and key == "data"
            else MAX_LOGO_BYTES
            if key == "default_logo_src"
            else MAX_LIST_BYTES
            if key in _LONG_FIELDS
            else MAX_SCALAR_BYTES
        )
        if encoded_size > limit:
            raise ValueError('Field "{}" exceeds its {}-byte limit.'.format(key, limit))
        if key == "default_logo_src":
            validate_shared_image_source(value)
        if conf_name == TEMPLATES_CONF and key == "data":
            validate_template_background_data(value)
        if key in _JSON_FIELDS and value:
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                raise ValueError('Field "{}" must contain valid JSON.'.format(key))
            if not isinstance(parsed, dict):
                raise ValueError('Field "{}" must contain a JSON object.'.format(key))
            if key == "payload_json":
                validate_topology_payload(parsed)
        settings[key] = value
    return settings


_ENDPOINTS = {
    "scd_insights_workspaces": WORKSPACE_CONF,
    "scd_customer_topology": TOPOLOGY_CONF,
    "scd_dashboard_backgrounds": TEMPLATES_CONF,
}


def _json_payload(raw):
    if not raw:
        return {}
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _form_payload(request):
    raw = request.get("payload", "")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return urllib.parse.parse_qs(raw, keep_blank_values=True)


def _route(request):
    rest_path = request.get("rest_path", "")
    for endpoint, conf_name in _ENDPOINTS.items():
        marker = "/{}".format(endpoint)
        marker_index = rest_path.find(marker)
        if marker_index < 0:
            continue
        suffix = rest_path[marker_index + len(marker) :].strip("/")
        stanza_name = urllib.parse.unquote(suffix) if suffix else None
        return endpoint, conf_name, stanza_name
    raise ValueError("Unknown shared configuration endpoint.")


def _response_payload(content):
    if not content:
        return {}
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    try:
        return json.loads(content)
    except (TypeError, ValueError):
        return {"message": str(content)[:1000]}


class WorkspaceMutationHandler(PersistentServerConnectionApplication):
    """Capability-gated proxy to app-local conf persistence.

    ``passSystemAuth`` supplies the system token only after splunkd has checked
    ``ssne_manage_insights_workspaces``. The handler validates the exact stanza
    and field surface, then uses that token for the generic conf write so a
    narrow custom role does not need the raw conf object's write ACL.
    """

    def __init__(self, _command_line, _command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def _proxy(
        self, request, conf_name, stanza_name, method, settings=None, query_args=None
    ):
        system_token = request.get("system_authtoken")
        if not system_token:
            return {"status": 500, "payload": {"error": "System authorization is unavailable."}}
        path = "/servicesNS/nobody/{}/configs/conf-{}".format(APP_NAME, conf_name)
        if stanza_name:
            path = "{}/{}".format(path, urllib.parse.quote(stanza_name, safe=""))
        get_args = {"output_mode": "json"}
        if query_args:
            get_args.update(query_args)
        # simpleRequest still raises ResourceNotFound for a 404 when only
        # raiseAllErrors is disabled. Preserve the actual response so clients
        # can distinguish a missing stanza and retry against the create route.
        response, content = rest.simpleRequest(
            path,
            sessionKey=system_token,
            method=method,
            postargs=settings,
            getargs=get_args,
            raiseAllErrors=False,
            rawResult=True,
        )
        return {
            "status": int(response.status),
            "payload": _response_payload(content),
        }

    def _ensure_template_background_quota(self, request, stanza_name, data):
        """Bound shared background count and bytes before a system-auth write."""
        existing = self._proxy(
            request,
            TEMPLATES_CONF,
            None,
            "GET",
            query_args={"count": "0"},
        )
        if existing["status"] < 200 or existing["status"] > 299:
            raise ValueError("Template background quota could not be checked.")
        entries = existing["payload"].get("entry", [])
        if not isinstance(entries, list):
            raise ValueError("Template background quota response is invalid.")
        entry_count = 0
        total_bytes = 0
        existing_data_bytes = None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name.startswith("background://"):
                continue
            entry_count += 1
            content = entry.get("content")
            value = content.get("data") if isinstance(content, dict) else ""
            value_bytes = len(value.encode("utf-8")) if isinstance(value, str) else 0
            total_bytes += value_bytes
            if name == stanza_name:
                existing_data_bytes = value_bytes
        if existing_data_bytes is None:
            entry_count += 1
            existing_data_bytes = 0
        projected_bytes = total_bytes - existing_data_bytes + len(data.encode("utf-8"))
        if entry_count > MAX_TEMPLATE_BACKGROUND_ENTRIES:
            raise ValueError(
                "Template backgrounds exceed their {}-entry limit.".format(
                    MAX_TEMPLATE_BACKGROUND_ENTRIES
                )
            )
        if projected_bytes > MAX_TEMPLATE_BACKGROUND_TOTAL_BYTES:
            raise ValueError(
                "Template backgrounds exceed their {}-byte total limit.".format(
                    MAX_TEMPLATE_BACKGROUND_TOTAL_BYTES
                )
            )

    def handle(self, in_string):
        try:
            request = _json_payload(in_string)
            _endpoint, conf_name, stanza_name = _route(request)
            method = str(request.get("method", "")).upper()
            if method == "GET":
                return self._proxy(request, conf_name, stanza_name, "GET")
            if method == "POST":
                is_create = stanza_name is None
                raw_settings = _form_payload(request)
                if stanza_name is None:
                    name_values = raw_settings.pop("name", [])
                    stanza_name = name_values[-1] if name_values else None
                settings = validate_settings(conf_name, stanza_name, raw_settings)
                if conf_name == TEMPLATES_CONF:
                    self._ensure_template_background_quota(
                        request, stanza_name, settings["data"]
                    )
                settings["updated_at"] = datetime.now(timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                )
                session = request.get("session", {})
                settings["updated_by"] = str(session.get("user") or "unknown")
                if "name" in settings:
                    settings.pop("name")
                if not is_create:
                    return self._proxy(
                        request, conf_name, stanza_name, "POST", settings
                    )
                create_settings = {"name": stanza_name}
                create_settings.update(settings)
                return self._proxy(
                    request, conf_name, None, "POST", create_settings
                )
            if method == "DELETE":
                fields_for_stanza(conf_name, stanza_name)
                return self._proxy(request, conf_name, stanza_name, "DELETE")
            return {"status": 405, "payload": {"error": "Method not allowed."}}
        except ValueError as error:
            return {"status": 400, "payload": {"error": str(error)}}
        except Exception:
            return {
                "status": 500,
                "payload": {"error": "Workspace configuration persistence failed."},
            }
