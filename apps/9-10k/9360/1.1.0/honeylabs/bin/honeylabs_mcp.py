"""Minimal client for the HoneyLabs MCP endpoint.

The REST API answers questions about a single IP address. Everything else the
platform knows, raw events, captured request payloads, who is probing a CVE,
what a hosting provider looks like, which addresses share a TLS fingerprint,
is reachable only as an MCP tool. This module is the thin layer that lets a
Splunk search command call those tools, so the add-on stops being an IP
enricher bolted to two threat feeds.

Three things about the protocol make this small:

* No handshake. The endpoint accepts a bare `tools/call` POST. There is no
  `initialize` exchange and no session id to carry, so a search command that
  runs for one chunk and exits does not have to manage a session it will
  immediately throw away.
* One frame. The reply is `text/event-stream`, but a tool call answers with a
  single `data:` line rather than a stream, so this reads frames until it has
  the response for its request id.
* Structured results. Every tool returns `structuredContent`, either an object
  for the single-subject tools or `{"result": [...]}` for the list tools. That
  is already the shape Splunk wants, so nothing has to parse prose.

A key is required. `tools/list` is open but `tools/call` is not, which is a
deliberate choice on the server and not something to work around here: the
error path says where to get a key rather than failing quietly.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import ssl

try:                                     # py3
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:                      # pragma: no cover - py2 fallback
    from urllib2 import Request, urlopen, HTTPError, URLError

from honeylabs_common import TIMEOUT, USER_AGENT

MCP_URL = os.environ.get("HONEYLABS_MCP_URL", "https://mcp.honeylabs.net/mcp")

NO_KEY = (
    "This command needs a HoneyLabs API key. The key is free and takes about a "
    "minute: create one at https://honeylabs.net/dashboard, then store it on "
    "the HoneyLabs setup page in this app. The `| honeylabs` enrichment "
    "command still works without one."
)


class McpError(RuntimeError):
    """A tool call that did not produce a result, with a reason worth showing."""


def call_tool(name, arguments, api_key):
    """Call one MCP tool. Returns a list of dicts, one per row.

    Single-subject tools (an IP, an ASN, a fingerprint) answer with one object,
    which comes back as a one-element list. That keeps the caller from having
    to branch: every mode yields rows, and a mode that describes one thing
    yields one row.
    """
    if not api_key:
        raise McpError(NO_KEY)

    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }).encode("utf-8")

    request = Request(MCP_URL, data=payload, headers={
        "Content-Type": "application/json",
        # Both types, because the endpoint chooses the streaming form and a
        # client that only offers application/json is refused before it runs.
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer " + api_key,
        "User-Agent": USER_AGENT,
    })

    try:
        response = urlopen(request, timeout=TIMEOUT, context=ssl.create_default_context())
    except HTTPError as exc:
        raise McpError(_http_reason(exc))
    except URLError as exc:
        raise McpError("cannot reach %s (%s)" % (MCP_URL, exc.reason))

    envelope = None
    with response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            # Frames are `event: message` then `data: {...}`. Only the data
            # line carries anything, and blank lines separate frames.
            if not line.startswith("data:"):
                continue
            chunk = line.split(":", 1)[1].strip()
            if not chunk:
                continue
            try:
                candidate = json.loads(chunk)
            except ValueError:
                continue
            if isinstance(candidate, dict) and candidate.get("id") == 1:
                envelope = candidate
                break

    if envelope is None:
        raise McpError("no response frame from %s" % MCP_URL)
    if "error" in envelope:
        raise McpError(str(envelope["error"].get("message") or envelope["error"])[:200])

    result = envelope.get("result") or {}

    # A tool that rejects its arguments answers 200 with isError set and the
    # complaint in the text content. Surfacing that verbatim is far more use
    # than "the call failed": it names the argument that was wrong.
    if result.get("isError"):
        raise McpError(_first_text(result) or "the tool reported an error")

    structured = result.get("structuredContent")
    if structured is None:
        text = _first_text(result)
        if not text:
            return []
        try:
            structured = json.loads(text)
        except ValueError:
            return [{"result": text}]

    return _rows(structured)


def _rows(structured):
    if isinstance(structured, dict):
        inner = structured.get("result")
        if isinstance(inner, list):
            return [r if isinstance(r, dict) else {"result": r} for r in inner]
        return [structured]
    if isinstance(structured, list):
        return [r if isinstance(r, dict) else {"result": r} for r in structured]
    return [{"result": structured}]


def _first_text(result):
    for item in result.get("content") or []:
        if item.get("type") == "text" and item.get("text"):
            return item["text"][:400]
    return ""


def _http_reason(exc):
    """Turn an HTTP failure into something an analyst can act on."""
    detail = ""
    try:
        body = json.loads(exc.read().decode("utf-8", "replace"))
        detail = body.get("detail") or body.get("error") or ""
    except Exception:                      # noqa: BLE001
        pass
    if exc.code in (401, 403):
        return ("HoneyLabs rejected the stored API key (HTTP %s). %s"
                % (exc.code, detail or "Check it on the HoneyLabs setup page."))
    if exc.code == 429:
        return ("HoneyLabs daily quota reached (HTTP 429). %s"
                % (detail or "The budget resets at midnight UTC."))
    return "HTTP %s from the HoneyLabs MCP endpoint. %s" % (exc.code, detail)
