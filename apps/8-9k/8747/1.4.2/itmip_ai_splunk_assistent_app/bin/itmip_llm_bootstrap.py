"""GET /services/itmip_llm/session_bootstrap

Single server-authoritative bootstrap for the React shell. Returns, for
the *calling* user (resolved from their own token — never client-claimed):

  - tenant            resolved Org / BU (server port of tenancy.ts)
  - is_admin          admin/splunk_admin?
  - user              caller username
  - llm_configs       the configs this user may choose, SECRETS STRIPPED
  - tool_assignments  assignment rows scoped to this user's tenant
  - tool_overrides    global tool-metadata overrides

This is the read-side counterpart to the F1 server-side tenant
resolution. It lets the frontend stop reading itmip_organisations /
itmip_business_units / itmip_llm_configs / itmip_tool_assignments /
itmip_tool_overrides directly from KVStore, so those collections can be
locked to admin-only at the ACL (see docs/Analysis Findings.md §2.3).

The endpoint is purely additive — no existing code calls it yet, so it
cannot break the running app. The frontend rewiring + ACL tightening are
the follow-up steps.

Query params:
  app=<host app id>   non-authoritative context hint for app_patterns
                      matching (role_patterns is the real gate).
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
    kv_list,
    ok,
    owns_personal_config,
    resolve_caller_tenant,
    system_token,
    user_name,
    user_roles,
    user_token,
)

LLM_CONFIG_COLLECTION = "itmip_llm_configs"
TOOL_ASSIGN_COLLECTION = "itmip_tool_assignments"
TOOL_OVERRIDE_COLLECTION = "itmip_tool_overrides"

# Fields safe to advertise to any authenticated user for the model
# dropdown. Deliberately EXCLUDES credential material:
# aws_access_key_id, aws_role_arn, tls_ca_pem, extra_headers (may carry
# internal gateway tokens), and the authz-internal extra_role_patterns /
# extra_user_names. Those are resolved server-side by the proxy and must
# never reach a non-admin browser.
_CONFIG_PUBLIC_FIELDS = (
    "_key",
    "name",
    "provider_kind",
    "scope",
    "org_short",
    "bu_short",
    "endpoint",
    "model",
    "request_timeout_ms",
    "call_mode",
    "browser_proxy",
    "azure_api_version",
    "aws_region",
    "customer_auth_enabled",
    "confirm_external",
    "confirm_external_message",
    "disable_style_profiles",
    "created_at",
    "updated_at",
)


def _parse_query(args):
    """Splunk passes query as a list of [key, value] pairs."""
    out = {}
    for pair in args.get("query") or []:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            out[str(pair[0])] = pair[1]
    return out


def _config_visible(cfg, user, roles, admin, org_short, bu_short):
    """Server port of the live Ask-tab dropdown filter
    (configs.ts::listLlmConfigsForUser), fed the SERVER-resolved Org/BU —
    never a client-claimed one. The owner sees their own personal config
    (B2), and ownership is an exact owner_user / name-token match, never a
    substring (B3). `admin` is unused — like the client filter, the dropdown
    is tenant-scoped for everyone (admin-sees-all belongs to the proxy
    gate, is_user_allowed_for_llm_config)."""
    c_org = (cfg.get("org_short") or "DFLT").upper()
    c_bu = (cfg.get("bu_short") or "DFLT").upper()
    org_u = (org_short or "").upper()
    bu_u = (bu_short or "").upper()
    if c_org != org_u and c_org != "DFLT":
        return False
    if c_bu != "DFLT" and c_bu != bu_u:
        return False
    extra_users = cfg.get("extra_user_names")
    if isinstance(extra_users, list) and user in extra_users:
        return True
    extra_roles = cfg.get("extra_role_patterns")
    if isinstance(extra_roles, list) and extra_roles:
        if any(r in extra_roles for r in roles):
            return True
    if (cfg.get("scope") or "central").lower() == "personal":
        return owns_personal_config(user, cfg)
    return True


def _assignment_in_tenant(a, org_short, bu_short):
    a_org = (a.get("org_short") or "*").upper()
    a_bu = (a.get("bu_short") or "*").upper()
    org_u = (org_short or "").upper()
    bu_u = (bu_short or "").upper()
    return (a_org == org_u or a_org == "*") and (a_bu == bu_u or a_bu == "*")


class Handler(application.PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(Handler, self).__init__()

    def handle(self, in_string):
        try:
            args = json.loads(in_string)
            method = (args.get("method") or "GET").upper()
            if method != "GET":
                return err(405, "Only GET is supported.")
            if not user_token(args):
                return err(401, "Not authenticated.")
            sys_token = system_token(args)
            if not sys_token:
                return err(503, "System auth token not provided.")

            query = _parse_query(args)
            app = query.get("app") or APP_NAME

            user = user_name(args)
            roles = user_roles(args, rest)
            lower = {str(r).lower() for r in roles}
            admin = ("admin" in lower) or ("splunk_admin" in lower)

            tenant = resolve_caller_tenant(
                args, rest, sys_token, url_app=app, roles=roles, is_admin_flag=admin
            )
            org_short = tenant["org_short"]
            bu_short = tenant["bu_short"]

            # LLM configs — filtered to the caller's tenant + grants, then
            # stripped of credential material.
            configs = []
            for cfg in kv_list(rest, sys_token, LLM_CONFIG_COLLECTION):
                if _config_visible(cfg, user, roles, admin, org_short, bu_short):
                    configs.append(
                        {k: cfg.get(k) for k in _CONFIG_PUBLIC_FIELDS if k in cfg}
                    )

            # Tool assignments — only rows that apply to this tenant.
            assignments = [
                {
                    "tool_name": a.get("tool_name") or "",
                    "org_short": (a.get("org_short") or "*"),
                    "bu_short": (a.get("bu_short") or "*"),
                    "enabled": a.get("enabled") is not False,
                }
                for a in kv_list(rest, sys_token, TOOL_ASSIGN_COLLECTION)
                if _assignment_in_tenant(a, org_short, bu_short)
            ]

            # Tool overrides — global metadata relabels, returned whole.
            overrides = []
            for o in kv_list(rest, sys_token, TOOL_OVERRIDE_COLLECTION):
                tags = o.get("tags")
                cats = o.get("categories")
                overrides.append(
                    {
                        "_key": o.get("_key") or "",
                        "tool_name": o.get("tool_name") or "",
                        "tags": tags if isinstance(tags, list) else None,
                        "categories": cats if isinstance(cats, list) else None,
                        "short_description": o.get("short_description"),
                        "short_description_concise": o.get("short_description_concise"),
                    }
                )

            return ok(
                {
                    "tenant": tenant,
                    "is_admin": admin,
                    "user": user,
                    "llm_configs": configs,
                    "tool_assignments": assignments,
                    "tool_overrides": overrides,
                }
            )
        except Exception as exc:
            return err(500, "Internal error: %s" % exc)

    def handleStream(self, *_args, **_kwargs):
        raise NotImplementedError()

    def done(self):
        pass
