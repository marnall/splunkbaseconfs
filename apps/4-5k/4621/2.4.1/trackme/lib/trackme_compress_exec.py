#!/usr/bin/env python
# coding=utf-8

"""Compression execution helpers used by TrackMe backup/restore.

Current backend: zstd via system binary if available.
"""

import os
import shutil
import subprocess
from typing import List, Optional


def _resolve_zstd_cmd() -> str:
    return os.environ.get("TRACKME_ZSTD_CMD", "zstd")


def _zstd_argv() -> List[str]:
    try:
        env_path = shutil.which("env")
        if os.name != "nt" and env_path:
            return [env_path, _resolve_zstd_cmd()]
    except Exception:
        pass
    return [_resolve_zstd_cmd()]


def is_available() -> bool:
    if shutil.which(_resolve_zstd_cmd()) is None:
        return False
    try:
        subprocess.run(_zstd_argv() + ["--version"], check=True, timeout=10, capture_output=True)
        return True
    except Exception:
        return False


def compress_tar(tar_path: str) -> None:
    subprocess.run(_zstd_argv() + ["-f", tar_path], check=True)


def decompress(src_zst_path: str, out_tar_path: str, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        _zstd_argv() + ["-d", os.path.abspath(src_zst_path), "-o", out_tar_path],
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
    )


def test_archive(path: str) -> int:
    proc = subprocess.run(_zstd_argv() + ["-t", path], capture_output=True)
    return proc.returncode


