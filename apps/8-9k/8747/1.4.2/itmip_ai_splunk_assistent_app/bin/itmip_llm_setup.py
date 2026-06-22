"""POST /services/itmip_llm/setup — idempotent first-run bootstrap.

For each managed KVStore collection this handler:

  1. Skips it if it already has data.
  2. Migrates data from a legacy collection if one exists with content
     (used for the v0.2 itmip_claude_use_cases → itmip_ai_use_cases
     rename).
  3. Seeds from default/data/seeds/<collection>.json if that file exists
     and contains a non-empty JSON array.

Writes use the system auth token so non-admins can also trigger the
endpoint (handy on a fresh Splunk where the first browser load happens
before an admin has logged in). The endpoint itself is gated on an
authenticated session — see requireAuthentication=true in restmap.conf.

The frontend calls this once per page-load on boot. Splunk admins can
also re-trigger it manually with:

    curl -k -u admin:<pass> -X POST \\
      https://localhost:8089/services/itmip_llm/setup
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
    APP_NAME,
    err,
    ok,
    system_token,
    user_token,
)

SEEDS_DIR = os.path.join(APP_DIR, "default", "data", "seeds")

# (target collection, legacy collection or None, seed filename)
MANAGED = [
    ("itmip_ai_use_cases", "itmip_claude_use_cases", "itmip_ai_use_cases.json"),
    ("itmip_organisations", None, "itmip_organisations.json"),
    ("itmip_business_units", None, "itmip_business_units.json"),
    ("itmip_llm_configs", None, "itmip_llm_configs.json"),
    ("itmip_tool_assignments", None, "itmip_tool_assignments.json"),
]

# Records that MUST exist regardless of seed-file state. Indexed by
# collection, each entry must include an explicit _key so the
# existence check is exact. These are upserted only when missing —
# never overwriting a user's edits.
MANDATORY_DEFAULTS = {
    "itmip_organisations": [
        {
            "_key": "DFLT",
            "short": "DFLT",
            "name": "Default Organisation",
            "description": (
                "Fallback tenant. Used by the bootstrap Anthropic LLM "
                "config and by users whose Splunk role doesn't map to "
                "any explicit org."
            ),
            "created_at": 0,
            "updated_at": 0,
        }
    ],
    "itmip_business_units": [
        {
            "_key": "DFLT_DFLT",
            "org_short": "DFLT",
            "short": "DFLT",
            "name": "Default Business Unit",
            "description": (
                "Fallback BU inside the default org. Mirrors the "
                "DFLT/DFLT scope the bootstrap Anthropic LLM config "
                "lives in."
            ),
            "created_at": 0,
            "updated_at": 0,
        }
    ],
}


def _kv_url(collection, suffix=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{sfx}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=collection, sfx=suffix)


def _query(sys_token, collection):
    """Return list of records (or [] on 404). Raises on other errors."""
    resp, content = rest.simpleRequest(
        _kv_url(collection), sessionKey=sys_token, method="GET"
    )
    status = getattr(resp, "status", 0)
    if status == 404:
        return []
    if status != 200:
        raise RuntimeError("GET %s -> %s" % (collection, status))
    data = json.loads(content)
    return data if isinstance(data, list) else []


def _batch_save(sys_token, collection, records):
    """Bulk-insert records using KVStore batch_save. Empty input is a no-op."""
    if not records:
        return 0
    resp, _ = rest.simpleRequest(
        _kv_url(collection, "/batch_save"),
        sessionKey=sys_token,
        method="POST",
        jsonargs=json.dumps(records),
    )
    status = getattr(resp, "status", 0)
    if status not in (200, 201):
        raise RuntimeError("batch_save %s -> %s" % (collection, status))
    return len(records)


def _read_seed_file(filename):
    path = os.path.join(SEEDS_DIR, filename)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _ensure_seeded(sys_token, target, legacy, seed_file):
    """Return ('skipped'|'migrated'|'seeded'|'empty', count)."""
    try:
        existing = _query(sys_token, target)
    except Exception as exc:
        return ("error: %s" % exc, 0)
    if existing:
        return ("skipped", len(existing))

    if legacy:
        try:
            legacy_items = _query(sys_token, legacy)
        except Exception:
            legacy_items = []
        if legacy_items:
            try:
                n = _batch_save(sys_token, target, legacy_items)
                return ("migrated_from_%s" % legacy, n)
            except Exception as exc:
                return ("error_migrating: %s" % exc, 0)

    seed = _read_seed_file(seed_file)
    if seed:
        try:
            n = _batch_save(sys_token, target, seed)
            return ("seeded", n)
        except Exception as exc:
            return ("error_seeding: %s" % exc, 0)

    return ("empty", 0)


def _ensure_mandatory(sys_token, collection, records):
    """Upsert mandatory defaults only when their _key is missing.

    A user who has edited the DFLT entry (e.g. renamed it) keeps their
    edit — the existence check is done by _key, so we only fill in the
    canonical record when no entry under that _key exists at all.
    """
    inserted = 0
    for rec in records:
        key = rec.get("_key")
        if not key:
            continue
        try:
            resp, _ = rest.simpleRequest(
                _kv_url(collection, "/" + key),
                sessionKey=sys_token,
                method="GET",
            )
            if getattr(resp, "status", 0) == 200:
                continue
        except Exception:
            continue
        try:
            rest.simpleRequest(
                _kv_url(collection),
                sessionKey=sys_token,
                method="POST",
                jsonargs=json.dumps(rec),
            )
            inserted += 1
        except Exception:
            pass
    return inserted


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "GET").upper()
            if method not in ("GET", "POST"):
                return err(405, "Only GET and POST are supported.")

            if not user_token(args):
                return err(401, "Not authenticated.")

            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")

            results = {}
            for target, legacy, seed_file in MANAGED:
                action, count = _ensure_seeded(sys_token, target, legacy, seed_file)
                results[target] = {"action": action, "count": count}

                mandatory = MANDATORY_DEFAULTS.get(target)
                if mandatory:
                    inserted = _ensure_mandatory(sys_token, target, mandatory)
                    if inserted:
                        results[target]["mandatory_inserted"] = inserted

            return ok({"ok": True, "collections": results})
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
