#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

"""
Pure helpers for the DHM per-host blocklist feature.

Kept dependency-free (only stdlib) so it can be imported and exercised
by unit tests without standing up a Splunk environment. The REST handler
(``trackme_rest_handler_splk_dhm_power.py``) and the streaming custom
command (``trackmedhmpipeline.py``) both share the same wildcard
semantics through this module.
"""

import ast
import fnmatch
import json


def parse_dhm_summary_value(value):
    """Parse a stored ``splk_dhm_st_summary`` value into a dict.

    Mirrors the JSON-first, ``ast.literal_eval``-fallback parsing that
    ``trackmedhmpipeline.TrackMeDhmPipeline._parse_dict`` uses on the read
    side — pre-migration records can still be serialised as a Python
    literal repr ``"{'idx': 'foo', ...}"`` instead of JSON
    ``'{"idx": "foo", ...}'``, and the REST-handler cleanup must honour
    both so it isn't silently a no-op on legacy data.

    Accepts ``None``, an empty string, a dict (returned unchanged), or a
    string in either format. Anything else, or a parse failure on a
    non-empty string, returns ``{}`` — callers treat that as "no combos
    to filter" rather than crashing the user's save request.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    stripped = value.strip()
    if not stripped:
        return {}
    # JSON first — the canonical on-disk format for new writes.
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError, TypeError):
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    # Legacy Python-literal repr — what trackmedhmpipeline used to write.
    try:
        parsed = ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError, TypeError):
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def matches_any_pattern(value, patterns):
    """Return True if ``value`` matches at least one fnmatch pattern in
    ``patterns``. Empty pattern list short-circuits to False so the caller
    does not have to special-case the "no blocklist" path.
    """
    if not patterns:
        return False
    return any(fnmatch.fnmatchcase(value, p) for p in patterns)


def filter_dhm_summary_by_blocklists(summary_dict, idx_patterns, st_patterns):
    """Filter a stored ``splk_dhm_st_summary`` dict against blocklist patterns.

    The stored dict shape is ``{combo_id: {"idx": str, "st": str, ...}}``.
    The ``summary_idx`` / ``summary_st`` keys that appear in the inspect
    view are a *display* renaming applied by the read REST handler
    (``trackme_rest_handler_component_user.py``) when it builds the _full
    view — the on-disk dict still uses the short keys. Cleanup logic must
    read the short keys.

    Returns a 4-tuple ``(filtered, removed_count, remaining_indexes,
    remaining_sourcetypes)``:

    - ``filtered``: the same dict shape with matching combos removed
    - ``removed_count``: number of combos removed (zero is a no-op)
    - ``remaining_indexes``, ``remaining_sourcetypes``: ``set[str]`` of the
      surviving values, suitable for rebuilding the comma-separated
      ``data_index`` / ``data_sourcetype`` display fields. **Only populated
      when ``removed_count > 0``**; both are empty sets on a no-op so the
      caller can short-circuit on ``removed_count == 0`` without having to
      double-check the rebuild strings.

    The function is a no-op (returns ``summary_dict`` unchanged with
    ``removed_count=0`` and empty sets) when:

    - both pattern lists are empty
    - the input is not a dict, is empty, or contains no dict-shaped values
    - no combo matches any pattern

    Non-dict entries are passed through unmodified — they are not expected
    in real data, but a defensive pass-through avoids losing data on
    schema drift.
    """
    if not idx_patterns and not st_patterns:
        return summary_dict, 0, set(), set()
    if not isinstance(summary_dict, dict) or not summary_dict:
        return summary_dict, 0, set(), set()

    filtered = {}
    remaining_indexes = set()
    remaining_sourcetypes = set()
    for combo_id, entry in summary_dict.items():
        if not isinstance(entry, dict):
            filtered[combo_id] = entry
            continue
        idx_val = str(entry.get("idx", "") or "")
        st_val = str(entry.get("st", "") or "")
        if matches_any_pattern(idx_val, idx_patterns):
            continue
        if matches_any_pattern(st_val, st_patterns):
            continue
        filtered[combo_id] = entry
        if idx_val:
            remaining_indexes.add(idx_val)
        if st_val:
            remaining_sourcetypes.add(st_val)

    removed = len(summary_dict) - len(filtered)
    # Uniform contract: the surviving sets are only meaningful to the caller
    # when removed > 0 (so it can rebuild data_index / data_sourcetype). When
    # nothing was removed, return empty sets so callers can short-circuit on
    # ``removed == 0`` without having to also check whether the rebuild
    # strings would be identical to the pre-existing ones.
    if removed <= 0:
        return summary_dict, 0, set(), set()
    return filtered, removed, remaining_indexes, remaining_sourcetypes
