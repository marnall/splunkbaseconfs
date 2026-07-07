"""
TrackMe AI Advisors — Pydantic compatibility shim.

``pydantic 2.x`` depends on the native ``pydantic_core`` extension.  In
this repository ``pydantic_core`` only ships in the Python 3.13 wheel
set (``lib/3rdparty/linux_with_deps_313/``) because the rest of the AI
Agent stack — ``splunklib.ai``, langchain, langgraph — requires Python
3.13+.  On Python 3.9 (Splunk 9.x default) a plain top-level
``from pydantic import ...`` raises ``ImportError`` and crashes the
persistent EAI handler process at module load, taking down every UCC
``admin_external`` endpoint (``trackme_vtenants``, ``trackme_settings``,
``trackme_account``, ``trackme_emails``, ``trackme_ai_provider``) in
the app — a blast radius far wider than just "AI Agent unavailable".

This module is the single, canonical entry point for the six advisor
libraries (``trackme_libs_ai_agents``, ``trackme_libs_ai_component_health``,
``trackme_libs_ai_concierge_advisor``, ``trackme_libs_ai_feed_lifecycle``,
``trackme_libs_ai_flx_threshold``, ``trackme_libs_ai_fqm_advisor``) and
for any future advisor lib.  Each advisor lib should import its
pydantic primitives from here:

    from trackme_libs_pydantic_compat import BaseModel, Field

On Python 3.13 the real ``pydantic.BaseModel`` / ``pydantic.Field`` are
re-exported unchanged.  On Python 3.9 we fall back to no-op stubs:
schema subclasses still *define* at module load (so ``class
MLAdvisorResult(BaseModel): ...`` etc. doesn't raise), but they are
never *instantiated* on 3.9 — the deferred ``from splunklib.ai.*
import ...`` calls inside each advisor's ``_run_<advisor>_agent``
entry point already raise a clean "AI SDK requires Python 3.13"
error before any code path that would build a ``BaseModel`` instance
runs, and the UI's pre-flight Python-version refusal blocks
invocation entirely.
"""

try:
    from pydantic import BaseModel, Field
except ImportError:  # Python 3.9 fallback — see module docstring.

    class BaseModel:  # type: ignore[no-redef]
        """No-op stub used when pydantic is unavailable (Python 3.9)."""

    def Field(*args, **kwargs):  # type: ignore[no-redef]
        return None


__all__ = ["BaseModel", "Field"]
