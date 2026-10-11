"""The `| polyswarmsync` generating command: run one intel pull on demand.

Design section 4.2 lists a manual sync as quality-of-life feature 2: "a Sync
now button on the inputs page and a `| polyswarmsync` generating command, both
writing a visible run-log event stream so an operator can see exactly what
happened and when". This is the command half.

    | polyswarmsync stanza=polyswarm_intel_pull

WHAT IT IS FOR
--------------
The scheduled input runs unattended, and the only thing it leaves behind is
events in an index plus lines in `_internal`. That is fine once it works and
useless while an operator is still setting it up: they have chosen a family
list, a floor and a cap, and they want to know whether the combination selects
anything at all before they turn a metered schedule on. Waiting an interval to
find out, then reading the app's log to interpret it, is the workflow this
command replaces.

So the answer it gives is the run summary: the window, how many artifacts the
window holds, how many were refused as already seen, how many pages and
requests it took, and whether the cap was hit.

IT REUSES THE INPUT'S PASS RATHER THAN REIMPLEMENTING IT
--------------------------------------------------------
`input_intel_pull.IntelPuller` is the cycle, and this command constructs the
same class with the same arguments read by the same readers. Nothing about the
query, the pagination, the cap or the dedupe is written twice. That matters
more here than tidiness suggests: two copies of the cap would be two answers to
what a run may spend, and this is the surface where somebody types the command
repeatedly while working out their configuration.

**THE PARAMETERS COME FROM THE STANZA AND NOT FROM THE SEARCH BAR.** The
command takes one option, the stanza name, and reads that stanza's own settings
out of `inputs.conf` through splunkd, which merges `default/` with the
`local/` copy the operator edited. Options for the families, the floor and the
cap were considered and rejected: the point of the command is to verify what
the SCHEDULED input will do, and a command that took its own parameters would
verify something else. It would also be a second place a cap could be set.

THE CHECKPOINT IS NOT ADVANCED, AND THAT IS THE MOST IMPORTANT LINE HERE
------------------------------------------------------------------------
A search command's output is search results. It is not indexed, and this
command deliberately does not index anything: writing to an index from a search
command means `| collect`, which needs its own permissions, its own summary
index conventions and its own opinion about which index to write to, none of
which belong in a verification tool.

The consequence is the rule. If this command advanced the checkpoint, the
window it just pulled would be marked done, the scheduled input would skip it
forever, and the artifacts in it would be absent from the customer's index with
nothing in the app able to tell later that they were ever missed. A silent,
permanent gap, caused by an operator pressing a button labelled Sync.

So the checkpoint is left exactly as it was, and the summary says so in a field
rather than in documentation nobody reads at the time. The cost is that the
scheduled run which follows re-covers the same window and re-bills it, bounded
by the cap. That is the same failure direction `bin/intel_checkpoint.py` takes
for a failed write, and for the same reason: a duplicate is recoverable and a
gap is not.

WHAT IT SPENDS, AND WHY IT IS ROLE GATED
----------------------------------------
Exactly what one scheduled run would spend: one request per page, up to the
stanza's own cap. That is real money on the customer's account, invoked by
typing a command, which is why `metadata/default.meta` restricts it to admin
and power rather than leaving it on the app's default read ACL. A user who can
run this can spend the intel budget, and design constraint C3 says a command
that spends quota gets a gate.

Constraint C6: no failure becomes a result row. An unconfigured app, an unknown
stanza and a rejected key all raise out of `generate()` with a sanitized
message, which Splunk reports as a search error. None of them produces a
summary row saying zero, because a row saying zero is indistinguishable from a
window that genuinely held nothing, and those are different facts.
"""

import os
import sys

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import input_intel_pull
import intel_checkpoint
import ps_log
from ps_client import ClientConfigurationError, get_client
from ps_sanitize import sanitize

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
)
from splunklib.searchcommands.validators import Boolean  # noqa: E402

# The command name, which must equal the commands.conf stanza. A test asserts
# it, the same way test_commands.py asserts it for the other four.
COMMAND_NAME = "polyswarmsync"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "cmd_sync"

# The conf file and the input kind the stanza name is resolved against.
INPUTS_CONF = "inputs"
INPUT_KIND = input_intel_pull.INPUT_KIND

# ---------------------------------------------------------------------------
# The summary row
# ---------------------------------------------------------------------------
#
# Unprefixed field names, matching | polyswarmusage rather than
# polyswarmsearch. The distinction is real and not stylistic: a streaming
# command adds fields to somebody else's event and has to namespace them, and a
# generating command owns every field on the rows it makes.
#
# THE BOOLEANS ARE STRINGS. "true" and "false", for the reason decision D9
# records for is_trial: these are SPL field values and Python's "True" is not
# one. An analyst filtering on limit_reached="true" should not have to know
# which language produced the row.

STANZA_FIELD = "stanza"
WINDOW_START_FIELD = "window_start"
WINDOW_END_FIELD = "window_end"
ARTIFACTS_FIELD = "artifacts"
DUPLICATES_FIELD = "duplicates"
UNREADABLE_FIELD = "unreadable"
PAGES_FIELD = "pages"
REQUESTS_FIELD = "requests"
LIMIT_FIELD = "limit"
LIMIT_REACHED_FIELD = "limit_reached"
CHECKPOINT_ADVANCED_FIELD = "checkpoint_advanced"
DEGRADED_FIELD = "degraded"
NOTE_FIELD = "note"

ALL_FIELDS = (
    STANZA_FIELD,
    WINDOW_START_FIELD,
    WINDOW_END_FIELD,
    ARTIFACTS_FIELD,
    DUPLICATES_FIELD,
    UNREADABLE_FIELD,
    PAGES_FIELD,
    REQUESTS_FIELD,
    LIMIT_FIELD,
    LIMIT_REACHED_FIELD,
    CHECKPOINT_ADVANCED_FIELD,
    DEGRADED_FIELD,
    NOTE_FIELD,
)

TRUE = "true"
FALSE = "false"

# The one note every row carries, because it is the one thing about this
# command an operator has to know and the one thing a field name cannot say on
# its own. See the docstring: a manual sync does not index and therefore must
# not advance the checkpoint.
NOTE_PREVIEW = (
    "This is a preview. The artifacts were not written to an index and the "
    "checkpoint was not advanced, so the scheduled input still covers this "
    "window."
)

NOTE_EMPTY_WINDOW = (
    "The window was empty, so no request was made. The last run's checkpoint "
    "is at or ahead of the current time."
)

NOTE_CHECKPOINT_UNREADABLE = (
    "The run was refused because the stored checkpoint could not be read, so "
    "no request was made and nothing about the window is known. The KV store "
    "answered with an error; the scheduled input retries on its next interval "
    "and this preview can be run again once the store answers."
)

NOTE_CAP = (
    "The run stopped at its cap and artifacts inside the window were left "
    "unpulled. Raise max_artifacts_per_run on the stanza, up to {0}, or let "
    "the scheduled input catch up over several runs."
).format(input_intel_pull.MAX_ARTIFACTS_HARD_CAP)

# Said on the row rather than left for somebody to work out, because the window
# on a drain row is not the window an operator expects: it ends where the last
# capped run got to rather than at the clock, and a preview that showed that
# with no explanation reads as a stuck feed.
NOTE_BACKLOG = (
    "The scheduled input is working through the backlog left by a run that "
    "stopped at its cap, so this window ends where that run reached rather "
    "than at the current time. It moves on once the backlog is drained."
)

DEGRADED_MESSAGE = (
    "The pull did not complete cleanly. See the polyswarm_app_for_splunk log "
    "for the reason. Nothing was checkpointed."
)

UNKNOWN_STANZA_MESSAGE = (
    "polyswarmsync found no {0} input stanza named {1}. Name a stanza that "
    "exists in inputs.conf, without the {0}:// prefix."
)

NO_STANZA_MESSAGE = (
    "polyswarmsync needs a stanza to run. Give it the name of a "
    "{0} input, for example stanza={1}."
).format(INPUT_KIND, input_intel_pull.SHIPPED_STANZA)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def qualified_stanza(name):
    """Return the full inputs.conf stanza name for a bare input name. Pure.

    Accepts either form, so an operator who pastes the whole stanza out of
    inputs.conf gets the same answer as one who types just the name. The kind
    prefix is added rather than required because the command already knows the
    kind: there is only one input this command can run.
    """
    text = str(name or "").strip()
    if not text:
        return None
    prefix = INPUT_KIND + "://"
    if text.startswith(prefix):
        text = text[len(prefix):]
    text = text.strip().strip("/")
    if not text:
        return None
    return prefix + text


def format_moment(epoch):
    """Return one window bound as the query spells it, or None. Pure.

    The same rendering the query uses, so an operator comparing the summary
    against the app's log against the platform's own portal sees one format.
    """
    if epoch is None:
        return None
    return input_intel_pull.format_window_bound(epoch)


def build_summary(puller, stanza, note=None):
    """Return the one summary row for a completed pass. Pure.

    Reads the puller's counters and nothing else. It has no parameter an
    exception could arrive through, which is constraint C6 held by
    construction: there is no expression here that could turn a failure into a
    result row.
    """
    notes = [NOTE_PREVIEW]
    if note:
        notes.insert(0, note)
    if getattr(puller, "draining", False):
        notes.insert(0, NOTE_BACKLOG)
    if puller.limit_reached:
        notes.insert(0, NOTE_CAP)

    return {
        STANZA_FIELD: stanza,
        WINDOW_START_FIELD: format_moment(puller.window_start),
        WINDOW_END_FIELD: format_moment(puller.window_end),
        ARTIFACTS_FIELD: puller.emitted,
        DUPLICATES_FIELD: puller.duplicates,
        UNREADABLE_FIELD: puller.unreadable,
        PAGES_FIELD: puller.pages,
        REQUESTS_FIELD: puller.requests,
        LIMIT_FIELD: puller.max_artifacts,
        LIMIT_REACHED_FIELD: TRUE if puller.limit_reached else FALSE,
        # Always false, and stated on every row rather than omitted. An absent
        # field reads as "not applicable"; this one is a promise.
        CHECKPOINT_ADVANCED_FIELD: FALSE,
        DEGRADED_FIELD: TRUE if puller.degraded else FALSE,
        NOTE_FIELD: " ".join(notes),
    }


def output_row(row):
    """Return one row padded to every declared field. Pure.

    Splunk's chunked protocol takes the field set from the first row it sees,
    so a field absent from row one is a column that does not exist for any
    later row. One row is emitted here, but the padding stays: it makes the
    emitted column set equal to ALL_FIELDS by construction, which is what a
    test can assert.
    """
    padded = dict((name, None) for name in ALL_FIELDS)
    padded.update(row or {})
    return padded


# ---------------------------------------------------------------------------
# The stanza lookup
# ---------------------------------------------------------------------------


def read_stanza_parameters(service, stanza):
    """Return one input stanza's settings as a mapping, or None.

    Reads `inputs.conf` through splunkd, which merges `default/` and `local/`,
    so this sees what the operator configured and not the shipped sample.

    None when the stanza does not exist, which is the case the caller turns
    into a search error naming the stanza. A stanza that exists but is disabled
    IS returned: running a preview against an input before enabling it is the
    main thing this command is for, and refusing on `disabled` would make it
    useless for exactly that.
    """
    if service is None:
        return None
    try:
        conf = service.confs[INPUTS_CONF]
    except Exception as error:
        ps_log.debug(
            LOG_COMPONENT, "conf_read", "absent", reason=type(error).__name__
        )
        return None

    try:
        entry = conf[stanza]
    except Exception as error:
        ps_log.debug(
            LOG_COMPONENT, "conf_read", "absent", reason=type(error).__name__
        )
        return None

    content = getattr(entry, "content", None)
    if isinstance(content, dict):
        return dict(content)
    try:
        return dict(entry)
    except Exception as error:
        ps_log.debug(
            LOG_COMPONENT, "conf_read", "absent", reason=type(error).__name__
        )
        return None


def build_client(service, community_name=None):
    """Return a configured client, or fail with a message naming the command.

    Constraint C8: unconfigured means a clear message and zero network calls.
    ps_client already refuses without a stored credential and already names the
    setup page; what it cannot know is which command the customer ran, which is
    the same reasoning cmd_usage.build_client carries.
    """
    try:
        return get_client(service, community=community_name)
    except ClientConfigurationError as error:
        raise ClientConfigurationError(
            "polyswarmsync cannot pull intel without a configured PolySwarm "
            "API key. {0}".format(error)
        )


class SyncRunner(object):
    """Runs one preview cycle and holds the row it produced.

    Split out of the command class for the reason UsageReporter and Detonator
    are split out of theirs: a search command cannot be instantiated
    meaningfully outside the chunked protocol, so logic left inside one is
    logic no test can reach.
    """

    def __init__(self, service, stanza, now=None):
        self.service = service
        self.stanza = stanza
        self._now = now

        self.puller = None
        self.checkpoint_degraded = False

    def rows(self):
        """Return the summary rows for one invocation.

        Nothing is caught here. An unknown stanza, an unconfigured key or a
        rejected credential propagates, because each affects the whole answer
        rather than one row of it, and constraint C6 forbids turning any of
        them into synthetic data.
        """
        parameters = read_stanza_parameters(self.service, self.stanza)
        if parameters is None:
            raise ClientConfigurationError(
                UNKNOWN_STANZA_MESSAGE.format(INPUT_KIND, self.stanza)
            )

        community_name = input_intel_pull.resolve_community(
            self.service,
            input_intel_pull.read_community_argument(parameters),
        )
        client = build_client(self.service, community_name)

        # The checkpoint is READ so the preview covers the window the scheduled
        # input would cover next, and it is never WRITTEN: advance_checkpoint is
        # False. See the module docstring.
        checkpoint = intel_checkpoint.IntelCheckpoint(
            self.service, now=self._now
        )
        self.puller = input_intel_pull.IntelPuller(
            client,
            checkpoint,
            self.stanza,
            families=input_intel_pull.read_families_argument(parameters),
            tags=input_intel_pull.read_tags_argument(parameters),
            min_polyscore=input_intel_pull.read_min_polyscore(parameters),
            lookback_minutes=input_intel_pull.read_lookback_minutes(parameters),
            max_artifacts=input_intel_pull.read_max_artifacts(parameters),
            lag_seconds=input_intel_pull.read_lag_seconds(parameters),
            community_name=community_name,
            advance_checkpoint=False,
            now=self._now,
        )

        # The sink COUNTS AND DISCARDS. The command's answer is the summary, and
        # the artifacts are not indexed, so holding them would build a list of
        # up to a thousand documents in memory to throw away. The puller's own
        # counters are what the row is built from.
        self.puller.run(lambda fields: None)
        self.checkpoint_degraded = bool(checkpoint.degraded)

        # THE REFUSAL COMES FIRST. A refused run also has zero requests and zero
        # artifacts, and describing it as an empty window would assert a fact
        # about a checkpoint the run could not read; finding 45 in the QA ledger
        # and decision D24 record why that sentence has to be different.
        note = None
        if getattr(self.puller, "checkpoint_read_failed", False):
            note = NOTE_CHECKPOINT_UNREADABLE
        elif self.puller.requests == 0 and self.puller.emitted == 0:
            note = NOTE_EMPTY_WINDOW

        return [build_summary(self.puller, self.stanza, note=note)]


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


@Configuration()
class PolySwarmSyncCommand(GeneratingCommand):
    """Run one PolySwarm intel pull cycle for a named input stanza.

    A plain @Configuration() on a GeneratingCommand runs the command locally on
    the search head: splunklib's distributed setting defaults to False. That is
    required rather than convenient, for the reason cmd_usage records: the
    command reads the API key out of storage/passwords and the checkpoint out
    of the KV store, and both live on the search head.
    """

    stanza = Option(
        doc="""
        **Syntax:** **stanza=**```<input name>```
        **Description:** the name of the polyswarm_intel_pull input to run one
        cycle for, as it appears in inputs.conf. The `input_intel_pull://`
        prefix is optional.""",
        require=True,
    )

    preview = Option(
        doc="""
        **Syntax:** **preview=**```<boolean>```
        **Description:** accepted for clarity and must be true. This command
        never indexes what it pulls and never advances the checkpoint, so a
        non-preview mode does not exist; the option is here so that a later
        release adding one cannot change what an existing saved search does.""",
        require=False,
        default=True,
        validate=Boolean(),
    )

    def generate(self):
        # ONE START LINE AND ONE FINISH LINE PER INVOCATION, matching
        # cmd_search and cmd_usage. A start with no finish is a command that
        # died or was killed, which is the "nothing is happening" a customer
        # reports and which nothing else tells apart from an empty answer.
        timer = ps_log.Timer()
        ps_log.info(LOG_COMPONENT, "start", "ok")

        if self.preview is False:
            raise ClientConfigurationError(
                "polyswarmsync only runs as a preview. It does not write to an "
                "index, so preview=false would advance the checkpoint for a "
                "window whose artifacts were never indexed."
            )

        stanza = qualified_stanza(self.stanza)
        if stanza is None:
            raise ClientConfigurationError(NO_STANZA_MESSAGE)

        runner = SyncRunner(getattr(self, "service", None), stanza)

        emitted = 0
        for row in runner.rows():
            emitted += 1
            yield sanitize(output_row(row))

        puller = runner.puller
        ps_log.info(
            LOG_COMPONENT,
            "finish",
            "degraded" if puller.degraded else "ok",
            records=puller.emitted,
            lookups=puller.requests,
            pages=puller.pages,
            duplicates=puller.duplicates,
            cache_degraded=runner.checkpoint_degraded,
            limit=puller.max_artifacts,
            limit_reached=puller.limit_reached,
            reason=puller.last_failure,
            duration_ms=timer.duration_ms,
        )

        if puller.degraded:
            self.write_warning(DEGRADED_MESSAGE)


def main(argv=None):
    """Console entry point invoked by Splunk."""
    dispatch(
        PolySwarmSyncCommand,
        argv if argv is not None else sys.argv,
        sys.stdin,
        sys.stdout,
        __name__,
    )


if __name__ == "__main__":
    main()
