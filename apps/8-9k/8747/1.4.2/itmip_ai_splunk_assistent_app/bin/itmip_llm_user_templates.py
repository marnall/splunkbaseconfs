"""v0.9.7 — End-user template authoring REST handler.

Exposes two endpoints, both POST-only (routed at `/itmip_llm/user_templates` in
restmap.conf; needs the matching `[expose:itmip_llm_user_templates]` +
`/user_templates/*` stanzas in web.conf or the SPA can't reach them):

  POST /services/itmip_llm/user_templates/user_create  → create a new
       private template owned by the calling user.
  POST /services/itmip_llm/user_templates/user_update  → update an existing
       private template the caller already owns.

Both are reachable from the LLM dispatcher via the
`splunk_create_user_template` / `splunk_update_user_template` built-in
tools (see src/services/tools.ts). They are the **only** path by which
an end user can write to `itmip_ai_use_cases` — the admin write path
goes through the standard KVStore endpoint, which is admin-only by ACL.

Server-side enforcement (regardless of what the LLM emits):

- `sharing` is forced to 'private'.
- `owner_user` is forced to the calling Splunk username.
- `owner_org_short` / `owner_bu_short` are taken from the dispatcher
  ctx in the request body (the dispatcher already resolved the user's
  tenant — see src/services/tenancy.ts).
- `creator` / `updated_by` / `updated_at` / `version` / `is_default` /
  `is_general` / `status` / `required_roles` / `dependent_apps` are
  all server-forced too.
- Skills referenced in `includes_skills` must exist AND be visible to
  the caller (we re-check against itmip_ai_skills using the system
  token + the caller's resolved tenant). Unknown / invisible skills
  → 400 with structured `errors[]`.
- Forbidden-content scan: the prompt body must not contain literals
  like `sharing=`, `is_default=`, `is_general=`, `creator: system`,
  role-elevation patterns, or `owner_user=`. Catches prompt-injected
  content the LLM passed through verbatim. Logs to audit.

Every successful write emits one row to `itmip_authoring_changes`
(`action=create|update`, `authoring_mode=llm_mediated`). Failed
attempts whose intent matters for the security audit (override
attempts, ownership-check failures) also emit an event with
`errors[...]` and `attempted_override_fields[...]`.

Spec: instructions/AUTHORING_AND_PROMOTION_SPEC.md §3 + §4.2.
"""

import json
import os
import re
import sys
import time
import uuid

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

from itmip_llm_common import (  # noqa: E402
    APP_NAME,
    err,
    json_response,
    ok,
    system_token,
    user_name,
    user_token,
)


# v0.9.7 — structured-envelope helper. splunkFetch on the TS side
# throws SplunkApiError on any non-2xx response, which would swallow
# our nicely-structured {ok:false, errors:[]} envelopes. Use this
# helper for validation / quota / ownership failures so the LLM
# dispatcher can read the envelope and self-correct on the workflow's
# retry loop. Reserve real non-2xx for "the dispatcher itself is
# broken" cases (missing auth token, KVStore unavailable, etc.).
def envelope(payload):
    """Return a 200-status JSON envelope. Always carries an `ok` bool
    and (on failure) an `errors` list of human-readable strings."""
    return json_response(200, payload)

TEMPLATES_COLLECTION = "itmip_ai_use_cases"
SKILLS_COLLECTION = "itmip_ai_skills"
AUDIT_COLLECTION = "itmip_authoring_changes"

# Per spec §4.2. Configurable per-Org via itmip_authoring_policies in
# a later release; hard-coded default for now (MVP slice).
DEFAULT_QUOTA_PER_USER = 25

DEFAULT_ORG = "DFLT"
DEFAULT_BU = "DFLT"

# Per spec §4.2 forbidden-content scan. Conservative — tuned to catch
# the obvious patterns without rejecting legitimate prose. False
# positives surface as 400 with a clear error string so the LLM can
# rephrase; legitimate retries succeed.
FORBIDDEN_CONTENT_PATTERNS = [
    re.compile(r"\bsharing\s*[:=]\s*(global|org|bu)\b", re.IGNORECASE),
    re.compile(r"\bowner_user\s*[:=]", re.IGNORECASE),
    re.compile(r"\bis_default\s*[:=]\s*true\b", re.IGNORECASE),
    re.compile(r"\bis_general\s*[:=]\s*true\b", re.IGNORECASE),
    re.compile(r"\bcreator\s*[:=]\s*[\"']?system[\"']?\b", re.IGNORECASE),
    # Tightened to require an admin-equivalent role after "to" — without
    # this the pattern false-positives on "Set my role to investigate
    # X further" (legitimate English). The threat is specifically role
    # elevation, so requiring the target role name keeps the catch.
    re.compile(
        r"\bset\s+(my|your|the)\s+role\s+to\s+(admin|sc_admin|power|splunk_admin)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\brequired_roles\s*[:=]\s*\[[^\]]*(admin|sc_admin)", re.IGNORECASE),
]

# Per spec §4.2: LLM-supplyable fields. Anything outside this list is
# silently stripped on create (and logged for audit on update).
LLM_SUPPLIABLE_FIELDS = {
    "name",
    "prompt_text",
    "question_text",
    "short_description",
    "short_description_concise",
    "style_profile",
    "categories",
    "tags",
    "includes_skills",
    "allowed_tools",
    "denied_tools",
    "tool_tag_filters",
    "tool_category_filters",
    "allowed_template_refs",
    "denied_template_refs",
    "template_tag_filters",
    "template_category_filters",
}

# Server-forced fields. If the LLM tried to set any of these, the
# attempt is logged with attempted_override_fields[].
SERVER_FORCED_FIELDS = {
    "sharing",
    "owner_user",
    "owner_org_short",
    "owner_bu_short",
    "creator",
    "updated_by",
    "updated_at",
    "created_at",
    "version",
    "is_default",
    "is_general",
    "status",
    "required_roles",
    "dependent_apps",
    "org_short",  # legacy fields — server keeps them in sync with owner_*
    "bu_short",
}


# ─────────────────────────────────────────────────────────────────────
# KVStore helpers
# ─────────────────────────────────────────────────────────────────────

def _coll_url(collection, suffix=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{suffix}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=collection, suffix=suffix)


def _list_collection(sys_token, collection):
    response, content = rest.simpleRequest(
        _coll_url(collection),
        sessionKey=sys_token,
        method="GET",
    )
    status_code = getattr(response, "status", 0)
    if status_code == 404:
        return []
    if status_code != 200:
        raise RuntimeError("KVStore returned %s on %s" % (status_code, collection))
    data = json.loads(content)
    return data if isinstance(data, list) else []


def _get_by_key(sys_token, collection, key):
    safe = "".join(c for c in (key or "") if c.isalnum() or c in "._-")
    if not safe:
        return None
    url = (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}/{k}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=collection, k=safe)
    try:
        resp, content = rest.simpleRequest(url, sessionKey=sys_token, method="GET")
        if getattr(resp, "status", 0) == 200:
            data = json.loads(content)
            return data if isinstance(data, dict) else None
    except Exception:
        pass
    return None


def _post(sys_token, collection, body, key=None):
    """POST a row to KVStore. When `key` is set we upsert that specific
    row; otherwise create a fresh row and let KVStore allocate the _key.

    Mirrors the proven POST pattern from bin/itmip_llm_mcp.py:
      - `?output_mode=json` so the response IS JSON (default is XML —
        without this, _key extraction silently fails).
      - `jsonargs=json.dumps(body)` serialises the payload.
      - `rawResult=True` returns the body as text so we can json.loads
        it ourselves.
    """
    if key:
        safe = "".join(c for c in (key or "") if c.isalnum() or c in "._-")
        url = (
            "/servicesNS/nobody/{app}/storage/collections/data/{coll}/{k}"
            "?output_mode=json"
        ).format(app=APP_NAME, coll=collection, k=safe)
    else:
        url = (
            "/servicesNS/nobody/{app}/storage/collections/data/{coll}"
            "?output_mode=json"
        ).format(app=APP_NAME, coll=collection)
    resp, content = rest.simpleRequest(
        url,
        sessionKey=sys_token,
        method="POST",
        jsonargs=json.dumps(body),
        getargs={"output_mode": "json"},
        rawResult=True,
    )
    return resp, content


# ─────────────────────────────────────────────────────────────────────
# Visibility checks (server-side, defense-in-depth)
# ─────────────────────────────────────────────────────────────────────

def _skill_visible(skill, caller_org, caller_bu):
    """Skill visibility per spec §6.4. Returns True iff the caller can
    see this skill row. Skills with status != operational are invisible
    to end users (admins bypass — but this handler is always called via
    end-user flow, so no bypass)."""
    status = (skill.get("status") or "operational").lower()
    if status != "operational":
        return False
    sharing = (skill.get("sharing") or "").lower()
    if not sharing:
        # Pre-0.9.7 row — derive from legacy org_short/bu_short.
        o = (skill.get("org_short") or DEFAULT_ORG).upper()
        b = (skill.get("bu_short") or DEFAULT_BU).upper()
        if o == DEFAULT_ORG and b == DEFAULT_BU:
            sharing = "global"
        elif o != DEFAULT_ORG and b == DEFAULT_BU:
            sharing = "org"
        else:
            sharing = "bu"
    if sharing == "global":
        return True
    own_org = (skill.get("owner_org_short") or skill.get("org_short") or "").upper()
    own_bu = (skill.get("owner_bu_short") or skill.get("bu_short") or "").upper()
    if sharing == "org":
        return own_org == caller_org.upper()
    if sharing == "bu":
        return own_org == caller_org.upper() and own_bu == caller_bu.upper()
    # private skills don't exist by design; treat as invisible
    return False


# ─────────────────────────────────────────────────────────────────────
# Validation chain
# ─────────────────────────────────────────────────────────────────────

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_field_shapes(payload, errors):
    """§4.2 step 4 — types + lengths + character set."""
    name = payload.get("name") or ""
    if not isinstance(name, str) or not name.strip():
        errors.append("name is required")
    elif len(name) > 80:
        errors.append("name must be ≤ 80 chars")
    elif not NAME_RE.match(name):
        # Convert "User Friendly Title" → "user_friendly_title" silently;
        # otherwise reject. We give the LLM one easy normalisation.
        normalised = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")
        if normalised and NAME_RE.match(normalised):
            payload["name"] = normalised
        else:
            errors.append(
                "name must match [a-z][a-z0-9_]* — got %r" % name
            )

    prompt_text = payload.get("prompt_text") or ""
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        errors.append("prompt_text is required")
    elif len(prompt_text) > 8000:
        errors.append("prompt_text must be ≤ 8000 chars (got %d)" % len(prompt_text))

    question_text = payload.get("question_text") or ""
    if not isinstance(question_text, str):
        errors.append("question_text must be a string")
    elif len(question_text) > 2000:
        errors.append("question_text must be ≤ 2000 chars")

    short_description = payload.get("short_description") or ""
    if not isinstance(short_description, str):
        errors.append("short_description must be a string")
    elif len(short_description) > 200:
        errors.append("short_description must be ≤ 200 chars")

    # ASCII / no-emoji rule on user-facing fields.
    for field_name in ("name", "short_description", "question_text"):
        v = payload.get(field_name)
        if isinstance(v, str):
            try:
                v.encode("ascii")
            except UnicodeEncodeError:
                errors.append(
                    "%s contains non-ASCII characters (emojis are not allowed)"
                    % field_name
                )


def _forbidden_content_scan(text, attempted, errors, field_name):
    """§4.2 step 6 — hard reject when forbidden patterns appear in
    `text`. The spec says body "MUST NOT contain" these — refusing
    here gives the LLM a chance to self-correct on the workflow's
    3-attempt retry loop. Also appends to attempted[] so the audit
    trail records what was tried.
    """
    if not text:
        return
    found = []
    for pat in FORBIDDEN_CONTENT_PATTERNS:
        m = pat.search(text)
        if m:
            found.append(m.group(0))
    if found:
        attempted.append("forbidden_content_in_%s:%s" % (field_name, "|".join(found[:3])))
        errors.append(
            "%s contains forbidden content (matches %s) — rephrase: do not "
            "use the verbatim strings 'sharing=', 'owner_user=', "
            "'is_default=true', 'is_general=true', or 'creator: system' "
            "inside the template body; describe the rule in your own "
            "words instead." % (field_name, found[:3])
        )


def _validate_skill_references(sys_token, payload, caller_org, caller_bu, errors):
    """§4.2 step 5 — every skill in includes_skills must exist AND be
    visible to the caller AND operational."""
    raw = payload.get("includes_skills") or []
    if not isinstance(raw, list) or not raw:
        return
    skill_names = [str(s) for s in raw if isinstance(s, str)]
    if not skill_names:
        return
    try:
        all_skills = _list_collection(sys_token, SKILLS_COLLECTION)
    except Exception:
        errors.append("could not validate skill references (KVStore unavailable)")
        return
    by_name = {s.get("name"): s for s in all_skills if isinstance(s, dict)}
    missing = []
    invisible = []
    for sn in skill_names:
        s = by_name.get(sn)
        if not s:
            missing.append(sn)
            continue
        if not _skill_visible(s, caller_org, caller_bu):
            invisible.append(sn)
    if missing:
        errors.append("unknown skill(s): %s" % ", ".join(missing))
    if invisible:
        errors.append(
            "skill(s) not visible to this user: %s" % ", ".join(invisible)
        )


def _enforce_quota(sys_token, caller_user, errors):
    """§4.2 step 2 — caller may own at most DEFAULT_QUOTA_PER_USER
    private templates."""
    try:
        rows = _list_collection(sys_token, TEMPLATES_COLLECTION)
    except Exception:
        # Be lenient on KVStore hiccups — quota is a soft limit anyway.
        return
    cu = (caller_user or "").lower()
    count = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        if (r.get("sharing") or "").lower() != "private":
            continue
        if (r.get("owner_user") or "").lower() != cu:
            continue
        count += 1
    if count >= DEFAULT_QUOTA_PER_USER:
        errors.append(
            "quota of %d private templates reached; delete some before creating more"
            % DEFAULT_QUOTA_PER_USER
        )


def _ensure_unique_name(sys_token, name, caller_user):
    """§4.2 step 3 — auto-suffix _v2 / _v3 on collision within
    (owner_user). Returns the final (possibly suffixed) name."""
    try:
        rows = _list_collection(sys_token, TEMPLATES_COLLECTION)
    except Exception:
        return name
    cu = (caller_user or "").lower()
    existing = set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        owner = (r.get("owner_user") or "").lower()
        if owner == cu:
            existing.add(r.get("name") or "")
    if name not in existing:
        return name
    n = 2
    while True:
        candidate = "%s_v%d" % (name, n)
        if candidate not in existing:
            return candidate
        n += 1
        if n > 999:
            return "%s_%s" % (name, uuid.uuid4().hex[:6])


# ─────────────────────────────────────────────────────────────────────
# Audit emission
# ─────────────────────────────────────────────────────────────────────

def _audit(sys_token, row):
    """Best-effort write to itmip_authoring_changes. We never let a
    failed audit kill a successful authoring call — log + carry on."""
    try:
        body = dict(row)
        body["timestamp"] = int(time.time())
        body["_key"] = uuid.uuid4().hex
        # KVStore enforceTypes=false on this collection so JSON arrays
        # serialise as-is. Arrays-of-strings stored as JSON strings.
        if isinstance(body.get("attempted_override_fields"), list):
            body["attempted_override_fields"] = json.dumps(
                body["attempted_override_fields"]
            )
        if isinstance(body.get("errors"), list):
            body["errors"] = json.dumps(body["errors"])
        _post(sys_token, AUDIT_COLLECTION, body)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────
# Sub-handlers
# ─────────────────────────────────────────────────────────────────────

def _handle_create(args, sys_token, caller_user, caller_org, caller_bu, payload):
    """POST /services/itmip_llm/use_cases/user_create — see spec §4.2."""
    errors = []
    attempted = []

    # Track which server-forced fields the LLM tried to set. We never
    # error on these — we silently override — but we audit.
    for f in SERVER_FORCED_FIELDS:
        if f in payload:
            attempted.append(f)

    # Strip non-LLM-supplyable fields from the input.
    clean = {k: v for k, v in payload.items() if k in LLM_SUPPLIABLE_FIELDS}

    # Step 4: field shapes.
    _validate_field_shapes(clean, errors)

    # Step 6: forbidden-content scan on the prose-bearing fields.
    # Hard reject — adds to errors[] so the call fails and the LLM
    # can self-correct on the workflow's retry loop.
    for f in ("prompt_text", "short_description", "question_text"):
        _forbidden_content_scan(clean.get(f, ""), attempted, errors, f)

    # Step 5: skill / tool reference validation.
    _validate_skill_references(sys_token, clean, caller_org, caller_bu, errors)
    # (Tool reference validation is intentionally lenient in this MVP
    # slice — tools.ts already gates LLM-side tool calls, so an
    # invalid allowed_tools entry just gets ignored at routing time.)

    if errors:
        _audit(sys_token, {
            "action": "create",
            "object": "template",
            "object_name": clean.get("name") or payload.get("name") or "",
            "owner_user": caller_user,
            "by_user": caller_user,
            "tenant_org": caller_org,
            "tenant_bu": caller_bu,
            "authoring_mode": "llm_mediated",
            "attempted_override_fields": attempted,
            "errors": errors,
        })
        # 200 + ok:false so the LLM dispatcher's splunkFetch (which
        # throws on non-2xx) can read the structured envelope and the
        # workflow retry loop can act on errors[].
        return envelope({
            "ok": False,
            "errors": errors,
            "attempted_override_fields": attempted,
        })

    # Step 2: quota.
    _enforce_quota(sys_token, caller_user, errors)
    if errors:
        _audit(sys_token, {
            "action": "create",
            "object": "template",
            "object_name": clean.get("name") or "",
            "owner_user": caller_user,
            "by_user": caller_user,
            "tenant_org": caller_org,
            "tenant_bu": caller_bu,
            "authoring_mode": "llm_mediated",
            "errors": errors,
        })
        return envelope({"ok": False, "errors": errors})

    # Step 3: auto-suffix on name collision (within owner_user).
    final_name = _ensure_unique_name(sys_token, clean["name"], caller_user)
    clean["name"] = final_name

    # Step 8: persist. Server-forced fields applied here.
    now = int(time.time() * 1000)
    row = dict(clean)
    row.update({
        # Server-forced fields per spec §4.2.
        "sharing": "private",
        "owner_user": caller_user,
        "owner_org_short": caller_org,
        "owner_bu_short": caller_bu,
        # Keep legacy fields in sync for one-release dual-read.
        "org_short": caller_org,
        "bu_short": caller_bu,
        "creator": caller_user,
        "updated_by": caller_user,
        "updated_at": now,
        "created_at": now,
        "version": 1,
        "is_default": False,
        "is_general": False,
        "status": "operational",
        "required_roles": [],
        "dependent_apps": [],
    })

    try:
        resp, content = _post(sys_token, TEMPLATES_COLLECTION, row)
        status_code = getattr(resp, "status", 0)
        if status_code not in (200, 201):
            raise RuntimeError("KVStore returned %s: %s" % (status_code, content))
        new_key = ""
        try:
            data = json.loads(content)
            new_key = data.get("_key") or ""
        except Exception:
            pass
    except Exception as exc:
        _audit(sys_token, {
            "action": "create",
            "object": "template",
            "object_name": final_name,
            "owner_user": caller_user,
            "by_user": caller_user,
            "tenant_org": caller_org,
            "tenant_bu": caller_bu,
            "authoring_mode": "llm_mediated",
            "errors": ["persist failed: %s" % exc],
        })
        return envelope({"ok": False, "errors": ["persist failed: %s" % exc]})

    # Step 9: audit success.
    _audit(sys_token, {
        "action": "create",
        "object": "template",
        "object_name": final_name,
        "object_key": new_key,
        "to_sharing": "private",
        "owner_user": caller_user,
        "by_user": caller_user,
        "tenant_org": caller_org,
        "tenant_bu": caller_bu,
        "authoring_mode": "llm_mediated",
        "attempted_override_fields": attempted,
    })

    return ok({
        "ok": True,
        "name": final_name,
        "_key": new_key,
        "sharing": "private",
        "owner_user": caller_user,
        "attempted_override_fields": attempted,
        "warnings": [],
    })


def _handle_update(args, sys_token, caller_user, caller_org, caller_bu, payload):
    """POST /services/itmip_llm/use_cases/user_update — see spec §4.2."""
    name = payload.get("name") or ""
    patch = payload.get("patch") or {}
    if not isinstance(name, str) or not name.strip():
        return envelope({"ok": False, "errors": ["name is required"]})
    if not isinstance(patch, dict):
        return envelope({"ok": False, "errors": ["patch must be an object"]})

    # Step 1: ownership check. Fetch by name + sharing=private + owner_user.
    try:
        rows = _list_collection(sys_token, TEMPLATES_COLLECTION)
    except Exception as exc:
        return envelope({"ok": False, "errors": ["KVStore read failed: %s" % exc]})

    cu = caller_user.lower()
    target = None
    for r in rows:
        if not isinstance(r, dict):
            continue
        if r.get("name") != name:
            continue
        if (r.get("sharing") or "").lower() != "private":
            continue
        if (r.get("owner_user") or "").lower() != cu:
            continue
        target = r
        break

    if not target:
        _audit(sys_token, {
            "action": "update",
            "object": "template",
            "object_name": name,
            "owner_user": caller_user,
            "by_user": caller_user,
            "tenant_org": caller_org,
            "tenant_bu": caller_bu,
            "authoring_mode": "llm_mediated",
            "errors": ["target template not found or not owned by caller"],
        })
        return envelope({
            "ok": False,
            "errors": ["You can only update private templates you own."],
        })

    attempted = []
    errors = []

    # Step 2: forbidden-field scan.
    for f in SERVER_FORCED_FIELDS:
        if f in patch:
            attempted.append(f)

    # Strip forbidden + unknown fields.
    clean_patch = {k: v for k, v in patch.items() if k in LLM_SUPPLIABLE_FIELDS}

    # Step 3 + 4: field validation against the merged proposed row.
    merged = dict(target)
    merged.update(clean_patch)
    _validate_field_shapes(merged, errors)

    # Forbidden-content scan on prose fields. Hard reject (see create).
    for f in ("prompt_text", "short_description", "question_text"):
        if f in clean_patch:
            _forbidden_content_scan(clean_patch[f], attempted, errors, f)

    # Skill reference validation on the new includes_skills (if changed).
    if "includes_skills" in clean_patch:
        _validate_skill_references(sys_token, clean_patch, caller_org, caller_bu, errors)

    if errors:
        _audit(sys_token, {
            "action": "update",
            "object": "template",
            "object_name": name,
            "owner_user": caller_user,
            "by_user": caller_user,
            "tenant_org": caller_org,
            "tenant_bu": caller_bu,
            "authoring_mode": "llm_mediated",
            "attempted_override_fields": attempted,
            "errors": errors,
        })
        return envelope({
            "ok": False,
            "errors": errors,
            "attempted_override_fields": attempted,
        })

    # Step 5: persist. Bump version + updated_by + updated_at; keep
    # sharing / owner_user / owner_org_short / owner_bu_short / creator
    # / is_default / is_general / required_roles / dependent_apps as
    # they were on the target row (server-enforced immutable for end
    # users).
    now = int(time.time() * 1000)
    new_row = dict(target)
    new_row.update(clean_patch)
    new_row.update({
        # Force-preserve server-managed fields.
        "sharing": "private",
        "owner_user": caller_user,
        "owner_org_short": target.get("owner_org_short") or caller_org,
        "owner_bu_short": target.get("owner_bu_short") or caller_bu,
        "creator": target.get("creator") or caller_user,
        "is_default": False,
        "is_general": False,
        "required_roles": [],
        "dependent_apps": [],
        # Bump.
        "updated_by": caller_user,
        "updated_at": now,
        "version": (target.get("version") or 1) + 1,
    })

    try:
        resp, content = _post(
            sys_token, TEMPLATES_COLLECTION, new_row, key=target.get("_key")
        )
        status_code = getattr(resp, "status", 0)
        if status_code not in (200, 201):
            raise RuntimeError("KVStore returned %s: %s" % (status_code, content))
    except Exception as exc:
        _audit(sys_token, {
            "action": "update",
            "object": "template",
            "object_name": name,
            "owner_user": caller_user,
            "by_user": caller_user,
            "tenant_org": caller_org,
            "tenant_bu": caller_bu,
            "authoring_mode": "llm_mediated",
            "errors": ["persist failed: %s" % exc],
        })
        return envelope({"ok": False, "errors": ["persist failed: %s" % exc]})

    _audit(sys_token, {
        "action": "update",
        "object": "template",
        "object_name": name,
        "object_key": target.get("_key") or "",
        "from_sharing": "private",
        "to_sharing": "private",
        "owner_user": caller_user,
        "by_user": caller_user,
        "tenant_org": caller_org,
        "tenant_bu": caller_bu,
        "authoring_mode": "llm_mediated",
        "attempted_override_fields": attempted,
    })

    # Build a simple diff summary.
    changed_fields = sorted(clean_patch.keys())

    return ok({
        "ok": True,
        "name": name,
        "_key": target.get("_key") or "",
        "version": new_row["version"],
        "changed_fields": changed_fields,
        "attempted_override_fields": attempted,
        "warnings": [],
    })


# ─────────────────────────────────────────────────────────────────────
# Handler entry point
# ─────────────────────────────────────────────────────────────────────

class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "GET").upper()
            if method != "POST":
                return err(405, "Only POST is supported on this endpoint.")

            if not user_token(args):
                return err(401, "Not authenticated.")
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")

            # Routing: Splunk's persistconn passes the URL via
            # `path_info` (or `path` on older runtimes). Whether the
            # match-prefix is stripped depends on Splunk version, so
            # we substring-match against known sub-paths rather than
            # equality-matching against a stripped tail. Mirror of the
            # itmip_llm_mcp.py routing pattern (which has shipped
            # since 0.7.0).
            path = (args.get("path_info") or args.get("path") or "") or ""
            payload_raw = args.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            except Exception:
                return err(400, "Body must be valid JSON.")
            if not isinstance(payload, dict):
                return err(400, "Body must be a JSON object.")

            # Detect action via substring on the URL. Fall back to a
            # `__action__` field in the payload so the dispatcher can
            # be explicit (used by automation that POSTs to the base
            # match path without a sub-segment).
            if "user_create" in path:
                action = "user_create"
            elif "user_update" in path:
                action = "user_update"
            else:
                action = (payload.pop("__action__", "") if isinstance(payload, dict) else "")
            if not action:
                return err(
                    400,
                    "Missing action (use sub-path /user_create or /user_update — got path=%r)." % path
                )

            caller_user = user_name(args)
            caller_org = (
                payload.pop("caller_org_short", None)
                or args.get("orgShort")
                or DEFAULT_ORG
            )
            caller_bu = (
                payload.pop("caller_bu_short", None)
                or args.get("buShort")
                or DEFAULT_BU
            )

            if action == "user_create":
                return _handle_create(
                    args, sys_token, caller_user, caller_org, caller_bu, payload
                )
            if action == "user_update":
                return _handle_update(
                    args, sys_token, caller_user, caller_org, caller_bu, payload
                )
            return err(404, "Unknown action %r (expected user_create / user_update)." % action)
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
