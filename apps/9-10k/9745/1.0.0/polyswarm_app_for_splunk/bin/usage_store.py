"""KV store state for the usage and entitlement surface.

Two collections and two jobs, and they are here together because both are the
same kind of thing: state that has to outlive one search so that a dashboard
can be cheap to open.

    ps_usage_throttle   one document, the last time | polyswarmusage called out
    ps_usage_cache      one document per emitted row, the last successful answer

WHY THERE IS A THROTTLE AT ALL
------------------------------
The two endpoints behind this surface are account endpoints. They are not
artifact lookups: nothing is submitted, scanned, or detonated, so they consume
none of the scan or detonation allowance a customer buys. That is what makes the
setup page's test-credentials button reasonable and what makes design 4.6's
usage page possible at all.

It is not the same as free. P0-6, quota semantics per endpoint, is still open,
so whether an account read counts against an api_requests feature is a question
this app does not have the answer to. And a dashboard panel is not a person: a
panel left open with an auto-refresh interval on it issues a request per
interval, per open browser tab, forever, and nothing in Splunk stops it. So the
guard is structural rather than advisory. The dashboard's token gate is the
other half, in default/data/ui/views/overview.xml, and neither half is
sufficient on its own: a token gate stops the page firing on load, and this
stops anything at all firing more than once a minute.

THE WINDOW IS CONSUMED BEFORE THE CALL, NOT AFTER
-------------------------------------------------
record_attempt() is called before the API calls, so a failing call still spends
the window. That ordering is deliberate and it is the opposite of what an
optimising reader would write. A window consumed only on success is a window
that lets a failing endpoint be retried as fast as a dashboard can dispatch,
which is exactly the condition where hammering is least welcome and most likely.
A window consumed by a failure costs a customer one minute of a stale panel.

THE THROTTLE FAILS OPEN, AND THAT IS A DECISION
-----------------------------------------------
Every KV failure here reports "not throttled" and logs one line. Fail closed was
considered and rejected: a search head with a broken KV store would then refuse
the usage surface permanently, with a throttle message and no way out, and the
customer's remedy would be to fix a cache in order to read their own quota. The
thing being protected is an endpoint that spends no artifact quota, reached
through a command a person has to invoke; the thing being risked by failing
closed is the surface itself. So it fails open and says so out loud, in the log
and in a warning to the analyst.

RELATION TO verdict_cache.py
----------------------------
The doctrine is that module's: state here is an optimisation and never a
correctness dependency, every splunkd exception is swallowed, and a broken
collection reads exactly like an empty one. What is different is the shape.
verdict_cache holds one document per indicator and is read by document id, one
at a time, which is what an enrichment command needs. This holds a handful of
documents that are read all at once by a dashboard through an | inputlookup, so
the rows are stored one per document with deterministic ids rather than as one
blob: a lookup definition cannot decompose a blob.

Layering
--------
    throttle_document()   pure, no I/O: build the throttle document
    read_last_run()       pure, no I/O: one raw document to a timestamp or None
    is_throttled()        pure, no I/O: the arithmetic
    row_document_id()     pure, no I/O
    UsageStore            the I/O seam, one instance per search
"""

import time

import ps_log

APP_NAME = "polyswarm_app_for_splunk"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "usage_store"

# The collections declared in default/collections.conf. One name, one home.
#
# Both carry the app's ps_ prefix, matching ps_verdict_cache. The collections
# are exported system wide (since 2026-09-09) so lookups against them resolve
# from any app, which makes the prefix load bearing: a bare name could collide
# with another app's collection, and a reader looking at a KV store listing on
# a search head sees which app owns what.
CACHE_COLLECTION_NAME = "ps_usage_cache"
THROTTLE_COLLECTION_NAME = "ps_usage_throttle"

# How long one search head has to wait between calls to the account endpoints.
#
# Sixty seconds is chosen against the thing being defended rather than against
# a rate limit nobody has measured: Splunk's shortest selectable dashboard
# refresh interval is well under a minute, and a person pressing a refresh
# input twice in a minute is asking for the same answer twice.
THROTTLE_SECONDS = 60.0

# The throttle is one document, not one per user or per search. The endpoint is
# shared, the key is shared, and the account is shared, so the window is too.
THROTTLE_DOCUMENT_ID = "usage"

# Document id prefix for a cached row, so an operator reading the collection can
# tell what a document is and so a row id cannot collide with anything a later
# writer puts in the same collection.
ROW_DOCUMENT_ID_PREFIX = "row_"

# The KV store's own document id field.
ID_FIELD = "_key"

LAST_RUN_FIELD = "last_run_at"
FETCHED_AT_FIELD = "fetched_at"

# splunkd answers a read for a document that is not there with a 404. For the
# throttle that is the ordinary state on a search head where nobody has run the
# command yet, so it is told apart from a real failure and produces no warning.
NOT_FOUND_STATUSES = (404,)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def row_document_id(index, row_type, name=None):
    """Return a deterministic document id for one emitted row.

    Deterministic on purpose. A row that is still present on the next refresh
    overwrites its own document rather than adding a second one, so the
    collection stays the size of the answer and not the size of the history.
    The index is included so that ordering survives a round trip through a
    lookup, which returns documents in no particular order.

    :param index: the row's position in the emitted sequence.
    :param row_type: the row's kind, for example account or feature.
    :param name: the feature name, where the row has one.
    """
    parts = [str(int(index)).zfill(3), str(row_type)]
    if name:
        parts.append(str(name))
    return ROW_DOCUMENT_ID_PREFIX + "_".join(parts)


def throttle_document(now):
    """Return the throttle document for a call being made at now. Pure."""
    return {ID_FIELD: THROTTLE_DOCUMENT_ID, LAST_RUN_FIELD: float(now)}


def read_last_run(document):
    """Return the last call time out of a raw throttle document, or None.

    Pure. None for every unusable document, and unusable is deliberately broad:
    not a mapping, or no readable timestamp. Both mean the same thing to the
    caller, which is that there is no window to respect.
    """
    if not isinstance(document, dict):
        return None
    return _as_float(document.get(LAST_RUN_FIELD))


def is_throttled(last_run_at, now, window_seconds=THROTTLE_SECONDS):
    """True when a call at now would fall inside the window. Pure.

    :param last_run_at: the previous call time, or None when there was none.
    :param now: epoch seconds.
    :param window_seconds: the minimum gap between calls.
    """
    if last_run_at is None:
        return False
    try:
        elapsed = float(now) - float(last_run_at)
    except (TypeError, ValueError):
        return False

    # A negative elapsed time is a document written in the future: a clock
    # corrected backwards, or another search head in the cluster disagreeing
    # with this one. Treated as throttled rather than as permission to call,
    # because the reading it supports is "somebody just called", and a document
    # that cannot be aged must not be the thing that opens the gate. It clears
    # on its own: the next call inside the window rewrites the timestamp with
    # this host's clock.
    if elapsed < 0:
        return True

    return elapsed < float(window_seconds)


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
    plain exception carrying a status. Same approach as verdict_cache.
    """
    for attribute in ("status", "code"):
        if getattr(error, attribute, None) in NOT_FOUND_STATUSES:
            return True
    return False


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------


class UsageStore(object):
    """Reads the throttle and writes the cache for one invocation.

    One instance per search. Nothing at module scope, so state cannot outlive
    the search that made it.

    Every method swallows every exception from splunkd, and none of them
    fabricates anything. A failed throttle read reports not throttled, which is
    the same answer an empty collection gives; a failed write does nothing at
    all. Constraint C6 forbids a catch-all that invents data, and nothing is
    invented on any of these paths.
    """

    def __init__(
        self,
        service,
        window_seconds=THROTTLE_SECONDS,
        cache_collection=CACHE_COLLECTION_NAME,
        throttle_collection=THROTTLE_COLLECTION_NAME,
        now=None,
    ):
        """
        :param service: the splunklib service a search command holds as
            self.service. None is accepted and disables both collections, which
            is what happens when the command is driven outside splunkd.
        :param window_seconds: the minimum gap between calls.
        :param cache_collection: collection name, for tests.
        :param throttle_collection: collection name, for tests.
        :param now: a callable returning epoch seconds, for tests.
        """
        self._service = service
        self._cache_collection = cache_collection
        self._throttle_collection = throttle_collection
        self._now = time.time if now is None else now

        self.window_seconds = float(window_seconds)

        self.stores = 0

        # True once anything has failed. Read by the command so an operator is
        # told the throttle could not be applied rather than left to assume it
        # was.
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

    # -- the throttle ----------------------------------------------------

    def last_run_at(self):
        """Return the last recorded call time, or None.

        None covers all of: nobody has called yet, the collection is absent,
        the running role cannot read it, splunkd is not answering, and the
        document is malformed. The caller cannot act on the difference, and
        conflating them is what makes the fail-open behaviour one code path
        rather than five.
        """
        data = self._data(self._throttle_collection)
        if data is None:
            return None

        try:
            document = data.query_by_id(THROTTLE_DOCUMENT_ID)
        except Exception as error:
            if _is_not_found(error):
                # Nobody has run the command on this search head yet. The
                # ordinary state, not a fault, so no warning and no
                # degradation: a first run must not report a broken throttle.
                ps_log.debug(
                    LOG_COMPONENT,
                    "throttle_read",
                    "absent",
                    collection=self._throttle_collection,
                )
                return None
            self._degrade("throttle_read", error, self._throttle_collection)
            return None

        return read_last_run(document)

    def throttled(self):
        """True when a call now would fall inside the window.

        FAILS OPEN. See the module docstring: a search head whose KV store is
        broken must not lose the usage surface permanently.
        """
        last = self.last_run_at()
        blocked = is_throttled(last, self._now(), self.window_seconds)
        ps_log.debug(
            LOG_COMPONENT,
            "throttle",
            "throttled" if blocked else "ok",
            collection=self._throttle_collection,
        )
        return blocked

    def record_attempt(self):
        """Write the throttle timestamp. Returns True when it was written.

        Called BEFORE the API calls, not after. See the module docstring.
        """
        data = self._data(self._throttle_collection)
        if data is None:
            return False

        try:
            # batch_save upserts. insert would fail with a conflict on every
            # call after the first, which is every call that matters.
            data.batch_save(throttle_document(self._now()))
        except Exception as error:
            self._degrade("throttle_write", error, self._throttle_collection)
            return False

        ps_log.debug(
            LOG_COMPONENT,
            "throttle_write",
            "ok",
            collection=self._throttle_collection,
        )
        return True

    # -- the cache -------------------------------------------------------

    def write_through(self, rows):
        """Store the rows of one successful answer. Returns rows written.

        WRITE-THROUGH, AND ONLY OF A SUCCESS. A failed or throttled invocation
        writes nothing, because a failure is not an answer and caching one would
        put a transient fault on the Overview dashboard for as long as the next
        success took to arrive.

        Deterministic document ids mean a feature still present on the next
        refresh overwrites its own document. A feature that has gone away leaves
        its document behind, which is why every row carries fetched_at and why
        the dashboard reads only the newest generation: deleting the collection
        first would be a destructive operation that can fail halfway and leave
        the panel showing half an answer.

        :param rows: the emitted rows, in order, each a mapping.
        :return: the number of rows written.
        """
        if not rows:
            return 0

        data = self._data(self._cache_collection)
        if data is None:
            return 0

        documents = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            document = dict(
                (name, value) for name, value in row.items() if value is not None
            )
            document[ID_FIELD] = row_document_id(
                index, row.get("row_type"), row.get("feature")
            )
            documents.append(document)

        if not documents:
            return 0

        try:
            data.batch_save(*documents)
        except Exception as error:
            self._degrade("cache_write", error, self._cache_collection)
            return 0

        self.stores += len(documents)
        ps_log.debug(
            LOG_COMPONENT,
            "cache_write",
            "ok",
            records=len(documents),
            collection=self._cache_collection,
        )
        return len(documents)
