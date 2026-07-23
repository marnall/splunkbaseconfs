# Copyright (c) 2026 Joshua Specht. All rights reserved.
"""TA Studio — splunkd REST handler (PersistentServerConnectionApplication).

Registered in restmap.conf at match=/ta_studio. Exposes the full project/
input/alert/build API at:

    /servicesNS/{user}/ta_studio/ta_studio/{path}

so tooling (curl, Splunk SDK, other apps) can interact without a splunkweb
session. tas_lib.router.dispatch() handles all routing.

Runs under splunkd's Python 3.9.

Write methods (POST/PUT/DELETE) require the `edit_ta_studio` capability,
enforced by restmap.conf (capability.post / .put / .delete stanzas). Reads
are open to any authenticated Splunk user.

File responses (icons, package downloads) are base64-encoded as
{data_b64, filename, mime} JSON. The frontend decodes them into Blob URLs for
display/download without a separate file-serving endpoint.
"""
from __future__ import annotations

import json
import os
import platform as _platform
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── sys.path ──────────────────────────────────────────────────────────────────
# splunkd prepends the app's bin/ to sys.path for scripts listed in restmap.conf
# so tas_lib.* should resolve automatically. Add vendor/ explicitly for future
# third-party deps installed with `splunk cmd python -m pip install --target vendor`.
_script_dir = Path(os.path.abspath(__file__)).parent  # .../bin/
_vendor_dir = _script_dir / "tas_lib" / "vendor"
for _p in (_script_dir, _vendor_dir):
    s = str(_p)
    if _p.is_dir() and s not in sys.path:
        sys.path.insert(0, s)

import splunk.rest as splunk_rest  # noqa: E402
from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402

from tas_lib.db.kvstore import KVStoreClient  # noqa: E402
from tas_lib.logging_setup import (  # noqa: E402
    configure as _configure_logging,
    get_logger,
    parse_log_fields,
)
from tas_lib.router import dispatch  # noqa: E402

# Shared logging setup: attaches the rotating file handler to the parent
# `splunk.ta_studio` logger so the PSCA, the router, and every service child
# logger all land in var/log/splunk/ta_studio.log (index=_internal). See
# tas_lib/logging_setup.py for why the handler must sit on the parent.
_configure_logging()
logger = get_logger("rest")
# NOTE: do NOT log at module import. splunkd spawns/recycles multiple PSCA
# worker processes and re-imports this module in each, so a module-level log
# line floods ta_studio.log with duplicate "handler loaded" entries (one per
# worker, many per minute). The per-request access log in router.dispatch is
# the real proof-of-life signal; the file is populated as soon as any write
# (or any request at DEBUG level) happens.


def _splunk_version(session_key: str) -> Optional[str]:
    try:
        _, content = splunk_rest.simpleRequest(
            "/services/server/info?output_mode=json",
            sessionKey=session_key,
            method="GET",
        )
        entries = json.loads(content).get("entry") or []
        return entries[0].get("content", {}).get("version") if entries else None
    except Exception:
        return None


def _fetch_logs(session_key: str, count: int, folder: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    try:
        # Folder name passes through a strict alnum/underscore allowlist before
        # interpolating into SPL — same defence as the splunkweb controller.
        # Per-project Logs page passes the built add-on's folder name; its
        # runtime logs land in var/log/splunk/<folder>_*.log, so search that
        # term. With no folder, show TA Studio's own builder logs (ta_studio.log).
        # Allowlist guards against SPL injection via the folder param. Hyphens are
        # permitted now that folder names allow them (TA-cisco_ios, SA-*, …) —
        # WITHOUT this the old `.isalnum()` check rejected hyphenated folders and
        # silently fell back to ta_studio's own logs. The term is also quoted so
        # SPL treats a hyphenated folder as one literal phrase, never an operator.
        safe = bool(folder) and all(c.isalnum() or c in "_-" for c in folder)
        term = folder if safe else "ta_studio"
        search = 'search index=_internal "%s" | head %d | reverse' % (term, count)
        _, raw = splunk_rest.simpleRequest(
            "/services/search/jobs/export?output_mode=json",
            sessionKey=session_key,
            method="POST",
            postargs={"search": search, "earliest_time": "-24h"},
        )
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        events = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "result" in ev:
                result = ev["result"]
                # Parse the raw line into structured fields server-side so the
                # Logs page renders columns without a brittle client-side regex
                # (and so it works the same for our handler format and solnlib's).
                result.update(parse_log_fields(result.get("_raw", "")))
                events.append(result)
        return 200, {"count": len(events), "events": events}
    except Exception as exc:
        return 422, {"detail": "log search failed: %s" % exc}


class TAStudioApp(PersistentServerConnectionApplication):

    def __init__(self, command_line: str, command_arg: str) -> None:
        super().__init__()

    def handle(self, in_string: str) -> str:
        """Entry point called by splunkd for every REST request.

        Response contract: this handler ALWAYS hands splunkd HTTP 200. The real
        application status (200/201/400/404/422/...) is carried inside the body
        as `{"__status": N, "body": <payload>}`. This is deliberate — splunkweb's
        proxy rewrites the body of any non-2xx response into its own HTML/XML
        error page, which would strip the router's `detail`/`errors` and leave
        the SPA showing a generic "API unreachable" message with no actionable
        detail. Keeping HTTP at 200 makes the proxy pass the body through
        untouched so the client (`api/client.ts`) can read `__status` and surface
        the true error. Genuine non-2xx the SPA may still see (401/403 auth, a
        splunkweb proxy crash, an unregistered endpoint) all originate BEFORE
        this handler runs, so the client still treats a real non-2xx as an
        infrastructure failure.

        Bulletproofing: any uncaught exception below this point makes splunkd
        serve its own HTML 500 error page (the `appserver/mrsparkle/lib/error.py`
        template), which the SPA can't parse. The outer try/except in this method
        is therefore a load-bearing safety net, not a nicety. Even `json.dumps`
        of the response is inside it so a payload with unserializable contents
        falls back to a logged 422 (inside a 200 envelope) instead of crashing
        splunkd.
        """
        # Initialise BEFORE the try so the response builder can't NameError if
        # something exotic (BaseException, hard interpreter error) escapes.
        status: int = 422
        payload: Any = {"detail": "ta_studio REST: response uninitialised"}
        try:
            try:
                request = json.loads(in_string)
                status, payload = self._route(request)
            except PermissionError as exc:
                # Filesystem EACCES on a workspace file — almost always means the
                # splunkd service account can't write into the workspace dir.
                # Surface the path + a platform-appropriate remediation. 422 maps
                # to the client's "permission/path access" message; the always-200
                # envelope (see handle's docstring) keeps this detail intact.
                logger.exception("ta_studio REST: workspace write blocked by OS permission")
                target = getattr(exc, "filename", None) or str(exc)
                if _platform.system() == "Windows":
                    remediation = (
                        "The Splunk service account (NT SERVICE\\Splunkd) lacks "
                        "write permission on the workspace directory. Grant modify "
                        "access, e.g.: icacls \"<workspace_dir>\" /grant "
                        "\"NT SERVICE\\Splunkd:(OI)(CI)M\" /T"
                    )
                else:
                    remediation = (
                        "The Splunk service account (typically 'splunk') lacks "
                        "write permission on the workspace directory. Grant access, "
                        "e.g.: chown -R splunk:splunk <workspace_dir> "
                        "&& chmod -R u+w <workspace_dir>"
                    )
                status, payload = 422, {
                    "detail": "Cannot write to workspace file '%s'. %s" % (target, remediation),
                    "code": "workspace_not_writable",
                    "path": target,
                }
            except Exception as exc:
                logger.exception("ta_studio REST: unhandled error in route")
                status, payload = 422, {"detail": "server error: %s" % exc}

            # Build the response body. CRITICAL: the HTTP status handed back to
            # splunkd is ALWAYS 200 — the real application status rides INSIDE
            # the body under `__status`. splunkweb's proxy replaces the body of
            # ANY non-2xx response with its own HTML/XML error page, which strips
            # the router's `detail`/`errors` and leaves the SPA showing a useless
            # "API unreachable" fallback (the bug that hid globalConfig schema
            # errors behind "restart Splunk"). Returning 200 keeps the proxy's
            # hands off the body so every error detail reaches the client intact.
            # `api/client.ts` reads `__status` to decide success vs failure; the
            # `X-TAStudio-Status` header echoes it so Splunk's own access logs can
            # still distinguish real outcomes. json.dumps can still fail here for
            # bizarre payloads (e.g. a circular reference that slipped past
            # default=str), so guard it too.
            try:
                inner = json.dumps(
                    {"__status": status, "body": None if status == 204 else payload},
                    default=str,
                )
            except Exception as exc:
                logger.exception("ta_studio REST: failed to serialize payload")
                status = 422
                inner = json.dumps({
                    "__status": 422,
                    "body": {"detail": "server error: response serialization failed: %s" % exc},
                })

            # Include Content-Type so splunkweb's proxy.py doesn't delete the
            # header and cause htmlinjectiontoolfactory to crash with KeyError.
            return json.dumps({
                "status": 200,
                "payload": inner,
                "headers": {
                    "Content-Type": "application/json; charset=utf-8",
                    "X-TAStudio-Status": str(status),
                },
            })
        except BaseException as exc:  # noqa: BLE001 — last-resort safety net
            # If we end up here, something exotic happened (SystemExit, etc.).
            # Splunkd needs a string back; anything else crashes the PSCA and
            # the user sees splunkd's HTML 500. Return a hardcoded 422 envelope.
            try:
                logger.exception("ta_studio REST: BaseException in handle()")
            except Exception:
                pass
            return ('{"status": 200, "payload": '
                    '"{\\"__status\\": 422, \\"body\\": {\\"detail\\": '
                    '\\"ta_studio REST: fatal handler error: %s\\"}}", '
                    '"headers": {"Content-Type": "application/json; charset=utf-8", '
                    '"X-TAStudio-Status": "422"}}') % (
                str(exc).replace("\\", "\\\\").replace('"', '\\"')
            )

    def _route(self, request: Dict[str, Any]) -> Tuple[int, Any]:
        method: str = (request.get("method") or "GET").upper()

        # path_info is the URL path AFTER the restmap.conf `match` prefix.
        # Splunk 9.x uses `path_info`; some older builds expose `rest_path`.
        path_info: str = (
            request.get("path_info")
            or request.get("rest_path")
            or "/"
        )

        session: Dict[str, Any] = request.get("session") or {}
        session_key: str = session.get("authtoken") or ""
        # splunkd hands persistent handlers a durable system token alongside the
        # per-request user session. Background jobs (build / cloud AppInspect)
        # use it so their heartbeat/result KV writes outlive a long run even if
        # the user's session token would expire meanwhile. Fall back to the user
        # token if splunkd didn't supply one.
        system_authtoken: str = request.get("system_authtoken") or session_key

        # Path segments the router expects: ["projects", "abc123", "inputs"]
        # splunkweb's proxy.py re-encodes the URI with urllib.parse.quote()
        # before forwarding to splunkd, turning a client-side %3A into %253A.
        # splunkd decodes once (%25→%), leaving %3A in path_info. Decode here
        # so names with colons/spaces/etc. round-trip correctly.
        segs: List[str] = [urllib.parse.unquote(s) for s in path_info.strip("/").split("/") if s]

        # Query string → dict of params.
        # Splunk 10.2.2+ delivers query as a list of [key, value] pairs;
        # older builds deliver a URL-encoded string.
        raw_query = request.get("query")
        if isinstance(raw_query, list):
            params: Dict[str, Any] = {}
            for item in raw_query:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    params[str(item[0])] = str(item[1])
                elif isinstance(item, str):
                    k, _, v = item.partition("=")
                    params[k] = v
        else:
            params = dict(urllib.parse.parse_qsl(raw_query or ""))

        # Request body — PSCA may deliver payload as a pre-parsed dict or string
        raw = request.get("payload") or ""
        if isinstance(raw, dict):
            body: Dict[str, Any] = raw
        else:
            try:
                body = json.loads(raw) if raw else {}
            except (json.JSONDecodeError, ValueError):
                body = {}

        kv_client = KVStoreClient(session_key=session_key)

        # Capability enforcement for write methods is handled by restmap.conf
        # (capability.post / .put / .delete = edit_ta_studio). Pass None to
        # skip the router's duplicate check for those methods. GET is open to
        # any authenticated user — router already skips the check for reads.
        status, payload = dispatch(
            method=method,
            path_segments=segs,
            params=params,
            body=body,
            splunk_version_provider=lambda: _splunk_version(session_key),
            log_fetcher=lambda n, folder=None: _fetch_logs(session_key, n, folder),
            kv_client=kv_client,
            user_capabilities=None,
            system_authtoken=system_authtoken,
        )

        if isinstance(payload, dict) and "_file" in payload:
            import base64 as _b64
            file_path = payload["_file"]
            mime = payload.get("_mime", "application/octet-stream")
            filename = payload.get("_download", Path(file_path).name)
            try:
                with open(file_path, "rb") as fh:
                    data = fh.read()
                return 200, {
                    "data_b64": _b64.b64encode(data).decode("ascii"),
                    "filename": filename,
                    "mime": mime,
                }
            except OSError as exc:
                return 422, {"detail": "cannot read file: %s" % exc}

        return status, payload
