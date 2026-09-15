"""RansomLeak API client for the Splunk add-on.

Deliberately free of Splunk imports so it can be unit-tested without a Splunk
instance. The modular input supplies a transport; production uses `requests`.
"""

import collections
import hashlib
import json
from datetime import datetime, timedelta, timezone

PHISHING_EVENTS_PATH = "/api/external/phishing-events"
# The keyset-cursor pull route the audit input reads. Deliberately a DIFFERENT
# path from `/api/external/security-events/export`, which orders timestamp DESC,
# truncates at 10000 rows and offers no cursor; `/export` still backs the admin
# CSV download and is not this add-on's surface.
SECURITY_EVENTS_PULL_PATH = "/api/external/security-events"
COMPLIANCE_EVIDENCE_PATH = "/api/external/compliance/evidence"
# The Grafana data-source query surface, shared by the `ransomleak_risk` and
# `ransomleak_metrics` inputs. Guarded by `@PartnerIntegrationAuth()`, i.e. the
# **`integration`** token scope -- NOT the `phishing` / `security_events` /
# `compliance` scopes the other three inputs use. A token minted for those gets
# a 403 here and nothing in the response says why, which is why the scope is
# called out in the README and in both inputs' help text.
GRAFANA_QUERY_PATH = "/api/integration/grafana/query"
# The one WRITE surface the add-on touches: the `ransomleak_assign_training`
# alert action. Guarded by the same `@PartnerIntegrationAuth()` -- i.e. the
# **`integration`** scope -- as `GRAFANA_QUERY_PATH`, so one account serves both
# the two aggregate inputs and the alert action. A token minted for the
# `phishing` / `security_events` / `compliance` scopes gets a 403 here with
# nothing in the body naming the scope, which is why the alert action's help
# text says so out loud.
ASSIGNMENTS_PATH = "/api/integration/assignments"
_ISO = "%Y-%m-%dT%H:%M:%S.%fZ"

# The envelope field every event carries as its FIRST key, and the only field
# `props.conf` extracts `_time` from. Defined here, above its own section, so
# `_GRAFANA_RESERVED_FIELDS` below can name it rather than repeat the string.
# See `event_payload` for what it is and props.conf's header for why.
EVENT_TIME_FIELD = "rlEventTime"

# The metric names `POST /api/integration/grafana/query` accepts, in the order
# `POST /search` returns them. Hand-mirrored from
# `backend/src/integration/constants/grafana-metrics.constant.ts`, and the
# backend comment there is explicit that renaming one is a breaking change for
# every installed dashboard.
#
# Drift here is LOUD: the request body is validated by `@IsIn(GRAFANA_METRICS)`
# server-side, so a name this add-on has but the backend does not comes back 400
# with the metric named, and the collector logs it and keeps going with the
# others. A name the backend has and this list does not simply cannot be
# selected in the input UI. Neither loses data silently, which is why this list
# needs no CI parity check.
GRAFANA_METRICS = [
    "human_risk_score",
    "training_completion_rate",
    "assignments_overdue",
    "phishing_click_rate",
    "phishing_report_rate",
    "overdue_users",
    "assignments_by_category",
    "auto_assigned_via_grafana",
]

# The metrics whose result the `channel` facet actually narrows. The DTO accepts
# `channel` on any metric and the service ignores it everywhere else, so sending
# it unconditionally would be harmless on the wire -- but the emitted event
# stamps the facets it was queried with, and a `channel=sms` field on a training
# completion event is a lie an operator would reasonably act on.
GRAFANA_CHANNEL_METRICS = frozenset(["phishing_click_rate", "phishing_report_rate"])

# Keys the emitted event body owns. A table column whose `text` collides with
# one is prefixed rather than allowed to overwrite it: losing `metric` to a
# column named `metric` would make the event unattributable, and the overwrite
# would be silent.
#
# The facets are `queryTeam` / `queryChannel` and NOT `team` / `channel`
# precisely so this set can stay this small. `overdue_users` returns a column
# called `team` -- verified against the live endpoint -- and with the shorter
# names the guard fired on it and renamed the row's own team to `column_team`.
# That is the wrong way round: the column is the data an operator searches on,
# while the facet is metadata about the QUERY (it describes what was asked for,
# not what the row is) and is the one that should carry the qualified name.
_GRAFANA_RESERVED_FIELDS = frozenset(
    ["metric", "format", "queryTeam", "queryChannel", EVENT_TIME_FIELD])

# Upper bound on the `(metric, target, bucket)` digests one input's checkpoint
# carries, mirroring the training input's `max_tracked` ceiling and degrading
# the same way: change detection off, every bucket emitted, loud warning. Two
# facets' worth of the widest metric over the longest permitted window stays
# three orders of magnitude below this, so it is a backstop and not a tuning
# knob -- deliberately a module constant, because docs/follow-ups.md already
# records `max_tracked` as one published knob too many.
MAX_TRACKED_BUCKETS = 100000

# Rows per request on the cursor route. The server defaults to 1000 and caps at
# 5000. Deliberately a module constant rather than a customer knob: the value
# only trades request count against response size, no operator can choose it
# better than the default, and docs/follow-ups.md already records `max_tracked`
# as one knob too many on a configuration surface about to be published.
AUDIT_PAGE_SIZE = 1000

# Substring the backend uses when the `after` cursor names a row it cannot find
# ("Unknown cursor: no security event '<id>' exists for this tenant."). Matched
# case-insensitively against the response body, because the SHAPE of the error
# body is not part of the contract but this sentence is: it is the only thing
# distinguishing a purged cursor -- which is routine, and recoverable -- from a
# genuinely malformed request such as `limit=6000`, which is a misconfiguration
# that must stay loud. Treating every 400 as a stale cursor would silently paper
# over the second class.
_UNKNOWN_CURSOR_MARKER = "unknown cursor"

# How many stale-cursor recoveries one run may make before it gives up and lets
# the error out. Retention deleting several of the rows a long backfill is
# paging through is plausible, so this is not 1; a server answering "unknown
# cursor" to everything is also plausible, and an unbounded retry there would
# hang the input with no error and no events instead of failing it.
_MAX_STALE_CURSOR_RECOVERIES = 10

# Upper bound on the ids the audit checkpoint carries. The retained set is
# otherwise bounded only by the lookback window, and `lookback_hours` validates
# up to 999 (~41 days): a ~10k-events/day tenant would retain ~400k UUIDs, some
# 16MB once JSON-encoded — past MongoDB's per-document limit. `store.update`
# then fails AFTER the events have been written, so the input re-emits its whole
# window every interval and never checkpoints. 100000 mirrors the ceiling the
# training input's `max_tracked` validates to, so both inputs degrade at the
# same order of magnitude.
#
# Deliberately a module constant rather than a customer knob: docs/follow-ups.md
# already records `max_tracked` as a Splunk implementation detail no operator
# can choose better than the default, and adding a second one would widen the
# published configuration surface right before Splunkbase submission.
MAX_SEEN_IDS = 100000

# How large the in-flight retention list may grow before it is compacted against
# the current floor. Compaction runs at most once per page, so the list is
# bounded by roughly `max(this, 2 * MAX_SEEN_IDS)` plus one page's rows —
# never by the length of the feed.
_RETAIN_COMPACT_MIN = 4096


def parse_iso(value):
    """Parse the API's ISO 8601 form. Python 3.9 cannot parse a trailing 'Z'.

    The backend renders every timestamp through JavaScript's `Date.toISOString()`,
    which is always `YYYY-MM-DDTHH:mm:ss.sssZ` — i.e. always UTC. The returned
    datetime is naive; callers that need an epoch must attach `timezone.utc`
    themselves rather than relying on the host's local zone.

    Public because the modular input needs it to stamp `_time` on each event.
    """
    return datetime.strptime(value, _ISO)


def parse_iso_or_none(value):
    """`parse_iso`, but `None` instead of an exception on an unusable value.

    The empty string is a DOCUMENTED, REACHABLE value in the contract, not a
    theoretical one: `external-compliance.controller.ts` projects
    `assignedAt: toIso(row.enrollment.assignedAt) ?? ''`, and `toIso` returns
    null for a null or unparsable date. `parse_iso('')` raises `ValueError`, and
    the modular inputs parse timestamps inside their single per-input `try`, so
    ONE malformed row aborts the entire tenant feed — no events for any row, no
    checkpoint update, repeating every interval until someone fixes that one
    enrollment. Callers must degrade per row instead.

    Catches `TypeError` as well as `ValueError` so a null (JSON `null` → `None`)
    is handled by the same path as an empty or malformed string.
    """
    if not value:
        return None
    try:
        return parse_iso(value)
    except (TypeError, ValueError):
        return None


def event_epoch(value):
    """Epoch seconds for an API timestamp, or `None` when it cannot be parsed.

    Lives here, not in the helpers, for two reasons. It is the per-row
    degradation point for the malformed-timestamp case above, and it is the one
    place `.replace(tzinfo=timezone.utc)` appears — a helper that re-typed that
    expression at its call site could lose it and shift every event's `_time` by
    the indexer's UTC offset with no test noticing, because the helpers cannot
    be imported without Splunk's libraries.
    """
    parsed = parse_iso_or_none(value)
    if parsed is None:
        return None
    return parsed.replace(tzinfo=timezone.utc).timestamp()


def observation_epoch(now=None):
    """`_time` for an event that reports an OBSERVATION, not an occurrence.

    `ransomleak:training` is the caller. That input polls a full state
    projection and emits a row whenever its content digest changes, so the
    event's subject is "the add-on saw this row change", and the instant that
    happened is now. It used to stamp `_time = assignedAt`, which put a
    completion observed today at the moment the training was assigned --
    possibly months earlier. That made the events invisible to recent-time
    searches (so completion alerting could not work at all), gave every change
    event for one enrollment the same `_time` (so `latest()` picked among them
    arbitrarily), and on an index with a short `frozenTimePeriodInSecs` aged
    them out on arrival. `assignedAt`, `completedAt` and `dueAt` all still ship
    verbatim in the event body, so a search that wants assignment time reads
    the field.

    Not used by `ransomleak:audit` or `ransomleak:phishing`: their `timestamp` /
    `occurredAt` genuinely are the event's own occurrence time.

    Takes `now` so a test can pin it. Lives here rather than inline in the
    helper for the same reason `event_epoch` does: this is the one place the
    `timezone.utc` attachment appears, the helpers cannot be imported without
    Splunk's libraries, and a naive `datetime.now().timestamp()` at the call
    site would shift every event by the indexer's UTC offset with no test
    noticing.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return now.timestamp()


def _format_iso(value):
    return value.strftime(_ISO)[:-4] + "Z"


# ── The one field `_time` is extracted from ────────────────────────────────
#
# Every event this add-on writes carries `EVENT_TIME_FIELD` (declared at the top
# of this module) as its FIRST key, and `props.conf` extracts `_time` from it
# with an anchored `TIME_PREFIX`. The anchor is the whole point: see props.conf's
# header for the measurements.
#
# The regex `props.conf` uses, duplicated here so a test can execute Splunk's
# rule -- "first match in the raw event wins" -- against real serialized bodies
# rather than merely reading the conf back. `tests/test_ransomleak_client.py`
# asserts the two are byte-identical, so they cannot drift.
#
# `^\{` is load-bearing and is the answer to the trap the previous wave hit: an
# unanchored `"(?:...|timestamp)":\s*"` alternation would match a `"timestamp"`
# key nested INSIDE `ransomleak:audit`'s unbounded `metadata` object, which is
# serialized BEFORE the DTO's own `timestamp`, and Splunk takes the first match.
# Anchored at the opening brace, only the first key of the top-level object can
# ever match -- and `event_payload` below makes that key `rlEventTime` by
# construction. No nesting depth, no key name and no field order in any payload
# can reach position zero.
EVENT_TIME_PREFIX = r'^\{"' + EVENT_TIME_FIELD + r'":\s*"'

# Bounds on an epoch this module will render. `datetime.fromtimestamp` raises
# OSError on a pre-1970 value on some platforms, and one raise inside a helper's
# single per-input `try` costs the whole tenant its feed -- the exact failure
# `parse_iso_or_none` exists to prevent. Clamping instead puts an absurd
# timestamp at an absurd, VISIBLE `_time` rather than aborting the input. The
# bounds are 1970-01-01 and 9999-12-31, the widest range `%Y` can express.
_MIN_RENDERABLE_EPOCH = 0.0
_MAX_RENDERABLE_EPOCH = 253402300799.999


def epoch_to_iso(epoch):
    """Epoch seconds -> the exact form `props.conf`'s `TIME_FORMAT` reads.

    Millisecond precision, always UTC, always the same width -- because a
    `TIME_FORMAT` is a fixed shape and a value that sometimes carried
    microseconds and sometimes none would parse for some events and not others.
    """
    clamped = min(max(float(epoch), _MIN_RENDERABLE_EPOCH), _MAX_RENDERABLE_EPOCH)
    return _format_iso(datetime.fromtimestamp(clamped, timezone.utc))


def event_payload(body, epoch):
    """The exact bytes one modular-input event carries.

    Every helper writes `data=event_payload(body, epoch)`. Three properties, all
    of which `_time` depends on:

    1. `EVENT_TIME_FIELD` is the FIRST key of the serialized object, so
       `EVENT_TIME_PREFIX`'s `^\\{` anchor matches it and can match nothing else.
    2. Its value is rendered by this module from the same epoch the caller
       stamps as `<time>`, so the event body and `_time` cannot disagree, and no
       payload field's format, presence or position is load-bearing.
    3. A payload that already carries the name cannot displace it -- the
       colliding value is kept, renamed, so nothing is lost.

    WHY EXTRACTION AT ALL, when the input also passes an explicit `<time>`:
    because on Splunk 10.4.2 the explicit stamp is NOT authoritative.
    `DATETIME_CONFIG = CURRENT` keeps only its sub-second fraction and takes the
    whole second from arrival (measured: 1181/1181 audit events, 264 distinct
    fractions, three arrival seconds), and leaving timestamp configuration off
    entirely falls back to auto-detection, which fails SILENTLY. Extraction from
    a field this module controls is the only arrangement that is both correct
    and loud when it breaks. See props.conf's header.
    """
    stamped = {EVENT_TIME_FIELD: epoch_to_iso(epoch)}
    for key, value in body.items():
        stamped[EVENT_TIME_FIELD + "_payload" if key == EVENT_TIME_FIELD else key] = value
    return json.dumps(stamped, ensure_ascii=False, default=str)


class ApiError(Exception):
    """A non-2xx response, carrying the status code and a slice of the body.

    The transport is a plain callable that tests replace wholesale, so its error
    contract has to be expressible without importing `requests` -- otherwise a
    fake could not reproduce a 404 or a 400 faithfully and every decision the
    collectors make about status codes would be tested against an invented
    exception shape rather than the real one. `requests.raise_for_status()`
    raises an exception whose status is reachable only through `.response`,
    which is exactly that dependency; this type replaces it.

    Both fields are load-bearing. `status` keeps a 404 or a 401 legible in the
    log line the input writes; `body` is what separates a purged cursor from a
    bad `limit`, since both are 400.
    """

    def __init__(self, status, body="", url=None):
        super().__init__("HTTP %s from %s: %s" % (status, url or "the API", (body or "")[:200]))
        self.status = status
        self.body = body or ""
        self.url = url


def is_unknown_cursor_error(error):
    """Is this the backend telling us our `after` cursor no longer exists?

    True only for a 400 whose body names the cursor. The retention cron deletes
    old security events, so the row a checkpoint points at is routinely gone;
    the backend answers 400 rather than an empty page precisely so a consumer
    cannot read "your cursor is dead" as "you are caught up". That case is
    recoverable without re-ingesting anything (resume from the high-water
    timestamp). Every other 400 -- `limit` out of range, a malformed date, a
    blank event type -- is a misconfiguration that must not be swallowed, and a
    status-only test would swallow all of them.
    """
    return (getattr(error, "status", None) == 400
            and _UNKNOWN_CURSOR_MARKER in getattr(error, "body", "").lower())


def _requests_transport(url, headers, params, verify, method="GET", json_body=None):
    """The production transport. `method` / `json_body` default to a GET.

    Both new parameters are OPTIONAL and trailing, and every GET call site still
    passes exactly four positional arguments. That is deliberate rather than
    tidy: the transport is a plain callable that tests replace wholesale, and
    the existing fakes are written as `def __call__(self, url, headers, params,
    verify)`. Making `method` a required parameter -- or passing it on the GET
    paths "for symmetry" -- would break every one of those fakes and force a
    rewrite of tests that pin the shipped inputs' request shapes. A fake that
    only ever sees GET traffic therefore never has to know POST exists.
    """
    import requests

    response = requests.request(
        method, url, headers=headers, params=params, json=json_body,
        verify=verify, timeout=60)
    if response.status_code >= 400:
        # `.text` rather than `.json()`: a 404 from a reverse proxy or a
        # WAF-shaped error page is not JSON, and the one thing this must not do
        # is turn a decodable status code into an unrelated parse error.
        raise ApiError(response.status_code, response.text, url)
    return response.json()


# The exact set of values that turn TLS certificate verification OFF, and the
# only ones. Byte-identical to `FALSEY_VERIFY_TLS` in
# `backend/src/splunk/utils/splunk-verify-tls.util.ts`, which parses the same
# flag for the HEC push rail; `tests/test_wire_field_contract.py` reads both
# files and fails if the two lists stop matching, element for element.
VERIFY_TLS_FALSEY = ("0", "false", "f", "no", "n", "off")


def should_verify_tls(raw):
    """Parse a `verify_tls` account value as a DENY-LIST.

    Verification stays ON unless the value is explicitly, recognisably "off".
    This is THE security decision in the add-on's transport setup, not a
    config-parsing convenience, and it lived inlined in five separate helpers
    before it lived here -- five chances for someone to "tidy" it into an
    allow-list and silently invert it. It is here, in the one module that
    imports nothing from Splunk, so pytest can actually execute it.

    WHY A DENY-LIST AND NOT AN ALLOW-LIST

    The flag has to exist at all because an on-premises LMS very commonly runs
    a self-signed or internal-CA certificate; without the escape hatch the
    add-on is unusable for exactly the customers it targets. The DIRECTION of
    the default is what keeps it safe.

    `verify_tls` reaches us from paths the UI checkbox never touches. The
    UCC-generated `.conf.spec` emits an EMPTY value, so an admin templating
    `local/` from it gets `""` -- and the key IS present, so a `.get` default
    never applies. The generated REST handler declares `validator=None` and
    stores whatever was typed, so `"true"`, `"yes"`, `"on"`, `"null"`,
    `"undefined"` all arrive verbatim. A deployment-server push or a
    hand-edited conf bypasses the UI's constraints entirely.

    Under an allow-list (`value == "true"` => verify) every one of those
    unrecognised spellings silently DISABLES verification, and the failure is
    invisible: nothing errors, the input reports success, and what is in flight
    is a tenant-wide integration token plus employee names, email addresses,
    who clicked a phish and who submitted credentials. Under a deny-list an
    unrecognised spelling leaves verification ON, so a self-signed host fails
    loudly with a certificate error the admin can act on. Loud-and-wrong beats
    silent-and-exposed for an input nobody positively recognised.

    WHY THERE IS NO SPECIAL CASE FOR `None`, FOR BOOLEANS, OR FOR ANYTHING ELSE

    There deliberately is not one, and the single expression is not laziness --
    every non-string input the callers can produce already lands on the right
    side of the deny-list under `str()`:

        None            -> "none"     not denied -> VERIFY   (absent means on)
        True            -> "true"     not denied -> VERIFY
        False           -> "false"    DENIED     -> off, which is what it means
        0 / 1           -> "0" / "1"  denied / not
        {} / []         -> "{}"/"[]"  not denied -> VERIFY

    `False` landing in the deny-list is not luck: `"false"` is IN the list, and
    that is the whole reason it is. An extra `isinstance(raw, bool)` arm would
    restate what the list already says, and a guard that cannot be broken
    without breaking something else too is a guard whose test can only ever
    pass vacuously. The list is the mechanism; nothing shadows it.
    """
    return str(raw).strip().lower() not in VERIFY_TLS_FALSEY


class RansomleakClient:
    """Thin HTTP wrapper over the external phishing-events feed."""

    def __init__(self, base_url, api_token, verify_tls=True, transport=None):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.verify_tls = verify_tls
        self._transport = transport or _requests_transport

    def fetch_page(self, start_date, after, limit):
        """One page of events, ordered by (occurredAt, eventId) ascending."""
        params = {"limit": limit}
        if start_date:
            params["startDate"] = start_date
        if after:
            params["after"] = after
        return self._transport(
            self.base_url + PHISHING_EVENTS_PATH,
            {"Authorization": "Bearer " + self.api_token},
            params,
            self.verify_tls,
        )

    def fetch_security_events_page(self, start_date, after, limit):
        """One page of audit events from the keyset-cursor route.

        Rows come back ascending by `(timestamp, id)`; `after` is the id of the
        last row already consumed and its position is resolved server-side.
        `start_date` is compared as an exact instant, so a full ISO value means
        what it says.

        Deliberately does NOT accept an `endDate` or an `eventType` filter even
        though the route offers both: nothing on this path needs to narrow the
        feed. Narrowing was a workaround for the row cap on the older `/export`
        route, and the cursor removes the cap.
        """
        params = {"limit": limit}
        if start_date:
            params["startDate"] = start_date
        if after:
            params["after"] = after
        return self._transport(
            self.base_url + SECURITY_EVENTS_PULL_PATH,
            {"Authorization": "Bearer " + self.api_token},
            params,
            self.verify_tls,
        )

    def fetch_compliance_page(self, limit, offset):
        """One page of training-state rows. Server max limit is 5000."""
        return self._transport(
            self.base_url + COMPLIANCE_EVIDENCE_PATH,
            {"Authorization": "Bearer " + self.api_token},
            {"limit": limit, "offset": offset},
            self.verify_tls,
        )

    def create_assignment(self, body):
        """Create (or replay) one partner assignment. The add-on's only write.

        Deliberately takes an already-built body rather than keyword arguments
        for each DTO field. The body is assembled by `ransomleak_assign`, which
        is where the two decisions that actually matter live -- how the
        idempotency key is derived, and that `triggerContext.source` is
        `"splunk"` -- and both need to be visible in one place next to the
        reasoning for them. Spreading them across a nine-parameter method
        signature here would put half of the contract in the transport layer.

        The server treats `idempotencyKey` as the assignment's identity:
        repeating a key returns the ORIGINAL assignment (with a fresh
        deep-link) instead of creating a second one, and answers 201 either
        way. So a retried, killed or re-fired alert action is safe by
        construction -- there is no "already exists" status code to special-case
        and none is looked for.

        Sends `params=None`: this endpoint takes no query string.
        """
        return self._transport(
            self.base_url + ASSIGNMENTS_PATH,
            {"Authorization": "Bearer " + self.api_token},
            None,
            self.verify_tls,
            method="POST",
            json_body=body,
        )

    def query_grafana(self, metric, range_from, range_to, team=None, channel=None,
                      response_format=None):
        """One aggregate metric over one window. A POST, but still a read.

        `range_from` / `range_to` are ISO-8601 instants and the window is
        INCLUSIVE at both ends, so the last bucket is the partial current day.

        `format` is deliberately left OFF the body unless a caller insists. The
        server picks a per-metric default (`GRAFANA_METRIC_DEFAULT_FORMAT`) and
        those defaults are the right ones: the five rate/count metrics come back
        as daily series, `overdue_users` and `assignments_by_category` as
        tables. Requesting a shape would also invite the collector to trust the
        request instead of the response -- and it cannot, because
        `overdue_users` is table-only whatever is asked for
        (`GRAFANA_TABLE_ONLY_METRICS`). The response is discriminated on its own
        `type` field instead; see `collect_grafana_metrics`.

        Sends `params=None`: this endpoint takes no query string, and passing an
        empty dict would leave a caller wondering whether one was intended.
        """
        body = {"metric": metric, "range": {"from": range_from, "to": range_to}}
        if team:
            body["team"] = team
        if channel:
            body["channel"] = channel
        if response_format:
            body["format"] = response_format
        return self._transport(
            self.base_url + GRAFANA_QUERY_PATH,
            {"Authorization": "Bearer " + self.api_token},
            None,
            self.verify_tls,
            method="POST",
            json_body=body,
        )


def _walk_cursor_feed(fetch, id_key, time_key, high_water, seen_ids, lookback_hours,
                      page_size, sink, start_date=None, after=None,
                      max_seen_ids=MAX_SEEN_IDS, recover_stale_cursor=False):
    """Page a keyset-cursor feed to exhaustion, streaming each page to `sink`.

    The one place the add-on knows how to consume a `(timestamp, id)`-ordered
    `?after=` feed. Both the phishing feed and the audit feed are exactly that
    shape, and this used to be two copies -- see the "already diverged" note in
    docs/follow-ups.md, which this replaces.

    THE HIGH-WATER SEMANTIC, which is what those copies disagreed about.
    `collect_events` computed the new high-water from the rows it EMITTED;
    `collect_audit_events` from every row the API RETURNED. This uses the
    second, everywhere, deliberately:

    * `high_water` is a POSITION IN THE FEED, not a record of what was indexed.
      It is the anchor the next run resumes from, and -- on the cursor path --
      the anchor a purged cursor recovers to. If it were computed from emitted
      rows it could lag the cursor: a page consisting entirely of rows already
      in `seen_ids` advances the cursor but would leave the high-water behind,
      so a stale-cursor recovery would rewind to an instant the walk had
      already passed and re-deliver everything in between.
    * The emitted-row variant can also stick permanently. An id retained in
      `seen_ids` whose timestamp is above the high-water mark is suppressed on
      every subsequent run, so it can never raise the mark that would let the
      window move past it.
    * It cannot skip anything. Rows excluded from the emitted set are excluded
      precisely because they were already emitted, so advancing over them
      indexes nothing twice and loses nothing.

    In the phishing collector the change is a no-op on real data (a returned row
    above the high-water mark is by construction not yet in `seen_ids`), which
    is why no existing test moves. It is the cursor path that makes the
    distinction observable, and both now agree.

    `sink` is called once per page, with that page's not-yet-seen rows in
    ascending order. It is required, and rows must not be retained past the
    call: it is what keeps the audit walk's peak memory flat across a backfill
    of any length.

    `recover_stale_cursor` handles the retention cron deleting the row `after`
    names. See `is_unknown_cursor_error`: dropping the cursor and resuming from
    the high-water TIMESTAMP resumes within one instant of where the cursor was,
    and the retained ids suppress the rows on the boundary that come back twice.
    Re-baselining from scratch instead would re-ingest the entire history.

    Returns `(new_high_water, new_seen_ids, last_id, warnings)`.
    """
    suppressed = set(seen_ids)
    # `(timestamp, id)` pairs for every row seen at or after the retention
    # floor, plus the id-only set used to test membership. Maintained
    # incrementally against a floor that rises with the high-water mark, so the
    # pair list is bounded by one lookback window rather than by the length of
    # the walk -- the property that lets the audit path page a whole history
    # without the memory growing.
    retained = []
    retained_ids = set()
    high = high_water
    floor = None
    if high:
        floor = _format_iso(parse_iso(high) - timedelta(hours=lookback_hours))
    compact_at = _RETAIN_COMPACT_MIN
    truncated = False
    warnings = []
    saw_rows = False
    last_id = after
    recoveries = 0

    while True:
        try:
            page = fetch(start_date, after, page_size)
        except ApiError as error:
            # Bounded, because this is the one branch that retries rather than
            # returning: each recovery does make progress (the row it resumes
            # from is gone, and the resume instant only moves forward), but a
            # server that answered "unknown cursor" to every request would
            # otherwise hang a modular input silently rather than failing it.
            if (recover_stale_cursor and after is not None and high is not None
                    and recoveries < _MAX_STALE_CURSOR_RECOVERIES
                    and is_unknown_cursor_error(error)):
                recoveries += 1
                warnings.append(
                    "Cursor %s no longer exists on the server -- the retention "
                    "cron has deleted that event. Resuming from the last "
                    "timestamp seen (%s) instead of re-ingesting the whole "
                    "history; events on that instant are suppressed by the "
                    "checkpoint's id list." % (after, high))
                after = None
                start_date = high
                continue
            raise
        if not page:
            break

        emitted = []
        for row in page:
            saw_rows = True
            rid = row[id_key]
            timestamp = row[time_key]
            if high is None or timestamp > high:
                high = timestamp
                floor = _format_iso(parse_iso(high) - timedelta(hours=lookback_hours))
            already = rid in suppressed or rid in retained_ids
            if floor is None or timestamp >= floor:
                retained.append((timestamp, rid))
                retained_ids.add(rid)
            if not already:
                emitted.append(row)

        # Compact once per page, not once per row: the floor only moves with the
        # high-water mark, and `compact_at` doubling off the surviving size
        # keeps the amortised cost linear while holding the list to roughly
        # twice the live set.
        if len(retained) >= compact_at:
            retained, truncated = _compact_retained(retained, floor, max_seen_ids, truncated)
            retained_ids = set(rid for _, rid in retained)
            compact_at = max(_RETAIN_COMPACT_MIN, 2 * len(retained))

        if emitted:
            sink(emitted)
        after = page[-1][id_key]
        last_id = after

    if high is None:
        return None, list(seen_ids), last_id, warnings
    if not saw_rows:
        # Nothing came back at all, so nothing can be pruned or learned. Hand
        # the checkpoint back exactly as it arrived rather than emptying it.
        return high, list(seen_ids), last_id, warnings

    retained, truncated = _compact_retained(retained, floor, max_seen_ids, truncated)
    if truncated:
        warnings.append(
            "Checkpoint bound: the lookback window holds more than %d event "
            "ids; the oldest were dropped from the checkpoint and events "
            "inside the window may be re-emitted next run. Lower "
            "lookback_hours or raise the interval." % (max_seen_ids,))
    return high, [rid for _, rid in retained], last_id, warnings


def collect_events(client, high_water, seen_ids, lookback_hours, page_size):
    """Collect everything new since `high_water`, with a lookback overlap.

    `occurredAt` is event time, not ingest time: an event can be written
    carrying a timestamp older than one already consumed. Advancing purely on a
    cursor would step past such an event forever, so each run re-queries a
    window reaching `lookback_hours` behind the high-water mark and suppresses
    the ids already emitted from that window.

    Retention: every id the API returned this run whose `occurredAt` is still
    inside the next run's lookback window is kept, not just the newly-emitted
    ones. The high-water mark only moves forward, so this run's query window
    always covers the next run's (narrower) retention window; an already-seen id
    still in that window comes back from the API this run too, and must stay
    suppressed or it will be re-emitted once a later run's window reaches back
    far enough to see it again. Anything older than the window can never be
    returned again, so remembering it would grow the checkpoint without bound.

    Returns `(new_events, new_high_water, new_seen_ids)`.
    """
    start_date = None
    if high_water:
        start_date = _format_iso(parse_iso(high_water) - timedelta(hours=lookback_hours))

    collected = []
    new_high_water, retained, _, _ = _walk_cursor_feed(
        client.fetch_page, "eventId", "occurredAt", high_water, seen_ids,
        lookback_hours, page_size, collected.extend, start_date=start_date)
    return collected, new_high_water, retained


def collect_audit_events(client, high_water, cursor, seen_ids, lookback_hours,
                         sink, page_size=AUDIT_PAGE_SIZE,
                         max_seen_ids=MAX_SEEN_IDS):
    """Collect audit events from the backend's keyset-cursor route.

    The same shape as `collect_events` above, because the two endpoints are now
    the same shape: the server pages for us in `(timestamp, id)` order and the
    only per-feed differences are the field names and the stale-cursor
    recovery.

    This replaced a day-window walk that subdivided a saturated window by event
    type, because the older `/export` route orders DESC, truncates at 10000 and
    offers no cursor. That scheme could not be made correct at any level of
    effort -- `security_event.event_type` is an unconstrained varchar, so rows
    carrying a type the server's own enum no longer holds (real tenants have
    them) were unrequestable, and subdivision could only ever warn about the
    shortfall. The whole apparatus is gone with it: no window or backfill knob,
    no row cap, no per-type fan-out, no coverage warnings, and no rows that
    cannot be asked for.

    HOW A RUN RESUMES, and why it is not simply `after=cursor`.

    With `lookback_hours > 0` (the default and the documented recommendation)
    the run resumes at `startDate = high_water - lookback_hours` and pages with
    the cursor from there. Resuming from the stored cursor alone would be
    exact-once but would reintroduce the defect `lookback_hours` exists to
    prevent: `timestamp` is assigned when an event is logged, not when its
    transaction commits, so a row can become visible with a timestamp already
    behind the cursor. A cursor-only reader steps past such a row permanently
    and silently -- the failure class this input has been fixed for twice. The
    re-queried overlap costs one small page per run and `seen_ids` suppresses
    everything in it.

    With `lookback_hours == 0` the operator has explicitly opted out of that
    overlap, and the stored cursor is then strictly better than
    `startDate = high_water`: it re-delivers nothing at all, not even the rows
    sharing the high-water instant.

    Either way the cursor is what pages WITHIN the run, so the stale-cursor
    recovery path is live in both modes -- a backfill deep enough to be paging
    through rows the retention cron is concurrently deleting will hit it.

    First run: no bounds at all, i.e. the entire retained history, streamed a
    page at a time. There is deliberately no backfill horizon -- one would only
    throw away history the server is willing to give us, and the peak memory is
    flat in the length of the feed because `sink` is called per page and the
    rows are dropped afterwards.

    Returns `(new_high_water, new_cursor, new_seen_ids, warnings)`.
    """
    start_date = None
    after = None
    if high_water and cursor and lookback_hours == 0:
        after = cursor
    elif high_water:
        start_date = _format_iso(parse_iso(high_water) - timedelta(hours=lookback_hours))

    new_high_water, retained, last_id, warnings = _walk_cursor_feed(
        client.fetch_security_events_page, "id", "timestamp", high_water, seen_ids,
        lookback_hours, page_size, sink, start_date=start_date, after=after,
        max_seen_ids=max_seen_ids, recover_stale_cursor=True)
    # `last_id or cursor`: a run that returned no rows learned nothing, and
    # must not blank a cursor a later run (or a later `lookback_hours = 0`)
    # would have used. The cursor only ever moves forward or stays put.
    return new_high_water, last_id or cursor, retained, warnings


def _compact_retained(retained, floor, max_seen_ids, already_truncated):
    """Drop retained ids below `floor`, dedupe, and bound the result.

    Returns `(pairs, truncated)`. `pairs` stays `(timestamp, id)` so a later
    compaction can still order by time. `floor` may be None only before any row
    has been seen, in which case there is nothing to drop.
    """
    unique = {}
    for timestamp, rid in retained:
        if floor is not None and timestamp < floor:
            continue
        if rid not in unique or timestamp > unique[rid]:
            unique[rid] = timestamp
    pairs = [(timestamp, rid) for rid, timestamp in unique.items()]
    if len(pairs) > max_seen_ids:
        pairs.sort(key=lambda pair: pair[0], reverse=True)
        del pairs[max_seen_ids:]
        return pairs, True
    return pairs, already_truncated


def row_key(row):
    """Stable identity of a training-state row. The endpoint exposes no id."""
    return "{}|{}".format(row["userEmail"], row["trainingId"])


def row_digest(row):
    """Short content hash, used to detect that a row changed since last poll.

    Covers the whole row deliberately, with nothing excluded: a change to any
    projected field is a real state change worth re-indexing.
    """
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def collect_training_state(client, tracked, page_size, max_tracked):
    """Emit only training rows that are new or changed since the last poll.

    The endpoint is a full state projection with no id and no delta, so the
    checkpoint carries a `key -> digest` map. Above `max_tracked` rows the map
    would outgrow a KV-store document, so tracking is disabled and every row is
    emitted — correct, just noisier. Returns
    `(changed_rows, new_tracked, tracking_disabled)`.
    """
    rows = []
    offset = 0
    while True:
        page = client.fetch_compliance_page(page_size, offset)
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    if len(rows) > max_tracked:
        return rows, {}, True

    new_tracked = {}
    changed = []
    for row in rows:
        key, digest = row_key(row), row_digest(row)
        new_tracked[key] = digest
        if tracked.get(key) != digest:
            changed.append(row)
    return changed, new_tracked, False


# --- The Grafana aggregate inputs (`ransomleak_risk`, `ransomleak_metrics`) ---


def epoch_millis_to_iso(millis):
    """Render a Grafana datapoint's epoch-millis bucket stamp as UTC ISO-8601.

    Only for the event BODY. `_time` is stamped from the same millis divided by
    1000 and never from re-parsing this string, so a rendering bug here is
    cosmetic rather than a time shift.
    """
    return _format_iso(datetime.fromtimestamp(millis / 1000.0, timezone.utc))


def parse_grafana_metrics(raw):
    """A multi-select's stored value -> an ordered, de-duplicated metric list.

    UCC stores a `multipleSelect` as one delimiter-joined string, so this is the
    only place that field stops being text. Lives HERE rather than in
    `grafana_input.py` for the reason docs/follow-ups.md gives for
    `event_time()` / `should_verify_tls()`: the helpers cannot be imported
    without Splunk's libraries, so anything left in them is untestable, and a
    parser that silently returned an empty list would leave an input reporting
    success while collecting nothing.

    Unknown names are DROPPED rather than raising: the value can reach us from a
    hand-edited `local/inputs.conf` that no validator ever saw, and one stale
    name must not stop the metrics beside it from being collected. The caller
    warns when the result is empty.

    Order follows `GRAFANA_METRICS` -- the backend's own dropdown order --
    rather than the order the operator happened to click, so two inputs
    selecting the same set issue their queries in the same order and their logs
    line up.
    """
    chosen = set(part.strip() for part in (raw or "").split(",") if part.strip())
    return [metric for metric in GRAFANA_METRICS if metric in chosen]


def grafana_range(lookback_days, now=None):
    """The `(from, to)` window one poll asks for: `now - lookback_days` .. `now`.

    `to` is `now` rather than yesterday's end deliberately. The window is
    inclusive server-side and every metric buckets by UTC day, so the final
    bucket is the CURRENT, partial day -- which is the bucket an operator
    actually watches, and the one whose value changes on every poll. Emitting a
    bucket only once would freeze it at its first observed value; the digest
    change detection below is what makes re-emitting it correct instead.

    Takes `now` so a test can pin it, for the same reason `observation_epoch`
    does.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return _format_iso(now - timedelta(days=lookback_days)), _format_iso(now)


GrafanaCollection = collections.namedtuple(
    "GrafanaCollection", "events tracked tracking_disabled gaps warnings")
"""What one poll produced.

`events` is a list of `(epoch_seconds, body)` pairs -- the epoch is carried
beside the body rather than inside it because `_time` differs by response shape
(see `collect_grafana_metrics`) and a helper that had to re-derive it per event
would be re-deriving the one decision this module exists to make.

A namedtuple rather than a bare 5-tuple: `gaps` and `tracking_disabled` are both
plain ints/bools sitting next to each other, and a caller that transposed them
would silently report nothing and disable nothing.
"""


def _grafana_facet_fields(team, channel):
    """The facet fields stamped on every event of one query.

    `queryTeam` / `queryChannel`, not `team` / `channel`: these describe what
    the input ASKED FOR, and `overdue_users` already returns a `team` column
    describing what the row IS. See `_GRAFANA_RESERVED_FIELDS`.

    Absent rather than null when unset: an operator filtering
    `queryTeam=Engineering` in SPL must not accidentally match a tenant-wide
    query, and Splunk's json KV_MODE would surface an explicit null as the
    string "None".
    """
    fields = {}
    if team:
        fields["queryTeam"] = team
    if channel:
        fields["queryChannel"] = channel
    return fields


def _grafana_key(parts):
    """Identity of one bucket or table row, as a JSON list.

    JSON rather than `"|".join(...)`: the parts include team names, campaign
    names and email addresses, all of which may contain any separator character
    that could be chosen. Two distinct rows colliding on one key would leave one
    of them permanently suppressed by the other's digest -- silent loss, in the
    checkpoint, of exactly the kind this add-on has already been fixed for.
    """
    return json.dumps(parts, separators=(",", ":"), sort_keys=False, default=str)


def _grafana_series_candidates(metric, result, facets):
    """`(candidates, gaps, malformed)` for one time-series result.

    A candidate is `(key, epoch_seconds, body)`; the caller digests the body.

    `_time` is the BUCKET epoch, not the observation instant. These are
    genuinely time-stamped observations of a day, and every chart over them
    depends on it. A re-emitted bucket therefore shares `_time` with the value
    it corrects, and `latest()` by `_indextime` resolves the current one -- the
    standard Splunk pattern for a corrected aggregate. Contrast
    `ransomleak:training`, whose rows carry no bucket at all.

    A `null` value is a GAP and is SKIPPED, never emitted as 0. The backend
    returns null precisely where a denominator was zero (`sent = 0`,
    `enrolled = 0`) -- "no simulations were sent that day", which is not "0% of
    them were clicked". Emitting the zero would drag every average and every
    alerting threshold toward it, and there would be nothing in the index to
    show it had happened. Skipping instead leaves a hole a `timechart` renders
    as a hole; the count is returned so the input can log it.
    """
    target = result.get("target")
    if not isinstance(target, str) or not target:
        # The contract always sets it; falling back to the metric name keeps a
        # single-series result usable rather than keying every bucket on "None".
        target = metric
    datapoints = result.get("datapoints")
    if not isinstance(datapoints, list):
        return [], 0, 0

    candidates = []
    gaps = 0
    malformed = 0
    for point in datapoints:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            malformed += 1
            continue
        value, millis = point[0], point[1]
        # `isinstance(True, int)` is True in Python, and a bool epoch is a
        # malformed point rather than the instant 1970-01-01T00:00:00.001Z.
        if isinstance(millis, bool) or not isinstance(millis, (int, float)):
            malformed += 1
            continue
        if value is None:
            gaps += 1
            continue
        try:
            bucket_iso = epoch_millis_to_iso(millis)
        except (OSError, OverflowError, ValueError):
            # An epoch outside the platform's representable range. Degrade this
            # ONE datapoint rather than the whole poll: the type check above
            # accepts any number, and `datetime.fromtimestamp` raises on the
            # absurd ones. Every collector in this file takes the per-row
            # degradation path for exactly this reason -- a single bad value
            # from the server must never cost a tenant its other seven metrics.
            malformed += 1
            continue
        # `bucketTime` is emitted first in THIS dict because a reader -- human
        # or SPL -- should meet the bucket before the measurement. It is
        # deliberately NOT what `_time` is extracted from: `event_payload` puts
        # `rlEventTime` ahead of it at write time, carrying the same instant,
        # and props.conf's anchored prefix reads that. The distinction matters
        # because the `format=table` shape of this same response has no bucket
        # at all, and one stanza must serve both. See props.conf's header.
        body = {"bucketTime": bucket_iso, "metric": metric,
                "format": "time_series", "target": target, "value": value}
        body.update(facets)
        candidates.append((
            _grafana_key([metric, facets.get("queryTeam", ""), facets.get("queryChannel", ""),
                          "time_series", target, millis]),
            millis / 1000.0,
            body,
        ))
    return candidates, gaps, malformed


def _grafana_table_candidates(metric, result, facets, observed_epoch):
    """`(candidates, ragged_rows)` for one table result.

    `_time` is OBSERVATION time. A table row carries no bucket of its own --
    `overdue_users` and the aggregate tables are computed against
    `CURRENT_DATE`, i.e. they describe now -- so the same reasoning that moved
    `ransomleak:training` off `assignedAt` applies verbatim: the event's subject
    is that this input saw this row, and that happened now. See
    `observation_epoch`.

    IDENTITY is the row's non-numeric columns. The backend orders these tables
    by a measure (`ORDER BY overdue_count DESC`), so a row's POSITION is not
    stable across polls and keying on the index would report a reordering as a
    change to every row. Column `type` is part of the declared response contract
    (`{text, type}`), and in every table the endpoint returns the dimensions are
    the non-numeric columns and the measures are the numeric ones. A table with
    no non-numeric column at all is a single-row aggregate, and there the index
    IS stable, so it is the fallback.
    """
    columns = result.get("columns")
    rows = result.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return [], 0

    names = []
    numeric = []
    for index, column in enumerate(columns):
        text = column.get("text") if isinstance(column, dict) else None
        if not isinstance(text, str) or not text:
            text = "column_%d" % (index,)
        # Never let a column silently overwrite the envelope this event is
        # attributed by.
        names.append("column_" + text if text in _GRAFANA_RESERVED_FIELDS else text)
        numeric.append(isinstance(column, dict) and column.get("type") == "number")

    candidates = []
    ragged = 0
    for index, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):
            ragged += 1
            continue
        if len(row) != len(names):
            ragged += 1
        body = {"metric": metric, "format": "table"}
        body.update(facets)
        dims = []
        for position, value in enumerate(row):
            if position < len(names):
                body[names[position]] = value
                if not numeric[position]:
                    dims.append(value)
            else:
                # Lossless rather than tidy: a column the response grew and the
                # header did not describe is still data, and dropping it is the
                # silent direction.
                body["column_%d" % (position,)] = value
        if not dims:
            dims = [index]
        candidates.append((
            _grafana_key([metric, facets.get("queryTeam", ""), facets.get("queryChannel", ""),
                          "table"] + list(dims)),
            observed_epoch,
            body,
        ))
    return candidates, ragged


def collect_grafana_metrics(client, metrics, range_from, range_to, tracked,
                            team=None, channel=None, now=None,
                            max_tracked=MAX_TRACKED_BUCKETS):
    """Emit only the aggregate buckets and rows that are new or changed.

    THE SHAPE OF THE PROBLEM. These metrics are a STATE PROJECTION, not an event
    stream. Re-querying an overlapping window returns the same buckets, and a
    bucket's VALUE can change -- the current day recomputes on every poll, and a
    late completion moves a day already behind us. So the phishing/audit
    "emit only what is newer than the high-water mark" scheme is exactly wrong
    here: it would freeze every bucket at its first observed value. This reuses
    the training input's `key -> digest` change detection instead, keyed on
    `(metric, facets, target, bucket)` so a bucket is re-emitted when, and only
    when, its value moves.

    TWO RESPONSE SHAPES, discriminated on the RESPONSE's own `type == 'table'`
    and never on the format requested. `overdue_users` is table-only whatever is
    asked for (`GRAFANA_TABLE_ONLY_METRICS`), so inferring the shape from the
    request would mis-read it as a series with no `datapoints` and emit nothing
    at all -- silently, since an empty result is indistinguishable from a quiet
    tenant. `_time` differs between them; see the two candidate builders.

    PER-METRIC DEGRADATION. One metric's failure must not take the others down:
    the metrics are independent queries and a tenant without the risk add-on
    404s/400s on `human_risk_score` alone. So an `ApiError` is recorded as a
    warning and the walk continues -- EXCEPT 401 and 403, which are re-raised.
    Those are properties of the token, not of the metric: 403 is what a token
    minted for the other three inputs' scopes gets here (this endpoint needs
    `integration`), and swallowing it per metric would leave the input reporting
    success while ingesting nothing, forever.

    Returns a `GrafanaCollection`.
    """
    candidates = []
    warnings = []
    gaps = 0
    observed_epoch = observation_epoch(now)

    for metric in metrics:
        facets = _grafana_facet_fields(
            team, channel if metric in GRAFANA_CHANNEL_METRICS else None)
        try:
            results = client.query_grafana(
                metric, range_from, range_to,
                team=team, channel=facets.get("queryChannel"))
        except ApiError as error:
            if error.status in (401, 403):
                raise
            warnings.append(
                "Metric %s could not be queried (HTTP %s): %s. The other "
                "selected metrics were collected normally."
                % (metric, error.status, error.body[:200]))
            continue

        if not isinstance(results, list):
            warnings.append(
                "Metric %s returned %s, not the documented array of results; "
                "skipped." % (metric, type(results).__name__))
            continue

        for result in results:
            if not isinstance(result, dict):
                warnings.append(
                    "Metric %s returned a non-object result; skipped." % (metric,))
                continue
            # Both envelope checks below guard a branch the typed backend
            # contract makes unreachable today, and both WARN rather than
            # returning quietly. A result the collector cannot read produces no
            # events, and no events is indistinguishable from a quiet tenant --
            # which is precisely the silent-data-loss shape this add-on has
            # already been fixed for twice. If the response shape ever drifts,
            # the operator hears about it.
            if result.get("type") == "table":
                if (not isinstance(result.get("columns"), list)
                        or not isinstance(result.get("rows"), list)):
                    warnings.append(
                        "Metric %s returned a table whose columns or rows are "
                        "not arrays; skipped." % (metric,))
                    continue
                rows, ragged = _grafana_table_candidates(
                    metric, result, facets, observed_epoch)
                candidates.extend(rows)
                if ragged:
                    warnings.append(
                        "Metric %s returned %d table row(s) whose length did not "
                        "match its columns; the values that aligned were kept and "
                        "any extras emitted as column_<n>." % (metric, ragged))
            elif "datapoints" in result:
                if not isinstance(result["datapoints"], list):
                    warnings.append(
                        "Metric %s returned a series whose datapoints are not "
                        "an array; skipped." % (metric,))
                    continue
                points, metric_gaps, malformed = _grafana_series_candidates(
                    metric, result, facets)
                candidates.extend(points)
                gaps += metric_gaps
                if malformed:
                    warnings.append(
                        "Metric %s returned %d datapoint(s) that were not a "
                        "[value, epochMillis] pair; skipped."
                        % (metric, malformed))
            else:
                warnings.append(
                    "Metric %s returned a result that is neither a table nor a "
                    "series (keys: %s); skipped."
                    % (metric, ", ".join(sorted(result.keys())) or "none"))

    if len(candidates) > max_tracked:
        # Same degradation as the training input, and the same direction: the
        # data stays complete and the checkpoint stays inside one KV-store
        # document. Only the de-duplication is lost.
        return GrafanaCollection(
            [(epoch, body) for _, epoch, body in candidates], {}, True, gaps, warnings)

    new_tracked = {}
    events = []
    for key, epoch, body in candidates:
        digest = row_digest(body)
        new_tracked[key] = digest
        if tracked.get(key) != digest:
            events.append((epoch, body))
    return GrafanaCollection(events, new_tracked, False, gaps, warnings)
