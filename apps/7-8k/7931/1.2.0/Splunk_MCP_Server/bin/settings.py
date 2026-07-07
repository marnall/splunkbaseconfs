"""
MCP Settings — singleton dataclass holding all application configuration.

This module defines the MCPSettings dataclass and its initialization phases:

- **Static**: Bundled JSON files loaded eagerly at process start.
- **Request-derived**: ``splunkd_url`` set from ``server.rest_uri`` on first request.
- **Conf**: ``.conf`` values read via Splunk REST API once a system service
  is available.

All parsing and file-loading utilities live in ``conf_util.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Optional, Set

from conf_util import (
    load_conf_into,
    load_generating_commands,
    load_safe_spl_config,
    set_conf_float,
    set_conf_int,
)
from constants import (
    CONF_KEY_DEFAULT_ROW_LIMIT,
    CONF_KEY_SAIA_TIMEOUT,
    CONF_KEY_TIMEOUT,
    DEFAULT_DEFAULT_ROW_LIMIT,
    DEFAULT_MAX_ROW_LIMIT,
    DEFAULT_SAIA_TIMEOUT,
    DEFAULT_TIMEOUT,
    SPLUNK_MCP_SERVER_APP,
    STANZA_SERVER,
)
from http_utils import extract_rest_uri
from logging_config import get_logger

logger = get_logger(__name__)

# Singleton storage
_singleton_instance: Optional["MCPSettings"] = None


def _reload_server_stanza(instance: "MCPSettings", session_key: str) -> None:
    """Reload guardrails-controlled fields from mcp.conf [server] on every request.

    Called on every MCPSettings.get(session_key) so that changes made via the
    guardrails handler (timeout, default_row_limit) are visible on the next tool
    invocation without a process restart.

    Only the [server] stanza is fetched — CUI settings, token lifetimes, and app
    metadata are written once at startup via load_splunk_conf() and never change
    at runtime. Rate limits are excluded because RateLimitManager reads them fresh
    on every tool invocation via its own ConfigFileManager call.

    ConfigFileManager is imported inside the function body to avoid a circular
    import: config_files_manager → splunk_api → settings → config_files_manager.
    """
    if not instance.splunkd_url:
        logger.debug("splunkd_url not set yet; skipping guardrails reload")
        return

    # Deferred to break the cyclic import:
    # config_files_manager → splunk_api → settings → config_files_manager
    from config_files_manager import ConfigFileManager  # noqa: PLC0415

    try:
        # One HTTP call to servicesNS/.../properties/mcp/server — returns the
        # fully merged conf (default/ + local/) for the [server] stanza.
        mgr = ConfigFileManager(session_key)
        server = mgr.get_stanza("mcp", STANZA_SERVER) or {}

        # Apply only the fields the guardrails handler can write.
        # set_conf_float/int are no-ops when the key is absent from the stanza,
        # so missing keys leave the existing instance values unchanged.
        set_conf_float(
            instance,
            server,
            CONF_KEY_TIMEOUT,
            CONF_KEY_TIMEOUT,
            min_val=0.0,
            min_inclusive=False,
        )
        set_conf_float(
            instance,
            server,
            CONF_KEY_SAIA_TIMEOUT,
            CONF_KEY_SAIA_TIMEOUT,
            min_val=0.0,
            min_inclusive=False,
        )
        set_conf_int(
            instance,
            server,
            CONF_KEY_DEFAULT_ROW_LIMIT,
            CONF_KEY_DEFAULT_ROW_LIMIT,
            min_val=1,
        )
        logger.info(
            "Guardrails reloaded — timeout=%.1f saia_timeout=%.1f default_row_limit=%d",
            instance.timeout,
            instance.saia_timeout,
            instance.default_row_limit,
        )
    except Exception:
        logger.exception(
            "Failed to reload guardrails conf from %s; keeping current values",
            instance.splunkd_url,
        )


@dataclass
class MCPSettings:
    """Application configuration for the MCP Splunk Server.

    Static: loaded eagerly from bundled JSON files.
    Request-derived: splunkd_url from server.rest_uri.
    Conf: loaded from mcp.conf/app.conf via Splunk REST API.
    """

    # ------------------------------------------------------------------
    # Static — loaded once at startup from bundled JSON files.
    # Populated by _load_static_config() via load_safe_spl_config() and
    # load_generating_commands() in conf_util.py.
    # Source files: default/safe_spl.json, default/generating_commands.json
    # ------------------------------------------------------------------
    safe_spl_commands: Set[str] = field(default_factory=set)
    generating_commands: Set[str] = field(default_factory=set)
    safe_spl_exclude_tools: Set[str] = field(default_factory=set)
    sub_search_arg_cmd: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Request-derived — extracted from the incoming REST request payload.
    # Updated by set_splunkd_url_from_request() on every request; only changes when
    # the value in request["server"]["rest_uri"] differs from current.
    # ------------------------------------------------------------------
    splunkd_url: Optional[str] = None

    # ------------------------------------------------------------------
    # Conf — read from mcp.conf [server] stanza and app.conf via Splunk
    # REST API.  Populated by load_splunk_conf() → load_conf_into() once a Splunk
    # service object is available.  Values below are safe defaults used
    # until load_splunk_conf() completes successfully.
    # ------------------------------------------------------------------

    # mcp.conf [server] timeout — HTTP timeout in seconds applied to all
    # outbound requests (splunkd REST API calls and JWKS fetches).
    timeout: float = DEFAULT_TIMEOUT

    # mcp.conf [server] saia_timeout — HTTP timeout in seconds used
    # for all Splunk AI Assistant API-backed tools.
    saia_timeout: float = DEFAULT_SAIA_TIMEOUT

    # app.conf [id] name
    app_name: str = SPLUNK_MCP_SERVER_APP

    # app.conf [id] version
    app_version: str = "1.2.0"

    # mcp.conf [server] max_row_limit
    max_row_limit: int = DEFAULT_MAX_ROW_LIMIT

    # mcp.conf [server] default_row_limit
    default_row_limit: int = DEFAULT_DEFAULT_ROW_LIMIT

    # mcp.conf [server] require_encrypted_token
    require_encrypted_token: bool = True

    # mcp.conf [server] legacy_token_grace_days (min: 0)
    legacy_token_grace_days: int = 180

    # mcp.conf [server] mcp_token_max_lifetime_seconds (must be positive)
    mcp_token_max_lifetime_seconds: int = 15552000  # 180 days

    # mcp.conf [server] mcp_token_default_lifetime_seconds (clamped to max)
    mcp_token_default_lifetime_seconds: int = 15552000

    # mcp.conf [server] token_key_reload_interval_seconds (min: 0.0)
    token_key_reload_interval_seconds: float = 0.0

    # CUI (Common User Interface) JWT validation settings
    # All read from mcp.conf [server] stanza via load_cui_settings()
    # mcp.conf [server] cui_enforce_jwt_validation
    cui_enforce_jwt_validation: bool = True

    # mcp.conf [server] cui_allowed_issuers (CSV, trailing slashes stripped)
    cui_allowed_issuers: Set[str] = field(default_factory=set)

    # mcp.conf [server] cui_allowed_audiences (CSV)
    cui_allowed_audiences: Set[str] = field(default_factory=set)

    # mcp.conf [server] cui_allowed_jwt_algs (CSV, uppercased; defaults to RS256)
    cui_allowed_jwt_algs: Set[str] = field(default_factory=lambda: {"RS256"})

    # mcp.conf [server] cui_jwks_by_issuer (JSON dict: issuer → JWKS URL)
    cui_jwks_by_issuer: Dict[str, str] = field(default_factory=dict)

    # mcp.conf [server] cui_jwt_clock_skew_seconds (min: 0)
    cui_jwt_clock_skew_seconds: int = 60

    # Tool collision detection threshold (not currently in .conf; hardcoded)
    jaccard_similarity_threshold: float = 0.8

    # ------------------------------------------------------------------
    # Internal class state
    # ------------------------------------------------------------------
    _conf_loaded: ClassVar[bool] = False

    # ==================================================================
    # Public API
    # ==================================================================

    @classmethod
    def get(cls, session_key: Optional[str] = None) -> "MCPSettings":
        """Get or create the singleton instance."""
        global _singleton_instance
        if _singleton_instance is None:
            _singleton_instance = cls._load_static_config()
        if session_key:
            _reload_server_stanza(_singleton_instance, session_key)
        return _singleton_instance

    @classmethod
    def set_splunkd_url_from_request(cls, request: Optional[Dict[str, Any]]) -> None:
        """Derive splunkd_url from server.rest_uri in the incoming request.

        Called on every request; only updates state when the URL changes.
        """
        if not request or not _singleton_instance:
            return

        rest_uri = extract_rest_uri(request)
        if not rest_uri:
            return

        splunkd_url = rest_uri.rstrip("/") + "/"
        if _singleton_instance.splunkd_url != splunkd_url:
            _singleton_instance.splunkd_url = splunkd_url
            logger.info("Updated splunkd_url to %s", splunkd_url)

    @classmethod
    def load_splunk_conf(cls, service: Any) -> None:
        """Read .conf settings via Splunk REST API (idempotent).

        Should be called once a system-level service is available.
        Subsequent calls are no-ops.
        """
        if cls._conf_loaded:
            return
        if service is None:
            logger.warning(
                "Cannot load .conf settings: Splunk service is not available"
            )
            return

        instance = cls.get()
        logger.info("Loading configuration from mcp.conf/app.conf via Splunk REST API")
        try:
            load_conf_into(instance, service)
            cls._conf_loaded = True
            logger.info("Configuration loaded successfully from Splunk .conf files")
        except Exception:
            logger.exception(
                "Failed to load .conf settings via Splunk REST API; using defaults"
            )

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset the singleton instance (testing only)."""
        global _singleton_instance
        _singleton_instance = None
        cls._conf_loaded = False

    # ==================================================================
    # Static — eager initialization from bundled JSON files
    # ==================================================================

    @classmethod
    def _load_static_config(cls) -> "MCPSettings":
        """Create singleton with static settings from bundled JSON files."""
        logger.info("Initializing static configuration from bundled JSON files")

        safe_spl_commands, safe_spl_exclude_tools, sub_search_arg_cmd = (
            load_safe_spl_config()
        )
        generating_commands = load_generating_commands()

        cls._conf_loaded = False
        return cls(
            safe_spl_commands=safe_spl_commands,
            generating_commands=generating_commands,
            safe_spl_exclude_tools=safe_spl_exclude_tools,
            sub_search_arg_cmd=sub_search_arg_cmd,
        )
