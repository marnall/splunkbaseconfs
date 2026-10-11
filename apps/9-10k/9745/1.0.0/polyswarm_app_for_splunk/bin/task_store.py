"""KV store state for the sandbox detonation surface.

Two collections, and they are two rather than one for the reason
default/collections.conf already gives about the usage pair: a lookup
definition returns every document in the collection it is pointed at, so a
cached providers blob living beside the task rows would arrive in the tasks tray
as a row with no task on it.

    ps_sandbox_tasks      one document per detonation. Design 4.3's task table.
    ps_sandbox_providers  one document, the cached providers and VMs list.

THIS IS NOT A CACHE, AND THAT IS THE DIFFERENCE FROM verdict_cache.py
---------------------------------------------------------------------
bin/verdict_cache.py opens with the sentence that the cache is an optimisation
and never a correctness dependency, and every branch in it is written to keep
that true. Half of this module is the same kind of thing and half of it is not,
so the difference is stated here rather than left to be inferred:

  * **The providers cache IS an optimisation.** A miss costs one live providers
    call. A broken collection reads exactly like an empty one.
  * **A task row IS NOT.** It is the only record that a detonation was bought.
    The platform's own listing endpoint for an account's tasks,
    /v3/sandbox/sandboxtask/my-tasks, HANGS (design section 0, item 5), so a
    task whose row is lost is a metered call the customer paid for that nothing
    in this app can ever find again. There is no second copy to fall back on.

So a failed task write still degrades rather than raising, because raising
after the spend would lose the analyst the task id as well as the row, which is
strictly worse. What it does instead is report the failure loudly: the flag on
this object is read by cmd_detonate, which puts a warning in front of the
analyst naming the task id that could not be stored. A silent degradation is
acceptable for a cache and is not acceptable here.

WHAT THE STATUS FIELD HOLDS, AND WHY THE MAPPING IS NOT STORED
--------------------------------------------------------------
The row carries the platform's status string verbatim: PENDING, STARTED,
SUCCEEDED, KNOWN_GOOD. The reading of it, "is this task finished", is applied
fresh at read time by map_status() below. That is decision D6's doctrine in a
second place: the platform's answer is stored and this app's interpretation of
it is applied by the current release, so a mapping change does not leave a
day's worth of rows carrying last release's reading.

Layering
--------
    map_status()          pure, no I/O: platform status to the shared reading
    is_terminal()         pure, no I/O
    read_providers()      pure, no I/O: the providers response to a mapping
    provider_slugs()      pure, no I/O
    vm_slugs()            pure, no I/O
    vm_supports_url()     pure, no I/O
    report_url_for()      pure, no I/O
    task_document_id()    pure, no I/O
    build_task_row()      pure, no I/O: a submit response to a task row
    TaskStore             the I/O seam, one instance per search
"""

import datetime
import json
import re
import time

import ps_log

APP_NAME = "polyswarm_app_for_splunk"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "task_store"

# The collections declared in default/collections.conf. One name, one home.
TASK_COLLECTION_NAME = "ps_sandbox_tasks"
PROVIDERS_COLLECTION_NAME = "ps_sandbox_providers"

# The KV store's own document id field.
ID_FIELD = "_key"

# ---------------------------------------------------------------------------
# The task row
# ---------------------------------------------------------------------------
#
# The first ten fields are the task table design section 4.3 asks for, and they
# are the tray's data source and the poller's worklist at the same time. The row
# is what a detonation leaves behind, so read the field list as a record of a
# purchase rather than as a convenience.

TASK_ID_FIELD = "task_id"
TARGET_FIELD = "target"
PROVIDER_FIELD = "provider"
VM_FIELD = "vm"
COMMUNITY_FIELD = "community"
STATUS_FIELD = "status"
SUBMITTED_AT_FIELD = "submitted_at"
UPDATED_AT_FIELD = "updated_at"
SHA256_FIELD = "sha256"
REPORT_URL_FIELD = "report_url"

# THE FINDINGS, and they exist because the report is not fetched twice.
#
# A finished detonation answers with its whole sandbox report inline: two
# kilobytes of processes, dumped files, network requests and signatures in the
# recorded case. Storing that blob on the row was the alternative and was
# rejected, unlike decision D6's rule for the verdict cache, and the difference
# between the two cases is what makes it the right call here:
#
#   * The verdict cache stores the response whole because the cache exists to
#     answer the same question again without a request, so a field the app does
#     not read today is a field a later release reads for free.
#   * A task row is not a cache. Nothing re-reads it to avoid a request, the
#     report is available at its own portal page, and a KV store collection has
#     a 25GB ceiling shared with everything else on the search head. So the row
#     carries the findings a tray shows and a count for the two lists an analyst
#     asks "how many" about.
#
# What that costs, named rather than implied: a finding this app does not read
# today needs a poll to happen again before it appears, and a terminal row is
# never polled again. So the field list below is a decision about what a
# detonation is worth remembering, and adding to it later only populates rows
# detonated after the change.
ANALYSIS_SCORE_FIELD = "analysis_score"
TAGS_FIELD = "tags"
MALWARE_FAMILY_FIELD = "malware_family"
C2_IP_COUNT_FIELD = "c2_ip_count"
C2_IPS_FIELD = "c2_ips"
PROCESS_COUNT_FIELD = "process_count"

# THE POLLER'S OWN STATE, WHICH IS ALSO THE POLLER'S CHECKPOINT.
#
# Constraint C7 asks every modular input to keep a checkpoint and be safe to run
# twice. These two fields are that checkpoint, and there is deliberately no
# separate checkpoint document: the worklist is the collection, and the state
# worth remembering is per row rather than per run. A checkpoint file beside it
# would be a second source of truth about the same rows, and the failure it
# would introduce is the one that matters here, a run that believes it is
# up to date while a row sits unpolled forever.
#
#   poll_attempts  how many status requests this row has cost, successful or
#                  not. The index into the backoff schedule.
#   next_poll_at   epoch seconds before which the poller leaves this row alone.
#                  ABSENT MEANS DUE NOW, which is why a row written by the
#                  detonate command needs neither field: a fresh detonation is
#                  polled on the next run.
POLL_ATTEMPTS_FIELD = "poll_attempts"
NEXT_POLL_AT_FIELD = "next_poll_at"

# THE POLLER'S OWN VERDICT ON A ROW THE PLATFORM WILL NEVER SETTLE.
#
# These two fields are what stops a task being polled forever, and they are
# APP-OWNED STATE RATHER THAN A STATUS. The distinction is the rule map_status()
# is built on: an unrecognised or absent platform status must never settle a
# task, because settling it is what stops the poller and drops the row into the
# tray as finished. So the poller does not write a status word of its own,
# neither into `status` nor anywhere a status is read from. It writes this
# instead, beside the platform's own last word, which stays exactly as the
# platform said it.
#
#   poll_abandoned_at  epoch seconds the poller gave up on this row. Set only
#                      by bin/input_task_poller.py, absent on every row it has
#                      not given up on, and read by is_due(), which returns
#                      False when it is set. Nothing else in the app reads it,
#                      and nothing clears it: an operator who wants a row
#                      polled again clears the field, which is the same
#                      management-port edit as any other repair.
#   poll_not_found     how many CONSECUTIVE polls of this row came back with no
#                      payload, which is the platform answering 404 for a task
#                      it does not know or a status read that keeps failing. A
#                      poll that does come back with a payload resets it. Three
#                      in a row abandons the row: a task the platform cannot
#                      find will not become findable.
#
# WHY ABANDONMENT IS A FIELD AND NOT A DELETION. The row is a receipt for a
# metered detonation and my-tasks hangs, so deleting it would destroy the only
# record that the money was spent. The row stays, with what the platform last
# said about it, and stops costing requests.
POLL_ABANDONED_AT_FIELD = "poll_abandoned_at"
POLL_NOT_FOUND_FIELD = "poll_not_found"

# ---------------------------------------------------------------------------
# Where a detonation came from
# ---------------------------------------------------------------------------
#
# OPTIONAL, PROVENANCE ONLY, AND FIRST CLASS ON THE ROW. These six fields say
# which search job, which result and which Enterprise Security notable asked
# for a detonation. They are written by bin/action_detonate.py, which is the
# only surface that has any of them: a person typing polyswarmdetonate into a
# search bar is their own provenance.
#
# STORED, DECLARED AND PROJECTED. They are members of ALL_FIELDS below, so
# default/collections.conf declares a type for each of them and the
# ps_sandbox_tasks_lookup definition in default/transforms.conf projects them.
# | inputlookup ps_sandbox_tasks_lookup returns them, which is what lets an
# operator answer "which notable spent this detonation" in SPL rather than
# through the management port. That is the whole point of storing them: a
# detonation is the most expensive metered call in the product, and the
# question gets asked a week later by somebody who has a search bar and not a
# REST client.
#
# WHAT THEY ARE NOT IS A TRAY COLUMN. The Sandbox Tasks page lists its columns
# explicitly, and none of these six is among them. They are empty on every
# detonation that did not come from Enterprise Security, so tabling them would
# put six mostly empty columns beside the target and the findings an analyst is
# triaging. It is the same split poll_attempts and next_poll_at already sit on:
# stored and projected for an operator, left off the analyst's screen.
# tests/unit/test_dashboards.py pins that exclusion to exactly this tuple, so a
# seventh stored field has to be classified as a column or as not one rather
# than quietly falling off the page.
#
# STILL A TUPLE OF THEIR OWN, because it answers a different question from
# ALL_FIELDS. ALL_FIELDS is every field the row may carry. This is the set the
# alert action stamps, and nothing else stamps: bin/action_detonate.py writes
# exactly these, the tray excludes exactly these, and both read the name from
# here instead of listing six strings.
#
#   source_sid        the search job that fired the action.
#   source_rid        the result within that job the detonation came from.
#   source_orig_sid   the search that produced the result, when the result was
#                     itself produced by an earlier action.
#   source_orig_rid   the result within that earlier search.
#   notable_event_id  the Enterprise Security notable a detonation was started
#                     from.
#   notable_rule_id   the correlation rule that raised that notable.
SOURCE_SID_FIELD = "source_sid"
SOURCE_RID_FIELD = "source_rid"
SOURCE_ORIG_SID_FIELD = "source_orig_sid"
SOURCE_ORIG_RID_FIELD = "source_orig_rid"
NOTABLE_EVENT_ID_FIELD = "notable_event_id"
NOTABLE_RULE_ID_FIELD = "notable_rule_id"

ADAPTIVE_RESPONSE_FIELDS = (
    SOURCE_SID_FIELD,
    SOURCE_RID_FIELD,
    SOURCE_ORIG_SID_FIELD,
    SOURCE_ORIG_RID_FIELD,
    NOTABLE_EVENT_ID_FIELD,
    NOTABLE_RULE_ID_FIELD,
)

# In the order a row carries them, which is the order default/transforms.conf
# projects and default/collections.conf declares. A tuple rather than a set for
# exactly that reason.
#
# THE PROVENANCE FIELDS COME LAST, and the order is the row's history: the
# task's identity, what was detonated and where, the status and the two
# timestamps, the digest and the portal link, the findings the poller reads out
# of the report, the poller's own two checkpoint fields, then where the
# detonation was asked for. Appending them keeps every earlier field at the
# offset it already had, which matters because output_row() pads a row into
# this order and a search command's column order is this list.
#
# MEMBERSHIP HERE IS NOT THE SAME AS BEING A COLUMN ON A PAGE. Ten fields in
# this tuple are deliberately not on the Sandbox Tasks table: the poller's four
# state fields and, per the block above, the six provenance fields. What this
# list decides is what is stored, declared and readable.
#
# THE POLLER'S TWO ABANDONMENT FIELDS SIT WITH ITS OTHER TWO rather than at the
# end, because they are the same kind of thing and the tuple's order is the
# row's history. Everything ahead of them keeps the offset it had, and the
# provenance fields stay last, which is what tests/unit/test_action_detonate.py
# asserts about them.
ALL_FIELDS = (
    TASK_ID_FIELD,
    TARGET_FIELD,
    PROVIDER_FIELD,
    VM_FIELD,
    COMMUNITY_FIELD,
    STATUS_FIELD,
    SUBMITTED_AT_FIELD,
    UPDATED_AT_FIELD,
    SHA256_FIELD,
    REPORT_URL_FIELD,
    ANALYSIS_SCORE_FIELD,
    TAGS_FIELD,
    MALWARE_FAMILY_FIELD,
    C2_IP_COUNT_FIELD,
    C2_IPS_FIELD,
    PROCESS_COUNT_FIELD,
    POLL_ATTEMPTS_FIELD,
    NEXT_POLL_AT_FIELD,
    POLL_ABANDONED_AT_FIELD,
    POLL_NOT_FOUND_FIELD,
) + ADAPTIVE_RESPONSE_FIELDS

# Every field a stored row may carry that a later write must not throw away.
#
# READ BY build_updated_row AND NOTHING ELSE, and it is ALL_FIELDS because the
# provenance fields are in ALL_FIELDS now. The name stays because the reason
# stays: provenance is written once, at detonation, and is never re-answered by
# a status response, so the merge has to carry it forward the way it carries
# submitted_at forward. A row that lost it on the first poll would answer
# "which notable was this" for two minutes.
PRESERVED_FIELDS = ALL_FIELDS

# Document id prefix for a task row, and the id scheme behind it.
#
# THE ID IS THE TASK ID, NOT A DIGEST OF IT, which is the opposite of what
# verdict_cache.py does and the reason is the difference between the two keys. A
# cache key is an indicator: unbounded in length, the customer's data, and
# sometimes a URL with credentials in its query string, all of which is why that
# module digests it. A task id is the platform's own opaque handle, seventeen
# digits in the recording, ours as much as theirs, and it is the value the
# poller has in hand when it needs to find the row. Digesting it would make the
# collection unreadable to an operator for no gain.
#
# It reaches splunkd as a path segment, so it is validated rather than trusted:
# TASK_ID_RE below is what a document id may be built from, and anything else
# is refused with no write attempted.
TASK_DOCUMENT_ID_PREFIX = "task_"

# What a task id may contain to be usable as a document id. Deliberately
# narrower than the recorded value, which is digits only: letters, digits,
# underscore and hyphen cover a platform that changes its id format without
# opening a path-traversal or an encoding question.
TASK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# ---------------------------------------------------------------------------
# The report link
# ---------------------------------------------------------------------------
#
# THE PREFIX IS DERIVED FROM A RECORDING, NOT TYPED, AND THE WHOLE FORM IS
# UNVERIFIED. Decision D8 established the one portal URL this repository can
# point at: the permalink in tests/fixtures/search-hash-recorded.json, whose
# shape is /scan/results/file/<sha256>/<scan id> on polyswarm.network. The host
# and the path prefix up to the artifact identifier are therefore observed
# facts, and the trailing scan-id segment is dropped because a scan id cannot
# be derived from an artifact. Whether the portal serves the resulting
# two-segment form is NOT VERIFIED, exactly as D8 records for the portal
# workflow action, and it is the same outstanding C10 item.
#
# WHAT THIS IS NOT. It is not a sandbox report URL from the platform. The
# status response carries no link of any kind: the recorded final task holds
# the report inline under "report" and names its artifacts under
# "sandbox_artifacts", and neither is a URL a browser can open. So this field
# points at the artifact's page in the portal, which is where a person goes to
# read a detonation, and it is honest about being derived rather than returned.
# The day the platform returns a report link is the day this function reads it
# instead of building one.
PORTAL_ARTIFACT_URL_PREFIX = "https://polyswarm.network/scan/results/file/"

# What a sha256 has to look like before it is put in a URL. A row's sha256
# comes from the platform, but it lands in a link an analyst clicks, and a
# value that is not a hash has no business being pasted into a URL path.
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------
#
# MIRRORED, FIELD FOR FIELD, FROM THE PRODUCTION CLIENTS. This app is the
# fourth surface to poll a sandbox task and it must agree with the other three
# about what "finished" means. The sources are:
#
#     the browser extension:  src/core/tasks/store.ts, mapSandboxStatus()
#     the local API wrapper:  wrapper/wrapper_app/sandbox.py, map_sandbox_status()
#     the iOS app:            PolySwarmKit/Sources/Models/DetonationTask.swift
#
# all in the product apps repository. The lists below are those lists. A
# divergence here would not fail anything in this repository, which is exactly
# why the mirror is written down: the corpus fixture rule
# (tests/fixtures/README.md) exists for the same class of cross-product
# contract, and this one has no fixture to enforce it.
#
# THE RECOGNIZED-ARTIFACT SHORT CIRCUIT IS THE DEFECT THIS ENCODES. When the
# platform already knows the sample it answers KNOWN_* instead of booking VM
# time, and the task is over: live, an EICAR detonation settles on KNOWN_GOOD in
# seconds. Read as queued, those tasks spun until a hard timeout and then
# reported a failure for a detonation that had already succeeded. That happened
# in two shipped products before it was fixed in both.
#
# THE WORD IS NOT A VERDICT. KNOWN_GOOD and KNOWN_MALICIOUS both mean settled
# and neither one bands anything. A verdict comes from the artifact's score,
# through the enrichment path, and nothing in this module reads one.
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_RUNNING = "running"
STATUS_QUEUED = "queued"

# PUBLIC, AND NOT PRIVATE ANY MORE. The Sandbox Tasks tray applies this same
# reading in SPL, because a lookup returns the platform's word and a dashboard
# has no way to call map_status(). Three names rather than a comment is what
# lets tests/unit/test_dashboards.py assert the tray's case() expression
# against these lists word for word, the way the verdict thresholds are
# asserted against cmd_search. A word added here and not there would leave a
# tray counting a settled task as running with nothing failing anywhere.
DONE_STATUSES = frozenset(
    [
        "SUCCEEDED",
        "SUCCESS",
        "COMPLETED",
        "DONE",
        # Matched by name and never by prefix, so an unlisted KNOWN_* spelling
        # still reads as keep waiting rather than as finished.
        "KNOWN_GOOD",
        "KNOWN_BENIGN",
        "KNOWN_MALICIOUS",
        "KNOWN_BAD",
    ]
)

FAILED_STATUSES = frozenset(["ERROR", "CANCELLED", "CANCELED"])

RUNNING_STATUSES = frozenset(["RUNNING", "PROCESSING", "IN_PROGRESS"])

# The prefix half of the failed reading, named for the same reason the three
# sets above are public: the tray has to mirror it, and it cannot mirror a
# literal buried in a function body.
FAILED_STATUS_PREFIX = "FAIL"

# The two readings a poller stops on. queued and running are both in flight and
# are told apart only for what a tray displays.
TERMINAL_STATUSES = (STATUS_DONE, STATUS_FAILED)

# ---------------------------------------------------------------------------
# The providers cache
# ---------------------------------------------------------------------------

PROVIDERS_DOCUMENT_ID = "providers"

# 24 hours, matching the verdict cache's default lifetime for the same reason:
# the answer is a list of sandbox images, which changes on a release cadence
# rather than an hourly one, and the point of holding it is that validating a
# provider and a VM must not cost a request per detonation.
PROVIDERS_TTL_SECONDS = 86400

PAYLOAD_FIELD = "payload"
STORED_AT_FIELD = "stored_at"
TTL_FIELD = "ttl_seconds"

# The keys a providers response uses. Pinned by
# tests/fixtures/sandbox-providers-recorded.json.
ENVELOPE_FIELD = "result"
VMS_FIELD = "vms"
SUPPORTED_ARTIFACT_TYPES_FIELD = "supported_artifact_types"
SLUG_FIELD = "slug"

# The artifact type a URL detonation needs the VM to support.
URL_ARTIFACT_TYPE = "URL"

# The keys a task response uses, inside its config block. Pinned by
# tests/fixtures/sandbox-submit-recorded.json.
CONFIG_FIELD = "config"
CONFIG_TARGET_FIELD = "target"
CONFIG_PROVIDER_FIELD = "provider"
CONFIG_VM_FIELD = "vm"
RESPONSE_TASK_ID_FIELD = "id"
RESPONSE_STATUS_FIELD = "status"
RESPONSE_COMMUNITY_FIELD = "community"
RESPONSE_SHA256_FIELD = "sha256"

# WHEN THE PLATFORM SAYS THE TASK STOPS BEING ITS PROBLEM.
#
# Every recorded task response carries it, submit and status alike, about three
# hours after `created`:
#
#     "created":    "2026-09-08T16:46:40.995986+00:00"
#     "expiration": "2026-09-08T19:46:40.998378+00:00"
#
# READ, NEVER WRITTEN, AND NEVER A STATUS. It is not stored on the row and it
# is not mapped: a task past its expiration that the platform still calls
# PENDING is a task that will not settle, which is a statement about whether
# the poller should keep asking and not a verdict on the detonation. So it
# feeds bin/input_task_poller.py's abandonment rule and nothing else, and the
# `status` field keeps the platform's own last word.
#
# THREE HOURS IS THE PLATFORM'S NUMBER AND NOT THIS APP'S, which is the whole
# reason to prefer it to the app's own age ceiling: it is the platform saying
# when it stops working on the task, where the ceiling is this app guessing.
# The ceiling is the fallback for a response that carries no readable
# expiration, and a response with none is not a fault: two of the three
# recorded shapes here are enough to read one and nothing published says every
# task has one.
RESPONSE_EXPIRATION_FIELD = "expiration"

# The keys the sandbox report uses. Pinned by
# tests/fixtures/sandbox-status-final-recorded.json, which is a real finished
# detonation, so every name below is observed rather than read off an SDK. That
# is the difference between these and the family key decision D11 marks
# provisional, and it is why the extraction has no fallback spellings in it.
#
# TWO SCORES ARE IN THAT RECORDING AND ONLY ONE IS READ. The report carries
# report.analysis.score, and the task's config block carries
# config.traige_analysis_score, misspelling and all, with the same value. The
# report is what is read: the config block is the request as the platform
# recorded it, the report is the answer, and a misspelled key is a key that gets
# corrected one day. The static score, report.static.score, is a different
# measurement and is not read at all rather than being folded into one number.
RESPONSE_REPORT_FIELD = "report"
REPORT_ANALYSIS_FIELD = "analysis"
REPORT_SCORE_FIELD = "score"
REPORT_TAGS_FIELD = "tags"
REPORT_MALWARE_FAMILY_FIELD = "malware_family"
REPORT_C2_IPS_FIELD = "extracted_c2_ips"
REPORT_PROCESSES_FIELD = "processes"

# How a list of findings is written into one KV store string field.
#
# A DELIMITER RATHER THAN TYPOGRAPHY, and that is the difference from
# cmd_usage.COMMUNITIES_SEPARATOR, which joins with ", " because a person reads
# the result in a table cell. These two fields are read BACK, by the tray's
# findings strip, with split() in SPL, so the separator is part of a contract
# and a space in it would put a leading space on every family name after the
# first. The values are platform tags and family names, which carry no comma in
# any recording or SDK example.
LIST_SEPARATOR = ","

# splunkd answers a read for a document that is not there with a 404. On both
# collections that is an ordinary state, not a fault: no detonation has been
# stored yet, or the providers list has never been fetched.
NOT_FOUND_STATUSES = (404,)


# ---------------------------------------------------------------------------
# Status: pure
# ---------------------------------------------------------------------------


def map_status(raw):
    """Return the shared reading of one platform status string.

    See the block comment above for where the lists come from and why they are
    not this app's to choose. An unknown string, an empty one and None all read
    as queued, which means keep waiting: an unrecognised status must never
    settle a task, because settling it is what stops the poller and drops the
    row into the tray as finished.

    Note what the recording makes visible here. The live intermediate status is
    STARTED, in tests/fixtures/sandbox-status-pending-recorded.json, and STARTED
    is not in the running list, so it reads as queued. Both readings are in
    flight and the poller treats them identically, so the difference is
    cosmetic; adding STARTED to the running set would be a four-surface change
    and not a local one.
    """
    value = ("" if raw is None else str(raw)).strip().upper()
    if value in DONE_STATUSES:
        return STATUS_DONE
    if value.startswith(FAILED_STATUS_PREFIX) or value in FAILED_STATUSES:
        return STATUS_FAILED
    if value in RUNNING_STATUSES:
        return STATUS_RUNNING
    return STATUS_QUEUED


def is_terminal(status):
    """True when a mapped status needs no further polling."""
    return status in TERMINAL_STATUSES


def is_terminal_platform_status(raw):
    """True when a raw platform status is settled. map_status then is_terminal.

    The form a poller wants, kept as one function so a caller cannot map with
    one release's table and compare against another's.
    """
    return is_terminal(map_status(raw))


def read_expiration_epoch(payload):
    """Return a task response's `expiration` as epoch seconds, or None. Pure.

    See the note on RESPONSE_EXPIRATION_FIELD for what the field is and why it
    is read rather than stored.

    The platform sends `2026-09-08T19:46:40.998378+00:00`, which
    datetime.fromisoformat reads directly on every Python this app supports. A
    `Z` suffix is translated first, because fromisoformat did not accept one
    before Python 3.11 and this app's floor is 3.9, and a value with no offset
    is read as UTC, which is what every timestamp in the recordings carries.
    Same reading as input_intel_pull.read_created_epoch, for the same reason:
    one app, one way to read the platform's clock.

    None for everything unreadable, and unreadable is deliberately broad. The
    caller treats None as "the platform did not say", which falls back to the
    app's own age ceiling, so a shape nobody has recorded costs a later
    abandonment rather than an early one.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        return None
    value = body.get(RESPONSE_EXPIRATION_FIELD)
    if value is None or isinstance(value, bool) or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
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


# ---------------------------------------------------------------------------
# The providers response: pure
# ---------------------------------------------------------------------------


def unwrap(payload):
    """Return the body inside a v3 response envelope, or the payload itself.

    Recognised by the TYPE of the "result" value and never by the name alone,
    for the reason cmd_usage.unwrap carries: an object may hold its own
    "result" key.
    """
    if not isinstance(payload, dict):
        return None
    inner = payload.get(ENVELOPE_FIELD)
    if isinstance(inner, dict):
        return inner
    return payload


def read_providers(payload):
    """Return {provider slug: provider object} from a providers response.

    The one reader of the providers shape. Pinned by
    tests/fixtures/sandbox-providers-recorded.json, whose result is a MAPPING
    KEYED BY SLUG and not a list; the SDK confirms it from the other side, in
    resources.SandboxProvider.parse_result.

    Structurally tolerant and never inventive: an entry that is not a mapping
    is dropped, and an empty result reads as no providers rather than as an
    error. A caller that gets {} refuses to detonate, which is the safe
    direction: see cmd_detonate.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        return {}

    providers = {}
    for slug in body:
        entry = body[slug]
        if not isinstance(entry, dict):
            continue
        text = str(slug).strip()
        if not text:
            continue
        providers[text] = entry
    return providers


def provider_slugs(providers):
    """Return the provider slugs, sorted, from read_providers() output."""
    if not isinstance(providers, dict):
        return []
    return sorted(providers)


def vm_slugs(providers, provider_slug):
    """Return one provider's VM slugs, sorted.

    An unknown provider and a provider with no readable vms block both return
    an empty list. The caller cannot act on the difference: either way there is
    no VM to validate against.
    """
    if not isinstance(providers, dict):
        return []
    entry = providers.get(provider_slug)
    if not isinstance(entry, dict):
        return []
    vms = entry.get(VMS_FIELD)
    if not isinstance(vms, dict):
        return []
    return sorted(str(name).strip() for name in vms if str(name).strip())


def vm_supports_url(providers, provider_slug, vm_slug):
    """True when the named VM declares support for the URL artifact type.

    THIS IS THE GUARD THE RECORDING PAID FOR. triage's android-11-x64 declares
    supported_artifact_types ["FILE"], with no URL, so submitting a URL to it
    would book sandbox time for a run that cannot do the job and bill the
    customer for it. The check is possible only because the providers response
    carries the field, which is why the providers call is a hard prerequisite of
    a detonation rather than a nicety.

    An absent or unreadable supported_artifact_types returns False. Refusing on
    a shape we cannot read costs a customer one refused search with a message
    naming the reason; the other direction costs them a detonation.
    """
    if not isinstance(providers, dict):
        return False
    entry = providers.get(provider_slug)
    if not isinstance(entry, dict):
        return False
    vms = entry.get(VMS_FIELD)
    if not isinstance(vms, dict):
        return False
    vm = vms.get(vm_slug)
    if not isinstance(vm, dict):
        return False
    supported = vm.get(SUPPORTED_ARTIFACT_TYPES_FIELD)
    if not isinstance(supported, (list, tuple)):
        return False
    for value in supported:
        if isinstance(value, str) and value.strip().upper() == URL_ARTIFACT_TYPE:
            return True
    return False


# ---------------------------------------------------------------------------
# The task row: pure
# ---------------------------------------------------------------------------


def task_document_id(task_id):
    """Return the document id for one task, or None when it is unusable.

    None for anything TASK_ID_RE refuses, which the caller treats as "do not
    write". See the note on TASK_DOCUMENT_ID_PREFIX for why this is the id
    rather than a digest of it, and why it is validated instead of quoted.
    """
    if task_id is None:
        return None
    text = str(task_id).strip()
    if not TASK_ID_RE.match(text):
        return None
    return TASK_DOCUMENT_ID_PREFIX + text


def report_url_for(sha256):
    """Return the portal URL for an artifact, or None.

    See the block comment on PORTAL_ARTIFACT_URL_PREFIX: the host and prefix
    are derived from a recorded permalink, the two-segment form is unverified,
    and this is the artifact's page rather than a report link the platform
    returned.

    None whenever there is no readable sha256, which is the ordinary case at
    submit time: the recorded create and finalize responses carry sha256 null,
    because the platform has not hashed the uploaded content yet. The field
    fills in on the first poll that sees a digest.
    """
    if sha256 is None:
        return None
    text = str(sha256).strip()
    if not SHA256_RE.match(text):
        return None
    return PORTAL_ARTIFACT_URL_PREFIX + text.lower()


def read_scalar(value):
    """Return one field as a stripped string, or None when unreadable.

    A mapping, a list, a boolean and an absent value all read as nothing to
    show. A boolean is refused rather than rendered, for the reason
    cmd_usage.read_scalar gives: no field on this row is a flag, and a "true"
    in a provider column is worse than an empty one.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    return text or None


def read_nested_slug(config, name):
    """Return the slug out of a task config's provider or vm object.

    The recorded config carries these as objects, not strings:

        "provider": {"id": "2", "name": "triage", "slug": "triage", ...}
        "vm": {"slug": "windows11-21h2-x64", "os_name": "Windows 11 21h2 x64", ...}

    The slug is what is read, and "name" is not accepted as a fallback. They
    happen to be equal for the provider in the recording and are not for the
    VM, whose name is a display string, so a fallback would silently put a
    display string in a column the poller matches on. Decision D4's rule about
    invented aliases, in a second place.
    """
    if not isinstance(config, dict):
        return None
    entry = config.get(name)
    if isinstance(entry, dict):
        return read_scalar(entry.get(SLUG_FIELD))
    # A platform that starts sending a bare slug string is read too. That is
    # container tolerance, not a field alias.
    return read_scalar(entry)


def build_task_row(
    payload,
    target=None,
    provider=None,
    vm=None,
    submitted_at=None,
    updated_at=None,
):
    """Return the task row for one submit or status response.

    THE PLATFORM'S ANSWER WINS AND THE REQUEST IS THE FALLBACK. Every field
    that the response carries is read out of the response, and the values the
    caller asked for are used only where it does not. Two reasons, and the
    first is not tidiness:

      1. The platform RESOLVES some of what it is sent. The community is the
         clearest case: the app sends "default", exactly as the SDK does, and
         the recorded task came back on "mainnet1". A row echoing the request
         would record a community the detonation did not run in.
      2. A row must never be missing the identity of a detonation the customer
         paid for. So target, provider and vm fall back to what was asked,
         because a row with a task id and no idea what was detonated is a
         receipt with the amount torn off.

    Fields that are unreadable and have no fallback are OMITTED rather than
    emitted empty, matching cmd_search.build_output_fields and
    cmd_usage.read_identity: an absent column says the app has nothing, and a
    present blank one reads as the platform having answered with nothing.

    :param payload: the decoded submit or status response, enveloped or not.
    :param target: the URL that was submitted, as a fallback.
    :param provider: the provider slug that was requested, as a fallback.
    :param vm: the VM slug that was requested, as a fallback.
    :param submitted_at: epoch seconds the submission was made.
    :param updated_at: epoch seconds this row was built.
    :return: the row as a mapping. Never None; a row with no readable task id
        is returned without one and the caller refuses to store it.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        body = {}
    config = body.get(CONFIG_FIELD)
    if not isinstance(config, dict):
        config = {}

    row = {}

    task_id = read_scalar(body.get(RESPONSE_TASK_ID_FIELD))
    if task_id is not None:
        row[TASK_ID_FIELD] = task_id

    resolved_target = read_scalar(config.get(CONFIG_TARGET_FIELD))
    if resolved_target is None:
        resolved_target = read_scalar(target)
    if resolved_target is not None:
        row[TARGET_FIELD] = resolved_target

    resolved_provider = read_nested_slug(config, CONFIG_PROVIDER_FIELD)
    if resolved_provider is None:
        resolved_provider = read_scalar(provider)
    if resolved_provider is not None:
        row[PROVIDER_FIELD] = resolved_provider

    resolved_vm = read_nested_slug(config, CONFIG_VM_FIELD)
    if resolved_vm is None:
        resolved_vm = read_scalar(vm)
    if resolved_vm is not None:
        row[VM_FIELD] = resolved_vm

    community = read_scalar(body.get(RESPONSE_COMMUNITY_FIELD))
    if community is not None:
        row[COMMUNITY_FIELD] = community

    # Verbatim. See the module docstring: the reading is applied at read time
    # by map_status(), not baked into the row.
    status = read_scalar(body.get(RESPONSE_STATUS_FIELD))
    if status is not None:
        row[STATUS_FIELD] = status

    sha256 = read_scalar(body.get(RESPONSE_SHA256_FIELD))
    if sha256 is not None:
        row[SHA256_FIELD] = sha256
        report_url = report_url_for(sha256)
        if report_url is not None:
            row[REPORT_URL_FIELD] = report_url

    # EPOCH SECONDS, AND NOT THE PLATFORM'S "created". The response carries an
    # ISO 8601 timestamp with an offset, and every other timestamp this app
    # stores is epoch seconds: fetched_at, stored_at, last_run_at. A tray sorts
    # and ages these rows, so they are numbers, and mixing the two forms in one
    # app is how an age calculation ends up parsing a string on one row and
    # subtracting a float on another.
    if submitted_at is not None:
        row[SUBMITTED_AT_FIELD] = float(submitted_at)
    if updated_at is not None:
        row[UPDATED_AT_FIELD] = float(updated_at)

    return row


def read_string_list(value):
    """Return a list of readable strings out of a report list, or [].

    Pure. A mapping, a scalar, a boolean and an absent value all read as no
    entries, and an entry that is not a readable scalar is dropped rather than
    stringified: a dict inside a family list is a shape this module does not
    understand, and "{'name': 'x'}" in a tray column is worse than one fewer
    family.

    Order is the platform's. It is not sorted, because the report lists a
    primary family first in the SDK's own examples and re-ordering would throw
    that away for a tidiness nobody asked for.
    """
    if not isinstance(value, (list, tuple)):
        return []
    names = []
    for entry in value:
        text = read_scalar(entry)
        if text is not None and text not in names:
            names.append(text)
    return names


def read_report_fields(payload):
    """Return the findings a task row carries, out of a status response.

    THE ONE READER OF THE SANDBOX REPORT SHAPE, for the reason this module is
    the one reader of the task shape: four surfaces poll these tasks and a
    second reader here would be a second reading of the same recording.

    Pure, and structurally tolerant in the same direction as every other reader
    in this module: a field it cannot read is OMITTED rather than emitted as a
    zero, because a zero is an assertion. The distinction that matters most is
    between the two shapes of "nothing":

      * `extracted_c2_ips: []` is the report saying it extracted no C2
        addresses, which is a finding. So c2_ip_count is 0 and c2_ips is
        absent, since a count of zero has no names to list.
      * an absent or unreadable `extracted_c2_ips` is the app having nothing to
        say, so neither field appears at all.

    An empty `malware_family` behaves the same way and produces no field, which
    is exactly what the recorded final report yields: it detonated
    polyswarm.network, which is not malware and is attributed to no family.

    WHEN THIS RETURNS NOTHING, AND WHY THAT IS THE COMMON CASE. A status
    response carries `report: null` until the detonation finishes, and a
    recognised artifact settles on KNOWN_GOOD without booking a VM at all, so
    it never produces a report. Both read as no findings rather than as an
    error.

    :param payload: the decoded status response, enveloped or not.
    :return: a mapping of row fields, possibly empty. Never None.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        return {}
    report = body.get(RESPONSE_REPORT_FIELD)
    if not isinstance(report, dict) or not report:
        return {}

    fields = {}

    analysis = report.get(REPORT_ANALYSIS_FIELD)
    if isinstance(analysis, dict):
        score = _as_number(analysis.get(REPORT_SCORE_FIELD))
        if score is not None:
            fields[ANALYSIS_SCORE_FIELD] = score
        tags = read_string_list(analysis.get(REPORT_TAGS_FIELD))
        if tags:
            fields[TAGS_FIELD] = LIST_SEPARATOR.join(tags)

    families = read_string_list(report.get(REPORT_MALWARE_FAMILY_FIELD))
    if families:
        fields[MALWARE_FAMILY_FIELD] = LIST_SEPARATOR.join(families)

    addresses = report.get(REPORT_C2_IPS_FIELD)
    if isinstance(addresses, (list, tuple)):
        readable = read_string_list(addresses)
        # The count is the report's own list length and not the number of
        # entries this module could read. An address it refuses is still an
        # address the sandbox extracted, and a count that quietly dropped it
        # would understate the finding.
        fields[C2_IP_COUNT_FIELD] = len(addresses)
        if readable:
            fields[C2_IPS_FIELD] = LIST_SEPARATOR.join(readable)

    processes = report.get(REPORT_PROCESSES_FIELD)
    if isinstance(processes, (list, tuple)):
        fields[PROCESS_COUNT_FIELD] = len(processes)

    return fields


def build_updated_row(row, payload, updated_at=None):
    """Return one stored row brought up to date by a status response.

    The poller's half of build_task_row, and it is a separate function because
    it has one thing to do that build_task_row does not: keep what the stored
    row already knows. A status response is not a superset of a submit
    response. It carries no submitted_at, because that is this app's own
    measurement, and a row that lost it would sort to the epoch in a tray.

    THE PLATFORM'S ANSWER WINS, THE STORED ROW IS THE FALLBACK, which is
    build_task_row's rule with the request replaced by the row. So a status
    response that has stopped carrying a field leaves the previous value in
    place rather than blanking a column, and every field the response does
    carry is refreshed from it.

    THE PROVENANCE FIELDS ARE CARRIED FORWARD TOO, which is what PRESERVED_FIELDS
    is for. A status response cannot re-answer which notable a detonation came
    from, so those fields are only ever as durable as this merge makes them.

    THE TASK ID IS A GUARD AND NOT A FIELD. A response naming a different task
    than the row is refused outright, and the reason is what save_task does
    with the answer: the document id is built from the row's own task id, so
    writing a mismatched response would create a SECOND document under the
    other task's id, and leave the row that was actually polled untouched and
    stale forever. That is the worst available failure on this collection,
    because the platform's my-tasks listing hangs and nothing would ever
    reconcile the two.

    :param row: the stored row, as list_tasks() returns it.
    :param payload: the decoded status response, enveloped or not.
    :param updated_at: epoch seconds this update was built.
    :return: the merged row, or None when the response names another task.
    """
    if not isinstance(row, dict):
        return None

    stored_task_id = read_scalar(row.get(TASK_ID_FIELD))
    if stored_task_id is None:
        return None

    body = unwrap(payload)
    if isinstance(body, dict):
        answered_task_id = read_scalar(body.get(RESPONSE_TASK_ID_FIELD))
        if answered_task_id is not None and answered_task_id != stored_task_id:
            return None

    fresh = build_task_row(
        payload,
        target=row.get(TARGET_FIELD),
        provider=row.get(PROVIDER_FIELD),
        vm=row.get(VM_FIELD),
        updated_at=updated_at,
    )

    merged = dict(
        (name, row[name])
        for name in PRESERVED_FIELDS
        if name in row and row[name] is not None
    )
    merged.update(fresh)
    merged.update(read_report_fields(payload))

    # The response has no task id of its own on a not-found, and the row's is
    # what the document id comes from either way.
    merged[TASK_ID_FIELD] = stored_task_id
    return merged


def output_row(row):
    """Return one row padded to ALL_FIELDS, ready to be yielded.

    THE SAME BUG FIX cmd_usage.output_row CARRIES, and the same mechanism.
    splunklib's RecordWriter fixes a chunk's CSV header from the keys of the
    first record written into it, and every later record is projected onto that
    header. This command emits one row today, so the padding is not what saves
    it; the padding is what makes the emitted column set the command's declared
    field list rather than whatever the platform happened to answer with. A row
    that arrived without a sha256 must still name a sha256 column, or a tray
    built on the search output gains and loses columns per detonation.

    Nothing is invented. splunklib writes an absent key and a None value as the
    same two empty CSV cells, which Splunk reads as the field not being present
    on the event, so a padded row and an unpadded row produce identical bytes.
    The row written to the KV store is the UNPADDED one, because a stored
    document full of nulls is a different and worse thing.
    """
    padded = {}
    for name in ALL_FIELDS:
        padded[name] = row.get(name)
    return padded


def _as_number(value):
    """Return a JSON number as itself, or None for anything else.

    Deliberately narrower than _as_float below, and the difference is which
    direction the two are used in. _as_float reads a timestamp this app wrote,
    so it coerces whatever came back out of the KV store. This reads a
    measurement the platform sent, and a score arriving as the string "3" is a
    shape change rather than a value: storing it would put a string in a field
    collections.conf declares as a number, and inventing the coercion would
    hide the change from the one place that would otherwise notice it.

    A NaN or an infinity reads as nothing, because neither is a score.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def _as_float(value):
    """Return value as a float, or None when it is not a readable number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_not_found(error):
    """True when an exception from splunkd means the document is not there.

    Read by attribute rather than by exception class so this module does not
    import splunklib's binding layer, and so a test can drive the branch with a
    plain exception carrying a status. Same approach as verdict_cache and
    usage_store.
    """
    for attribute in ("status", "code"):
        if getattr(error, attribute, None) in NOT_FOUND_STATUSES:
            return True
    return False


def read_cached_providers(document, ttl_seconds=PROVIDERS_TTL_SECONDS, now=None):
    """Return the cached providers payload out of a raw document, or None.

    Pure. None for every unusable document, and unusable is deliberately
    broad: not a mapping, no readable write time, past its lifetime, or a
    payload that does not decode. All of them mean the same thing to the
    caller, which is one live providers call.

    A negative age is a document written in the future, by a corrected clock or
    by another search head, and reads as a miss for the reason
    verdict_cache.read_document gives: a document that cannot be aged would
    otherwise be immortal.
    """
    if not isinstance(document, dict):
        return None

    stored_at = _as_float(document.get(STORED_AT_FIELD))
    if stored_at is None:
        return None

    lifetime = _as_float(document.get(TTL_FIELD))
    if lifetime is None:
        lifetime = float(ttl_seconds)
    if lifetime <= 0:
        return None

    moment = time.time() if now is None else float(now)
    age = moment - stored_at
    if age < 0 or age > lifetime:
        return None

    raw = document.get(PAYLOAD_FIELD)
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------


class TaskStore(object):
    """Reads and writes the detonation collections for one search.

    One instance per search, holding the counters and the degradation flag a
    caller wants. Nothing at module scope, so state cannot outlive the search
    that made it.

    Every method swallows every exception from splunkd and none of them
    fabricates anything, which is not the catch-all C6 forbids: a failed read
    reports the same nothing an absent document would, and a failed write does
    nothing at all. What is different from verdict_cache is what the caller
    does about it, and the module docstring says why: a lost task row is a lost
    receipt for a metered call, so cmd_detonate turns a write failure into a
    warning an analyst reads rather than a log line nobody does.
    """

    def __init__(
        self,
        service,
        collection=TASK_COLLECTION_NAME,
        providers_collection=PROVIDERS_COLLECTION_NAME,
        providers_ttl_seconds=PROVIDERS_TTL_SECONDS,
        now=None,
    ):
        """
        :param service: the splunklib service a search command holds as
            self.service. None is accepted and disables both collections, which
            is what happens when the command is driven outside splunkd.
        :param collection: the task collection name, for tests.
        :param providers_collection: the providers collection name, for tests.
        :param providers_ttl_seconds: lifetime of the cached providers answer.
        :param now: a callable returning epoch seconds, for tests.
        """
        self._service = service
        self._collection = collection
        self._providers_collection = providers_collection
        self._now = time.time if now is None else now

        self.providers_ttl_seconds = float(providers_ttl_seconds)

        self.stores = 0

        # True once anything has failed. Read by the command, which reports it
        # to the analyst rather than only to the log.
        self.degraded = False

    # -- collections -----------------------------------------------------

    def _data(self, collection):
        """Return one collection's data endpoint, or None when unreachable."""
        if self._service is None:
            return None
        try:
            return self._service.kvstore[collection].data
        except Exception as error:
            self._degrade("open", error, collection)
            return None

    def _degrade(self, event, error, collection):
        """Record one failure: one flag, one log line, nothing raised.

        Only the exception's class name reaches the log, for the reason written
        out in ps_client.get_api_key: splunklib's binding layer quotes the HTTP
        exchange it attempted into its exception text, and a class name is the
        diagnostically useful half that cannot carry a payload.
        """
        self.degraded = True
        ps_log.warning(
            LOG_COMPONENT,
            event,
            "degraded",
            reason=type(error).__name__,
            collection=collection,
        )

    # -- task rows -------------------------------------------------------

    def save_task(self, row):
        """Store one task row. Returns True when it was written.

        NO LINE HERE CARRIES THE TARGET. The row holds the URL that was
        detonated, which is the customer's data, and ps_log has no key it could
        travel under. That is the whitelist working as intended and it is the
        same reasoning verdict_cache applies to an indicator.

        :param row: the row from build_task_row(). A row with no usable task id
            is refused, because a document id cannot be built from it and a
            random id would make the row invisible to the poller.
        :return: True when the document was written.
        """
        if not isinstance(row, dict):
            return False

        document_id = task_document_id(row.get(TASK_ID_FIELD))
        if document_id is None:
            ps_log.warning(LOG_COMPONENT, "task_write", "refused")
            self.degraded = True
            return False

        data = self._data(self._collection)
        if data is None:
            return False

        document = dict(
            (name, value) for name, value in row.items() if value is not None
        )
        document[ID_FIELD] = document_id

        try:
            # batch_save upserts, which is what a poller needs: the same task's
            # row is rewritten on every status change rather than added again.
            data.batch_save(document)
        except Exception as error:
            self._degrade("task_write", error, self._collection)
            return False

        self.stores += 1
        ps_log.debug(
            LOG_COMPONENT, "task_write", "ok", collection=self._collection
        )
        return True

    def list_tasks(self):
        """Return every stored task row, or [] when there are none to read.

        THE POLLER'S WORKLIST, AND THE REASON IT IS UNFILTERED.
        splunkd's KV store endpoint takes a query, so asking it for the
        non-terminal rows is possible and is not done. The terminal reading is
        map_status()'s, applied by the current release per this module's opening
        note, and a query would have to spell the same word lists into a JSON
        filter: two copies of a cross-product contract, one of them invisible
        to every test that checks the other. So the rows come back whole and
        the reading is applied in Python, where there is one of it.

        What that costs is proportionate to what the collection holds. One
        document per detonation, and a detonation is the most expensive metered
        call in the product: an Enterprise plan includes 30 a month. A
        collection sized in tens is read whole without apology, and the
        poller's own per-run ceiling is what bounds the requests that follow.

        [] covers all of: no rows, the collection is absent, the running user
        cannot read it, and splunkd is not answering. A caller cannot act on
        the difference, and none of them is a reason for an input to raise: the
        next run reads the same rows.
        """
        data = self._data(self._collection)
        if data is None:
            return []

        try:
            rows = data.query()
        except Exception as error:
            if _is_not_found(error):
                ps_log.debug(
                    LOG_COMPONENT,
                    "task_list",
                    "absent",
                    collection=self._collection,
                )
                return []
            self._degrade("task_list", error, self._collection)
            return []

        if not isinstance(rows, (list, tuple)):
            # splunkd answers this endpoint with a JSON array. Anything else is
            # a shape this module does not understand, and guessing at it would
            # be guessing about a purchase record.
            self._degrade("task_list", TypeError("not a list"), self._collection)
            return []

        return [row for row in rows if isinstance(row, dict)]

    def get_task(self, task_id):
        """Return one stored task row, or None.

        None covers all of: no such task, the collection is absent, the running
        role cannot read it, and splunkd is not answering. A caller cannot act
        on the difference.
        """
        document_id = task_document_id(task_id)
        if document_id is None:
            return None

        data = self._data(self._collection)
        if data is None:
            return None

        try:
            return data.query_by_id(document_id)
        except Exception as error:
            if _is_not_found(error):
                ps_log.debug(
                    LOG_COMPONENT,
                    "task_read",
                    "absent",
                    collection=self._collection,
                )
                return None
            self._degrade("task_read", error, self._collection)
            return None

    # -- the providers cache ---------------------------------------------

    def cached_providers(self):
        """Return the cached providers response, or None on a miss.

        A miss and a broken collection are the same answer, which is what makes
        this half of the module an optimisation: the caller makes one live
        providers call either way.
        """
        data = self._data(self._providers_collection)
        if data is None:
            return None

        try:
            document = data.query_by_id(PROVIDERS_DOCUMENT_ID)
        except Exception as error:
            if _is_not_found(error):
                # Nothing has been cached on this search head yet. The
                # ordinary first-run state, so no warning and no degradation.
                ps_log.debug(
                    LOG_COMPONENT,
                    "providers_read",
                    "absent",
                    collection=self._providers_collection,
                )
                return None
            self._degrade(
                "providers_read", error, self._providers_collection
            )
            return None

        payload = read_cached_providers(
            document, self.providers_ttl_seconds, now=self._now()
        )
        ps_log.debug(
            LOG_COMPONENT,
            "providers_read",
            "miss" if payload is None else "hit",
            collection=self._providers_collection,
        )
        return payload

    def store_providers(self, payload):
        """Cache one providers response. Returns True when it was written.

        A None payload is not stored. The providers list is a prerequisite of a
        detonation rather than an answer about an indicator, so there is no
        cached-not-found to hold here: caching "the platform told us nothing"
        would refuse every detonation for 24 hours on the strength of one bad
        request. That is the opposite of verdict_cache's write-through rule and
        the difference is that a cached not-found there saves a request, where
        one here would withhold a capability.
        """
        if payload is None:
            return False

        data = self._data(self._providers_collection)
        if data is None:
            return False

        try:
            encoded = json.dumps(payload)
        except (TypeError, ValueError) as error:
            self._degrade("providers_encode", error, self._providers_collection)
            return False

        document = {
            ID_FIELD: PROVIDERS_DOCUMENT_ID,
            PAYLOAD_FIELD: encoded,
            STORED_AT_FIELD: float(self._now()),
            TTL_FIELD: self.providers_ttl_seconds,
        }

        try:
            data.batch_save(document)
        except Exception as error:
            self._degrade("providers_write", error, self._providers_collection)
            return False

        ps_log.debug(
            LOG_COMPONENT,
            "providers_write",
            "ok",
            collection=self._providers_collection,
        )
        return True
