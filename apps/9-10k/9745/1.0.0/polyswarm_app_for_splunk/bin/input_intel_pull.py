"""Modular input that pulls PolySwarm threat intel into a Splunk index.

Registered in default/inputs.conf as

    [input_intel_pull://polyswarm_intel_pull]

Design section 4.2 asks for a "scheduled, checkpointed pull of the customer's
entitled intel" writing "to a dedicated app-owned index and sourcetype". This
is that input, and it is the last feature the retired v1 add-on had that this
app did not.

THE INPUT KIND IS THIS FILE'S OWN NAME, AND THAT COUPLING IS NOT OPTIONAL
-------------------------------------------------------------------------
splunkd discovers a modular input by scanning an app's bin directory, running
each script with `--scheme`, and taking THE SCRIPT'S FILE NAME as the input
kind. So the stanza is `[input_intel_pull://<name>]` because this file is
`input_intel_pull.py`. Renaming the file renames the kind, which orphans every
stanza a customer has configured: their input stops running and nothing reports
why, because from splunkd's side the kind no longer exists. The same paragraph
is on `bin/input_task_poller.py` for the same reason.

WHAT v1 DID, AND WHICH PARTS OF IT ARE MIRRORED HERE
----------------------------------------------------
The v1 implementation is `bin/get_polyswarm_data.py` on branch `v1-archive` of
the `polyswarm/Polyswarm-Splunk-App` repository. Every line cite below is to
that file, and the FEATURE is mirrored while the code is not.

The query construction is mirrored clause for clause, because it is the whole
of what the feature is: which artifacts a customer's pull selects. v1 built one
Lucene string (L119 to L149):

    L119  qp  = 'artifact.created:['+startd+'T00:00:00 TO '+endd+'T00:00:00]'
    L120  qp += ' AND scan.latest_scan.polyscore:>='+pscore+' AND ('
    L124  if list_malware_family:
    L129    if i>3: break                       at most three families
    L131    if i>1: qp += ' OR '                joined with OR
    L133    qp += 'polyunite.malware_family:'+mname+' OR families:'+mname
            +' OR scan.\\*.\\*.metadata.malware_family:*'+mname+'*'
            +' OR triage_sandbox_v0.analysis.family:'+mname
            +' OR cape_sandbox_v2.malware_family:'+mname
    L136  if list_tags:
    L137    if list_malware_family: qp += ' OR '   bridged with OR
    L143    if i>3: break                          at most three tags
    L147    qp += 'tags:"'+mtags+'"'               quoted
    L149  qp += ')'

and L216 to L217 supplied the default when the operator named neither a family
nor a tag: `list_tags = 'feed:premium'`. `build_query()` below reproduces all
of that, including the three-value ceilings, the OR bridge between the two
groups, the quoting on a tag and the absence of quoting on a family, and the
literal backslashes in the wildcard field path.

Three things about the query are deliberately NOT mirrored, and all three are
stated here rather than buried:

  * **The window has second resolution and is computed in UTC.** v1 took
    `date.today()` in the SEARCH HEAD'S LOCAL TIME and formatted `%Y-%m-%d`
    (L113 to L117), so its window was always whole local days. That cannot
    express `lookback_minutes` and it cannot express a checkpoint, and it is
    also skewed: the platform's `artifact.created` carries `+00:00` in the
    recorded response, so a local-time bound asks about a different window than
    the operator typed. The bracket syntax, the field name and the `T`
    separator are v1's; the resolution and the timezone are corrected.
  * **No `include` list is sent.** v1 sent a 27-entry `include` (L152) to
    narrow the response. This app sends none, so the response is the whole
    document, which is exactly what `tests/fixtures/metadata-search-recorded.json`
    is a capture of. Constraint C10 is the reason: no recording exists of an
    include-filtered response on this endpoint, so shipping one would build the
    reader on a shape nobody has observed, and a field selection that silently
    does not apply returns a document with fields missing and no error to show
    for it. `ps_client.search_metadata` takes `include` and `exclude` so the
    capability is there when a recording is.
  * **The operator's families and tags are ESCAPED.** v1 interpolated both
    verbatim, so a family of `*` pulled every artifact above the score floor
    and a stray quote or parenthesis either rewrote the query or failed every
    run with a 400 whose log line named nothing responsible. The clause shapes
    are v1's; the values inside them are escaped, and the form refuses
    characters that could only ever be matched as literal text. See the block
    above LUCENE_TERM_SPECIALS.

WHAT v1 GOT WRONG, WHICH IS WHY THIS FILE IS LONG
-------------------------------------------------
v1's two defects here are the two defect classes this repository exists to
prevent, and both are in the error paths rather than the happy path.

  * **The API key went into an indexed event.** L108, L257 and L265 each build
    a dict carrying `'APIKEY': global_api_key` and hand it to the event writer.
    That is constraint C1's leak, in the input, on every failure. Nothing in
    this file assembles an error payload at all: failures go to `ps_log`, whose
    whitelist has no key a credential could travel under, and the run reports
    itself degraded.
  * **Errors were emitted as data events.** L169, L173, L177, L181, L203, L255,
    L266 and L285 all append an error dict to `dataload` or `dataerror`, and
    L275 to L282 writes every one of them into the index as an event. So a
    customer's intel index filled with rows whose fields were `PolySwarm Error`
    and `query`, indistinguishable at search time from an artifact. That is
    constraint C6, and it is why `IntelPuller` has exactly ONE call site that
    can produce an event and that call site is fed only by
    `build_event_fields()`, which reads an artifact and nothing else. There is
    no path in this file from an exception to an event.

The third v1 defect is why the leak was not already public: `result._content`
(L164) raised on responses the serializer could not walk, so the crash masked
the leak. Repairing the crash without stripping the key would have converted a
crash into a working leak, which design section 2's C1 note calls the
fix-unmasks-crash class.

CONSTRAINT C7: CHECKPOINTED, AND SAFE TO RUN TWICE
--------------------------------------------------
The checkpoint is a document per stanza in `ps_intel_pull_checkpoint`, and
`bin/intel_checkpoint.py` carries the reasoning for its shape and for why this
input has one where the task poller does not. Three properties follow, and each
has a test:

  * **The window starts where the last one ended.** So an artifact older than
    the checkpoint is excluded by the platform's own range filter, and a second
    run a second later asks about a window a second wide.
  * **A digest the previous run emitted is refused.** Lucene's square brackets
    are inclusive at both ends, so the instant the two windows share would
    otherwise emit twice. The previous run's digest list closes it.
  * **A digest is emitted once per run.** The same artifact can arrive on two
    pages, and a set inside the run refuses the second.

Running the input twice over an unchanged platform emits nothing the second
time, which is C7 stated as a measurement rather than an intention.

**The checkpoint advances after a run that FAILED not at all, and after a run
that stopped at its CAP only as far as that run got.** A failed run leaves the
previous checkpoint in place and re-pulls the window, which costs duplicate
events bounded by the cap. The alternative loses the window for good: nothing in
the app can tell later that a window was skipped.

**A RUN THAT COULD NOT READ THE CHECKPOINT DOES NOT RUN AT ALL.** That is
stronger than not advancing and it is the fix for the one defect in this input
that could destroy data rather than duplicate it. A failed read used to answer
"no checkpoint", the run pulled a fresh-install window, and a run that then
completed wrote the position with both backlog fields cleared: one transient KV
store outage re-emitted a lookback window AND overwrote the real position and
any drain in progress, which is a permanent gap nothing can reconstruct.
`bin/intel_checkpoint.py` reports a failed read as `READ_FAILED` now, and this
input refuses the run on it: no request, no event, no write, and
`reason=CheckpointUnreadable` on a degraded finish line. A stanza that has
genuinely never run is a different answer and still opens a `lookback_minutes`
window.

A CAPPED RUN STILL MOVES, AND THE ORDERING IS WHAT MAKES THAT SAFE
------------------------------------------------------------------
A capped run used to write no checkpoint at all, and that was a defect rather
than caution. The next run recomputed the same window from the same stored
`window_end` and carried only the previous COMPLETED run's digests, so it
re-emitted the same artifacts as new events, spent the same requests, and never
reached anything past the cap. A window holding more than the cap pinned the
input there for good: up to `max_artifacts_per_run` duplicate events and four or
more metered requests every interval, forever.

**This endpoint answers newest first.** That is read off the recording rather
than assumed: the three kept entries in
`tests/fixtures/metadata-search-recorded.json` descend by `artifact.created`
(15:32:21, then 05:22:33 the same day, then two days earlier), and
`tests/unit/test_input_intel_pull.py` asserts that ordering against the file so
it cannot quietly change. **Ascending cannot be asked for.** The parameters this
endpoint takes are mirrored from the SDK in `bin/ps_client.py` and they are
query, community, include, exclude, offset and limit. There is no sort
parameter, and constraint C10 forbids sending one no recording proves the
platform accepts: a sort that silently does not apply returns the newest page
while the code believes it holds the oldest, which is a gap rather than a
duplicate.

So the drain runs BACKWARDS through the window, and the state that describes it
is the two backlog fields `bin/intel_checkpoint.py` documents:

  1. A capped run has covered the newest part of its window. It stores the
     unchanged floor as `window_end`, the whole second containing the oldest
     artifact it emitted as `backlog_end`, and its own window end as
     `backlog_target`.
  2. The next run asks about `[floor TO backlog_end]`, which is the remainder,
     and refuses the digests the capped run emitted. That closes the boundary,
     which is inclusive at both ends here as everywhere else.
  3. When a drain run finally covers its window whole, `window_end` jumps to
     `backlog_target` and both backlog fields clear. The feed is caught up and
     the next window is an ordinary one.

The boundary is rounded UP to a whole second, because the query renders bounds
at second resolution and a bound rounded down could exclude an artifact in the
same second that has not been emitted yet. Rounding up re-covers a sub-second
sliver whose artifacts are, by the ordering above, exactly the ones the digest
list already refuses.

Three refusals guard the advance, and each is a case where the ordering
argument does not hold:

  * **A run that failed advances nothing.** A request that returned None means
    a page was never seen, so nothing can be said about what is older than what
    was.
  * **A capped run that emitted nothing advances nothing.** With no emitted
    artifact there is no boundary to store.
  * **A capped run that saw the stream go BACKWARDS advances nothing.** The
    documents are checked as they arrive, and a page carrying an artifact newer
    than one already emitted means the ordering this design rests on is not the
    ordering the platform is using. The run reports itself degraded, names
    `UnexpectedOrdering` on its finish line, and falls back to the old
    behaviour: duplicates rather than a gap.

WHAT THIS DESIGN STILL DUPLICATES, SAID HERE RATHER THAN DISCOVERED LATER
-------------------------------------------------------------------------
One case, bounded, and in the recoverable direction. The digest list is one run
deep by design, so during a drain it holds the digests of the most recent drain
run and not of the capped run that started it. When the drain finishes,
`window_end` jumps to the target and the next ordinary window opens at that
same instant, inclusive. An artifact created at EXACTLY the target instant was
emitted by the capped run, its digest is no longer in the list by then, and the
next window emits it a second time.

So the cost of a drain is up to one instant's worth of duplicate events, once,
at the moment the feed catches up. Closing it would mean carrying a second
digest list across the whole drain purely for that boundary, which is more
stored state for a smaller failure than the one this design fixes, and the
failure it would prevent is a duplicate rather than a gap. It is pinned by a
test so that it is a known quantity rather than a surprise.

WHAT A DRAIN GIVES UP ON, WHICH IS ONE SECOND AND IS THE PRICE OF TERMINATING
-----------------------------------------------------------------------------
A drain moves by storing the digests of what it emitted, and the checkpoint
document carries at most `intel_checkpoint.MAX_DIGESTS` of them. One second
holding more artifacts than that used to stall the drain for good: the boundary
stayed on that second, the union of the stored list and the run's own exceeded
the ceiling, `join_digests()` kept the lexically smallest of them and silently
dropped the rest, and the dropped ones were exactly what the next run needed to
refuse what it then re-emitted. Duplicates and four metered requests every
interval, for as long as the stanza existed, and nothing in the app said so.

`_advance()` now notices that the union is over the ceiling and advances the
boundary PAST that second instead: the run counts a `digest_overflow`, logs a
warning naming `DigestListFull`, reports itself degraded, and the next window
closes one second lower. The remainder of that one second is not pulled. That
is a gap, said out loud, and it is accepted here for the reason every other
choice in this file is argued from: the alternative is not a smaller gap, it is
everything older than that second never being pulled at all, plus a duplicate
flood and a bill, forever. Decision D26.

CONSTRAINT C7 AGAIN: THE LAG BUFFER, AND WHY A WINDOW DOES NOT END AT NOW
-------------------------------------------------------------------------
Each window closes at `now - lag_seconds` rather than at `now`, and the setting
exists because an artifact's `artifact.created` is stamped when the platform
takes the artifact, not when the metadata search can find it. Scanning,
normalising and indexing all happen after that stamp. A window that ended
exactly at `now` therefore asked about an instant whose artifacts were partly
not yet searchable, and because the next window starts where this one ended,
every one of those artifacts was skipped permanently. Nothing in the app could
tell later that it had happened: the query answered 200 and the run reported
success.

The buffer is a plain subtraction and it costs no artifacts, because the windows
still chain: what this run does not ask about, the next run does.

CONSTRAINT C11: WHAT THIS SPENDS, AND WHAT BOUNDS IT
----------------------------------------------------
Every page is one metered request against the customer's account, so this input
is the most expensive thing in the app that runs unattended, and it is bounded
three ways:

  * `max_artifacts_per_run` caps the events one run may write. Default 200,
    and `MAX_ARTIFACTS_HARD_CAP` is 1000, which an operator cannot raise from a
    form. A run that reaches the cap STOPS, reports `limit_reached` on its
    finish line, and leaves the rest for the next run. That is C11's
    refuse-rather-than-proceed shape.
  * The page size follows the remaining allowance, so the last page asks for
    what is still wanted rather than a full page. The requests one run can
    spend are therefore bounded by the cap divided by the page size, and
    `MAX_PAGES_HARD_CAP` is a second ceiling on the loop itself.
  * **It ships DISABLED**, which is defect class B8 applied properly. The task
    poller ships enabled and explains at length why that is a defensible
    exception: it spends nothing on its own behalf, because with no detonations
    there are no rows. This input is the opposite. On a fresh install with a
    configured key it would begin pulling intel on a schedule that nobody asked
    for and bill it, which is precisely the "cost-incurring feature defaulted
    on" that B8 names. So the stanza ships `disabled = true` and an operator
    turns it on after choosing a window, a floor and a cap.

WHAT REACHES THE LOG
--------------------
One start line and one finish line per stanza, through `ps_log`, so the
whitelist is the only route a value has into a log file. The finish line uses
the app's existing count vocabulary:

    records        artifacts written as events
    lookups        API requests this run spent
    pages          pages of the paginated response walked
    duplicates     artifacts refused because they were already emitted
    cache_stores   checkpoint documents written
    cache_degraded whether the KV store failed anything
    limit          the per-run cap in force
    limit_reached  whether the run stopped at it
    reason         the class name of the failure, when there was one

Note the omissions, which are the same ones every component here makes: there
is no key for a digest, a family, a tag, a query string, a stanza name or a
community. Those are the customer's own data and their own detection logic, and
`ps_log` has no name they could travel under.

Importing this module is side effect free. It only runs when splunkd invokes it,
and `bin/cmd_sync.py` imports it to run one cycle on demand rather than owning
a second copy of any of it.
"""

import datetime
import json
import math
import os
import re
import sys
import time

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import cmd_search
import community
import intel_checkpoint
import ps_log
import ps_splunkd
import task_store
from ps_client import (
    METADATA_HAS_MORE_FIELD,
    AuthenticationError,
    ClientConfigurationError,
    get_client,
)

from splunklib.modularinput import Argument, Event, Scheme, Script  # noqa: E402

APP_NAME = "polyswarm_app_for_splunk"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "input_intel_pull"

# The input kind, which is this file's own basename. See the module docstring:
# splunkd derives it from the file name, so this constant is a statement of
# that fact rather than a setting anything reads.
INPUT_KIND = "input_intel_pull"

# The stanza this app ships. Named here because three files have to agree on
# it: default/inputs.conf, README/inputs.conf.spec and this module, and a test
# asserts all three do.
SHIPPED_STANZA = "polyswarm_intel_pull"

# ---------------------------------------------------------------------------
# The sourcetype, and why it is set in code as well as in the conf
# ---------------------------------------------------------------------------
#
# Every event this input writes declares this sourcetype on the event itself,
# not only in inputs.conf. That is deliberate duplication with one purpose:
# default/props.conf keys its JSON extraction and its timestamp fields on this
# exact string, so an operator who edits the sourcetype in a local inputs.conf
# would keep indexing events and silently lose every field extraction and the
# CIM mapping built on top of them. Setting it on the event makes the contract
# structural, and a test asserts the constant, the shipped stanza and the props
# stanza all name the same string, which is how the B5 defect class (a config
# sample contradicting a code default) is kept from opening here.
SOURCETYPE = "polyswarm:artifact"

# ---------------------------------------------------------------------------
# The arguments, their defaults and their ceilings
# ---------------------------------------------------------------------------
#
# Every name below appears in default/inputs.conf and README/inputs.conf.spec
# as well, and a test asserts the three agree.

FAMILIES_ARGUMENT = "families"
TAGS_ARGUMENT = "tags"
MIN_POLYSCORE_ARGUMENT = "min_polyscore"
LOOKBACK_MINUTES_ARGUMENT = "lookback_minutes"
MAX_ARTIFACTS_ARGUMENT = "max_artifacts_per_run"
LAG_SECONDS_ARGUMENT = "lag_seconds"
COMMUNITY_ARGUMENT = "community"

# The PolyScore floor.
#
# 0.7, which is not an arbitrary default: it is cmd_search.MALICIOUS_THRESHOLD,
# the score at which this app already bands an artifact malicious. So the
# shipped floor pulls what the rest of the app would call malicious and nothing
# below it, and an operator lowering it is deliberately widening the pull into
# the suspicious band. v1 defaulted to 0.75 (L232), which sat between two of
# this app's own bands and matched nothing else in the product.
DEFAULT_MIN_POLYSCORE = 0.7

# The floor's own floor and ceiling. A polyscore is defined on 0.0 to 1.0, and
# a floor outside that range is a query that matches everything or nothing.
MIN_POLYSCORE_FLOOR = 0.0
MIN_POLYSCORE_CEILING = 1.0

# How far back a first run reaches, in minutes. 1440 is one day, which is v1's
# own default expressed in the unit this input uses (L227: starttime defaulted
# to 1 day). It applies ONLY when there is no checkpoint: every subsequent run
# starts where the last one ended, so this is the size of the first window and
# not a rolling overlap.
DEFAULT_LOOKBACK_MINUTES = 1440

# A ceiling on the first window. A year of backfill at one request per page is
# not a thing to make available from a form, and the cap on artifacts bounds
# what any single run can write anyway, so a very long lookback buys nothing
# except a query the platform has to scan.
MAX_LOOKBACK_MINUTES = 43200

# The per-run event cap and the hard limit on it. See the C11 note in the
# module docstring. 200 is v1's own limit doubled (L222 defaulted to 100), and
# 1000 is the ceiling an operator cannot raise from a form.
DEFAULT_MAX_ARTIFACTS = 200
MAX_ARTIFACTS_HARD_CAP = 1000

# The page size asked for, and the ceiling on how many pages one run may walk.
#
# 50 is the platform's own answer: the recorded response carries "limit": 50
# for a request that asked for no limit, so this is the observed page size
# rather than a guess. The page ceiling is a second bound on the loop itself,
# independent of the artifact cap, so that a platform which kept answering
# has_more with a cursor that never advanced could not spend requests forever.
DEFAULT_PAGE_SIZE = 50
MAX_PAGES_HARD_CAP = 40

DEFAULT_INTERVAL_SECONDS = 900

# How far behind the clock a window closes, in seconds. See the lag buffer note
# in the module docstring for what the setting is for.
#
# 300, and the number is argued rather than picked. Three things bound it:
#
#   * It has to exceed the platform's own indexing latency for the ordinary
#     artifact, because that latency is the whole reason the setting exists. We
#     have no published figure for it and no recording that measures it, so the
#     honest statement is that 300 seconds is the longest delay this app already
#     treats as normal elsewhere: bin/input_task_poller.py's per-row backoff
#     runs 30, 60, 120 then 300 seconds, and 300 is the step at which it settles
#     for a platform-side operation that has not finished yet. Using the same
#     number here keeps one claim in the app about how long the platform may
#     take rather than two.
#   * It has to be small against the interval, because it is also the age of the
#     freshest event the feed can carry. At the shipped 900 second interval a
#     300 second buffer means an artifact is indexed between 5 and 20 minutes
#     after the platform took it, which is well inside what a correlation search
#     over threat intel needs.
#   * It costs no artifacts at any value, because the windows chain: what one
#     run does not ask about, the next run does.
#
# Zero is accepted and is the pre-buffer behaviour, for a deployment that has
# measured its own latency and wants the freshest possible feed. It is not the
# default, because the failure it exposes is silent.
DEFAULT_LAG_SECONDS = 300

# A ceiling on the buffer. An hour, which is already an eccentric amount of
# deliberate lateness for a feed consumed by correlation searches, and past it
# the setting stops being a buffer and becomes a delay nobody will remember
# configuring when the dashboard looks empty.
MAX_LAG_SECONDS = 3600

# The two names that reach a finish line as `reason` without an exception
# behind them. Written as constants because a test asserts the exact strings:
# they are what an operator searches the log for.
#
#   CheckpointUnreadable  the checkpoint read failed, so the run was refused
#                         before it asked the platform anything.
#   DigestListFull        a drain second held more artifacts than the
#                         checkpoint's refusal list may carry, so the drain
#                         advanced past that second. See _advance().
CHECKPOINT_UNREADABLE = "CheckpointUnreadable"
DIGEST_LIST_FULL = "DigestListFull"

SCHEME_TITLE = "PolySwarm threat intel pull"

SCHEME_DESCRIPTION = (
    "Pulls PolySwarm artifacts matching malware families, tags and a PolyScore "
    "floor into a Splunk index on a schedule. Each run covers the window since "
    "the last successful run and writes one event per artifact. Every page is a "
    "metered API request, so the input ships disabled and every run is capped."
)

# ---------------------------------------------------------------------------
# The query, mirrored from v1
# ---------------------------------------------------------------------------

# The field the window filters on. v1 L119.
QUERY_TIME_FIELD = "artifact.created"

# The field the floor filters on. v1 L120. Confirmed against the platform's own
# field catalog: tests/fixtures/metadata-mappings-recorded.json declares it with
# type float and the example "scan.latest_scan.polyscore:[0.5 TO *]".
QUERY_POLYSCORE_FIELD = "scan.latest_scan.polyscore"

# The timestamp format inside the range. v1 built "%Y-%m-%d" and appended
# "T00:00:00" (L115 to L119), which is this format with the time part always
# midnight. Same format, real times.
QUERY_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

# The five clauses one family name expands to. v1 L133, character for
# character, with two things worth naming because a reader will want to tidy
# them and must not:
#
#   * THE BACKSLASHES ARE REAL AND THEY GO ON THE WIRE. v1's source read
#     'scan.\*.\*.metadata.malware_family:*' + mname + '*'. In Python `\*` is
#     not a recognised escape, so the interpreter leaves the backslash in place
#     and the platform received `scan.\*.\*.metadata.malware_family:*NAME*`.
#     They are written here as `\\*` so the literal is explicit rather than
#     relying on that behaviour, which Python 3.12 warns about.
#   * A FAMILY IS NOT QUOTED AND A TAG IS. That asymmetry is v1's (L133 against
#     L147) and it is preserved: quoting a family would change which of these
#     five fields match, and the two are matched differently on purpose.
FAMILY_CLAUSE_TEMPLATE = (
    "polyunite.malware_family:{0}"
    " OR families:{0}"
    " OR scan.\\*.\\*.metadata.malware_family:*{0}*"
    " OR triage_sandbox_v0.analysis.family:{0}"
    " OR cape_sandbox_v2.malware_family:{0}"
)

# One tag clause. v1 L147.
TAG_CLAUSE_TEMPLATE = 'tags:"{0}"'

# ---------------------------------------------------------------------------
# What a family and a tag may contain, and what happens to the rest
# ---------------------------------------------------------------------------
#
# THE OPERATOR'S TEXT GOES INTO A QUERY LANGUAGE, which v1 did too and neither
# of them thought about. A family or a tag is free text typed into a form, the
# clause templates above interpolate it into a Lucene string, and the platform
# parses that string. Two things follow, and both were live before this block
# existed:
#
#   * A metacharacter REWRITES THE QUERY. `families = *` expands to five
#     wildcard clauses and pulls every artifact above the score floor, which is
#     a metered pull nobody asked for. A parenthesis or a colon can close the
#     group the clauses sit in or turn the value into a field name.
#   * A metacharacter the parser rejects FAILS EVERY RUN. The platform answers
#     400, the finish line says degraded with the client error's class name,
#     and nothing on it names the character responsible. A feed that has been
#     dead for a week looks like a platform problem.
#
# So there are two gates, at the two points that can hold one.
#
# ESCAPING, HERE, applies to every value on every run, including a stanza
# somebody wrote into local/inputs.conf by hand rather than through the form.
# It makes the value a literal term: what the operator typed is what is
# matched, and nothing they typed can change the shape of the query.
#
# VALIDATION, IN validate_input(), refuses at save time. Escaping already makes
# the run safe, so this is about the operator: a family of `*` escaped to `\*`
# matches the literal string "*" and pulls nothing, forever, with no error
# anywhere. Being told at the point of typing is the difference between a
# refusal and a silent empty feed.
#
# THE TWO ARE ESCAPED DIFFERENTLY BECAUSE ONE IS QUOTED, which is v1's
# asymmetry (L133 against L147) and is preserved for the reason the note on
# FAMILY_CLAUSE_TEMPLATE gives. Inside a quoted phrase, Lucene treats every
# metacharacter as a literal except the quote that ends the phrase and the
# backslash that escapes it, so a tag needs those two escaped and nothing
# else. That matters rather than being a nicety: DEFAULT_TAG is `feed:premium`
# and the shipped stanza's `sector:healthcare` example carries a colon too, so
# escaping a tag's colon would change what every default pull matches.
#
# The set is Lucene's own documented list of special characters, plus the
# forward slash that later versions added. A family may still carry a dot, an
# underscore or a digit, because none of those is special and family names are
# full of them.
LUCENE_TERM_SPECIALS = "\\+-!(){}[]^\"~*?:/&|"

# The two characters that survive nothing inside a quoted phrase.
LUCENE_PHRASE_SPECIALS = "\\\""

# What a family may contain, which is narrower than what escaping can carry.
#
# Letters, digits, dot, underscore and hyphen, which is every family name in
# the recorded response and in v1's own examples. A space is refused as well as
# a metacharacter: an unquoted term with a space in it is two terms to the
# parser, and the second one lands outside the clause it was meant for.
FAMILY_ALLOWED_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# What a tag may contain. Wider, because a tag IS quoted and because the
# product's own tags carry colons: `feed:premium` is the default pull.
# Everything printable except the two characters a phrase cannot hold.
TAG_REFUSED_CHARACTERS = '"\\'

# The ceilings v1 applied to each list, at L129 and L143. Three, and the values
# past it are dropped silently there. Mirrored, and reported here: the input
# counts what it dropped so an operator who typed five families is told four
# and five were ignored rather than left to wonder why they match nothing.
MAX_FAMILIES = 3
MAX_TAGS = 3

# What v1 searched for when the operator named neither a family nor a tag.
# L216 to L217: `list_tags = 'feed:premium'`, which then went through the tag
# clause at L147 and became tags:"feed:premium". The recorded response confirms
# it is a real tag: three of the fifty artifacts carry it.
DEFAULT_TAG = "feed:premium"

JOIN = " OR "

# ---------------------------------------------------------------------------
# The event, and where each field comes from
# ---------------------------------------------------------------------------
#
# THE FIELD NAMES ARE THE ENRICHMENT COMMAND'S, IMPORTED RATHER THAN RETYPED.
#
# `polyswarmsearch` already annotates an event with polyswarm_polyscore,
# polyswarm_verdict, polyswarm_detections, polyswarm_permalink,
# polyswarm_families and polyswarm_tags, and those names are its public
# contract. An indexed artifact that used different names for the same facts
# would make every saved search and every dashboard panel written against one
# surface wrong on the other, so this input imports the constants from
# cmd_search and the two surfaces cannot drift.
#
# The reader functions are imported for the same reason and it buys more than
# tidiness: read_detections, read_detection_total and read_score take a mapping
# and look for "detections" and "polyscore" inside it, and the metadata
# response carries both of those under its `scan` group with exactly those
# names. So the enrichment command's reader reads a metadata artifact correctly
# already, and cmd_search.verdict_for() is the one definition of the verdict band in the
# app rather than a second copy of two thresholds.
#
# Four field names are this input's own, because the enrichment command has no
# constant for them: it annotates an event that already carries its own subject
# and its own timestamp, and an indexed artifact has to carry both itself.
# The six the enrichment command already defines. Assigned rather than
# retyped, so the two surfaces cannot drift and so a reader can see at a
# glance which names are borrowed and which are this input's own.
POLYSCORE_FIELD = cmd_search.POLYSCORE_FIELD
VERDICT_FIELD = cmd_search.VERDICT_FIELD
DETECTIONS_FIELD = cmd_search.DETECTIONS_FIELD
PERMALINK_FIELD = cmd_search.PERMALINK_FIELD
FAMILIES_FIELD = cmd_search.FAMILIES_FIELD
TAGS_FIELD = cmd_search.TAGS_FIELD

# The four that are this input's own.
SHA256_FIELD = "polyswarm_sha256"
FIRST_SEEN_FIELD = "polyswarm_first_seen"
LAST_SEEN_FIELD = "polyswarm_last_seen"
COMMUNITY_FIELD = "polyswarm_community"

# Every field an event can carry. Asserted field for field against
# build_event_fields(), which is what stops a field appearing in an event that
# props.conf has never heard of.
EVENT_FIELDS = (
    SHA256_FIELD,
    POLYSCORE_FIELD,
    VERDICT_FIELD,
    DETECTIONS_FIELD,
    FAMILIES_FIELD,
    TAGS_FIELD,
    FIRST_SEEN_FIELD,
    LAST_SEEN_FIELD,
    PERMALINK_FIELD,
    COMMUNITY_FIELD,
)

# The groups and leaves this input reads out of one metadata document. Every
# one of them is declared in the platform's own field catalog, and
# tests/unit/test_input_intel_pull.py asserts that against
# tests/fixtures/metadata-mappings-recorded.json rather than trusting it.
ARTIFACT_GROUP = "artifact"
HASH_GROUP = "hash"
SCAN_GROUP = "scan"
POLYUNITE_GROUP = "polyunite"
FAMILIES_GROUP = "families"
TAGS_GROUP = "tags"
LATEST_SCAN_KEY = "latest_scan"
CREATED_KEY = "created"
SHA256_KEY = "sha256"
FIRST_SEEN_KEY = "first_seen"
LAST_SEEN_KEY = "last_seen"
MALWARE_FAMILY_KEY = "malware_family"

# The community the artifact was found in, as the platform reports it. Recorded
# value "_public". Read rather than echoed back from the request for the reason
# a task row records the resolved community rather than the requested one: the
# platform resolves the scope server side and the event should say where the
# artifact actually is.
META_COMMUNITY_KEY = "meta_community"


# ---------------------------------------------------------------------------
# The query builder: pure
# ---------------------------------------------------------------------------


def split_list(raw):
    """Return the comma separated values of one argument, in order. Pure.

    MIRRORS v1's PARSING, WHITESPACE HANDLING INCLUDED. v1 removed every space
    from the whole string before splitting it (L207 and L212:
    `list_malware_family.replace(" ", "")`), so "red line, godfather" became
    two values "redline" and "godfather" rather than one value with a space in
    it. That is preserved deliberately rather than improved: a family name is
    interpolated unquoted into five field clauses (L133), and a space inside
    one would end the clause early and change what the query matches. An
    operator who needs a value with a space in it needs the tag form, which is
    quoted.

    Empty values are dropped, so a trailing comma and a doubled comma are both
    harmless.
    """
    if raw is None:
        return []
    text = str(raw).replace(" ", "")
    if not text:
        return []
    return [part for part in text.split(",") if part]


def format_polyscore(value):
    """Return the floor as it appears in the query. Pure.

    v1 interpolated the operator's own string straight into the query (L120:
    `'>='+pscore`), which put whatever they typed on the wire. This formats a
    float that read_min_polyscore() has already validated, using repr's
    shortest round-tripping form so that 0.7 renders as "0.7" and not as
    "0.7000000000000001".
    """
    return repr(float(value))


def format_window_bound(epoch):
    """Return one end of the window as the query spells it. Pure.

    UTC, and see the module docstring for why that is a correction to v1 rather
    than a mirror of it: the platform's own timestamps carry +00:00, so a bound
    built from the search head's local date asks about a different window than
    the operator asked for.

    The offset is not written into the bound. The recorded live query that this
    app's fixture came from used the bare `%Y-%m-%dT%H:%M:%S` form and answered
    200, so that is the form known to parse.
    """
    moment = datetime.datetime.fromtimestamp(
        float(epoch), datetime.timezone.utc
    )
    return moment.strftime(QUERY_TIME_FORMAT)


def _quote_character(character):
    """Return one character as a message names it. Pure.

    A space has no visible form, so it is named rather than shown: a refusal
    reading `cannot contain  ` teaches an operator nothing.
    """
    if character == " ":
        return "a space"
    if character.isspace():
        return "whitespace"
    return "the character {0}".format(character)


def _first_refused_family_character(name):
    """Return the first character of a family name that is not allowed. Pure.

    Named in the refusal so an operator reads which character to remove rather
    than a charset to compare their value against by eye. An empty answer
    cannot happen: the caller only asks about a name the pattern refused.
    """
    for character in str(name or ""):
        if not FAMILY_ALLOWED_RE.match(character):
            return _quote_character(character)
    return "that value"


def escape_lucene_term(value):
    """Return one unquoted query term with its metacharacters escaped. Pure.

    For a family, which the clause template interpolates unquoted. Every
    character in LUCENE_TERM_SPECIALS gets a backslash in front of it, so the
    value can only ever be matched as the literal text somebody typed.

    The backslash is escaped by the same loop, and it is first in the set for
    the usual reason: escaping it after anything else would double the
    backslashes the earlier characters just gained.
    """
    text = "" if value is None else str(value)
    escaped = []
    for character in text:
        if character in LUCENE_TERM_SPECIALS:
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


def escape_lucene_phrase(value):
    """Return one quoted query phrase with its two specials escaped. Pure.

    For a tag, which the clause template interpolates inside double quotes.
    Only the quote and the backslash are escaped, because inside a phrase
    Lucene reads everything else literally, and escaping more would change
    what the product's own colon-bearing tags match. See the block above
    LUCENE_TERM_SPECIALS.
    """
    text = "" if value is None else str(value)
    escaped = []
    for character in text:
        if character in LUCENE_PHRASE_SPECIALS:
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


def build_query(families, tags, min_polyscore, window_start, window_end):
    """Return the metadata query string for one run. Pure.

    Assembled in v1's own order and with v1's own separators, so that the
    string this produces is the string v1 produced for the same inputs, up to
    the window resolution. See the module docstring for the line by line
    mapping.

    :param families: family names, already split. At most MAX_FAMILIES are used.
    :param tags: tag values, already split. At most MAX_TAGS are used.
    :param min_polyscore: the floor, as a float.
    :param window_start: epoch seconds the window opens at, inclusive.
    :param window_end: epoch seconds the window closes at, inclusive.
    """
    selected_families = list(families or [])[:MAX_FAMILIES]
    selected_tags = list(tags or [])[:MAX_TAGS]

    # v1 L216 to L217. Neither list given means the premium feed, which is what
    # made a stanza with every field left blank still pull something useful.
    if not selected_families and not selected_tags:
        selected_tags = [DEFAULT_TAG]

    query = "{0}:[{1} TO {2}]".format(
        QUERY_TIME_FIELD,
        format_window_bound(window_start),
        format_window_bound(window_end),
    )
    query += " AND {0}:>={1} AND (".format(
        QUERY_POLYSCORE_FIELD, format_polyscore(min_polyscore)
    )

    # ESCAPED ON THE WAY IN, both of them, and differently. See the block above
    # LUCENE_TERM_SPECIALS for why a family is escaped against the whole
    # metacharacter set and a tag against two characters: the family is
    # interpolated unquoted and the tag inside a phrase.
    clauses = [
        FAMILY_CLAUSE_TEMPLATE.format(escape_lucene_term(name))
        for name in selected_families
    ]
    clauses.extend(
        TAG_CLAUSE_TEMPLATE.format(escape_lucene_phrase(tag))
        for tag in selected_tags
    )

    # One join over the concatenated list gives v1's bridge between the two
    # groups (L137 to L138) as a consequence rather than as a special case.
    query += JOIN.join(clauses)
    query += ")"
    return query


# ---------------------------------------------------------------------------
# The response reader: pure
# ---------------------------------------------------------------------------


def read_result_list(payload):
    """Return the artifact documents on one page, in order. Pure.

    An empty list for every payload that does not carry one, which covers a
    None from a 204, an envelope with nothing in it, and a shape this app does
    not recognise. None of those is an error: a window with no matching
    artifacts is the ordinary answer for a narrow family filter, and an input
    that raised on it would report a failure every quiet hour.

    THE ENVELOPE IS RECOGNISED BY THE TYPE OF ITS VALUE AND NEVER BY THE NAME
    ALONE, which is the trap cmd_search.select_result carries: an artifact can
    hold its own "result" key. Here the outer value must be a list to be taken
    as the page.
    """
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    inner = payload.get("result")
    if isinstance(inner, list):
        return [item for item in inner if isinstance(item, dict)]
    return []


def read_has_more(payload):
    """True when the platform says another page exists. Pure.

    STRICTLY True AND NOT MERELY TRUTHY. The SDK notes the field "will always
    be present, being either False or True"
    (core.PolyswarmRequest.parse_result), so anything else arriving here is a
    shape this app has not seen, and the safe reading of an unrecognised value
    is that the walk is over: guessing there is another page spends a request
    to find out.
    """
    if not isinstance(payload, dict):
        return False
    return payload.get(METADATA_HAS_MORE_FIELD) is True


def read_offset(payload):
    """Return the cursor for the next page, or None. Pure.

    A non-empty string only. See ps_client.METADATA_OFFSET_PARAM: the value is
    an opaque encrypted token and the only valid thing to do with it is send it
    back unchanged. A number arriving here would be a shape change rather than
    a row offset, and it is refused rather than sent, because a cursor the
    platform cannot decode returns a page that silently is not the next one.
    """
    if not isinstance(payload, dict):
        return None
    value = payload.get("offset")
    if value is None or isinstance(value, bool) or not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def read_sha256(item):
    """Return one artifact's digest, lowercased, or None. Pure.

    Read from the `hash` group first and the `artifact` group second. Both
    carry it in the recorded response and they agree there; the hash group is
    preferred because it is the group whose whole purpose is digests, and the
    fallback exists because a document with no hash group is a shape this app
    should degrade on rather than drop.

    Validated against task_store's own digest pattern rather than a second one,
    so the app has one definition of what a sha256 looks like. A document with
    no readable digest yields no event: the digest is the event's subject, it
    is what the permalink is derived from, and it is the key the dedupe works
    on, so an artifact without one cannot be reported honestly.
    """
    if not isinstance(item, dict):
        return None
    for group in (HASH_GROUP, ARTIFACT_GROUP):
        block = item.get(group)
        if not isinstance(block, dict):
            continue
        value = block.get(SHA256_KEY)
        if value is None or isinstance(value, bool) or not isinstance(value, str):
            continue
        text = value.strip().lower()
        if task_store.SHA256_RE.match(text):
            return text
    return None


def read_text(block, key):
    """Return one string field as the platform sent it, or None. Pure.

    Passed through verbatim rather than reformatted. Used for the two ISO
    timestamps and for the community name, which is every scalar string this
    input reads out of a document.

    A TIMESTAMP IS NOT REWRITTEN. props.conf tells Splunk how to read the ISO
    form the platform sends, and a timestamp this app reformatted would be a
    second format to support for no gain.

    A bool is refused before the isinstance check would have refused it anyway,
    so the rule reads the same way it does in cmd_search.read_string_list: a
    boolean is never a name and never a date.
    """
    if not isinstance(block, dict):
        return None
    value = block.get(key)
    if value is None or isinstance(value, bool) or not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def read_created_epoch(item):
    """Return one artifact's `artifact.created` as epoch seconds, or None. Pure.

    THE FIELD IS THE ONE THE WINDOW FILTERS ON, and that coupling is the point:
    this value is compared against window bounds and stored as the drain
    boundary, so reading any other timestamp would move the boundary somewhere
    the query does not agree with. `scan.first_seen` is NOT a fallback here for
    that reason, even though build_event_fields() accepts it as one for the
    event's own first-seen field.

    The platform sends `2026-09-08T15:32:21.069612+00:00`, which
    datetime.fromisoformat reads directly on every Python this app supports. A
    `Z` suffix is translated first, because fromisoformat did not accept one
    before Python 3.11 and this app's floor is 3.9. A value with no offset at
    all is read as UTC, which is the timezone every timestamp in the recording
    carries.

    None for anything unreadable, and the caller treats that as a reason not to
    advance a checkpoint rather than as a value to guess at.
    """
    if not isinstance(item, dict):
        return None
    text = read_text(item.get(ARTIFACT_GROUP), CREATED_KEY)
    if text is None:
        return None
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.timezone.utc)
    return moment.timestamp()


def read_families(item):
    """Return the families on file for one artifact, or None. Pure.

    TWO SOURCES, MERGED, AND THAT IS A DEPARTURE WORTH NAMING. The metadata
    document carries family attribution in two places: a top level `families`
    list, and `polyunite.malware_family`, a single name from the platform's own
    normaliser. v1 queried both (L133) and this reads both, because they do not
    always agree: in the recorded set an artifact carries families
    ["CobaltStrike"] next to polyunite Emotet, and reporting only one of those
    would drop an attribution the platform holds.

    cmd_search.read_string_list is used for the list and its doctrine is that
    the platform's list is never deduplicated or reordered. That still holds
    for the list itself. What is deduplicated here is the MERGE, case
    insensitively, keeping the first spelling seen: the same family arriving
    from both sources is one fact about the artifact and emitting it twice in a
    multivalue field would be this app's own artefact rather than the
    platform's answer.

    None rather than an empty list when there is nothing, because an empty
    multivalue field in Splunk is a field that is present and says nothing, and
    most artifacts have no attribution at all.
    """
    if not isinstance(item, dict):
        return None

    found = []
    seen = set()

    for value in cmd_search.read_string_list(item, FAMILIES_GROUP) or []:
        folded = value.lower()
        if folded not in seen:
            seen.add(folded)
            found.append(value)

    polyunite = item.get(POLYUNITE_GROUP)
    if isinstance(polyunite, dict):
        value = polyunite.get(MALWARE_FAMILY_KEY)
        if isinstance(value, str) and not isinstance(value, bool):
            text = value.strip()
            if text and text.lower() not in seen:
                seen.add(text.lower())
                found.append(text)

    return found or None


def build_event_fields(item):
    """Return the event fields for one artifact document, or None. Pure.

    THE ONLY THING IN THIS MODULE THAT PRODUCES THE CONTENT OF AN EVENT, and
    that is constraint C6 held by construction rather than by review. It takes
    an artifact document and nothing else: it has no parameter an exception, a
    message, a query string or a credential could arrive through, so there is
    no path in this file from a failure to an indexed event. v1's failure was
    exactly the absence of that property.

    None when the document carries no readable digest. See read_sha256().

    Every other field is OMITTED when it cannot be read, never guessed and
    never emitted empty. A verdict is always present because cmd_search.verdict_for()
    always answers, and its answer for an unreadable score is `unknown`, which
    is a real statement and distinct from malicious, suspicious and benign.
    """
    sha256 = read_sha256(item)
    if sha256 is None:
        return None

    scan = item.get(SCAN_GROUP)
    scan = scan if isinstance(scan, dict) else {}
    latest = scan.get(LATEST_SCAN_KEY)
    latest = latest if isinstance(latest, dict) else {}

    score = cmd_search.read_score(latest)
    total = cmd_search.read_detection_total(scan)

    fields = {
        SHA256_FIELD: sha256,
        VERDICT_FIELD: cmd_search.verdict_for(score, total),
    }

    if score is not None:
        fields[POLYSCORE_FIELD] = score

    detections = cmd_search.read_detections(scan)
    if detections is not None:
        fields[DETECTIONS_FIELD] = detections

    families = read_families(item)
    if families is not None:
        fields[FAMILIES_FIELD] = families

    tags = cmd_search.read_string_list(item, TAGS_GROUP)
    if tags is not None:
        fields[TAGS_FIELD] = tags

    first_seen = read_text(scan, FIRST_SEEN_KEY) or read_text(
        item.get(ARTIFACT_GROUP), CREATED_KEY
    )
    if first_seen is not None:
        fields[FIRST_SEEN_FIELD] = first_seen

    last_seen = read_text(scan, LAST_SEEN_KEY)
    if last_seen is not None:
        fields[LAST_SEEN_FIELD] = last_seen

    # Derived from the digest, not read from the response: the metadata
    # endpoint sends no permalink, unlike the hash and URL searches. The prefix
    # is task_store's, so the app has one portal URL construction and one
    # place where decision D8's unverified two-segment note lives.
    permalink = task_store.report_url_for(sha256)
    if permalink is not None:
        fields[PERMALINK_FIELD] = permalink

    meta_community = read_text(item, META_COMMUNITY_KEY)
    if meta_community is not None:
        fields[COMMUNITY_FIELD] = meta_community

    return fields


# ---------------------------------------------------------------------------
# The argument readers: pure
# ---------------------------------------------------------------------------


def _clamp_int(raw, default, minimum, maximum):
    """Return a whole number inside the bounds, or the default. Pure.

    Every unreadable value reads as the default, which is the direction that
    keeps the input running: a stanza with `lookback_minutes = a day` in it
    should pull a day and not nothing. A value above the ceiling is clamped
    rather than refused for the same reason, and validate_input() is where an
    operator is told about it, at the point they can still fix it.
    """
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if value < minimum:
        return default
    return min(value, maximum)


def read_families_argument(parameters):
    """Return the families one stanza asks for. Pure."""
    if not isinstance(parameters, dict):
        return []
    return split_list(parameters.get(FAMILIES_ARGUMENT))


def read_tags_argument(parameters):
    """Return the tags one stanza asks for. Pure."""
    if not isinstance(parameters, dict):
        return []
    return split_list(parameters.get(TAGS_ARGUMENT))


def read_min_polyscore(parameters):
    """Return the floor one stanza asks for. Pure.

    THE FLOOR IS RAISE-ONLY AGAINST THE DEFAULT IN ONE DIRECTION ONLY, which
    is worth stating precisely because it is easy to over-read. An operator may
    lower the floor: widening a pull into the suspicious band is a legitimate
    thing to want and the cap is what keeps it affordable. What is refused is a
    floor OUTSIDE the range a polyscore is defined on, because 0.0 matches
    every artifact the platform holds and anything above 1.0 matches none, and
    neither is a threat intel feed.
    """
    if not isinstance(parameters, dict):
        return DEFAULT_MIN_POLYSCORE
    raw = parameters.get(MIN_POLYSCORE_ARGUMENT)
    if raw is None or str(raw).strip() == "":
        return DEFAULT_MIN_POLYSCORE
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_MIN_POLYSCORE
    if value != value or value in (float("inf"), float("-inf")):
        return DEFAULT_MIN_POLYSCORE
    if value <= MIN_POLYSCORE_FLOOR or value > MIN_POLYSCORE_CEILING:
        return DEFAULT_MIN_POLYSCORE
    return value


def read_lookback_minutes(parameters):
    """Return the first window's size in minutes. Pure."""
    if not isinstance(parameters, dict):
        return DEFAULT_LOOKBACK_MINUTES
    return _clamp_int(
        parameters.get(LOOKBACK_MINUTES_ARGUMENT),
        DEFAULT_LOOKBACK_MINUTES,
        1,
        MAX_LOOKBACK_MINUTES,
    )


def read_max_artifacts(parameters):
    """Return the per-run event cap. Pure, and clamped at the hard cap."""
    if not isinstance(parameters, dict):
        return DEFAULT_MAX_ARTIFACTS
    return _clamp_int(
        parameters.get(MAX_ARTIFACTS_ARGUMENT),
        DEFAULT_MAX_ARTIFACTS,
        1,
        MAX_ARTIFACTS_HARD_CAP,
    )


def read_lag_seconds(parameters):
    """Return how far behind the clock the window closes. Pure.

    ZERO IS A VALUE AND NOT AN ABSENCE, which is the one thing that separates
    this reader from the other two integer readers here. `max_artifacts_per_run`
    and `lookback_minutes` both floor at 1 because zero means "do nothing" for
    each of them, and an operator who typed it wants the input disabled instead.
    Zero here is a coherent request: close the window at the clock, which is
    what this input did before the buffer existed. So the minimum is 0 and a
    stanza carrying `lag_seconds = 0` gets exactly that.
    """
    if not isinstance(parameters, dict):
        return DEFAULT_LAG_SECONDS
    return _clamp_int(
        parameters.get(LAG_SECONDS_ARGUMENT),
        DEFAULT_LAG_SECONDS,
        0,
        MAX_LAG_SECONDS,
    )


def read_community_argument(parameters):
    """Return the community one stanza names, or None for the app's rule. Pure.

    BLANK MEANS bin/community.py, which is design 4.3's rule and decision D15:
    the operator's configured community wins, then the account's most private
    entitled one, then the platform default. This argument is the per-stanza
    override above all three, for a deployment that pulls one community's intel
    into one index and another's into another.
    """
    if not isinstance(parameters, dict):
        return None
    raw = parameters.get(COMMUNITY_ARGUMENT)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


# ---------------------------------------------------------------------------
# The pull
# ---------------------------------------------------------------------------


class IntelPuller(object):
    """Runs one pull cycle for one stanza.

    Split out from the Script subclass for the reason TaskPoller is: a modular
    input script cannot be driven outside splunkd's own handshake, so logic
    left inside it is logic no test can reach. This takes anything with a
    `search_metadata()` method, anything with `read()` and `write()`, and a
    plain callable to emit through, so the whole cycle runs with a fake client,
    a fake KV store, a fake clock and a list.

    It is also what `bin/cmd_sync.py` runs, which is the reason the emit sink
    is a callable: the command needs the same cycle with a different
    destination, and a second copy of the cycle is how the two would come to
    disagree about the cap.
    """

    def __init__(
        self,
        client,
        checkpoint,
        stanza,
        families=None,
        tags=None,
        min_polyscore=DEFAULT_MIN_POLYSCORE,
        lookback_minutes=DEFAULT_LOOKBACK_MINUTES,
        max_artifacts=DEFAULT_MAX_ARTIFACTS,
        lag_seconds=DEFAULT_LAG_SECONDS,
        page_size=DEFAULT_PAGE_SIZE,
        community_name=None,
        advance_checkpoint=True,
        now=None,
    ):
        """
        :param client: anything with a search_metadata() method.
        :param checkpoint: an intel_checkpoint.IntelCheckpoint, or anything
            with read() and write(). None disables checkpointing entirely,
            which is what happens when there is no KV store to reach.
        :param stanza: the input stanza name, which keys the checkpoint.
        :param lag_seconds: how far behind the clock the window closes. See the
            lag buffer note in the module docstring.
        :param advance_checkpoint: whether a run writes the checkpoint. False
            for the manual sync, which does not index what it pulls and must
            not tell the scheduled input a window is done. See bin/cmd_sync.py.
        :param now: a callable returning epoch seconds, for tests.
        """
        self.client = client
        self.checkpoint = checkpoint
        self.stanza = stanza
        self.families = list(families or [])
        self.tags = list(tags or [])
        self.min_polyscore = float(min_polyscore)
        self.lookback_minutes = int(lookback_minutes)
        self.max_artifacts = min(int(max_artifacts), MAX_ARTIFACTS_HARD_CAP)
        self.lag_seconds = max(0, min(int(lag_seconds), MAX_LAG_SECONDS))
        self.page_size = max(1, min(int(page_size), self.max_artifacts))
        self.community_name = community_name
        self.advance_checkpoint = bool(advance_checkpoint)
        self._now = time.time if now is None else now

        # Counters, read by the caller for its finish line and by the sync
        # command for its summary. Every spend assertion in the tests reads
        # these rather than a fake's internals.
        self.window_start = None
        self.window_end = None
        self.emitted = 0
        self.duplicates = 0
        self.unreadable = 0
        self.requests = 0
        self.pages = 0
        self.limit_reached = False
        self.checkpoint_written = False
        self.dropped_families = 0
        self.dropped_tags = 0

        # The backlog state, which is what makes a capped run move. See the
        # capped-run section of the module docstring.
        #
        #   draining         this run's window end came from a stored backlog
        #                    boundary rather than from the clock
        #   backlog_target   where window_end goes when the drain finishes.
        #                    Equal to this run's own window end when there is no
        #                    drain in progress, which is the ordinary case
        #   backlog_written  the boundary this run stored, or None
        #   oldest_emitted   the earliest artifact.created this run emitted,
        #                    which the boundary is derived from
        #   out_of_order     documents that arrived NEWER than one already
        #                    emitted, which is the ordering assumption failing
        self.draining = False
        self.backlog_target = None
        self.backlog_written = None
        self.oldest_emitted = None
        self.undated = 0
        self.out_of_order = 0

        # The boundary and digests this run started from, held for the write.
        self._stored_backlog_end = None
        self._known_digests = set()

        # The class name of the failure that stopped the run, and nothing else
        # about it. See ps_client.get_api_key for why the message is dropped
        # rather than sanitized.
        self.last_failure = None
        self.authentication_failed = False

        # True when the checkpoint read failed and the run was refused. Held
        # separately from last_failure because the two say different things to
        # a reader: last_failure names what went wrong, and this says the run
        # never started, so the zero counters beside it are a refusal rather
        # than an empty window. bin/cmd_sync.py reads it for the same reason.
        self.checkpoint_read_failed = False

        # How many times this run gave up on a drain boundary because the
        # refusal list it would have had to store was larger than the
        # checkpoint document may carry. See _advance(): each one is a whole
        # second of the window advanced past, so it is a bounded, counted,
        # logged skip rather than the endless loop it replaces.
        self.digest_overflow = 0

        # The digests this run emitted, which become the next run's refusal
        # list. Held rather than streamed because the checkpoint is written
        # once, after the run completes.
        self.digests = set()

        self.query = None

    # -- the cycle -------------------------------------------------------

    def run(self, emit):
        """Run one cycle. Returns the number of events emitted.

        NOTHING RAISES OUT OF HERE. An input runs unattended on a schedule, so
        a transport failure part way through a walk keeps the pages that
        succeeded and stops: the alternative loses a page of artifacts already
        paid for. That is not the catch-all constraint C6 forbids, because
        nothing is fabricated and nothing is swallowed silently: the failure is
        counted, its class name reaches the finish line, the run reports itself
        degraded, and the checkpoint is NOT advanced, so the window is pulled
        again rather than lost.

        A RUN WHOSE CHECKPOINT READ FAILED IS REFUSED BEFORE IT STARTS, which
        is a stronger statement than "does not advance" and is a different one.
        A walk that fails part way has a window it knows and pages it already
        paid for, so it keeps them and leaves the checkpoint alone. A run that
        could not read the checkpoint has neither: it cannot tell a stanza that
        has never run from one whose position it simply could not fetch, and
        the two want opposite windows. So it asks nothing, emits nothing,
        writes nothing, spends no metered request, and reports itself degraded
        with `reason=CheckpointUnreadable` on the finish line. The next
        interval reads the collection again.

        :param emit: a callable taking one mapping of event fields.
        """
        self.dropped_families = max(0, len(self.families) - MAX_FAMILIES)
        self.dropped_tags = max(0, len(self.tags) - MAX_TAGS)

        now = float(self._now())
        stored_end, known_digests = None, set()
        backlog_end, backlog_target = None, None
        if self.checkpoint is not None:
            position = self.checkpoint.read(self.stanza)
            if intel_checkpoint.is_read_failure(position):
                # THE RUN IS REFUSED, and the refusal is the fix for the worst
                # failure this input had. See the note above run() and
                # bin/intel_checkpoint.py's own: a run that could not read its
                # position does not know its window, so it asks nothing, emits
                # nothing and writes nothing, and the next interval reads the
                # collection again.
                self.checkpoint_read_failed = True
                self.last_failure = CHECKPOINT_UNREADABLE
                return 0
            stored_end = position[0]
            known_digests = position[1]
            if len(position) > 3:
                backlog_end, backlog_target = position[2], position[3]
        self._known_digests = set(known_digests or ())

        # The frontier: the newest instant this run is willing to ask about.
        # NOT `now`, and the lag buffer note in the module docstring is why.
        frontier = now - self.lag_seconds

        if stored_end is None:
            self.window_start = frontier - (self.lookback_minutes * 60.0)
        else:
            self.window_start = stored_end

        self.window_end = frontier
        self.backlog_target = frontier

        # A stored backlog moves the CEILING of this run's window down to where
        # the capped run got to, and leaves the floor alone. It is applied only
        # when it describes a drain this input could have written: the boundary
        # inside the window this run would otherwise ask about, and the target
        # at or after the boundary. Anything else came from somewhere else, and
        # the safe reading of it is that there is no drain, which falls back to
        # the ordinary window and duplicates rather than skips.
        #
        # The same three conditions are in intel_checkpoint.read_backlog, and
        # they are here as well ON PURPOSE. This class accepts anything with
        # read() and write(), so the store is not the only thing that can hand
        # it a position, and a window bound is not a value to take on trust from
        # a caller.
        if (
            backlog_end is not None
            and backlog_target is not None
            and self.window_start <= backlog_end <= frontier
            and backlog_end <= backlog_target
        ):
            self.draining = True
            self.window_end = backlog_end
            self.backlog_target = backlog_target
            self._stored_backlog_end = backlog_end

        if self.window_start > self.window_end or (
            self.window_start == self.window_end and not self.draining
        ):
            # Nothing to ask about. Three ways to get here and one behaviour:
            # two runs inside the same second, a checkpoint written by a search
            # head whose clock is ahead of this one, and a stanza whose lag
            # buffer is longer than the time since the last run. None is a fault
            # and none is a reason to spend a request, and the checkpoint is
            # left alone rather than moved backwards.
            #
            # A DRAIN IS EXEMPT FROM THE EQUAL CASE, which is not a nicety: a
            # capped run whose oldest emitted artifact sits at the window floor
            # leaves a boundary equal to the floor, and refusing a zero-wide
            # window there would leave that remainder unpulled for good. The
            # window is one instant, both ends inclusive, and the digest list is
            # what keeps it from re-emitting.
            return 0

        self.query = build_query(
            self.families,
            self.tags,
            self.min_polyscore,
            self.window_start,
            self.window_end,
        )

        completed = self._walk(emit, self._known_digests)

        if self.advance_checkpoint and self.checkpoint is not None:
            self._advance(completed)

        return self.emitted

    def _advance(self, completed):
        """Write the checkpoint this run earned, if it earned one.

        Two shapes and no others, and the module docstring argues both:

          * a run that covered its window whole stores the target and clears
            the backlog, so the next window is an ordinary one;
          * a run that stopped at its cap stores the unchanged floor plus the
            boundary the next window closes at.

        Everything else writes nothing, which is what this input did for every
        outcome before the backlog existed.
        """
        if self.checkpoint_read_failed:
            # Unreachable through run(), which returns before the walk on a
            # failed read. Stated anyway, because this method is the one that
            # can overwrite a real stored position with a fresh-install one and
            # a guard on the way in costs nothing.
            return

        if completed:
            self.checkpoint_written = self.checkpoint.write(
                self.stanza,
                self.backlog_target,
                self.digests,
                self.emitted,
                backlog_end=None,
                backlog_target=None,
            )
            return

        boundary = self._backlog_boundary()
        if boundary is None:
            return

        # The digests are UNIONED with the ones this run started from when the
        # boundary has not moved, which happens when a single second holds more
        # artifacts than one run may emit. Replacing them there would drop the
        # run before last out of the refusal list and emit its artifacts again.
        digests = set(self.digests)
        stalled = (
            self._stored_backlog_end is not None
            and boundary >= self._stored_backlog_end
        )
        if stalled:
            digests |= self._known_digests

        if len(digests) > intel_checkpoint.MAX_DIGESTS:
            # THE UNION IS BIGGER THAN THE DOCUMENT MAY CARRY, so this second
            # cannot be drained. QA found the loop it produces, and it is the
            # worst shape a bounded feed can take.
            #
            # One second holding more artifacts than max_artifacts_per_run
            # pins the boundary there: every run emits a capful, unions its
            # digests with the stored list, and join_digests() keeps the
            # lexically smallest MAX_DIGESTS of them and drops the rest with
            # no complaint. The dropped digests are the ones that would have
            # refused the artifacts the next run emits, so the next run emits
            # them again, and the boundary never moves. Duplicate events and
            # four metered requests, every interval, for good.
            #
            # So the drain gives up on that second and advances past it: the
            # boundary becomes the instant BELOW it, which is the next window's
            # inclusive ceiling, and the drain carries on through the older part
            # of the window it was already working through. What is lost is
            # whatever that one second still held, which is bounded by a second
            # and is counted here and logged below; what is bought is a drain
            # that terminates. Raising MAX_DIGESTS moves the same loop to a
            # busier second rather than closing it, which is why the ceiling is
            # not the lever. Decision D26.
            #
            # The digests written are this run's own. The next window ends
            # below the second they came from, so none of them can repeat in
            # it, and the list is the shape every other write has rather than a
            # special case.
            self.digest_overflow += 1
            boundary = float(self._stored_backlog_end or boundary) - 1.0
            digests = set(self.digests)
            ps_log.warning(
                LOG_COMPONENT,
                "backlog",
                "degraded",
                reason=DIGEST_LIST_FULL,
                limit=intel_checkpoint.MAX_DIGESTS,
            )
            if boundary < self.window_start:
                # The over-full second is the floor of the window itself, so
                # there is nothing older left to drain and nothing to advance
                # to. The backlog is cleared instead, which puts the stanza
                # back on ordinary windows.
                self.backlog_written = None
                self.checkpoint_written = self.checkpoint.write(
                    self.stanza,
                    self.backlog_target,
                    digests,
                    self.emitted,
                    backlog_end=None,
                    backlog_target=None,
                )
                return

        self.backlog_written = boundary
        self.checkpoint_written = self.checkpoint.write(
            self.stanza,
            self.window_start,
            digests,
            self.emitted,
            backlog_end=boundary,
            backlog_target=self.backlog_target,
        )

    def _backlog_boundary(self):
        """Return the instant the next window must close at, or None.

        None is the refusal, and there are four of them. Each is a case where
        the newest-first ordering argument does not support advancing anything,
        so the run falls back to what this input used to do for every capped
        run: leave the checkpoint alone and re-cover the window.
        """
        if not self.limit_reached:
            # The walk stopped for a reason that is not the cap: a failure, an
            # unusable cursor, or a repeated one. A page that was never seen
            # says nothing about what is older than what was.
            return None
        if self.last_failure is not None:
            return None
        if self.emitted <= 0 or self.oldest_emitted is None:
            # Nothing was emitted, or nothing emitted carried a readable
            # created time, so there is no boundary to store.
            return None
        if self.undated or self.out_of_order:
            return None

        # Rounded UP to a whole second, because the query renders its bounds at
        # second resolution: a bound rounded down could exclude an artifact
        # inside the same second that has not been emitted. Never above this
        # run's own window end, so the next window cannot be wider than this
        # one and the drain cannot fail to terminate.
        boundary = float(math.ceil(self.oldest_emitted))
        return min(boundary, float(self.window_end))

    def _walk(self, emit, known_digests):
        """Walk pages until the cap, the last page, or a failure.

        Returns True when the walk finished for a reason that means the window
        was covered WHOLE, which is the only condition under which the caller
        may advance the window end. Reaching the cap returns False, because
        artifacts inside the window were left unpulled.

        False is not the end of the story any more. The caller reads
        `limit_reached` to tell a capped walk apart from a failed one, and a
        capped walk still moves the drain boundary forward so the next run asks
        about the remainder instead of asking the same question again. See
        _advance() and the capped-run section of the module docstring.
        """
        offset = None
        while True:
            if self.pages >= MAX_PAGES_HARD_CAP:
                # The loop's own ceiling, independent of the artifact cap. A
                # platform answering has_more with a cursor that never advanced
                # would otherwise spend requests until splunkd killed the
                # process, and a killed input reports nothing at all.
                self.limit_reached = True
                return False

            remaining = self.max_artifacts - self.emitted
            if remaining <= 0:
                self.limit_reached = True
                return False

            payload = self._request(min(self.page_size, remaining), offset)
            if payload is None:
                return False

            self.pages += 1
            items = read_result_list(payload)

            for item in items:
                if self.emitted >= self.max_artifacts:
                    self.limit_reached = True
                    return False
                self._offer(emit, item, known_digests)

            if not read_has_more(payload):
                # The platform says this was the last page. The window is
                # covered and the checkpoint may advance.
                return True

            next_offset = read_offset(payload)
            if next_offset is None or next_offset == offset:
                # has_more with no usable cursor, or the same cursor twice.
                # Either is a shape this app cannot walk, and continuing would
                # re-request the page just paid for. Not covered: the next run
                # asks about the window again.
                self.last_failure = "UnusableCursor"
                return False
            offset = next_offset

    def _request(self, limit, offset):
        """Ask for one page. Returns the payload, or None on a failure.

        The one place in this module that spends anything.
        """
        try:
            self.requests += 1
            return self.client.search_metadata(
                self.query,
                community=self.community_name,
                offset=offset,
                limit=limit,
            )
        except AuthenticationError as error:
            # Not per page. Every subsequent request carries the same rejected
            # credential, so the walk stops here and the operator gets one line
            # rather than one per page.
            self.authentication_failed = True
            self.last_failure = type(error).__name__
            ps_log.warning(
                LOG_COMPONENT, "search", "error", reason=type(error).__name__
            )
            return None
        except Exception as error:
            self.last_failure = type(error).__name__
            ps_log.warning(
                LOG_COMPONENT, "search", "error", reason=type(error).__name__
            )
            return None

    def _offer(self, emit, item, known_digests):
        """Emit one artifact, unless it has already been emitted."""
        fields = build_event_fields(item)
        if fields is None:
            # No readable digest. Counted rather than ignored: the only way to
            # get one is a shape change, and an operator should see it on the
            # finish line instead of wondering why a page of fifty produced
            # forty-nine events.
            self.unreadable += 1
            return

        digest = fields[SHA256_FIELD]
        if digest in self.digests or digest in known_digests:
            self.duplicates += 1
            return

        self.digests.add(digest)
        emit(fields)
        self.emitted += 1
        self._record_position(item)

    def _record_position(self, item):
        """Track where in the stream this run has reached.

        Two facts come out of this and both feed _backlog_boundary(): the
        oldest created time emitted, which is the boundary itself, and whether
        the stream ever went backwards, which is the ordering assumption the
        boundary rests on failing.

        THE ORDERING CHECK IS NOT A NICETY. The endpoint answers newest first
        today, which is what makes it safe for a capped run to advance: what was
        not reached is older than what was. If the platform changed to any other
        order, a boundary derived from the oldest emitted artifact would skip
        everything newer that had not been reached, and a skipped artifact is
        gone from the customer's index with nothing able to tell later. So a
        document arriving newer than one already emitted stops the advance,
        reports the run degraded, and puts a name on the finish line.
        """
        created = read_created_epoch(item)
        if created is None:
            # Emitted, but with nothing to place it in time. Counted, and it
            # refuses the advance for the same reason an out-of-order document
            # does: the boundary would claim to cover an artifact it cannot see.
            self.undated += 1
            return

        if self.oldest_emitted is None:
            self.oldest_emitted = created
            return

        if created > self.oldest_emitted:
            self.out_of_order += 1
            if self.last_failure is None:
                self.last_failure = "UnexpectedOrdering"
            return

        self.oldest_emitted = created

    # -- reporting -------------------------------------------------------

    @property
    def degraded(self):
        """True when anything went wrong that an operator should know about.

        `undated` is here for the same reason `unreadable` is: an artifact the
        input cannot place in time is a document shape nobody has recorded, and
        it stops a capped run advancing, so an operator watching a feed that has
        stopped moving should see the flag rather than infer it.

        `digest_overflow` is here because it is the one path in this input that
        skips artifacts on purpose. It is bounded by a second and it is what
        keeps a drain terminating, but an operator whose feed did that should
        see it on the finish line rather than find it in a warning line later.
        """
        if self.last_failure is not None or self.unreadable or self.undated:
            return True
        if self.digest_overflow:
            return True
        if self.checkpoint is not None and getattr(
            self.checkpoint, "degraded", False
        ):
            return True
        return False


# ---------------------------------------------------------------------------
# The splunkd seam
# ---------------------------------------------------------------------------


def build_service(metadata):
    """Return a splunklib service scoped to this app.

    NOT `Script.service`, and the difference is not cosmetic: the base class
    builds its service with no app namespace, and everything this input needs
    is a namespaced object. The credential is in this app's storage/passwords,
    the checkpoint is in this app's KV store, and the community setting is in
    this app's conf file. A default-namespace service answers 404 for all three
    on a healthy install, which reads as "there is nothing to pull".

    The construction is ps_splunkd.build_service, which the task poller and the
    detonate alert action also use, for the reason decision D15 records: two
    copies of that constructor is how one of them ends up in the default
    namespace.
    """
    return ps_splunkd.build_service(
        metadata["server_uri"], metadata["session_key"], app=APP_NAME
    )


def build_event(stanza, fields, sourcetype=SOURCETYPE):
    """Return one splunklib Event for one artifact. Pure apart from the clock.

    NO INDEX IS SET HERE. The destination is the stanza's own `index` setting
    in inputs.conf, which is the standard way a Splunk input names its index
    and the only one an operator can change without editing the app. Setting it
    in code would silently override what they typed in the form.

    The sourcetype IS set here, and the reason is on the SOURCETYPE constant:
    props.conf keys its extraction on the exact string, so making it structural
    is what stops an edited conf turning every event into unparsed JSON.

    The event time is deliberately not taken from the artifact. `first_seen` is
    when the platform first saw the file, which can be months before the pull,
    and using it as the event time would file today's intel under a date the
    customer's retention may already have passed. props.conf carries the
    timestamp fields so an analyst can search on either.
    """
    event = Event()
    event.stanza = stanza
    event.sourcetype = sourcetype
    event.time = time.time()
    event.data = _dumps(fields)
    return event


def _dumps(fields):
    """Return one event's payload as JSON.

    Sorted keys, so two events describing the same artifact are byte identical
    and a diff between two runs is a real difference. Separators without spaces
    for the same reason v1's commented-out attempt at it wanted them: an event
    is a line in an index, not a document to read.
    """
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def resolve_community(service, stanza_community):
    """Return the community one run scopes its search to, or None.

    A stanza's own setting wins outright and costs nothing to apply. Otherwise
    bin/community.py's rule answers, which may cost one cached whois call, and
    None from here means the client's own configured default.

    NO COMMUNITY NAME REACHES THE LOG. community.resolve already holds that
    line and says why: a community is the customer's own scoping, in the same
    class as an indicator, and ps_log has no key it could travel under.
    """
    if stanza_community is not None:
        return stanza_community
    try:
        resolution = community.resolve(
            service, client_builder=lambda: get_client(service)
        )
    except Exception as error:
        ps_log.warning(
            LOG_COMPONENT, "community", "degraded", reason=type(error).__name__
        )
        return None
    return resolution.community


def pull_once(service, stanza, parameters, emit, now=None):
    """Run one cycle for one stanza and write one finish line.

    The whole of what an input invocation does for one stanza, with the splunkd
    handshake lifted off it, so a test drives this with a fake service and
    bin/cmd_sync.py drives it with a real one and a different sink.

    :param emit: a callable taking one mapping of event fields.
    :return: the IntelPuller, or None when the app is not configured.
    """
    timer = ps_log.Timer()
    ps_log.info(LOG_COMPONENT, "start", "ok")

    community_name = resolve_community(
        service, read_community_argument(parameters)
    )

    try:
        client = get_client(service, community=community_name)
    except ClientConfigurationError:
        # CONSTRAINT C8, AND ZERO NETWORK CALLS ON THE WAY OUT. An unconfigured
        # app is the ordinary state of a fresh install. One line an operator can
        # search for, no stack trace, and no request. The message is not logged
        # because it belongs to the setup page and ps_log has no key it could
        # travel under.
        ps_log.warning(
            LOG_COMPONENT,
            "finish",
            "refused",
            reason="ClientConfigurationError",
            duration_ms=timer.duration_ms,
        )
        return None

    checkpoint = intel_checkpoint.IntelCheckpoint(service, now=now)
    puller = IntelPuller(
        client,
        checkpoint,
        stanza,
        families=read_families_argument(parameters),
        tags=read_tags_argument(parameters),
        min_polyscore=read_min_polyscore(parameters),
        lookback_minutes=read_lookback_minutes(parameters),
        max_artifacts=read_max_artifacts(parameters),
        lag_seconds=read_lag_seconds(parameters),
        community_name=community_name,
        now=now,
    )
    puller.run(emit)

    ps_log.info(
        LOG_COMPONENT,
        "finish",
        "degraded" if puller.degraded else "ok",
        records=puller.emitted,
        lookups=puller.requests,
        pages=puller.pages,
        duplicates=puller.duplicates,
        cache_stores=1 if puller.checkpoint_written else 0,
        cache_degraded=checkpoint.degraded,
        limit=puller.max_artifacts,
        limit_reached=puller.limit_reached,
        reason=puller.last_failure,
        duration_ms=timer.duration_ms,
    )
    return puller


class IntelPullScript(Script):
    """The splunkd entry point. Everything testable is above this line."""

    def get_scheme(self):
        """Declare the input kind and its six arguments.

        `use_external_validation` is on so that a cap above the hard cap or a
        floor outside 0 to 1 is reported when an operator saves the input,
        rather than being silently clamped on the next run.
        `use_single_instance` is off: each stanza gets its own process, which is
        what keeps one broken stanza from taking the others down with it and
        what lets two stanzas pull two communities into two indexes.
        """
        scheme = Scheme(SCHEME_TITLE)
        scheme.description = SCHEME_DESCRIPTION
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        for name, title, description, data_type in (
            (
                FAMILIES_ARGUMENT,
                "Malware families",
                "Comma separated malware family names, for example "
                "emotet,ryuk. At most {0} are used. Leave both this and tags "
                "blank to pull the {1} feed.".format(MAX_FAMILIES, DEFAULT_TAG),
                Argument.data_type_string,
            ),
            (
                TAGS_ARGUMENT,
                "Tags",
                "Comma separated tag values, for example "
                "sector:healthcare,ransomware. At most {0} are used.".format(
                    MAX_TAGS
                ),
                Argument.data_type_string,
            ),
            (
                MIN_POLYSCORE_ARGUMENT,
                "Minimum PolyScore",
                "Only artifacts scoring at or above this are pulled. Above 0 "
                "and at most 1. Defaults to {0}, the score this app bands "
                "malicious.".format(DEFAULT_MIN_POLYSCORE),
                Argument.data_type_number,
            ),
            (
                LOOKBACK_MINUTES_ARGUMENT,
                "First window, in minutes",
                "How far back the FIRST run reaches. Later runs start where "
                "the last one ended. Defaults to {0}, and cannot exceed "
                "{1}.".format(DEFAULT_LOOKBACK_MINUTES, MAX_LOOKBACK_MINUTES),
                Argument.data_type_number,
            ),
            (
                MAX_ARTIFACTS_ARGUMENT,
                "Maximum artifacts per run",
                "Most events one run may write. Artifacts above the cap are "
                "left for the next run. Defaults to {0}, and cannot exceed "
                "{1}. Every page of results is a metered API request.".format(
                    DEFAULT_MAX_ARTIFACTS, MAX_ARTIFACTS_HARD_CAP
                ),
                Argument.data_type_number,
            ),
            (
                LAG_SECONDS_ARGUMENT,
                "Indexing lag buffer, in seconds",
                "How far behind the clock each window closes. An artifact is "
                "stamped when the platform takes it and becomes searchable a "
                "little later, so a window that ended at the clock would skip "
                "whatever was not yet searchable. Defaults to {0}, may be 0, "
                "and cannot exceed {1}.".format(
                    DEFAULT_LAG_SECONDS, MAX_LAG_SECONDS
                ),
                Argument.data_type_number,
            ),
            (
                COMMUNITY_ARGUMENT,
                "Community",
                "The PolySwarm community to pull from. Leave blank to use the "
                "community the app resolves for this account.",
                Argument.data_type_string,
            ),
        ):
            argument = Argument(name)
            argument.title = title
            argument.description = description
            argument.data_type = data_type
            argument.required_on_create = False
            argument.required_on_edit = False
            scheme.add_argument(argument)

        return scheme

    def validate_input(self, definition):
        """Refuse the values whose clamped form is not what was asked for.

        The refusal is the point. An operator typing 5000 into the cap is
        asking for something the app will not do, and clamping it silently
        teaches them it worked. Same for a floor of 5, which would match
        nothing, and a floor of 0, which would match everything.

        The families and the tags are refused here for a related reason and a
        different mechanism: the query escapes them either way, so what a
        refusal buys is telling the operator, at the point they can still fix
        it, that the character they typed will be matched literally and will
        match nothing. See the block above LUCENE_TERM_SPECIALS.
        """
        parameters = definition.parameters

        for name in read_families_argument(parameters):
            if not FAMILY_ALLOWED_RE.match(name):
                raise ValueError(
                    "{0} may only contain letters, digits, dots, underscores "
                    "and hyphens. {1} is not one of those, and a family name "
                    "carrying it is matched as literal text rather than as a "
                    "query, which pulls nothing.".format(
                        FAMILIES_ARGUMENT, _first_refused_family_character(name)
                    )
                )

        for tag in read_tags_argument(parameters):
            for character in tag:
                if character in TAG_REFUSED_CHARACTERS:
                    raise ValueError(
                        "{0} cannot contain {1}. A tag is matched as a quoted "
                        "phrase, and that character ends the phrase rather "
                        "than being searched for.".format(
                            TAGS_ARGUMENT, _quote_character(character)
                        )
                    )

        for name, ceiling in (
            (MAX_ARTIFACTS_ARGUMENT, MAX_ARTIFACTS_HARD_CAP),
            (LOOKBACK_MINUTES_ARGUMENT, MAX_LOOKBACK_MINUTES),
        ):
            raw = parameters.get(name)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                value = int(str(raw).strip())
            except (TypeError, ValueError):
                raise ValueError("{0} must be a whole number.".format(name))
            if value < 1:
                raise ValueError(
                    "{0} must be at least 1. Disable the input instead of "
                    "setting it to zero.".format(name)
                )
            if value > ceiling:
                raise ValueError(
                    "{0} cannot exceed {1}.".format(name, ceiling)
                )

        # The lag buffer is validated separately from the two above because its
        # floor is 0 rather than 1, and zero is a coherent request here: close
        # the window at the clock. See read_lag_seconds().
        raw = parameters.get(LAG_SECONDS_ARGUMENT)
        if raw is not None and str(raw).strip() != "":
            try:
                value = int(str(raw).strip())
            except (TypeError, ValueError):
                raise ValueError(
                    "{0} must be a whole number of seconds.".format(
                        LAG_SECONDS_ARGUMENT
                    )
                )
            if value < 0:
                raise ValueError(
                    "{0} cannot be negative. A window cannot close in the "
                    "future.".format(LAG_SECONDS_ARGUMENT)
                )
            if value > MAX_LAG_SECONDS:
                raise ValueError(
                    "{0} cannot exceed {1}.".format(
                        LAG_SECONDS_ARGUMENT, MAX_LAG_SECONDS
                    )
                )

        raw = parameters.get(MIN_POLYSCORE_ARGUMENT)
        if raw is not None and str(raw).strip() != "":
            try:
                score = float(str(raw).strip())
            except (TypeError, ValueError):
                raise ValueError(
                    "{0} must be a number between 0 and 1.".format(
                        MIN_POLYSCORE_ARGUMENT
                    )
                )
            if score <= MIN_POLYSCORE_FLOOR or score > MIN_POLYSCORE_CEILING:
                raise ValueError(
                    "{0} must be above {1} and at most {2}. A floor of {1} "
                    "pulls every artifact the platform holds.".format(
                        MIN_POLYSCORE_ARGUMENT,
                        MIN_POLYSCORE_FLOOR,
                        MIN_POLYSCORE_CEILING,
                    )
                )

    def stream_events(self, inputs, ew):
        """Run one cycle per configured stanza.

        One event per artifact, and NOTHING ELSE IS EVER WRITTEN HERE. The
        writer is handed a mapping that came out of build_event_fields() and
        from nowhere else, which is constraint C6 held structurally: there is no
        expression in this method that could put a failure into the index.
        """
        service = build_service(self._input_definition.metadata)
        for stanza, parameters in (inputs.inputs or {}).items():
            pull_once(
                service,
                stanza,
                parameters,
                lambda fields, name=stanza: ew.write_event(
                    build_event(name, fields)
                ),
            )


def main(argv=None):
    """Console entry point invoked by splunkd."""
    return IntelPullScript().run(argv if argv is not None else sys.argv)


if __name__ == "__main__":
    sys.exit(main())
