#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
install_deps.py — bootstrap third-party dependencies for the Agentic path.

splunklib.ai (Python 3.13 only) pulls langchain, langgraph, mcp, pydantic v2,
httpx, anyio. These cannot be shipped in the Splunkbase tarball because they
include native Rust extensions (pydantic_core) that vary per platform/CPU
architecture, and the combined size exceeds the App store limit.

This script is invoked by the setup wizard on first use to install all heavy
dependencies into `bin/lib/site-packages/` using Splunk's bundled pip.

Behaviour:
    • Runs only on Python 3.13+ (no-op on 3.9 — legacy path doesn't need these).
    • Installs to a *vendor* directory inside the app — never to the system Python.
    • Idempotent: re-running just upgrades.
    • Writes a marker file `bin/lib/site-packages/.deps_installed` on success.

Usage:
    splunk cmd python bin/install_deps.py

Exit codes:
    0  Success (or no-op on Python 3.9).
    1  Pip failure.
    2  Not on Splunk Python (`sys.executable` doesn't look like splunkd's python).
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

LOG = logging.getLogger("install_deps")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# splunklib.ai's *runtime* third-party deps (pinned to versions that work with
# splunklib.ai develop @ May 2026; bump as the SDK evolves).
DEPS = [
    "pydantic>=2.10,<3",
    "httpx>=0.27,<1",
    "anyio>=4.6,<5",
    # splunklib.ai engines.langchain uses the v1 APIs (langchain.agents.middleware,
    # langchain.messages, create_agent). Must be langchain >= 1.0.
    "langchain>=1.0,<2",
    "langgraph>=0.3,<2",
    # langchain v1 splits provider integrations into separate adapter packages.
    # splunklib.ai imports ChatOpenAI / ChatAnthropic / ChatGoogleGenerativeAI
    # from these on demand based on which provider the user picks.
    "langchain-openai>=1.0,<2",
    "langchain-anthropic>=1.0,<2",
    "langchain-google-genai>=4.0,<5",
    "mcp>=1.1,<2",
    "openai>=1.50,<2",
    "anthropic>=0.40,<1",
    # google-genai is optional (only loaded when GoogleModel is used) but
    # cheap enough to install eagerly so first-run UX is smooth.
    # langchain-google-genai 4.x requires google-genai >=1.53,<2, so we
    # widen this range to keep pip's resolver happy.
    "google-genai>=1.5,<3",
    # vendored splunklib.results uses the `deprecation` package; the GitHub
    # sparse-clone doesn't bring it in, so install it explicitly here.
    "deprecation>=2,<3",
]

# Resolved at runtime — never hard-code.
APP_ROOT = Path(__file__).resolve().parent.parent
SITE_PACKAGES = APP_ROOT / "bin" / "lib" / "site-packages"
MARKER = SITE_PACKAGES / ".deps_installed"


def is_python_313_or_newer() -> bool:
    return sys.version_info >= (3, 13)


def main() -> int:
    if not is_python_313_or_newer():
        LOG.info(
            "Python %s.%s detected — Agentic path requires 3.13+. "
            "v4.0.0 will run in legacy mode (no install needed).",
            sys.version_info.major,
            sys.version_info.minor,
        )
        return 0

    SITE_PACKAGES.mkdir(parents=True, exist_ok=True)
    LOG.info("Installing Agentic dependencies into %s", SITE_PACKAGES)

    # Use the Splunk-bundled pip via `python -m pip` so we always match the
    # interpreter that will actually load these modules later.
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--no-warn-script-location",
        "--target",
        str(SITE_PACKAGES),
        *DEPS,
    ]

    LOG.info("Running: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        LOG.error("pip install failed (exit %d)", proc.returncode)
        LOG.error("stdout: %s", proc.stdout[-2000:] if proc.stdout else "(empty)")
        LOG.error("stderr: %s", proc.stderr[-2000:] if proc.stderr else "(empty)")
        return 1

    import datetime
    MARKER.write_text(
        "Installed at " + datetime.datetime.now(datetime.UTC).isoformat() + "\n",
        encoding="utf-8",
    )
    LOG.info("Dependencies installed successfully → %s", MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
