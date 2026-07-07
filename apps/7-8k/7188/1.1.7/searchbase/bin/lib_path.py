"""
Resolve arch- and Python-version-specific vendored lib paths for Searchbase.

Splunk 9.3+ ships Python 3.9 by default; 10.2+ supports opt-in 3.13.
Vendored wheels live under lib/py39|py313/linux_x86_64|linux_aarch64/.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Optional


_SUPPORTED_PYTHON_TAGS = {
    (3, 9): "py39",
    (3, 13): "py313",
}


def linux_arch_dir(machine: Optional[str] = None) -> str:
    """Map platform.machine() to vendored lib subdirectory name."""
    normalized = (machine or platform.machine()).lower()
    if normalized in ("x86_64", "amd64"):
        return "linux_x86_64"
    if normalized in ("aarch64", "arm64"):
        return "linux_aarch64"
    raise RuntimeError(
        f"Unsupported CPU architecture for vendored libs: {machine!r}. "
        "Expected x86_64/amd64 or aarch64/arm64."
    )


def python_vendor_tag(
    version_info: Optional[tuple[int, int]] = None,
) -> str:
    """Map sys.version_info to vendored lib subdirectory name."""
    if version_info is None:
        major, minor = sys.version_info.major, sys.version_info.minor
    else:
        major, minor = version_info
    tag = _SUPPORTED_PYTHON_TAGS.get((major, minor))
    if tag is None:
        supported = ", ".join(f"{m}.{n}" for (m, n) in sorted(_SUPPORTED_PYTHON_TAGS))
        raise RuntimeError(
            f"Unsupported Python {major}.{minor} for vendored libs. "
            f"Supported: {supported} (Splunk 9.3+)."
        )
    return tag


def resolve_vendor_lib_dir(
    app_root: str,
    *,
    machine: Optional[str] = None,
    version_info: Optional[tuple[int, int]] = None,
) -> str:
    """Absolute path to the vendored lib tree for this host."""
    py_tag = python_vendor_tag(version_info)
    arch_dir = linux_arch_dir(machine)
    return os.path.join(app_root, "lib", py_tag, arch_dir)


def prepend_vendor_lib(
    app_root: str,
    *,
    machine: Optional[str] = None,
    version_info: Optional[tuple[int, int]] = None,
) -> Optional[str]:
    """
    Insert the arch/Python-specific vendored lib directory at the front of sys.path.

    Returns the path that was prepended, or None if the directory does not exist.
    """
    vendor_lib = resolve_vendor_lib_dir(
        app_root, machine=machine, version_info=version_info
    )
    if os.path.isdir(vendor_lib):
        if vendor_lib not in sys.path:
            sys.path.insert(0, vendor_lib)
        return vendor_lib
    return None


def prepend_bin_dir(bin_dir: str) -> None:
    if bin_dir not in sys.path:
        sys.path.insert(0, bin_dir)
