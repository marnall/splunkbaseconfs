#!/bin/sh

# CryptView Collector collects cryptographic metadata only. It does not collect private keys,
# passwords, keystore secrets, tokens, cookies, or confidential file contents.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"

if [ -n "${CRYPTVIEW_PYTHON:-}" ]; then
  PYTHON_BIN="$CRYPTVIEW_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "CryptView Collector wrapper error: Python 3 was not found in PATH." >&2
  exit 1
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/cryptview_collect.py" "$@"
