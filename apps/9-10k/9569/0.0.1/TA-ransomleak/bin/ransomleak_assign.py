"""The `ransomleak_assign_training` alert action's logic, without Splunk.

Deliberately free of Splunk imports, for the reason docs/follow-ups.md records
against the modular-input helpers: anything living in the alert-action script
itself cannot be imported without `splunktaucclib`, so pytest cannot reach it
and the two decisions that carry the whole safety story of this action -- how
the idempotency key is derived, and that one unparsable row must not abort the
batch -- would ship untested. `ransomleak_assign_training_handler.py` is
therefore reduced to configuration reading, iteration and logging.

Beside `ransomleak_client.py` rather than inside it: that module is the pull
rails' HTTP client and its collectors, this one is the single push rail. Only
`RansomleakClient.create_assignment` is shared, and it lives there.
"""

import collections
import hashlib
import json
from datetime import datetime, timezone

from ransomleak_client import ApiError

# The value `triggerContext.source` carries, and the value the top-level
# `source` field carries. BOTH are set, and they are not redundant:
#
# * `triggerContext.source` is what a future `auto_assigned_via_splunk` metric
#   would count. Its Grafana twin is already implemented that way --
#   `integration-grafana.service.ts` counts the Rail-B closed loop with
#   `pa.trigger_context ->> 'source' = 'grafana'` -- so an assignment that set
#   only the top-level field would be invisible to the query that is supposed
#   to prove this loop works.
# * The top-level `source` is what drives completion write-back to the
#   originating system, which is a different mechanism entirely.
#
# Getting either one wrong is silent: the assignment is still created, still
# completes, and simply never appears in the metric. Hence one constant feeding
# both, and a test pinning the literal.
ASSIGNMENT_SOURCE = "splunk"

# The result field the email is read from. Defaults to the field name the
# add-on's OWN sourcetypes emit (`ransomleak:training`, `ransomleak:phishing`
# and the `overdue_users` table all carry `userEmail`), so an alert built on
# `sourcetype=ransomleak:*` -- the overwhelmingly common case, and the only one
# this add-on can promise anything about -- needs no configuration at all.
DEFAULT_EMAIL_FIELD = "userEmail"

# How many DISTINCT users one firing may assign to. A search returning 10,000
# rows would otherwise issue 10,000 sequential POSTs; Splunk kills a long alert
# action mid-batch (`alert_actions.conf` `maxtime`, 5m by default), leaving a
# partial, unattributable run. 100 is chosen as "more than any deliberate
# remediation cohort, less than any mis-scoped search": at a healthy few hundred
# milliseconds per request it finishes inside the default `maxtime` with room to
# spare, and an alert legitimately assigning more than 100 people at once is a
# campaign, not an alert.
#
# The overflow is REPORTED, never silent -- see `plan_assignments`. Silent
# truncation here would read as "everyone was assigned" to the one person who
# would have checked.
DEFAULT_MAX_ASSIGNMENTS = 100

# Hard ceiling on the operator's override. Past this the `maxtime` kill above
# stops being a risk and becomes the expected outcome, so the value is clamped
# (and the clamp is warned about) rather than honoured.
MAX_ASSIGNMENTS_CEILING = 1000

# Server-side `@MaxLength` on the DTO. `idempotencyKey` is a digest and cannot
# approach its cap; `reference` carries a saved-search name, which can, so it is
# truncated rather than allowed to 400 the whole batch.
IDEMPOTENCY_KEY_MAX = 255
REFERENCE_MAX = 255

# The re-assignment periods offered in the alert action UI, and the ONLY values
# the handler honours. See `reassign_bucket` for why the default is "never".
REASSIGN_PERIODS = collections.OrderedDict([
    ("never", 0),
    ("30", 30),
    ("90", 90),
    ("180", 180),
    ("365", 365),
])
DEFAULT_REASSIGN_PERIOD = "never"

# Version tag inside the hashed key material. A change to how the key is derived
# would otherwise silently re-assign every user in every tenant on upgrade --
# the keys would simply stop matching the stored ones. Bumping this deliberately
# is how that would be DONE on purpose; leaving it alone is how it is avoided by
# accident.
_KEY_VERSION = "splunk-v1"

# How many offending values a skip warning quotes. Enough to diagnose a wrong
# field name (three empty strings, or three values that are plainly not emails)
# without pasting a whole result set into the customer's own logs.
_SKIP_SAMPLE = 3
_SKIP_SAMPLE_CHARS = 80

# Longest address the local check will consider. RFC 5321 caps a path at 256
# octets; anything past that is certain to fail `@IsEmail` server-side and is
# more likely to be a stray blob of text in the chosen field.
_EMAIL_MAX = 320


AssignmentPlan = collections.namedtuple(
    "AssignmentPlan", "requests skipped duplicates dropped warnings")
"""What one result set turned into.

`requests` is a list of `(email, body)` pairs, capped and de-duplicated.
`skipped` is a list of `(row_index, quoted_value)` for rows with no usable
email. `duplicates` counts rows that collapsed onto a request already planned,
`dropped` counts DISTINCT users the batch cap excluded.

A namedtuple rather than a bare 5-tuple: `duplicates` and `dropped` are both
plain ints sitting next to each other and mean opposite things -- one is
routine, the other is data an operator asked for and did not get.
"""

AssignmentOutcome = collections.namedtuple("AssignmentOutcome", "created failures")
"""What the POSTs produced.

`created` is a list of `(email, assignment_id)`; `failures` a list of
`(email, reason)`. The server answers 201 for both a fresh assignment and a
replay of an existing key, and says nothing to distinguish them, so `created`
means "the server accepted it", not "a new row appeared".
"""


def parse_reassign_period(raw):
    """A stored period value -> `(days, warning_or_None)`.

    Unrecognised input falls back to `never`, i.e. the fail-safe direction: a
    hand-edited `alert_actions.conf` carrying `reassign_period = 7d` must not be
    read as "re-assign weekly". It reaches us un-validated by construction --
    UCC's alert entities support no validators at all (unlike the modular
    inputs' `globalConfig.json` regexes), so this function IS the gate.
    """
    value = (raw if isinstance(raw, str) else "").strip().lower()
    if not value:
        return 0, None
    if value in REASSIGN_PERIODS:
        return REASSIGN_PERIODS[value], None
    return 0, (
        "Re-assignment period %r is not one of %s; treating it as 'never' so "
        "nobody is re-assigned unexpectedly."
        % (raw, ", ".join(REASSIGN_PERIODS)))


def parse_max_assignments(raw, default=DEFAULT_MAX_ASSIGNMENTS):
    """A stored batch cap -> `(cap, warning_or_None)`. Same un-validated path."""
    value = (raw if isinstance(raw, str) else "").strip()
    if not value:
        return default, None
    try:
        cap = int(value)
    except (TypeError, ValueError):
        return default, (
            "Maximum assignments %r is not a whole number; using the default of "
            "%d." % (raw, default))
    if cap < 1:
        return default, (
            "Maximum assignments must be at least 1; %r would assign nobody, so "
            "the default of %d is used instead." % (raw, default))
    if cap > MAX_ASSIGNMENTS_CEILING:
        return MAX_ASSIGNMENTS_CEILING, (
            "Maximum assignments %d exceeds the ceiling of %d and was clamped. "
            "Splunk kills an alert action that runs past alert_actions.conf's "
            "maxtime, and a batch that large will hit it."
            % (cap, MAX_ASSIGNMENTS_CEILING))
    return cap, None


def normalize_email(raw):
    """A result-field value -> a lowercased address, or `None` if unusable.

    Deliberately a SHAPE check and not an RFC 5322 implementation. The server's
    `@IsEmail()` is the authority and this is only trying to separate "this row
    has an address" from "this row has an empty cell, a NULL, a display name or
    the wrong field entirely" -- the class of value that must be skipped and
    counted rather than POSTed. Being stricter than the server would silently
    drop deliverable addresses; being looser only costs one 400 that is already
    counted as a failure.

    LOWERCASING IS LOAD-BEARING, not cosmetic. The backend matches an existing
    user with `email.toLowerCase()`, so `Jane@acme.com` and `jane@acme.com` are
    one person server-side -- but they are two different strings, and the
    idempotency key is derived from this value. Without normalising here, a
    search whose results vary in case would mint two keys for one user and
    create two assignments for them, which is exactly the failure the key exists
    to prevent.
    """
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value or len(value) > _EMAIL_MAX:
        return None
    if any(character.isspace() for character in value):
        return None
    local, separator, domain = value.partition("@")
    if not separator or not local or not domain or "@" in domain:
        return None
    # `require_tld` defaults to true in class-validator, so a dotless domain is
    # rejected server-side; mirroring it here turns a guaranteed 400 into a
    # counted skip.
    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        return None
    return value.lower()


def reassign_bucket(reassign_days, now=None):
    """The coarse time component of the idempotency key. `""` means "never".

    THE WHOLE SAFETY STORY OF THIS ACTION IS HERE, so it is worth stating the
    two ways to get it wrong.

    A key that VARIES PER FIRING -- the search `sid` is the obvious candidate,
    and it is right there in `helper.settings` -- creates one assignment per
    firing. A scheduled search running every 5 minutes over a 60-minute window
    returns the same risky user twelve times, so that user receives twelve
    assignments and twelve notifications for one piece of training. That is the
    spam failure, and it is the one an operator notices immediately and blames
    the product for.

    A key that NEVER varies means a user can never be assigned that training
    again by that search, for the life of the tenant. That is the starvation
    failure, and it is silent: the alert keeps firing, the action keeps
    reporting success, the server keeps replaying the original assignment, and
    the annual refresher never lands.

    DEFAULT: no time component at all, i.e. the starvation direction. Fail-safe
    here means "no spam", because spam is unrecoverable (mails are sent, people
    are annoyed) while starvation is recoverable by an operator who sets a
    period, and because the assignment the server replays is genuinely still
    open until it is completed.

    THE OPT-IN is a floor-divided epoch-day bucket -- stateless, which it has to
    be: the alert action has no checkpoint and cannot know when this user was
    last assigned. Two consequences worth being honest about:

    * The boundaries are GLOBAL, not per-user. A user first assigned on day 89
      of a 90-day period is re-assignable on day 90, one day later. Over any
      long run this costs at most one extra assignment per user per period, and
      it can only ever make the cadence tighter than configured, never looser.
    * The period must comfortably exceed the training's completion window, or
      the action re-assigns work the user is still doing. That is why the
      shortest offered period is 30 days and the one the help text recommends is
      90: assignments are ordinarily due within 14-30 days, so a quarter
      guarantees the previous one has had its full window to be completed or to
      go overdue before another can be minted.
    """
    if reassign_days <= 0:
        return ""
    if now is None:
        now = datetime.now(timezone.utc)
    epoch_day = int(now.timestamp() // 86400)
    return str(epoch_day // reassign_days)


def idempotency_key(search_name, email, exercise_slug, bucket=""):
    """The assignment's logical identity, hashed to a fixed length.

    Identity is `(saved search, user, exercise)` plus the optional re-assignment
    bucket. The saved-search name is in it so two different alerts assigning the
    same training to the same person remain two decisions; the `sid` is NOT, for
    the reason `reassign_bucket` gives.

    HASHED rather than concatenated because the server caps the key at 255
    characters and none of the three inputs is bounded anywhere near that: a
    saved-search name is free text, an address may be 320 octets, and a slug is
    whatever the catalogue says. A concatenation would silently truncate --
    which is the collision failure, two different users sharing one key and one
    of them never being assigned at all.

    The material is JSON-encoded rather than delimiter-joined, for the reason
    `_grafana_key` gives in `ransomleak_client.py`: a saved-search name may
    contain any separator character that could be chosen, and two distinct
    identities colliding on one key is silent data loss.
    """
    material = json.dumps(
        [_KEY_VERSION, search_name or "", email or "", exercise_slug or "", bucket or ""],
        separators=(",", ":"))
    key = "splunk:" + hashlib.sha256(material.encode("utf-8")).hexdigest()
    # 71 characters, so this can only fire if the prefix or the digest changes.
    assert len(key) <= IDEMPOTENCY_KEY_MAX
    return key


def build_trigger_context(search_name, sid, app):
    """The `triggerContext` object echoed back on the completion webhook.

    Four keys, kept small on purpose: this is stored per assignment forever and
    surfaced to partner webhooks, so it carries what is needed to trace an
    assignment back to the decision that made it -- which search, which run of
    it, in which app -- and nothing else. No result row is copied in: a row can
    hold arbitrary customer data, and this field is not the place to persist it.

    `source` is first and is always present, even when everything else is
    unknown, because it is the field the closed-loop metric matches on.
    """
    context = {"source": ASSIGNMENT_SOURCE}
    if search_name:
        context["searchName"] = search_name
    if sid:
        context["sid"] = sid
    if app:
        context["app"] = app
    return context


def _http_url(value):
    """An http(s) URL, or None. `referenceUrl` is audit-only server-side and
    anything else is silently dropped there; dropping it here instead keeps the
    request honest about what it is asking to store."""
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    lowered = trimmed.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return trimmed
    return None


def _truncate(value, limit):
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    return trimmed[:limit]


def build_assignment(email, exercise_slug, key, trigger_context,
                     reference=None, reference_url=None):
    """One `POST /api/integration/assignments` body.

    `firstName` / `lastName` / `externalId` are deliberately absent. They are
    used server-side only when the user does not already exist, and a Splunk
    result row has no trustworthy source for them -- the add-on's own
    sourcetypes carry `userFullName`, and splitting a display name into given
    and family names is guesswork that would be persisted on a real account.
    A JIT-created user therefore lands with an email and no name; see
    docs/follow-ups.md.
    """
    body = {
        "exerciseSlug": exercise_slug,
        "user": {"email": email},
        "idempotencyKey": key,
        "triggerContext": trigger_context,
        "source": ASSIGNMENT_SOURCE,
    }
    if reference:
        body["reference"] = reference
    if reference_url:
        body["referenceUrl"] = reference_url
    return body


def _quote(value):
    if value is None:
        return "<missing>"
    text = value if isinstance(value, str) else repr(value)
    if len(text) > _SKIP_SAMPLE_CHARS:
        text = text[:_SKIP_SAMPLE_CHARS] + "..."
    return repr(text)


def plan_assignments(rows, exercise_slug, email_field=DEFAULT_EMAIL_FIELD,
                     search_name=None, sid=None, app=None, reassign_days=0,
                     max_assignments=DEFAULT_MAX_ASSIGNMENTS, results_link=None,
                     now=None):
    """A Splunk result set -> the assignments to POST, plus what was not.

    ONE BAD ROW MUST NOT ABORT THE BATCH. A result row is a CSV record with
    whatever fields the search produced; the chosen field may be absent, empty,
    a NULL rendered as the empty string, a display name, or a whole different
    kind of value if the operator named the wrong field. Every one of those is
    skipped and counted here rather than raised -- the same per-row degradation
    `parse_iso_or_none` exists for on the pull rails, and for the same recorded
    reason: one unparsable value taking down a whole tenant's feed was a
    Critical on this add-on already. The equivalent here is one malformed row
    costing every OTHER at-risk user in the same alert their training.

    DE-DUPLICATION IS LOCAL AS WELL AS SERVER-SIDE. Rows collapsing onto one
    idempotency key are collapsed here too. The server would replay rather than
    duplicate, so this is not a correctness fix -- it is what keeps a search
    returning one row per phishing click from spending twelve requests, and
    twelve slots of the batch cap, on one person.

    Both `now` and the facets are injectable so a test can pin them.
    """
    field = (email_field or "").strip() or DEFAULT_EMAIL_FIELD
    bucket = reassign_bucket(reassign_days, now)
    context = build_trigger_context(search_name, sid, app)
    reference = _truncate(search_name, REFERENCE_MAX)
    reference_url = _http_url(results_link)

    requests = []
    planned = set()
    skipped = []
    duplicates = 0
    dropped = 0
    warnings = []
    total = 0

    for index, row in enumerate(rows):
        total += 1
        raw = row.get(field) if isinstance(row, dict) else None
        email = normalize_email(raw)
        if email is None:
            skipped.append((index, _quote(raw)))
            continue
        key = idempotency_key(search_name, email, exercise_slug, bucket)
        if key in planned:
            duplicates += 1
            continue
        # Recorded before the cap check so a later duplicate of a DROPPED user
        # is counted as the duplicate it is, and `dropped` stays a count of
        # distinct people rather than of rows.
        planned.add(key)
        if len(requests) >= max_assignments:
            dropped += 1
            continue
        requests.append((email, build_assignment(
            email, exercise_slug, key, context, reference, reference_url)))

    if skipped:
        sample = ", ".join(quoted for _, quoted in skipped[:_SKIP_SAMPLE])
        warnings.append(
            "Skipped %d of %d result row(s): field '%s' held no usable email "
            "address. The other rows were assigned normally. First offending "
            "value(s): %s." % (len(skipped), total, field, sample))
    if total and len(skipped) == total:
        warnings.append(
            "No result row carried a usable email address in field '%s', so "
            "nothing was assigned. Check the 'Email field' setting against the "
            "fields your search actually returns." % (field,))
    if dropped:
        warnings.append(
            "Batch cap reached: %d assignment(s) were sent and %d further "
            "distinct user(s) were NOT assigned. Raise 'Maximum assignments "
            "per firing' or narrow the search; the users left out are not "
            "retried on the next firing unless they are still in its results."
            % (len(requests), dropped))

    return AssignmentPlan(requests, skipped, duplicates, dropped, warnings)


def send_assignments(client, requests):
    """POST each planned assignment, degrading per row.

    A 4xx/5xx on one assignment is recorded and the walk continues -- a user who
    has exhausted the tenant's licences (400) or whose address the server
    rejects must not cost the rest of the cohort their training.

    EXCEPT 401, 403 and 404, which are re-raised. None of the three is a
    property of the row:

    * 401/403 are properties of the TOKEN. This endpoint needs the `integration`
      scope, and a token minted for the three pull-only inputs' scopes gets a
      403 here with nothing in the body saying why. Swallowing it per row would
      turn one configuration mistake into `max_assignments` identical failures
      and an action that still looks like it merely had a bad batch.
    * 404 is a property of the configured `exerciseSlug`, which is fixed for the
      whole batch. Every row would fail identically; failing once, loudly, names
      the actual mistake.

    Transport-level exceptions (DNS, connection refused, TLS) are not caught at
    all. They are not per-row either, and the deterministic idempotency key is
    what makes the resulting partial batch safe to re-run.
    """
    created = []
    failures = []
    for email, body in requests:
        try:
            response = client.create_assignment(body)
        except ApiError as error:
            if error.status in (401, 403, 404):
                raise
            failures.append(
                (email, "HTTP %s: %s" % (error.status, (error.body or "")[:200])))
            continue
        assignment_id = response.get("assignmentId") if isinstance(response, dict) else None
        created.append((email, assignment_id))
    return AssignmentOutcome(created, failures)
