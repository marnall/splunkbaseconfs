"""Search command entry point for polyswarmsearch.

Registered in default/commands.conf as a chunked (v2 protocol) command.

    ... | polyswarmsearch limit=500
    ... | polyswarmsearch field=sha256 limit=100
    ... | polyswarmsearch field=url limit=100
    ... | polyswarmsearch field=query ioctype=url limit=100

Looks each distinct indicator in the result set up against the PolySwarm API and
annotates the event with the platform's verdict.

Output fields. The response shape they are read from is pinned by two recorded
live responses; see the RESPONSE SHAPE note below.

    polyswarm_polyscore     the platform's score, 0.0 to 1.0
    polyswarm_verdict       malicious, suspicious, benign, or unknown
    polyswarm_detections    "malicious/total" across engines
    polyswarm_permalink     a link to the scan result in the web UI

Two more fields describe how the answer was obtained, or why there is not one,
rather than what it says:

    polyswarm_cache         hit when the answer came out of the KV store cache
                            and cost no quota, live when a request was made.
                            Absent when no lookup was attempted at all, which
                            is the case for a blank value, for a value no
                            endpoint answers for, and for an event past the
                            limit.
    polyswarm_note          why no lookup was attempted, on the events where
                            none was. Absent otherwise. See THE ROUTING TABLE,
                            and the note at STOP_AUTH for the two failures that
                            stop a search and put their reason here.

A MULTIVALUE INPUT FIELD IS ENRICHED MEMBER BY MEMBER. Splunk delivers a
multivalue field as a list, which is the ordinary shape after `stats values()`
and after polyswarmextract, so every member is looked up and the output fields
come back as lists aligned index for index with the input, exactly as
polyswarmextract's three fields are. See the block comment at
MULTIVALUE_ABSENT.

Four more fields arrive only with attribution=true, which is OFF BY DEFAULT
because it spends one extra request per distinct sha256:

    polyswarm_families      the malware families on file for the artifact,
                            multivalue
    polyswarm_tags          the namespaced tags, verbatim, multivalue
    polyswarm_actor         the actor: tag values with the prefix stripped,
                            multivalue
    polyswarm_emerging      the platform's emerging timestamp, when it has one

All four are ABSENT rather than empty when the platform holds no attribution
for an artifact, and no note is written for that, because most artifacts have
none and it is a fact about the artifact rather than a limit of the app. The
block comment at ACTOR_TAG_PREFIX has the reasoning, the cost and the second
cap; the response shape is marked PROVISIONAL-SDK and the caveat is stated
where the reader is, because it is the one shape in this app that is not pinned
by a recorded live response.

THE ROUTING TABLE
-----------------
A Splunk field holds one value and the platform has one endpoint per indicator
class, so the command has to choose. ioctype governs that, and defaults to auto.

    auto (default)  classify the value with extract_engine.classify_ioc and
                    route on the type
    hash            force the sha256 artifact search, no classification
    url             force the URL search, no classification

In auto mode:

    sha256          -> ps_client.search_hash
    url             -> ps_client.search_url
    domain          -> ps_client.search_url, queried as the bare host
    md5, sha1       -> no request. unknown, plus a note.
    ip, email       -> no request. unknown, plus a note.
    unclassifiable  -> no request. unknown, plus a note.

The three no-request rows are the honest half of this command and they are not
a placeholder for something better. md5 and sha1 are refused because the
platform's artifact search takes a sha256: there is no md5 endpoint to call, and
inventing one would either 404 on every event or answer about something else. An
address is refused because no recorded response for an address exists in this
repository, and design constraint C10 says a field is not a feature until one
does. In every one of those cases the command spends nothing, says unknown, and
says why in polyswarm_note, so an analyst reading a screen of unknowns can tell
"we have no way to ask" from "we asked and the platform has nothing".

Both endpoints answer in the same envelope and the same artifact shape, which is
a recorded fact and not an assumption: tests/fixtures/search-url-recorded.json
and tests/fixtures/search-hash-recorded.json have the same key sets, asserted in
tests/fixtures/test_search_url_fixture_integrity.py. That is why routing added a
second endpoint and no second reader of a response.

Why limit is required
---------------------
This command spends a customer's API quota, one request per distinct hash. A
search over an index can produce millions of distinct hashes, and an analyst
who pipes a wide search into an enrichment command by accident should get an
error, not a drained quota and a rate limit. So there is no default. The
operator states the ceiling every time, and the command refuses to run without
one. The hard cap exists on top of that, because a mistyped limit is as easy to
make as an omitted one.

Two caches, and they are not the same cache
-------------------------------------------
1. Per-search dedup, held on the enricher for the duration of one search. Each
   distinct indicator costs exactly one request per search, no matter how many
   events carry it. Repeated values are common in real data: the same binary
   across a fleet is the normal case, not an edge case, and a search over a day
   of process-execution events can carry one hash thousands of times. A proxy
   log carries one domain far more often than that. This one is not shared
   between searches.

2. The KV store verdict cache in bin/verdict_cache.py, which does outlive a
   search, for the default 24 hours of design section 4.1. It is what makes the
   second search over the same data cost nothing, and what makes the triage
   dashboard in section 4.8 free to open.

The limit counts distinct hashes looked up, not input events, for the same
reason: it is a quota ceiling, and quota is spent per lookup. A KV cache hit
spends no quota, so it does not count against the limit either. That ordering
is deliberate and is written out at the check itself.

THE LIMIT IS A CEILING FOR THE SEARCH AND NOT FOR A CHUNK. Splunk hands a
streaming command its input in chunks and calls stream() once for each, so the
client, the verdict cache and the enricher are built on the first call and
reused for the rest of the search, and the finish line is written on the last
chunk. The note at PolySwarmSearchCommand's per-search state has the protocol
detail and the line numbers in the vendored SDK.

Importing this module is side effect free. It only runs when Splunk invokes it
as a subprocess.
"""

import os
import sys

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import ps_log
from extract_engine import classify_ioc
from ps_client import (
    AuthenticationError,
    ClientConfigurationError,
    RateLimitError,
    get_client,
)
from ps_sanitize import sanitize, sanitize_message
from verdict_cache import VerdictCache

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
    validators,
)

COMMAND_NAME = "polyswarmsearch"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "cmd_search"

# The field the command reads hashes out of by default. file_hash is the CIM
# field name in the Malware and Endpoint data models, so the default works
# against CIM-compliant data with no option.
DEFAULT_HASH_FIELD = "file_hash"

# The most distinct indicators one invocation will ever look up. A ceiling on
# blast radius, not a tuning knob: a runaway search costs quota and trips the
# customer's rate limit, and both of those outlive the search that caused them.
MAX_LIMIT = 10000
MIN_LIMIT = 1

# ---------------------------------------------------------------------------
# IOC type routing
# ---------------------------------------------------------------------------

# The ioctype option's accepted values, and the endpoint names they force.
#
# auto is the default because the alternative is worse for the surface this
# command actually serves. Workflow actions dispatch this command with one
# field value and no idea what type it holds: the enrich action is offered on
# eleven field names spanning hashes, URLs, domains and addresses, and a menu
# entry that needed the analyst to pick the right ioctype first would be a menu
# entry that is wrong most of the time. The two forced modes exist for the case
# auto cannot cover, which is a value the classifier will not recognise but the
# operator knows the type of.
IOCTYPE_AUTO = "auto"
IOCTYPE_HASH = "hash"
IOCTYPE_URL = "url"
IOCTYPE_VALUES = (IOCTYPE_AUTO, IOCTYPE_HASH, IOCTYPE_URL)
DEFAULT_IOCTYPE = IOCTYPE_AUTO

# Endpoint names. Deliberately the same two strings as the forced ioctype values
# so there is one vocabulary for "which endpoint", and ROUTE_NONE for "none of
# them", which is a routing outcome and not a failure.
ROUTE_HASH = IOCTYPE_HASH
ROUTE_URL = IOCTYPE_URL
ROUTE_NONE = None

# THE AUTO ROUTING TABLE, AS DATA.
#
# Every type extract_engine can classify appears here, mapped to the endpoint
# that answers for it or to ROUTE_NONE. It is a table rather than a chain of
# ifs so that the tests can read it and enumerate it: a test asserts that every
# member of extract_engine.IOC_TYPES has a row, which is what stops a new type
# in the engine from silently falling through to the unclassified path.
AUTO_ROUTES = {
    "sha256": ROUTE_HASH,
    "url": ROUTE_URL,
    # A DOMAIN GOES TO THE URL ENDPOINT AS A BARE HOST, AND THAT IS RECORDED.
    # tests/fixtures/search-url-recorded.json was captured by querying
    # google.com with no scheme and no path, and the platform answered 200 with
    # a full artifact. So nothing synthesises an https:// prefix onto a domain
    # field: the recording says the bare host is what the endpoint takes, and a
    # synthesised scheme would ask about a different resource and would have to
    # guess between http and https to do it.
    "domain": ROUTE_URL,
    "md5": ROUTE_NONE,
    "sha1": ROUTE_NONE,
    "ip": ROUTE_NONE,
    "email": ROUTE_NONE,
}

# Types whose two spellings are the same indicator, so their cache key may be
# case folded. Everything here is either hexadecimal or a DNS name, both of
# which are case insensitive by specification.
#
# url IS ABSENT AND THAT IS THE WHOLE POINT OF THIS SET. A URL path and query
# are case sensitive, so /Report and /report are two resources. Folding them
# into one cache key would not waste a lookup, it would serve one verdict for
# two different things, and a wrong answer is the one thing a cache may never
# produce. See verdict_cache.document_id_for.
FOLD_CASE_TYPES = frozenset(["sha256", "sha1", "md5", "ip", "domain"])

# WHY THE NO-REQUEST ROWS SAY WHY, IN THE RESULT AND NOT ONLY IN A DOC.
#
# Without a note, an md5 field and a URL the platform has never seen produce the
# identical row: verdict unknown, nothing else. Those are completely different
# facts. One means "we asked and there is nothing on file", the other means "we
# cannot ask at all", and an analyst who cannot tell them apart concludes the
# platform is empty when the truth is that the app declined to guess. So the
# reason travels with the event. It is also what makes this honest rather than
# quietly thin: the limitation arrives in the analyst's own results.
NOTE_HASH_TYPE_UNSUPPORTED = (
    "PolySwarm artifact search takes a sha256, so a {0} cannot be looked up. "
    "No request was made and no verdict is claimed for this value."
)
NOTE_NO_RECORDED_ENDPOINT = (
    "This app has no recorded PolySwarm lookup endpoint for a {0} indicator, "
    "so no request was made and no verdict is claimed for this value."
)
NOTE_UNCLASSIFIED = (
    "This value was not recognised as a sha256, a URL, or a domain, so no "
    "request was made and no verdict is claimed for it. Add ioctype=hash or "
    "ioctype=url to polyswarmsearch to route it explicitly."
)

# WHY TWO FAILURES STOP THE WHOLE SEARCH, AND ONLY TWO.
#
# A lookup that fails for one value is a bad afternoon on one indicator: the
# row is reported unknown, the count is reported once by report_failures(), and
# the search carries on. That is right for a 500 on one hash and wrong for
# these two.
#
# A rejected API key is rejected for every remaining value in the search. A
# rate limit that survived the client's three attempts is a ceiling the
# customer's account has reached, not a fact about one indicator. Retrying
# either one per value spends thousands of requests that cannot succeed, and on
# the authentication path each one is a further failed credential attempt
# against the customer's own account, which is how a key gets locked out.
#
# So the first of either stops enrichment for the rest of the search. The
# remaining rows are still emitted, with the reason in polyswarm_note, and one
# warning line says what happened. An analyst has to be able to tell "the key
# saved on the setup page is wrong" from "the platform knows nothing about any
# of this", and those two produce the same screen of unknowns otherwise.
STOP_AUTH = "authentication"
STOP_RATE_LIMIT = "rate_limit"

NOTE_STOPPED_AUTH = (
    "PolySwarm rejected this app's API key, so enrichment stopped for this "
    "search and no verdict is claimed for this value. Check the key saved on "
    "the app setup page."
)
NOTE_STOPPED_RATE_LIMIT = (
    "PolySwarm rate limited this search and the request was still refused "
    "after the client's retries, so enrichment stopped for this search and no "
    "verdict is claimed for this value. Run the search again later, or with a "
    "lower limit."
)

# The note each stop puts on every row after it. One per reason, so a reason
# that is added later cannot end up with no note.
STOP_NOTES = {
    STOP_AUTH: NOTE_STOPPED_AUTH,
    STOP_RATE_LIMIT: NOTE_STOPPED_RATE_LIMIT,
}

# The one warning line each stop writes to the search job, formatted with the
# number of requests spent before the stop and the first sanitized message.
# ONE LINE PER SEARCH, NOT ONE PER ROW: the per-row reason is the note above,
# and a warning per row would be ten thousand copies of one sentence.
STOP_REPORTS = {
    STOP_AUTH: (
        "PolySwarm enrichment stopped after {0} requests because the platform "
        "rejected this app's API key. The remaining events are reported as "
        "unknown, with the reason in polyswarm_note. Check the key saved on "
        "the app setup page. First failure: {1}"
    ),
    STOP_RATE_LIMIT: (
        "PolySwarm enrichment stopped after {0} requests because the platform "
        "rate limited this search and the request was still refused after the "
        "client's retries. The remaining events are reported as unknown, with "
        "the reason in polyswarm_note. Run the search again later, or with a "
        "lower limit. First failure: {1}"
    ),
}

# One note per unrouted type. Built from the routing table rather than written
# out beside it, so a type that stops being routed cannot end up with no note.
AUTO_NOTES = {
    "md5": NOTE_HASH_TYPE_UNSUPPORTED.format("md5"),
    "sha1": NOTE_HASH_TYPE_UNSUPPORTED.format("sha1"),
    "ip": NOTE_NO_RECORDED_ENDPOINT.format("network address"),
    "email": NOTE_NO_RECORDED_ENDPOINT.format("email address"),
}

# Verdict bands, applied to the polyscore. Inclusive lower bounds: exactly 0.7
# is malicious and exactly 0.4 is suspicious. The boundaries are tested at their
# exact values because a band expressed with the wrong comparison is invisible
# in ordinary data and only shows up on the one event that sits on the edge.
MALICIOUS_THRESHOLD = 0.7
SUSPICIOUS_THRESHOLD = 0.4

VERDICT_MALICIOUS = "malicious"
VERDICT_SUSPICIOUS = "suspicious"
VERDICT_BENIGN = "benign"

# Used when the platform has no opinion: nothing on file, a response with no
# score, or a low score backed by no engine detections at all. Deliberately
# distinct from benign. "We have never seen this file" and "we have seen this
# file and it is clean" are different answers, and collapsing them into benign
# would tell an analyst a hash is safe when it is merely unknown.
VERDICT_UNKNOWN = "unknown"

# Output field names. Part of the command's public contract.
POLYSCORE_FIELD = "polyswarm_polyscore"
VERDICT_FIELD = "polyswarm_verdict"
DETECTIONS_FIELD = "polyswarm_detections"
PERMALINK_FIELD = "polyswarm_permalink"

OUTPUT_FIELDS = (
    POLYSCORE_FIELD,
    VERDICT_FIELD,
    DETECTIONS_FIELD,
    PERMALINK_FIELD,
)

# Cost provenance, kept out of OUTPUT_FIELDS on purpose.
#
# OUTPUT_FIELDS is the set of fields derived from a response payload, and
# build_output_fields() is asserted against it field for field. This one is not
# derived from the payload at all: it records where the answer came from, which
# only the enrichment pass knows. Folding it into OUTPUT_FIELDS would make the
# payload reader responsible for a fact it cannot see.
#
# It is here because the cache is a commercial claim. "Repeated enrichment
# costs zero quota" is checkable in a search bar with this field and not
# otherwise, so a demo can show it and a test can assert it.
CACHE_FIELD = "polyswarm_cache"
CACHE_HIT = "hit"
CACHE_LIVE = "live"

# Why no lookup was attempted, on the events where none was. Out of
# OUTPUT_FIELDS for the same reason CACHE_FIELD is: it is not derived from a
# response payload, and build_output_fields() is asserted against OUTPUT_FIELDS
# field for field. This one is only ever set on a path where there is no
# payload at all.
NOTE_FIELD = "polyswarm_note"

# Every field the command can emit in its default mode. OUTPUT_FIELDS plus the
# two fields that describe how the answer was reached rather than what it says.
#
# ATTRIBUTION_FIELDS BELOW ARE DELIBERATELY NOT IN HERE. They are emitted only
# when attribution=true, which is off by default per constraint C11, so folding
# them in would make the default-mode field set a promise the default mode does
# not keep: the enrich workflow action tables ALL_FIELDS, and four permanently
# empty attribution columns on an action that never fetches them is worse than
# no columns. EVERY_FIELD below is the union, for the callers that want it.
ALL_FIELDS = OUTPUT_FIELDS + (CACHE_FIELD, NOTE_FIELD)

# ---------------------------------------------------------------------------
# Threat attribution
# ---------------------------------------------------------------------------
#
# Design section 4.1 lists polyswarm_families among the enrichment output
# fields and 4.4 wants family and actor context in Splunk. This is that surface,
# read out of the platform's tag-link endpoint rather than out of the KG profile
# endpoint 4.4 was written against, which has returned 500 since roughly
# 2026-07-23 (design section 0, item 5) and is therefore not something to build
# a shipped field on.
#
# WHAT IS EMITTED, AND WHAT EACH FIELD MEANS
#
#   polyswarm_families  the malware families the platform associates with the
#                       artifact. Multivalue.
#   polyswarm_tags      the namespaced tags, verbatim, prefix and all.
#                       Multivalue. Namespaces observed in the SDK's own
#                       vocabulary include actor:, campaign:, sector: and ttp:.
#   polyswarm_actor     the values of the actor: tags with the prefix stripped.
#                       Multivalue. A convenience over polyswarm_tags and never
#                       a substitute for it: the tags field keeps every
#                       namespace, including ones this app has never seen, so a
#                       namespace the platform adds tomorrow still arrives.
#   polyswarm_emerging  the platform's emerging timestamp, as the ISO string it
#                       sent. Absent when null, which is the ordinary case.
#
# ALL FOUR ARE ABSENT RATHER THAN EMPTY WHEN THERE IS NOTHING TO SAY, AND NO
# NOTE IS WRITTEN. That is the opposite of the routing table's behaviour and the
# difference is not an oversight. A note exists to say "the app declined to
# ask", which is a limit of the app. An artifact with no family and no actor tag
# is a fact about the artifact: most artifacts in a customer's index have no
# attribution at all, so a note on every one of them would put a sentence about
# nothing on the majority of a result set and teach an analyst to ignore the
# note field on the rows where it means something.
ACTOR_TAG_PREFIX = "actor:"

FAMILIES_FIELD = "polyswarm_families"
TAGS_FIELD = "polyswarm_tags"
ACTOR_FIELD = "polyswarm_actor"
EMERGING_FIELD = "polyswarm_emerging"

ATTRIBUTION_FIELDS = (
    FAMILIES_FIELD,
    TAGS_FIELD,
    ACTOR_FIELD,
    EMERGING_FIELD,
)

# Every field any invocation of this command can emit, in either mode.
EVERY_FIELD = ALL_FIELDS + ATTRIBUTION_FIELDS

# The attribution option's default. FALSE, and this is design constraint C11
# rather than a taste in defaults.
#
# Attribution costs ONE MORE METERED REQUEST PER DISTINCT SHA256, on top of the
# verdict request. A customer who turns it on doubles the worst-case request
# count of every enrichment search they run, and defect class B8 in design 7.2
# is precisely "cost-incurring features defaulted on", found in our own
# connector work by a maintainer rather than by us. So the feature ships opt-in,
# the option has to be typed to spend anything, and the second cap below is
# what bounds it once it has been.
DEFAULT_ATTRIBUTION = False

# The truth values the option accepts, taken from splunklib's own Boolean
# validator rather than written out beside it.
#
# The validator is what splunkd applies to the option before the command sees
# it, and resolve_attribution() is what makes the same rule testable without
# splunkd. Two hand-written lists would be two vocabularies, and the one that
# is not exercised in a unit test is the one that drifts, so the resolver reads
# the validator's table. A test asserts the two agree value by value.
TRUE_VALUES = frozenset(
    name for name, truth in validators.Boolean.truth_values.items() if truth
)
FALSE_VALUES = frozenset(
    name for name, truth in validators.Boolean.truth_values.items() if not truth
)

# No module logger here. Everything this command writes goes through ps_log,
# so that the whitelist is the only route a value has into a log line.


class SearchOptionError(Exception):
    """Raised when the command's options are unusable.

    Separate from ClientConfigurationError because this is an operator error in
    the search string, not a configuration problem on the search head, and the
    two want different remedies in their messages.
    """


# ---------------------------------------------------------------------------
# Option handling
# ---------------------------------------------------------------------------


def resolve_limit(limit):
    """Validate and return the distinct-hash ceiling for one invocation.

    Enforced here as a plain function as well as declared require=True on the
    Option, so the refusal is testable without splunkd and so the message names
    the option rather than relying on the SDK's phrasing.

    :param limit: the raw option value, possibly None or a string.
    :returns: the limit as an int.
    :raises SearchOptionError: if absent, not an integer, or out of range.
    """
    if limit is None or (isinstance(limit, str) and not limit.strip()):
        raise SearchOptionError(
            "The limit option is required. polyswarmsearch spends one API "
            "request per distinct hash, so state a ceiling explicitly, for "
            "example: polyswarmsearch limit=500 (maximum {0}).".format(MAX_LIMIT)
        )

    try:
        resolved = int(limit)
    except (TypeError, ValueError):
        raise SearchOptionError(
            "The limit option must be an integer, for example limit=500."
        )

    if resolved < MIN_LIMIT:
        raise SearchOptionError(
            "The limit option must be at least {0}.".format(MIN_LIMIT)
        )

    if resolved > MAX_LIMIT:
        raise SearchOptionError(
            "The limit option cannot exceed {0}. polyswarmsearch spends one "
            "API request per distinct hash and this ceiling is a hard cap on "
            "how much of a quota one search can consume.".format(MAX_LIMIT)
        )

    return resolved


def resolve_field(field):
    """Return the input field name to read indicators from."""
    if field is None or not str(field).strip():
        return DEFAULT_HASH_FIELD
    return str(field).strip()


def resolve_attribution(attribution):
    """Validate and return whether this invocation fetches attribution.

    Enforced here as a plain function as well as declared with a Boolean
    validator on the Option, for the reason resolve_limit() and
    resolve_ioctype() both carry a pair of checks: the refusal is then testable
    without splunkd and the message is ours rather than the SDK's.

    DEFAULTS TO FALSE, AND THE DEFAULT IS THE CONSTRAINT. Attribution spends
    one more metered request per distinct sha256. Design constraint C11 and
    defect class B8 both say a cost-incurring feature ships opt-in, so an
    absent option and a blank option resolve to false. Erring towards not
    spending is the only safe direction here: the cost of a wrong false is an
    analyst re-running a search with the option typed, and the cost of a wrong
    true is a doubled bill nobody asked for.

    AN UNREADABLE VALUE IS REFUSED OUTRIGHT AND IS NOT SILENTLY THE DEFAULT.
    attribution=maybe raises rather than resolving to false, which looks like
    the less safe of the two answers and is the right one. A value the operator
    typed and this app could not read is an operator error in the search
    string, and defaulting it would mean a search that quietly did something
    other than what was typed. The refusal costs one corrected search; the
    silent default would cost a customer who typed attribution=yesplease and
    concluded the platform holds no families for anything in their index.

    The spellings accepted are splunklib's own truth values, so that
    attribution=t, attribution=1 and attribution=yes behave the way every other
    boolean option in Splunk does.

    :param attribution: the raw option value, possibly None, a bool or a string.
    :returns: True or False.
    :raises SearchOptionError: if the value is not a recognisable truth value.
    """
    if attribution is None:
        return DEFAULT_ATTRIBUTION
    if isinstance(attribution, bool):
        return attribution

    text = str(attribution).strip().lower()
    if not text:
        return DEFAULT_ATTRIBUTION

    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False

    raise SearchOptionError(
        "The attribution option must be a truth value, for example "
        "attribution=true. It defaults to {0} because it spends one extra "
        "PolySwarm request per distinct sha256, on top of the verdict "
        "request.".format("true" if DEFAULT_ATTRIBUTION else "false")
    )


def resolve_ioctype(ioctype):
    """Validate and return the routing mode for one invocation.

    Enforced here as a plain function as well as declared on the Option with a
    Set validator, for the reason resolve_limit() gives: the refusal is then
    testable without splunkd and the message is ours rather than the SDK's.

    Case is folded and whitespace stripped, because ioctype=URL out of a
    dashboard token or a workflow action is plainly the same request as
    ioctype=url and refusing it would be pedantry with a quota bill attached.

    :param ioctype: the raw option value, possibly None or a string.
    :returns: one of IOCTYPE_VALUES.
    :raises SearchOptionError: if the value is not one of them.
    """
    if ioctype is None or not str(ioctype).strip():
        return DEFAULT_IOCTYPE

    resolved = str(ioctype).strip().lower()
    if resolved not in IOCTYPE_VALUES:
        raise SearchOptionError(
            "The ioctype option must be one of {0}, for example ioctype=url. "
            "The default is {1}, which classifies each value and routes "
            "it.".format(", ".join(IOCTYPE_VALUES), DEFAULT_IOCTYPE)
        )
    return resolved


# ---------------------------------------------------------------------------
# Verdict banding
# ---------------------------------------------------------------------------


def classify(polyscore):
    """Map a polyscore to a verdict string.

    Bands are inclusive at their lower bound. A score that is absent or not a
    number is unknown rather than benign. See VERDICT_UNKNOWN.

    :param polyscore: the score, or None.
    :returns: one of the VERDICT_* constants.
    """
    if polyscore is None:
        return VERDICT_UNKNOWN
    try:
        score = float(polyscore)
    except (TypeError, ValueError):
        return VERDICT_UNKNOWN
    if score != score:
        # NaN. Compares false against every threshold, so it would otherwise
        # fall through to benign, which is the one answer it must not give.
        return VERDICT_UNKNOWN
    if score >= MALICIOUS_THRESHOLD:
        return VERDICT_MALICIOUS
    if score >= SUSPICIOUS_THRESHOLD:
        return VERDICT_SUSPICIOUS
    return VERDICT_BENIGN


def verdict_for(polyscore, detection_total):
    """Band a polyscore, requiring engine coverage before saying benign.

    classify() bands the score alone. This adds the one thing the score cannot
    tell you: whether any engine actually looked. The recorded response carries
    a detections object with a total, and an artifact can be on file with a low
    polyscore and a total of zero, which happens when it is known but nothing
    has asserted on it yet. Banding that to benign would report "we have seen
    this file and it is clean" on the strength of no engine opinions at all,
    which is the exact confusion VERDICT_UNKNOWN exists to prevent.

    The malicious and suspicious bands are not gated. A score at or above 0.4
    is already a positive statement, and withholding it because the detection
    counts were unreadable would lose the more urgent half of the answer.

    :param polyscore: the score, or None.
    :param detection_total: detections.total, or None when unreadable.
    :returns: one of the VERDICT_* constants.
    """
    banded = classify(polyscore)
    if banded != VERDICT_BENIGN:
        return banded

    try:
        total = int(detection_total)
    except (TypeError, ValueError):
        return VERDICT_UNKNOWN

    return VERDICT_BENIGN if total > 0 else VERDICT_UNKNOWN


# ---------------------------------------------------------------------------
# Response reading
# ---------------------------------------------------------------------------
#
# RESPONSE SHAPE
#
# The contract is two scrubbed recordings of live responses:
# tests/fixtures/search-hash-recorded.json from GET /v3/search/hash/sha256, and
# tests/fixtures/search-url-recorded.json from GET /v3/search/url. Those files,
# not this comment and not the v3 documentation, are what the readers below are
# written against, and tests/unit/test_commands.py asserts every emitted field
# against the numbers in both. A shape change is a fixture re-recording, not an
# edit here.
#
# ONE READER FOR BOTH ENDPOINTS, AND THAT IS A MEASURED FACT.
#
# The two recordings have the same envelope key set and the same artifact key
# set, down to the member. That is asserted in
# tests/fixtures/test_search_url_fixture_integrity.py against both files rather
# than assumed here, so the day the two shapes diverge is the day that test
# fails, instead of the day a customer's URL enrichment quietly reports
# unknown. Until then a second reader would be a second thing to keep in step
# with a shape that only has one definition. Decision D4.
#
# The one artifact field that differs in VALUE rather than in presence is
# "type", which is "FILE" in the hash recording and "URL" in the URL one.
# Nothing below reads it. It is not needed: the caller already knows what it
# asked about, and banding a verdict does not depend on the class of the thing
# banded.
#
# The recorded shape is:
#
#     {"has_more": bool, "limit": int, "status": str, "result": [artifact, ...]}
#
# and the artifact fields this command reads are:
#
#     polyscore       float, the score banded into a verdict
#     detections      {"benign": int, "malicious": int, "total": int}
#     permalink       str, the scan result in the web UI
#     window_closed   bool, whether the assertion window has closed
#
# Field names that earlier readings guessed at are deliberately not accepted:
# there is no polyswarm_score or score alias for the polyscore, no url or link
# alias for the permalink, and detections is only ever the counts object. The
# recording answered those questions, and accepting invented aliases would
# claim a contract the API does not offer.
#
# What remains tolerant is structural, and defensive rather than contractual: a
# payload that does not match yields an unknown verdict, never an exception. An
# enrichment command that raises on an unexpected response fails the whole
# search over one odd event, and the analyst loses the results that did work.

SCORE_KEY = "polyscore"
PERMALINK_KEY = "permalink"
DETECTIONS_KEY = "detections"
WINDOW_CLOSED_KEY = "window_closed"

# The artifact's own digest, present in both recordings. Read only to address
# the attribution request; see read_sha256().
SHA256_KEY = "sha256"

# ---------------------------------------------------------------------------
# THE ATTRIBUTION RESPONSE SHAPE, AND WHY IT IS WEAKER THAN THE ONE ABOVE
# ---------------------------------------------------------------------------
#
# PROVISIONAL-SDK. Every key name below is taken from the polyswarm-api SDK's
# TagLink resource, which builds itself out of the response body and therefore
# names what the platform sends. It is NOT taken from a recorded live 200, which
# is what decision D4 requires of the two search endpoints and what
# tests/fixtures/search-hash-recorded.json and search-url-recorded.json are.
#
# That difference is stated rather than glossed, because it is the whole caveat
# on this feature. An SDK reading is a strong source and a second-hand one: it
# tells us what a client parses, not what a server sent on a given day. A public
# scoped key answered 204 on 2026-09-08 even for family-list queries, so tag
# coverage appears to be entitlement gated and this repository has never held a
# populated response from this endpoint.
#
# The consequences are carried in the reader below rather than in a promise:
#
#   * every field is validated on the way out and OMITTED when unreadable,
#     never guessed and never emitted as an empty multivalue
#   * no field alias is accepted, on the same rule D9 applies to the account
#     endpoints, because accepting a name the platform never sends hides a real
#     shape change behind it
#   * an unrecognised payload yields no attribution fields, never an exception,
#     because an enrichment command that raises on one odd response loses the
#     analyst every result that did work
#
# The open item is docs/decisions.md D11: take a recording with an entitled key
# and pin this the way D4 pins the other two.
#
# The shape, per the SDK resource:
#
#     {"id": ..., "sha256": str, "created": iso, "updated": iso,
#      "first_seen": iso, "tags": [str], "families": [str],
#      "emerging": iso or null}
#
# The keys this app reads are families, tags and emerging. id, created, updated,
# first_seen and the response's own sha256 are deliberately not read: the caller
# already knows which artifact it asked about, and a field that is not read
# cannot be got wrong.
FAMILIES_KEY = "families"
TAGS_KEY = "tags"
EMERGING_KEY = "emerging"


def select_result(payload):
    """Return the one artifact to report on, or None.

    SELECTION RULE. "result" is a list and more than one entry is possible for
    a single hash, because the same artifact can have been scanned more than
    once. The entry chosen is the FIRST with window_closed true, and the first
    entry overall when none of them has it.

    Preferring a closed window is the point of the rule. While a window is open
    the assertions are still arriving, so the polyscore and the detection counts
    are a partial tally that will change; a closed window is a settled answer.
    Taking the first entry when nothing is settled keeps the command answering
    with the API's own ordering rather than silently reporting unknown for an
    artifact the platform does know about.

    A bare artifact object and a bare list are also accepted, so that a
    response missing its envelope degrades to a verdict instead of an error.
    """
    if payload is None:
        return None

    if isinstance(payload, dict):
        # TRAP: an artifact carries its own "result" key, a boolean, alongside
        # the envelope's "result" list. So the envelope is recognised by the
        # type of the value and not by the presence of the name. Descending on
        # the name alone would follow an artifact's result=false to nothing and
        # report unknown for a hash the platform answered on.
        inner = payload.get("result")
        if isinstance(inner, (list, dict)):
            payload = inner
        elif "result" in payload and inner is None:
            # An envelope carrying nothing. Not an artifact: an artifact's own
            # result key is a boolean.
            return None
        else:
            return payload

    if isinstance(payload, dict):
        return payload

    if not isinstance(payload, list):
        return None

    entries = [entry for entry in payload if isinstance(entry, dict)]
    if not entries:
        return None

    for entry in entries:
        if entry.get(WINDOW_CLOSED_KEY) is True:
            return entry

    return entries[0]


def read_score(result):
    """Return the polyscore as a float, or None when absent or unreadable."""
    if not isinstance(result, dict):
        return None
    value = result.get(SCORE_KEY)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_detection_total(result):
    """Return detections.total as an int, or None when not readable.

    Split out from read_detections because the verdict band needs the total on
    its own: a low score with no engine coverage is unknown, not benign. See
    verdict_for().
    """
    if not isinstance(result, dict):
        return None
    detections = result.get(DETECTIONS_KEY)
    if not isinstance(detections, dict):
        return None
    total = detections.get("total")
    if total is None or isinstance(total, bool):
        return None
    try:
        return int(total)
    except (TypeError, ValueError):
        return None


def read_detections(result):
    """Return a "malicious/total" string, or None when not determinable.

    Both counts come from the detections object and nothing is inferred. The
    total is authoritative: it is the engine coverage the platform reports, and
    it is not necessarily malicious plus benign, because an engine can fail or
    abstain and still count as coverage. The recorded fixture carries two
    trimmed assertions alongside a total of 9 for exactly that reason, so
    counting assertions or summing the other keys would both be wrong.
    """
    if not isinstance(result, dict):
        return None

    detections = result.get(DETECTIONS_KEY)
    if not isinstance(detections, dict):
        return None

    malicious = detections.get("malicious")
    if malicious is None or isinstance(malicious, bool):
        return None

    total = read_detection_total(result)
    if total is None:
        return None

    try:
        return "{0}/{1}".format(int(malicious), total)
    except (TypeError, ValueError):
        return None


def read_permalink(result):
    """Return the result permalink, or None."""
    if not isinstance(result, dict):
        return None
    value = result.get(PERMALINK_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def read_sha256(result):
    """Return the artifact's own sha256, or None when unreadable.

    WHY THIS IS HERE AND NOT AT THE CALL SITE. The attribution endpoint takes a
    sha256, and the value the analyst's event carried may not be one: a url or
    a domain field routes to URL search, and the artifact that comes back
    carries the digest of the content it served. Reading it is what lets
    attribution work from a proxy log and not only from a hash field.

    That makes it a read of the artifact shape, so it lives beside the other
    readers rather than in the enrichment pass, which is decision D4's
    single-reader rule applied to a second question about the same object.
    build_output_fields() does not call it, because a digest is not an output
    field: it is the input to the next request, and
    test_the_recorded_response_emits_exactly_the_four_output_fields asserts
    that field set stays exactly four.

    A blank, a non-string and a bool are all None. A bool matters because the
    artifact carries its own boolean "result" key next to this one, so a reader
    that coerced would be one typo away from asking the platform about "True".
    """
    if not isinstance(result, dict):
        return None
    value = result.get(SHA256_KEY)
    if isinstance(value, bool) or not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def build_output_fields(payload):
    """Return the output fields for one API response payload.

    A payload of None means the platform reported not-found, which is the
    normal answer for a hash it has never seen, so it produces an unknown
    verdict and no other fields rather than an error. See
    ps_client.NOT_FOUND_STATUS_CODES: both 204 and 404 arrive here as None.
    """
    result = select_result(payload)
    score = read_score(result)
    total = read_detection_total(result)

    fields = {VERDICT_FIELD: verdict_for(score, total)}

    if score is not None:
        fields[POLYSCORE_FIELD] = score

    detections = read_detections(result)
    if detections is not None:
        fields[DETECTIONS_FIELD] = detections

    permalink = read_permalink(result)
    if permalink is not None:
        fields[PERMALINK_FIELD] = permalink

    return fields


def read_string_list(payload, key):
    """Return the non-blank strings under one key, in order, or None.

    None rather than an empty list when there is nothing to report, because the
    caller omits an absent field and an empty multivalue field in Splunk is a
    field that is present and says nothing. Those read differently to an
    analyst and only one of them is true here.

    Nothing is deduplicated and nothing is reordered. The platform's list is
    what the analyst gets: two spellings of one family are the platform's
    statement about the artifact, and quietly collapsing them would be this app
    editing an answer it does not own.

    A bool is refused before the isinstance(str) check would have refused it
    anyway, so the rule reads the same way it does in read_sha256() and in the
    account readers of decision D9: a boolean is never a name.
    """
    if not isinstance(payload, dict):
        return None
    values = payload.get(key)
    if not isinstance(values, (list, tuple)):
        return None

    found = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, str):
            continue
        text = value.strip()
        if text:
            found.append(text)

    return found or None


def read_actors(tags):
    """Return the actor: tag values with the prefix stripped, or None.

    Derived from the tag list this app already read rather than from a second
    read of the payload, so there is one place the tags come from.

    The prefix match is case sensitive and exact. A tolerant match would have
    to decide what "Actor:" and "actor :" mean, and inventing a second spelling
    for a namespace is the same class of guess as inventing a field alias. A
    tag that is nothing but the prefix contributes no actor, because an empty
    actor name is not an actor.
    """
    if not tags:
        return None

    found = []
    for tag in tags:
        if not tag.startswith(ACTOR_TAG_PREFIX):
            continue
        name = tag[len(ACTOR_TAG_PREFIX):].strip()
        if name:
            found.append(name)

    return found or None


def read_emerging(payload):
    """Return the emerging timestamp as the string the platform sent, or None.

    Passed through verbatim rather than parsed and reformatted. The SDK parses
    it into a datetime; this app has no use for one, and a reformat would mean
    choosing an output format and a timezone on the customer's behalf for a
    value they can already read. A null emerging is the ordinary case and
    produces no field.
    """
    if not isinstance(payload, dict):
        return None
    value = payload.get(EMERGING_KEY)
    if isinstance(value, bool) or not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def build_attribution_fields(payload):
    """Return the attribution fields for one tag-link response payload.

    THE SINGLE READER OF THE TAG-LINK SHAPE, in the sense
    build_output_fields() is the single reader of a search response. Kept
    separate from it rather than merged, because they read two different
    responses from two different endpoints: merging them would produce one
    function whose behaviour depended on which of two payloads it was handed.

    A payload of None means the platform holds no tag link for the artifact,
    which is HTTP 204 with an empty body and is the common answer on this
    endpoint. It produces NO FIELDS AT ALL and no note. See the block comment
    at ACTOR_TAG_PREFIX for why absence is silent here while an unrouted value
    gets a sentence.

    :param payload: the decoded tag-link response, or None.
    :returns: a dict of zero to four fields. Never raises.
    """
    if not isinstance(payload, dict):
        return {}

    fields = {}

    families = read_string_list(payload, FAMILIES_KEY)
    if families is not None:
        fields[FAMILIES_FIELD] = families

    tags = read_string_list(payload, TAGS_KEY)
    if tags is not None:
        fields[TAGS_FIELD] = tags

    actors = read_actors(tags)
    if actors is not None:
        fields[ACTOR_FIELD] = actors

    emerging = read_emerging(payload)
    if emerging is not None:
        fields[EMERGING_FIELD] = emerging

    return fields


def unknown_fields(note=None):
    """The output for a value that was not looked up or was not found.

    :param note: why no lookup was attempted, when that is the reason. Omitted
        for a value that WAS looked up and came back not-found, because there
        is nothing to explain there: the platform answered.
    """
    fields = {VERDICT_FIELD: VERDICT_UNKNOWN}
    if note is not None:
        fields[NOTE_FIELD] = note
    return fields


def route_for(value, ioctype=DEFAULT_IOCTYPE):
    """Choose the endpoint for one value. Pure, no I/O.

    Split out as a plain function so the whole routing table is testable
    without a client, a cache, or splunkd, which is what makes the
    classification table in tests/unit/test_commands.py a table rather than a
    dozen end-to-end runs.

    :param value: the field value, already stripped and known non-empty.
    :param ioctype: one of IOCTYPE_VALUES.
    :returns: an (endpoint, fold_case, note) triple. endpoint is ROUTE_HASH,
        ROUTE_URL, or ROUTE_NONE; when it is ROUTE_NONE the note says why and
        is never None. fold_case says whether the caches may lowercase the
        value before keying on it.
    """
    if ioctype == IOCTYPE_HASH:
        # FORCED, AND NOT CLASSIFIED. The operator stated the type, so this
        # app's own regular expressions do not get to overrule them. Case is
        # folded unconditionally because the only thing this mode sends is a
        # hash, and folding hexadecimal is always safe.
        return ROUTE_HASH, True, None

    if ioctype == IOCTYPE_URL:
        # FORCED, BUT THE FOLD RULE IS STILL CLASSIFIED, because the fold rule
        # is the one thing the operator did not state. A value that reads as a
        # bare host folds; anything else is keyed byte for byte. Getting that
        # wrong in this direction can only split one cache entry into two,
        # which costs a lookup. Getting it wrong the other way would merge two
        # URLs into one answer.
        return ROUTE_URL, classify_ioc(value) == "domain", None

    ioc_type = classify_ioc(value)
    if ioc_type is None:
        return ROUTE_NONE, True, NOTE_UNCLASSIFIED

    endpoint = AUTO_ROUTES.get(ioc_type, ROUTE_NONE)
    if endpoint is ROUTE_NONE:
        # AUTO_NOTES covers every unrouted type in AUTO_ROUTES, and a test
        # enumerates the table to prove it, so the fallback here is unreachable
        # rather than load bearing. It exists because an unreachable branch that
        # returns a true statement is better than one that returns None into a
        # field an analyst reads.
        return ROUTE_NONE, True, AUTO_NOTES.get(ioc_type, NOTE_UNCLASSIFIED)

    return endpoint, ioc_type in FOLD_CASE_TYPES, None


# ---------------------------------------------------------------------------
# Failures that stop the search rather than one value
# ---------------------------------------------------------------------------


def stop_reason_for(error):
    """Return the stop reason one exception calls for, or None.

    Pure, so the whole circuit breaker rule is testable without a client. None
    means the failure belongs to one value: it is counted, reported once, and
    the search carries on. See the note at STOP_AUTH.

    TWO CLASSES, BOTH FROM ps_client, AND NO MESSAGE MATCHING. A rejected key
    is AuthenticationError, raised on a 401 or a 403 and never retried. A rate
    limit that outlived every attempt is RateLimitError, raised only when the
    last attempt was still a 429; a 503 storm or a network failure that
    exhausted the same retries stays a plain ClientError and is a per-value
    failure, which is the distinction the class exists to carry.

    Both are ClientError subclasses, so both are tested before the class they
    derive from is reached anywhere: order matters here in the same way it
    matters in an except chain.
    """
    if isinstance(error, AuthenticationError):
        return STOP_AUTH
    if isinstance(error, RateLimitError):
        return STOP_RATE_LIMIT
    return None


def client_secrets(client):
    """The secret values this command's own output fields are scrubbed of.

    The app's API key, when the client carries one. Read off the client rather
    than out of credential storage a second time, so there is one place the key
    is fetched and one value the sanitizer is given.

    Returns an empty tuple for a client with no configuration, which is what
    every fake client in the tests is and what the enricher runs with outside
    splunkd. An empty tuple is a supported input to sanitize().
    """
    config = getattr(client, "config", None)
    if config is None:
        return ()
    value = getattr(config, "api_key", None)
    if not isinstance(value, str) or not value:
        return ()
    return (value,)


# ---------------------------------------------------------------------------
# Multivalue input
# ---------------------------------------------------------------------------
#
# A SPLUNK FIELD CAN HOLD MORE THAN ONE VALUE, AND THE SDK DELIVERS THAT AS A
# LIST. It is the ordinary shape after `| stats values(file_hash) as file_hash`
# and after `| polyswarmextract`, whose polyswarm_ioc field is multivalue by
# construction. str() on a list produces "['a', 'b']", which classifies as
# nothing in auto mode and, with ioctype=hash forced, would be sent to the
# platform verbatim as a metered request that cannot match anything.
#
# So each member is enriched on its own and the output fields are emitted as
# LISTS ALIGNED INDEX FOR INDEX with the input members, which is the same
# contract polyswarmextract's three fields already keep: position n of every
# polyswarm_ field describes member n of the input field. That is what makes
# mvzip and mvexpand work over the result.
#
# A MEMBER WITH NOTHING TO SAY FOR A FIELD GETS AN EMPTY STRING AND NOT A
# MISSING ENTRY. The fields are not the same set for every member: a sha256
# answers with a polyscore and an md5 answers with a note, and a column that
# skipped the members it had no value for would be shorter than the others and
# would silently misalign every entry after the gap. An empty string is a
# readable "nothing here for this one" and keeps the columns the same length.
MULTIVALUE_ABSENT = ""

# The separator for an output field that is ITSELF multivalue, which is the
# attribution fields and only those. A Splunk result row has one dimension of
# multivalue, so a list of lists cannot be represented in it: the writer would
# JSON encode the inner list and the alignment would be unreadable. With a
# multivalue input field the inner list is therefore rendered as one string per
# member, which keeps the outer alignment, which is the contract an analyst
# depends on. Attribution is off by default, so this is the rare case of a rare
# case, and it is documented in docs/using.md section 2 rather than left to be
# discovered.
MULTIVALUE_INNER_SEPARATOR = ", "


def flatten_multivalue(value):
    """Render one member's value for an aligned multivalue column."""
    if isinstance(value, (list, tuple)):
        return MULTIVALUE_INNER_SEPARATOR.join(str(item) for item in value)
    return value


def align_fields(per_member):
    """Merge one field dict per input member into aligned multivalue fields.

    :param per_member: the output fields for each member of the input field, in
        input order.
    :returns: a dict of field name to a list with one entry per member.

    Field order follows first appearance across the members rather than a sort,
    so a result set reads the way a single-valued one does. Every list returned
    has exactly one entry per member; see MULTIVALUE_ABSENT.
    """
    names = []
    for fields in per_member:
        for name in fields:
            if name not in names:
                names.append(name)

    merged = {}
    for name in names:
        merged[name] = [
            flatten_multivalue(fields.get(name, MULTIVALUE_ABSENT))
            for fields in per_member
        ]
    return merged


# ---------------------------------------------------------------------------
# The enrichment pass
# ---------------------------------------------------------------------------


class IocEnricher(object):
    """Looks indicators up through a client, deduplicating within one search.

    Split out from the command class so the whole enrichment pass is testable
    with a fake client and no splunkd. The command class is left holding the
    protocol and the options and nothing else.

    Routing lives here rather than in the command class for the same reason:
    choosing an endpoint for a value is the part worth testing exhaustively,
    and route_for() above is a pure function so that it can be.
    """

    def __init__(
        self,
        client,
        limit,
        field=DEFAULT_HASH_FIELD,
        cache=None,
        ioctype=DEFAULT_IOCTYPE,
        attribution=DEFAULT_ATTRIBUTION,
    ):
        """
        :param client: anything with search_hash(value) and search_url(value)
            methods, plus tag_link(sha256) when attribution is on. Only the one
            a value routes to is ever called, so a fake carrying just
            search_hash still drives every hash path, and a fake with no
            tag_link at all still drives every default-mode path.
        :param limit: the distinct-indicator ceiling for this search. Also the
            separate ceiling on attribution requests; see the note on
            attribution_limit below.
        :param field: the input field to read indicators from.
        :param cache: a verdict_cache.VerdictCache, or None to run with no
            persistent cache at all. None is a supported mode, not a
            degradation: it is what the enricher does outside splunkd.
        :param ioctype: one of IOCTYPE_VALUES. See route_for().
        :param attribution: whether to spend one extra request per distinct
            sha256 on the tag-link endpoint. False by default, per C11.
        """
        self.client = client
        self.limit = limit
        self.field = field
        self.cache = cache
        self.ioctype = ioctype
        self.attribution = bool(attribution)

        # THE ONLY VALUES THIS COMMAND'S OWN FIELDS ARE SCRUBBED OF, and they
        # are read once here rather than per record. See enrich() for why the
        # customer's fields are not scrubbed at all.
        self.secrets = client_secrets(client)

        # THE SECOND CAP, AND WHY IT IS A SECOND CAP RATHER THAN A SHARED ONE.
        #
        # Constraint C11 requires every metered path to declare a hard ceiling.
        # Attribution is a second metered path over the same events, so it
        # needs a ceiling of its own, and the question is whether it should
        # share the verdict budget or hold one beside it.
        #
        # It holds one beside it, equal to the same number, and the worst case
        # of an attribution=true invocation is therefore 2 x limit requests.
        # That is stated in the option's own documentation, on the finish log
        # line and in docs/decisions.md D11, so a customer reading limit=500
        # with attribution on is told the ceiling is a thousand requests rather
        # than left to work it out.
        #
        # Sharing one budget was considered and rejected. It reads tighter and
        # behaves worse: with attribution on, half the analyst's distinct
        # indicators would get no verdict at all, because the attribution
        # requests would eat the ceiling the verdicts needed. Turning on a
        # context feature must not silently stop answering the primary
        # question, and an analyst who sees half a result set come back unknown
        # has been given a wrong impression of the platform rather than a
        # smaller bill.
        #
        # A SEPARATE CAP IS NOT OPTIONAL HERE, and this is the case that proves
        # it. Attribution keys on the ARTIFACT'S sha256 and is owed on a verdict
        # cache HIT as well as on a live lookup, because a cached verdict may
        # have been stored by an attribution=false search. So a search over ten
        # thousand fully-cached hashes spends zero verdict requests and would
        # spend ten thousand attribution requests with nothing bounding them.
        # self.lookups cannot bound that: it is zero on exactly that search.
        self.attribution_limit = limit

        # ioc value or cache key -> output fields. One entry per distinct
        # indicator resolved this search, whether it was resolved from the KV
        # cache, from a request, or by the routing table declining to make one.
        self._cache = {}

        # ARTIFACT SHA256 -> attribution fields, and it is keyed differently
        # from the dedup map above on purpose.
        #
        # Two distinct indicators can resolve to one artifact: a URL and the
        # sha256 of what it served are two rows in a proxy-log-plus-endpoint
        # search and one artifact on the platform. The verdict dedup keys on
        # the value that was queried, because that is what the verdict endpoints
        # take. Attribution keys on the digest that came back, because that is
        # what the tag-link endpoint takes. Keying attribution on the queried
        # value would spend two requests for one artifact and is exactly the
        # "one metered call per unique sha256" promise this map keeps.
        #
        # Lowercased, because a digest is hexadecimal and two spellings of one
        # digest are one artifact.
        self._attribution_cache = {}

        # Counted so a test can assert the dedup guarantee directly, and so an
        # operator can be told why enrichment stopped. lookups counts requests
        # actually spent, so a KV cache hit does not increment it.
        self.lookups = 0
        self.limit_reached = False

        # The same pair for the attribution path, counted separately because
        # they are a separate budget and a separate refusal. attribution_lookups
        # is tag-link requests actually spent, so neither a per-search dedup hit
        # nor a stored attribution increments it.
        self.attribution_lookups = 0
        self.attribution_limit_reached = False

        # Distinct values no endpoint answers for. Reported on the finish line
        # so that "every row came back unknown" has a readable cause in the
        # log as well as in the events. Not a failure count: nothing went
        # wrong on this path, the app declined to guess.
        self.unrouted = 0

        # Cost accounting for the search, reported to the operator at the end.
        self.cache_hits = 0
        self.live_lookups = 0

        # Per-hash lookup failures. Counted rather than logged one by one, and
        # the first sanitized message is kept so the analyst gets told what
        # went wrong once instead of never. See _lookup().
        self.failures = 0
        self.first_failure = None

        # The same pair for the attribution path, counted apart from the
        # verdict failures because they are not the same failure to an analyst.
        # A verdict that could not be looked up is a missing answer; an
        # attribution that could not be looked up is missing context beside an
        # answer that arrived. Reporting them together would put an alarming
        # sentence in front of a customer whose enrichment worked perfectly.
        self.attribution_failures = 0
        self.first_attribution_failure = None

        # THE SEARCH LEVEL CIRCUIT BREAKER. None while enrichment is running,
        # and one of the STOP_ constants once a failure that applies to every
        # remaining value has been seen. See the note at STOP_AUTH.
        #
        # stop_detail is the first sanitized message, reported once to the
        # analyst. stop_class is the exception class name, which is the only
        # part of a failure ps_log has a key for.
        self.stopped_reason = None
        self.stop_detail = None
        self.stop_class = None

    def stop(self, reason, error):
        """Stop enriching for the rest of this search, and say why once.

        Called on the first failure that will affect every remaining value
        identically. The row that triggered it gets the same note every later
        row gets, and is marked as a live lookup because the request was made
        and may well have been billed.

        A second stop does not overwrite the first: the first cause is the one
        worth reporting, and a rate limit arriving after a rejected key is a
        consequence rather than a new fact.
        """
        if self.stopped_reason is None:
            self.stopped_reason = reason
            # ps_client sanitizes its own messages against its own key, and
            # this is the second pass, on the way to a sentence a customer
            # reads. The cost of the pass is nothing and the cost of skipping
            # it is a credential in a search job's message list.
            self.stop_detail = sanitize_message(str(error), secrets=self.secrets)
            self.stop_class = type(error).__name__
            # ONE WARNING LINE, not one per value, which is the whole point of
            # stopping. The per-value failure path logs at DEBUG for the
            # opposite reason: it can run ten thousand times and this cannot
            # run twice.
            ps_log.warning(
                LOG_COMPONENT,
                "enrichment_stopped",
                "error",
                reason=self.stop_class,
                lookups=self.lookups,
            )

        stopped = unknown_fields(STOP_NOTES[self.stopped_reason])
        stopped[CACHE_FIELD] = CACHE_LIVE
        return stopped

    def report_stop(self):
        """Return one sanitized sentence about a stopped search, or None."""
        if self.stopped_reason is None:
            return None
        return STOP_REPORTS[self.stopped_reason].format(
            self.lookups, self.stop_detail
        )

    def report_attribution_failures(self):
        """Return one sanitized sentence about tag-link failures, or None.

        Separate from report_failures() and worded so that it cannot be read as
        the enrichment having failed, because it has not: the verdicts in the
        result set are correct and complete, and what is missing is the family
        and actor context beside them.
        """
        if not self.attribution_failures:
            return None
        return (
            "PolySwarm enrichment could not fetch attribution for {0} of the "
            "artifacts in this search, so family and actor fields are absent "
            "on those events. The verdicts are unaffected. First failure: "
            "{1}".format(
                self.attribution_failures, self.first_attribution_failure
            )
        )

    def report_failures(self):
        """Return one sanitized sentence about per-hash failures, or None.

        Per-value failures do not fail the search, by design: one odd indicator
        must not cost an analyst every result that did work. The consequence is
        that without this they are invisible in the search bar, and a result set
        full of unknown verdicts looks like a quiet platform rather than a
        broken one. So the count and the first message are reported once.
        """
        if not self.failures:
            return None
        return (
            "PolySwarm enrichment could not look up {0} of the indicators in "
            "this search and reported them as unknown. First failure: "
            "{1}".format(self.failures, self.first_failure)
        )

    def enrich(self, record):
        """Return a copy of one record with the output fields merged in.

        ONLY THIS APP'S OWN FIELDS GO THROUGH THE SANITIZER. THE CUSTOMER'S
        RECORD IS PASSED THROUGH BYTE FOR BYTE, AND THAT IS A FIX RATHER THAN
        A RELAXATION.
        --------------------------------------------------------------------
        The sanitizer applies an unanchored field-NAME rule, so any key whose
        name merely CONTAINS api_key, authorization, password or token has its
        value replaced with [REDACTED], with no secret involved and no way for
        the customer to tell it happened. Running the whole record through it
        therefore corrupted ordinary customer data on every event that passed
        through this command: password_age_days, tokens_issued and
        Authorization_Type are all real field names, and all three came out
        redacted. An enrichment command that silently edits the events it was
        asked to annotate is worse than one that does not run.
        --------------------------------------------------------------------
        The credential protection the sanitizer is there for is unchanged,
        because the API key can only ever reach a field this app built: the
        fields_for() dict is where a client error message or a payload value
        would arrive, and that dict is sanitized with the client's own key as
        the secret. A field the app did not write cannot contain a secret the
        app never gave it.

        The sanitizer's own field-name rule still runs over the app's fields,
        and no polyswarm_ field name matches it. A test asserts that, so a
        future output field called polyswarm_token cannot quietly start
        emitting [REDACTED].
        """
        output = dict(record)
        value = record.get(self.field)
        output.update(sanitize(self.fields_for(value), secrets=self.secrets))
        return output

    def fields_for(self, value):
        """Return the output fields for one field value.

        A LIST IS A MULTIVALUE FIELD AND EACH MEMBER IS ENRICHED. The output
        fields then come back as lists aligned index for index with the input
        members. See the block comment at MULTIVALUE_ABSENT for why an
        alignment placeholder is used rather than a shorter column, and
        fields_for_one() for the single-value path every member takes.

        A list of one member returns scalar fields, because a single-member
        multivalue field is a single value to everything downstream and a
        one-entry list would make the result set's shape depend on how the
        input happened to be built. An empty list is treated as a blank value.
        """
        if isinstance(value, (list, tuple)):
            if not value:
                return unknown_fields()
            if len(value) == 1:
                return self.fields_for_one(value[0])
            return align_fields(
                [self.fields_for_one(member) for member in value]
            )
        return self.fields_for_one(value)

    def fields_for_one(self, value):
        """Return the output fields for one single-valued field value.

        Resolution order, and the order is the design:

          0. the routing table, which decides whether there is anything to ask
          1. the per-search dedup cache, which costs nothing
          2. the KV store verdict cache, which also costs nothing
          3. the limit
          4. a request

        ROUTING COMES FIRST, BEFORE EVERY CACHE AND BEFORE THE LIMIT. A value
        no endpoint answers for is not a lookup that failed and not a lookup
        that was skipped, it is a lookup that does not exist, so it must not
        consume a limit slot, must not reach a client, and must not be recorded
        as a cache miss. An md5-heavy search would otherwise burn its whole
        ceiling on values that were never going to be asked about, and the
        sha256 rows behind them would come back unknown for the wrong reason.

        A value that would exceed the limit gets an unknown verdict and is not
        remembered, so that it is not mistaken for a looked-up miss.
        """
        if value is None:
            return unknown_fields()

        text = str(value).strip()
        if not text:
            return unknown_fields()

        endpoint, fold_case, note = route_for(text, self.ioctype)

        if endpoint is ROUTE_NONE:
            # Remembered like any other resolution: it is deterministic for a
            # given value and mode, so re-deriving it per event would be work
            # for nothing. Counted once per DISTINCT value for the same reason
            # the lookup counters are.
            key = text.lower() if fold_case else text
            if key in self._cache:
                return dict(self._cache[key])
            self.unrouted += 1
            fields = unknown_fields(note)
            self._cache[key] = fields
            return dict(fields)

        # Case is folded only where two spellings are one indicator. See
        # FOLD_CASE_TYPES: it is right for a hash, whose case different log
        # sources disagree about for the same file, and wrong for a URL.
        key = text.lower() if fold_case else text

        if key in self._cache:
            return dict(self._cache[key])

        # THE KV CACHE IS CONSULTED BEFORE THE LIMIT, DELIBERATELY.
        #
        # The limit is a quota ceiling and nothing else: it exists so that one
        # mistyped search cannot drain a customer's month of API calls. A cache
        # hit spends no quota, so counting it against the ceiling would charge
        # the customer's budget for a request that was never made.
        #
        # It also matters for section 4.8. The triage dashboard renders from
        # this cache over whatever search the analyst drills into, and if hits
        # counted against the limit then a dashboard over a large result set
        # would stop enriching partway through and report unknown for the tail,
        # despite having every one of those answers already on hand.
        cached = self._from_cache(text, fold_case)
        if cached is not None:
            self._cache[key] = cached
            return dict(cached)

        # THE CIRCUIT BREAKER, CHECKED AFTER BOTH CACHES AND BEFORE THE LIMIT.
        #
        # After the caches, because a cached answer costs nothing and is still
        # correct: a rejected key does not make yesterday's verdict wrong, and
        # withholding answers already on hand would turn a credential problem
        # into a worse result set than it has to be.
        #
        # Before the limit and before the request, because that is the whole
        # point: nothing after the stop reaches the client. Not remembered in
        # the dedup map either, so a value refused here is not mistaken for a
        # value the platform answered nothing for.
        if self.stopped_reason is not None:
            return unknown_fields(STOP_NOTES[self.stopped_reason])

        if self.lookups >= self.limit:
            self.limit_reached = True
            return unknown_fields()

        self.lookups += 1
        fields = self._lookup(text, endpoint, fold_case)
        self._cache[key] = fields
        return dict(fields)

    def _from_cache(self, ioc_value, fold_case=True):
        """Return output fields from the KV cache, or None for a miss.

        The cache never raises, so there is no error branch here. A missing
        collection, an unreadable one, and a stale document all arrive as None
        and read as a miss. See the note at the top of verdict_cache.
        """
        if self.cache is None:
            return None

        entry = self.cache.get_entry(ioc_value, fold_case=fold_case)
        if entry is None:
            return None

        self.cache_hits += 1

        # Banded from the stored response, not from stored fields. The cache
        # holds the platform's answer and this app's reading of it is applied
        # fresh, so a release that changes a threshold takes effect at once
        # instead of a day later. See verdict_cache's "what is cached" note.
        fields = build_output_fields(entry.payload)
        fields[CACHE_FIELD] = CACHE_HIT

        if self.attribution:
            fields.update(self._attribution_from_entry(ioc_value, entry, fold_case))

        return fields

    def _attribution_from_entry(self, ioc_value, entry, fold_case):
        """Attribution fields for a verdict that came out of the KV cache.

        TWO CASES, AND THE SECOND ONE IS WHY THIS METHOD EXISTS.
        -------------------------------------------------------
        1. The stored document already carries an attribution, because the
           search that stored it had the option on. Nothing is spent and the
           stored answer is read fresh, exactly as the verdict beside it is.
        2. The stored document carries no attribution, because the search that
           stored it did not ask for one. The verdict is free and the
           attribution is still owed, so a request is made, capped by the
           attribution ceiling, and written back into the same document.

        Case 2 is not an optimisation, it is the difference between the feature
        working and not working. Without it, the first attribution=true search
        an analyst runs over data they have already enriched returns no
        attribution at all, because every verdict is a cache hit, and the
        analyst concludes the platform has no families for any of their
        artifacts. That is a wrong answer produced by a cache, which decision
        D6 forbids on the same grounds it forbids folding a URL's case.

        THE WRITE-BACK PRESERVES THE DOCUMENT'S AGE. entry.stored_at and
        entry.ttl_seconds go back in, so attaching an attribution does not
        reset the verdict's lifetime. Otherwise a fleet enriched with
        attribution on every hour would hold verdicts that never expired, and
        the 24 hour freshness rule would quietly stop applying to the busiest
        indicators. verdict_cache.put() carries the same note at its stored_at
        parameter.
        """
        if entry.attribution_fetched:
            return build_attribution_fields(entry.attribution)

        digest = read_sha256(select_result(entry.payload))
        if digest is None:
            # Not an artifact response, so there is no sha256 to ask about.
            # A cached not-found is the ordinary case here.
            return {}

        fetched, payload = self._attribution_lookup(digest)
        if not fetched:
            return {}

        # Written back on the document's own clock. A store failure is a no-op
        # like every other cache write, so the only cost is asking again next
        # search.
        if self.cache is not None:
            self.cache.put(
                ioc_value,
                entry.payload,
                ttl_seconds=entry.ttl_seconds,
                fold_case=fold_case,
                attribution=payload,
                attribution_fetched=True,
                stored_at=entry.stored_at,
            )

        return build_attribution_fields(payload)

    def _attribution_lookup(self, digest):
        """One tag-link call for one artifact digest, deduplicated and capped.

        :param digest: the artifact's sha256, already known non-empty.
        :returns: a (fetched, payload) pair. fetched is False when no request
            was made and no stored answer was available, which happens when the
            cap was reached or the call failed; the caller then emits no
            attribution fields, because it has nothing to say rather than
            something to deny.

        ONE REQUEST PER DISTINCT SHA256 PER SEARCH, whatever it cost. The dedup
        map holds the answer for a digest that has been asked about, including
        the None a 204 produces, so a fleet carrying one binary asks once. A
        digest refused by the cap is deliberately NOT remembered, for the same
        reason a value refused by the verdict limit is not: remembering it would
        make it indistinguishable from an artifact the platform answered
        nothing for.

        A FAILURE HERE NEVER FAILS THE SEARCH AND NEVER FAILS THE VERDICT. The
        verdict is the answer the analyst asked for and attribution is context
        beside it, so a tag-link endpoint having a bad afternoon costs the
        context and not the enrichment. Configuration and authentication
        failures still propagate, on the same reasoning _lookup() gives: they
        will affect every remaining value identically.
        """
        key = digest.lower()
        if key in self._attribution_cache:
            return True, self._attribution_cache[key]

        # The verdict path's circuit breaker binds here too. Attribution is a
        # second metered path over the same account, so a rejected key or an
        # exhausted rate limit is exactly as final for it, and a search over
        # already-cached verdicts reaches this method without going through
        # _lookup() at all. Without this check that search would keep asking.
        if self.stopped_reason is not None:
            return False, None

        if self.attribution_lookups >= self.attribution_limit:
            self.attribution_limit_reached = True
            return False, None

        self.attribution_lookups += 1
        try:
            payload = self.client.tag_link(digest)
        except ClientConfigurationError:
            raise
        except NotImplementedError:
            raise
        except Exception as error:
            # The same two failures stop the search from here as from
            # _lookup(), for the same reason. No attribution fields are
            # emitted for this artifact, which is what this method's
            # (fetched, payload) pair already says.
            stop = stop_reason_for(error)
            if stop is not None:
                self.stop(stop, error)
                return False, None

            # Counted and logged the way a verdict failure is, and reported to
            # the analyst through the same one sentence, so a systemic tag-link
            # failure is visible without ten thousand log lines.
            self.attribution_failures += 1
            if self.first_attribution_failure is None:
                self.first_attribution_failure = sanitize_message(str(error))
            ps_log.debug(
                LOG_COMPONENT,
                "attribution",
                "error",
                reason=type(error).__name__,
            )
            return False, None

        self._attribution_cache[key] = payload
        return True, payload

    def _store(
        self,
        ioc_value,
        payload,
        fold_case=True,
        attribution=None,
        attribution_fetched=False,
    ):
        """Write one live answer through to the KV cache.

        A not-found is written through as well, with the shorter lifetime the
        cache applies to it. The reasoning is in verdict_cache.put(): most
        values in a search over an index are ones the platform has never seen,
        so a not-found that is not cached re-bills on every later search over
        the same data and the cache would save quota only on the malicious
        minority. On the URL endpoint a not-found is a recorded 204 with an
        empty body, so this is the ordinary path there rather than an edge.

        Nothing is written for a failed lookup. A failure is not an answer, and
        caching it would hold a transient network fault for hours.

        fold_case is passed through because a reader and a writer of one value
        that disagree about it key different documents, so the write would land
        somewhere nothing reads.

        ONE WRITE CARRIES BOTH ANSWERS. The two attribution arguments go
        straight through to verdict_cache.put(), so a live lookup with
        attribution on stores the verdict and the attribution in one document
        in one round trip. Two writes would have been two chances for the
        second one to fail and leave a document claiming attribution had been
        asked for when it had not.

        attribution_fetched defaults to false, so a caller that says nothing
        about attribution writes no attribution field, which is what an
        attribution=false search does and what every caller written before this
        option existed did.
        """
        if self.cache is None:
            return
        self.cache.put(
            ioc_value,
            payload,
            fold_case=fold_case,
            attribution=attribution,
            attribution_fetched=attribution_fetched,
        )

    def _lookup(self, ioc_value, endpoint, fold_case=True):
        """One API call. Never raises for a per-value failure.

        A lookup that fails for one value produces an unknown verdict and a log
        line, and the search carries on. The alternative, raising, loses every
        result in the search because one value was odd. An authentication or
        configuration failure is different in kind and is allowed to propagate,
        because it will affect every remaining value identically and there is no
        value in making the customer wait for thousands of repeats of the same
        failure.

        THE ENDPOINT IS CHOSEN BY route_for() AND NOT RE-DERIVED HERE, so there
        is one place a value's type decides anything. Only the method the value
        routed to is called, which is also why a fake client carrying only
        search_hash still drives every hash test unchanged.
        """
        self.live_lookups += 1
        try:
            if endpoint == ROUTE_URL:
                payload = self.client.search_url(ioc_value)
            else:
                payload = self.client.search_hash(ioc_value)
        except ClientConfigurationError:
            raise
        except NotImplementedError:
            raise
        except Exception as error:
            # TWO FAILURES STOP THE SEARCH INSTEAD OF DEGRADING ONE VALUE.
            #
            # A rejected key and an exhausted rate limit are facts about the
            # search, not about this indicator, so retrying them for every
            # remaining value spends requests that cannot succeed. The first of
            # either trips the breaker; see stop_reason_for() for how each is
            # recognised and the note at STOP_AUTH for why. Everything else
            # falls through to the per-value handling below, unchanged: a 500
            # on one hash still costs that one hash and nothing more.
            stop = stop_reason_for(error)
            if stop is not None:
                return self.stop(stop, error)

            # ONE STRUCTURED LINE, AT DEBUG, AND THE DETAIL GOES TO THE
            # ANALYST INSTEAD.
            #
            # This branch runs once per failing value, so a systemic failure
            # runs it for every value in the search. A WARNING here would put
            # ten thousand identical lines in the customer's log, and the
            # human readable detail would be repeated ten thousand times with
            # it. So the line is at DEBUG and carries only the class name, and
            # the sanitized detail is kept on this object and reported once,
            # to the analyst, by the command. See report_failures().
            #
            # sanitize_message before the value is kept at all, per the
            # single-chokepoint rule in ps_sanitize.
            self.failures += 1
            if self.first_failure is None:
                self.first_failure = sanitize_message(str(error))
            ps_log.debug(
                LOG_COMPONENT, "lookup", "error", reason=type(error).__name__
            )
            # Marked live even though there is no answer. The request was made
            # and may well have been billed, so reporting it as a cache hit
            # would understate what the search cost.
            failed = unknown_fields()
            failed[CACHE_FIELD] = CACHE_LIVE
            return failed

        # ATTRIBUTION IS FETCHED BEFORE THE STORE, SO ONE WRITE CARRIES BOTH.
        #
        # It is addressed by the ARTIFACT'S sha256 and not by the value that was
        # queried, which is what makes attribution work on a url or a domain
        # field: a URL search answers with the artifact the URL served, and that
        # artifact carries its own digest. A not-found payload yields no digest
        # and therefore costs nothing, which is the right answer as well as the
        # cheap one: there is no artifact to attribute.
        attribution = {}
        attribution_payload = None
        attribution_fetched = False
        if self.attribution:
            digest = read_sha256(select_result(payload))
            if digest is not None:
                attribution_fetched, attribution_payload = (
                    self._attribution_lookup(digest)
                )
                if attribution_fetched:
                    attribution = build_attribution_fields(attribution_payload)

        self._store(
            ioc_value,
            payload,
            fold_case=fold_case,
            attribution=attribution_payload,
            attribution_fetched=attribution_fetched,
        )

        fields = build_output_fields(payload)
        fields[CACHE_FIELD] = CACHE_LIVE
        fields.update(attribution)
        return fields

    def enrich_all(self, records):
        """Yield an enriched record for each input record."""
        for record in records:
            yield self.enrich(record)


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


@Configuration()
class PolySwarmSearchCommand(StreamingCommand):
    """Annotate events with the PolySwarm verdict for their indicator."""

    field = Option(
        doc="""
        **Syntax:** **field=***<field>*
        **Description:** the field holding the indicator. Defaults to
        file_hash.
        """,
        require=False,
        default=DEFAULT_HASH_FIELD,
    )

    # The Set validator is the SDK-level declaration. resolve_ioctype() enforces
    # the same rule in code, for the reason limit's pair of checks exists.
    ioctype = Option(
        doc="""
        **Syntax:** **ioctype=***auto|hash|url*
        **Description:** how to route each value. auto, the default,
        classifies the value: a sha256 goes to artifact search, a URL or a
        domain goes to URL search, and an md5, a sha1 or an address is
        reported as unknown with a note rather than guessed at. hash forces
        artifact search. url forces URL search, which also answers for a bare
        domain.
        """,
        require=False,
        default=DEFAULT_IOCTYPE,
        validate=validators.Set(*IOCTYPE_VALUES),
    )

    # THE ONE OPTION ON THIS COMMAND THAT INCREASES WHAT A SEARCH COSTS.
    #
    # Off by default, and design constraint C11 is the whole reason rather than
    # a preference. Each distinct sha256 that resolves to an artifact costs ONE
    # MORE metered request when this is on, so the ceiling on an invocation goes
    # from limit requests to 2 x limit requests. That is said here, in the
    # option a customer reads in the search assistant, because a cost that is
    # only documented in a design doc is a cost a customer discovers on an
    # invoice.
    #
    # The second half of the cap is in IocEnricher: attribution requests are
    # counted against their own ceiling, equal to limit, so the doubling is a
    # bound and not an open end. See the note there for why it is a separate
    # budget rather than a shared one.
    #
    # resolve_attribution() enforces the same rule in code, for the reason
    # limit's and ioctype's pairs of checks exist.
    attribution = Option(
        doc="""
        **Syntax:** **attribution=***<bool>*
        **Description:** also fetch malware family and namespaced tag
        attribution for each artifact, emitting polyswarm_families,
        polyswarm_tags, polyswarm_actor and polyswarm_emerging. Defaults to
        false, because it spends one extra PolySwarm request per distinct
        sha256 on top of the verdict request, so the maximum requests an
        invocation can make with it on is twice the limit option. Artifacts
        with no attribution on file produce no attribution fields at all.
        """,
        require=False,
        default=DEFAULT_ATTRIBUTION,
        validate=validators.Boolean(),
    )

    # require=True is the SDK-level declaration. resolve_limit() enforces the
    # same rule in code so the refusal is testable and the message is ours.
    limit = Option(
        doc="""
        **Syntax:** **limit=***<integer>*
        **Description:** the maximum number of distinct indicators to look up.
        Required, because each distinct indicator spends one API request. The
        maximum accepted value is 10000.
        """,
        require=True,
        validate=validators.Integer(MIN_LIMIT, MAX_LIMIT),
    )

    # PER-SEARCH STATE, HELD ON THE INSTANCE, BECAUSE stream() IS CALLED ONCE
    # PER INPUT CHUNK AND NOT ONCE PER SEARCH.
    #
    # splunklib's chunked protocol loop reads one chunk at a time and calls the
    # command's stream() for each: see bin/lib/splunklib/searchcommands/
    # search_command.py, _execute_v2 at line 1050, which loops on _read_chunk
    # and calls _execute_chunk_v2 at line 1067, which in turn calls
    # process(records), the stream() of streaming_command.py. Splunk sends up
    # to 50,000 records per chunk, and StreamingCommand's own docstring says a
    # streaming command "must be prepared to be invoked many times during the
    # course of pipeline processing".
    #
    # Everything that must be true of the SEARCH therefore has to outlive one
    # call. Building the client, the cache and the enricher per chunk made the
    # limit, the dedup map, every counter, the finish line and the warning
    # texts per chunk as well: a search over a million events with limit=1000
    # could spend a thousand requests in each of twenty chunks, the same hash
    # in two chunks cost two requests, and the customer got one start and one
    # finish line per chunk. The limit is a quota ceiling for the search, so it
    # is now built once and shared, and the storage/passwords read that builds
    # the client happens once instead of per chunk.
    #
    # Declared as class attributes so the first call can test them without an
    # __init__ override. SearchCommand.__init__ takes no arguments and sets up
    # the protocol state, and overriding it to add two counters would put this
    # command's state in front of the SDK's.
    _ps_enricher = None
    _ps_cache = None
    _ps_client = None
    _ps_timer = None
    _ps_limit = None
    _ps_records = 0

    def _pipeline(self):
        """Build the client, cache and enricher once, then reuse them.

        The first chunk builds them and writes the start line. Every later
        chunk gets the same objects back, which is what makes the limit, the
        dedup map and the counters properties of the search rather than of a
        chunk.
        """
        if self._ps_enricher is not None:
            return self._ps_enricher

        # ONE START LINE AND ONE FINISH LINE PER SEARCH.
        #
        # The pair is what makes design section 4.6's page answerable. A start
        # with no finish is a command that died or was killed, which is exactly
        # the "nothing is happening" a customer reports and which no other
        # signal distinguishes from a search that legitimately matched nothing.
        #
        # The finish line carries the cost of the search: how many records were
        # enriched, how many requests were actually spent, and how much of that
        # the cache saved. Those four numbers together are what turns "the app
        # is expensive" into a conversation about a specific search.
        self._ps_timer = ps_log.Timer()
        ps_log.info(LOG_COMPONENT, "start", "ok")

        limit = resolve_limit(self.limit)
        field = resolve_field(self.field)
        ioctype = resolve_ioctype(self.ioctype)
        attribution = resolve_attribution(self.attribution)

        service = getattr(self, "service", None)
        self._ps_limit = limit
        self._ps_records = 0
        self._ps_client = get_client(service)

        # Built even when the collection is missing. VerdictCache degrades to a
        # miss on every read and a no-op on every write, so constructing it
        # unconditionally keeps the cache-present and cache-absent paths the
        # same code rather than two code paths where only one gets exercised.
        self._ps_cache = VerdictCache(service)
        self._ps_enricher = IocEnricher(
            self._ps_client,
            limit,
            field=field,
            cache=self._ps_cache,
            ioctype=ioctype,
            attribution=attribution,
        )
        return self._ps_enricher

    def _is_finished(self):
        """True when splunkd has said this is the last chunk of the search.

        _finished is the SDK's own answer to that question. _execute_v2 reads
        it off the chunk's metadata before the chunk is processed
        (search_command.py line 1064) and reads it back afterwards to close the
        output stream (line 1069), so it is already true while the last chunk's
        records are being yielded. It is None until the first chunk arrives
        (line 97), so a plain truth test is the reading.

        SearchCommand.finish() is NOT the hook for this: it flushes the output
        buffer with finished=True (line 414), which is the SDK's job at the end
        of the protocol and not a question about whether the command is done.
        Calling it here would close the stream in the middle of a search.
        """
        return bool(getattr(self, "_finished", False))

    def stream(self, records):
        enricher = self._pipeline()

        for record in enricher.enrich_all(records):
            self._ps_records += 1
            yield record

        # THE FINISH LINE AND THE WARNINGS BELONG TO THE SEARCH, SO THEY ARE
        # WRITTEN ONCE, ON THE LAST CHUNK. Written per chunk they said "stopped
        # after 1000 distinct indicators" twenty times over for one search, and
        # every count on the line was a fraction of what the search cost.
        if self._is_finished():
            self._report()

    def _report(self):
        """Write the finish line and the search's warnings. Once per search."""
        enricher = self._ps_enricher
        cache = self._ps_cache
        limit = self._ps_limit

        ps_log.info(
            LOG_COMPONENT,
            "finish",
            # DEGRADED, NOT OK, WHEN THE SEARCH STOPPED EARLY. A rejected key
            # produces a result set full of unknowns and an outcome=ok line
            # would be the app reporting success on it. reason carries the
            # exception class name, which is the only part of a failure ps_log
            # has a key for, and is absent on an ordinary run.
            "degraded" if enricher.stopped_reason is not None else "ok",
            reason=enricher.stop_class,
            records=self._ps_records,
            limit=limit,
            limit_reached=enricher.limit_reached,
            lookups=enricher.lookups,
            # Distinct values no endpoint answers for. On the finish line
            # because it is the readable cause of a screen of unknowns, and a
            # count rather than content, which is what ps_log's whitelist
            # permits.
            unrouted=enricher.unrouted,
            # The second metered path's cost, on the same line as the first, so
            # that "what did this search cost" is one line and not two. A zero
            # here on an attribution=true search is the cache having answered
            # everything, and a number equal to the limit is the second cap
            # having been reached, which attribution_limit_reached says outright.
            attribution_lookups=enricher.attribution_lookups,
            attribution_limit_reached=enricher.attribution_limit_reached,
            cache_hits=cache.hits,
            cache_misses=cache.misses,
            cache_stores=cache.stores,
            cache_degraded=cache.degraded,
            duration_ms=self._ps_timer.duration_ms,
        )

        stop_report = enricher.report_stop()
        if stop_report is not None:
            # ONE LINE, NAMING THE CAUSE. The log line was already written by
            # IocEnricher.stop() when the breaker tripped, so this is the
            # analyst's copy and not a second record of the same event.
            self.write_warning(stop_report)

        failure_report = enricher.report_failures()
        if failure_report is not None:
            ps_log.warning(
                LOG_COMPONENT, "lookups_failed", "error", lookups=enricher.failures
            )
            self.write_warning(failure_report)

        attribution_report = enricher.report_attribution_failures()
        if attribution_report is not None:
            ps_log.warning(
                LOG_COMPONENT,
                "attribution_failed",
                "error",
                lookups=enricher.attribution_failures,
            )
            self.write_warning(attribution_report)

        if enricher.attribution_limit_reached:
            # Reported separately from the verdict limit, and worded so the
            # analyst knows the verdicts are complete. Reaching this ceiling
            # without reaching the verdict one is the ordinary case on a search
            # over already-cached indicators, where the verdicts cost nothing
            # and the attribution requests are the whole bill.
            self.write_warning(
                "PolySwarm attribution stopped after {0} distinct artifacts, "
                "the attribution limit for this search. Verdicts are "
                "unaffected; family and actor fields are absent on the "
                "remaining events.".format(limit)
            )

        if cache.degraded:
            # The "why is nothing happening" case, in the one form it takes for
            # this command: the search worked, and cost the customer full quota
            # for every hash because the cache could not be reached.
            self.write_warning(
                "PolySwarm enrichment ran without its verdict cache, so every "
                "indicator cost an API request. Check that the app is fully "
                "installed and that the KV store is available."
            )

        if enricher.limit_reached:
            # write_warning is splunklib's, and surfaces in the job's message
            # list where the analyst sees it. Reaching the limit is not an
            # error: the results are still correct, they are just partial, and
            # silently returning unknown for the tail would be misleading.
            self.write_warning(
                "PolySwarm enrichment stopped after {0} distinct indicators, "
                "the limit for this search. Remaining events are reported as "
                "unknown.".format(limit)
            )


def main(argv=None):
    """Console entry point invoked by Splunk."""
    dispatch(
        PolySwarmSearchCommand,
        argv if argv is not None else sys.argv,
        sys.stdin,
        sys.stdout,
        __name__,
    )


if __name__ == "__main__":
    main()
