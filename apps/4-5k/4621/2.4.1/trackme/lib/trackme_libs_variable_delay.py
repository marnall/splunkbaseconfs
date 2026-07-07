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
Pure helper functions for the variable-delay subsystem.

These helpers used to live at the top of
`package/bin/trackmesplkvariabledelay.py` (a custom search command). That
arrangement created a transitive-import hazard: any REST handler or
custom command that wanted to reuse one of the helpers had to do
`from trackmesplkvariabledelay import ...`, and that import side-effect
walks the custom command's module-load code — which installs a
`RotatingFileHandler` pointing at `trackme_variable_delay.log` on the
root logger. The destination of every `logging.<level>(...)` call in
the importing process is silently rebound for the rest of the
process's lifetime.

In particular, the schema-upgrade slow path in
`package/bin/trackmetrackerhealth.py` imports the API-catalog warmup
helper, which imports every REST handler at top level. Before this
module existed, `trackme_rest_handler_splk_variable_delay_user.py`
imported these three helpers from the custom command, so every
schema-upgrade log line that fired AFTER the warmup landed in
`trackme_variable_delay.log` instead of `trackme_tracker_health.log`.
See issue #1717 (follow-up to #1711 / PR #1712).

The functions themselves are pure (no I/O, no logging, no Splunk SDK).
The bodies are byte-identical to their previous definitions in
`trackmesplkvariabledelay.py` — moving them here is a refactor, not a
behaviour change.
"""

# Standard library imports
import math


def aggregate_slots(hourly_thresholds):
    """
    Aggregate per-hour thresholds into named slots by grouping adjacent hours
    with the same threshold value on the same days.

    Args:
        hourly_thresholds: dict of {(day, hour): threshold_value}

    Returns:
        list of slot dicts with slot_name, days, hours, max_delay_allowed
    """

    # Group by threshold value, collecting (day, hour) pairs
    threshold_groups = {}
    for (day, hour), threshold in hourly_thresholds.items():
        if threshold not in threshold_groups:
            threshold_groups[threshold] = []
        threshold_groups[threshold].append((day, hour))

    slots = []
    slot_index = 0

    for threshold, day_hour_pairs in sorted(threshold_groups.items()):
        # Group by days that share the same hours for this threshold
        day_hours_map = {}
        for day, hour in day_hour_pairs:
            if day not in day_hours_map:
                day_hours_map[day] = []
            day_hours_map[day].append(hour)

        # Sort hours for each day
        for day in day_hours_map:
            day_hours_map[day].sort()

        # Group days that have identical hour sets
        hours_to_days = {}
        for day, hours in day_hours_map.items():
            hours_key = tuple(hours)
            if hours_key not in hours_to_days:
                hours_to_days[hours_key] = []
            hours_to_days[hours_key].append(day)

        for hours_tuple, days in hours_to_days.items():
            days.sort()
            slot_index += 1
            slots.append(
                {
                    "slot_name": f"auto_slot_{slot_index}",
                    "days": days,
                    "hours": list(hours_tuple),
                    "max_delay_allowed": int(threshold),
                }
            )

    return slots


def compute_threshold(perc95_value):
    """
    Compute a safe threshold from a percentile value.
    Round to nearest hour + 1 hour buffer, minimum 3600.
    """
    if perc95_value is None or perc95_value <= 0:
        return 3600

    # Round up to nearest hour + 1 hour buffer
    threshold = (math.ceil(perc95_value / 3600.0)) * 3600 + 3600
    return max(int(threshold), 3600)


def recompute_existing_slot_thresholds(
    existing_slots, hourly_thresholds, max_threshold_sec=604800
):
    """
    Refresh max_delay_allowed on existing slots while preserving each slot's
    slot_name, days, and hours. Used by the auto-compute "honour existing
    slots" strategy.

    Args:
        existing_slots: list of slot dicts as stored in variable_delay_slots
                        (slot_name, days[], hours[], max_delay_allowed)
        hourly_thresholds: dict of {(day, hour): threshold_seconds} already
                           passed through compute_threshold()
        max_threshold_sec: safety cap applied to any refreshed threshold

    Returns:
        (refreshed_slots, recommended_default)
        - refreshed_slots: deep-copied slot list with updated
          max_delay_allowed (cells that have no metric data leave the
          existing slot threshold unchanged, so a slot covering only
          quiet (day, hour) cells is not silently downgraded)
        - recommended_default: max threshold across cells not covered by
          any slot. Falls back to the max across covered cells when every
          (day, hour) is covered, and to 3600 when hourly_thresholds is
          empty.
    """

    refreshed = []
    covered_cells = set()

    for slot in existing_slots or []:
        days = slot.get("days", []) or []
        hours = slot.get("hours", []) or []
        candidates = []
        for d in days:
            for h in hours:
                try:
                    cell = (int(d), int(h))
                except (TypeError, ValueError):
                    continue
                covered_cells.add(cell)
                value = hourly_thresholds.get(cell)
                if value is not None:
                    candidates.append(int(value))

        new_slot = dict(slot)
        # Defensive copies so callers cannot mutate the inputs via the response.
        new_slot["days"] = list(days)
        new_slot["hours"] = list(hours)
        if candidates:
            chosen = max(candidates)
            if chosen > max_threshold_sec:
                chosen = max_threshold_sec
            new_slot["max_delay_allowed"] = int(chosen)
        # else: preserve the existing max_delay_allowed — no data means
        # we have no signal to revise the slot with, and silently
        # collapsing it to a default would surprise the operator.
        refreshed.append(new_slot)

    uncovered_values = [
        v for (d, h), v in hourly_thresholds.items() if (d, h) not in covered_cells
    ]
    if uncovered_values:
        recommended_default = max(uncovered_values)
    elif hourly_thresholds:
        recommended_default = max(hourly_thresholds.values())
    else:
        recommended_default = 3600

    if recommended_default > max_threshold_sec:
        recommended_default = max_threshold_sec

    return refreshed, int(recommended_default)
