# Copyright 2026 Kamal Singh Bisht
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Render a preview of the events an eventgen stanza would produce.

This is a faithful-but-independent reimplementation of eventgen's token
replacement, used to answer "what will this config actually emit?" without
enabling a generator and waiting for an interval to elapse.

It is deliberately read-only and side-effect free: it never writes to an
index, a socket, or the spool directory.

Known simplifications, surfaced to the user in the UI:
  * Rating settings scale the reported count, not the wall-clock cadence.
  * ``replaytimestamp`` offsets are derived from the sampled events in view
    rather than from a full pass over the file.
  * Custom ``generator`` / ``rater`` plugins are not executed; their stanzas
    preview as the built-in behaviour.
"""

from __future__ import absolute_import, division, print_function

import csv
import datetime
import io
import json
import os
import random
import re
import string
import uuid

MAX_PREVIEW_EVENTS = 100
MAX_SAMPLE_BYTES = 2 * 1024 * 1024

DEFAULT_BREAKER = r"[^\r\n\s]+"

# Relative-time units accepted by Splunk's modifier syntax.
_TIME_UNITS = {
    "s": "seconds", "sec": "seconds", "secs": "seconds",
    "second": "seconds", "seconds": "seconds",
    "m": "minutes", "min": "minutes", "mins": "minutes",
    "minute": "minutes", "minutes": "minutes",
    "h": "hours", "hr": "hours", "hrs": "hours",
    "hour": "hours", "hours": "hours",
    "d": "days", "day": "days", "days": "days",
    "w": "weeks", "week": "weeks", "weeks": "weeks",
    "mon": "months", "month": "months", "months": "months",
    "y": "years", "yr": "years", "yrs": "years",
    "year": "years", "years": "years",
}

_RELATIVE_RE = re.compile(
    r"^(?P<sign>[+-])?(?P<num>\d+)?(?P<unit>[a-zA-Z]+)?(?:@(?P<snap>[a-zA-Z]+))?$"
)


class PreviewError(Exception):
    """Raised for malformed configuration that the user can fix."""


# --------------------------------------------------------------------------
# Time handling
# --------------------------------------------------------------------------


def _shift(dt, unit, amount):
    """Shift a datetime, approximating calendar months and years."""
    if unit == "months":
        month = dt.month - 1 + amount
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, _days_in_month(year, month))
        return dt.replace(year=year, month=month, day=day)
    if unit == "years":
        try:
            return dt.replace(year=dt.year + amount)
        except ValueError:  # Feb 29 in a non-leap year
            return dt.replace(year=dt.year + amount, day=28)
    return dt + datetime.timedelta(**{unit: amount})


def _days_in_month(year, month):
    if month == 12:
        nxt = datetime.date(year + 1, 1, 1)
    else:
        nxt = datetime.date(year, month + 1, 1)
    return (nxt - datetime.date(year, month, 1)).days


def _snap(dt, unit):
    """Snap a datetime down to the start of the given unit."""
    if unit == "seconds":
        return dt.replace(microsecond=0)
    if unit == "minutes":
        return dt.replace(second=0, microsecond=0)
    if unit == "hours":
        return dt.replace(minute=0, second=0, microsecond=0)
    if unit == "days":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if unit == "weeks":
        start = dt - datetime.timedelta(days=(dt.weekday() + 1) % 7)
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if unit == "months":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if unit == "years":
        return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt


def parse_relative_time(value, now=None):
    """Resolve a Splunk relative-time string such as ``-1h@h`` to a datetime."""
    now = now or datetime.datetime.now()
    if value is None:
        return now
    value = str(value).strip()
    if value == "" or value.lower() == "now":
        return now

    # Allow an already-formatted absolute timestamp to pass through.
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y:%H:%M:%S",
                "%Y-%m-%d"):
        try:
            parsed = datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=now.tzinfo)

    match = _RELATIVE_RE.match(value)
    if not match:
        raise PreviewError("Cannot read the time '%s'. Use a value like now, "
                           "-60m, or -1h@h." % value)

    parts = match.groupdict()
    result = now

    if parts["unit"] and parts["unit"].lower() in _TIME_UNITS:
        unit = _TIME_UNITS[parts["unit"].lower()]
        num = int(parts["num"] or 1)
        if parts["sign"] == "-":
            num = -num
        result = _shift(result, unit, num)
    elif parts["num"] or parts["unit"]:
        # Something was written that is not a unit we recognise.
        if parts["unit"] and parts["unit"].lower() not in _TIME_UNITS:
            raise PreviewError("'%s' is not a time unit. Use s, m, h, d, w, "
                               "mon, or y." % parts["unit"])

    if parts["snap"]:
        snap_unit = _TIME_UNITS.get(parts["snap"].lower())
        if not snap_unit:
            raise PreviewError("'%s' is not a snap unit." % parts["snap"])
        result = _snap(result, snap_unit)

    return result


_TZ_OFFSET_RE = re.compile(r"^(?P<sign>[+-])?(?P<hh>\d{2})(?P<mm>\d{2})$")


def resolve_timezone(value):
    """Turn the ``timezone`` setting into a tzinfo.

    ``local`` (or unset) uses the server's zone, ``0000`` means UTC, and an
    offset such as ``-0500`` or ``+0530`` is taken literally.
    """
    if value is None or str(value).strip() == "":
        return datetime.datetime.now().astimezone().tzinfo

    text = str(value).strip()
    if text.lower() == "local":
        return datetime.datetime.now().astimezone().tzinfo

    match = _TZ_OFFSET_RE.match(text)
    if not match:
        raise PreviewError(
            "timezone '%s' is not valid. Use local, 0000 for UTC, or an "
            "offset such as -0500." % value)

    hours = int(match.group("hh"))
    minutes = int(match.group("mm"))
    if minutes > 59:
        raise PreviewError(
            "timezone '%s' has more than 59 minutes. The last two digits are "
            "minutes." % value)
    if hours > 23:
        raise PreviewError(
            "timezone '%s' is out of range. Valid values run from -2359 to "
            "+2359." % value)

    delta = datetime.timedelta(hours=hours, minutes=minutes)
    if match.group("sign") == "-":
        delta = -delta
    return datetime.timezone(delta)


def _random_between(earliest, latest):
    """Pick a uniform random datetime in the (possibly zero-width) range."""
    if latest < earliest:
        earliest, latest = latest, earliest
    span = (latest - earliest).total_seconds()
    if span <= 0:
        return earliest
    return earliest + datetime.timedelta(seconds=random.uniform(0, span))


def strftime(dt, fmt):
    """Format a datetime, adding support for the epoch-seconds directive."""
    if "%s" in fmt:
        # %s is not portable through datetime.strftime; substitute it first.
        epoch = int(dt.timestamp())
        fmt = fmt.replace("%s", str(epoch))
    try:
        return dt.strftime(fmt)
    except (ValueError, TypeError) as exc:
        raise PreviewError("Cannot apply the time format '%s': %s" % (fmt, exc))


# --------------------------------------------------------------------------
# Replacement value generation
# --------------------------------------------------------------------------


_INT_RANGE_RE = re.compile(r"^integer\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]$", re.I)
_FLOAT_RANGE_RE = re.compile(
    r"^float\[\s*(-?\d+(?:\.\d+)?)\s*:\s*(-?\d+(?:\.\d+)?)\s*\]$", re.I)
_STRING_RE = re.compile(r"^string\(\s*(\d+)\s*\)$", re.I)
_HEX_RE = re.compile(r"^hex\(\s*(\d+)\s*\)$", re.I)
_LIST_RE = re.compile(r"^list(\[.*\])$", re.I | re.S)


def _random_ipv4():
    return "%d.%d.%d.%d" % (random.randint(1, 254), random.randint(0, 255),
                            random.randint(0, 255), random.randint(1, 254))


def _random_ipv6():
    return ":".join("%04x" % random.randint(0, 0xFFFF) for _ in range(8))


def _random_mac():
    return ":".join("%02x" % random.randint(0, 255) for _ in range(6))


def _random_float(start, end, precision):
    value = random.uniform(float(start), float(end))
    return "%.*f" % (precision, value)


def _float_precision(start_literal):
    if "." in start_literal:
        return len(start_literal.split(".", 1)[1])
    return 0


class ReplacementFiles(object):
    """Loads and caches the list/CSV files referenced by file and mvfile tokens."""

    def __init__(self, search_dirs, splunk_home=None):
        self.search_dirs = [d for d in search_dirs if d]
        self.splunk_home = splunk_home or os.environ.get("SPLUNK_HOME", "")
        self._cache = {}
        self.missing = []

    def _resolve(self, raw_path):
        path = raw_path.strip().replace("\\\\", os.sep).replace("\\", os.sep)
        if self.splunk_home:
            path = path.replace("$SPLUNK_HOME", self.splunk_home)
        path = os.path.expandvars(path)

        candidates = []
        if os.path.isabs(path):
            candidates.append(path)
        else:
            for base in self.search_dirs:
                candidates.append(os.path.join(base, path))
            # Also try the bare filename inside each search directory.
            for base in self.search_dirs:
                candidates.append(os.path.join(base, os.path.basename(path)))

        for candidate in candidates:
            normalised = os.path.normpath(candidate)
            if os.path.isfile(normalised):
                return normalised
        return None

    def lines(self, raw_path):
        if raw_path in self._cache:
            return self._cache[raw_path]

        resolved = self._resolve(raw_path)
        if resolved is None:
            if raw_path not in self.missing:
                self.missing.append(raw_path)
            self._cache[raw_path] = []
            return []

        try:
            with io.open(resolved, "r", encoding="utf-8",
                         errors="replace") as handle:
                rows = [line.rstrip("\r\n") for line in handle
                        if line.strip() != ""]
        except (IOError, OSError):
            if raw_path not in self.missing:
                self.missing.append(raw_path)
            rows = []

        self._cache[raw_path] = rows
        return rows


class TokenReplacer(object):
    """Applies one configured token to an event."""

    def __init__(self, index, token_regex, replacement_type, replacement,
                 files, rating=1.0):
        self.index = index
        self.raw_regex = token_regex
        self.replacement_type = (replacement_type or "").strip().lower()
        self.replacement = replacement if replacement is not None else ""
        self.files = files
        self.rating = rating
        self._counter = None
        self._mvfile_rows = {}

        try:
            self.regex = re.compile(token_regex)
        except re.error as exc:
            raise PreviewError(
                "token.%s.token is not a valid regular expression: %s"
                % (index, exc))

        if self.replacement_type == "integerid":
            try:
                self._counter = int(str(self.replacement).strip() or 0)
            except ValueError:
                raise PreviewError(
                    "token.%s.replacement must be a whole number when the "
                    "type is integerid." % index)

    # -- value generation --------------------------------------------------

    def _value_random(self, spec):
        spec = spec.strip()
        lowered = spec.lower()

        if lowered == "guid":
            return str(uuid.uuid4())
        if lowered == "ipv4":
            return _random_ipv4()
        if lowered == "ipv6":
            return _random_ipv6()
        if lowered == "mac":
            return _random_mac()

        match = _INT_RANGE_RE.match(spec)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            if end < start:
                start, end = end, start
            value = random.randint(start, end)
            if self.replacement_type == "rated":
                value = int(round(value * self.rating))
            return str(value)

        match = _FLOAT_RANGE_RE.match(spec)
        if match:
            precision = _float_precision(match.group(1))
            start, end = float(match.group(1)), float(match.group(2))
            if end < start:
                start, end = end, start
            if self.replacement_type == "rated":
                value = random.uniform(start, end) * self.rating
                return "%.*f" % (precision, value)
            return _random_float(start, end, precision)

        match = _STRING_RE.match(spec)
        if match:
            length = int(match.group(1))
            alphabet = string.ascii_letters + string.digits
            return "".join(random.choice(alphabet) for _ in range(length))

        match = _HEX_RE.match(spec)
        if match:
            length = int(match.group(1))
            return "".join(random.choice("0123456789ABCDEF")
                           for _ in range(length))

        match = _LIST_RE.match(spec)
        if match:
            try:
                items = json.loads(match.group(1))
            except ValueError:
                raise PreviewError(
                    "token.%s.replacement has a list that is not valid JSON. "
                    'Use list["a", "b", "c"].' % self.index)
            if not items:
                return ""
            return str(random.choice(items))

        raise PreviewError(
            "token.%s.replacement '%s' is not a random type. Use guid, ipv4, "
            "ipv6, mac, integer[a:b], float[a:b], string(n), hex(n), or "
            'list["a","b"].' % (self.index, spec))

    def _value_file(self, spec):
        rows = self.files.lines(spec)
        if not rows:
            return ""
        return random.choice(rows)

    def _value_mvfile(self, spec, shared_rows):
        if ":" not in spec:
            raise PreviewError(
                "token.%s.replacement needs a column, for example "
                "users.sample:2" % self.index)
        path, column = spec.rsplit(":", 1)
        try:
            column_index = int(column) - 1
        except ValueError:
            raise PreviewError(
                "token.%s.replacement column '%s' must be a number."
                % (self.index, column))
        if column_index < 0:
            raise PreviewError(
                "token.%s.replacement columns start at 1." % self.index)

        rows = self.files.lines(path)
        if not rows:
            return ""

        # Tokens pointing at the same file share a row within an event, which
        # is how eventgen keeps multi-column values consistent.
        if path not in shared_rows:
            shared_rows[path] = random.choice(rows)
        row = shared_rows[path]

        try:
            fields = next(csv.reader([row]))
        except (csv.Error, StopIteration):
            fields = row.split(",")
        if column_index >= len(fields):
            return ""
        return fields[column_index]

    def value(self, event_time, shared_rows, replay_time=None):
        kind = self.replacement_type
        spec = str(self.replacement)

        if kind == "static":
            return spec
        if kind == "timestamp":
            return strftime(event_time, spec)
        if kind == "replaytimestamp":
            if spec.strip().startswith("["):
                try:
                    formats = json.loads(spec)
                except ValueError:
                    raise PreviewError(
                        "token.%s.replacement is not a valid JSON list of "
                        "time formats." % self.index)
                spec = formats[0] if formats else "%Y-%m-%d %H:%M:%S"
            return strftime(replay_time or event_time, spec)
        if kind in ("random", "rated"):
            return self._value_random(spec)
        if kind == "file":
            return self._value_file(spec)
        if kind == "mvfile":
            return self._value_mvfile(spec, shared_rows)
        if kind == "integerid":
            current = self._counter
            self._counter += 1
            return str(current)

        raise PreviewError(
            "token.%s.replacementType '%s' is not recognised."
            % (self.index, kind))

    # -- application -------------------------------------------------------

    def apply(self, event, event_time, shared_rows, replay_time=None,
              spans=None):
        """Replace every occurrence, generating a fresh value for each.

        Returns the rewritten event, how many replacements were made, and the
        character ranges now occupied by generated values. Ranges recorded by
        earlier tokens are carried forward so the UI can highlight every
        substitution, no matter which token produced it.
        """
        spans = spans or []
        edits = []

        for match in self.regex.finditer(event):
            if match.groups():
                start, end = match.span(1)
                if start < 0:  # optional group that did not participate
                    continue
            else:
                start, end = match.span(0)

            if end < start:
                continue

            edits.append((start, end,
                          self.value(event_time, shared_rows, replay_time)))

            if len(edits) > 500:  # runaway pattern guard
                break

        if not edits:
            return event, 0, spans

        parts = []
        kept_regions = []   # (old_start, old_end, new_start)
        new_spans = []
        position = 0
        length = 0

        for start, end, value in edits:
            kept = event[position:start]
            kept_regions.append((position, start, length))
            parts.append(kept)
            length += len(kept)

            new_spans.append((length, length + len(value)))
            parts.append(value)
            length += len(value)
            position = end

        tail = event[position:]
        kept_regions.append((position, len(event), length))
        parts.append(tail)

        def remap(offset):
            for old_start, old_end, new_start in kept_regions:
                if old_start <= offset <= old_end:
                    return new_start + (offset - old_start)
            return None

        for span_start, span_end in spans:
            mapped_start = remap(span_start)
            mapped_end = remap(span_end)
            if mapped_start is None or mapped_end is None:
                continue  # this range was overwritten by the current token
            new_spans.append((mapped_start, mapped_end))

        return "".join(parts), len(edits), merge_spans(new_spans)


def merge_spans(spans):
    """Sort and coalesce overlapping or touching character ranges."""
    ordered = sorted(span for span in spans if span[1] > span[0])
    merged = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def to_segments(text, spans):
    """Split an event into alternating original and generated pieces."""
    segments = []
    position = 0
    for start, end in spans:
        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))
        if start > position:
            segments.append({"t": text[position:start], "g": False})
        if end > start:
            segments.append({"t": text[start:end], "g": True})
        position = end
    if position < len(text):
        segments.append({"t": text[position:], "g": False})
    return segments


# --------------------------------------------------------------------------
# Sample parsing
# --------------------------------------------------------------------------


def split_events(sample_text, stanza):
    """Break raw sample text into the events eventgen would work with."""
    if _is_true(stanza.get("bundlelines")):
        return [sample_text.strip("\r\n")] if sample_text.strip() else []

    breaker = stanza.get("breaker", DEFAULT_BREAKER) or DEFAULT_BREAKER
    if breaker.strip() == DEFAULT_BREAKER:
        return [line for line in sample_text.splitlines() if line.strip() != ""]

    try:
        pattern = re.compile(breaker)
    except re.error as exc:
        raise PreviewError("breaker is not a valid regular expression: %s"
                           % exc)

    pieces = [piece.strip("\r\n") for piece in pattern.split(sample_text)]
    events = [piece for piece in pieces if piece and piece.strip() != ""]
    if not events and sample_text.strip():
        # A breaker that never matches yields one iteration of the sample.
        return [sample_text.strip("\r\n")]
    return events


def parse_csv_sample(sample_text):
    """Return (events, metadata_rows) for a sampletype = csv sample."""
    reader = csv.DictReader(io.StringIO(sample_text))
    events, metadata = [], []
    for row in reader:
        raw = row.get("_raw")
        if raw is None:
            continue
        events.append(raw)
        metadata.append({key: value for key, value in row.items()
                         if key in ("host", "source", "sourcetype", "index")
                         and value})
    return events, metadata


# --------------------------------------------------------------------------
# Rating
# --------------------------------------------------------------------------


def _load_rate(stanza, key):
    raw = stanza.get(key)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise PreviewError("%s is not valid JSON." % key)
    if not isinstance(parsed, dict):
        raise PreviewError("%s must be a JSON object such as "
                           '{"0": 1, "1": 0.5}.' % key)
    return parsed


def compute_rating(stanza, when):
    """Multiply the configured rate curves for a point in time."""
    rating = 1.0
    applied = {}

    curves = (
        ("hourOfDayRate", str(when.hour)),
        ("dayOfWeekRate", str((when.weekday() + 1) % 7)),
        ("minuteOfHourRate", str(when.minute)),
        ("dayOfMonthRate", str(when.day)),
        ("monthOfYearRate", str(when.month)),
    )

    for key, lookup in curves:
        table = _load_rate(stanza, key)
        if not table:
            continue
        if lookup in table:
            try:
                factor = float(table[lookup])
            except (TypeError, ValueError):
                raise PreviewError("%s contains a non-numeric value for key "
                                   "'%s'." % (key, lookup))
            rating *= factor
            applied[key] = factor

    return rating, applied


def _is_true(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _as_float(value, default=0.0):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Token extraction
# --------------------------------------------------------------------------


_TOKEN_KEY_RE = re.compile(r"^token\.(\d+)\.(token|replacementType|replacement)$")


def extract_tokens(stanza):
    """Collect token.N.* keys into an ordered list of definitions."""
    collected = {}
    for key, value in stanza.items():
        match = _TOKEN_KEY_RE.match(key.strip())
        if not match:
            continue
        index = int(match.group(1))
        collected.setdefault(index, {})[match.group(2)] = value

    tokens = []
    for index in sorted(collected):
        definition = collected[index]
        if not definition.get("token"):
            continue
        tokens.append({
            "index": index,
            "token": definition.get("token"),
            "replacementType": definition.get("replacementType", "static"),
            "replacement": definition.get("replacement", ""),
        })
    return tokens


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def render(stanza, sample_text, search_dirs=None, limit=20, seed=None):
    """Produce a preview of the events this stanza would generate.

    Returns a dict with rendered events, the effective settings that shaped
    them, and any warnings worth showing the user.
    """
    if seed is not None:
        random.seed(seed)

    if sample_text is None:
        sample_text = ""
    if len(sample_text.encode("utf-8", "ignore")) > MAX_SAMPLE_BYTES:
        sample_text = sample_text[:MAX_SAMPLE_BYTES]

    limit = max(1, min(int(limit or 20), MAX_PREVIEW_EVENTS))
    warnings = []

    files = ReplacementFiles(search_dirs or [])

    # --- pick the events to work with ---
    metadata_rows = []
    if str(stanza.get("sampletype", "raw")).strip().lower() == "csv":
        source_events, metadata_rows = parse_csv_sample(sample_text)
        if not source_events:
            warnings.append(
                "No events found. A csv sample needs a header row with a "
                "_raw column.")
    else:
        source_events = split_events(sample_text, stanza)

    if not source_events:
        return {
            "events": [],
            "warnings": warnings or ["The sample is empty."],
            "settings": {},
            "tokens": [],
        }

    tzinfo = resolve_timezone(stanza.get("timezone"))
    now = datetime.datetime.now(tz=tzinfo)
    earliest = parse_relative_time(stanza.get("earliest", "now"), now)
    latest = parse_relative_time(stanza.get("latest", "now"), now)

    rating, applied_rates = compute_rating(stanza, now)

    count = _as_int(stanza.get("count"), 0)
    randomize = _as_float(stanza.get("randomizeCount"), 0.0)

    effective_count = count if count > 0 else len(source_events)
    if applied_rates:
        effective_count = int(round(effective_count * rating))
    if randomize > 0:
        low = int(round(effective_count * (1 - randomize)))
        high = int(round(effective_count * (1 + randomize)))
        effective_count = random.randint(max(0, low), max(0, high))

    mode = str(stanza.get("mode", "sample")).strip().lower()
    per_day_volume = stanza.get("perDayVolume")
    if per_day_volume:
        warnings.append(
            "perDayVolume is set, so eventgen sizes each interval by target "
            "volume rather than count. The preview shows sample events only.")

    # --- choose which events appear in the preview ---
    shown = min(limit, max(1, effective_count))
    if _is_true(stanza.get("randomizeEvents")) and mode != "replay":
        pool = list(source_events)
        random.shuffle(pool)
    else:
        pool = source_events

    selected = []
    for position in range(shown):
        selected.append(pool[position % len(pool)])

    # --- build the token replacers ---
    tokens = extract_tokens(stanza)
    replacers = []
    for definition in tokens:
        replacers.append(TokenReplacer(
            definition["index"],
            definition["token"],
            definition["replacementType"],
            definition["replacement"],
            files,
            rating,
        ))

    host_token = stanza.get("host.token")
    host_replacement = stanza.get("host.replacement")

    # --- render ---
    interval = _as_int(stanza.get("interval"), 60)
    time_multiple = _as_float(stanza.get("timeMultiple"), 1.0) or 1.0

    rendered = []
    total_replacements = 0
    replay_base = parse_relative_time(stanza.get("earliest", "now"), now)

    for position, raw_event in enumerate(selected):
        if mode == "replay":
            offset = position * max(1.0, time_multiple)
            event_time = replay_base + datetime.timedelta(seconds=offset)
            replay_time = event_time
        else:
            event_time = _random_between(earliest, latest)
            replay_time = event_time

        shared_rows = {}
        event = raw_event
        matched_tokens = []
        spans = []

        for replacer in replacers:
            event, replaced, spans = replacer.apply(
                event, event_time, shared_rows, replay_time, spans)
            if replaced:
                matched_tokens.append(replacer.index)
                total_replacements += replaced

        entry = {
            "index": position + 1,
            "raw": event,
            "original": raw_event,
            "segments": to_segments(event, spans),
            "time": event_time.isoformat(sep=" ", timespec="seconds"),
            "tokensApplied": matched_tokens,
        }

        if position < len(metadata_rows):
            entry["metadata"] = metadata_rows[position]
        if host_token and host_replacement:
            entry["hostReplaced"] = True

        rendered.append(entry)

    # --- warnings the user can act on ---
    unmatched = [replacer.index for replacer in replacers
                 if not any(replacer.index in item["tokensApplied"]
                            for item in rendered)]
    if unmatched:
        warnings.append(
            "These tokens did not match anything in the sample: %s. Check the "
            "regular expression in each one."
            % ", ".join("token.%d" % index for index in unmatched))

    if files.missing:
        warnings.append(
            "These replacement files were not found: %s. Upload them as "
            "sample files or use a full path."
            % ", ".join(files.missing))

    if not replacers and not host_token:
        warnings.append(
            "No tokens are configured, so every event will be emitted exactly "
            "as it appears in the sample.")

    if _is_true(stanza.get("disabled")):
        warnings.append(
            "This configuration is turned off. Turn it on to start "
            "generating events.")

    settings = {
        "mode": mode,
        "sampletype": str(stanza.get("sampletype", "raw")),
        "interval": interval,
        "eventsInSample": len(source_events),
        "eventsPerInterval": effective_count,
        "eventsShown": len(rendered),
        "earliest": earliest.isoformat(sep=" ", timespec="seconds"),
        "latest": latest.isoformat(sep=" ", timespec="seconds"),
        "rating": round(rating, 4),
        "ratesApplied": applied_rates,
        "outputMode": str(stanza.get("outputMode", "modinput")),
        "index": str(stanza.get("index", "main")),
        "sourcetype": str(stanza.get("sourcetype", "eventgen")),
        "source": str(stanza.get("source", "")),
        "replacements": total_replacements,
    }

    if interval > 0 and effective_count:
        settings["eventsPerDay"] = int(
            round(effective_count * (86400.0 / interval)))

    return {
        "events": rendered,
        "warnings": warnings,
        "settings": settings,
        "tokens": tokens,
    }
