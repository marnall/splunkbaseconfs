"""Customer authorisation hook for outbound LLM requests.

When an LLM endpoint sits behind a corporate IAM / SSO gateway
(WebEAM.Next, Ping, Okta, AzureAD, internal SAML, etc.), the Splunk
proxy needs to attach fresh auth headers to every outbound call. Static
`extra_headers` on the LlmConfig is fine for constants like
`X-Tenant-Id: foo` but cannot run code or refresh short-lived tokens.

This file is the customer-supplied hook. Edit ``get_request_headers`` to
perform whatever login/refresh dance your gateway requires and return a
dict of HTTP headers — the proxy merges them into the outbound LLM
request right before forwarding.

============================================================================
WHEN IT RUNS
============================================================================
This hook serves TWO flows:

1. **LLM proxy** — when an LLM configuration has
   ``customer_auth_enabled = true`` AND ``call_mode = splunk_proxy``.
   The proxy calls the hook once per outbound LLM request and merges
   the returned headers onto the upstream call.

2. **Custom tool dispatcher** — when a custom tool definition has
   ``implementation.customer_auth = true``. The /invoke handler calls
   the hook once per tool invocation and merges the returned headers
   onto the outbound HTTP request to the tool's target. This is the
   path used for IAM-fronted ServiceNow / Confluence / internal-API
   targets.

Distinguish the two flows via ``context["target_kind"]`` (``"llm"`` or
``"tool"``). A customer with ONE gateway for both can ignore the
discriminator and return the same headers; a customer with separate
gateways (or one flow that needs no auth) branches on it.

The hook does NOT cache anything for you — if your tokens are
expensive to mint, cache them inside this module (see the example
below). The module-level cache persists across requests within the
splunkd process.

============================================================================
UPGRADE GUIDANCE
============================================================================
The default install ships this file under ``bin/``. The proxy prefers a
copy at ``local/bin/customer_authorisation.py`` when present. The
recommended workflow is:

    1. Copy this file:
       cp $SPLUNK_HOME/etc/apps/itmip_ai_splunk_assistent_app/bin/customer_authorisation.py \\
          $SPLUNK_HOME/etc/apps/itmip_ai_splunk_assistent_app/local/bin/customer_authorisation.py
    2. Edit the LOCAL copy.
    3. Restart splunkd.

``local/`` is never overwritten on app upgrades, so your edits survive.

============================================================================
SECURITY MODEL
============================================================================
- Runs in the splunkd Python process, as the splunkd user. Has full
  stdlib access (urllib, ssl, http.client) and full Splunk REST access
  via ``splunk.rest.simpleRequest``.
- Customer-trusted code: nothing in this file is sandboxed. Treat it
  like any other splunkd extension.
- Store credentials in Splunk's ``storage/passwords`` (encrypted at rest)
  and read them inside the hook. Never put cleartext credentials in this
  file.
- Don't log secret values. Use ``logger.info(...)`` for non-sensitive
  audit lines if you need them.

============================================================================
THE FUNCTION CONTRACT
============================================================================
``get_request_headers(context: dict) -> dict[str, str]``

Input ``context`` keys — ALWAYS present:
    target_kind        str  — ``"llm"`` or ``"tool"``. Use this to
                              branch when LLM and tool flows need
                              different gateways or token scopes.
    splunk_user        str  — the calling Splunk user name.
    splunk_session_key str  — the user's Splunk session key (may be
                              empty in tool flow; see below).

Additional keys when ``target_kind == "llm"``:
    llm_config        dict  — the LLM configuration record. Useful
                              keys: name, endpoint, provider_kind,
                              model, org_short, bu_short.
    body_preview       str  — first ~256 chars of the outbound LLM
                              request body (so you can route auth on
                              e.g. system-prompt content).

Additional keys when ``target_kind == "tool"``:
    tool_name          str  — the custom tool's name (from its
                              KVStore definition).
    tool_target_url    str  — the fully resolved outbound URL (after
                              ``{{ }}`` parameter substitution).
    tool_target_host   str  — host extracted from tool_target_url.
    tool_method        str  — ``"GET"``/``"POST"``/etc.
    (splunk_session_key is "" — the tool dispatcher already
    authenticated the caller and does not forward the session key.
    Hooks that need to read storage/passwords from the tool flow
    can fetch a system token via splunk.rest directly.)

Return value:
    A dict mapping header name (str) -> header value (str). Both must
    be strings. Empty dict = "no extra headers, but proceed". Non-
    string values cause the proxy / dispatcher to refuse the request.

Error semantics:
    Raise any exception to abort the request. The proxy returns 502
    to the browser with ``{"error": "customer_auth hook failed:
    <msg>"}``; the tool dispatcher returns ``{ok: false, error:
    "customer_auth hook failed: <msg>"}`` to the LLM. Either way the
    upstream call is NEVER made unauthenticated. The traceback is
    written to splunkd.log.

============================================================================
ILLUSTRATIVE WEBEAM.NEXT EXAMPLE (paste-in starting point)
============================================================================

The example below is intentionally fictional — every customer's
WebEAM.Next deployment uses slightly different field names and flow
steps. Adapt to your environment.

    import json
    import time
    import urllib.request
    import urllib.parse

    import splunk.rest as rest

    _TOKEN_CACHE = {}            # name -> (token, expires_epoch)
    _CACHE_TTL_SEC = 55 * 60     # refresh 5 min before expiry


    def _load_credentials(session_key):
        \"\"\"Read WebEAM creds out of storage/passwords.\"\"\"
        path = (
            "/servicesNS/nobody/itmip_ai_splunk_assistent_app/"
            "storage/passwords/itmip_llm_assistent_app%3Awebeam_login%3A"
            "?output_mode=json"
        )
        resp, content = rest.simpleRequest(
            path, sessionKey=session_key, method="GET"
        )
        if resp.status != 200:
            raise RuntimeError("WebEAM creds missing in storage/passwords")
        data = json.loads(content)["entry"][0]["content"]
        # `clear_password` is "<username>:<password>" by convention.
        u, _, p = data["clear_password"].partition(":")
        return u, p


    def _fetch_token(session_key):
        username, password = _load_credentials(session_key)
        body = json.dumps({
            "username": username,
            "password": password,
            "clientId": "splunk-ai-assistent",
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://webeam.example.com/api/v2/login",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
        return payload["access_token"], int(time.time()) + _CACHE_TTL_SEC


    def get_request_headers(context):
        target_kind = context.get("target_kind", "llm")

        if target_kind == "llm":
            cfg = context["llm_config"]
            # Skip configs that don't go through WebEAM (route by
            # endpoint host, provider_kind, name — whatever fits).
            if "webeam" not in cfg.get("endpoint", "").lower():
                return {}
            cache_key = "llm:" + (cfg.get("name") or "default")
            session_key = context.get("splunk_session_key", "")

        elif target_kind == "tool":
            target_host = context.get("tool_target_host", "")
            # Only intercept tools that hit WebEAM-fronted hosts.
            if "webeam" not in target_host.lower():
                return {}
            cache_key = "tool:" + target_host
            # Tool flow doesn't get the session key; mint via system
            # token if your token endpoint needs Splunk creds.
            session_key = ""

        else:
            return {}

        cached = _TOKEN_CACHE.get(cache_key)
        now = int(time.time())
        if not cached or cached[1] < now:
            token, expires = _fetch_token(session_key)
            _TOKEN_CACHE[cache_key] = (token, expires)
        else:
            token = cached[0]

        return {
            "Authorization": "Bearer " + token,
            "X-WebEAM-User": context["splunk_user"],
        }

============================================================================
TESTING LOCALLY
============================================================================

Run this file directly with Splunk's bundled Python — it ships with a
``__main__`` block that calls the hook with a stub context and prints
the result:

    $SPLUNK_HOME/bin/splunk cmd python \\
        $SPLUNK_HOME/etc/apps/itmip_ai_splunk_assistent_app/bin/customer_authorisation.py

You should see an empty dict from the default no-op implementation.
After you paste in your real flow, re-run and inspect what headers come
out.
"""


def get_request_headers(context):
    """Return HTTP headers to attach to the outbound LLM request.

    See the module docstring for the full contract. The default
    implementation is a no-op — replace it with your IAM/SSO flow.
    """
    # No-op by default. Customers paste their flow above and replace
    # this `return {}` with the appropriate logic.
    return {}


if __name__ == "__main__":
    # Smoke-test from the CLI. Prints whatever the hook returns for
    # both flows so you can iterate without involving Splunk Web.
    llm_stub = {
        "target_kind": "llm",
        "llm_config": {
            "name": "DFLT_DFLT_anthropic_central",
            "endpoint": "https://api.example.com/v1/messages",
            "provider_kind": "anthropic",
            "model": "claude-sonnet-4-6",
            "org_short": "DFLT",
            "bu_short": "DFLT",
        },
        "splunk_session_key": "<paste-a-real-session-key-for-live-tests>",
        "splunk_user": "admin",
        "body_preview": '{"messages":[{"role":"user","content":"hi"}]}',
    }
    tool_stub = {
        "target_kind": "tool",
        "tool_name": "servicenow_create_incident",
        "tool_target_url": "https://servicenow.example.com/api/now/table/incident",
        "tool_target_host": "servicenow.example.com",
        "tool_method": "POST",
        "splunk_session_key": "",
        "splunk_user": "admin",
    }
    print("LLM flow ->", get_request_headers(llm_stub))
    print("Tool flow ->", get_request_headers(tool_stub))
