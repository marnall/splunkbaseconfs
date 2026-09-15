#!/usr/bin/env bash
#
# build_bundled_spl.sh
#
# Run this ON a server where TA-Oracle-OCI is already installed AND
# the `pip install --target=bin/lib` step has already completed
# successfully (confirm via index=_internal source=*oci_stream.py* -
# should show it polling cleanly, not FATAL/import errors).
#
# It packages the current app - INCLUDING the already-installed bin/lib
# dependencies - into a new .spl, so copying that .spl to a restricted-
# access server (no PyPI reachability) skips the pip install step there
# entirely.
#
# ============================================================================
# IMPORTANT TRADEOFF - READ BEFORE USING
# ============================================================================
# bin/lib contains compiled binaries (cryptography's C/Rust extensions,
# cffi's _cffi_backend.so) built for THIS server's exact:
#   - Python version   (e.g. 3.9)
#   - OS                (e.g. Linux)
#   - Architecture       (e.g. x86_64)
#
# This bundled .spl will ONLY work on other servers matching that same
# combination. On a server with a different Python version, OS, or CPU
# architecture, it will fail to import - which is exactly the problem that
# broke the original archived TA 5222 (its binaries were frozen to Python
# 3.7 and later Splunk versions moved past that).
#
# Verify the match BEFORE deploying, on both source and target servers:
#   $SPLUNK_HOME/bin/splunk cmd python3 -c "import sys; print(sys.version_info)"
#   uname -s
#   uname -m
#
# Safe to use when: source and target servers match on all three - e.g.
# a fleet of identically-provisioned Splunk instances.
#
# NOT safe to use when: target server might differ in any of the three.
# In that case, run the normal pip install step fresh on that server
# instead (see README.md) - slower, but always correct, since it resolves
# the right wheel for whatever that specific machine actually has.
# ============================================================================

set -euo pipefail

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
APP_DIR="$SPLUNK_HOME/etc/apps/TA-Oracle-OCI"
OUT_FILE="${1:-./TA-Oracle-OCI-bundled.spl}"

if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: $APP_DIR not found. Set SPLUNK_HOME or check the app is installed." >&2
    exit 1
fi

if [ ! -d "$APP_DIR/bin/lib/oci" ]; then
    echo "ERROR: $APP_DIR/bin/lib/oci not found." >&2
    echo "Run the pip install step from README.md first, and confirm it works" >&2
    echo "(check index=_internal source=*oci_stream.py* for clean startup)" >&2
    echo "before bundling - otherwise you'll just be freezing the same broken state." >&2
    exit 1
fi

THIS_PYVER=$("$SPLUNK_HOME/bin/splunk" cmd python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
THIS_ARCH=$(uname -m)
THIS_OS=$(uname -s)

echo "Bundling for: Python $THIS_PYVER, $THIS_OS $THIS_ARCH"
echo "This bundle will ONLY work on servers matching that exact combination."
echo

read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

WORKDIR=$(mktemp -d)
trap 'find "$WORKDIR" -depth -delete' EXIT

cp -r "$APP_DIR" "$WORKDIR/TA-Oracle-OCI"

# Strip anything that shouldn't travel in a redistributable package:
# - local/inputs.conf may contain real secrets/paths for THIS server only
# - __pycache__ is regenerable cruft
find "$WORKDIR/TA-Oracle-OCI/local" -name "inputs.conf" -delete 2>/dev/null || true
find "$WORKDIR/TA-Oracle-OCI" -depth -name "__pycache__" -exec sh -c 'find "$1" -depth -delete' _ {} \; 2>/dev/null || true
find "$WORKDIR/TA-Oracle-OCI" -name "*.pyc" -delete 2>/dev/null || true

# Drop a marker file recording exactly what this bundle was built for,
# so anyone deploying it later can verify compatibility before installing.
cat > "$WORKDIR/TA-Oracle-OCI/bin/lib/BUNDLED_FOR.txt" << EOF
This bin/lib was frozen from a working install with:
  Python:       $THIS_PYVER
  OS:           $THIS_OS
  Architecture: $THIS_ARCH
  Built on:     $(date -u +"%Y-%m-%dT%H:%M:%SZ")

Only install this .spl on servers matching ALL of the above. If unsure,
run the normal pip install step from README.md instead of using this
pre-bundled package.
EOF

tar -czf "$OUT_FILE" -C "$WORKDIR" TA-Oracle-OCI

echo
echo "Built: $OUT_FILE"
echo "Contains bin/lib pre-installed - target servers can skip the pip install step,"
echo "but ONLY if they match: Python $THIS_PYVER, $THIS_OS $THIS_ARCH"
