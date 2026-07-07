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

import os
import re
import sys
import time
import json
from datetime import datetime as _dt

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))

# Relative-offset grammar accepted by resolve_maintenance_epoch. Unlike the
# outliers' parse_user_datetime (which only accepts PAST offsets like "-30d"
# because training windows look backwards), maintenance windows look FORWARD,
# so we accept a leading "+" and a bare "+N" (seconds). The unit is optional;
# absent unit means seconds.
_MAINTENANCE_REL_RE = re.compile(r"^([+-])(\d+)([smhdw]?)$", re.IGNORECASE)
_MAINTENANCE_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def resolve_maintenance_epoch(value, now=None):
    """Resolve a user / LLM-supplied time spec into an integer epoch (seconds).

    Accepted forms (case-insensitive for the unit / "now"):
      - epoch seconds, int or string: ``1769644800`` / ``"1769644800"``
      - the literal ``"now"``
      - a relative offset from now: ``"+30m"``, ``"+2h"``, ``"+1d"``, ``"-1h"``,
        or a bare-seconds offset ``"+86400"`` / ``"+1800"`` (no unit = seconds)
      - ISO datetime: ``"YYYY-MM-DD"`` / ``"YYYY-MM-DDTHH:MM"`` /
        ``"YYYY-MM-DDTHH:MM:SS"`` (interpreted as local-time naive)

    This is deliberately forgiving so small LLMs (Concierge / advisors building
    the request body from the endpoint's describe) can express "the next 24
    hours" as ``start="now"`` / ``end="+24h"`` (or even ``"+86400"``) and have it
    just work, rather than fabricating a 10-digit epoch. Raises ``ValueError``
    on anything unparseable so the REST layer can return a clean 400.
    """
    if now is None:
        now = time.time()
    s = str(value).strip()
    if not s:
        raise ValueError("empty datetime value")

    if s.lower() == "now":
        return int(now)

    # Relative offset (must be checked BEFORE int(): int("+86400") would
    # otherwise silently become the absolute epoch 86400 = Jan 1970).
    m = _MAINTENANCE_REL_RE.match(s)
    if m:
        sign, num, unit = m.group(1), int(m.group(2)), m.group(3).lower()
        offset = num * (_MAINTENANCE_UNIT_SECONDS[unit] if unit else 1)
        return int(now + offset) if sign == "+" else int(now - offset)

    # Absolute epoch seconds (unsigned int / float string).
    try:
        return int(float(s))
    except (TypeError, ValueError):
        pass

    # ISO date / datetime forms (naive — matches parse_user_datetime).
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return int(round(_dt.strptime(s, fmt).timestamp()))
        except ValueError:
            continue

    raise ValueError(
        f"cannot parse '{value}' — accepted: epoch seconds, 'now', a relative "
        "offset ('+24h' / '+30m' / '+86400' / '-1h'; units s/m/h/d/w, no unit = "
        "seconds), or ISO 'YYYY-MM-DD' / 'YYYY-MM-DDTHH:MM' / 'YYYY-MM-DDTHH:MM:SS'"
    )


# Canonical anomaly_reason value written while an entity is under maintenance.
ENTITY_MAINTENANCE_ANOMALY_REASON = "entity_under_maintenance"


def entity_maintenance_is_active(maintenance_record, now=None):
    """Return True iff ``maintenance_start_epoch <= now < maintenance_end_epoch``.

    The active window is computed live from ``now`` — it is never persisted, so
    a record goes inert the moment its end epoch passes (the decision maker then
    ignores it and the entity returns to its computed state) without any writer
    having to flip a flag.
    """

    if not maintenance_record:
        return False

    if now is None:
        now = time.time()

    try:
        start_epoch = float(maintenance_record.get("maintenance_start_epoch", 0) or 0)
    except (TypeError, ValueError):
        start_epoch = 0.0
    try:
        end_epoch = float(maintenance_record.get("maintenance_end_epoch", 0) or 0)
    except (TypeError, ValueError):
        end_epoch = 0.0

    # A window with no positive end can never be active (defensive).
    if not end_epoch > 0:
        return False

    return start_epoch <= now < end_epoch


def entity_maintenance_lookup(
    key_value,
    entity_maintenance_collection_keys,
    entity_maintenance_collection_dict,
    now=None,
):
    """Return the maintenance record for ``key_value`` iff it is currently active.

    Mirrors ``disruption_queue_lookup`` — a cheap dict lookup keyed by the
    entity's SHA256 object_id (``_key``). Returns ``{}`` when there is no record
    or the window is not active right now.
    """

    if key_value not in entity_maintenance_collection_keys:
        return {}

    try:
        maintenance_record = entity_maintenance_collection_dict[key_value]
    except Exception:
        return {}

    if entity_maintenance_is_active(maintenance_record, now=now):
        return maintenance_record

    return {}


def _format_epoch(epoch):
    """Human-readable server-local timestamp for the status message.

    The frontend re-renders epochs in browser-local time; this string is only a
    convenience for the raw status_message / non-UI consumers (alerts, AI).
    """
    try:
        epoch = float(epoch)
    except (TypeError, ValueError):
        return "unknown"
    if not epoch > 0:
        return "unknown"
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(epoch))


def apply_entity_maintenance_override(record, maintenance_record, now=None):
    """Force the entity into BLUE (protected) maintenance state, in place.

    This is applied as the FINAL state mutation in every decision-maker path
    (the unified engine, the component_user REST handler, and the
    trackmedecisionmaker search command), so it wins over the computed state
    AND over every other blue/protection override (ACK, disruption grace,
    logical-group protection) — per the top-precedence product decision.

    Mutates ``record`` to:
      - ``object_state`` = ``"blue"``
      - ``is_under_maintenance`` = 1 + the window epochs / comment (consumed by
        the UI, describe/entity, and the AI read tool)
      - ``status_message`` / ``status_message_json`` — prepends a clear
        "under scheduled maintenance until <end>" line, preserving any prior
        messages so the underlying reason stays visible.

    ``anomaly_reason`` is deliberately left untouched: maintenance is a
    protection layer, not an anomaly, and rewriting the reason would churn the
    ACK-remove-on-reason-change machinery for a state that is already
    non-alerting.

    No-op (returns the record unchanged) if ``maintenance_record`` is empty.
    """

    if not maintenance_record:
        return record

    if now is None:
        now = time.time()

    try:
        start_epoch = float(maintenance_record.get("maintenance_start_epoch", 0) or 0)
    except (TypeError, ValueError):
        start_epoch = 0.0
    try:
        end_epoch = float(maintenance_record.get("maintenance_end_epoch", 0) or 0)
    except (TypeError, ValueError):
        end_epoch = 0.0
    comment = str(maintenance_record.get("maintenance_comment", "") or "")

    # Force the protected state.
    record["object_state"] = "blue"
    record["is_under_maintenance"] = 1
    record["maintenance_start_epoch"] = start_epoch
    record["maintenance_end_epoch"] = end_epoch
    record["maintenance_comment"] = comment

    # Build the leading status message line.
    maintenance_message = (
        f"Entity is under scheduled maintenance until {_format_epoch(end_epoch)} "
        f"— protected (blue) state is enforced, alerting is suppressed for the "
        f"maintenance window."
    )
    if comment:
        maintenance_message = f"{maintenance_message} Comment: {comment}"

    # Preserve any prior status messages; the maintenance line leads.
    status_message_json = record.get("status_message_json")
    if not isinstance(status_message_json, dict):
        status_message_json = {}
    existing = status_message_json.get("status_message")
    if isinstance(existing, str):
        existing = [existing] if existing else []
    elif not isinstance(existing, list):
        existing = []

    new_status_message = [maintenance_message] + [m for m in existing if m]
    status_message_json["status_message"] = new_status_message
    record["status_message_json"] = status_message_json
    record["status_message"] = " | ".join(new_status_message)

    return record


def clear_entity_maintenance_fields(record):
    """Strip stale maintenance metadata from ``record`` in place.

    The decision-maker output is persisted back to the entity KV record, so a
    window that has expired (or been cleared) can otherwise leave a stale
    ``is_under_maintenance=1`` / window / comment on the record on the next
    cycle. Each decision-maker path calls this when the maintenance lookup
    returns no ACTIVE window, so the persisted record reflects reality.

    Idempotent — safe to call on records that were never under maintenance.
    """
    record["is_under_maintenance"] = 0
    record.pop("maintenance_start_epoch", None)
    record.pop("maintenance_end_epoch", None)
    record.pop("maintenance_comment", None)
    return record
