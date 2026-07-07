"""Epoch extraction from CTI API timestamp strings (mirrors legacy input modules)."""

from __future__ import annotations

import datetime

UTC_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


def epoch_from_iso_z(dt: str) -> float:
    if not dt:
        msg = "empty timestamp"
        raise ValueError(msg)
    if dt.endswith("Z"):
        parsed = datetime.datetime.fromisoformat(f"{dt[:-1]}+00:00")
    else:
        parsed = datetime.datetime.fromisoformat(dt)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return (parsed - UTC_EPOCH).total_seconds()


def epoch_strip_subsecond(dt: str) -> float:
    if not dt:
        msg = "empty timestamp"
        raise ValueError(msg)
    pieces = dt.split(".")
    head = pieces[0]
    naive = datetime.datetime.strptime(head, "%Y-%m-%dT%H:%M:%S")
    parsed = datetime.datetime.fromisoformat(f"{naive.isoformat()}+00:00")
    return (parsed - UTC_EPOCH).total_seconds()


def epoch_for_parser(parser: str, dt: str) -> float:
    if parser == "iso_z":
        return epoch_from_iso_z(dt)
    if parser == "strip_subsecond":
        return epoch_strip_subsecond(dt)
    msg = f"unknown epoch parser: {parser!r}"
    raise ValueError(msg)
