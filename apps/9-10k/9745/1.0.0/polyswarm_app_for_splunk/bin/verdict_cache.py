"""KV store verdict cache for the PolySwarm App.

THE CACHE IS AN OPTIMISATION, NEVER A CORRECTNESS DEPENDENCY.

That sentence is the whole design of this module and every branch below is
written to keep it true. A search that would have worked without a cache must
still work when the collection is missing, when the running role cannot read
it, when splunkd is down, when a document is malformed, and when a clock has
gone backwards. In every one of those cases this module reports a miss or does
nothing, records one structured log line, and returns. Nothing here raises into
a search.

The reason it earns its place at all is commercial rather than technical. This
app meters per API call, one request per distinct indicator, so the second
search over the same fleet of endpoint events costs the customer a second full
quota draw unless the first search's answers are still on hand. Design section
4.1 sets the default lifetime at 24 hours; section 4.8 builds the triage
dashboard on top of it, so that opening a dashboard is not a metered event.

One cache, every indicator type. cmd_search routes a value to an endpoint by
type, and both endpoints it routes to answer in the same shape, so there is one
collection keyed on the value that was queried and no per-type partition. See
the note on DOCUMENT_ID_PREFIX for the key scheme and for the one thing the
caller has to tell this module: whether the value's case may be folded.

What is cached
--------------
The API response body, verbatim, as JSON. Not the banded verdict, and not the
output fields. Two reasons:

  1. The band thresholds and the coverage gate are this app's reading of the
     platform's answer, and that reading changes with a code release. A cache
     of derived fields would keep serving last release's interpretation for a
     day after an upgrade. A cache of the response re-reads correctly the
     moment the reader changes.
  2. There is exactly one reader of the response shape, by decision of record
     D4. Storing derived fields would make this module a second reader.

A not-found is cached too. See the write-through note on put().

The same document also carries the attribution response body, verbatim, in its
own field, on exactly the same doctrine: the platform's answer is stored and
this app's reading of it is applied fresh on the way out. See the note on
ATTRIBUTION_FIELD for the one place in this module where the presence of a key
carries meaning, and why "asked and there is none" has to be told apart from
"never asked".

Freshness
---------
Each document carries its own ttl_seconds, and the stored value wins over the
default handed to the reader. That is what lets a cached not-found expire
sooner than a cached answer: the shorter lifetime is written into the document
at store time and travels with it, rather than being a rule the reader has to
remember to apply to the right documents.

Layering
--------
    document_id_for()   pure, no I/O
    read_document()     pure, no I/O: one raw document to a CacheEntry or None
    VerdictCache        the I/O seam, one instance per search
    get() / put()       module level convenience over VerdictCache

Everything except VerdictCache is testable with no splunkd and no fake at all.
VerdictCache is testable with a fake service, which is how the tests drive it.
"""

import hashlib
import json
import time

import ps_log

APP_NAME = "polyswarm_app_for_splunk"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "verdict_cache"

# The collection declared in default/collections.conf. One name, one home.
COLLECTION_NAME = "ps_verdict_cache"

# Default lifetime of a cached answer, in seconds. Design section 4.1.
DEFAULT_TTL_SECONDS = 86400

# Lifetime of a cached not-found, in seconds.
#
# Shorter than an answer's on purpose. "We have never seen this artifact" is
# the one verdict that is expected to change without warning: a file unknown to
# the platform at nine in the morning can have been submitted, scanned, and
# banded malicious by ten. Holding a not-found for a full day would report a
# now-known malicious artifact as unknown for the rest of that day, which is a
# worse failure than paying for the lookup again.
MISS_TTL_SECONDS = 3600

# Document id prefix, and the id scheme behind it.
#
# THIS CACHE KEYS ON THE QUERIED VALUE, WHATEVER TYPE IT IS. It was a hash
# cache; it is now an indicator cache, because cmd_search routes by IOC type and
# the value it looked up is as likely to be a URL as a hash. Nothing in this
# module classifies anything, and that is the point: one collection, one key
# space, keyed on exactly the string that was sent to the API.
#
# THE DOCUMENT ID IS A DIGEST OF THAT VALUE, NOT THE VALUE ITSELF. Three
# reasons, and only the first is cosmetic:
#
#   1. A value is no longer bounded in length. A hash is 64 characters; a URL
#      out of a proxy log can be thousands, and a KV store document id is an
#      indexed field with a length limit of its own.
#   2. It reaches splunkd as a path segment. splunklib does quote it
#      (query_by_id wraps the id in UrlEncoded with encode_slash=True), so that
#      hazard is handled rather than hypothetical, but the encoded form of a
#      long URL is longer still and a GET whose path is a re-encoded URL is not
#      a request anyone wants to debug from a customer's splunkd log.
#   3. It would put the customer's raw URLs, their query strings, and any
#      credentials embedded in them into a document id. ps_log already refuses
#      to carry an indicator for that reason, and an id is the worse place for
#      one: it does not age out on a log rotation.
#
# A sha256 of the value is 64 characters whatever went in, needs no quoting in
# a path, and is deterministic, which is the only property a cache key needs.
# It also removes the type-collision worry the previous prefix existed for: two
# different values cannot share a document, and one value is one document
# regardless of which endpoint answered for it.
#
# MIGRATION, STATED RATHER THAN DISCOVERED. Documents written by an earlier
# build carry the old hash_<value> id and will never be read again. Nothing
# breaks, because the cache is an optimisation and never a correctness
# dependency: a miss on every one of them is the same answer as an empty
# collection, which is a supported state on every path in this module. They
# expire on their own stored ttl_seconds and splunkd reclaims them. The cost is
# one round of re-lookups after an upgrade, and this app has no released install
# base to charge that to. The collection name and every field name inside a
# document are unchanged, so nothing else in the app had to move.
DOCUMENT_ID_PREFIX = "ioc_"

# The KV store's own document id field.
ID_FIELD = "_key"

PAYLOAD_FIELD = "payload"
STORED_AT_FIELD = "stored_at"
TTL_FIELD = "ttl_seconds"

# The attribution response body, JSON encoded, in the same document.
#
# ONE DOCUMENT PER INDICATOR CARRIES BOTH ANSWERS, AND THAT IS THE POINT.
# The verdict and the attribution are two requests about the same indicator,
# made in the same enrichment pass, expiring together. A second collection
# would have doubled the key scheme, the freshness arithmetic and the
# degradation paths to hold a second field, and it would have let the two drift
# out of step: a fresh verdict beside a stale attribution is a state nothing in
# this app knows how to read.
#
# THE FIELD BEING ABSENT AND THE FIELD BEING "null" ARE DIFFERENT FACTS, AND
# BOTH ARE REAL. This is the one place in this module where the presence of a
# key carries meaning, so it is spelled out:
#
#   absent        attribution was never asked for. The ordinary case, because
#                 the attribution option is off by default per constraint C11.
#                 A reader that treated this as "no attribution exists" would
#                 serve an empty answer to a later attribution=true search,
#                 which is a wrong answer rather than a wasted lookup.
#   "null"        attribution WAS asked for and the platform holds none. A real
#                 cached answer, exactly as a stored "null" payload is a real
#                 cached not-found. No second request is owed.
#   a JSON object attribution was asked for and the platform answered.
#
# CacheEntry carries that distinction as attribution_fetched, and the caller
# reads it rather than inferring it from a None.
ATTRIBUTION_FIELD = "attribution"

# splunkd answers a read for a document that is not there with a 404. That is
# an ordinary cache miss, not a fault, so it is told apart from every other
# failure and does not count as a degradation or produce a log line. Getting
# this wrong in the other direction would log once per unknown hash, which on a
# wide search is thousands of lines saying nothing happened.
NOT_FOUND_STATUSES = (404,)


class CacheEntry(object):
    """One fresh document read back out of the collection.

    An entry existing is the answer to "was this indicator in the cache". The
    payload being None is the answer to "and what did the platform say", where
    None means the platform reported nothing on it. Those are two different
    questions and this class is why they do not get collapsed into one: a true
    miss is a CacheEntry of None, and a cached not-found is a CacheEntry whose
    payload is None.
    """

    __slots__ = (
        "payload",
        "stored_at",
        "ttl_seconds",
        "attribution",
        "attribution_fetched",
    )

    def __init__(
        self,
        payload,
        stored_at,
        ttl_seconds,
        attribution=None,
        attribution_fetched=False,
    ):
        self.payload = payload
        self.stored_at = stored_at
        self.ttl_seconds = ttl_seconds

        # The attribution response body, or None. None means either "asked and
        # the platform holds none" or "never asked", and attribution_fetched is
        # which. Both default so that every caller written before attribution
        # existed constructs an entry unchanged.
        self.attribution = attribution
        self.attribution_fetched = bool(attribution_fetched)

    @property
    def found(self):
        """True when the cached answer is a real platform response."""
        return self.payload is not None

    def __repr__(self):
        # No payload and no attribution content. An attribution body carries
        # family and actor names, which are the customer's investigation rather
        # than this app's diagnostics, and a repr ends up in a traceback.
        return (
            "<CacheEntry found={0!r} stored_at={1!r} ttl_seconds={2!r} "
            "attribution_fetched={3!r}>".format(
                self.found,
                self.stored_at,
                self.ttl_seconds,
                self.attribution_fetched,
            )
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def document_id_for(ioc_value, fold_case=True):
    """Return the document id for one indicator value, or None when unusable.

    See the note on DOCUMENT_ID_PREFIX for why the id is a digest.

    WHY CASE FOLDING IS THE CALLER'S DECISION AND NOT THIS MODULE'S.
    ---------------------------------------------------------------
    Whether two spellings of a value are the same value is a property of the
    IOC type, and this module does not know the type. It is handed one.

    Folding is right for a hash: different log sources genuinely disagree about
    hash case for the same file, and two spellings must not become two documents
    and two billable lookups. It is right for a bare host, which DNS treats
    case insensitively. It is WRONG for a URL, whose path and query are case
    sensitive by specification, so /Report and /report are two resources.
    Folding those together would serve one cached verdict for both, which is not
    a wasted lookup but a wrong answer, and a wrong answer is the one thing a
    cache is never allowed to produce.

    So the default is True, which preserves the folding this function has always
    done for hashes, and cmd_search passes False for a url. Getting it wrong in
    the safe direction, by not folding something that could have been folded,
    costs one extra lookup and cannot corrupt an answer.

    :param ioc_value: the value that was queried: a hash, a URL, or a host.
    :param fold_case: lowercase the value before digesting it.
    :return: the document id, or None when there is nothing to key on.
    """
    if ioc_value is None:
        return None
    text = str(ioc_value).strip()
    if fold_case:
        text = text.lower()
    if not text:
        return None
    return DOCUMENT_ID_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_document(document, default_ttl_seconds=DEFAULT_TTL_SECONDS, now=None):
    """Turn one raw KV store document into a CacheEntry, or None.

    Pure. None is returned for every unusable document, and unusable is
    deliberately broad: not a mapping, no readable timestamp, no readable
    payload, or past its lifetime. All of those mean the same thing to the
    caller, which is that there is nothing here to use, so they are not
    distinguished. A malformed document is a miss rather than an error, because
    the alternative is failing a customer's search over a bad row in a cache.

    :param document: the mapping splunkd returned.
    :param default_ttl_seconds: lifetime to apply when the document does not
        carry its own. The document's own value wins when it has one.
    :param now: epoch seconds, for tests. Defaults to time.time().
    :return: a CacheEntry, or None.
    """
    if not isinstance(document, dict):
        return None

    stored_at = _as_float(document.get(STORED_AT_FIELD))
    if stored_at is None:
        # No readable write time means the document cannot be aged, and an
        # entry that cannot be aged cannot be trusted to expire.
        return None

    ttl_seconds = _as_float(document.get(TTL_FIELD))
    if ttl_seconds is None:
        ttl_seconds = float(default_ttl_seconds)
    if ttl_seconds <= 0:
        return None

    moment = time.time() if now is None else float(now)
    age = moment - stored_at

    # A negative age is a document written in the future: a clock that moved
    # backwards, or a search head disagreeing with the one that wrote it. Left
    # alone such a document would be immortal, since its age never reaches the
    # lifetime. Treated as a miss it costs one lookup and then gets rewritten
    # with this host's own clock, which repairs it.
    if age < 0 or age > ttl_seconds:
        return None

    raw = document.get(PAYLOAD_FIELD)
    if not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None

    # The attribution half. Read separately and never allowed to fail the
    # document, because a document written before attribution existed carries
    # no such field and is still a perfectly good cached verdict. An
    # unparseable attribution reads as never fetched rather than as a corrupt
    # document, for the same reason: the verdict beside it is intact and
    # failing the whole document would re-bill a lookup that is already paid
    # for.
    attribution = None
    attribution_fetched = False
    raw_attribution = document.get(ATTRIBUTION_FIELD)
    if isinstance(raw_attribution, str):
        try:
            attribution = json.loads(raw_attribution)
        except ValueError:
            attribution = None
        else:
            attribution_fetched = True

    return CacheEntry(
        payload,
        stored_at,
        ttl_seconds,
        attribution=attribution,
        attribution_fetched=attribution_fetched,
    )


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
    have to import splunklib's binding layer, and so a test can drive the
    branch with a plain exception carrying a status.
    """
    for attribute in ("status", "code"):
        if getattr(error, attribute, None) in NOT_FOUND_STATUSES:
            return True
    return False


# ---------------------------------------------------------------------------
# The cache
# ---------------------------------------------------------------------------


class VerdictCache(object):
    """Reads and writes the verdict cache for the duration of one search.

    One instance per search, holding the counters a caller and the health
    surface want: hits, misses, stores, and whether anything degraded. Nothing
    is held at module scope, so a cache cannot outlive the search that made it.

    Every method swallows every exception from splunkd. That is not a catch-all
    that fabricates data, which C6 forbids: nothing is invented on any of these
    paths. A failed read reports the same miss it would have reported had the
    document simply not been there, and a failed write does nothing at all. The
    caller's behaviour with a broken cache is exactly its behaviour with an
    empty one.
    """

    def __init__(
        self,
        service,
        ttl_seconds=DEFAULT_TTL_SECONDS,
        miss_ttl_seconds=MISS_TTL_SECONDS,
        collection=COLLECTION_NAME,
        now=None,
    ):
        """
        :param service: the splunklib service a search command holds as
            self.service. None is accepted and disables the cache, which is the
            case when the command is driven outside splunkd.
        :param ttl_seconds: default lifetime for a cached answer.
        :param miss_ttl_seconds: lifetime for a cached not-found.
        :param collection: the collection name, for tests.
        :param now: a callable returning epoch seconds, for tests.
        """
        self._service = service
        self._collection = collection
        self._now = time.time if now is None else now

        self.ttl_seconds = float(ttl_seconds)
        self.miss_ttl_seconds = float(miss_ttl_seconds)

        self.hits = 0
        self.misses = 0
        self.stores = 0

        # True once anything has failed. Read by the caller so a search can
        # report that it ran without a cache rather than leaving an operator to
        # wonder why every hash cost a request.
        self.degraded = False

    # -- the collection --------------------------------------------------

    def _data(self):
        """Return the collection's data endpoint, or None when unreachable.

        Every reason it could be None is the same reason as far as the caller
        is concerned: there is no cache this search. A missing collection, a
        role without read access, and a splunkd that is not answering all land
        here.
        """
        if self._service is None:
            return None
        try:
            return self._service.kvstore[self._collection].data
        except Exception as error:
            self._degrade("open", error)
            return None

    def _degrade(self, event, error):
        """Record one failure: one counter, one log line, nothing raised.

        WARNING level, because this is the line that answers "why is every
        hash costing me a request". It is the one thing in this module an
        operator has to act on, and it is rare: a broken cache is broken for
        the whole search, so this fires once and not once per hash.

        Only the exception's class name reaches the log. The message is dropped
        deliberately, for the reason written out in ps_client.get_api_key:
        splunklib's binding layer quotes the HTTP exchange it attempted into
        its exception text, and a storage exchange can carry a value that
        should not be in a log file. A class name is the diagnostically useful
        half and cannot carry a payload.
        """
        self.degraded = True
        ps_log.warning(
            LOG_COMPONENT,
            event,
            "degraded",
            reason=type(error).__name__,
            collection=self._collection,
        )

    # -- reads -----------------------------------------------------------

    def get_entry(self, ioc_value, fold_case=True):
        """Return a fresh CacheEntry for one indicator, or None for a miss.

        A miss and a degraded cache are the same answer on purpose. See the
        class docstring.

        EVERY OUTCOME IS LOGGED, AND EVERY ONE OF THEM AT DEBUG.
        --------------------------------------------------------
        A hit and a miss are each one line, because an operator investigating a
        quota bill needs to see the hit rate and not just the total, and there
        is no other place that number comes from. They are at DEBUG because
        this method runs once per distinct hash: a search over ten thousand
        hashes would otherwise write ten thousand lines to report that the
        cache was working normally, which buries the one WARNING that means it
        was not. The counters on this object carry the same information in
        aggregate and are logged once per search by the command.

        No line carries the indicator. ps_log has no key it could travel under,
        which is the whitelist doing its job: the hash is the customer's data,
        and a per-hash debug line would put a copy of everything they enriched
        into a second file with a different retention. That reasoning got
        stronger when this cache started holding URLs, which carry query strings
        and sometimes credentials.

        :param ioc_value: the value that was queried.
        :param fold_case: see document_id_for(). The reader and the writer of
            one value have to agree on this or they key different documents.
        """
        document_id = document_id_for(ioc_value, fold_case=fold_case)
        if document_id is None:
            return None

        data = self._data()
        if data is None:
            self.misses += 1
            self._log_read("miss", "unavailable")
            return None

        try:
            document = data.query_by_id(document_id)
        except Exception as error:
            if _is_not_found(error):
                # The ordinary miss, and not a fault. Told apart from every
                # other failure so that it neither degrades the cache nor
                # writes a WARNING: on a wide search over hashes the platform
                # has never seen, this branch is the common case.
                self.misses += 1
                self._log_read("miss", "absent")
                return None
            self._degrade("get", error)
            self.misses += 1
            return None

        entry = read_document(document, self.ttl_seconds, now=self._now())
        if entry is None:
            # Present but unusable: past its lifetime, or malformed. Both are
            # a miss, and the reason is worth having because a cache that is
            # always stale and a cache that is always malformed look identical
            # from the hit rate alone.
            self.misses += 1
            self._log_read("miss", "stale")
            return None

        self.hits += 1
        self._log_read("hit", "found" if entry.found else "not_found")
        return entry

    def _log_read(self, event, outcome):
        """One DEBUG line per read. See the note in get_entry()."""
        ps_log.debug(LOG_COMPONENT, event, outcome, collection=self._collection)

    def get(self, ioc_value, fold_case=True):
        """Return the cached payload for one indicator, or None.

        The convenience form. It cannot tell a cached not-found from a miss,
        because both are None, so a caller that has to distinguish them uses
        get_entry(). Kept because most callers only want the payload.
        """
        entry = self.get_entry(ioc_value, fold_case=fold_case)
        if entry is None:
            return None
        return entry.payload

    # -- writes ----------------------------------------------------------

    def put(
        self,
        ioc_value,
        payload,
        ttl_seconds=None,
        fold_case=True,
        attribution=None,
        attribution_fetched=False,
        stored_at=None,
    ):
        """Store one platform answer against one indicator.

        WRITE-THROUGH INCLUDES A NOT-FOUND, and that is the point of the
        shorter lifetime. In a search over hashes taken out of an index, most
        hashes are ones the platform has never seen: ordinary in-house
        binaries, installer temp files, and everything else a fleet writes to
        disk. If a not-found is not cached, every one of those is re-billed on
        every subsequent search over the same data, and the cache saves quota
        only on the small malicious minority, which is the opposite of what the
        customer needs. So a not-found is a cached answer like any other, held
        for MISS_TTL_SECONDS rather than the full day because it is the answer
        most likely to change underneath us.

        :param ioc_value: the value that was queried.
        :param payload: the decoded response body, or None for a not-found.
        :param ttl_seconds: lifetime override. None uses this cache's default
            for an answer, and miss_ttl_seconds for a not-found.
        :param fold_case: see document_id_for(). Must match what the reader of
            this value passes, or the write lands on a document nothing reads.
        :param attribution: the decoded tag-link response body, or None for the
            platform holding no attribution for the artifact. Only written when
            attribution_fetched is true. See the note on ATTRIBUTION_FIELD:
            "asked and there is none" and "never asked" are different facts and
            None alone cannot tell them apart.
        :param attribution_fetched: whether an attribution request was actually
            made. False, the default, leaves the field off the document
            entirely, which is what every caller written before attribution
            existed does and what an attribution=false search does.
        :param stored_at: the write time to record, in epoch seconds. None,
            the default, uses this cache's clock, which is what a fresh answer
            wants.

            AN OVERRIDE EXISTS SO THAT ADDING ATTRIBUTION TO AN ALREADY-CACHED
            VERDICT DOES NOT EXTEND THE VERDICT'S LIFE. batch_save replaces the
            whole document, so re-writing one to attach an attribution would
            otherwise reset its age and keep a day-old verdict alive for
            another day, over and over, for as long as somebody kept enriching
            with attribution on. Passing the document's original stored_at back
            in means the verdict expires exactly when it always would have and
            the attribution rides along on the remaining lifetime. The caller
            passes ttl_seconds back the same way, for the same reason.
        :return: True when the document was written.
        """
        document_id = document_id_for(ioc_value, fold_case=fold_case)
        if document_id is None:
            return False

        data = self._data()
        if data is None:
            return False

        if ttl_seconds is None:
            lifetime = (
                self.ttl_seconds if payload is not None else self.miss_ttl_seconds
            )
        else:
            lifetime = float(ttl_seconds)
        if lifetime <= 0:
            return False

        try:
            encoded = json.dumps(payload)
            encoded_attribution = (
                json.dumps(attribution) if attribution_fetched else None
            )
        except (TypeError, ValueError) as error:
            self._degrade("encode", error)
            return False

        document = {
            ID_FIELD: document_id,
            PAYLOAD_FIELD: encoded,
            STORED_AT_FIELD: float(self._now() if stored_at is None else stored_at),
            TTL_FIELD: lifetime,
        }

        # Added only when an attribution request was actually made. An absent
        # field is what tells a later reader that attribution is still owed on
        # this indicator, so writing the key with a null in it when nothing was
        # asked would cache an answer nobody obtained.
        if attribution_fetched:
            document[ATTRIBUTION_FIELD] = encoded_attribution

        try:
            # batch_save rather than insert, because it upserts. insert would
            # fail with a conflict the second time a hash is stored, which
            # happens every time an entry expires and is looked up again.
            data.batch_save(document)
        except Exception as error:
            self._degrade("put", error)
            return False

        self.stores += 1
        ps_log.debug(LOG_COMPONENT, "store", "ok", collection=self._collection)
        return True


# ---------------------------------------------------------------------------
# Module level convenience
# ---------------------------------------------------------------------------


def get(service, ioc_value, ttl_seconds=DEFAULT_TTL_SECONDS, fold_case=True):
    """Return the cached payload for one indicator, or None.

    For a caller holding a service and nothing else. A search command builds a
    VerdictCache instead, so that its counters cover the whole search.

    :param service: the splunklib service.
    :param ioc_value: the value that was queried.
    :param ttl_seconds: lifetime applied to a document that does not carry its
        own. Entries older than their lifetime are a miss.
    :param fold_case: see document_id_for().
    """
    return VerdictCache(service, ttl_seconds=ttl_seconds).get(
        ioc_value, fold_case=fold_case
    )


def put(
    service,
    ioc_value,
    payload,
    ttl_seconds=None,
    fold_case=True,
    attribution=None,
    attribution_fetched=False,
    stored_at=None,
):
    """Store one platform answer. Returns True when it was written.

    :param service: the splunklib service.
    :param ioc_value: the value that was queried.
    :param payload: the decoded response body, or None for a not-found.
    :param ttl_seconds: lifetime override, in seconds.
    :param fold_case: see document_id_for().
    :param attribution: the tag-link response body. See VerdictCache.put().
    :param attribution_fetched: whether an attribution request was made.
    :param stored_at: write time override, in epoch seconds.
    """
    return VerdictCache(service).put(
        ioc_value,
        payload,
        ttl_seconds=ttl_seconds,
        fold_case=fold_case,
        attribution=attribution,
        attribution_fetched=attribution_fetched,
        stored_at=stored_at,
    )
