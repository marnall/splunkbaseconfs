# Copyright 2026 Cisco, Inc.
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape as xml_escape

_EXAMPLE_HUB_TEMPLATE_MARKER = (
    'template="splunk-dashboard-studio:/templates/example-hub.html"'
)
_EXAMPLE_HUB_LOCALE = "en-US"
_JS_DEFINITION_REFERENCE_RE = re.compile(
    r"\bdefinition:(?P<var_name>[A-Za-z_$][A-Za-z0-9_$]*)\b"
)


class _JavaScriptLiteralParser:
    """Parse the limited JavaScript literal subset used by example-hub bundles."""

    _IDENTIFIER_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
    _NUMBER_RE = re.compile(
        r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|-?\.\d+(?:[eE][+-]?\d+)?"
    )

    def __init__(self, source: str, start_index: int = 0):
        """Create a parser for a JavaScript literal starting at ``start_index``."""
        self._source = source
        self._index = start_index
        self._length = len(source)

    def parse(self) -> Any:
        """Parse one literal value from the current index and return the result."""
        value = self._parse_value()
        self._skip_whitespace()
        return value

    def _parse_value(self) -> Any:
        """Parse the next JavaScript literal token at the current parser index."""
        self._skip_whitespace()
        if self._index >= self._length:
            raise ValueError("Unexpected end of JavaScript literal")

        if self._source.startswith("!0", self._index):
            self._index += 2
            return True
        if self._source.startswith("!1", self._index):
            self._index += 2
            return False
        if self._source.startswith("true", self._index):
            self._index += 4
            return True
        if self._source.startswith("false", self._index):
            self._index += 5
            return False
        if self._source.startswith("null", self._index):
            self._index += 4
            return None
        if self._source.startswith("undefined", self._index):
            self._index += 9
            return None
        if self._source.startswith("void 0", self._index):
            self._index += 6
            return None

        current = self._source[self._index]
        if current == "{":
            return self._parse_object()
        if current == "[":
            return self._parse_array()
        if current in {'"', "'", "`"}:
            return self._parse_string(current)
        if current == "-" or current.isdigit() or current == ".":
            return self._parse_number()

        raise ValueError(
            f"Unsupported JavaScript literal token {current!r} at index {self._index}"
        )

    def _parse_object(self) -> Dict[str, Any]:
        """Parse an object literal when the current token is ``{``."""
        obj: Dict[str, Any] = {}
        self._consume("{")
        self._skip_whitespace()
        if self._peek() == "}":
            self._consume("}")
            return obj

        while True:
            key = self._parse_object_key()
            self._skip_whitespace()
            self._consume(":")
            obj[key] = self._parse_value()
            self._skip_whitespace()
            current = self._peek()
            if current == ",":
                self._consume(",")
                self._skip_whitespace()
                if self._peek() == "}":
                    self._consume("}")
                    return obj
                continue
            if current == "}":
                self._consume("}")
                return obj
            raise ValueError(
                f"Unexpected object token {current!r} at index {self._index}"
            )

    def _parse_array(self) -> List[Any]:
        """Parse an array literal when the current token is ``[``."""
        arr: List[Any] = []
        self._consume("[")
        self._skip_whitespace()
        if self._peek() == "]":
            self._consume("]")
            return arr

        while True:
            arr.append(self._parse_value())
            self._skip_whitespace()
            current = self._peek()
            if current == ",":
                self._consume(",")
                self._skip_whitespace()
                if self._peek() == "]":
                    self._consume("]")
                    return arr
                continue
            if current == "]":
                self._consume("]")
                return arr
            raise ValueError(
                f"Unexpected array token {current!r} at index {self._index}"
            )

    def _parse_object_key(self) -> str:
        """Parse one object-key token from the current index."""
        self._skip_whitespace()
        current = self._peek()
        if current in {'"', "'", "`"}:
            return self._parse_string(current)
        identifier_match = self._IDENTIFIER_RE.match(self._source, self._index)
        if identifier_match is not None:
            self._index = identifier_match.end()
            return identifier_match.group(0)
        if current == "-" or current.isdigit():
            return str(self._parse_number())
        raise ValueError(f"Unsupported object key token {current!r} at {self._index}")

    def _parse_number(self) -> Any:
        """Parse an integer or float literal from the current index."""
        number_match = self._NUMBER_RE.match(self._source, self._index)
        if number_match is None:
            raise ValueError(f"Invalid number at index {self._index}")
        token = number_match.group(0)
        self._index = number_match.end()
        if any(char in token for char in ".eE"):
            return float(token)
        return int(token)

    def _parse_string(self, quote_char: str) -> str:
        """Parse a quoted string using ``quote_char`` as the active delimiter."""
        self._consume(quote_char)
        chars: List[str] = []
        while self._index < self._length:
            current = self._source[self._index]
            if current == quote_char:
                self._index += 1
                return "".join(chars)
            if quote_char == "`" and current == "$" and self._peek(1) == "{":
                raise ValueError("Template string interpolation is not supported")
            if current != "\\":
                chars.append(current)
                self._index += 1
                continue

            self._index += 1
            if self._index >= self._length:
                raise ValueError("Unexpected end of escape sequence")
            escape_char = self._source[self._index]

            if escape_char in {'"', "'", "`", "\\", "/"}:
                chars.append(escape_char)
                self._index += 1
            elif escape_char == "b":
                chars.append("\b")
                self._index += 1
            elif escape_char == "f":
                chars.append("\f")
                self._index += 1
            elif escape_char == "n":
                chars.append("\n")
                self._index += 1
            elif escape_char == "r":
                chars.append("\r")
                self._index += 1
            elif escape_char == "t":
                chars.append("\t")
                self._index += 1
            elif escape_char == "v":
                chars.append("\v")
                self._index += 1
            elif escape_char == "0":
                chars.append("\0")
                self._index += 1
            elif escape_char == "u":
                if self._peek(1) == "{":
                    closing_index = self._source.find("}", self._index + 2)
                    if closing_index == -1:
                        raise ValueError("Invalid unicode codepoint escape")
                    codepoint = self._source[self._index + 2 : closing_index]
                    chars.append(chr(int(codepoint, 16)))
                    self._index = closing_index + 1
                else:
                    hex_value = self._source[self._index + 1 : self._index + 5]
                    if len(hex_value) != 4:
                        raise ValueError("Invalid unicode escape")
                    chars.append(chr(int(hex_value, 16)))
                    self._index += 5
            elif escape_char == "x":
                hex_value = self._source[self._index + 1 : self._index + 3]
                if len(hex_value) != 2:
                    raise ValueError("Invalid hexadecimal escape")
                chars.append(chr(int(hex_value, 16)))
                self._index += 3
            elif escape_char in {"\n", "\r"}:
                self._index += 1
                if escape_char == "\r" and self._peek() == "\n":
                    self._index += 1
            else:
                chars.append(escape_char)
                self._index += 1
        raise ValueError("Unterminated string literal")

    def _skip_whitespace(self) -> None:
        """Advance the parser past any whitespace before the next token."""
        while self._index < self._length and self._source[self._index].isspace():
            self._index += 1

    def _peek(self, offset: int = 0) -> Optional[str]:
        """Return the character at ``offset`` from the current index, if any."""
        index = self._index + offset
        if index >= self._length:
            return None
        return self._source[index]

    def _consume(self, expected: str) -> None:
        """Consume ``expected`` from the current index or raise ``ValueError``."""
        if not self._source.startswith(expected, self._index):
            actual = self._source[self._index : self._index + len(expected)]
            raise ValueError(
                f"Expected {expected!r} at index {self._index}, found {actual!r}"
            )
        self._index += len(expected)


def read_service_json(service: Any, endpoint: str, **params: Any) -> Dict[str, Any]:
    """Fetch and decode JSON from a Splunk service endpoint.

    Call this with a Splunk ``service`` object, the relative REST ``endpoint``,
    and any extra query parameters to forward to ``service.get``.
    """
    response = service.get(endpoint, output_mode="json", **params)
    return json.loads(response.body.read())


def get_splunk_web_base_url(service: Any, *, splunkd_uri: str) -> str:
    """Return the Splunk Web base URL derived from ``server/settings``.

    Call this with the current Splunk ``service`` and the caller's
    ``splunkd_uri`` so the function can reuse the management host while
    selecting the correct web scheme and port.
    """
    payload = read_service_json(service, "server/settings")
    entries = payload.get("entry", [])
    if not entries:
        raise ValueError("Missing server/settings payload")

    content = entries[0].get("content", {})
    httpport = content.get("httpport")
    if httpport in (None, ""):
        raise ValueError("Missing server/settings httpport")

    parsed_splunkd_uri = urlparse(splunkd_uri)
    host = parsed_splunkd_uri.hostname or "127.0.0.1"
    enable_web_ssl = content.get("enableSplunkWebSSL")
    # Splunk may return enableSplunkWebSSL as a bool, number, or string. Treat `True`, `1`,
    # `"true"`, `"yes"`, and `"on"` as enabled; treat `False`, `0`, `""`,
    # `"false"`, and `None` as disabled.
    if isinstance(enable_web_ssl, bool):
        is_web_ssl_enabled = enable_web_ssl
    elif isinstance(enable_web_ssl, (int, float)):
        is_web_ssl_enabled = enable_web_ssl != 0
    elif isinstance(enable_web_ssl, str):
        is_web_ssl_enabled = enable_web_ssl.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    else:
        is_web_ssl_enabled = False

    scheme = "https" if is_web_ssl_enabled else "http"
    return f"{scheme}://{host}:{int(httpport)}"


def get_dashboard_studio_example_bundle_base_url(
    service: Any,
    *,
    splunkd_uri: str,
    cached_base_url: Optional[str] = None,
) -> str:
    """Build the base URL used to fetch Dashboard Studio example bundles.

    Call this with a Splunk ``service`` and ``splunkd_uri``. Pass
    ``cached_base_url`` when a previous call already resolved the value and you
    want to avoid extra REST requests.
    """
    if cached_base_url:
        return cached_base_url

    server_info = read_service_json(service, "server/info")
    server_entries = server_info.get("entry", [])
    if not server_entries:
        raise ValueError("Missing server/info payload")

    static_asset_id = server_entries[0].get("content", {}).get("staticAssetId")
    if not static_asset_id:
        raise ValueError("Missing server/info staticAssetId")

    dashboard_app = read_service_json(service, "apps/local/splunk-dashboard-studio")
    app_entries = dashboard_app.get("entry", [])
    if not app_entries:
        raise ValueError("Missing apps/local/splunk-dashboard-studio payload")

    app_build = app_entries[0].get("content", {}).get("build")
    if app_build in (None, ""):
        raise ValueError("Missing splunk-dashboard-studio build metadata")

    web_base_url = get_splunk_web_base_url(service, splunkd_uri=splunkd_uri)
    return (
        f"{web_base_url}/{_EXAMPLE_HUB_LOCALE}/static/"
        f"@{static_asset_id}.1:{app_build}"
        "/app/splunk-dashboard-studio/build/examples"
    )


def get_dashboard_studio_example_bundle_url(
    service: Any,
    dashboard_name: str,
    *,
    splunkd_uri: str,
    cached_base_url: Optional[str] = None,
) -> str:
    """Return the JavaScript bundle URL for one example dashboard.

    Call this with the example ``dashboard_name`` plus the same ``service`` and
    ``splunkd_uri`` used to resolve the bundle base URL. Optionally reuse a
    previously computed ``cached_base_url``.
    """
    base_url = get_dashboard_studio_example_bundle_base_url(
        service,
        splunkd_uri=splunkd_uri,
        cached_base_url=cached_base_url,
    )
    return f"{base_url}/{quote(dashboard_name, safe='')}.js"


def fetch_dashboard_studio_example_bundle(
    service: Any,
    dashboard_name: str,
    *,
    session_key: Optional[str],
    send_request_fn: Callable[..., Any],
    output_mode: Any,
    splunkd_uri: str,
    cached_bundle_base_url: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Download and decode an example dashboard bundle.

    Call this with the Splunk ``service``, the example ``dashboard_name``, and
    a ``send_request_fn`` compatible with Splunk's HTTP helper signature. The
    function returns the decoded bundle source and the bundle base URL that can
    be cached by the caller for later requests.
    """
    bundle_base_url = get_dashboard_studio_example_bundle_base_url(
        service,
        splunkd_uri=splunkd_uri,
        cached_base_url=cached_bundle_base_url,
    )
    bundle_url = get_dashboard_studio_example_bundle_url(
        service,
        dashboard_name,
        splunkd_uri=splunkd_uri,
        cached_base_url=bundle_base_url,
    )
    headers = {"Accept": "text/javascript"}
    if session_key:
        headers["Authorization"] = f"Splunk {session_key}"

    bundle_bytes = send_request_fn(
        url=bundle_url,
        method="get",
        headers=headers,
        output_mode=output_mode,
    )
    if not isinstance(bundle_bytes, (bytes, bytearray)):
        raise ValueError("Unexpected example bundle response type")
    return bundle_bytes.decode("utf-8"), bundle_base_url


def extract_dashboard_studio_definition_from_example_bundle(
    bundle_source: str,
) -> Dict[str, Any]:
    """Extract the dashboard definition object from bundle JavaScript source.

    Call this with the decoded bundle text returned by
    ``fetch_dashboard_studio_example_bundle``. It locates the definition
    variable, parses the literal object, and returns it as a Python dict.
    """
    reference_match = _JS_DEFINITION_REFERENCE_RE.search(bundle_source)
    variable_name = reference_match.group("var_name") if reference_match else "e"
    declaration_match = re.search(
        rf"\b(?:var|let|const)\s+{re.escape(variable_name)}\s*=",
        bundle_source,
    )
    if declaration_match is None:
        raise ValueError("Unable to locate dashboard definition variable")

    parser = _JavaScriptLiteralParser(bundle_source, declaration_match.end())
    definition = parser.parse()
    if not isinstance(definition, dict):
        raise ValueError("Dashboard definition bundle did not produce an object")
    return definition


def is_regular_dashboard_studio_definition(definition: Any) -> bool:
    """Return ``True`` when ``definition`` looks like a standard Studio dashboard.

    Call this before converting a parsed bundle into ``eai:data`` to skip
    non-dashboard example payloads such as wrapper or hub metadata.
    """
    return (
        isinstance(definition, dict)
        and isinstance(definition.get("visualizations"), dict)
        and isinstance(definition.get("dataSources"), dict)
    )


def build_dashboard_studio_eai_data(
    *,
    title: str,
    description: str,
    definition: Dict[str, Any],
) -> str:
    """Serialize a Studio definition into the XML stored in ``content['eai:data']``.

    Call this with normalized dashboard ``title`` and ``description`` strings
    plus the parsed Studio ``definition`` dict. The returned XML is ready to be
    assigned to the entry's ``eai:data`` field.
    """
    normalized_title = title if isinstance(title, str) else ""
    normalized_description = description if isinstance(description, str) else ""
    definition_json = json.dumps(definition, indent=4, ensure_ascii=False)
    cdata_safe_json = definition_json.replace("]]>", "]]]]><![CDATA[>")
    return "\n".join(
        [
            '<dashboard version="2">',
            f"    <label>{xml_escape(normalized_title)}</label>",
            f"    <description>{xml_escape(normalized_description)}</description>",
            "    <definition><![CDATA[",
            cdata_safe_json,
            "    ]]></definition>",
            "</dashboard>",
        ]
    )


def is_dashboard_studio_example_wrapper(entry: Dict[str, Any]) -> bool:
    """Identify example-hub wrapper entries that need bundle enrichment.

    Call this with a dashboard REST ``entry`` dict. It returns ``True`` only
    when the entry belongs to ``splunk-dashboard-studio`` and its ``eai:data``
    points at the example-hub HTML template instead of an embedded definition.
    """
    content = entry.get("content")
    acl = entry.get("acl")
    if not isinstance(content, dict) or not isinstance(acl, dict):
        return False
    eai_data = content.get("eai:data")
    return (
        acl.get("app") == "splunk-dashboard-studio"
        and isinstance(eai_data, str)
        and _EXAMPLE_HUB_TEMPLATE_MARKER in eai_data
    )


def _normalize_dashboard_studio_text_fields(
    content: Dict[str, Any], definition: Dict[str, Any]
) -> Tuple[str, str]:
    """Choose the title and description that should be written back to the entry.

    Call this with the original entry ``content`` and the parsed dashboard
    ``definition``. Definition values win when present; otherwise the function
    falls back to the existing entry metadata.
    """
    title = definition.get("title")
    description = definition.get("description")
    normalized_title = (
        title if isinstance(title, str) and title else content.get("label", "")
    )
    if not isinstance(normalized_title, str):
        normalized_title = ""
    normalized_description = (
        description if isinstance(description, str) else content.get("description", "")
    )
    if not isinstance(normalized_description, str):
        normalized_description = ""
    return normalized_title, normalized_description


def enrich_dashboard_studio_example_entry(
    entry: Dict[str, Any],
    *,
    service: Any,
    logger: Optional[logging.Logger],
    session_key: Optional[str],
    send_request_fn: Callable[..., Any],
    output_mode: Any,
    splunkd_uri: str,
    cached_bundle_base_url: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Replace an example-hub wrapper entry with a normal Studio dashboard entry.

    Call this for a single dashboard REST ``entry`` together with the Splunk
    request helpers needed to fetch example bundles. It returns a copied and
    possibly enriched entry plus the bundle base URL cache value to reuse on the
    next call.
    """
    entry_copy = dict(entry)
    content = entry_copy.get("content")
    if not isinstance(content, dict):
        return entry_copy, cached_bundle_base_url

    entry_copy["content"] = dict(content)
    if not is_dashboard_studio_example_wrapper(entry_copy):
        return entry_copy, cached_bundle_base_url

    dashboard_name = entry_copy.get("name", "")
    if not isinstance(dashboard_name, str) or not dashboard_name:
        return entry_copy, cached_bundle_base_url

    bundle_source, cached_bundle_base_url = fetch_dashboard_studio_example_bundle(
        service,
        dashboard_name,
        session_key=session_key,
        send_request_fn=send_request_fn,
        output_mode=output_mode,
        splunkd_uri=splunkd_uri,
        cached_bundle_base_url=cached_bundle_base_url,
    )
    definition = extract_dashboard_studio_definition_from_example_bundle(bundle_source)
    if not is_regular_dashboard_studio_definition(definition):
        if logger is not None:
            logger.warning(
                "Skipping dashboard example enrichment for %s: bundle is not a regular Studio dashboard",
                dashboard_name,
            )
        return entry_copy, cached_bundle_base_url

    normalized_title, normalized_description = _normalize_dashboard_studio_text_fields(
        content,
        definition,
    )
    entry_copy["content"]["eai:data"] = build_dashboard_studio_eai_data(
        title=normalized_title,
        description=normalized_description,
        definition=definition,
    )
    entry_copy["content"]["label"] = normalized_title
    entry_copy["content"]["description"] = normalized_description
    entry_copy["content"]["rootNode"] = "dashboard"
    entry_copy["content"]["dashboardType"] = 1
    if logger is not None:
        logger.info("Enriched dashboard example-hub bundle for %s", dashboard_name)
    return entry_copy, cached_bundle_base_url


def enrich_dashboard_entries(
    entries: List[Dict[str, Any]],
    *,
    service: Any,
    logger: Optional[logging.Logger],
    session_key: Optional[str],
    send_request_fn: Callable[..., Any],
    output_mode: Any,
    splunkd_uri: str,
    cached_bundle_base_url: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Enrich every dashboard entry that references a Studio example bundle.

    Call this with the list of REST ``entries`` returned by Splunk plus the same
    request context accepted by ``enrich_dashboard_studio_example_entry``. The
    function preserves non-example entries, logs per-entry failures, and returns
    the processed list together with an updated bundle base URL cache.
    """
    enriched_entries: List[Dict[str, Any]] = []
    for entry in entries:
        try:
            enriched_entry, cached_bundle_base_url = (
                enrich_dashboard_studio_example_entry(
                    entry,
                    service=service,
                    logger=logger,
                    session_key=session_key,
                    send_request_fn=send_request_fn,
                    output_mode=output_mode,
                    splunkd_uri=splunkd_uri,
                    cached_bundle_base_url=cached_bundle_base_url,
                )
            )
            enriched_entries.append(enriched_entry)
        except Exception as exc:
            if logger is not None:
                logger.warning(
                    "Failed to enrich dashboard example entry %s: %s",
                    entry.get("name", ""),
                    exc,
                )
            enriched_entries.append(entry)
    return enriched_entries, cached_bundle_base_url
