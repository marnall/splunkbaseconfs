"""Schema validation for intel_sources.yaml (runtime + CLI)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

REQUIRED_SOURCE_FIELDS = (
    "title",
    "sourcetype",
    "path",
    "date_param",
    "date_field",
    "default_lookback",
    "legacy_modular_input",
    "legacy_python_module",
    "default_interval_seconds",
    "epoch_parser",
)

ALLOWED_EPOCH_PARSERS = frozenset({"iso_z", "strip_subsecond"})


class IntelSourcesValidationError(Exception):
    """Raised when intel_sources.yaml fails validation."""


def load_intel_sources(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, Mapping):
        raise IntelSourcesValidationError("Root YAML value must be a mapping")
    return dict(data)


def validate_intel_sources(data: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    sources = data.get("sources")
    if not isinstance(sources, Mapping) or not sources:
        raise IntelSourcesValidationError("'sources' must be a non-empty mapping")

    seen_st: set[str] = set()
    seen_legacy: set[str] = set()
    seen_paths: set[str] = set()
    seen_modules: set[str] = set()

    for key, spec in sources.items():
        if not isinstance(key, str) or not key:
            raise IntelSourcesValidationError(f"Invalid source key: {key!r}")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise IntelSourcesValidationError(
                f"Source key {key!r} must match ^[a-z][a-z0-9_]*$",
            )
        if not isinstance(spec, Mapping):
            raise IntelSourcesValidationError(f"Source {key!r} must be a mapping")

        missing = [f for f in REQUIRED_SOURCE_FIELDS if f not in spec]
        if missing:
            raise IntelSourcesValidationError(
                f"Source {key!r} missing required fields: {', '.join(missing)}",
            )

        path_val = spec["path"]
        if not isinstance(path_val, str) or not path_val.startswith("/"):
            raise IntelSourcesValidationError(
                f"Source {key!r}: 'path' must be a string starting with /",
            )

        for text_key in (
            "title",
            "sourcetype",
            "date_param",
            "date_field",
            "legacy_modular_input",
            "legacy_python_module",
            "epoch_parser",
        ):
            val = spec[text_key]
            if not isinstance(val, str) or not val:
                raise IntelSourcesValidationError(
                    f"Source {key!r}: {text_key!r} must be a non-empty string",
                )

        if spec["epoch_parser"] not in ALLOWED_EPOCH_PARSERS:
            raise IntelSourcesValidationError(
                f"Source {key!r}: epoch_parser must be one of {sorted(ALLOWED_EPOCH_PARSERS)}",
            )

        interval = spec["default_interval_seconds"]
        if not isinstance(interval, int) or interval <= 0:
            raise IntelSourcesValidationError(
                f"Source {key!r}: default_interval_seconds must be a positive int",
            )

        lookback = spec["default_lookback"]
        if not isinstance(lookback, Mapping):
            raise IntelSourcesValidationError(
                f"Source {key!r}: default_lookback must be a mapping",
            )
        hours = lookback.get("hours")
        days = lookback.get("days")
        has_hours = isinstance(hours, int) and hours > 0
        has_days = isinstance(days, int) and days > 0
        if has_hours == has_days:
            raise IntelSourcesValidationError(
                f"Source {key!r}: default_lookback must set exactly one of " "'hours' or 'days' as a positive int",
            )

        st = spec["sourcetype"]
        if st in seen_st:
            raise IntelSourcesValidationError(f"Duplicate sourcetype {st!r}")
        seen_st.add(st)

        legacy = spec["legacy_modular_input"]
        if legacy in seen_legacy:
            raise IntelSourcesValidationError(f"Duplicate legacy_modular_input {legacy!r}")
        seen_legacy.add(legacy)

        if path_val in seen_paths:
            raise IntelSourcesValidationError(f"Duplicate path {path_val!r}")
        seen_paths.add(path_val)

        mod = spec["legacy_python_module"]
        if mod in seen_modules:
            raise IntelSourcesValidationError(f"Duplicate legacy_python_module {mod!r}")
        seen_modules.add(mod)

        filters = spec.get("filters")
        if filters is not None:
            if not isinstance(filters, Mapping) or not filters:
                raise IntelSourcesValidationError(
                    f"Source {key!r}: 'filters' must be a non-empty mapping when present",
                )
            for fk, fv in filters.items():
                if not isinstance(fk, str) or not fk:
                    raise IntelSourcesValidationError(
                        f"Source {key!r}: filter keys must be non-empty strings",
                    )
                if not isinstance(fv, str) or not fv:
                    raise IntelSourcesValidationError(
                        f"Source {key!r}: filter values must be non-empty strings",
                    )

        extra = spec.get("extra_query_params")
        if extra is not None:
            if not isinstance(extra, Mapping) or not extra:
                raise IntelSourcesValidationError(
                    f"Source {key!r}: extra_query_params must be a non-empty mapping when present",
                )
            for ek, ev in extra.items():
                if not isinstance(ek, str) or not isinstance(ev, str) or not ek or not ev:
                    raise IntelSourcesValidationError(
                        f"Source {key!r}: extra_query_params keys and values must be non-empty strings",
                    )

    return dict(sources)


def validate_file(path: Path) -> dict[str, Mapping[str, Any]]:
    data = load_intel_sources(path)
    _schema = data.get("schema_version")
    if _schema is not None and not isinstance(_schema, int):
        raise IntelSourcesValidationError("schema_version must be an integer when set")
    return validate_intel_sources(data)
