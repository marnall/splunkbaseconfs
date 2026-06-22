"""POST /services/itmip_llm/validate_conf

Validate a props.conf / transforms.conf stanza body against Splunk's OWN
authoritative `.conf.spec` (bin/itmip_conf_spec_lib.py) — server-side because the
spec files are on disk, not in REST. Catches **unknown / hallucinated attribute
names** (the failure mode that makes a whole stanza a silent no-op), basic
value-type mismatches, and (for transforms) regexes that don't compile. Does NOT
persist anything; pairs with `splunk_generate_conf_package`.

POST body:
  { conf: "props" | "transforms", stanza_name?: "..", stanza_body: "key=value\\n..." }

Returns:
  { ok, conf, spec_available, splunk_version,
    errors:   [ {attribute, kind, message} ],
    warnings: [ {attribute, kind, message} ],
    recognized_attributes: [..], unknown_attributes: [..] }

`ok` is true when there are no errors (warnings don't fail it). When the spec
isn't readable (Splunk Cloud / no $SPLUNK_HOME) it degrades gracefully:
spec_available=false, attribute names not checked, ok=true with one warning.

Gated on the `data_onboarding` capability (Professional+). Read-only.
"""

from __future__ import annotations

import json
import os
import re
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(APP_DIR, "lib"), os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_common import err, ok, system_token, user_token  # noqa: E402
from itmip_llm_license import capability_enabled  # noqa: E402
import itmip_conf_spec_lib as speclib  # noqa: E402

_VALID_CONFS = ("props", "transforms")
_ATTR_LINE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.<>\-]*?)\s*=\s*(.*)$")
_BOOL_VALUES = {"true", "false", "0", "1", "yes", "no", "t", "f"}


def _splunk_version(sys_token):
    try:
        resp, content = rest.simpleRequest(
            "/services/server/info?output_mode=json",
            sessionKey=sys_token, method="GET")
        if getattr(resp, "status", 0) == 200 and content:
            return (json.loads(content).get("entry", [{}])[0]
                    .get("content", {}).get("version"))
    except Exception:
        pass
    return None


def _parse_stanza_body(body):
    """Return [(attr, value)] from a stanza body, joining `\\`-continued lines."""
    out = []
    pending = ""
    for raw in (body or "").splitlines():
        line = raw.rstrip("\n")
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("[") and s.endswith("]"):
            # Caller pasted a stanza header in the body — ignore it.
            continue
        joined = (pending + " " + s).strip() if pending else s
        if joined.endswith("\\"):
            pending = joined[:-1]
            continue
        pending = ""
        m = _ATTR_LINE.match(joined)
        if m:
            out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def _value_type_issue(syntax, value):
    """Cheap value sanity for the few unambiguous spec types. Returns a message
    or None. Conservative — only flags clear mismatches."""
    syn = (syntax or "").lower()
    v = (value or "").strip()
    if not v:
        return None
    if "<boolean>" in syn:
        if v.lower() not in _BOOL_VALUES:
            return "expects a boolean (true/false), got %r" % value
    elif "<non-negative integer>" in syn:
        if not v.isdigit():
            return "expects a non-negative integer, got %r" % value
    elif "<integer>" in syn:
        if not re.match(r"^-?\d+$", v):
            return "expects an integer, got %r" % value
    return None


def _validate(conf, stanza_body):
    spec = speclib.load_spec(conf)
    errors, warnings, recognized, unknown = [], [], [], []
    pairs = _parse_stanza_body(stanza_body)

    if not spec:
        warnings.append({
            "attribute": "", "kind": "spec_unavailable",
            "message": "%s.conf.spec is not readable on this instance "
                       "(Splunk Cloud / no $SPLUNK_HOME) — attribute names were "
                       "NOT validated. Found %d attribute(s)." % (conf, len(pairs)),
        })
        return {"ok": True, "spec_available": False, "errors": errors,
                "warnings": warnings,
                "recognized_attributes": [a for a, _ in pairs],
                "unknown_attributes": []}

    seen = {}
    for attr, value in pairs:
        if attr in seen:
            warnings.append({"attribute": attr, "kind": "duplicate",
                             "message": "attribute set more than once in this stanza."})
        seen[attr] = value
        form = speclib.recognise(spec, attr)
        if form is None:
            unknown.append(attr)
            errors.append({
                "attribute": attr, "kind": "unknown_attribute",
                "message": "not a recognised %s.conf attribute — Splunk will "
                           "ignore it (check spelling/case)." % conf,
            })
            continue
        recognized.append(attr)
        # value-type sanity (only on exact-named attrs where we know the syntax)
        if form == "exact":
            issue = _value_type_issue(spec["attrs"].get(attr, {}).get("syntax"), value)
            if issue:
                warnings.append({"attribute": attr, "kind": "value_type",
                                 "message": issue})

    # transforms-specific: regex compile + completeness
    if conf == "transforms":
        if "REGEX" in seen:
            rx = seen["REGEX"]
            try:
                re.compile(rx)
            except re.error as rexc:
                # Python re != PCRE exactly; flag as a warning, not a hard error.
                warnings.append({
                    "attribute": "REGEX", "kind": "regex_compile",
                    "message": "regex did not compile in a Python check (%s) — "
                               "verify it; some valid PCRE differs from Python re." % rexc,
                })
            if ("FORMAT" not in seen and "DEST_KEY" not in seen
                    and "WRITE_META" not in seen):
                warnings.append({
                    "attribute": "REGEX", "kind": "incomplete_transform",
                    "message": "REGEX without FORMAT or DEST_KEY — the extraction/"
                               "rewrite has no destination.",
                })

    # props-specific: one high-value consistency warning
    if conf == "props":
        if "LINE_BREAKER" in seen and seen.get("SHOULD_LINEMERGE", "").lower() in ("", "true", "1"):
            warnings.append({
                "attribute": "SHOULD_LINEMERGE", "kind": "consistency",
                "message": "you set a custom LINE_BREAKER but SHOULD_LINEMERGE is "
                           "true/unset — set SHOULD_LINEMERGE=false so your "
                           "LINE_BREAKER actually controls event boundaries.",
            })

    return {"ok": len(errors) == 0, "spec_available": True, "errors": errors,
            "warnings": warnings, "recognized_attributes": recognized,
            "unknown_attributes": unknown}


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            if (args.get("method") or "POST").upper() != "POST":
                return err(405, "Only POST is supported.")
            if not user_token(args):
                return err(401, "Not authenticated.")
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")
            if not capability_enabled(sys_token, "data_onboarding"):
                return err(403, "Config validation requires a Professional or "
                                "higher license.")
            try:
                payload = json.loads(args.get("payload") or "{}")
            except Exception:
                return err(400, "Invalid JSON payload.")

            conf = str(payload.get("conf") or "").strip().lower()
            if conf not in _VALID_CONFS:
                return err(400, "conf must be one of %s." % ", ".join(_VALID_CONFS))
            body = payload.get("stanza_body")
            if not isinstance(body, str) or not body.strip():
                return err(400, "stanza_body (string) is required.")
            if len(body) > 64 * 1024:
                return err(400, "stanza_body too large (64KB max).")

            result = _validate(conf, body)
            result["conf"] = conf
            result["stanza_name"] = str(payload.get("stanza_name") or "")
            result["splunk_version"] = _splunk_version(sys_token)
            return ok(result)
        except Exception as exc:
            sys.stderr.write("itmip_llm_validate_conf error: %s\n" % exc)
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_a, **_k):
        raise NotImplementedError()

    def done(self):
        pass
