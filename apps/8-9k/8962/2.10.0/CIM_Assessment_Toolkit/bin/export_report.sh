#!/bin/bash
# CIM Assessment Report Generator - Linux/macOS Wrapper
# Machine Data Insights Inc.
#
# Copyright 2025-2026 Machine Data Insights Inc.
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
#
# Usage:
#   ./export_report.sh --env "Production" --splunk-uri "https://localhost:8089"
#   ./export_report.sh --env "Corp-Prod" --splunk-uri "https://localhost:8089" --output-dir /tmp/reports
#   ./export_report.sh --env "Production" --no-email
#
# This script is a thin wrapper around email_report.py. All arguments are
# passed through directly. Run email_report.py --help for full options.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_SCRIPT="$SCRIPT_DIR/email_report.py"

# Find Python
PYTHON_BIN=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1)
        if echo "$version" | grep -q "Python 3"; then
            PYTHON_BIN="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: Python 3 not found. Ensure python3 or python is in your PATH." >&2
    exit 1
fi

if [ ! -f "$REPORT_SCRIPT" ]; then
    echo "ERROR: email_report.py not found at: $REPORT_SCRIPT" >&2
    exit 1
fi

exec "$PYTHON_BIN" "$REPORT_SCRIPT" "$@"
