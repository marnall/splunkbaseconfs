"""Which PolySwarm community a detonation is sent to.

Design section 4.3 asks that "every submission carries an explicit public or
private community choice, defaulting to the account's most-private entitled
community, never silently public". Decision D12 shipped URL detonation without
that and said so: the app sent the SDK's own `default` and let the platform
resolve it. This module is the deferred piece, and it is one module rather than
a branch inside the command because two callers need the same answer: the
`polyswarmdetonate` command and the PolySwarm Detonate alert action.

THE RULE, IN THE ORDER IT IS APPLIED
------------------------------------
1. **The operator's answer, if they gave one.** `polyswarm.conf`'s
   `[settings] community`, which the setup page writes into `local/`. A
   non-blank value wins outright and no request is made to find out anything.
   An operator who typed a community name into a form is not asking the app to
   audit the choice, and an app that overrode it would be unusable in exactly
   the deployment that cares: one whose analysts must detonate into a named
   private community.
2. **The most private entitled community, from whois.** The account's
   `communities` list, with the public one removed. See the ordering note below
   for what "most private" can honestly mean here.
3. **`default`, which is what the app has always sent.** The platform then
   resolves the account's own community, and the task row records where the
   detonation actually went.

WHAT "MOST PRIVATE" CAN MEAN, AND WHAT IT CANNOT
------------------------------------------------
The platform exposes no privacy rank. Design 4.3 says as much from the other
direction: public instances carry arbitrary shard names, so classification is
by membership match rather than by a shard-name allowlist. So the only ranking
this module can make honestly is a two-way one, and it is a membership
statement rather than a name pattern: `public` is the community every account
is in, and anything else in the list is one this account was added to.

That leaves the case of an account entitled to more than one non-public
community, and there the answer is a coin flip dressed as a decision. Three
options were considered:

  * **Refuse to detonate and make the operator choose.** Rejected: it withholds
    the capability from exactly the accounts that paid for it, and the operator
    already has a place to make the choice, which is option 1 above.
  * **Take the first entry the platform listed.** Rejected: whois's list order
    is not documented as stable, so the same account could detonate into two
    different communities on two days with nothing changed.
  * **Sort and take the first.** Chosen. It is arbitrary and it is STABLE, which
    is the property that matters: the same account resolves to the same
    community on every search head on every day, and the row records it either
    way. An operator who wants the other one sets it in the setup page and
    option 1 takes over.

**PROVISIONAL: no recorded response carries a private community.**
`tests/fixtures/whois-recorded.json` pins the shape, `communities` as a list of
strings, and its value is `["public"]`, because the key that recording was taken
with is public scoped. So the one thing the recording does not pin is what a
private community's entry looks like, and the consequence is worth stating
plainly: **on that account this module resolves to `default` and the app behaves
exactly as D12 shipped it.** Branch 2 fires only for an account whose whois
lists something else, which is the "Erick Partner OEM" team key design section
9 names for private-community paths, and it has not been run against one. That
is the same outstanding C10 item as the rest of Phase 2.

WHY THE ANSWER IS CACHED, AND FOR HOW LONG
------------------------------------------
Without a cache, every detonation carries a whois request in front of it, which
is the defect the providers cache exists to prevent one call further along the
same path. One hour rather than the providers cache's twenty four, because the
two answers change on different clocks: a provider list is a set of sandbox
images that moves on a release cadence, and an account's community membership
moves when somebody at PolySwarm adds a team, which is a support conversation
happening while the customer waits.

**A failure is never cached and never refuses the detonation.** This is the
opposite of the providers cache's fail-closed rule, and the difference is what
each one protects. A providers call that fails takes away the check in front of
the most expensive call in the product, so it refuses. A whois call that fails
takes away an improvement on the behaviour the app already shipped: falling back
to `default` sends the detonation where D12 sent every detonation, the platform
resolves the account's own community, and the row records the answer. Refusing
instead would mean an account whose whois is briefly unavailable cannot
detonate at all, which trades a working feature for a scoping preference.

What the caller does about that fallback is not nothing: `Resolution.degraded`
is true, and `cmd_detonate` puts a warning in front of the analyst naming the
community it used. A silent fallback is what would make this dishonest.
"""

import json
import time

import ps_log
import ps_client

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "community"

# The conf file, stanza and setting the setup page writes. One name, one home,
# and the same three strings README/polyswarm.conf.spec documents.
CONF_FILE = "polyswarm"
CONF_STANZA = "settings"
CONF_SETTING = "community"

# The whois key carrying the account's entitled communities. Pinned by
# tests/fixtures/whois-recorded.json.
COMMUNITIES_FIELD = "communities"

# The envelope, recognised by the TYPE of its "result" value and never by the
# name alone, for the reason cmd_usage.unwrap carries.
ENVELOPE_FIELD = "result"

# The one community name this module reads as "not private".
#
# A MEMBERSHIP STATEMENT AND NOT A NAME PATTERN. Every account is in the public
# community, so an entry that is not this one is a community this account was
# added to. There is no allowlist of private names, no prefix rule and no
# pattern, because design 4.3 records that public instances carry arbitrary
# shard names: a name-shaped test would mislabel them.
PUBLIC_COMMUNITY = "public"

# What the app sends when it has nothing better, which is what D12 shipped and
# what ps_client sends with no community argument at all.
FALLBACK_COMMUNITY = ps_client.DEFAULT_COMMUNITY

# Where the answer came from. Recorded on the Resolution so a caller can log a
# source without logging a community name, and so a test asserts the branch
# rather than inferring it from the value.
SOURCE_CONFIGURED = "configured"
SOURCE_WHOIS = "whois"
SOURCE_FALLBACK = "fallback"

# The cache. One document, in a collection of its own for the reason
# collections.conf gives about every other pair in this app: a lookup
# definition returns every document in the collection it is pointed at, so a
# cached blob living beside rows a panel reads arrives as a row with nothing on
# it.
CACHE_COLLECTION_NAME = "ps_community_cache"
CACHE_DOCUMENT_ID = "whois"
CACHE_TTL_SECONDS = 3600

PAYLOAD_FIELD = "payload"
STORED_AT_FIELD = "stored_at"
TTL_FIELD = "ttl_seconds"

ID_FIELD = "_key"

# splunkd answers a read for a document that is not there with a 404, which on
# this collection is the ordinary first-run state.
NOT_FOUND_STATUSES = (404,)


# ---------------------------------------------------------------------------
# Pure
# ---------------------------------------------------------------------------


def read_setting(value):
    """Return the operator's configured community, or None. Pure.

    BLANK IS A MEANINGFUL VALUE AND IT IS THE SHIPPED DEFAULT. It means "let
    the app work it out", which is branches 2 and 3, and it is what
    default/polyswarm.conf and README/polyswarm.conf.spec both say. So an empty
    string, whitespace, a missing setting and a value that is not a string all
    read the same way: nothing was configured.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    return text or None


def unwrap(payload):
    """Return the body inside a v3 response envelope, or the payload. Pure."""
    if not isinstance(payload, dict):
        return None
    inner = payload.get(ENVELOPE_FIELD)
    if isinstance(inner, dict):
        return inner
    return payload


def read_communities(payload):
    """Return the account's entitled communities as a list. Pure.

    THE SECOND READER OF THIS FIELD IN THIS APP, and the first is
    cmd_usage.read_communities, which joins the same list into one display
    string for a row in the entitlement table. They are not the same function
    because they answer different questions: that one renders, this one
    decides, and a decision needs the entries apart. They must agree about what
    the list holds, and a test asserts that they do against the recorded whois
    response rather than leaving it to inspection.

    A mapping is refused, exactly as it is there: a communities object keyed by
    something is a different shape, and picking its keys or its values would be
    a guess about which of the two the names are. A single string is read as a
    list of one, which is container tolerance and not a field alias.
    """
    body = unwrap(payload)
    if not isinstance(body, dict):
        return []

    value = body.get(COMMUNITIES_FIELD)
    if isinstance(value, dict):
        return []
    if not isinstance(value, (list, tuple)):
        single = read_setting(value)
        return [single] if single is not None else []

    names = []
    for entry in value:
        text = read_setting(entry)
        if text is not None and text not in names:
            names.append(text)
    return names


def most_private(names):
    """Return the most private entitled community, or None. Pure.

    None when the account is entitled to nothing but the public community,
    which is what the recorded whois response says and which is why branch 3
    exists. See the module docstring for why the pick among several is a sort
    and not the platform's own order.

    The comparison folds case, because `Public` and `public` are one community
    and a fold is not a guess about a name's meaning. The value returned is the
    entry AS THE PLATFORM SPELLED IT, because it goes on the wire and into the
    task row.
    """
    if not isinstance(names, (list, tuple)):
        return None
    private = [
        name
        for name in names
        if read_setting(name) is not None
        and str(name).strip().lower() != PUBLIC_COMMUNITY
    ]
    if not private:
        return None
    return sorted(str(name).strip() for name in private)[0]


# What a cache read answers with when there is nothing usable stored. A pair
# rather than None, for the reason read_cached_entry gives.
MISS = (False, None)


def read_cached_entry(document, ttl_seconds=CACHE_TTL_SECONDS, now=None):
    """Return (hit, payload) for one raw cached document. Pure.

    A PAIR AND NOT A PAYLOAD, BECAUSE A STORED NOTHING IS AN ANSWER. The
    platform answers a 204 or a 404 with no body, `ps_client` returns None for
    both, and that is a real fact about the account rather than a failure. If
    this returned the payload alone, that fact would be indistinguishable from
    an empty cache, and the app would ask whois again on every single
    detonation for exactly the accounts whose whois has nothing to say. This is
    the same distinction `verdict_cache.CacheEntry` carries for a cached
    not-found, and it is the reason that module returns an entry rather than a
    body.

    A miss for every unusable document, and unusable is deliberately broad: not
    a mapping, no readable write time, past its lifetime, or a payload that does
    not decode. All of them mean the same thing to the caller, which is one
    whois call. A negative age is a document written in the future, by a
    corrected clock or another search head, and reads as a miss because a
    document that cannot be aged would be immortal.
    """
    if not isinstance(document, dict):
        return MISS

    stored_at = _as_float(document.get(STORED_AT_FIELD))
    if stored_at is None:
        return MISS

    lifetime = _as_float(document.get(TTL_FIELD))
    if lifetime is None:
        lifetime = float(ttl_seconds)
    if lifetime <= 0:
        return MISS

    moment = time.time() if now is None else float(now)
    age = moment - stored_at
    if age < 0 or age > lifetime:
        return MISS

    raw = document.get(PAYLOAD_FIELD)
    if not isinstance(raw, str):
        return MISS
    try:
        return (True, json.loads(raw))
    except ValueError:
        return MISS


def read_cached_document(document, ttl_seconds=CACHE_TTL_SECONDS, now=None):
    """Return the cached whois payload out of a raw document, or None. Pure.

    THE THIRD IMPLEMENTATION OF ONE DOCUMENT SHAPE IN THIS APP, and the
    duplication is named rather than hidden: `verdict_cache.read_document` and
    `task_store.read_cached_providers` read the same three fields with the same
    rules. A shared helper is the obvious tidy-up and it would have to live in a
    module none of the three owns, so what guards the duplication instead is a
    test asserting this function and task_store's agree document for document.

    It is kept as the payload-only form for exactly that reason, and the
    freshness logic lives once, in read_cached_entry above. Nothing in this
    module calls this: the caller needs the pair, because a stored nothing is
    an answer.
    """
    return read_cached_entry(document, ttl_seconds, now=now)[1]


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
    plain exception carrying a status. Same approach as task_store.
    """
    for attribute in ("status", "code"):
        if getattr(error, attribute, None) in NOT_FOUND_STATUSES:
            return True
    return False


# ---------------------------------------------------------------------------
# The answer
# ---------------------------------------------------------------------------


class Resolution(object):
    """One community decision, and how it was reached.

    Carries the source and the degradation flag as well as the value, because
    the caller has to be able to say more than the name: `cmd_detonate` warns
    an analyst when a whois failure sent a detonation to the platform default,
    and a log line reports which branch answered without reporting the
    community itself, which is the customer's own scoping and has no key in
    ps_log to travel under.
    """

    __slots__ = ("community", "source", "cached", "whois_called", "degraded")

    def __init__(
        self,
        community,
        source,
        cached=False,
        whois_called=False,
        degraded=False,
    ):
        self.community = community
        self.source = source
        self.cached = cached
        self.whois_called = whois_called
        self.degraded = degraded

    def __repr__(self):
        return "<Resolution source={0!r} cached={1!r} degraded={2!r}>".format(
            self.source, self.cached, self.degraded
        )


class CommunityCache(object):
    """Reads and writes the one cached whois answer.

    An optimisation and never a correctness dependency, which is the
    verdict_cache sentence rather than the task_store one: a miss, an absent
    collection and an unreadable document all cost the same one whois call, and
    a failed write costs the next detonation the same call again.
    """

    def __init__(
        self,
        service,
        collection=CACHE_COLLECTION_NAME,
        ttl_seconds=CACHE_TTL_SECONDS,
        now=None,
    ):
        """
        :param service: the splunklib service a command or input holds. None
            is accepted and disables the cache, which is what happens when the
            caller is driven outside splunkd.
        :param collection: the collection name, for tests.
        :param ttl_seconds: the lifetime of a stored answer.
        :param now: a callable returning epoch seconds, for tests.
        """
        self._service = service
        self._collection = collection
        self._now = time.time if now is None else now
        self.ttl_seconds = float(ttl_seconds)
        self.degraded = False

    def _data(self):
        if self._service is None:
            return None
        try:
            return self._service.kvstore[self._collection].data
        except Exception as error:
            self._degrade("open", error)
            return None

    def _degrade(self, event, error):
        """One flag, one log line, nothing raised.

        Only the exception's class name reaches the log, for the reason written
        out in ps_client.get_api_key.
        """
        self.degraded = True
        ps_log.warning(
            LOG_COMPONENT,
            event,
            "degraded",
            reason=type(error).__name__,
            collection=self._collection,
        )

    def read(self):
        """Return (hit, payload) for the stored whois answer.

        The pair rather than the payload, for the reason read_cached_entry
        gives: a stored nothing is a real answer about the account, and a
        caller that could not tell it from an empty cache would ask whois again
        on every detonation.
        """
        data = self._data()
        if data is None:
            return MISS

        try:
            document = data.query_by_id(CACHE_DOCUMENT_ID)
        except Exception as error:
            if _is_not_found(error):
                ps_log.debug(
                    LOG_COMPONENT,
                    "read",
                    "absent",
                    collection=self._collection,
                )
                return MISS
            self._degrade("read", error)
            return MISS

        hit, payload = read_cached_entry(
            document, self.ttl_seconds, now=self._now()
        )
        ps_log.debug(
            LOG_COMPONENT,
            "read",
            "hit" if hit else "miss",
            collection=self._collection,
        )
        return (hit, payload)

    def store(self, payload):
        """Cache one whois response. Returns True when it was written.

        A None payload IS stored, and that is the opposite of what
        task_store.store_providers does with one. The difference is what a
        cached nothing costs on each path. There, caching "the platform told us
        nothing" would refuse every detonation for twenty four hours on the
        strength of one bad request. Here it means the app sends the platform
        default for an hour, which is what it does anyway when whois says the
        account is public only, so the cached nothing saves a request and
        withholds nothing.

        What is never cached is a FAILURE, which never reaches this method: see
        resolve(), where an exception falls back without storing, so a whois
        outage does not pin the fallback in place for an hour.
        """
        data = self._data()
        if data is None:
            return False

        try:
            encoded = json.dumps(payload)
        except (TypeError, ValueError) as error:
            self._degrade("encode", error)
            return False

        document = {
            ID_FIELD: CACHE_DOCUMENT_ID,
            PAYLOAD_FIELD: encoded,
            STORED_AT_FIELD: float(self._now()),
            TTL_FIELD: self.ttl_seconds,
        }

        try:
            data.batch_save(document)
        except Exception as error:
            self._degrade("write", error)
            return False

        ps_log.debug(LOG_COMPONENT, "write", "ok", collection=self._collection)
        return True


def read_configured(service):
    """Return the operator's configured community, or None.

    Reads `polyswarm.conf` through splunkd, which merges `default/` and the
    `local/` copy the setup page writes, so this sees the customer's answer and
    not the shipped blank.

    Every failure reads as "nothing configured", which is the direction that
    keeps a detonation possible: a role that cannot read the app's own conf
    file, or a splunkd that is not answering, leaves the app on branches 2 and
    3 rather than refusing to detonate over a scoping preference.
    """
    if service is None:
        return None
    try:
        stanza = service.confs[CONF_FILE][CONF_STANZA]
    except Exception as error:
        ps_log.debug(
            LOG_COMPONENT, "conf_read", "absent", reason=type(error).__name__
        )
        return None

    try:
        content = getattr(stanza, "content", None)
        if isinstance(content, dict):
            value = content.get(CONF_SETTING)
        else:
            value = stanza[CONF_SETTING]
    except Exception as error:
        ps_log.debug(
            LOG_COMPONENT, "conf_read", "absent", reason=type(error).__name__
        )
        return None

    return read_setting(value)


def resolve(service, client_builder=None, cache=None, now=None):
    """Return the Resolution for this invocation.

    :param service: the splunklib service, for the conf read and the cache.
    :param client_builder: a callable returning a client with a `whois()`
        method, called AT MOST ONCE and only when branch 2 needs a live
        answer. A callable rather than a client because the common paths never
        make the call: an operator-configured community answers with no
        client at all, and a cached whois answers with none either. The cost of
        that laziness is one extra credential read on the miss path, since the
        caller builds its own client with the resolved community afterwards.
    :param cache: a CommunityCache, or None to build one from the service.
    :param now: a callable returning epoch seconds, for tests.
    :return: a Resolution. Never None.
    """
    configured = read_configured(service)
    if configured is not None:
        # NO COMMUNITY NAME ON THIS LINE, and no key for one either. A
        # community is the customer's own scoping, in the same class as an
        # indicator: ps_log's whitelist has no name it could travel under, so
        # the line says a value was configured and never which.
        ps_log.debug(LOG_COMPONENT, "resolve", "ok")
        return Resolution(configured, SOURCE_CONFIGURED)

    if cache is None:
        cache = CommunityCache(service, now=now)

    cached, payload = cache.read()
    whois_called = False
    degraded = False

    if not cached and client_builder is not None:
        try:
            client = client_builder()
            payload = client.whois()
            whois_called = True
            cache.store(payload)
        except Exception as error:
            # FAILS OPEN, DELIBERATELY, AND NOT SILENTLY. See the module
            # docstring: falling back sends the detonation where every
            # detonation went before this module existed, and refusing would
            # trade a working feature for a scoping preference. The caller
            # reads `degraded` and tells the analyst.
            degraded = True
            payload = None
            ps_log.warning(
                LOG_COMPONENT, "whois", "error", reason=type(error).__name__
            )

    private = most_private(read_communities(payload))
    if private is not None:
        return Resolution(
            private,
            SOURCE_WHOIS,
            cached=cached,
            whois_called=whois_called,
        )

    return Resolution(
        FALLBACK_COMMUNITY,
        SOURCE_FALLBACK,
        cached=cached,
        whois_called=whois_called,
        degraded=degraded,
    )
