"""POST /services/itmip_llm/mltk_share — privileged ACL elevation for
AI-Assistent-created MLTK models.

When an end-user runs an AI-Toolkit template, `fit ... into <name>`
writes a lookup-table-file (`__mlspl_<name>.csv` / `.mlmodel` / `.onnx`)
into the **calling app's** lookups directory at the calling user's
privilege level. The user doesn't need any special role for that.

The next step — flipping the lookup's ACL to `owner=nobody,
sharing=global` so dashboards in OTHER apps can `apply <name>` — DOES
need `admin_all_objects`, which stock `user` and `power` roles lack.

This handler is the bridge: a normal authenticated user POSTs the model
name + host app; the handler uses splunkd's **system token** to flip the
ACL, bypassing the user's role limit. To prevent it being a generic
"promote any lookup globally" backdoor, the model-name pattern is
strictly pinned to `^mltk_[a-z]+_[a-z0-9_]+_aiworkbench_v\\d+$` — only
lookup-table-files produced by our own MLTK templates qualify.

Request body (JSON):
  model_name : string  -- e.g. "mltk_outlier_disk_smart3raw_aiworkbench_v1"
                          (without the __mlspl_ prefix or extension).
  app        : string  -- the Splunk app the model file lives in.
                          Must be one the calling user can see in
                          /services/apps/local.

Response (JSON):
  ok               : bool
  model_name       : echoed
  promoted_files   : list of __mlspl_<name>.<ext> entries promoted
  failed           : list of {file, reason}
  registry_updated : bool   -- whether itmip_llm_mltk_models was upserted

Security:
- Authenticated user required.
- Model-name regex pin (no arbitrary lookup promotion).
- `app` validated against the user's visible apps list (no system apps,
  no apps the caller can't see).
- Rate-limited per user (10 / minute).
- Every successful call is logged via stderr -> splunkd.log AND upserted
  into the itmip_llm_mltk_models KVStore collection so admins can audit.
"""

import json
import os
import re
import sys
import time
import traceback

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_license import capability_enabled  # noqa: E402

from itmip_llm_common import (  # noqa: E402
    APP_NAME,
    err,
    ok,
    rate_limit_check,
    system_token,
    user_name,
    user_token,
)


# Model-name pin. The `_aiworkbench_v<N>` suffix marks it as ours; the
# `mltk_<algo>_<thing>_` prefix mirrors the convention in
# src/services/useCases.ts. Anything outside this pattern is refused so
# this endpoint can never be used to globally share a customer's
# unrelated lookup-table-file.
# The legacy `_aiasst_` token (renamed to `_aiworkbench_` to avoid confusion
# with Splunk's own "AI Assistant" app) is still accepted so models trained
# before the rename remain shareable.
MODEL_NAME_RE = re.compile(r"^mltk_[a-z]+_[a-z0-9_]+_(?:aiasst|aiworkbench)_v\d+$")

# Apps an end-user is never allowed to target — system / SA / TA apps
# the AI Assistent has no business writing into.
APP_DENY_PREFIXES = ("splunk_internal_", "system", "search_artifacts")
APP_DENY_EXACT = {"launcher", "splunk_monitoring_console"}

# MLTK persists models as exactly one of these three file extensions.
# We attempt to share every variant — silently tolerate the 404s for
# variants that don't exist.
MODEL_EXTENSIONS = ("csv", "mlmodel", "onnx")

REGISTRY_COLLECTION = "itmip_llm_mltk_models"

# Rate limit per user (per-minute cap). Set deliberately tight: a normal
# template run shares at most 2 models in 30 seconds. 10/min leaves
# plenty of headroom while making automation-driven misuse obvious.
RATE_LIMIT_PER_MINUTE = 10


def _user_visible_apps(sys_token, user_token_value):
    """Return the set of app ids visible to the calling user.

    Uses the user's own token (so Splunk's ACL filters the list) — the
    handler refuses any `app` argument outside this set.
    """
    try:
        resp, content = rest.simpleRequest(
            "/services/apps/local?count=0&output_mode=json",
            sessionKey=user_token_value,
            method="GET",
        )
    except Exception:
        return set()
    if getattr(resp, "status", 0) != 200:
        return set()
    try:
        data = json.loads(content)
    except Exception:
        return set()
    out = set()
    for entry in data.get("entry") or []:
        name = entry.get("name") or ""
        content_obj = entry.get("content") or {}
        if content_obj.get("disabled"):
            continue
        if content_obj.get("visible") is False:
            continue
        out.add(name)
    return out


def _app_allowed(app, visible_apps):
    if not app or not isinstance(app, str):
        return False
    if app in APP_DENY_EXACT:
        return False
    for pref in APP_DENY_PREFIXES:
        if app.startswith(pref):
            return False
    return app in visible_apps


def _model_owner_for(app, sys_token, file_name):
    """Find the owner-namespace the file lives in.

    `fit … into <model>` writes the model as USER-OWNED + sharing=user
    when the dispatching user has not explicitly elevated sharing. The
    file therefore lives at /servicesNS/<owner>/<app>/... — NOT in
    `nobody`. We GET via the `-` wildcard owner (Splunk's standard
    "any owner" alias) which returns the actual entry with its true
    owner in the ACL. We then re-POST to the owner-specific path to
    promote the ACL.

    Returns the owner string (e.g. "admin") on found, None on missing.
    """
    path = (
        "/servicesNS/-/{app}/data/lookup-table-files/{file}?output_mode=json"
    ).format(app=app, file=file_name)
    try:
        resp, content = rest.simpleRequest(
            path, sessionKey=sys_token, method="GET"
        )
    except Exception as exc:
        msg = str(exc)
        if "[HTTP 404]" in msg or "HTTP 404" in msg:
            return None
        return None
    if getattr(resp, "status", 0) != 200:
        return None
    try:
        data = json.loads(content)
        entries = data.get("entry") or []
        if not entries:
            return None
        acl = entries[0].get("acl") or {}
        return acl.get("owner") or "nobody"
    except Exception:
        return None


def _promote_file(sys_token, app, file_name):
    """POST owner=nobody, sharing=global to the lookup-table-file's ACL.

    Discovers the real owner first (via `-` wildcard) so user-private
    files written by `fit` get re-owned to `nobody` AND promoted to
    global sharing in one call. Without the discovery step we'd POST
    to /servicesNS/nobody/<app>/... and Splunk would 404 because the
    entry doesn't exist under that owner.

    Returns ('ok' | 'missing' | 'error', detail).
    """
    owner = _model_owner_for(app, sys_token, file_name)
    if owner is None:
        return "missing", "not found"
    path = (
        "/servicesNS/{owner}/{app}/data/lookup-table-files/{file}/acl"
    ).format(owner=owner, app=app, file=file_name)
    try:
        resp, _content = rest.simpleRequest(
            path,
            sessionKey=sys_token,
            method="POST",
            postargs={"owner": "nobody", "sharing": "global"},
        )
    except Exception as exc:
        msg = str(exc)
        if "[HTTP 404]" in msg or "HTTP 404" in msg:
            return "missing", "not found"
        return "error", msg[:240]
    status = getattr(resp, "status", 0)
    if status in (200, 201):
        return "ok", "promoted from %s" % owner
    if status == 404:
        return "missing", "not found"
    return "error", "status %s" % status


def _model_file_exists(sys_token, app, file_name):
    """HEAD-style probe via the `-` wildcard owner so user-private files
    are discoverable. (Splunk's `fit` writes the model as user-owned by
    default; the file lives under /servicesNS/<owner>/<app>/, NOT under
    /servicesNS/nobody/<app>/.)"""
    return _model_owner_for(app, sys_token, file_name) is not None


def _find_model_apps(sys_token, model_name, candidate_apps):
    """Scan candidate apps for any of the __mlspl_<name>.<ext> files.

    Returns dict {app: [matching_file_names]}. Apps with no match aren't
    in the result. We probe candidate apps with HEADs that splunkd
    answers in well under 10ms each — the scan adds a few hundred ms
    at most for a typical 20-app install.
    """
    found = {}
    for app in candidate_apps:
        present = []
        for ext in MODEL_EXTENSIONS:
            file_name = "__mlspl_%s.%s" % (model_name, ext)
            if _model_file_exists(sys_token, app, file_name):
                present.append(file_name)
        if present:
            found[app] = present
    return found


def _upsert_registry(
    sys_token, model_name, app, user, template, description
):
    """Write a row into itmip_llm_mltk_models indexed by model_name.

    Best-effort — registry write failure is not fatal to the share
    operation. Returns True on success.

    KVStore's keyed-URL POST replaces the entire document, so we must
    include every field every time. To preserve `created_at_epoch`
    across re-shares we GET first and merge.
    """
    now = int(time.time())
    keyed_url = (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}/{key}"
    ).format(app=APP_NAME, coll=REGISTRY_COLLECTION, key=model_name)
    existing_created = None
    try:
        resp, content = rest.simpleRequest(
            keyed_url + "?output_mode=json",
            sessionKey=sys_token,
            method="GET",
        )
        if getattr(resp, "status", 0) == 200:
            existing = json.loads(content)
            if isinstance(existing, dict):
                existing_created = existing.get("created_at_epoch")
    except Exception:
        # 404 (first share) or other read failure — fall through.
        pass

    body = {
        "_key": model_name,
        "model_name": model_name,
        "host_app": app,
        "created_by": user,
        "template": template or "",
        "description": description or "",
        "created_at_epoch": existing_created if existing_created else now,
        "last_shared_at": now,
    }

    # Try keyed update first.
    try:
        resp, _ = rest.simpleRequest(
            keyed_url, sessionKey=sys_token, method="POST", jsonargs=json.dumps(body)
        )
        if getattr(resp, "status", 0) in (200, 201):
            return True
    except Exception:
        pass

    # Fallback: create at the collection root (used when the keyed URL
    # 404s on some Splunk versions even though we want an upsert).
    create_url = (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}"
    ).format(app=APP_NAME, coll=REGISTRY_COLLECTION)
    try:
        resp, _ = rest.simpleRequest(
            create_url,
            sessionKey=sys_token,
            method="POST",
            jsonargs=json.dumps(body),
        )
        return getattr(resp, "status", 0) in (200, 201)
    except Exception:
        return False


def _audit_log(user, model_name, app, promoted, failed):
    """Emit one structured line to stderr — splunkd routes that to
    splunkd.log so admins can grep for 'mltk_share' to audit."""
    sys.stderr.write(
        "itmip_llm_audit action=mltk_share user=%s model=%s app=%s "
        "promoted=%d failed=%d\n"
        % (user, model_name, app, len(promoted), len(failed))
    )
    sys.stderr.flush()


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "POST").upper()
            if method != "POST":
                return err(405, "Only POST is supported.")
            usr_token = user_token(args)
            if not usr_token:
                return err(401, "Not authenticated.")
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")

            # v1.4.1 — ML generation (MLTK fit / CDTSM training) is a
            # Professional+ feature (per-feature licensing). Promoting a
            # fit-trained model is the server-side completion of an ML
            # workflow, so refuse it below the cap. Fail-closed.
            # Spec: instructions/FEATURE_LICENSING_SPEC.md
            if not capability_enabled(sys_token, "ml_generation"):
                return err(
                    403, "Machine-learning workflows require a Professional or "
                    "higher license."
                )

            who = user_name(args) or "unknown"
            if not rate_limit_check("mltk_share", who, RATE_LIMIT_PER_MINUTE):
                return err(
                    429,
                    "Too many MLTK share requests; rate-limited at %d/min "
                    "per user." % RATE_LIMIT_PER_MINUTE,
                )

            payload_raw = args.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw)
            except Exception:
                return err(400, "Invalid JSON payload.")

            model_name = (payload.get("model_name") or "").strip()
            # `host_app` is the preferred name when the LLM knows
            # exactly where the model file landed; `app` is the legacy
            # name kept for backward compatibility.
            hint_app = (
                payload.get("host_app") or payload.get("app") or ""
            ).strip()
            template = (payload.get("template") or "").strip()
            description = (payload.get("description") or "").strip()

            if not MODEL_NAME_RE.match(model_name):
                return err(
                    400,
                    "model_name must match the AI-Assistent pattern "
                    "mltk_<algo>_<thing>_aiworkbench_v<N> (lowercase, "
                    "alphanumeric + underscore).",
                )

            visible = _user_visible_apps(sys_token, usr_token)

            # Build the candidate-app probe order:
            #   1. The hint_app the caller passed (most common: where
            #      they JUST created the training search).
            #   2. Splunk_ML_Toolkit (where MLTK's own UI persists
            #      models — always a strong candidate).
            #   3. Every other visible app — covers the case where the
            #      LLM dispatched the search inline (which runs in
            #      whatever app context Splunk decided) and the model
            #      ended up somewhere unexpected.
            candidate_apps = []
            if hint_app and _app_allowed(hint_app, visible):
                candidate_apps.append(hint_app)
            if (
                "Splunk_ML_Toolkit" in visible
                and "Splunk_ML_Toolkit" not in candidate_apps
            ):
                candidate_apps.append("Splunk_ML_Toolkit")
            for a in sorted(visible):
                if a in candidate_apps:
                    continue
                if not _app_allowed(a, visible):
                    continue
                candidate_apps.append(a)

            if not candidate_apps:
                return err(
                    403,
                    "No allowed apps to scan. hint_app=%r is not visible "
                    "to the calling user (and no other visible apps "
                    "qualified)." % hint_app,
                )

            # If the caller gave a hint_app but it isn't visible, refuse
            # explicitly — don't silently scan the wider set.
            if hint_app and not _app_allowed(hint_app, visible):
                return err(
                    403,
                    "App %r is not visible to the calling user, or is "
                    "system-reserved." % hint_app,
                )

            # Probe candidate apps for the model file. Stop after the
            # first match (typical case). If the same model exists in
            # MULTIPLE apps we still promote them all — that's safer
            # than picking one and leaving the others stuck on private
            # sharing.
            found_by_app = _find_model_apps(
                sys_token, model_name, candidate_apps
            )

            if not found_by_app:
                return err(
                    404,
                    "No model files named __mlspl_%s.{csv,mlmodel,onnx} "
                    "exist in any visible app. Did the training search "
                    "run, and did it succeed? Probed apps: %s"
                    % (model_name, ", ".join(candidate_apps[:8])),
                )

            promoted = []
            failed = []
            promoted_app = None
            for app_name, file_names in found_by_app.items():
                for file_name in file_names:
                    status, detail = _promote_file(sys_token, app_name, file_name)
                    if status == "ok":
                        promoted.append(
                            {"app": app_name, "file": file_name}
                        )
                        promoted_app = promoted_app or app_name
                    elif status == "missing":
                        # Race: existed at HEAD time, gone at POST time.
                        continue
                    else:
                        failed.append(
                            {
                                "app": app_name,
                                "file": file_name,
                                "reason": detail,
                            }
                        )

            registry_updated = False
            if promoted and promoted_app:
                registry_updated = _upsert_registry(
                    sys_token,
                    model_name,
                    promoted_app,
                    who,
                    template,
                    description,
                )
                _audit_log(
                    who,
                    model_name,
                    promoted_app,
                    [p["file"] for p in promoted],
                    failed,
                )

            return ok(
                {
                    "ok": len(failed) == 0 and len(promoted) > 0,
                    "model_name": model_name,
                    "promoted_app": promoted_app,
                    "promoted_files": [p["file"] for p in promoted],
                    "promoted_in_apps": sorted(
                        {p["app"] for p in promoted}
                    ),
                    "failed": failed,
                    "registry_updated": registry_updated,
                    "probed_apps": candidate_apps[: len(found_by_app) + 1],
                }
            )
        except Exception as exc:
            sys.stderr.write(
                "itmip_llm_mltk_share unhandled error: %s\n%s\n"
                % (exc, traceback.format_exc())
            )
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
