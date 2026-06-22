"""POST /services/itmip_llm/usage_log — write a usage telemetry event.

Body (JSON):
  tokens_in, tokens_out, cache_read, cost_usd : numeric
  model         : string (e.g. "claude-sonnet-4-6", "gpt-4o-mini")
  provider      : string (e.g. "anthropic", "openai")
  splunk_app    : string (URL-context Splunk app the user is in)
  org_short     : string (4-letter Org short name, default "DFLT")
  bu_short      : string (4-letter BU short name, default "DFLT")
  llm_name      : string (LLM config name)
  metrics_index : string (optional, default "_metrics")

Uses the system auth token (passSystemAuth=true) so any authenticated user
can write telemetry even without their own access to the metrics index.
"""

import json
import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_common import (  # noqa: E402
    DEFAULT_METRICS_INDEX,
    USAGE_SOURCE,
    USAGE_SOURCETYPE,
    err,
    ok,
    rate_limit_check,
    system_token,
    user_name,
    user_token,
)


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "POST").upper()
            if method != "POST":
                return err(405, "Only POST is supported on this endpoint.")

            if not user_token(args):
                return err(401, "Not authenticated.")

            user = user_name(args)
            # Cheap defensive cap: a malicious or buggy client can't
            # flood Tokens & Costs with fake events. 120/min is well
            # above any legitimate conversation cadence.
            if not rate_limit_check("usage_log", user, 120):
                return err(429, "Too many telemetry writes; slow down.")
            sys_token = system_token(args) or user_token(args)

            payload_raw = args.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw)
            except Exception:
                return err(400, "Invalid JSON payload.")

            tokens_in = int(payload.get("tokens_in") or 0)
            tokens_out = int(payload.get("tokens_out") or 0)
            cache_read = int(payload.get("cache_read") or 0)
            cost_usd = float(payload.get("cost_usd") or 0.0)
            model = str(payload.get("model") or "unknown")[:64]
            provider = str(payload.get("provider") or "unknown")[:32]
            splunk_app = str(payload.get("splunk_app") or "unknown")[:64]
            org_short = str(payload.get("org_short") or "DFLT")[:8]
            bu_short = str(payload.get("bu_short") or "DFLT")[:8]
            llm_name = str(payload.get("llm_name") or "default")[:64]
            metrics_index = str(payload.get("metrics_index") or DEFAULT_METRICS_INDEX)[:64]
            # v0.9.3 Concise Mode telemetry. Accepted values:
            # "default", "concise", "followup_concise", "verbose".
            # Unknown values are coerced to "default" so a buggy client
            # can't poison Tokens & Costs group-bys.
            raw_profile = str(payload.get("style_profile_used") or "default")[:24]
            if raw_profile not in ("default", "concise", "followup_concise", "verbose"):
                raw_profile = "default"
            style_profile_used = raw_profile

            # Plain event payload — numeric fields plus string dimensions.
            # INDEXED_EXTRACTIONS=json on the sourcetype (props.conf) auto-
            # extracts all keys at search time so the Tokens & Costs panel
            # can `stats sum(tokens_in) ... by ai_app` without any
            # metric-format gymnastics.
            event = {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cache_read": cache_read,
                "cost_usd": cost_usd,
                "ai_app": splunk_app,
                "ai_user": user,
                "ai_model": model,
                "ai_provider": provider,
                "ai_org": org_short,
                "ai_bu": bu_short,
                "ai_llm_name": llm_name,
                # v0.9.3 Concise Mode telemetry. Group-by dimension for the
                # forthcoming Tokens & Costs "Concise mode delta" panel.
                "ai_style_profile": style_profile_used,
            }
            event_body = json.dumps(event)

            url = (
                "/services/receivers/simple"
                "?index={index}&sourcetype={sourcetype}&source={source}&host=ai_assistant"
            ).format(
                index=metrics_index,
                sourcetype=USAGE_SOURCETYPE,
                source=USAGE_SOURCE,
            )

            # NOTE: splunk.rest.simpleRequest doesn't take a `body` kwarg.
            # For raw request bodies we use `jsonargs` (despite the name —
            # it just passes the bytes through unchanged when the content-
            # type is JSON, which is what receivers/simple wants).
            try:
                response, content = rest.simpleRequest(
                    url,
                    sessionKey=sys_token,
                    method="POST",
                    rawResult=True,
                    jsonargs=event_body,
                )
                status_code = getattr(response, "status", 0)
                if status_code not in (200, 201):
                    return err(
                        502,
                        "receivers/simple returned %s: %s"
                        % (status_code, (content or b"")[:200]),
                    )
            except Exception as exc:
                return err(502, "Could not write to %s: %s" % (metrics_index, exc))

            return ok({"ok": True, "index": metrics_index})
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
