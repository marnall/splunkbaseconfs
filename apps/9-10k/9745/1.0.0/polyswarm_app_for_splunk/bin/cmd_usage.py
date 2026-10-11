"""Search command entry point for polyswarmusage.

Registered in default/commands.conf as a chunked (v2 protocol) generating
command.

    | polyswarmusage

Design section 4.6's usage and entitlement surface, which commercial goal 2
moves into Phase 1: the app is the demand-generation surface, so quota and
entitlement have to be visible in the first release rather than the fifth.
This command is the mechanism. It calls the two account endpoints and turns
their answer into rows a dashboard panel and a search bar can both read.

Output rows. Every row carries row_type, which says what kind of row it is, and
fetched_at, the epoch second the answer was obtained.

    row_type=account   account_type, tenant, communities, account_plan_name,
                       is_trial, daily_api_limit, daily_api_remaining,
                       plan_period_end
    row_type=feature   feature, tag, feature_type, base_uses, remaining_uses,
                       overage
    row_type=throttled message

One account row comes first and the feature rows follow it, sorted by feature
name so a table is stable between refreshes. A throttled invocation emits the
notice row and nothing else: no account row, no feature rows, no numbers.

The account row is fed by BOTH responses, and that is not an accident of
convenience. whois answers "which account is this" and accounts answers "on
what plan, with what left today": account_type, tenant and communities come
from the first, and account_plan_name, is_trial, daily_api_limit,
daily_api_remaining and plan_period_end come from the second. They are one row
because they are one answer to one question a customer asks, and splitting them
across two row types would make a dashboard join two rows to render a header.

THE FIELD SET IS DECLARED ON EVERY EMITTED ROW, AND THAT IS A BUG FIX
---------------------------------------------------------------------
This is the defect that shipped in the first cut of this command, seen on a
real instance: the account identity row rendered correctly and every feature
row came out empty. The reader was not at fault. splunklib's chunked writer
fixes the CSV header of a chunk from the keys of the FIRST record written into
it (RecordWriter._write_record, lib/splunklib/searchcommands/internals.py), and
every later record in that chunk is projected onto that header. The account row
goes first and carries no feature or quota keys, so feature, tag, feature_type,
base_uses, remaining_uses and overage were never in the header and every value
under them was dropped on the floor between this command and splunkd.

So output_row() pads every emitted row to ALL_FIELDS before it is yielded. That
is not a retreat from omit-if-unreadable, and it does not put a zero anywhere:
the padding value is None, and splunklib writes an absent key and a None value
to exactly the same two empty CSV cells, which Splunk reads as the field not
being present on that event. The wire bytes for a padded row and an unpadded
one are identical; what changes is only that the header now names every column
the command can fill. A test asserts that byte-for-byte equivalence rather than
taking this paragraph's word for it.

The rows handed to the KV store write-through are the UNPADDED ones, so the
stored documents keep carrying only the fields that were readable. Padding is a
property of the emission boundary and of nothing else.

WHAT THIS SPENDS, AND WHY THERE IS STILL A THROTTLE
---------------------------------------------------
The two endpoints are account endpoints. Neither submits, scans, nor detonates
anything, so neither consumes the scan or detonation allowance a customer buys.
That is a real distinction from polyswarmsearch and it is why constraint C11's
machinery is not reproduced here: there is no per-event metered path to cap,
because there are no events. One invocation is two requests whatever the search
around it looks like.

It is not the same as free, and the command is guarded structurally rather than
on that assurance. Two reasons.

  1. P0-6, quota semantics per endpoint, is open. Whether an account read counts
     against an api_requests feature is not something this app knows, and a
     command that assumed the generous answer would be assuming it on the
     customer's bill.
  2. A dashboard panel is not a person. A panel with an auto-refresh interval
     issues a request per interval, per open browser tab, indefinitely, and
     nothing in Splunk stops it. The refresh input on the Overview dashboard is
     token gated so the panel cannot fire on load, and this command refuses to
     call out more than once a minute per search head so that the panel cannot
     fire in a loop either. Neither half is sufficient alone.

The throttle is in bin/usage_store.py, backed by the ps_usage_throttle
collection, and it fails open when the KV store is unreachable. That decision
and its reasoning are written out in that module.

RESPONSE SHAPES ARE PINNED BY A RECORDING
-----------------------------------------
Decision D4 pinned the hash search response to
tests/fixtures/search-hash-recorded.json, and D3 keeps every unrecorded client
seam at NotImplementedError for exactly that reason. These two endpoints stood
outside that rule for one release and no longer do. Both are now pinned by
scrubbed live recordings:

    tests/fixtures/whois-recorded.json      GET /public/accounts/whois
    tests/fixtures/accounts-recorded.json   GET /public/accounts

Those files, not this docstring and not the v3 documentation, are the contract.
The readers below are driven through both of them end to end and the emitted
rows are asserted value by value, which is what closes D9.

The structural tolerance the readers had before the recording is kept rather
than narrowed, and the recording is what makes keeping it a decision instead of
a hedge: both responses arrive inside a "result" envelope and the features
block arrives as a LIST of objects keyed by "name", so that is the path the
tests pin. The mapping form is still read because it costs one branch and
because a container shape is not a field alias. No field alias is accepted for
the feature's name, and the recording is the reason that matters more now than
it did: the same objects carry a "tag", which is the platform's machine
identifier, and a reader that accepted "tag" as a second spelling of the name
would have silently swapped the display name for the tag on a shape change.
"tag" is surfaced as its own column instead, which is data rather than a guess.

Importing this module is side effect free. It only runs when Splunk invokes it
as a subprocess.
"""

import os
import sys
import time

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import ps_log
from ps_client import ClientConfigurationError, get_client
from ps_sanitize import sanitize
from usage_store import THROTTLE_SECONDS, UsageStore

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    dispatch,
)

COMMAND_NAME = "polyswarmusage"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "cmd_usage"

# Row discriminator, present on every row.
#
# One command emitting rows of three different shapes needs a name for which
# shape a row is, or a dashboard has to guess from which fields are populated
# and a search bar user has to read the source. It is first in the table on the
# dashboard for the same reason.
ROW_TYPE_FIELD = "row_type"

ROW_TYPE_ACCOUNT = "account"
ROW_TYPE_FEATURE = "feature"
ROW_TYPE_THROTTLED = "throttled"

# Account identity, from the whois endpoint.
#
# WHAT IS DELIBERATELY NOT HERE. The recorded whois response also carries
# account_name and account_number, and the accounts response carries
# account_number and user_account_number. None of them is emitted. They
# identify the customer rather than describing their entitlement, they would be
# written into a KV collection and rendered in a dashboard by a command whose
# purpose is quota, and nothing on this surface needs them. A field that is not
# read cannot leak.
ACCOUNT_TYPE_FIELD = "account_type"
TENANT_FIELD = "tenant"
COMMUNITIES_FIELD = "communities"

IDENTITY_FIELDS = (ACCOUNT_TYPE_FIELD, TENANT_FIELD, COMMUNITIES_FIELD)

# The plan the account is on, from the accounts endpoint's top level rather
# than from its features block. These ride on the account row, not on a feature
# row: they describe the whole plan and there is one of each per account.
#
# daily_api_limit and daily_api_remaining are the pair design 4.6 asks for by
# name, "quota consumed against entitled", and they are the only place on this
# surface where a customer can read today's headroom. Note from the recording
# that a limit of 0 with a remaining of -1 is what an unmetered internal plan
# looks like, so nothing downstream may treat remaining as a count without
# checking its sign; the Overview panel's arithmetic guards on it.
ACCOUNT_PLAN_NAME_FIELD = "account_plan_name"
IS_TRIAL_FIELD = "is_trial"
DAILY_API_LIMIT_FIELD = "daily_api_limit"
DAILY_API_REMAINING_FIELD = "daily_api_remaining"
PLAN_PERIOD_END_FIELD = "plan_period_end"

# Declared in the order they appear on the row, so a table reads plan, then
# trial state, then today's numbers, then when the period ends.
PLAN_FIELDS = (
    ACCOUNT_PLAN_NAME_FIELD,
    IS_TRIAL_FIELD,
    DAILY_API_LIMIT_FIELD,
    DAILY_API_REMAINING_FIELD,
    PLAN_PERIOD_END_FIELD,
)

# Which reader each plan field gets. Split by the type the recording shows
# rather than by guessing per call site, because the whole doctrine of this
# module is that a value of the wrong type is omitted instead of coerced.
PLAN_NUMBER_FIELDS = (DAILY_API_LIMIT_FIELD, DAILY_API_REMAINING_FIELD)
PLAN_FLAG_FIELDS = (IS_TRIAL_FIELD,)

# Per feature entitlement, from the accounts endpoint's features block.
FEATURE_FIELD = "feature"
BASE_USES_FIELD = "base_uses"
REMAINING_USES_FIELD = "remaining_uses"
OVERAGE_FIELD = "overage"

QUOTA_FIELDS = (BASE_USES_FIELD, REMAINING_USES_FIELD, OVERAGE_FIELD)

# The two descriptive fields a recorded feature carries beside its numbers.
#
# tag is the platform's stable machine identifier for the feature, for example
# sandbox_download, where the name is a display string. It is the field an
# operator correlates against a price book or a support conversation, and it is
# the one field on this surface that is safe to match on in SPL, because a
# display name is free to be reworded.
#
# NAMED feature_type AND NOT type, WHICH IS WHAT THE API CALLS IT. Every row
# this command emits already carries row_type, and a table with row_type and
# type side by side is a table an analyst misreads. The prefix also keeps the
# dashboard assertion honest: "type" is a substring of "row_type", so a test
# that checks a panel names its columns would have passed for free.
TAG_FIELD = "tag"
FEATURE_TYPE_FIELD = "feature_type"

FEATURE_DETAIL_FIELDS = (TAG_FIELD, FEATURE_TYPE_FIELD)

# When the answer was obtained. On every row, including the throttle notice, so
# that a panel reading the stored copy can say "as of" without a second lookup.
FETCHED_AT_FIELD = "fetched_at"

MESSAGE_FIELD = "message"

# Every field this command can emit, in the order a row carries them.
#
# Three things are asserted against this tuple and each one closes a different
# silent-loss path: the shipped lookup definition's projection in
# default/transforms.conf, because a field absent from fields_list is not
# returned by | inputlookup even though the document carries it; the field
# declarations in default/collections.conf; and the columns of both Overview
# entitlement panels.
#
# It is also the header of the emitted chunk. See the docstring: output_row()
# pads every row to this tuple, so the order here is the column order a
# customer sees, and it is a tuple rather than a set for that reason.
ALL_FIELDS = (
    (ROW_TYPE_FIELD, FETCHED_AT_FIELD, MESSAGE_FIELD, FEATURE_FIELD)
    + FEATURE_DETAIL_FIELDS
    + QUOTA_FIELDS
    + IDENTITY_FIELDS
    + PLAN_FIELDS
)

# The key the account endpoints wrap their body in.
#
# TRAP, and it is decision D4's trap in a second place: an object can carry its
# own "result" key next to an envelope's. So the envelope is recognised by the
# TYPE of the value and never by the presence of the name, and only a mapping is
# descended into.
ENVELOPE_FIELD = "result"

# The key the accounts endpoint holds the per feature entitlement under.
FEATURES_FIELD = "features"

# The key a feature carries its own name under, in the list form of the
# features block. Exactly one name is accepted and there are no aliases: D4
# established that accepting a name the platform never sends hides a real shape
# change behind it, and the recording is now what says which single name is
# right. tests/fixtures/accounts-recorded.json shows "name" carrying the
# display string, alongside a "tag" carrying the machine identifier, so
# accepting "tag" as a fallback spelling would have quietly replaced every
# display name with a tag the first time the platform stopped sending "name".
FEATURE_NAME_FIELD = "name"

# The API-side names of the two descriptive fields. Held separately from the
# emitted column names because one of them is renamed on the way out: the
# response calls it "type" and this command emits it as feature_type, for the
# reason written on FEATURE_TYPE_FIELD. One place per direction of that
# mapping, so a reader cannot find only half of it.
FEATURE_TAG_SOURCE = "tag"
FEATURE_TYPE_SOURCE = "type"

FEATURE_DETAIL_SOURCES = (
    (TAG_FIELD, FEATURE_TAG_SOURCE),
    (FEATURE_TYPE_FIELD, FEATURE_TYPE_SOURCE),
)

COMMUNITIES_SEPARATOR = ", "

# How a readable boolean renders in a row. Lower case, because these are SPL
# field values a customer will write a where clause against and SPL's own
# true() and false() are lower case.
TRUE_TEXT = "true"
FALSE_TEXT = "false"

# Hard cap on feature rows.
#
# Not a tuning knob and not a quota ceiling: it is a bound on what a malformed
# or unexpectedly large features block can do to a search. A mapping with fifty
# thousand entries in it would otherwise become fifty thousand rows and fifty
# thousand KV store documents on the write-through. The real answer is a handful
# of features, so a cap two orders of magnitude above that is invisible in
# normal operation and load bearing in the one case that matters.
MAX_FEATURE_ROWS = 200

THROTTLED_MESSAGE = (
    "Throttled, showing nothing. polyswarmusage calls the PolySwarm account "
    "endpoints at most once every {0} seconds per search head, so that a "
    "dashboard refresh cannot call them in a loop. The Entitlement panel on "
    "the PolySwarm Overview dashboard shows the last stored answer and its "
    "age.".format(int(THROTTLE_SECONDS))
)

TRUNCATED_MESSAGE = (
    "PolySwarm reported more than {0} entitlement features and the rest were "
    "not emitted.".format(MAX_FEATURE_ROWS)
)

DEGRADED_MESSAGE = (
    "PolySwarm usage ran without its KV store, so the once-a-minute call "
    "throttle could not be applied and no answer was stored for the "
    "Entitlement panel. Check that the app is fully installed and that the KV "
    "store is available."
)

# No module logger here. Everything this command writes goes through ps_log, so
# that the whitelist is the only route a value has into a log line.


# ---------------------------------------------------------------------------
# Reading the two responses
# ---------------------------------------------------------------------------


def unwrap(payload):
    """Return the object an account response carries, or None.

    Descends into the envelope only when its "result" is a mapping. See the
    TRAP note on ENVELOPE_FIELD: an object carrying its own boolean "result"
    must not be mistaken for an envelope, and following the name alone would
    descend into False and report nothing for an account the platform answered
    on.
    """
    if not isinstance(payload, dict):
        return None
    inner = payload.get(ENVELOPE_FIELD)
    if isinstance(inner, dict):
        return inner
    return payload


def read_scalar(value):
    """Return one identity value as a string, or None when unreadable.

    A mapping, a list, a boolean and an absent value all read the same way to
    the caller, which is that there is nothing here to show, so they are not
    distinguished. A boolean is refused rather than rendered as true, because
    no identity field this command emits is a flag and a "true" in a tenant
    column is worse than an empty one.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    return text or None


def read_number(value):
    """Return one quota value as an int or float, or None when unreadable.

    A numeric string is accepted, because a JSON body that quotes its numbers
    is still telling us the number. A boolean is not: True would arrive as 1
    and a base_uses of 1 is a claim about a customer's plan.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return None


def read_flag(value):
    """Return one boolean field as "true" or "false", or None when unreadable.

    THE MIRROR IMAGE OF read_number's BOOLEAN RULE, AND FOR THE SAME REASON.
    read_number refuses a boolean because True coerces to 1 and a base_uses of
    1 is a claim about a customer's plan. This refuses a NUMBER, because 0 and
    1 coerce to False and True just as readily and "is_trial: false" on an
    account the app could not read is the same kind of false statement in the
    other direction. Only a real boolean, or a body that quotes its booleans,
    reads at all.

    Rendered as text rather than passed through as a Python bool because these
    rows are written into a KV collection and shown in a Studio table, and
    "True" with a capital letter is Python's rendering leaking into a
    customer's dashboard.
    """
    if isinstance(value, bool):
        return TRUE_TEXT if value else FALSE_TEXT
    if isinstance(value, str):
        text = value.strip().lower()
        if text == TRUE_TEXT:
            return TRUE_TEXT
        if text == FALSE_TEXT:
            return FALSE_TEXT
    return None


def read_communities(value):
    """Return the account's communities as one joined string, or None.

    A list of names is joined. A single name is passed through. A mapping is
    refused: a communities object keyed by something is a different shape and
    picking its keys or its values would be a guess about which of the two the
    customer's community names are.
    """
    if isinstance(value, (list, tuple)):
        names = []
        for entry in value:
            text = read_scalar(entry)
            if text is not None:
                names.append(text)
        if not names:
            return None
        return COMMUNITIES_SEPARATOR.join(names)
    return read_scalar(value)


def read_identity(payload):
    """Return the identity fields from a whois response.

    Only the fields that are readable are returned. An unreadable field is
    omitted rather than emitted empty, matching cmd_search.build_output_fields:
    a column that is absent says the app has nothing, and a column present and
    blank reads as the platform having answered with nothing.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        return {}

    identity = {}

    account_type = read_scalar(body.get(ACCOUNT_TYPE_FIELD))
    if account_type is not None:
        identity[ACCOUNT_TYPE_FIELD] = account_type

    tenant = read_scalar(body.get(TENANT_FIELD))
    if tenant is not None:
        identity[TENANT_FIELD] = tenant

    communities = read_communities(body.get(COMMUNITIES_FIELD))
    if communities is not None:
        identity[COMMUNITIES_FIELD] = communities

    return identity


def read_plan(payload):
    """Return the plan fields from an accounts response.

    The other half of the account row. read_identity() answers "which account
    is this" out of whois; this answers "on what plan, with what left today"
    out of the top level of the accounts response, beside the features block
    rather than inside it.

    Same omit-if-unreadable rule and the same refusal to carry a field this
    command has not declared. Note what the recording makes ordinary rather
    than exceptional: plan_period_end is null on an account with no period end,
    so that field being absent from the row is the normal reading of a healthy
    response and not a sign of a shape change.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        return {}

    plan = {}
    for name in PLAN_FIELDS:
        raw = body.get(name)
        if name in PLAN_NUMBER_FIELDS:
            value = read_number(raw)
        elif name in PLAN_FLAG_FIELDS:
            value = read_flag(raw)
        else:
            value = read_scalar(raw)
        if value is not None:
            plan[name] = value
    return plan


def read_features(payload):
    """Return [(feature name, attributes)] from an accounts response.

    Sorted by name, so the rows and therefore a dashboard table are stable
    between refreshes rather than reordering with whatever the API iterated.

    Two container shapes are accepted, and that tolerance is structural rather
    than a set of field aliases. A mapping of name to attributes carries the
    name as its key; a list of objects carries it in a field. Nothing else is
    accepted and no second spelling of the name field is, per the note on
    FEATURE_NAME_FIELD.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        return []

    features = body.get(FEATURES_FIELD)
    found = []

    if isinstance(features, dict):
        for name in features:
            attributes = features[name]
            if not isinstance(attributes, dict):
                continue
            text = read_scalar(name)
            if text is None:
                continue
            found.append((text, attributes))
    elif isinstance(features, (list, tuple)):
        for entry in features:
            if not isinstance(entry, dict):
                continue
            text = read_scalar(entry.get(FEATURE_NAME_FIELD))
            if text is None:
                continue
            found.append((text, entry))

    found.sort(key=lambda pair: pair[0])
    return found


def read_quota(attributes):
    """Return the readable quota fields of one feature."""
    if not isinstance(attributes, dict):
        return {}
    quota = {}
    for name in QUOTA_FIELDS:
        value = read_number(attributes.get(name))
        if value is not None:
            quota[name] = value
    return quota


def read_feature_details(attributes):
    """Return the readable descriptive fields of one feature.

    Separate from read_quota because these are strings and those are numbers,
    and the two readers refuse different things: a boolean must not become a 1
    in a quota column, and a mapping must not become a repr in a tag column.
    One reader over a mixed field list would have to branch per field anyway,
    and it would be the place a later field got the wrong branch.

    This is also where the one rename on this surface happens, "type" in to
    feature_type out. See FEATURE_TYPE_FIELD.
    """
    if not isinstance(attributes, dict):
        return {}
    details = {}
    for name, source in FEATURE_DETAIL_SOURCES:
        value = read_scalar(attributes.get(source))
        if value is not None:
            details[name] = value
    return details


# ---------------------------------------------------------------------------
# Building rows
# ---------------------------------------------------------------------------


def account_row(identity, plan, fetched_at):
    """Return the one account identity and plan row.

    Emitted even when both responses were unreadable, carrying its row_type
    and nothing else. That is the honest answer to "which account is this": the
    app asked and could not read the reply. Omitting the row entirely would
    render as a table of features belonging to nobody in particular.

    :param identity: the readable whois fields, from read_identity().
    :param plan: the readable accounts plan fields, from read_plan().
    :param fetched_at: epoch seconds the answer was obtained.
    """
    row = {ROW_TYPE_FIELD: ROW_TYPE_ACCOUNT, FETCHED_AT_FIELD: fetched_at}
    for source, names in ((identity, IDENTITY_FIELDS), (plan, PLAN_FIELDS)):
        for name in names:
            if name in source:
                row[name] = source[name]
    return row


def feature_rows(features, fetched_at):
    """Return one row per feature, capped at MAX_FEATURE_ROWS."""
    rows = []
    for name, attributes in features[:MAX_FEATURE_ROWS]:
        row = {
            ROW_TYPE_FIELD: ROW_TYPE_FEATURE,
            FEATURE_FIELD: name,
            FETCHED_AT_FIELD: fetched_at,
        }
        row.update(read_feature_details(attributes))
        row.update(read_quota(attributes))
        rows.append(row)
    return rows


def throttle_notice_row(fetched_at):
    """Return the single row a throttled invocation emits.

    A typed notice, not fabricated data. It carries no account fields and no
    quota numbers, which is what "showing nothing" means here: the panel is
    told why it is empty instead of being left to look broken. Constraint C6
    forbids inventing data on an error path and nothing is invented on this one.
    """
    return {
        ROW_TYPE_FIELD: ROW_TYPE_THROTTLED,
        FETCHED_AT_FIELD: fetched_at,
        MESSAGE_FIELD: THROTTLED_MESSAGE,
    }


def build_rows(identity, plan, features, fetched_at):
    """Return the full row sequence for one successful invocation."""
    return [account_row(identity, plan, fetched_at)] + feature_rows(
        features, fetched_at
    )


def output_row(row):
    """Return one row padded to ALL_FIELDS, ready to be yielded.

    THE FIX FOR THE LIVE DEFECT. The module docstring has the whole account of
    it; the short version is that splunklib fixes a chunk's CSV header from the
    keys of the first record written into that chunk, the account row goes
    first and has no feature keys on it, and so every feature value was being
    projected away by the writer before splunkd ever saw it.

    Nothing is invented here, and the reason is mechanical rather than a matter
    of judgement. splunklib's RecordWriter._write_record reads each header field
    off the record with record.get(fieldname, None) and writes both an absent
    key and a None value as the same pair of empty CSV cells, which Splunk reads
    as the field not being present on that event. So a padded row and an
    unpadded row produce identical bytes; the padding exists only so that the
    first row's key list names every column the command can fill. The omit-if-
    unreadable rule is untouched: an unreadable quota still renders as an empty
    cell and never as a zero.

    The rows written through to the KV store are the unpadded ones. See
    UsageReporter.rows(): padding belongs to the emission boundary, and a
    stored document full of nulls would be a different, worse thing.

    Field order follows ALL_FIELDS, which makes the emitted column order
    deterministic. Registering the names on the record writer's custom_fields
    set was the alternative and was rejected: it reaches into a private
    splunklib attribute, and a set has no order, so the columns after the first
    row's own would arrive in a different order on every run.
    """
    padded = {}
    for name in ALL_FIELDS:
        padded[name] = row.get(name)
    return padded


# ---------------------------------------------------------------------------
# The reporting pass
# ---------------------------------------------------------------------------


class UsageReporter(object):
    """Calls the two account endpoints and returns the rows.

    Split out from the command class for the reason IocEnricher is: a
    GeneratingCommand cannot be instantiated meaningfully outside the chunked
    protocol handshake, so logic left inside it is logic no test can reach. This
    class takes anything with whois() and accounts() methods and an optional
    store, so the whole pass runs with a fake client, a fake KV store, and a
    fake clock.
    """

    def __init__(self, client, store=None, now=None):
        """
        :param client: anything with whois() and accounts() methods.
        :param store: a usage_store.UsageStore, or None to run with no throttle
            and no write-through at all. None is a supported mode rather than a
            degradation: it is what the reporter does outside splunkd.
        :param now: a callable returning epoch seconds, for tests.
        """
        self.client = client
        self.store = store
        self._now = time.time if now is None else now

        self.throttled = False
        self.truncated = False
        self.stored = 0

    def rows(self):
        """Return the rows for one invocation.

        Order of operations, and each step is in this order for a reason:

          1. Check the throttle. A call inside the window is not made.
          2. Record the attempt, BEFORE calling out, so a failing call still
             spends the window. See the note in usage_store.
          3. Call whois, then accounts.
          4. Write the rows through to the cache, only on success.

        The accounts response is read twice, once for the plan fields on the
        account row and once for the features block. That is two readers over
        one body and not two requests: the body is held in a local, and the
        call counter on the client is what the tests assert against.

        The rows returned here are UNPADDED, which is what the write-through
        stores. output_row() is applied at the yield in generate() and nowhere
        else.

        Nothing is caught here. An authentication failure or a transport failure
        propagates, because it affects the whole answer rather than one row of
        it and because constraint C6 forbids turning it into synthetic data. The
        analyst gets the client's sanitized message.
        """
        fetched_at = float(self._now())

        if self.store is not None and self.store.throttled():
            self.throttled = True
            ps_log.info(LOG_COMPONENT, "call", "throttled")
            return [throttle_notice_row(fetched_at)]

        if self.store is not None:
            self.store.record_attempt()

        identity = read_identity(self.client.whois())

        accounts = self.client.accounts()
        plan = read_plan(accounts)
        features = read_features(accounts)
        self.truncated = len(features) > MAX_FEATURE_ROWS

        rows = build_rows(identity, plan, features, fetched_at)

        if self.store is not None:
            self.stored = self.store.write_through(rows)

        return rows


def build_client(service):
    """Return a configured client, or fail with a message naming the command.

    Constraint C8: unconfigured means a clear message and zero network calls.
    ps_client already refuses without a stored credential and already names the
    setup page; what it cannot know is which command the customer was running,
    and "no API key is stored" arriving from a search the customer did not
    associate with a credential is a support ticket. So the command's own name
    goes on the front of it.
    """
    try:
        return get_client(service)
    except ClientConfigurationError as error:
        raise ClientConfigurationError(
            "polyswarmusage cannot report entitlement without a configured "
            "PolySwarm API key. {0}".format(error)
        )


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


@Configuration()
class PolySwarmUsageCommand(GeneratingCommand):
    """Report the PolySwarm account's identity and per feature entitlement.

    A plain @Configuration() on a GeneratingCommand runs the command locally on
    the search head: splunklib's distributed setting defaults to False, and its
    protocol v2 serialisation turns the default streaming type into stateful
    when it is. That default is required rather than merely convenient here,
    because the command reads the API key out of storage/passwords, which
    exists on the search head and not on an indexer.
    """

    def generate(self):
        # ONE START LINE AND ONE FINISH LINE PER INVOCATION, matching
        # cmd_search. A start with no finish is a command that died or was
        # killed, which is the "nothing is happening" a customer reports and
        # which nothing else distinguishes from a legitimately empty answer.
        timer = ps_log.Timer()
        ps_log.info(LOG_COMPONENT, "start", "ok")

        service = getattr(self, "service", None)
        client = build_client(service)

        # Built even when the collections are missing. UsageStore reports "not
        # throttled" and stores nothing in that case, so constructing it
        # unconditionally keeps the present and absent paths the same code
        # rather than two paths where only one is exercised.
        store = UsageStore(service)
        reporter = UsageReporter(client, store=store)

        # output_row() before sanitize(), not after. Padding adds only keys
        # already declared in ALL_FIELDS and only None values, and a test
        # asserts no declared field name is credential shaped, so the order is
        # not load bearing for redaction; it is this way round because
        # sanitize() is the last thing that touches a value on its way out and
        # that property is worth keeping true by construction.
        emitted = 0
        for row in reporter.rows():
            emitted += 1
            yield sanitize(output_row(row))

        ps_log.info(
            LOG_COMPONENT,
            "finish",
            "ok",
            records=emitted,
            duration_ms=timer.duration_ms,
        )

        if reporter.throttled:
            self.write_warning(THROTTLED_MESSAGE)

        if reporter.truncated:
            self.write_warning(TRUNCATED_MESSAGE)

        if store.degraded:
            self.write_warning(DEGRADED_MESSAGE)


def main(argv=None):
    """Console entry point invoked by Splunk."""
    dispatch(
        PolySwarmUsageCommand,
        argv if argv is not None else sys.argv,
        sys.stdin,
        sys.stdout,
        __name__,
    )


if __name__ == "__main__":
    main()
