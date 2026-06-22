"""REST handler for licensing.

All licensing operations live behind one endpoint with the verb in
the JSON body — keeps the restmap regex simple and matches how the
other handlers in this app shape their API.

  GET    /services/itmip_llm/license
      → returns the full state (tier, badge, GUID, recipients, expiry)
  POST   /services/itmip_llm/license  body {action: "store", cryptolens_response: {...}}
      → persists a Cryptolens response (browser-activated flow)
  POST   /services/itmip_llm/license  body {action: "validate"}
      → re-calls Cryptolens server-side (only when SH has internet)
  POST   /services/itmip_llm/license  body {action: "validate", cryptolens_response: {...}}
      → uses a browser-refreshed response, no server-side internet call
  POST   /services/itmip_llm/license  body {action: "recipients", emails: [...]}
      → saves the expiry-warning recipient list + (re)creates the
        Splunk Enterprise alert
  DELETE /services/itmip_llm/license
      → removes the stored license

The Cryptolens response is encrypted at rest via storage/passwords
(realm=itmip_llm_assistent_app, name=license_blob). The
non-sensitive subset (key, tier, expires, recipients) is mirrored
into KVStore `itmip_llm_license` for fast reads.
"""

import json
import os
import sys
import urllib.parse

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_LIB = os.path.join(APP_DIR, "lib")
APP_BIN = os.path.dirname(os.path.abspath(__file__))
for p in (APP_LIB, APP_BIN):
    if p not in sys.path:
        sys.path.insert(0, p)

import splunk.persistconn.application as application  # type: ignore
import splunk.rest as rest  # type: ignore

import time  # noqa: E402

from itmip_llm_common import (  # noqa: E402
    APP_NAME,
    LLM_PASSWORD_REALM,
    err,
    is_admin,
    ok,
    system_token,
    user_name,
    user_token,
)
from itmip_llm_guid import get_environment_guid  # noqa: E402
from itmip_llm_license_cryptolens import (  # noqa: E402
    activate as cryptolens_activate,
)
from itmip_llm_license_tier import (  # noqa: E402
    resolve_tier, caps_for, resolve_capabilities,
)


LICENSE_SECRET_NAME = "license_blob"
LICENSE_KV_COLLECTION = "itmip_llm_license"
LICENSE_KV_KEY = "current"

# v1.4.1 — MSP header badge text is install-configurable (MSPs white-label).
# itmip_ai_workbench.conf [branding] msp_badge_label; default below.
BRANDING_CONF_FILE = "itmip_ai_workbench"
BRANDING_STANZA = "branding"
DEFAULT_MSP_BADGE_LABEL = "MSP Enterprise Edition"


def _msp_badge_label():
    """MSP header-badge text from itmip_ai_workbench.conf [branding]
    msp_badge_label, defaulting to 'MSP Enterprise Edition'. Install-time only
    (no UI/REST). Fails safe to the default if the conf/stanza is absent."""
    try:
        from splunk.clilib import cli_common  # type: ignore
        stanza = cli_common.getConfStanza(BRANDING_CONF_FILE, BRANDING_STANZA)
        if isinstance(stanza, dict):
            val = (stanza.get("msp_badge_label") or "").strip()
            if val:
                return val
    except Exception:
        pass
    return DEFAULT_MSP_BADGE_LABEL
RECIPIENT_KV_KEY = "recipients"
# v1.3.0 — single-user (free-tier) owner binding. The first user to load a
# personal-tier install becomes the owner; everyone else is greyed until a
# license is added. Stored in the license KVStore collection; never deleted
# on downgrade ("hide, don't delete").
FREE_OWNER_KV_KEY = "free_owner"
SAVED_SEARCH_STANZA = "itmip_llm_license_expiry_warning"


# ---------- storage helpers ----------------------------------------------

def _kv_url(suffix=""):
    return (
        "/servicesNS/nobody/{app}/storage/collections/data/{coll}{sfx}"
        "?output_mode=json"
    ).format(app=APP_NAME, coll=LICENSE_KV_COLLECTION, sfx=suffix)


def _password_path(name):
    return (
        "/servicesNS/nobody/{app}/storage/passwords/"
        "{realm}%3A{name}%3A?output_mode=json"
    ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=name)


def _store_secret(sys_token, name, value):
    """POST to /servicesNS/.../storage/passwords. Updates if exists."""
    # Try create first.
    try:
        rest.simpleRequest(
            "/servicesNS/nobody/{app}/storage/passwords".format(app=APP_NAME),
            sessionKey=sys_token,
            method="POST",
            postargs={
                "name": name,
                "realm": LLM_PASSWORD_REALM,
                "password": value,
            },
        )
    except Exception:
        # Already exists → update.
        update_path = (
            "/servicesNS/nobody/{app}/storage/passwords/"
            "{realm}%3A{name}%3A"
        ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=name)
        rest.simpleRequest(
            update_path,
            sessionKey=sys_token,
            method="POST",
            postargs={"password": value},
        )


def _load_secret(sys_token, name):
    try:
        resp, content = rest.simpleRequest(
            _password_path(name), sessionKey=sys_token, method="GET"
        )
    except Exception as exc:
        msg = str(exc)
        if "[HTTP 404]" in msg or "HTTP 404" in msg:
            return None
        raise
    if getattr(resp, "status", 0) != 200:
        return None
    data = json.loads(content)
    entries = data.get("entry") or []
    if not entries:
        return None
    return (entries[0].get("content") or {}).get("clear_password") or None


def _delete_secret(sys_token, name):
    delete_path = (
        "/servicesNS/nobody/{app}/storage/passwords/"
        "{realm}%3A{name}%3A"
    ).format(app=APP_NAME, realm=LLM_PASSWORD_REALM, name=name)
    try:
        rest.simpleRequest(delete_path, sessionKey=sys_token, method="DELETE")
    except Exception:
        pass


def _kv_get(sys_token, key):
    try:
        resp, content = rest.simpleRequest(
            _kv_url("/" + key), sessionKey=sys_token, method="GET"
        )
    except Exception as exc:
        msg = str(exc)
        if "[HTTP 404]" in msg or "HTTP 404" in msg:
            return None
        return None
    if getattr(resp, "status", 0) != 200:
        return None
    return json.loads(content)


def _kv_put(sys_token, key, doc):
    """Upsert at explicit _key."""
    body = dict(doc)
    body["_key"] = key
    try:
        rest.simpleRequest(
            _kv_url("/" + key),
            sessionKey=sys_token,
            method="POST",
            jsonargs=json.dumps(body),
        )
    except Exception:
        rest.simpleRequest(
            _kv_url(),
            sessionKey=sys_token,
            method="POST",
            jsonargs=json.dumps(body),
        )


def _kv_delete(sys_token, key):
    try:
        rest.simpleRequest(
            _kv_url("/" + key), sessionKey=sys_token, method="DELETE"
        )
    except Exception:
        pass


# ---------- saved search (expiry alert) ----------------------------------

def _saved_search_url(app):
    return "/servicesNS/nobody/{app}/saved/searches".format(app=app)


def _delete_recipient_savedsearch(sys_token):
    """Remove the expiry alert. No-op if it isn't there yet."""
    delete_url = "{base}/{name}".format(
        base=_saved_search_url(APP_NAME), name=SAVED_SEARCH_STANZA
    )
    try:
        rest.simpleRequest(delete_url, sessionKey=sys_token, method="DELETE")
    except Exception:
        pass


def _write_recipient_savedsearch(sys_token, emails):
    """(Re)create the expiry-warning saved search.

    Uses the standard `saved/searches` REST endpoint so the alert
    appears in Splunk's UI and survives app reloads cleanly.

    When `emails` is empty there's nobody to notify, so we delete any
    existing alert rather than leave one that fires and emails no one.
    """
    if not emails:
        _delete_recipient_savedsearch(sys_token)
        return

    # Use the `ai_assistant_license_index` macro so customers can route
    # license events into a non-default index by overriding the macro
    # AND inputs.conf in lock-step. earliest/latest are set via
    # dispatch.* so the saved-search Time Range UI matches.
    search = (
        'search `ai_assistant_license_index` | '
        'where expiring_in_days<30 | head 1'
    )
    name = SAVED_SEARCH_STANZA
    body = {
        "name": name,
        "search": search,
        "cron_schedule": "0 9 * * *",
        "is_scheduled": "1",
        "dispatch.earliest_time": "-7d@d",
        "dispatch.latest_time": "now",
        # Splunk needs BOTH `actions = email` (to enable) AND the
        # `action.email.*` params (to configure). Setting only
        # `action.email = 1` is documented as equivalent but in
        # practice does NOT light the email action up in the UI on
        # Splunk Enterprise 9.x — confirmed by inspecting a save'd
        # alert that came out with only "Add to Triggered Alerts".
        "actions": "email",
        "action.email": "1",
        "action.email.to": ",".join(emails),
        "action.email.subject": (
            "AiWorkbench — license expiring soon"
        ),
        "action.email.message.alert": (
            "The AiWorkbench license is expiring "
            "within 30 days. Renew or replace it in the License tab."
        ),
        "alert.track": "1",
        "alert.severity": "3",
        "alert_type": "number of events",
        "alert_comparator": "greater than",
        "alert_threshold": "0",
    }
    namespaced = _saved_search_url(APP_NAME)
    # Try create.
    try:
        rest.simpleRequest(
            namespaced, sessionKey=sys_token, method="POST", postargs=body
        )
        return
    except Exception:
        pass
    # Update path: POST against the existing entity. `name` is in the
    # URL; sending it in the body causes a 400.
    update = "{base}/{name}".format(base=namespaced, name=name)
    update_body = dict(body)
    update_body.pop("name", None)
    try:
        rest.simpleRequest(
            update, sessionKey=sys_token, method="POST", postargs=update_body
        )
    except Exception:
        # Last resort: delete and recreate.
        try:
            rest.simpleRequest(update, sessionKey=sys_token, method="DELETE")
        except Exception:
            pass
        rest.simpleRequest(
            namespaced, sessionKey=sys_token, method="POST", postargs=body
        )


# ---------- state assembly ----------------------------------------------

def _resolve_free_tier_owner(sys_token, effective_tier, user):
    """For a personal-tier (free) install, resolve the single-user owner.

    Binds the FIRST user to load a personal-tier install as the owner, then
    locks out everyone else (greyed in the UI) until a license is added. The
    owner row is NEVER deleted on downgrade — a re-licensed install simply
    stops locking; if it later downgrades again, the same owner is restored.

    Returns (owner_username_or_None, locked_bool).
    """
    if effective_tier != "personal":
        return None, False
    owner = (_kv_get(sys_token, FREE_OWNER_KV_KEY) or {}).get("owner")
    if not owner and user and user not in ("", "unknown"):
        owner = user
        try:
            _kv_put(sys_token, FREE_OWNER_KV_KEY, {
                "_key": FREE_OWNER_KV_KEY,
                "owner": owner,
                "bound_at": int(time.time()),
            })
        except Exception:
            pass  # best-effort; a transient write failure must not 500 the load
    locked = bool(owner) and (user or "") != owner
    return owner, locked


def free_tier_status(sys_token, user):
    """Public helper for OTHER handlers (the proxy) to enforce the
    single-user free-tier gate server-side. Returns
    {effective_tier, owner, locked}. `locked` is True when this is a
    personal-tier install and `user` is not the bound owner."""
    secret_raw = _load_secret(sys_token, LICENSE_SECRET_NAME)
    blob = None
    if secret_raw:
        try:
            blob = json.loads(secret_raw)
        except Exception:
            blob = None
    license_key_obj = (blob or {}).get("licenseKey") if isinstance(blob, dict) else None
    guid_state = get_environment_guid(sys_token)
    tier_state = resolve_tier(license_key_obj, current_guid=guid_state["guid"])
    eff = tier_state.get("effective_tier")
    owner, locked = _resolve_free_tier_owner(sys_token, eff, user)
    return {"effective_tier": eff, "owner": owner, "locked": locked}


def effective_tier(sys_token):
    """Resolve the current EFFECTIVE license tier server-side (authoritative).
    Fails safe to 'personal' (the most restrictive tier) on any error, so the
    feature gates built on this fail CLOSED. Reuses the same blob -> GUID ->
    resolve_tier path as _assemble_state()."""
    try:
        secret_raw = _load_secret(sys_token, LICENSE_SECRET_NAME)
        blob = json.loads(secret_raw) if secret_raw else None
    except Exception:
        blob = None
    license_key_obj = (blob or {}).get("licenseKey") if isinstance(blob, dict) else None
    try:
        guid_state = get_environment_guid(sys_token)
        tier_state = resolve_tier(license_key_obj, current_guid=guid_state.get("guid"))
        return tier_state.get("effective_tier") or "personal"
    except Exception:
        return "personal"


def capability_enabled(sys_token, cap):
    """Authoritative server-side per-feature licensing check for the REST
    handlers. True iff the current EFFECTIVE tier unlocks `cap` (see
    CAPABILITY_MIN_TIER in itmip_llm_license_tier). FAIL-CLOSED: any resolution
    error collapses to the personal tier, so paid features are denied on doubt.
    Spec: instructions/FEATURE_LICENSING_SPEC.md"""
    try:
        return bool(resolve_capabilities(effective_tier(sys_token)).get(cap, False))
    except Exception:
        return False


def _assemble_state(sys_token, user=None):
    """Return the front-end-friendly license state."""
    secret_raw = _load_secret(sys_token, LICENSE_SECRET_NAME)
    blob = None
    if secret_raw:
        try:
            blob = json.loads(secret_raw)
        except Exception:
            blob = None

    license_key_obj = (blob or {}).get("licenseKey") if isinstance(blob, dict) else None

    guid_state = get_environment_guid(sys_token)
    tier_state = resolve_tier(license_key_obj, current_guid=guid_state["guid"])

    recipients_doc = _kv_get(sys_token, RECIPIENT_KV_KEY) or {}
    recipients = recipients_doc.get("emails") or []

    free_owner, free_locked = _resolve_free_tier_owner(
        sys_token, tier_state.get("effective_tier"), user
    )

    eff_tier = tier_state.get("effective_tier")
    return {
        "license": tier_state,
        "guid": guid_state,
        "recipients": recipients,
        "has_license": bool(license_key_obj),
        "raw_present": bool(blob),
        # v1.3.0 — single-user free tier.
        "free_tier_owner": free_owner,
        "free_tier_locked": free_locked,
        # v1.4.1 — per-feature licensing, server-emitted so the frontend never
        # hard-codes the tier matrix. caps = scale/mechanic caps + derived
        # legacy booleans; capabilities = the full {capability: bool} feature
        # map. Spec: instructions/FEATURE_LICENSING_SPEC.md
        "caps": caps_for(eff_tier),
        "capabilities": resolve_capabilities(eff_tier),
        # v1.4.1 — configurable MSP header-badge text (white-label). The
        # frontend uses this only when badge == "msp".
        "msp_badge_label": _msp_badge_label(),
    }


# ---------- handler -------------------------------------------------------

class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "GET").upper()
            if not user_token(args):
                return err(401, "Not authenticated.")
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")
            caller = user_name(args)

            # ---- GET ----
            if method == "GET":
                return ok(_assemble_state(sys_token, caller))

            # Writes require admin.
            if method in ("POST", "DELETE") and not is_admin(args, rest):
                return err(403, "Admin role required.")

            # ---- DELETE ----
            if method == "DELETE":
                _delete_secret(sys_token, LICENSE_SECRET_NAME)
                _kv_delete(sys_token, LICENSE_KV_KEY)
                return ok(_assemble_state(sys_token, caller))

            if method != "POST":
                return err(405, "Only GET / POST / DELETE supported.")

            payload_raw = args.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw) if payload_raw else {}
            except Exception:
                return err(400, "Invalid JSON payload.")

            action = (payload.get("action") or "").lower()

            if action == "store":
                response = payload.get("cryptolens_response")
                if not isinstance(response, dict):
                    return err(
                        400,
                        "'cryptolens_response' must be the JSON dict from "
                        "Cryptolens.",
                    )
                if response.get("result") != 0:
                    return err(
                        400,
                        "Cryptolens returned an error: %s"
                        % response.get("message", "unknown"),
                    )
                license_key = response.get("licenseKey") or {}
                _store_secret(
                    sys_token, LICENSE_SECRET_NAME, json.dumps(response)
                )
                guid_state = get_environment_guid(sys_token, force=True)
                resolved = resolve_tier(
                    license_key, current_guid=guid_state["guid"]
                )
                _kv_put(
                    sys_token,
                    LICENSE_KV_KEY,
                    {
                        "key": license_key.get("key"),
                        "tier": resolved["tier"],
                        "effective_tier": resolved["effective_tier"],
                        "badge": resolved["badge"],
                        "expires_at": resolved["expires_at"],
                        "stored_at": int(__import__("time").time()),
                    },
                )
                return ok(_assemble_state(sys_token, caller))

            if action == "validate":
                response = payload.get("cryptolens_response")
                if not isinstance(response, dict):
                    blob_raw = _load_secret(sys_token, LICENSE_SECRET_NAME)
                    if not blob_raw:
                        return err(404, "No license stored to validate.")
                    try:
                        existing = json.loads(blob_raw)
                    except Exception:
                        return err(500, "Stored license blob is corrupt.")
                    key = (existing.get("licenseKey") or {}).get("key")
                    if not key:
                        return err(500, "Stored license has no key.")
                    guid_state = get_environment_guid(sys_token, force=True)
                    try:
                        response = cryptolens_activate(
                            key, guid_state["guid"]
                        )
                    except Exception as exc:
                        return err(502, "Cryptolens unreachable: %s" % exc)
                if response.get("result") != 0:
                    return err(400, "Cryptolens: %s" % response.get("message"))
                _store_secret(
                    sys_token, LICENSE_SECRET_NAME, json.dumps(response)
                )
                guid_state = get_environment_guid(sys_token, force=True)
                resolved = resolve_tier(
                    response.get("licenseKey") or {},
                    current_guid=guid_state["guid"],
                )
                _kv_put(
                    sys_token,
                    LICENSE_KV_KEY,
                    {
                        "key": (response.get("licenseKey") or {}).get("key"),
                        "tier": resolved["tier"],
                        "effective_tier": resolved["effective_tier"],
                        "badge": resolved["badge"],
                        "expires_at": resolved["expires_at"],
                        "stored_at": int(__import__("time").time()),
                    },
                )
                return ok(_assemble_state(sys_token, caller))

            if action == "recipients":
                emails = payload.get("emails")
                if not isinstance(emails, list):
                    return err(400, "'emails' must be an array of strings.")
                cleaned = []
                for e in emails:
                    if isinstance(e, str) and "@" in e and len(e) < 320:
                        cleaned.append(e.strip())
                _kv_put(
                    sys_token,
                    RECIPIENT_KV_KEY,
                    {
                        "emails": cleaned,
                        "updated_at": int(__import__("time").time()),
                    },
                )
                try:
                    _write_recipient_savedsearch(sys_token, cleaned)
                except Exception as exc:
                    return ok(
                        {
                            **_assemble_state(sys_token, caller),
                            "savedsearch_warning": str(exc),
                        }
                    )
                return ok(_assemble_state(sys_token, caller))

            return err(400, "Unknown action '%s'." % action)
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
