"""Output and error sanitizer for the PolySwarm App.

This module is the single chokepoint every value passes through before it
leaves the app. "Leaves the app" means any of the following:

  * a field written into a Splunk event or search result
  * a line written to a log file under $SPLUNK_HOME/var/log/splunk
  * an error string rendered in the search bar or on a setup page

sanitize() is a pure function. It takes the object to clean plus the secret
values the caller knows about, and it returns a new object of the same shape.
It never mutates its input and it never reads global state, so it is fully
testable without a Splunk instance.

Two independent rules are applied:

  1. Field-name rule. Any mapping key whose name matches SENSITIVE_FIELD_RE is
     replaced wholesale, regardless of what the value looks like.
  2. Value rule. Any string containing one of the caller-supplied secrets has
     that substring replaced.

The field-name rule runs even when no secrets are supplied, so a caller that
forgets to pass the API key still cannot emit a field literally named
"api_key".
"""

import re

REDACTED = "[REDACTED]"

# Field names that must never carry a value out of the app.
#
# The separator class in the first alternative covers api_key, apikey, and the
# hyphenated header spelling x-api-key. A hyphen is the usual separator in an
# HTTP header name, and header dictionaries are exactly the kind of structure
# that gets logged wholesale when a request fails.
SENSITIVE_FIELD_RE = re.compile(r"(?i)(api[-_ ]?key|authorization|password|token)")

# Secrets shorter than this are ignored by the value rule. Redacting a one or
# two character secret would blank out unrelated text and hide real errors.
MIN_SECRET_LENGTH = 8

# Depth ceiling. Splunk result rows are shallow; anything deeper than this is
# either a cycle or a payload we should not be emitting in the first place.
MAX_DEPTH = 32

_TRUNCATED = "[TRUNCATED]"


def is_sensitive_field(name):
    """Return True when a mapping key must never carry its value outward."""
    if not isinstance(name, str):
        return False
    return SENSITIVE_FIELD_RE.search(name) is not None


def _usable_secrets(secrets):
    """Normalise the caller's secrets into a tuple of long-enough strings."""
    if not secrets:
        return ()
    if isinstance(secrets, (str, bytes)):
        secrets = (secrets,)
    usable = []
    for secret in secrets:
        if isinstance(secret, bytes):
            try:
                secret = secret.decode("utf-8")
            except UnicodeDecodeError:
                continue
        if not isinstance(secret, str):
            continue
        if len(secret) < MIN_SECRET_LENGTH:
            continue
        usable.append(secret)
    # Longest first, so a key that contains a shorter key is redacted whole.
    usable.sort(key=len, reverse=True)
    return tuple(usable)


def _scrub_text(text, secrets):
    for secret in secrets:
        if secret in text:
            text = text.replace(secret, REDACTED)
    return text


def sanitize(obj, secrets=()):
    """Return a copy of obj with credential material removed.

    :param obj: any value: mapping, sequence, string, bytes, exception, scalar.
    :param secrets: a single secret string or an iterable of them. Values
        shorter than MIN_SECRET_LENGTH are ignored.
    :return: a new object of the same shape, safe to index, log, or display.
    """
    return _sanitize(obj, _usable_secrets(secrets), 0)


def _sanitize(obj, secrets, depth):
    if depth > MAX_DEPTH:
        return _TRUNCATED

    if obj is None or isinstance(obj, (bool, int, float, complex)):
        return obj

    if isinstance(obj, str):
        return _scrub_text(obj, secrets)

    if isinstance(obj, (bytes, bytearray)):
        try:
            decoded = obj.decode("utf-8")
        except UnicodeDecodeError:
            return obj
        scrubbed = _scrub_text(decoded, secrets)
        if scrubbed == decoded:
            return obj
        return scrubbed.encode("utf-8")

    if isinstance(obj, BaseException):
        return _sanitize_exception(obj, secrets, depth)

    if isinstance(obj, dict):
        cleaned = {}
        for name, value in obj.items():
            clean_name = _sanitize(name, secrets, depth + 1)
            if is_sensitive_field(name):
                cleaned[clean_name] = REDACTED
            else:
                cleaned[clean_name] = _sanitize(value, secrets, depth + 1)
        return cleaned

    if isinstance(obj, (list, tuple, set, frozenset)):
        items = [_sanitize(item, secrets, depth + 1) for item in obj]
        if isinstance(obj, list):
            return items
        if isinstance(obj, tuple):
            return tuple(items)
        if isinstance(obj, set):
            return set(items)
        return frozenset(items)

    # Anything else is rendered as text and scrubbed. Reaching this branch with
    # an object whose repr embeds a credential is the case this guards.
    return _scrub_text(repr(obj), secrets)


def _sanitize_exception(exc, secrets, depth):
    """Rebuild an exception with sanitized args, preserving its type."""
    clean_args = tuple(_sanitize(arg, secrets, depth + 1) for arg in exc.args)
    if clean_args == exc.args:
        return exc
    try:
        return type(exc)(*clean_args)
    except Exception:
        # Some exception types do not accept their own args positionally.
        # Degrade to a plain error carrying the sanitized text.
        return RuntimeError(*clean_args)


def sanitize_message(template, secrets=()):
    """Sanitize a preformatted message string.

    Convenience wrapper for log and error paths where the value is already a
    string. Kept separate so call sites read as an explicit redaction step.
    """
    return _scrub_text(str(template), _usable_secrets(secrets))
