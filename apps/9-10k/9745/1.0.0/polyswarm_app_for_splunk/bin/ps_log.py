"""Structured logging for the PolySwarm App.

Design section 4.6 calls the health dashboard "the why is nothing happening
page". This module is what puts anything on it. Every line it writes is one
line, in key=value form, with a fixed shape:

    component=ps_client event=request outcome=ok endpoint=/search/hash/sha256
    duration_ms=142

which Splunk's own field extraction reads without a props stanza, so an
operator can go straight to:

    index=_internal sourcetype=polyswarm_app_for_splunk_log outcome=error
      | stats count by component, event, reason

WHAT THIS MODULE WILL NOT LOG, AND HOW IT IS STOPPED
----------------------------------------------------
A log file is the easiest place in a Splunk app to leak, because a log line
looks like every other log line and there is no failing test unless one is
written on purpose. Constraint C1 says the API key never appears in a log line
and C6 says errors surface as structured sanitized messages. So this module is
built as a whitelist, not a formatter with a sanitizer bolted on, and there are
four independent gates:

  1. **The function names are chosen to sit inside the static leak rule.**
     tests/unit/test_leak_rule.py treats a call whose name matches emit, or is
     one of debug / info / warning, as an output sink, and reports any
     credential-shaped variable handed to one. That is not a coincidence in the
     naming: these functions are called emit(), debug(), info() and warning()
     so that ps_log.emit(component=..., endpoint=api_key) fails CI on every
     commit without this module having to notice anything at runtime.

  2. **Only whitelisted keys are accepted.** ALLOWED_KEYS below is the complete
     set. A key that is not on it is refused, so a caller cannot invent
     api_key=, authorization=, or query= and have it written. There is
     deliberately no name on that list for an indicator, a field value, a query
     string, a response body, or a message, so those values have nothing to
     travel under.

  3. **A credential-shaped key is refused even if it is whitelisted.** The
     second condition reads ps_sanitize.SENSITIVE_FIELD_RE, the same pattern
     the output sanitizer uses to decide a field must never carry a value out
     of the app. So there is one definition of "looks like a credential" in
     this repository, and adding such a name to ALLOWED_KEYS by mistake does
     not open a hole: the key is still refused.

  4. **Only scalar values are accepted.** A mapping, a list, an exception or
     any other object is refused. This is the gate that keeps raw event content
     out: the way event content reaches a log is somebody passing the record,
     or a response payload, or an exception, and none of those is a scalar. An
     exception is logged by its class name, which the caller extracts, for the
     reason written out in ps_client.get_api_key: splunklib's binding layer
     quotes the HTTP exchange it attempted into its exception text.

  5. **Accepted string values are narrowed.** Every character outside a small
     safe set is replaced, then the result is capped at MAX_VALUE_LENGTH. That
     guarantees the single-line, unquoted key=value shape the searches above
     depend on, and it means a value carrying a newline cannot forge a second
     log line.

WHAT THIS MODULE DOES NOT DO, SAID PLAINLY
------------------------------------------
It does not run values through the sanitizer's value rule, and it must not be
read as if it did. That rule works by replacing known secret strings, so it
needs the secret in hand to redact it, and this module deliberately never holds
one: the API key lives in ps_client and putting a copy in the logging module to
redact against would create the second credential-handling surface that C1's
single-chokepoint rule exists to prevent. Calling sanitize_message() here with
no secrets would be a no-op that reads as a safeguard, which is worse than not
calling it, so it is not called. The five gates above are what actually holds,
and each one of them is load bearing.

Gates 2, 3 and 4 raise, because a refusal is a programming error and should
fail a test rather than be silently tolerated. Nothing raises out of emit()
itself, though: a logging call must never be the thing that breaks a customer's
search. So emit() catches the refusal and writes a line naming the refused keys
and nothing else, which is loud in a log and harmless in production.

Where the lines go
------------------
Through splunklib's own logging setup, configure_logging(), which looks for
default/logging.conf inside the app and loads it. That is what puts the lines in
$SPLUNK_HOME/var/log/splunk/polyswarm_app_for_splunk.log, where splunkd indexes
them into _internal on its own. If that setup is unavailable for any reason,
including this module being imported outside splunkd with no vendored splunklib
on the path, logging falls back to stderr, which is where splunkd collects a
search command's output anyway.
"""

import logging
import re
import sys

from ps_sanitize import SENSITIVE_FIELD_RE

APP_NAME = "polyswarm_app_for_splunk"

# The complete set of keys any caller may write. Adding one is a deliberate
# edit here, which is the point: a whitelist that can be extended at the call
# site is not a whitelist.
#
# Read the omissions as carefully as the entries. There is no key for an
# indicator, a hash, a field value, a query string, a URL with its parameters,
# a response body, an account id, or a message. Those are the things that carry
# either a customer's data or ours, and none of them has a name to travel
# under.
ALLOWED_KEYS = frozenset(
    [
        # Always present. See REQUIRED_KEYS.
        "component",  # which module: ps_client, verdict_cache, cmd_search
        "event",  # what happened: request, start, finish, hit, miss
        "outcome",  # how it went: ok, error, not_found, degraded, refused
        # Timing, where there is anything to time.
        "duration_ms",
        # An exception's class name. Never its message.
        "reason",
        # An API path, with no query parameters. See the note in ps_client.
        "endpoint",
        "status",
        "attempts",
        # Counts. Safe because a count is not content.
        "records",
        "lookups",
        # Distinct values the enrichment command found no endpoint for. A
        # count, so it says how many and never which.
        "unrouted",
        # Tag-link requests the enrichment command spent, and whether it hit
        # the separate ceiling on them. Counts, so they say how many and never
        # which artifact, and no key exists for a family or an actor name: an
        # attribution value is the customer's investigation and it has no name
        # to travel under here, exactly as an indicator has none.
        "attribution_lookups",
        "attribution_limit_reached",
        "cache_hits",
        "cache_misses",
        "cache_stores",
        "cache_degraded",
        # Pages of a paginated response one run walked, and artifacts one run
        # refused because it had already emitted them. Both are counts, so
        # they are safe for the reason every other count here is: a count says
        # how many and never which. There is deliberately still no key for a
        # digest, a family, a tag or a query string, so the intel pull's
        # duplicate suppression can report its size and never its contents.
        "pages",
        "duplicates",
        "limit",
        "limit_reached",
        # Task rows the sandbox poller stopped following on one run, because
        # the platform expired them, could not find them, or they passed the
        # stanza's own age ceiling. A count for the same reason every count
        # here is one: it says how many and never which, and there is
        # deliberately still no key for a task id or a detonated URL.
        "abandoned",
        # The KV store collection name, which is a constant in this app.
        "collection",
        # Used only by the refusal line this module writes about itself.
        "rejected",
    ]
)

# Every line carries these three, in this order, so that a line is
# recognisable and groupable before anything else on it is read.
REQUIRED_KEYS = ("component", "event", "outcome")

# Characters permitted in a value. Everything else becomes an underscore.
#
# Chosen so that the key=value shape needs no quoting and cannot be forged:
# there is no whitespace in the set, so a value cannot split a line or add a
# field, and no equals sign, so a value cannot look like a second pair.
SAFE_VALUE_RE = re.compile(r"[^A-Za-z0-9._:/+@-]")

REPLACEMENT_CHARACTER = "_"

# A value that survives all four gates and is still longer than this is
# truncated. Nothing legitimate on the whitelist is long: the longest real
# value is an API path.
MAX_VALUE_LENGTH = 80

TRUNCATION_MARKER = "..."

# Written when a value is present but empty, so that a key's presence does not
# depend on whether its value happened to be blank.
EMPTY_VALUE = "-"


class UnsupportedLogKey(Exception):
    """Raised when a caller offers a key that is not on the whitelist."""


class UnsupportedLogValue(Exception):
    """Raised when a caller offers a value that is not a scalar.

    The gate that keeps raw event content and response payloads out of the log,
    since none of those is a scalar.
    """


# ---------------------------------------------------------------------------
# Value and line formatting: pure, no I/O, no logger
# ---------------------------------------------------------------------------


def format_value(value):
    """Return one value as a safe, single-line, unquoted string.

    :param value: a scalar. None means the caller has nothing to say for this
        key, and the key is dropped by format_line rather than written empty.
    :return: the formatted value.
    :raises UnsupportedLogValue: for anything that is not a scalar.
    """
    # bool is a subclass of int, so it has to be tested first or True would be
    # written as 1.
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        # A NaN or an infinity would otherwise be written as nan or inf, which
        # reads as a real measurement. Neither is one.
        if value != value or value in (float("inf"), float("-inf")):
            return EMPTY_VALUE
        return repr(value)

    if not isinstance(value, str):
        raise UnsupportedLogValue(
            "ps_log accepts only scalar values. A {0} was offered, and a "
            "structured value is how raw event content reaches a log. Pass a "
            "count, a status, or an exception class name instead.".format(
                type(value).__name__
            )
        )

    # Gate 5. Narrow to the safe character set, then cap. See the module
    # docstring for why the sanitizer's value rule is not applied here.
    text = SAFE_VALUE_RE.sub(REPLACEMENT_CHARACTER, value)
    if not text:
        return EMPTY_VALUE
    if len(text) > MAX_VALUE_LENGTH:
        text = text[: MAX_VALUE_LENGTH - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER
    return text


def format_line(component, event, outcome, **fields):
    """Return one complete log line. Pure.

    The enforcement point for gates 2, 3 and 4, and the function the tests
    drive. It raises rather than dropping, because a refused key is a mistake
    in code and should fail a test. emit() is the one that has to stay quiet.

    :param component: the module reporting, for example ps_client.
    :param event: what happened, for example request.
    :param outcome: how it went, for example ok.
    :param fields: any other whitelisted keys. A key whose value is None is
        omitted, so a caller can pass an optional measurement unconditionally.
    :return: the line, with no trailing newline.
    :raises UnsupportedLogKey: if any key is not on the whitelist, or looks
        like a credential.
    :raises UnsupportedLogValue: if any value is not a scalar.
    """
    offered = dict(fields)
    offered["component"] = component
    offered["event"] = event
    offered["outcome"] = outcome

    # Gate 2. The whitelist.
    unsupported = sorted(name for name in offered if name not in ALLOWED_KEYS)
    if unsupported:
        raise UnsupportedLogKey(
            "ps_log refuses the key or keys {0}. Only the names in "
            "ALLOWED_KEYS may be written, so that no value can travel under a "
            "name nobody reviewed.".format(", ".join(unsupported))
        )

    # Gate 3. Independent of the whitelist, and checked after it rather than
    # instead of it. Two conditions have to be satisfied for a key to be
    # written, so adding a credential-shaped name to ALLOWED_KEYS by mistake
    # does not open a hole. The pattern is ps_sanitize's, so this repository
    # has one definition of what looks like a credential.
    credential_shaped = sorted(
        name for name in offered if SENSITIVE_FIELD_RE.search(str(name))
    )
    if credential_shaped:
        raise UnsupportedLogKey(
            "ps_log refuses the credential-shaped key or keys {0}, whatever "
            "ALLOWED_KEYS says. Nothing under a name like that belongs in a "
            "log file.".format(", ".join(credential_shaped))
        )

    pairs = []
    for name in REQUIRED_KEYS:
        pairs.append((name, format_value(offered.pop(name))))
    for name in sorted(offered):
        value = offered[name]
        if value is None:
            continue
        pairs.append((name, format_value(value)))

    return " ".join("{0}={1}".format(name, value) for name, value in pairs)


# ---------------------------------------------------------------------------
# The logger
# ---------------------------------------------------------------------------

_logger = None
_destination = None


def get_logger():
    """Return the app's logger, configuring it on first use.

    splunklib's configure_logging() is tried first. It is the app-aware setup:
    it chdirs to the app root, loads default/logging.conf, and hands back the
    named logger, which is how the lines reach the app's own file under
    $SPLUNK_HOME/var/log/splunk.

    Every reason it can fail ends in the same place, a logger on stderr, and
    they are not distinguished because the caller cannot act on the difference.
    The common one is not an error at all: this module is imported by ps_client,
    which a test imports with no vendored splunklib on sys.path.
    """
    global _logger, _destination
    if _logger is not None:
        return _logger

    try:
        from splunklib.searchcommands.environment import configure_logging

        configured, _ = configure_logging(APP_NAME)
    except Exception:
        configured = None

    if configured is not None:
        _logger, _destination = configured, "splunklib"
        return _logger

    logger = logging.getLogger(APP_NAME)
    if not logger.handlers:
        # splunkd collects a search command's stderr, so this is a real
        # destination and not a black hole.
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
    _logger, _destination = logger, "stderr"
    return _logger


def destination():
    """Return where lines are going: splunklib, stderr, or None if unused yet.

    Diagnostic only. Present so a test can assert the fallback was taken rather
    than inferring it.
    """
    return _destination


def reset():
    """Forget the configured logger. For tests only."""
    global _logger, _destination
    _logger = None
    _destination = None


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


def emit(component, event, outcome, level=logging.INFO, **fields):
    """Write one structured line. Never raises.

    A logging call is not allowed to break a search, so a refusal from
    format_line is caught here and turned into a line that names the refused
    keys and carries none of their values. That is deliberately visible: a
    developer sees it immediately, and a customer's log gets a harmless line
    instead of a stack trace in the middle of a result set.

    :param component: the module reporting.
    :param event: what happened.
    :param outcome: how it went.
    :param level: a logging level. Defaults to INFO.
    :param fields: any other whitelisted keys.
    """
    try:
        line = format_line(component, event, outcome, **fields)
    except (UnsupportedLogKey, UnsupportedLogValue) as error:
        line = _refusal_line(component, event, fields, error)
    except Exception:
        # Nothing below format_line should be able to reach here, and a logging
        # call still does not get to raise.
        line = "component={0} event=log outcome=refused reason=Exception".format(
            REPLACEMENT_CHARACTER
        )

    try:
        get_logger().log(level, "%s", line)
    except Exception:
        # A logger that cannot write is not a reason to fail a search. There is
        # nowhere left to report this, which is exactly why it is swallowed.
        pass


def _refusal_line(component, event, fields, error):
    """Build the substitute line for a refused call.

    Only key NAMES appear. A name is a literal written in this repository's own
    source, so it carries nothing; a value is the thing that might. Built out
    of whitelisted keys and pre-formatted strings so that it cannot itself be
    refused, with a constant as the last resort if even that fails.
    """
    try:
        names = ",".join(sorted(str(name) for name in fields)) or EMPTY_VALUE
        return format_line(
            _safe_label(component),
            _safe_label(event),
            "refused",
            reason=type(error).__name__,
            rejected=names,
        )
    except Exception:
        return "component=ps_log event=log outcome=refused reason=UnsupportedLogCall"


def _safe_label(value):
    """Coerce a component or event to something format_value will accept."""
    if isinstance(value, str) and value.strip():
        return value
    return "unknown"


def debug(component, event, outcome, **fields):
    """Emit at DEBUG.

    For lines that are one per record or one per lookup. A wide search can
    carry tens of thousands of hashes, and a per-hash line at INFO would put
    tens of thousands of lines in the customer's log to say that the cache
    worked. They are still written, so an operator debugging a cost problem can
    raise the level and see every hit and miss, which is the whole reason they
    exist.
    """
    return emit(component, event, outcome, level=logging.DEBUG, **fields)


def info(component, event, outcome, **fields):
    """Emit at INFO. For once-per-search and once-per-request lines."""
    return emit(component, event, outcome, level=logging.INFO, **fields)


def warning(component, event, outcome, **fields):
    """Emit at WARNING. For a degradation an operator should act on."""
    return emit(component, event, outcome, level=logging.WARNING, **fields)


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


class Timer(object):
    """Elapsed milliseconds since construction.

    Uses a monotonic clock, so a duration cannot come out negative because
    someone corrected the system time mid-search.
    """

    __slots__ = ("_clock", "_started")

    def __init__(self, clock=None):
        """
        :param clock: a callable returning seconds, for tests. Defaults to
            time.monotonic.
        """
        if clock is None:
            import time

            clock = time.monotonic
        self._clock = clock
        self._started = clock()

    @property
    def duration_ms(self):
        """Whole milliseconds elapsed. Never negative."""
        elapsed = self._clock() - self._started
        if elapsed < 0:
            return 0
        return int(round(elapsed * 1000))
