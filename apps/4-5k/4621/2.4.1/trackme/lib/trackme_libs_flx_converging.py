"""Shared helpers for FLX converging trackers.

A converging tracker's editable configuration is not stored as discrete
fields — it lives embedded inside the ``| trackmesplkflxconverging ...``
command string that the creation wizard builds client-side and the backend
persists verbatim in two places:

  * the wrapper saved search SPL
    (``trackme_flx_hybrid_<name>_wrapper_tenant_<tid>``), and
  * the KV registry ``kv_trackme_flx_hybrid_trackers_tenant_<tid>`` under
    ``knowledge_objects.properties[0].root_constraint`` (the canonical,
    un-mutated copy — prefer this for re-hydration).

These helpers are the single source of truth for round-tripping that command
string into structured fields (``parse_converging_command``) and back
(``build_converging_command``). They MUST mirror the client-side builder in
``splunkui/packages/tenant-home/src/components/SplkFlxHybridTrackersConvergingWizard.tsx``
so a tracker modified in-place behaves identically to a freshly-created one.

Tested in ``unit_tests/check_flx_converging_spl_roundtrip.py``.
"""

import re

# Default object_description the wizard always sends for converging trackers.
DEFAULT_OBJECT_DESCRIPTION = "Flex converging tracker"


def build_converging_command(
    tenants_scope,
    object_name,
    group,
    root_constraint="",
    consider_orange_as_up=True,
    min_pct_for_green=100,
    object_description=DEFAULT_OBJECT_DESCRIPTION,
    remove_extra_attributes=False,
):
    """Build the ``| trackmesplkflxconverging ...`` command string.

    Mirrors the client-side builder byte-for-byte (live variant). The inner
    ``root_constraint`` filter is embedded as a double-quoted argument with
    its own double quotes escaped as ``\\"`` — exactly as the wizard does via
    ``(rootConstraint||'').replace(/"/g, '\\"')``.

    When ``remove_extra_attributes`` is True the ``remove_extra_attributes``
    flag is appended (simulation variant — keeps the member breakdown out of
    the results for readability); live/persisted commands omit it.
    """
    inner = (root_constraint or "").replace('"', '\\"')
    rc = f' root_constraint="{inner}"' if inner else ""
    rea = ' remove_extra_attributes="True"' if remove_extra_attributes else ""
    orange = "True" if _coerce_bool(consider_orange_as_up) else "False"
    try:
        min_green = int(min_pct_for_green)
    except (TypeError, ValueError):
        min_green = 100
    return (
        f'| trackmesplkflxconverging tenants_scope="{tenants_scope}" '
        f'object="{object_name}" object_description="{object_description}" '
        f'group="{group}"{rc} consider_orange_as_up={orange}{rea} '
        f'min_pct_for_green={min_green}\n'
        f'| eval max_sec_inactive=3600'
    )


def parse_converging_command(cmd):
    """Parse a converging command string into structured fields.

    Returns a dict with: tenants_scope, object, object_description, group,
    root_constraint (inner filter, unescaped), consider_orange_as_up (bool),
    min_pct_for_green (int). Missing args come back as sensible defaults
    (empty string / True / 100) — the parser never raises on malformed input.
    """
    cmd = cmd or ""
    return {
        "tenants_scope": _extract_quoted(cmd, "tenants_scope") or "",
        "object": _extract_quoted(cmd, "object") or "",
        "object_description": _extract_quoted(cmd, "object_description")
        or DEFAULT_OBJECT_DESCRIPTION,
        "group": _extract_group(cmd),
        # root_constraint is stored with escaped quotes — unescape for editing.
        "root_constraint": _unescape(_extract_quoted(cmd, "root_constraint") or ""),
        "consider_orange_as_up": _extract_bool(cmd, "consider_orange_as_up", True),
        "min_pct_for_green": _extract_int(cmd, "min_pct_for_green", 100),
    }


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def _extract_quoted(cmd, key):
    """Return the raw inner of ``key="..."`` honoring ``\\"`` escapes.

    The returned value keeps escape sequences as-is; callers unescape when
    the value can itself contain quotes (root_constraint).
    """
    m = re.search(rf'(?:^|\s){re.escape(key)}="((?:\\.|[^"\\])*)"', cmd)
    return m.group(1) if m else None


def _extract_group(cmd):
    """Extract the group token.

    Converging trackers built by the wizard always quote the group
    (``group="01-Service-Availability"``), but be defensive: if it is not
    quoted (a bare eval expression, as use_case trackers may carry), capture
    the raw token up to the next ``<key>=`` boundary or a pipe.
    """
    quoted = _extract_quoted(cmd, "group")
    if quoted is not None:
        return _unescape(quoted)
    m = re.search(
        r'(?:^|\s)group=(.+?)(?=\s+\w+=|\s*\||$)',
        cmd,
        re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _extract_bool(cmd, key, default):
    m = re.search(rf'(?:^|\s){re.escape(key)}=(True|False)\b', cmd, re.IGNORECASE)
    if not m:
        return default
    return m.group(1).lower() == "true"


def _extract_int(cmd, key, default):
    m = re.search(rf'(?:^|\s){re.escape(key)}=(\d+)', cmd)
    if not m:
        return default
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return default


def _unescape(value):
    return (value or "").replace('\\"', '"')
