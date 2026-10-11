"""KV store checkpoint for the scheduled intel pull.

One collection, `ps_intel_pull_checkpoint`, one document per input stanza. It
answers one question: where did this stanza get to, so that the next run does
not pull the same artifacts again.

WHY THIS INPUT HAS A CHECKPOINT DOCUMENT AND THE TASK POLLER DOES NOT
---------------------------------------------------------------------
`bin/input_task_poller.py` opens with a paragraph explaining that it keeps no
checkpoint document, and the reasoning there is sound and does not transfer.
That input walks rows it already owns, and the state worth remembering is per
row and is written in the same document as the answer it describes.

This input has no rows. It pulls a stream, and for a stream the answer to
"where did I get to" is a POSITION, which belongs in a document of its own.
There is nothing else in the app for it to be written alongside: the artifacts
go into a Splunk index, and an index is append-only and is not something this
app can read back cheaply to work out what it already sent.

WHAT IS STORED, AND WHY IT IS FOUR THINGS RATHER THAN ONE
---------------------------------------------------------
    window_end      epoch seconds of the last successfully completed window
    digests         the sha256 of every artifact that window emitted, comma
                    joined
    backlog_end     epoch seconds the NEXT window must close at while a capped
                    run's leftovers are still being drained, or 0 when there
                    are none
    backlog_target  epoch seconds window_end becomes once that drain finishes,
                    or 0 when there is no drain in progress

The window end alone is nearly enough and not quite. It is what makes the next
query cheap: the next window starts where this one ended, so an artifact older
than the checkpoint is excluded by the platform's own range filter rather than
by anything this app does.

THE TWO BACKLOG FIELDS, AND WHY ONE OF THEM IS NOT ENOUGH
---------------------------------------------------------
A run that stops at `max_artifacts_per_run` has covered part of its window and
not the rest, and the platform answers this endpoint NEWEST FIRST (the evidence
is in `tests/fixtures/README.md` and in the recorded response itself, whose
kept entries descend by `artifact.created`). So the part covered is the NEWEST
part, and what is left is everything older than the oldest artifact the run
emitted. Three numbers describe that state and all three are needed:

  * `window_end` stays where it was, because the floor of the window has not
    moved: everything at or below it is still the only thing known to be done.
  * `backlog_end` is where the next window closes, so the next run asks about
    the older remainder instead of asking the same question again.
  * `backlog_target` is where `window_end` jumps to when the drain finishes.

Dropping the target and letting a finished drain set `window_end` to the drain
window's own end was tried on paper and rejected. The artifacts between the
drain boundary and the original window end were emitted by the capped runs, and
their digests are gone by then (this list is one run deep, deliberately), so the
next ordinary window would re-cover them and re-emit every one. That is the
duplicate flood the cap exists to prevent, arriving by a different route.

While a drain is in progress the digest list is UNIONED rather than replaced
whenever the boundary does not move, which happens when more artifacts share
the boundary second than one run may emit. Without the union the run before last
would drop out of the refusal list and its artifacts would be emitted a second
time. The union is bounded by MAX_DIGESTS, so a second holding more artifacts
than that degrades to duplicate events rather than to a gap, which is the
direction every failure path in this module takes.

What it cannot close on its own is the boundary. The query mirrors v1's range
syntax, `artifact.created:[start TO end]`, and Lucene's square brackets are
INCLUSIVE AT BOTH ENDS. So an artifact created at exactly the stored instant
falls inside both the window that stored it and the window that follows, and a
window end on its own would emit that artifact twice. The digest list is what
refuses it, and it is the previous run's list rather than a growing history
because that is all it needs to be: two consecutive windows overlap only at the
instant they share, so an artifact that could repeat is necessarily one the
immediately preceding run emitted.

The alternative was an exclusive lower bound, `{start TO end]`. Rejected on
constraint C10: no recorded response proves this platform's query parser
accepts the curly form, and a range syntax that silently does not parse is a
window that quietly matches nothing.

WHAT IS NOT STORED, AND THAT IS THE MORE IMPORTANT LIST
-------------------------------------------------------
No query string, no family, no tag, no permalink, and no pagination cursor.

The cursor is worth saying out loud because it looks like checkpoint state and
is not. The offset the platform returns is an encrypted token scoped to one
search, so storing it across runs would resume a search whose window has moved,
and the platform is the only party that can say what it decodes to. Pagination
lives entirely inside one run; see `bin/input_intel_pull.py`.

Families and tags are not stored because the checkpoint is not a record of the
question. An operator who edits the stanza's families gets the new question
asked over the window that follows the checkpoint, which is the behaviour that
lets somebody widen a pull without re-billing the history.

THE FAILURE DIRECTION IS DELIBERATE, AND IT IS NOT THE USUAL ONE
---------------------------------------------------------------
Every other KV surface in this app fails OPEN, because every other one is an
optimisation: `verdict_cache` degrades to a miss, `usage_store` degrades to not
throttled, and the cost of being wrong is one extra request.

This one fails CLOSED on the read and open on the write, and the asymmetry is
the point:

  * **A FAILED READ IS SAID OUT LOUD AND IS NOT A POSITION.** `read()` answers
    `READ_FAILED` for it, which is a different answer from the empty position a
    stanza that has never run gets, and the caller refuses the whole run: no
    request, no event, no write. See the paragraph below for why the earlier
    reading of this, "an unreadable checkpoint reads as no checkpoint", was a
    data-loss defect rather than the bounded cost it looked like.
  * **A failed write leaves the previous checkpoint in place,** so the next run
    re-pulls the window that was just pulled. Duplicate events, bounded by the
    cap, rather than a gap. A gap is worse: nothing in the app can tell later
    that a window was skipped, and the artifacts in it are gone from the
    customer's index for good.

Both directions are counted and reported. `IntelCheckpoint.degraded` reaches
the input's finish line, so an operator whose collection is broken sees
`cache_degraded=True` rather than being left to infer it from a duplicate count.

WHY A FAILED READ CANNOT READ AS "NO CHECKPOINT"
------------------------------------------------
It used to, and the cost was described as one lookback window of duplicate
events. That description was wrong in the direction that matters, and QA found
it: the duplicates were the small half.

A run that read no position starts a fresh-install window, and a run that then
completes its window writes the checkpoint with both backlog fields cleared. So
a single transient KV store failure on the READ did two things. It re-emitted
the lookback window, which is the bounded cost that was argued for. And it then
OVERWROTE the real stored position, including any drain in progress, with the
fresh-install one. The drain state is the only record that a capped run left
part of a window unpulled, nothing else in the app can reconstruct it, and the
artifacts it pointed at are excluded from every later window by the position
that replaced it. One outage, and a permanent gap in the customer's index.

The reading that survives is that a run which does not know where it got to
cannot know its window either, so it has nothing to say and nothing to spend.
`READ_FAILED` is that statement, `bin/input_intel_pull.py` refuses the run on
it, and the next interval reads the collection again. A KV store outage
therefore costs a delayed feed, which the windows chain over, rather than a
gap.

An empty position is still an empty position. A stanza nobody has run answers
404, which is the ordinary state of a fresh install, and it keeps starting a
`lookback_minutes` window exactly as before.

Layering, the same shape usage_store uses:
    document_id_for()   pure, no I/O
    is_read_failure()   pure, no I/O
    read_window_end()   pure, no I/O
    read_digests()      pure, no I/O
    read_backlog()      pure, no I/O
    join_digests()      pure, no I/O
    checkpoint_document() pure, no I/O
    IntelCheckpoint     the I/O seam, one instance per run
"""

import collections
import hashlib
import time

import ps_log

APP_NAME = "polyswarm_app_for_splunk"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "intel_checkpoint"

# The collection declared in default/collections.conf. One name, one home.
COLLECTION_NAME = "ps_intel_pull_checkpoint"

# The KV store's own document id field.
ID_FIELD = "_key"

STANZA_FIELD = "stanza"
WINDOW_END_FIELD = "window_end"
DIGESTS_FIELD = "digests"
BACKLOG_END_FIELD = "backlog_end"
BACKLOG_TARGET_FIELD = "backlog_target"
ARTIFACTS_FIELD = "artifacts"
UPDATED_AT_FIELD = "updated_at"

ALL_FIELDS = (
    STANZA_FIELD,
    WINDOW_END_FIELD,
    DIGESTS_FIELD,
    BACKLOG_END_FIELD,
    BACKLOG_TARGET_FIELD,
    ARTIFACTS_FIELD,
    UPDATED_AT_FIELD,
)

# What read() answers with.
#
# A named tuple rather than a bare four-tuple, and that is not decoration: the
# four values are two epochs, a set and a third epoch, so a caller unpacking
# them in the wrong order gets a window rather than an error. The names are what
# bin/input_intel_pull.py reads, and it compares equal to a plain tuple, so a
# test may assert either form.
Position = collections.namedtuple(
    "Position", ("window_end", "digests", "backlog_end", "backlog_target")
)


class _ReadFailure(object):
    """The answer `read()` gives when the collection could not be read.

    A TYPE OF ITS OWN AND NOT A POSITION, which is the whole point. The values
    on a position are window bounds, and a failed read has no window bounds to
    offer: it does not know where the stanza got to, so anything tuple-shaped
    it returned would be a window a caller could act on. This is not
    subscriptable and not iterable, so a caller that ignores the signal fails
    in a test rather than quietly pulling a fresh-install window over a
    position it never read.

    Falsy, so `if not position:` reads correctly for a caller that only wants
    to know whether there is anything to resume from.
    """

    __slots__ = ()

    def __bool__(self):
        return False

    # Python 2 spelling of the same thing. The app's floor is Python 3.9 and
    # nothing here runs on 2, but ps_client and task_store both carry the
    # same courtesy for a reader who greps for one and finds the other.
    __nonzero__ = __bool__

    def __repr__(self):
        return "READ_FAILED"


# The one instance. Compared by identity through is_read_failure(), so a second
# instance cannot be mistaken for it and a caller cannot construct one that
# means something slightly different.
READ_FAILED = _ReadFailure()


def is_read_failure(position):
    """True when a position came back from a checkpoint read that failed. Pure.

    The seam `bin/input_intel_pull.py` branches on, and it is a function rather
    than an `is READ_FAILED` at the call site for one reason: the puller
    accepts anything with read() and write(), so a fake store in a test asks
    this question too and asks it the same way.
    """
    return position is READ_FAILED or isinstance(position, _ReadFailure)

# The value stored for an absent epoch.
#
# Zero rather than a missing key, because every write carries every field: a
# document whose field set changed between releases is a document a reader has
# to guess about, and read_backlog() already treats anything at or below zero as
# "no backlog". A test asserts the written field set equals ALL_FIELDS.
NO_EPOCH = 0.0

# The document id is a digest of the stanza name, for the reason
# verdict_cache.DOCUMENT_ID_PREFIX gives for an indicator: the input is the
# operator's own free text. A modular input stanza name can carry a colon, a
# slash, a space or a non-ASCII character, none of which belong in a KV store
# document id, and validating a charset would refuse a stanza that splunkd
# accepted. A digest accepts every name and produces one id per name.
DOCUMENT_ID_PREFIX = "stanza_"

# The separator on the stored digest list.
#
# A bare comma and not ", ", for the reason task_store.LIST_SEPARATOR carries:
# the value is read back with split(), so a space in the separator puts a
# leading space on every digest after the first and none of them then matches
# a digest computed fresh.
LIST_SEPARATOR = ","

# How many digests one checkpoint document may carry.
#
# Equal to the input's hard cap on artifacts per run, because that is exactly
# how many the previous run can have emitted. Stated as its own constant rather
# than imported from the input so this module does not depend on the module that
# depends on it, and a test asserts the two agree.
#
# The size is bounded by construction: 1000 digests of 64 characters plus a
# separator is about 65KB in one document, once per stanza. That is large for a
# KV document and it is the honest cost of not double-emitting; the default cap
# of 200 makes the ordinary document about 13KB.
#
# THE TRUNCATION BELOW IS A GUARD AND MUST STAY UNREACHABLE, which is decision
# D26. join_digests() keeps the lexically smallest MAX_DIGESTS values and says
# nothing, so a caller that hands it more than this many has silently dropped
# the rest of its refusal list, and during a drain that is a loop rather than a
# duplicate: the boundary stops moving and every run re-emits what the dropped
# digests would have refused. So the caller does not hand it more.
# bin/input_intel_pull.py compares the union it is about to store against this
# number and advances past the second instead, counted and logged. Raising the
# number would only move the loop to a busier second, because the union at one
# second grows with the artifacts in that second and not with this constant.
MAX_DIGESTS = 1000

# splunkd answers a read for a document that is not there with a 404. For this
# collection that is the ordinary state of a stanza nobody has run yet, so it is
# told apart from a real failure and produces no warning.
NOT_FOUND_STATUSES = (404,)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def document_id_for(stanza):
    """Return the document id for one input stanza, or None when unusable.

    See the note on DOCUMENT_ID_PREFIX for why the id is a digest.

    :param stanza: the input stanza name, as splunkd names it.
    :return: the document id, or None when there is nothing to key on.
    """
    if stanza is None:
        return None
    text = str(stanza).strip()
    if not text:
        return None
    return DOCUMENT_ID_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_window_end(document):
    """Return the stored window end out of a raw document, or None.

    Pure. None for every unusable document, and unusable is deliberately
    broad: not a mapping, no readable number, a negative number, or a
    non-finite one. All of them mean the same thing to the caller, which is
    that there is no position to resume from, and conflating them is what
    keeps the fall-back to lookback_minutes one code path rather than five.
    """
    if not isinstance(document, dict):
        return None
    value = _as_float(document.get(WINDOW_END_FIELD))
    if value is None or value <= 0:
        return None
    return value


def read_digests(document):
    """Return the digests the last run emitted, as a set. Pure.

    An empty set for every unusable document and for a document whose list is
    empty, which are the same thing to the caller: nothing is known to have
    been emitted, so nothing is refused.

    Case is folded, for the reason verdict_cache.document_id_for folds it on a
    hash: different sources genuinely disagree about hash case for the same
    file, and a stored digest that does not match the same digest computed
    fresh would let the artifact through.
    """
    if not isinstance(document, dict):
        return set()
    raw = document.get(DIGESTS_FIELD)
    if raw is None or isinstance(raw, bool) or not isinstance(raw, str):
        return set()
    found = set()
    for part in raw.split(LIST_SEPARATOR):
        text = part.strip().lower()
        if text:
            found.add(text)
    return found


def read_backlog(document):
    """Return (backlog_end, backlog_target) out of a raw document. Pure.

    (None, None) unless BOTH are readable positive numbers AND the target is at
    or after the boundary. All three conditions have to hold for the pair to
    describe a drain that can be resumed:

      * a boundary with no target would leave a finished drain with nowhere to
        advance window_end to, which is the duplicate flood the module
        docstring describes;
      * a target BEFORE the boundary is not a state this app writes, so it is a
        document from somewhere else, and the safe reading of one is that there
        is no backlog. The next run then covers the ordinary window, which
        duplicates rather than skips.

    Read as a pair for that reason: there is no useful half of this state, and
    returning one without the other would make the caller re-derive the rule.
    """
    if not isinstance(document, dict):
        return None, None
    end = _as_float(document.get(BACKLOG_END_FIELD))
    target = _as_float(document.get(BACKLOG_TARGET_FIELD))
    if end is None or target is None:
        return None, None
    if end <= 0 or target <= 0:
        return None, None
    if target < end:
        return None, None
    return end, target


def join_digests(digests):
    """Return the stored form of a digest collection. Pure.

    Sorted, so that the same set of artifacts produces the same document
    whatever order the pages arrived in: an unstable document would rewrite
    the collection on every run for no change. Truncated at MAX_DIGESTS, which
    the caller cannot exceed anyway because the input's hard cap is the same
    number, so the truncation is a guard rather than a behaviour.

    Case is folded on the way in for the reason read_digests folds it on the
    way out.
    """
    if not digests:
        return ""
    cleaned = set()
    for value in digests:
        if value is None or isinstance(value, bool):
            continue
        text = str(value).strip().lower()
        if text:
            cleaned.add(text)
    return LIST_SEPARATOR.join(sorted(cleaned)[:MAX_DIGESTS])


def checkpoint_document(
    stanza,
    window_end,
    digests,
    artifacts,
    now,
    backlog_end=None,
    backlog_target=None,
):
    """Return the document for one window, or None. Pure.

    None when the stanza has no usable name, because the document id comes
    from it and a document with no id cannot be written.

    :param stanza: the input stanza name.
    :param window_end: epoch seconds everything is now known to be done to.
    :param digests: the sha256 values the window emitted.
    :param artifacts: how many events the window wrote.
    :param now: epoch seconds at the moment of the write.
    :param backlog_end: epoch seconds the next window must close at, or None
        when the window was covered whole and there is nothing to drain.
    :param backlog_target: epoch seconds window_end becomes when the drain
        finishes, or None. Written together with backlog_end or not at all:
        read_backlog() refuses a half of this state, so writing one alone would
        store something no reader accepts.
    """
    document_id = document_id_for(stanza)
    if document_id is None:
        return None
    both = backlog_end is not None and backlog_target is not None
    return {
        ID_FIELD: document_id,
        STANZA_FIELD: str(stanza).strip(),
        WINDOW_END_FIELD: float(window_end),
        DIGESTS_FIELD: join_digests(digests),
        BACKLOG_END_FIELD: float(backlog_end) if both else NO_EPOCH,
        BACKLOG_TARGET_FIELD: float(backlog_target) if both else NO_EPOCH,
        ARTIFACTS_FIELD: int(artifacts),
        UPDATED_AT_FIELD: float(now),
    }


def _as_float(value):
    """Return value as a finite float, or None when it is not a readable one."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    # A NaN compares unequal to itself and an infinity is not a clock reading.
    # Both would produce a window this app cannot reason about, so both read as
    # no checkpoint at all.
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


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


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------


class IntelCheckpoint(object):
    """Reads and writes one stanza's checkpoint. One instance per run.

    Nothing at module scope, so state cannot outlive the run that made it.

    Every method swallows every exception from splunkd and none of them
    fabricates anything. Constraint C6 forbids a catch-all that invents data,
    and nothing is invented on any of these paths: a failed read reports that
    it failed, which is a different answer from the empty position an empty
    collection reports, and a failed write does nothing at all.
    """

    def __init__(self, service, collection=COLLECTION_NAME, now=None):
        """
        :param service: the splunklib service, app namespaced. None is
            accepted and disables the collection, which is what happens when
            the input is driven outside splunkd by a test.
        :param collection: collection name, for tests.
        :param now: a callable returning epoch seconds, for tests.
        """
        self._service = service
        self._collection = collection
        self._now = time.time if now is None else now

        self.reads = 0
        self.writes = 0

        # True once anything has failed. Read by the input so an operator is
        # told the checkpoint could not be applied rather than left to infer it
        # from a duplicate count.
        self.degraded = False

    # -- the collection --------------------------------------------------

    def _data(self):
        """Return the collection's data endpoint, or None when unreachable."""
        if self._service is None:
            return None
        try:
            return self._service.kvstore[self._collection].data
        except Exception as error:
            self._degrade("open", error)
            return None

    def _degrade(self, event, error):
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
            collection=self._collection,
        )

    # -- reading ---------------------------------------------------------

    def read(self, stanza):
        """Return the stored Position for one stanza, or READ_FAILED.

        TWO ANSWERS THAT USED TO BE ONE, and the module docstring's note on
        why a failed read cannot read as no checkpoint is the argument for
        splitting them.

        An empty Position, (None, set(), None, None), when there is genuinely
        nothing to resume from and nothing failed. Three ways to get one, and
        all three are ordinary: this stanza has never run (splunkd answers 404
        for a document that is not there), there is no service at all, which is
        how the input is driven outside splunkd, and the stanza has no usable
        name to key on.

        READ_FAILED when the collection could not be read: it is absent, the
        running role cannot read it, splunkd is not answering, or the read
        raised anything that is not a not-found. The caller refuses the run on
        that answer rather than pulling a window it cannot place.

        A MALFORMED DOCUMENT IS STILL AN EMPTY POSITION rather than a failure,
        and the distinction is who wrote it. A document this app cannot read
        was written by something that is not this app, so there is no position
        of ours to lose; the safe reading is the fresh-install window, which
        duplicates a bounded window rather than skipping one.

        NO STANZA NAME REACHES THE LOG. A stanza name is the operator's own
        text and ps_log has no key it could travel under; the collection name
        is a constant in this app and does.
        """
        empty = Position(None, set(), None, None)

        document_id = document_id_for(stanza)
        if document_id is None:
            return empty

        if self._service is None:
            # Checkpointing is switched off rather than broken. Nothing was
            # attempted, so nothing failed, and a test driving the input with
            # no splunkd still gets the fresh-install window.
            return empty

        data = self._data()
        if data is None:
            # _data() has already degraded and logged. The collection is not
            # reachable, so this stanza's position is unknown rather than
            # absent.
            return READ_FAILED

        try:
            document = data.query_by_id(document_id)
        except Exception as error:
            if _is_not_found(error):
                # Nobody has run this stanza yet. The ordinary state of a fresh
                # install, not a fault, so no warning and no degradation: a
                # first run must not report a broken checkpoint.
                ps_log.debug(
                    LOG_COMPONENT,
                    "read",
                    "absent",
                    collection=self._collection,
                )
                return empty
            self._degrade("read", error)
            return READ_FAILED

        self.reads += 1
        backlog_end, backlog_target = read_backlog(document)
        return Position(
            read_window_end(document),
            read_digests(document),
            backlog_end,
            backlog_target,
        )

    # -- writing ---------------------------------------------------------

    def write(
        self,
        stanza,
        window_end,
        digests,
        artifacts,
        backlog_end=None,
        backlog_target=None,
    ):
        """Store one position. Returns True when it was written.

        CALLED ONLY AFTER A RUN THAT MADE PROVABLE PROGRESS, and the input is
        what enforces that. There are two such runs and no others:

          * one that covered its whole window, which stores the window end and
            no backlog;
          * one that stopped at its own cap, which stores the unchanged floor
            plus the boundary the next window must close at. See the module
            docstring for why that is safe on a newest-first endpoint and why
            it takes two fields.

        A run that FAILED part way stores nothing, which is the case this
        method's caller still refuses: a transport failure is not a statement
        about what the window holds, and recording one would turn it into a
        permanent gap in the customer's index.
        """
        document = checkpoint_document(
            stanza,
            window_end,
            digests,
            artifacts,
            self._now(),
            backlog_end=backlog_end,
            backlog_target=backlog_target,
        )
        if document is None:
            return False

        data = self._data()
        if data is None:
            return False

        try:
            # batch_save upserts. insert would fail with a conflict on every
            # run after the first, which is every run that matters.
            data.batch_save(document)
        except Exception as error:
            self._degrade("write", error)
            return False

        self.writes += 1
        ps_log.debug(
            LOG_COMPONENT,
            "write",
            "ok",
            records=int(artifacts),
            collection=self._collection,
        )
        return True
