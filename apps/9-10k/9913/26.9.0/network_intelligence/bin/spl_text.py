"""Shared SPL text-rendering primitives used by both health/spl.py and alerts/spl.py."""


def spl_string_literal(value: str) -> str:
    """Wrap a value in double quotes, escaping internal double quotes."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
