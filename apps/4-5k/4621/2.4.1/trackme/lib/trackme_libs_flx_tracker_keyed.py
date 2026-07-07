#!/usr/bin/env python
# coding=utf-8

"""FLX tracker-keyed field helpers.

TrackMe 2.3.12 introduced FLX concurrent-tracker support. Several fields that
previously stored a single payload per entity are now wrapped into a
tracker-keyed dict so multiple trackers can write to the same entity without
overwriting each other:

  object_description, status_description, status_description_short:
    legacy shape:        '{"indexes": "...", "last_event_time": 1234567, ...}'
                         (JSON-stringified scalar dict — keys are field names)
    2.3.12+ shape:       '{"<tracker_name>": "<inner JSON string>"}'
                         (root keys are tracker names; values are stringified
                         JSON payloads)

  metrics:
    legacy shape:        '{"metric_a": 1.0, "metric_b": 2}'  (keys=metric names)
    2.3.12+ shape:       '{"<tracker_name>": {"metric_a": 1.0, ...}}'
                         (root keys are tracker names; values are dicts of
                         scalar metrics)

Without a defensive filter, the merge logic in
``trackmepersistentfields.py`` (existing.copy(); merged.update(new)) unions
legacy root keys with the new tracker-keyed entry, leaving stale top-level
values frozen forever on entities that pre-date the 2.3.12 upgrade. The
``splk_hosts_tracking`` and ``cribl_edge_fleet_metrics`` use-case templates
read ``object_description`` back via ``spath`` and rely on
``last_event_time`` / ``last_ingest_time`` at the root — so legacy frozen
values "win" in ``stats first(last_event_time)``, producing entities stuck
at the upgrade timestamp.

The helpers below detect legacy-flat root keys and strip them before the
union merge, so the next cycle persists a clean tracker-keyed-only shape
(self-healing — no schema migration required).

Fields that store a single scalar at the top level (``status``,
``max_sec_inactive``, ``disruption_min_time_sec``) are NOT affected:
legacy storage was a scalar, not a nested dict, so no root-key
contamination is possible.
"""

import json


def looks_like_stringified_json_object(value):
    """Return True if ``value`` is a string that JSON-parses to a dict/list.

    Used to discriminate tracker-keyed root values (each holding a per-tracker
    JSON payload stored as a string) from legacy flat root keys (which hold
    plain scalars such as numbers, simple identifiers like ``"linux_secure"``,
    timestamps, etc.).
    """
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not (s.startswith("{") or s.startswith("[")):
        return False
    try:
        parsed = json.loads(s)
    except (json.JSONDecodeError, ValueError, TypeError):
        return False
    return isinstance(parsed, (dict, list))


def strip_legacy_flat_keys(field_name, parsed):
    """Drop pre-2.3.12 root keys from a parsed tracker-keyed field.

    ``field_name`` selects the per-field discriminator:

      object_description / status_description / status_description_short:
        tracker-keyed root values are JSON-stringified objects. Legacy root
        values are plain scalars (numbers, simple strings) — easy to filter
        with :func:`looks_like_stringified_json_object`.

      metrics:
        tracker-keyed root values are dicts of scalar metrics. Legacy root
        values are scalars (the metric value itself). Filter by value type.

    For any other field, return ``parsed`` unchanged (no contamination risk).
    """
    if not isinstance(parsed, dict):
        return parsed

    if field_name in (
        "object_description",
        "status_description",
        "status_description_short",
    ):
        return {
            k: v for k, v in parsed.items()
            if looks_like_stringified_json_object(v)
        }

    if field_name == "metrics":
        return {
            k: v for k, v in parsed.items()
            if isinstance(v, dict) and all(
                isinstance(inner, (int, float, str, bool)) or inner is None
                for inner in v.values()
            )
        }

    return parsed


# Sentinel returned by ``strip_legacy_flat_keys_from_raw`` when the parsed
# value is a dict that ends up empty after stripping. Callers should drop
# the field rather than persist ``"{}"``.
DROP_FIELD = object()


def strip_legacy_flat_keys_from_raw(field_name, raw_value):
    """Strip legacy flat keys from a *raw* KV string and re-serialize.

    Convenience wrapper around :func:`strip_legacy_flat_keys` for the merge
    fallback branches in ``trackmepersistentfields.py`` that previously wrote
    ``existing_record.get("<field>")`` back to the record verbatim — which
    re-introduced the legacy contamination that the in-merge strip had just
    cleaned (bugbot finding on PR #1686, commit 24e3cdb).

    Behaviour:

    - Non-string, empty, or whitespace-only input → returned unchanged
      (the merge logic already handles those falsy cases separately).
    - JSON parse failure → return the raw value unchanged (legacy
      non-JSON shapes pass through harmlessly — same fail-open behaviour
      as the in-merge strip).
    - Non-dict parsed value → return unchanged (no contamination risk for
      arrays / scalars at the root).
    - Dict parsed + stripped to empty → return :data:`DROP_FIELD` sentinel
      so the caller can ``record.pop("<field>", None)`` instead of
      persisting ``"{}"``.
    - Otherwise → return ``json.dumps(stripped_dict)``.
    """
    if not isinstance(raw_value, str) or not raw_value.strip():
        return raw_value
    try:
        parsed = json.loads(raw_value)
    except (json.JSONDecodeError, ValueError, TypeError):
        return raw_value
    if not isinstance(parsed, dict):
        return raw_value
    stripped = strip_legacy_flat_keys(field_name, parsed)
    if not stripped:
        return DROP_FIELD
    return json.dumps(stripped)
