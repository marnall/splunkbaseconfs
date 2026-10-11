"""Search command entry point for polyswarmdetonate.

Registered in default/commands.conf as a chunked (v2 protocol) generating
command.

    | polyswarmdetonate url="https://example.com/suspect"
    | polyswarmdetonate url="https://example.com/suspect" provider=cape vm=win-10-build-19041

Design section 4.3's first half: submit a URL for detonation and return the
task immediately. The row it emits is also written to the ps_sandbox_tasks
collection, which is the tasks tray's data source and the poller's worklist.

Output. One row, carrying the ten fields of the task table:

    task_id       the platform's task id, and the key the poller reads
    target        the URL that was detonated
    provider      the sandbox provider, as the platform resolved it
    vm            the VM image, as the platform resolved it
    community     the community the detonation ran in, as RESOLVED. The app
                  sends "default"; the platform answers with the real one.
    status        the platform's status string, verbatim
    submitted_at  epoch seconds the submission was made
    updated_at    epoch seconds this row was last written
    sha256        the artifact digest, once the platform has hashed the upload.
                  Absent at submit time, which is the ordinary case.
    report_url    the artifact's portal page, once there is a digest to build
                  it from. See the note in bin/task_store.py: the prefix is
                  derived from a recorded permalink and the form is unverified.

ONE DETONATION PER INVOCATION, AND THE CAP IS THE WHOLE DESIGN OF THIS COMMAND
-----------------------------------------------------------------------------
Constraint C11 says every code path that spends quota declares a hard cap and
refuses rather than proceeding past it. A detonation is the most expensive
metered call in the product: an enrichment request is a database lookup, and
this books a virtual machine, runs a browser in it, and captures the result.

So the cap is one, and it is structural rather than a parameter. There is no
limit option to get wrong, no input events to fan out over, and no way to raise
the ceiling from the search bar. The browser and iOS apps do allow a batch, up
to twenty, with a per-item confirmation in front of it. A search command has
nowhere to put a confirmation: a search runs when it is dispatched, from a
saved search, an alert action, a dashboard panel, or a mistyped command line.
Without the confirmation the only honest cap is one, and a batch form is a v1
non-goal for that reason and not for want of the loop.

What that leaves open, named rather than implied: C11's preflight quota math
against /v3/public/accounts is still the item decision D3 records as
outstanding. A cap of one is the hardest cap available, so a preflight here
could only tell a customer they are out of allowance a moment before the
platform does.

WHY THE PROVIDER AND THE VM ARE VALIDATED BEFORE ANYTHING IS SPENT
------------------------------------------------------------------
Both options default, to triage and windows11-21h2-x64, and both are checked
against the platform's own providers list before the submit. Three checks, and
the third is the one that pays for the other two: the VM has to declare support
for the URL artifact type. triage's android-11-x64 declares FILE only, so
`vm=android-11-x64` with a URL is a detonation that cannot do the job, and
without the check it would be bought and then wasted.

The providers answer is cached in the KV store for 24 hours, so validation
costs nothing per detonation and one request per day at most. On a cache miss
the command makes exactly one live providers call. IF THAT CALL FAILS, THE
COMMAND REFUSES: a validation that fails open is not a validation, and the
thing on the other side of it is the most expensive call this app can make.

Importing this module is side effect free. It only runs when Splunk invokes it
as a subprocess.
"""

import os
import sys
import time

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import community
import ps_log
import task_store
from ps_client import ClientConfigurationError, get_client
from ps_sanitize import sanitize

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
)

COMMAND_NAME = "polyswarmdetonate"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "cmd_detonate"

# The hard cap. See the module docstring, and constraint C11.
#
# It is a named constant with a test on it rather than an implicit property of
# the code, because the property being asserted is not "the loop runs once": it
# is that a future reader who adds a loop has to change a number that a test is
# watching.
MAX_DETONATIONS = 1

# The defaults, and they are live values rather than plausible ones. Both come
# from tests/fixtures/sandbox-providers-recorded.json:
#
#   triage                 one of the two providers the platform lists today
#   windows11-21h2-x64     a triage VM that declares FILE and URL support, with
#                          edge as its browser
#
# triage rather than cape because cape lists one Windows 10 VM and triage lists
# a Windows 11 one alongside Android and Ubuntu, so the default is the provider
# with somewhere to go next. Neither default is hard coded past this line: both
# are validated against the providers list on every invocation, so a default
# that the platform retires produces a refusal naming what is available rather
# than a failed detonation.
DEFAULT_PROVIDER = "triage"
DEFAULT_VM = "windows11-21h2-x64"

# The URL schemes a detonation target may use.
#
# A SCHEME IS REQUIRED, AND THAT IS THE MIRROR IMAGE OF THE URL SEARCH RULE.
# ps_client.search_url deliberately does NOT synthesise a scheme onto a bare
# host, because asking about http://x and https://x are two different questions
# and guessing would answer about a resource the event did not name. The same
# fact bites harder here: a sandbox VM has to actually browse the target, so a
# value with no scheme would either fail in the VM or be resolved by somebody
# else's guess, after the detonation was bought. Refusing costs a customer a
# corrected search; guessing costs them a detonation.
ALLOWED_URL_SCHEMES = ("http://", "https://")

# Characters that cannot appear in a target URL. A value carrying whitespace is
# two values, or a copy-and-paste accident, and either way the sandbox would
# browse something other than what the analyst meant.
FORBIDDEN_URL_CHARACTERS = (" ", "\t", "\r", "\n")

COMMUNITY_FALLBACK_MESSAGE = (
    "The PolySwarm account's entitled communities could not be read, so this "
    "detonation was scoped to the platform default ({0}) and PolySwarm "
    "resolved the account's own community for it. The task row records where "
    "it actually ran. Set a community on the app setup page to scope "
    "detonations explicitly."
)

STORE_FAILED_MESSAGE = (
    "PolySwarm detonation task {0} was submitted but could not be written to "
    "the {1} collection, so it will not appear in the tasks tray and the "
    "poller will not follow it. The task id in these results is the only "
    "record of it. Check that the app is fully installed and that the KV "
    "store is available."
)

# No module logger here. Everything this command writes goes through ps_log, so
# that the whitelist is the only route a value has into a log line. Note what
# that means for this command in particular: there is no key for a URL, so the
# target of a detonation never reaches a log line.


class DetonateOptionError(Exception):
    """Raised when an option is missing, malformed, or not available.

    Its own exception so that every refusal in this module is testable without
    splunkd, and so that the message an analyst sees is written here rather
    than assembled by the SDK's validators.
    """


# ---------------------------------------------------------------------------
# Option handling: pure
# ---------------------------------------------------------------------------


def resolve_url(value):
    """Return the target URL, or refuse.

    :raises DetonateOptionError: if it is absent, malformed, or has no scheme.
    """
    text = "" if value is None else str(value).strip()
    if not text:
        raise DetonateOptionError(
            "polyswarmdetonate requires a url option. Example: "
            '| polyswarmdetonate url="https://example.com/suspect"'
        )

    for character in FORBIDDEN_URL_CHARACTERS:
        if character in text:
            raise DetonateOptionError(
                "The url option contains whitespace, so it is not a single "
                "URL. Quote the value and check it for a stray space or line "
                "break."
            )

    lowered = text.lower()
    for scheme in ALLOWED_URL_SCHEMES:
        if lowered.startswith(scheme):
            return text

    raise DetonateOptionError(
        "The url option must start with http:// or https://. A sandbox has to "
        "browse the target, and a value with no scheme would make something "
        "other than this app choose between them, after the detonation had "
        "been spent."
    )


def resolve_slug(value, default, option_name):
    """Return a provider or VM slug, or the default. Refuses an empty value.

    Availability is checked separately, against the providers list, because
    that check needs a network answer and this one does not.

    :raises DetonateOptionError: if the option was given as a blank string.
    """
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        raise DetonateOptionError(
            "The {0} option was given with no value. Leave it out to use the "
            "default, {1}.".format(option_name, default)
        )
    return text


def validate_against_providers(providers, provider_slug, vm_slug):
    """Refuse a provider or VM the platform did not list, or cannot browse.

    Three checks in the order that produces the most useful message: the
    provider, then the VM within it, then whether that VM can take a URL at
    all. Each refusal names what IS available, because a message that says only
    "unknown vm" sends the customer to a portal to find out.

    :param providers: task_store.read_providers() output.
    :param provider_slug: the requested provider.
    :param vm_slug: the requested VM.
    :raises DetonateOptionError: on any of the three.
    """
    available = task_store.provider_slugs(providers)
    if not available:
        # Distinguished from an unknown slug on purpose. An empty list is not
        # the customer's mistake, and telling them their provider is wrong when
        # the app could not read any provider at all would send them looking in
        # the wrong place.
        raise DetonateOptionError(
            "PolySwarm returned no sandbox providers, so the provider and VM "
            "for this detonation could not be validated. Nothing was "
            "submitted. Check the API key's entitlement on the app setup page."
        )

    if provider_slug not in available:
        raise DetonateOptionError(
            "PolySwarm does not list a sandbox provider called {0}. Available "
            "providers: {1}.".format(provider_slug, ", ".join(available))
        )

    vms = task_store.vm_slugs(providers, provider_slug)
    if vm_slug not in vms:
        raise DetonateOptionError(
            "The {0} provider does not list a VM called {1}. Available VMs: "
            "{2}.".format(provider_slug, vm_slug, ", ".join(vms) or "none")
        )

    if not task_store.vm_supports_url(providers, provider_slug, vm_slug):
        raise DetonateOptionError(
            "The {0} VM on provider {1} does not accept a URL, so a URL "
            "detonation on it would be spent without running. Choose a VM "
            "that lists URL support.".format(vm_slug, provider_slug)
        )


# ---------------------------------------------------------------------------
# The detonation pass
# ---------------------------------------------------------------------------


class Detonator(object):
    """Validates, submits once, and stores the row.

    Split out from the command class for the reason UsageReporter and
    IocEnricher are: a GeneratingCommand cannot be instantiated meaningfully
    outside the chunked protocol handshake, so logic left inside it is logic no
    test can reach. This class takes anything with sandbox_providers() and
    sandbox_submit_url() methods, plus an optional store, so the whole pass
    runs with a fake client, a fake KV store, and a fake clock.
    """

    def __init__(self, client, store=None, now=None):
        """
        :param client: anything with sandbox_providers() and
            sandbox_submit_url() methods.
        :param store: a task_store.TaskStore, or None to run with no providers
            cache and no task row at all. None is a supported mode rather than
            a degradation: it is what the pass does outside splunkd.
        :param now: a callable returning epoch seconds, for tests.
        """
        self.client = client
        self.store = store
        self._now = time.time if now is None else now

        # Whether the providers answer came out of the cache or off the wire.
        # Read by the command for its finish line, because "did this search
        # make one request or two" is the question a quota conversation starts
        # with.
        self.providers_cached = False

        # Whether the task row reached the collection. False after a submit is
        # a spend with no receipt, and the command says so to the analyst.
        self.stored = False

        self.detonations = 0

    def providers(self):
        """Return the providers mapping, from the cache or one live call.

        ONE LIVE CALL AT MOST, AND ONLY ON A MISS. The answer is cached for 24
        hours in ps_sandbox_providers, so a customer detonating fifty URLs in a
        day makes one providers request, not fifty.

        A FAILURE HERE IS NOT SWALLOWED. Every other KV-backed path in this app
        degrades to a miss and carries on, because what is lost is an
        optimisation. What would be lost here is the validation in front of the
        most expensive call in the product, so a providers call that fails
        propagates and the detonation does not happen.

        AN EMPTY ANSWER IS NEVER CACHED, AND THAT IS WHAT THIS ORDER IS FOR.
        ------------------------------------------------------------------
        The payload is READ BEFORE IT IS STORED, and it is stored only when the
        reading yields at least one provider. The other order, which is what
        this method used to do, turns one transient 200 with an empty result
        into a day-long outage: the empty document goes into a cache with a 24
        hour lifetime, every read of it yields no providers, and every
        `polyswarmdetonate` and every firing of the PolySwarm Detonate alert
        action is refused with "PolySwarm returned no sandbox providers" until
        somebody deletes the document by hand. Nothing in the app clears it,
        because from the cache's point of view the document is perfectly fresh.

        So there are three outcomes and each one is deliberate:

          * **The live answer carries providers.** Cached, and returned. The
            ordinary path.
          * **The live answer is empty and a cached document reads as
            providers.** The cached one is preferred, a warning is logged, and
            the empty answer is discarded rather than written over it. A stale
            list is a far better basis for validation than no list: the worst
            it can do is refuse a VM that has just been added, and it costs
            nothing.
          * **Both are empty.** Refused, exactly as today, by
            validate_against_providers. Nothing is submitted and nothing is
            cached, so the next invocation asks again instead of reading back a
            refusal somebody has to delete.

        The cache is read a second time on the empty-live path, and only there.
        It is one KV read on a path that should never happen, and it is what
        makes the preference above real: the live call takes long enough for a
        concurrent detonation search on this search head to have cached a good
        answer in the meantime, and reading again is the only way to see it
        without holding a second opinion about what the cache contains.

        task_store.store_providers has its own reason for guarding only None,
        which is that it is the generic writer; the caller is where the
        emptiness rule belongs, because the caller is what knows an empty
        providers list is a refusal rather than an answer.
        """
        cached_payload = None
        if self.store is not None:
            cached_payload = self.store.cached_providers()

        cached = task_store.read_providers(cached_payload)
        if cached:
            self.providers_cached = True
            return cached

        payload = self.client.sandbox_providers()
        live = task_store.read_providers(payload)

        if live:
            if self.store is not None:
                self.store.store_providers(payload)
            return live

        # The live answer carries no providers. Prefer anything usable in the
        # cache over it, and never write it.
        if self.store is not None:
            fallback = task_store.read_providers(self.store.cached_providers())
            if fallback:
                self.providers_cached = True
                ps_log.warning(
                    LOG_COMPONENT, "providers_read", "degraded"
                )
                return fallback

        ps_log.warning(LOG_COMPONENT, "providers_read", "refused")
        return live

    def detonate(self, url, provider_slug, vm_slug):
        """Submit one detonation and return the rows to emit.

        Order of operations, and every step before the submit is there to make
        the submit unnecessary when it would be wasted:

          1. Resolve the options. No network.
          2. Get the providers list, from the cache or one call.
          3. Validate the provider, the VM, and URL support. Refuse before
             spending anything.
          4. Submit once. Three HTTP requests, one detonation. See
             ps_client.sandbox_submit_url.
          5. Build the row and write it through.

        Nothing is caught. An authentication failure or a transport failure
        propagates, because it affects the whole answer rather than one row of
        it, and because constraint C6 forbids turning it into synthetic data.
        The analyst gets the client's sanitized message.

        :return: a list of exactly one row, unpadded.
        """
        target = resolve_url(url)
        provider = resolve_slug(provider_slug, DEFAULT_PROVIDER, "provider")
        vm = resolve_slug(vm_slug, DEFAULT_VM, "vm")

        validate_against_providers(self.providers(), provider, vm)

        submitted_at = float(self._now())
        response = self.client.sandbox_submit_url(target, provider, vm)
        self.detonations += 1

        row = task_store.build_task_row(
            response,
            target=target,
            provider=provider,
            vm=vm,
            submitted_at=submitted_at,
            updated_at=float(self._now()),
        )

        if self.store is not None:
            self.stored = self.store.save_task(row)

        return [row]


def build_client(service, community_name=None):
    """Return a configured client, or fail with a message naming the command.

    Constraint C8: unconfigured means a clear message and zero network calls.
    ps_client already refuses without a stored credential and already names the
    setup page; what it cannot know is which command the customer was running.

    :param service: the splunklib service the command holds.
    :param community_name: the resolved community, or None for the platform
        default. Named with the suffix because `community` is the module this
        command resolves it with, and a local shadowing that import is how a
        later edit ends up calling a string.
    """
    try:
        return get_client(service, community=community_name)
    except ClientConfigurationError as error:
        raise ClientConfigurationError(
            "polyswarmdetonate cannot submit a detonation without a "
            "configured PolySwarm API key. {0}".format(error)
        )


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


@Configuration()
class PolySwarmDetonateCommand(GeneratingCommand):
    """Submit one URL for sandbox detonation and return its task row.

    A plain @Configuration() on a GeneratingCommand runs the command locally on
    the search head: splunklib's distributed setting defaults to False, and its
    protocol v2 serialisation turns the default streaming type into stateful
    when it is. That default is required rather than merely convenient here,
    because the command reads the API key out of storage/passwords, which
    exists on the search head and not on an indexer.
    """

    # require=True is the SDK-level declaration. resolve_url() enforces the
    # same rule in code, so the refusal is testable without splunkd and the
    # message is ours.
    url = Option(
        doc="""
        **Syntax:** **url=***<url>*
        **Description:** the URL to detonate. Required. Must start with
        http:// or https://. One URL per invocation: a detonation is metered
        and there is no confirmation step in a search, so this command has no
        batch form.
        """,
        require=True,
    )

    provider = Option(
        doc="""
        **Syntax:** **provider=***<slug>*
        **Description:** the sandbox provider. Defaults to triage. Validated
        against the providers PolySwarm lists for this key, which is cached for
        24 hours, so an unavailable value is refused before anything is spent.
        """,
        require=False,
        default=DEFAULT_PROVIDER,
    )

    # No validators.Set on either slug option, deliberately. The set of valid
    # values is whatever the platform lists for this key today, which an
    # Option's validator cannot know: baking last month's list into a validator
    # would refuse a VM the platform has added and accept one it has retired.
    vm = Option(
        doc="""
        **Syntax:** **vm=***<slug>*
        **Description:** the VM image to detonate in. Defaults to
        windows11-21h2-x64. Validated against the provider's VM list, including
        whether that VM accepts a URL at all.
        """,
        require=False,
        default=DEFAULT_VM,
    )

    def generate(self):
        # ONE START LINE AND ONE FINISH LINE PER INVOCATION, matching
        # cmd_search and cmd_usage. A start with no finish is a command that
        # died or was killed, and on this command that is the case an operator
        # most needs to be able to see: a detonation may have been bought.
        timer = ps_log.Timer()
        ps_log.info(LOG_COMPONENT, "start", "ok")

        service = getattr(self, "service", None)

        # THE COMMUNITY IS RESOLVED BEFORE THE CLIENT IS BUILT, because it is
        # part of the client's configuration and a ClientConfig is immutable
        # once made. bin/community.py holds the rule; what this line adds is
        # the laziness: the builder it is handed is called at most once, and
        # only on the path that needs a live whois, so an operator-configured
        # community and a cached whois answer both cost one credential read
        # rather than two.
        resolution = community.resolve(
            service, client_builder=lambda: build_client(service)
        )
        client = build_client(service, community_name=resolution.community)

        # Built even when the collections are missing. TaskStore reports a
        # providers miss and stores nothing in that case, so constructing it
        # unconditionally keeps the present and absent paths the same code
        # rather than two paths where only one is exercised.
        store = task_store.TaskStore(service)
        detonator = Detonator(client, store=store)

        rows = detonator.detonate(self.url, self.provider, self.vm)

        # output_row() before sanitize(), matching cmd_usage: padding adds only
        # keys already declared in task_store.ALL_FIELDS and only None values,
        # and sanitize() stays the last thing that touches a value on its way
        # out.
        emitted = 0
        for row in rows:
            emitted += 1
            yield sanitize(task_store.output_row(row))

        ps_log.info(
            LOG_COMPONENT,
            "finish",
            "ok",
            records=emitted,
            # The cost of the invocation. One detonation, and whether the
            # providers list came off the wire or out of the cache.
            lookups=detonator.detonations,
            cache_hits=1 if detonator.providers_cached else 0,
            cache_misses=0 if detonator.providers_cached else 1,
            cache_stores=store.stores,
            cache_degraded=store.degraded,
            duration_ms=timer.duration_ms,
        )

        if resolution.degraded:
            # The whois call failed and the detonation went to the platform
            # default. It is a real detonation and a real result, so this is a
            # warning rather than a refusal, and it is in front of the analyst
            # rather than only in a log because the community a detonation ran
            # in is a scoping decision they may have to account for.
            self.write_warning(
                COMMUNITY_FALLBACK_MESSAGE.format(resolution.community)
            )

        if not detonator.stored:
            # The loudest warning in this app, and the reason is in
            # bin/task_store.py: the platform's own my-tasks listing hangs, so
            # a task row that was not written is a metered call nothing can
            # find again. The task id is in the results, which is why the
            # message points at them.
            for row in rows:
                self.write_warning(
                    STORE_FAILED_MESSAGE.format(
                        row.get(task_store.TASK_ID_FIELD) or "unknown",
                        task_store.TASK_COLLECTION_NAME,
                    )
                )


def main(argv=None):
    """Console entry point invoked by Splunk."""
    dispatch(
        PolySwarmDetonateCommand,
        argv if argv is not None else sys.argv,
        sys.stdin,
        sys.stdout,
        __name__,
    )


if __name__ == "__main__":
    main()
