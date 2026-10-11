"""Alert action: PolySwarm Detonate.

Registered in default/alert_actions.conf as `[polyswarm_detonate]`, with its
configuration form in default/data/ui/alerts/polyswarm_detonate.html.

Design section 4.3 asks for an alert action and an ES adaptive response action
that "fire from correlation searches or manually from a notable". This file is
both: given the rows a saved search or a notable produced, detonate the URL out
of a configured field and write the task rows the tasks tray and the poller
read. The adaptive response half is a declaration rather than a second
mechanism, and it is `param._cam` in default/alert_actions.conf.

WHAT ENTERPRISE SECURITY ADDS TO THE PAYLOAD, AND WHERE THAT IS DOCUMENTED
--------------------------------------------------------------------------
Nothing about the invocation changes. Enterprise Security runs an adaptive
response action the same way splunkd runs any custom alert action, so the
contract below is the whole contract and this module still needs no library
from Enterprise Security to read it.

What is different is that the payload and the result rows carry identifiers
saying where the request came from, and those are worth keeping: a detonation
is metered, and "which notable spent this" is the question somebody asks a week
later. The fields, and the source each one was read from:

  * `sid`, on the payload. The search job that fired the action.
  * `result_id`, on the payload. The result within that job, present when
    splunkd invokes the action per result rather than per firing.
  * `rid`, `orig_sid`, `orig_rid`, on the RESULT ROW rather than the payload.
    `orig_sid` and `orig_rid` name the search and result that produced the row
    when the row was itself produced by an earlier action.
  * `event_id` and `rule_id`, on the result row when that row is an Enterprise
    Security notable: the notable itself and the correlation rule behind it.

Read out of Splunk's own common action model library, `cim_actions.py`, which
is the reference implementation of this contract and the place each field's
origin is unambiguous: `ModularAction.__init__` takes `sid` from the payload
settings, `ModularAction.update(result)` takes `orig_sid`, `orig_rid` and `rid`
from the result row and `result_id` from the settings, and `event_id` appears in
that library's own list of notable result fields. The copy read is the one
Splunk ships:

    https://github.com/splunk/pytest-splunk-addon/blob/main/deps/apps/Splunk_SA_CIM/lib/cim_actions.py

`rule_id` is documented as a notable field by Enterprise Security itself, in
the mapfields list on the page about creating notable events. The common action
model's own specification is quoted where it is used, in
default/alert_actions.conf.

**NO DEPENDENCY ON SA-Utils OR cim_actions.py, and that is a decision rather
than an omission.** Importing that library would tie this action to a package
that only exists on a search head with Enterprise Security installed, so the
action would stop working on plain Splunk Enterprise, which is where every
customer of this app starts. The library's value is its introspection events in
the `cim_modaction` index and the queueing model behind remote workers; neither
is something this action needs to write a task row. So the four payload fields
are read directly, absent ones stay absent, and the action behaves on plain
Splunk exactly as it did before any of this was added.

WHAT IT IS INVOKED WITH, AND WHY THAT CONTRACT IS WRITTEN DOWN HERE
-------------------------------------------------------------------
splunkd runs a custom alert action once per firing, as

    action_detonate.py --execute

with one JSON object on standard input. The keys this module reads are
`server_uri` and `session_key`, which are how it reaches splunkd at all,
`configuration`, which carries the parameters from the form, `results_file`,
the gzipped CSV of the search's results, and `sid` and `result_id`, which are
recorded on the task row as provenance and are read for nothing else.
`search_name` is read for nothing at all.

NONE OF THOSE REACHES A LOG. ps_log has no key for a search id, a result id or
a notable id, and it is not getting one: a scheduler sid and a correlation
rule id are the customer's own detection logic. They are written to the task
row, which lives in a collection the app's own metadata gates, and nowhere
else.

Two shapes of result arrive and both are handled. `results_file` is the whole
result set and is the ordinary case. A single `result` object appears in
Splunk's own documented payload as well, and reading it costs four lines, so a
payload carrying one row that way detonates it rather than reporting no rows.

**`--execute` is required.** splunkd passes it, and refusing without it is what
stops this file from doing anything when it is run by hand out of curiosity, or
by a future caller that has decided what the arguments mean for itself. A
detonation is not a thing to spend on an accident.

CONSTRAINT C11: THE CAP IS THE MOST IMPORTANT LINE IN THIS FILE
---------------------------------------------------------------
An alert fires on a schedule, over whatever the search matched, with nobody
watching. `polyswarmdetonate` answers that risk by refusing to loop at all: one
detonation per invocation, because a search command has nowhere to put a
confirmation. An alert action cannot use that answer, because the whole point of
attaching it to a correlation search is to act on what the search found, and it
has the same absence of a confirmation with a schedule on top.

So the cap is explicit, small, and enforced twice:

  * `max_detonations` is a parameter with a default of **one**. An operator who
    wants more asks for more, on a form that says what each one costs.
  * `MAX_DETONATIONS_HARD_CAP` is **five**, in this file, and a configured
    value above it is clamped rather than honoured. Five because an Enterprise
    plan includes thirty detonations a month: an alert firing hourly at five a
    time would spend a month's allowance before lunch, and the point of the
    hard cap is that no number typed into a form can do worse than that.

The rows above the cap are not detonated and the run says so on its finish
line. That is C11's refuse-rather-than-proceed shape: the alert does what it
was allowed to do and reports what it did not.

WHAT IT HOLDS IN MEMORY, AND WHY THE READ IS BOUNDED BY THE CAP
---------------------------------------------------------------
A correlation search can match tens of thousands of rows and the cap means at
most five of them are ever acted on, so the results file is read as a stream
and the reader keeps only what the run can still use: at most `max_detonations`
(URL, row) pairs and four integers. The file is still read to the end, because
the counts on the finish line are the whole of the report an operator gets, and
a count of rows above the cap that stopped counting when it ran out of room
would be a number nobody could act on. Reading to the end costs one pass over a
file splunkd has already written and holds nothing while it does it.

The one thing bounded past the cap is the duplicate check. Below the cap it is
exact, because the row that first carried a URL is the row credited with the
detonation. Past the cap the retained targets are the only URLs remembered, so
a URL appearing only among the rows above the cap is counted once per row
rather than once. Remembering every distinct URL instead is the unbounded
growth this reader exists to remove, and it grows with the search rather than
with the cap. The count that direction produces is an upper bound on what
raising the limit would buy rather than a number that could understate it, and
a row duplicating something actually detonated is still counted as a duplicate,
which is the case that would otherwise tell an operator to raise a limit that
would buy nothing.

**Defect class B8, and why this ships enabled.** An alert action that exists
spends nothing. It runs when somebody attaches it to a saved search, which is
the opt-in, and there is no correlation search in this package that uses it.
The shipped parameter defaults are the cheapest ones that work: one detonation,
from a field called `url`.

WHAT REACHES A LOG, AND WHAT CANNOT
-----------------------------------
One start line and one finish line through ps_log, with counts only. There is
no key on the whitelist for a URL, a saved search name, a task id or a session
token, so none of them can travel into a log line, and the assertions in
tests/unit/test_action_detonate.py are over the whole of stdout, stderr and the
log for a complete run rather than over one line at a time.

Errors go to stderr, which is where splunkd collects an alert action's output
and where the alert's own status message comes from. Every message written
there is either a literal in this file or a message from ps_client, which is
sanitized against the credential before it is raised. Nothing else is printed:
an unexpected exception is reported by its class name, for the reason
ps_client.get_api_key gives at length.

Importing this module is side effect free. It only runs when splunkd invokes it.
"""

import collections
import csv
import gzip
import json
import os
import sys

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import cmd_detonate
import community
import ps_log
import ps_splunkd
import task_store
from ps_client import ClientConfigurationError, ClientError, get_client

APP_NAME = "polyswarm_app_for_splunk"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "action_detonate"

# The stanza name in default/alert_actions.conf, which is also the base name of
# the configuration form under default/data/ui/alerts/. Splunk resolves the
# form by that name, so the two cannot drift apart without the form
# disappearing from the alert dialog.
ACTION_NAME = "polyswarm_detonate"

# The argument splunkd passes, and the one this file insists on. See the
# module docstring.
EXECUTE_ARGUMENT = "--execute"

# The parameters the form collects, their defaults, and the hard cap.
#
# THE HARD CAP IS THE C11 LINE. A configured value above it is clamped, so the
# ceiling is a property of this file rather than of a form somebody filled in.
FIELD_PARAMETER = "field"
DEFAULT_FIELD = "url"

MAX_DETONATIONS_PARAMETER = "max_detonations"
DEFAULT_MAX_DETONATIONS = 1
MAX_DETONATIONS_HARD_CAP = 5

# The payload keys this module reads. Named as constants because the payload is
# a contract with splunkd and a typo in one of them reads as an empty alert.
SERVER_URI_KEY = "server_uri"
SESSION_KEY_KEY = "session_key"
CONFIGURATION_KEY = "configuration"
RESULTS_FILE_KEY = "results_file"
SINGLE_RESULT_KEY = "result"

# The provenance keys. Named as constants for the same reason the five above
# are, and split into two groups because they arrive in two different places
# and getting that wrong reads as an empty column rather than as an error.
#
# On the payload:
SID_KEY = "sid"
RESULT_ID_KEY = "result_id"

# On the result row:
RID_FIELD = "rid"
ORIG_SID_FIELD = "orig_sid"
ORIG_RID_FIELD = "orig_rid"
EVENT_ID_FIELD = "event_id"
RULE_ID_FIELD = "rule_id"

# Splunk writes multivalue fields into a results CSV as a value plus a
# companion column with this prefix. The companion is skipped: a URL is one
# value, and a row whose field is genuinely multivalue is a row where the
# analyst's search, not this action, has to decide which URL was meant.
MULTIVALUE_PREFIX = "__mv_"


class PayloadError(Exception):
    """Raised when the invocation itself is unusable.

    Its own class so that every refusal in this module is testable without
    splunkd, and so the message an operator reads in the alert's status is
    written here rather than assembled from a traceback.
    """


# ---------------------------------------------------------------------------
# The payload: pure
# ---------------------------------------------------------------------------


def read_payload(stream):
    """Return the decoded payload object from a stream. Pure apart from the read.

    :raises PayloadError: if it is not a JSON object.
    """
    try:
        payload = json.load(stream)
    except ValueError:
        raise PayloadError(
            "The alert action payload was not readable JSON, so there is "
            "nothing to detonate. This is a Splunk invocation problem rather "
            "than a PolySwarm one."
        )
    if not isinstance(payload, dict):
        raise PayloadError(
            "The alert action payload was not a JSON object, so it carries no "
            "results and no session."
        )
    return payload


def read_configuration(payload):
    """Return the parameter mapping out of a payload. Pure.

    An absent or unreadable `configuration` reads as an empty mapping, which
    gives every parameter its default rather than refusing: the defaults are
    the cheapest values that work, so an alert whose configuration did not
    survive the round trip detonates one URL from a field called url rather
    than nothing at all.
    """
    if not isinstance(payload, dict):
        return {}
    configuration = payload.get(CONFIGURATION_KEY)
    if not isinstance(configuration, dict):
        return {}
    return configuration


def read_field_name(configuration):
    """Return the result field to take the URL from. Pure.

    Defaults to `url`. A blank or unreadable value takes the default rather
    than refusing, for the reason read_configuration gives.
    """
    if not isinstance(configuration, dict):
        return DEFAULT_FIELD
    value = configuration.get(FIELD_PARAMETER)
    if value is None or isinstance(value, (bool, dict, list, tuple)):
        return DEFAULT_FIELD
    text = str(value).strip()
    return text or DEFAULT_FIELD


def read_max_detonations(configuration):
    """Return how many detonations this firing may spend. Pure.

    CLAMPED, NEVER HONOURED PAST THE HARD CAP, and every unreadable value
    reads as the default of one. The clamp direction is what makes the ceiling
    structural: a form is a place a person types a number, and the number that
    matters here is the one this file will not go above.
    """
    if not isinstance(configuration, dict):
        return DEFAULT_MAX_DETONATIONS
    raw = configuration.get(MAX_DETONATIONS_PARAMETER)
    if raw is None or isinstance(raw, bool):
        return DEFAULT_MAX_DETONATIONS
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_MAX_DETONATIONS
    if value < 1:
        return DEFAULT_MAX_DETONATIONS
    return min(value, MAX_DETONATIONS_HARD_CAP)


def read_results(payload):
    """Return the alert's result rows as an iterator of mappings.

    AN ITERATOR RATHER THAN A LIST, and that is the memory bound. A
    correlation search can match tens of thousands of rows to buy one
    detonation, so the rows are produced one at a time and the caller keeps
    only the few it can still act on. See the module docstring.

    Two shapes, both from Splunk's own documented payload. `results_file` is
    the gzipped CSV of the whole result set and is the ordinary case; a single
    `result` object is the other, and it is read because reading it costs four
    lines and ignoring it would silently detonate nothing.

    An unreadable results file is a PayloadError rather than an empty
    iterator: an alert that fired on rows it cannot read has failed, and
    reporting success with a count of zero would hide it. The file is opened
    and its header row is read before this returns, so a file that is missing,
    is not gzip, or carries no readable header refuses here rather than part
    way through a run that has already spent something.

    :raises PayloadError: if the results file is named and cannot be read.
    """
    path = payload.get(RESULTS_FILE_KEY)
    if isinstance(path, str) and path.strip():
        return read_results_file(path.strip())

    single = payload.get(SINGLE_RESULT_KEY)
    if isinstance(single, dict):
        return iter([single])

    return iter([])


def read_results_file(path):
    """Return an iterator over the rows of a gzipped Splunk results CSV.

    THE OPEN AND THE HEADER HAPPEN NOW, THE ROWS HAPPEN LATER. Opening the
    file and reading its header is what tells the difference between a results
    file this action can read and one it cannot, and that answer is worth
    having before a client is built or a detonation is bought. The rows
    themselves arrive as the caller asks for them, which is what keeps the
    whole of a large result set out of memory.

    The handle is closed when the rows run out, when a read fails, and when
    close_results is called on what this returns, which is what execute does
    whether or not the firing got as far as reading anything.

    :raises PayloadError: if the file cannot be opened or decoded.
    """
    try:
        handle = gzip.open(path, "rt", newline="")
    except (IOError, OSError, EOFError, ValueError) as error:
        raise PayloadError(results_file_message(error))

    try:
        reader = csv.DictReader(handle)
        # Reading the field names is what forces the header row, and that read
        # is the one that finds out whether this is a gzipped CSV at all.
        header = reader.fieldnames
    except (IOError, OSError, EOFError, ValueError, csv.Error) as error:
        handle.close()
        raise PayloadError(results_file_message(error))

    if header is None:
        # An empty file, which is what a search matching nothing produces. Not
        # a failure: there are no rows, and the handle has no reason to stay
        # open waiting for a caller to find that out.
        handle.close()
        return iter([])

    return ResultRows(handle, reader)


class ResultRows(object):
    """An iterator over the rows of an open results file. One row at a time.

    A CLASS RATHER THAN A GENERATOR, and the difference is the close. A
    generator only runs its cleanup if it was started, so a firing that failed
    before it read a row (an unconfigured credential is the ordinary case)
    would leave the file open until the collector noticed. This closes on the
    last row, on a read failure, and on an explicit close, whether or not
    anything was ever read.

    A read failure part way through the file is a PayloadError for the same
    reason a failure to open it is one: an alert that fired on rows it cannot
    read has failed, and half a result set reported as a whole one would hide
    it.
    """

    def __init__(self, handle, reader):
        """
        :param handle: the open text handle, owned from here on.
        :param reader: a csv.DictReader over that handle, header consumed.
        """
        self._handle = handle
        self._reader = reader

    def __iter__(self):
        return self

    def __next__(self):
        if self._handle is None:
            # Exhausted or closed. An iterator that has finished stays
            # finished, rather than reporting the closed file as a read error.
            raise StopIteration
        try:
            row = next(self._reader)
        except StopIteration:
            self.close()
            raise
        except (IOError, OSError, EOFError, ValueError, csv.Error) as error:
            self.close()
            raise PayloadError(results_file_message(error))
        return dict(row)

    def close(self):
        """Close the file. Idempotent, and safe before the first row."""
        handle, self._handle = self._handle, None
        if handle is not None:
            handle.close()


def close_results(rows):
    """Close a results iterator if it is one that holds a file. Pure otherwise.

    A run that stops before the rows are exhausted, because the client could
    not be built or the platform refused, should not wait for the garbage
    collector to close a file under $SPLUNK_HOME. The single-result payload
    shape has no file and nothing to close, which is why this asks rather than
    assumes.
    """
    close = getattr(rows, "close", None)
    if close is not None:
        close()


def results_file_message(error):
    """Return the operator-facing message for an unreadable results file. Pure.

    THE PATH IS NOT IN THE MESSAGE. It is a temporary file under $SPLUNK_HOME
    with the search id in its name, which is the customer's own search rather
    than anything of ours, and an operator reading this in an alert status has
    the search in front of them already.
    """
    return (
        "The alert action could not read the search results Splunk handed "
        "it ({0}), so nothing was detonated.".format(type(error).__name__)
    )


TargetSelection = collections.namedtuple(
    "TargetSelection",
    # pairs           the (URL, row) pairs the run may act on, in order.
    # skipped_rows    rows carrying no usable URL, plus duplicates.
    # rows_above_cap  usable rows the cap left undetonated.
    # rows_read       every row the search handed over, cap or no cap.
    "pairs skipped_rows rows_above_cap rows_read",
)


def select_targets(rows, field_name, limit=None):
    """Return a TargetSelection over an iterable of result rows.

    Pure apart from consuming the iterable it is handed, which is the whole of
    the read: it decides nothing from anywhere else and reaches nothing.

    THE ONE FUNCTION THAT DECIDES WHAT IS USABLE, and with a limit it is also
    the only place the result set is held at all. It consumes `rows` once, in
    order, and retains at most `limit` (URL, row) pairs: a fifty thousand row
    correlation search leaves this function with five rows and four counters,
    which is the point.

    Every row is read even after the retained list is full, because
    `rows_above_cap` is what the finish line reports and a count that gave up
    when it ran out of room would tell an operator nothing. `rows_read` is the
    same number `len(rows)` used to be, and it is the count the log line calls
    records.

    A row whose field is absent, blank, or not a single valid URL is skipped
    rather than refused, and the count of skipped rows is what the caller
    reports. That direction is deliberate: an alert matching fifty rows where
    three have no URL should detonate what it can, and a correlation search
    that produces mixed rows is normal.

    Validation is `cmd_detonate.resolve_url`, which is the same function the
    search command validates with. Two copies of the URL rule would be two
    answers to whether a scheme is required, and the answer matters most here:
    an alert action browses whatever it is given, from our infrastructure, with
    nobody watching.

    DUPLICATES ARE DROPPED. A correlation search grouping by something other
    than the URL can easily produce the same URL twice, and detonating it twice
    would buy the same answer twice out of an allowance measured in tens. The
    FIRST row carrying a URL is the one paired with it, which matters for the
    provenance: a duplicate is the same detonation, and the row that asked for
    it first is the row that gets the credit.

    THE ROW IS PAIRED WITH THE URL SO THE PROVENANCE STAYS ATTACHED. A firing
    from a notable has one row and one URL, but a correlation search has many
    of each, and a per-firing answer to "which result did this come from" would
    be wrong on every row but the first.

    THE DUPLICATE CHECK IS EXACT BELOW THE CAP AND BOUNDED ABOVE IT. With a
    limit, the URLs remembered are the retained ones, so a URL appearing only
    among the rows above the cap counts once per row rather than once. The
    alternative is a set of every distinct URL in the result set, which grows
    with the search instead of with the cap and is the allocation this reader
    exists to remove. The count that produces is an upper bound on what raising
    the limit would buy, never an understatement, and a row duplicating
    something actually detonated is still counted as a duplicate, which is the
    case that would otherwise report rows above the cap when raising it would
    buy nothing.

    :param rows: an iterable of result rows. Consumed once, so an iterator is
        as good as a list and is what the ordinary path passes.
    :param field_name: the result field to take the URL from.
    :param limit: how many pairs to retain, or None for all of them. None is
        the whole-result-set form and it holds the whole result set.
    """
    pairs = []
    seen = []
    skipped = 0
    above_cap = 0
    rows_read = 0
    for row in rows:
        rows_read += 1
        if not isinstance(row, dict):
            skipped += 1
            continue
        value = row.get(field_name)
        if value is None and field_name.startswith(MULTIVALUE_PREFIX):
            skipped += 1
            continue
        try:
            target = cmd_detonate.resolve_url(value)
        except cmd_detonate.DetonateOptionError:
            skipped += 1
            continue
        if target in seen:
            skipped += 1
            continue
        if limit is not None and len(pairs) >= limit:
            # USABLE, AND NOT DETONATED. Counted rather than retained: the row
            # itself is of no further use, and holding it would make the cap a
            # limit on what is spent rather than on what is read.
            above_cap += 1
            continue
        seen.append(target)
        pairs.append((target, row))
    return TargetSelection(
        pairs=pairs,
        skipped_rows=skipped,
        rows_above_cap=above_cap,
        rows_read=rows_read,
    )


def read_target_rows(rows, field_name):
    """Return (URL, row) pairs for the usable result rows, in order. Pure.

    The whole-result-set form of select_targets, which is where the rules are
    written down. It retains every usable row, so the ordinary path calls
    select_targets with the cap as its limit instead.
    """
    selection = select_targets(rows, field_name)
    return selection.pairs, selection.skipped_rows


def read_targets(rows, field_name):
    """Return the usable URLs out of the result rows, in order. Pure.

    The URL-only form of read_target_rows above. Kept because a caller that
    wants the list of URLs and nothing else should not have to unpack pairs.
    """
    pairs, skipped = read_target_rows(rows, field_name)
    return [target for target, _ in pairs], skipped


def read_source_fields(payload, row=None):
    """Return the provenance fields for one detonation, as task row fields. Pure.

    WHERE EACH VALUE COMES FROM is the module docstring's list, and the split
    between the payload and the result row is the part worth not getting wrong.

    ABSENT IS ABSENT. Every value goes through task_store.read_scalar, so a
    key that is missing, empty, blank, a boolean or a container produces no
    field at all rather than a field holding "". That is the same rule
    task_store.build_task_row applies to everything else on the row: an absent
    column says the app has nothing, and a present blank one reads as somebody
    having answered with nothing.

    On plain Splunk Enterprise this returns the search job id and usually
    nothing else, because the rest of these fields are Enterprise Security's.
    A payload with no `sid` at all returns an empty mapping, and nothing
    downstream treats that as a fault.

    :param payload: the decoded alert action payload.
    :param row: the result row this detonation came from, if there is one.
    :return: a mapping of task row fields, possibly empty. Never None.
    """
    fields = {}

    result_id = None
    if isinstance(payload, dict):
        sid = task_store.read_scalar(payload.get(SID_KEY))
        if sid is not None:
            fields[task_store.SOURCE_SID_FIELD] = sid
        result_id = task_store.read_scalar(payload.get(RESULT_ID_KEY))

    rid = None
    if isinstance(row, dict):
        rid = task_store.read_scalar(row.get(RID_FIELD))

    # THE ROW'S OWN rid WINS OVER THE PAYLOAD'S result_id. Both name the same
    # thing and each exists in a case the other does not: cim_actions.py reads
    # `result_id` off the settings when splunkd invokes the action once per
    # result, and `rid` off the row otherwise. The row is the more specific
    # answer when both are there, because the payload's is per invocation and
    # the row's is per row.
    if rid is None:
        rid = result_id
    if rid is not None:
        fields[task_store.SOURCE_RID_FIELD] = rid

    if isinstance(row, dict):
        for field_name, row_field in (
            (task_store.SOURCE_ORIG_SID_FIELD, ORIG_SID_FIELD),
            (task_store.SOURCE_ORIG_RID_FIELD, ORIG_RID_FIELD),
            (task_store.NOTABLE_EVENT_ID_FIELD, EVENT_ID_FIELD),
            (task_store.NOTABLE_RULE_ID_FIELD, RULE_ID_FIELD),
        ):
            value = task_store.read_scalar(row.get(row_field))
            if value is not None:
                fields[field_name] = value

    return fields


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


class SourceTaggingStore(object):
    """A task store that stamps where a detonation came from onto every row.

    WHY A WRAPPER AND NOT AN ARGUMENT. cmd_detonate.Detonator builds the task
    row and writes it in one step, which is right: the row is the receipt for a
    metered call and the code that spends the money is the code that should
    write it. This action knows one thing the command cannot, which is that the
    firing came from a particular search result, and a wrapper is how that gets
    onto the row without a second write.

    The alternative was to let the command write the row and then upsert it
    again with the provenance added. That was rejected: it doubles the writes
    to the collection for something that is not new information, and the window
    between the two writes is a window where the tray shows a row that claims
    to have come from nowhere.

    Only save_task changes. The providers cache is passed straight through,
    because a cached providers list has nothing to do with who asked for it.
    """

    def __init__(self, store, payload=None):
        """
        :param store: a task_store.TaskStore, or anything with its surface.
        :param payload: the decoded alert action payload, for the fields that
            live on it rather than on a result row.
        """
        self._store = store
        self._payload = payload

        # The fields the next save_task will add. Empty until a result is set,
        # and empty is a supported state: it is what a payload with no
        # provenance in it produces, and it stamps nothing.
        self.source = {}

    def set_result(self, row):
        """Name the result row the next detonation comes from.

        Mirrors ModularAction.update(result) in Splunk's own common action
        model library, and for the same reason that library gives: the
        identifiers are per result, so they have to be re-read before each one
        is acted on rather than once per firing.
        """
        self.source = read_source_fields(self._payload, row)

    # -- the store's surface ---------------------------------------------

    def cached_providers(self):
        return self._store.cached_providers()

    def store_providers(self, payload):
        return self._store.store_providers(payload)

    def save_task(self, row):
        """Store one task row with the provenance added.

        The provenance never overwrites anything: the six field names are not
        in task_store.ALL_FIELDS, so a stamped row and the row the command
        built differ only by fields the command does not produce.
        """
        if isinstance(row, dict) and self.source:
            stamped = dict(row)
            stamped.update(self.source)
            return self._store.save_task(stamped)
        return self._store.save_task(row)

    @property
    def stores(self):
        return self._store.stores

    @property
    def degraded(self):
        return self._store.degraded


class ActionRun(object):
    """One firing of the alert action.

    Split out from main() so the whole pass runs with a fake payload, a fake
    client and a fake store, which is the same reason Detonator and TaskPoller
    are split out of the command and the input.
    """

    def __init__(
        self, detonator, max_detonations=DEFAULT_MAX_DETONATIONS, store_tagger=None
    ):
        """
        :param detonator: a cmd_detonate.Detonator, or anything with the same
            detonate() signature. The command's own pass is reused rather than
            reimplemented: it validates the provider and the VM against the
            platform's list before spending anything, writes the task row, and
            reports whether the write landed.
        :param max_detonations: the ceiling for this firing, already clamped.
        :param store_tagger: the SourceTaggingStore the detonator writes
            through, so each detonation can be told which result row it came
            from. None runs the pass with no provenance, which is what happens
            when this class is driven without a payload.
        """
        self.detonator = detonator
        self.max_detonations = min(int(max_detonations), MAX_DETONATIONS_HARD_CAP)
        self.store_tagger = store_tagger

        self.detonations = 0
        self.rows_read = 0
        self.skipped_rows = 0
        self.rows_above_cap = 0
        self.unstored = 0
        self.failure = None

    def run(self, rows, field_name):
        """Detonate up to the cap and return the task rows written.

        Order of operations matters and it is the order that spends least: the
        targets are read and de-duplicated first, the cap is applied as they
        are read, and only then is anything submitted. Reading the rows costs
        nothing, so there is no reason to discover an invalid URL after buying
        a detonation for the row above it, and a results file that fails part
        way through still fails before anything is spent.

        THE CAP IS APPLIED BY THE READER RATHER THAN TO A LIST IT BUILT.
        `rows` is consumed once and at most `max_detonations` of the rows
        survive the read, so a correlation search matching tens of thousands of
        rows costs this pass five rows and four counters. `rows` may be an
        iterator, which is what the ordinary path hands over.
        """
        selection = select_targets(rows, field_name, limit=self.max_detonations)
        self.rows_read = selection.rows_read
        self.skipped_rows = selection.skipped_rows
        self.rows_above_cap = selection.rows_above_cap

        written = []
        for target, row in selection.pairs:
            # BEFORE THE SUBMIT, so the row the command writes carries the
            # provenance on its first and only write.
            if self.store_tagger is not None:
                self.store_tagger.set_result(row)
            try:
                rows_written = self.detonator.detonate(
                    target, cmd_detonate.DEFAULT_PROVIDER, cmd_detonate.DEFAULT_VM
                )
            except (ClientError, cmd_detonate.DetonateOptionError) as error:
                # STOPS RATHER THAN CONTINUING, and the reason is the cost.
                # A refused provider list, a rejected key or an unreachable API
                # will refuse the next target the same way, and every attempt
                # is a request against the customer's account. The failure is
                # reported and the alert is marked failed.
                self.failure = error
                break
            self.detonations += 1
            written.extend(rows_written)
            if not self.detonator.stored:
                # The loudest failure in the app, per bin/task_store.py: the
                # detonation was bought and the receipt was lost, and the
                # platform's own my-tasks listing hangs, so nothing can find
                # it again. There is no analyst in front of an alert action to
                # warn, so it is counted and reported on the finish line as a
                # degraded outcome.
                self.unstored += 1
        return written


def build_client(service, community_name=None):
    """Return a configured client, or fail with a message naming the action.

    Constraint C8: unconfigured means a clear message and zero network calls.
    ps_client refuses without a stored credential and names the setup page;
    what it cannot know is that the caller was an alert firing in the
    background, where "open the setup page" is the whole of the remedy and
    nobody is watching a search bar for it.
    """
    try:
        return get_client(service, community=community_name)
    except ClientConfigurationError as error:
        raise ClientConfigurationError(
            "The PolySwarm Detonate alert action cannot submit a detonation "
            "without a configured PolySwarm API key. {0}".format(error)
        )


def execute(payload, service_builder=None):
    """Run one firing. Returns the ActionRun.

    :param payload: the decoded payload object.
    :param service_builder: a callable taking (server_uri, session_key) and
        returning a splunklib service, for tests. Production leaves it None
        and ps_splunkd.build_service is used, which is the one place this app
        builds an app-namespaced service.
    :raises PayloadError: if the payload cannot be acted on.
    :raises ClientConfigurationError: if there is no usable credential.
    """
    timer = ps_log.Timer()
    ps_log.info(LOG_COMPONENT, "start", "ok")

    configuration = read_configuration(payload)
    field_name = read_field_name(configuration)
    max_detonations = read_max_detonations(configuration)

    # OPENED HERE AND READ INSIDE THE RUN. read_results has already found out
    # whether the file can be read at all, and the rows themselves arrive one
    # at a time so that a result set of any size costs this process the cap.
    rows = read_results(payload)

    try:
        builder = (
            ps_splunkd.build_service if service_builder is None else service_builder
        )
        service = builder(payload.get(SERVER_URI_KEY), payload.get(SESSION_KEY_KEY))

        # The same three steps the command takes, in the same order, so that an
        # alert and a search bar detonate into the same community: resolve,
        # build the client with the answer, then validate and submit.
        resolution = community.resolve(
            service, client_builder=lambda: build_client(service)
        )
        client = build_client(service, community_name=resolution.community)

        store = task_store.TaskStore(service)

        # The provenance seam. On plain Splunk this stamps the search job id;
        # from an Enterprise Security notable it stamps the notable and the
        # rule as well. See SourceTaggingStore for why it is a wrapper rather
        # than an extra argument to the command's pass.
        tagger = SourceTaggingStore(store, payload)
        detonator = cmd_detonate.Detonator(client, store=tagger)

        run = ActionRun(
            detonator, max_detonations=max_detonations, store_tagger=tagger
        )
        run.run(rows, field_name)
    finally:
        # A run that stopped before the rows ran out leaves a temporary file
        # under $SPLUNK_HOME open until the collector notices. Closing it here
        # is one line and it makes the failure paths as tidy as the ordinary
        # one.
        close_results(rows)

    degraded = (
        run.failure is not None
        or run.unstored > 0
        or store.degraded
        or resolution.degraded
    )
    ps_log.info(
        LOG_COMPONENT,
        "finish",
        "degraded" if degraded else "ok",
        # records is the rows the search handed over, lookups the detonations
        # actually spent. The app's existing count vocabulary, so a health
        # panel does not need a new key for this surface. The count comes off
        # the run because the rows were streamed: nothing here ever held the
        # result set to take its length.
        records=run.rows_read,
        lookups=run.detonations,
        unrouted=run.skipped_rows,
        limit=run.max_detonations,
        limit_reached=run.rows_above_cap > 0,
        cache_stores=store.stores,
        cache_degraded=store.degraded,
        reason=None if run.failure is None else type(run.failure).__name__,
        duration_ms=timer.duration_ms,
    )
    return run


def report(run, stream):
    """Write what the firing did to a stream, for the alert's own status.

    NOTHING HERE IS FORMATTED FROM A RESULT ROW. The counts are integers this
    module produced, the failure is reported by its class name and its own
    sanitized message, and there is no URL, task id or search name in any of
    it: an alert action's stderr goes to splunkd.log, which is a place a
    customer's own data does not belong any more than a credential does.
    """
    if run.rows_above_cap:
        stream.write(
            "PolySwarm Detonate: {0} more matching row(s) were not detonated, "
            "because this action is limited to {1} detonation(s) per firing. "
            "Raise the limit on the action's configuration, up to {2}, or "
            "narrow the search.\n".format(
                run.rows_above_cap, run.max_detonations, MAX_DETONATIONS_HARD_CAP
            )
        )
    if run.unstored:
        stream.write(
            "PolySwarm Detonate: {0} detonation(s) were submitted but could "
            "not be written to the {1} collection, so they will not appear in "
            "the tasks tray and the poller will not follow them.\n".format(
                run.unstored, task_store.TASK_COLLECTION_NAME
            )
        )
    if run.failure is not None:
        stream.write(
            "PolySwarm Detonate: stopped after {0} detonation(s). {1}\n".format(
                run.detonations, run.failure
            )
        )


def main(argv=None, stdin=None, stderr=None):
    """Entry point invoked by splunkd. Returns the process exit code."""
    arguments = list(sys.argv if argv is None else argv)
    stream = sys.stdin if stdin is None else stdin
    errors = sys.stderr if stderr is None else stderr

    if EXECUTE_ARGUMENT not in arguments[1:]:
        errors.write(
            "PolySwarm Detonate: this program is run by Splunk as an alert "
            "action, with {0} and a JSON payload on standard input. It does "
            "nothing when run any other way, deliberately: a detonation is "
            "metered.\n".format(EXECUTE_ARGUMENT)
        )
        return 1

    try:
        payload = read_payload(stream)
        run = execute(payload)
    except (PayloadError, ClientConfigurationError) as error:
        # Both carry a message written to be read by an operator, and neither
        # can carry a credential: PayloadError's are literals in this file, and
        # ps_client sanitizes before it raises.
        errors.write("PolySwarm Detonate: {0}\n".format(error))
        return 2
    except Exception as error:
        # THE CLASS NAME AND NOTHING ELSE, for the reason
        # ps_client.get_api_key writes out at length: an unexpected exception's
        # text is not something this module can vouch for, and splunkd's own
        # binding layer quotes the exchange it attempted into its exceptions.
        ps_log.warning(LOG_COMPONENT, "finish", "error", reason=type(error).__name__)
        errors.write(
            "PolySwarm Detonate: failed with {0}. See the app's log for the "
            "structured record of this run.\n".format(type(error).__name__)
        )
        return 3

    report(run, errors)
    return 0 if run.failure is None and run.unstored == 0 else 4


if __name__ == "__main__":
    sys.exit(main())
