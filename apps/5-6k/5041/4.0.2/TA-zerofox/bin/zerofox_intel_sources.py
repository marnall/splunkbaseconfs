"""Load and query intel_sources.yaml."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from intel_sources_schema import IntelSourcesValidationError, validate_intel_sources


class IntelRegistry:
    """Validated CTI feed definitions keyed by intel source id (e.g. botnet, phishing)."""

    __slots__ = ("_sources",)

    def __init__(self, sources: dict[str, Mapping[str, Any]]) -> None:
        self._sources = sources

    @classmethod
    def from_yaml_mapping(cls, root: Mapping[str, Any]) -> IntelRegistry:
        sources = validate_intel_sources(root)
        return cls(sources)

    @classmethod
    def from_path(cls, path: Path) -> IntelRegistry:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            msg = "intel_sources root must be a mapping"
            raise IntelSourcesValidationError(msg)
        return cls.from_yaml_mapping(raw)

    def require(self, intel_source: str) -> Mapping[str, Any]:
        try:
            return self._sources[intel_source]
        except KeyError as err:
            msg = f"unknown intel_source: {intel_source!r}"
            raise KeyError(msg) from err

    def sources(self) -> Mapping[str, Mapping[str, Any]]:
        return self._sources


def resolve_intel_sources_path(bin_file: str | Path = __file__) -> Path:
    """Resolve intel_sources.yaml for packaged TA or dev repo layout."""
    env = os.environ.get("ZFOX_INTEL_SOURCES_PATH")
    if env:
        return Path(env)

    bin_dir = Path(bin_file).resolve().parent
    candidates = (
        bin_dir.parent / "default" / "intel_sources.yaml",
        bin_dir.parent.parent / "config" / "intel_sources.yaml",
    )
    for p in candidates:
        if p.is_file():
            return p
    msg = "intel_sources.yaml not found; set ZFOX_INTEL_SOURCES_PATH or ship default/intel_sources.yaml"
    raise FileNotFoundError(msg)


def load_default_registry(bin_file: str | Path = __file__) -> IntelRegistry:
    return IntelRegistry.from_path(resolve_intel_sources_path(bin_file))
