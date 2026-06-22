"""Shared loader + invoker for the customer-supplied IAM/SSO auth hook.

This module is used by both the LLM proxy (``itmip_llm_proxy.py``) and
the custom-tools dispatcher (``itmip_llm_custom_tools.py``) so that
ONE customer-edited ``bin/customer_authorisation.py`` (or
``local/bin/customer_authorisation.py``) can serve both flows. The
loader honours the same precedence in either caller, and the context
shape is documented in ``bin/customer_authorisation.py`` itself.

Public surface
--------------
- ``invoke(app_dir, context) -> (headers: dict, error: str | None)``
    Loads the hook, calls ``get_request_headers(context)``, validates
    the return is a ``dict[str, str]``. On any failure returns
    ``({}, error_str)`` so the caller can surface a clean error to the
    end user without exposing the traceback (which is still written to
    splunkd.log).
- ``resolve(app_dir) -> (path: str | None, module | None)``
    Path/module of whichever hook file exists, ``local/bin/`` first.
    Exposed so callers can detect "no hook installed" without paying
    the import cost twice.

Module-level state
------------------
None. We re-import on every call so that admins can iterate on
``local/bin/customer_authorisation.py`` without restarting splunkd.
If a customer needs token caching across calls, they put it inside
the hook module (a module-level cache is preserved as long as Python
keeps the module object alive between requests, which happens
because importlib.util.module_from_spec returns a fresh module each
time but the customer can also use a file-scoped cache keyed by
expiry time — see the example in customer_authorisation.py).
"""

import importlib.util
import os
import sys
import traceback


_HOOK_FILENAME = "customer_authorisation.py"


def _hook_paths(app_dir):
    """Return the lookup order. local/bin first, then bin."""
    return (
        os.path.join(app_dir, "local", "bin", _HOOK_FILENAME),
        os.path.join(app_dir, "bin", _HOOK_FILENAME),
    )


def resolve(app_dir):
    """Return (path, module) for the first hook file that exists.

    Loaded explicitly from path via importlib.util — no sys.modules
    pollution, so an upgrade that replaces bin/customer_authorisation.py
    doesn't leak the old module if local/bin/ ever stops shadowing.
    """
    for path in _hook_paths(app_dir):
        if not os.path.isfile(path):
            continue
        spec = importlib.util.spec_from_file_location(
            "customer_authorisation_runtime", path
        )
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return path, module
    return None, None


def invoke(app_dir, context):
    """Run the customer hook and return its headers dict.

    Parameters
    ----------
    app_dir : str
        Absolute path to the app root (e.g.
        ``$SPLUNK_HOME/etc/apps/itmip_ai_splunk_assistent_app``).
    context : dict
        Hook context. MUST include ``target_kind`` ("llm" or "tool").
        For LLM calls the additional keys are: ``llm_config``,
        ``splunk_session_key``, ``splunk_user``, ``body_preview``.
        For tool calls the additional keys are: ``tool_name``,
        ``tool_target_url``, ``tool_target_host``, ``tool_method``,
        plus the same ``splunk_session_key`` and ``splunk_user``.
        See ``bin/customer_authorisation.py`` docstring for the
        authoritative shape.

    Returns
    -------
    (headers, error)
        ``headers`` is a non-None ``dict[str, str]`` on success.
        ``error`` is ``None`` on success, or a one-line description
        of what went wrong. The caller turns a non-None error into
        a clean upstream error and refuses to make the outbound
        call (so an IAM-auth failure never silently degrades into
        an unauthenticated request).
    """
    try:
        path, module = resolve(app_dir)
    except Exception as exc:
        return {}, "Failed to load customer_authorisation hook: %s" % exc
    if not module:
        return {}, (
            "customer auth requested but neither "
            "local/bin/customer_authorisation.py nor "
            "bin/customer_authorisation.py exists."
        )

    fn = getattr(module, "get_request_headers", None)
    if not callable(fn):
        return {}, (
            "customer_authorisation.py at %s does not define a callable "
            "get_request_headers(context)." % path
        )

    try:
        result = fn(context)
    except Exception as exc:
        # Log the full traceback to splunkd.log so admins can debug.
        sys.stderr.write(
            "customer_authorisation hook raised: %s\n%s\n"
            % (exc, traceback.format_exc())
        )
        return {}, "customer_authorisation hook failed: %s" % exc

    if not isinstance(result, dict):
        return {}, (
            "customer_authorisation hook returned %s (expected dict[str,str])."
            % type(result).__name__
        )
    safe = {}
    for k, v in result.items():
        if not isinstance(k, str) or not isinstance(v, str):
            return {}, (
                "customer_authorisation hook returned a non-string header "
                "(%r=%r); refusing." % (k, v)
            )
        safe[k] = v
    return safe, None
